// SYNK wire protocol types — mirrors protocol/messages.md. Keep in sync with the
// Python server. Coordinates are [x, y, z]; facing is yaw radians.

export const PROTOCOL_VERSION = 1;

export type Vec3 = [number, number, number];

// ---- Client -> server ----
export interface JoinMessage {
  type: "join";
  v: number;
  name: string;
  zone?: string;
}

export interface MoveMessage {
  type: "move";
  v: number;
  position: Vec3;
  facing?: number;
}

export interface SayMessage {
  type: "say";
  v: number;
  target: string;
  text: string;
}

export interface InteractMessage {
  type: "interact";
  v: number;
  target: string;
  kind: string;
  payload?: Record<string, unknown>;
}

export interface LeaveMessage {
  type: "leave";
  v: number;
}

export type ClientMessage =
  | JoinMessage
  | MoveMessage
  | SayMessage
  | InteractMessage
  | LeaveMessage;

// ---- Server -> client ----
export interface AgentSnapshot {
  id: string;
  name: string;
  position: Vec3;
  facing: number;
  action: string;
}

export interface ZoneSnapshot {
  tick: number;
  agents: AgentSnapshot[];
}

export interface WelcomeMessage {
  type: "welcome";
  v: number;
  player_id: string;
  token: string;
  tick_rate: number;
  zone: string;
  snapshot: ZoneSnapshot;
}

export interface WorldStateMessage {
  type: "world_state";
  v: number;
  zone: string;
  tick: number;
  agents: AgentSnapshot[];
}

export interface AgentEventMessage {
  type: "agent_event";
  v: number;
  agent_id: string;
  kind: string;
  payload: Record<string, unknown>;
}

export interface DialogueMessage {
  type: "dialogue";
  v: number;
  agent_id: string;
  text: string;
  overheard?: boolean;
}

export interface ErrorMessage {
  type: "error";
  v: number;
  code: string;
  message: string;
}

export type ServerMessage =
  | WelcomeMessage
  | WorldStateMessage
  | AgentEventMessage
  | DialogueMessage
  | ErrorMessage;
