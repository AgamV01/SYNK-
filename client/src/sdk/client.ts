// SynkClient: a typed WebSocket client for the SYNK protocol.

import { PROTOCOL_VERSION } from "./types";
import type {
  AgentEventMessage,
  ClientMessage,
  DialogueMessage,
  ErrorMessage,
  ServerMessage,
  Vec3,
  WelcomeMessage,
  WorldStateMessage,
} from "./types";

interface ServerMessageMap {
  welcome: WelcomeMessage;
  world_state: WorldStateMessage;
  agent_event: AgentEventMessage;
  dialogue: DialogueMessage;
  error: ErrorMessage;
}

type Listener<K extends keyof ServerMessageMap> = (msg: ServerMessageMap[K]) => void;

export interface SynkClientOptions {
  baseBackoffMs?: number;
  maxBackoffMs?: number;
}

export class SynkClient {
  private ws: WebSocket | null = null;
  private url = "";
  private shouldReconnect = false;
  private reconnectAttempts = 0;
  private readonly baseBackoffMs: number;
  private readonly maxBackoffMs: number;
  private sessionToken: string | null = null;
  private listeners: { [K in keyof ServerMessageMap]: Listener<K>[] } = {
    welcome: [],
    world_state: [],
    agent_event: [],
    dialogue: [],
    error: [],
  };

  constructor(options: SynkClientOptions = {}) {
    this.baseBackoffMs = options.baseBackoffMs ?? 250;
    this.maxBackoffMs = options.maxBackoffMs ?? 10000;
  }

  private readonly openHandlers: Array<() => void> = [];

  on<K extends keyof ServerMessageMap>(type: K, handler: Listener<K>): this {
    this.listeners[type].push(handler);
    return this;
  }

  /** Register a callback fired whenever the socket (re)connects. */
  onOpen(handler: () => void): this {
    this.openHandlers.push(handler);
    return this;
  }

  protected dispatch(msg: ServerMessage): void {
    switch (msg.type) {
      case "welcome":
        this.sessionToken = msg.token; // capture for authenticated intents
        this.listeners.welcome.forEach((fn) => fn(msg));
        break;
      case "world_state":
        this.listeners.world_state.forEach((fn) => fn(msg));
        break;
      case "agent_event":
        this.listeners.agent_event.forEach((fn) => fn(msg));
        break;
      case "dialogue":
        this.listeners.dialogue.forEach((fn) => fn(msg));
        break;
      case "error":
        this.listeners.error.forEach((fn) => fn(msg));
        break;
    }
  }

  connect(url: string): void {
    this.url = url;
    this.shouldReconnect = true;
    this.open();
  }

  private open(): void {
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.openHandlers.forEach((fn) => fn());
    };
    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data as string) as ServerMessage;
      this.dispatch(data);
    };
    ws.onclose = () => {
      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    const delay = Math.min(
      this.maxBackoffMs,
      this.baseBackoffMs * 2 ** this.reconnectAttempts,
    );
    this.reconnectAttempts += 1;
    setTimeout(() => {
      if (this.shouldReconnect) {
        this.open();
      }
    }, delay);
  }

  /** Stop reconnecting and close the socket. */
  disconnect(): void {
    this.shouldReconnect = false;
    this.ws?.close();
  }

  get socket(): WebSocket | null {
    return this.ws;
  }

  // ---- Intents (client -> server) ----
  protected send(msg: ClientMessage): void {
    this.ws?.send(JSON.stringify(msg));
  }

  join(name: string, zone?: string): void {
    this.send({ type: "join", v: PROTOCOL_VERSION, name, zone });
  }

  private get token(): string | undefined {
    return this.sessionToken ?? undefined;
  }

  move(position: Vec3, facing?: number): void {
    this.send({ type: "move", v: PROTOCOL_VERSION, position, facing, token: this.token });
  }

  say(target: string, text: string): void {
    this.send({ type: "say", v: PROTOCOL_VERSION, target, text, token: this.token });
  }

  interact(target: string, kind: string, payload?: Record<string, unknown>): void {
    this.send({ type: "interact", v: PROTOCOL_VERSION, target, kind, payload, token: this.token });
  }

  leave(): void {
    this.send({ type: "leave", v: PROTOCOL_VERSION, token: this.token });
  }
}
