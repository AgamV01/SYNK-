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

export class SynkClient {
  private ws: WebSocket | null = null;
  private listeners: { [K in keyof ServerMessageMap]: Listener<K>[] } = {
    welcome: [],
    world_state: [],
    agent_event: [],
    dialogue: [],
    error: [],
  };

  on<K extends keyof ServerMessageMap>(type: K, handler: Listener<K>): this {
    this.listeners[type].push(handler);
    return this;
  }

  protected dispatch(msg: ServerMessage): void {
    switch (msg.type) {
      case "welcome":
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
    const ws = new WebSocket(url);
    this.ws = ws;
    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data as string) as ServerMessage;
      this.dispatch(data);
    };
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

  move(position: Vec3, facing?: number): void {
    this.send({ type: "move", v: PROTOCOL_VERSION, position, facing });
  }

  say(target: string, text: string): void {
    this.send({ type: "say", v: PROTOCOL_VERSION, target, text });
  }

  interact(target: string, kind: string, payload?: Record<string, unknown>): void {
    this.send({ type: "interact", v: PROTOCOL_VERSION, target, kind, payload });
  }

  leave(): void {
    this.send({ type: "leave", v: PROTOCOL_VERSION });
  }
}
