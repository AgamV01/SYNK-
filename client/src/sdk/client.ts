// SynkClient: a typed WebSocket client for the SYNK protocol.

import type {
  AgentEventMessage,
  DialogueMessage,
  ErrorMessage,
  ServerMessage,
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
}
