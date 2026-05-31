// DOM overlay: proximity prompt + chat input for talking to nearby NPCs.

export interface DemoUIOptions {
  onSay?: (text: string) => void;
  onMic?: () => void;
}

export interface AgentDebugInfo {
  name: string;
  action: string;
  goal?: string | null;
  recent?: string[];
}

// Inputs to the top-right HUD chip: the world clock/phase and token spend.
export interface HudInfo {
  phase: string;
  worldTime: number;
  tokensUsed?: number;
  llmCalls?: number;
}

const PHASE_ICON: Record<string, string> = {
  morning: "🌅",
  day: "☀️",
  evening: "🌇",
  night: "🌙",
};

export class DemoUI {
  private readonly prompt: HTMLDivElement;
  private readonly input: HTMLInputElement;
  private readonly log: HTMLDivElement;
  private readonly debug: HTMLDivElement;
  private readonly hud: HTMLDivElement;
  private nearbyAgentId: string | null = null;
  private readonly onSay?: (text: string) => void;
  private readonly onMic?: () => void;

  constructor(root: HTMLElement, options: DemoUIOptions = {}) {
    this.onSay = options.onSay;
    this.onMic = options.onMic;

    this.hud = document.createElement("div");
    Object.assign(this.hud.style, {
      position: "fixed",
      top: "16px",
      right: "16px",
      padding: "8px 14px",
      borderRadius: "10px",
      background: "rgba(20,20,28,0.7)",
      color: "#eee",
      font: "13px ui-monospace, monospace",
      lineHeight: "1.6",
      textAlign: "right",
      whiteSpace: "pre",
    } satisfies Partial<CSSStyleDeclaration>);
    root.appendChild(this.hud);

    this.log = document.createElement("div");
    Object.assign(this.log.style, {
      position: "fixed",
      top: "16px",
      left: "16px",
      width: "min(320px, 40vw)",
      maxHeight: "40vh",
      overflowY: "auto",
      padding: "10px 12px",
      borderRadius: "10px",
      background: "rgba(20,20,28,0.7)",
      color: "#eee",
      font: "13px system-ui, sans-serif",
      lineHeight: "1.5",
    } satisfies Partial<CSSStyleDeclaration>);
    root.appendChild(this.log);

    this.debug = document.createElement("div");
    Object.assign(this.debug.style, {
      position: "fixed",
      bottom: "16px",
      right: "16px",
      width: "min(300px, 40vw)",
      padding: "10px 12px",
      borderRadius: "10px",
      background: "rgba(20,20,28,0.7)",
      color: "#9fe0a0",
      font: "12px ui-monospace, monospace",
      whiteSpace: "pre-wrap",
      display: "none",
    } satisfies Partial<CSSStyleDeclaration>);
    root.appendChild(this.debug);

    this.prompt = document.createElement("div");
    Object.assign(this.prompt.style, {
      position: "fixed",
      top: "16px",
      left: "50%",
      transform: "translateX(-50%)",
      padding: "8px 14px",
      borderRadius: "8px",
      background: "rgba(20,20,28,0.8)",
      color: "#fff",
      font: "14px system-ui, sans-serif",
      display: "none",
    } satisfies Partial<CSSStyleDeclaration>);
    root.appendChild(this.prompt);

    const form = document.createElement("form");
    Object.assign(form.style, {
      position: "fixed",
      bottom: "16px",
      left: "50%",
      transform: "translateX(-50%)",
      width: "min(560px, 90vw)",
      display: "flex",
      gap: "8px",
    } satisfies Partial<CSSStyleDeclaration>);

    this.input = document.createElement("input");
    this.input.type = "text";
    this.input.placeholder = "Walk up to an NPC and type to talk…";
    Object.assign(this.input.style, {
      flex: "1",
      padding: "10px 14px",
      borderRadius: "10px",
      border: "1px solid #3a3a4a",
      background: "rgba(20,20,28,0.85)",
      color: "#fff",
      font: "15px system-ui, sans-serif",
    } satisfies Partial<CSSStyleDeclaration>);
    form.appendChild(this.input);

    // Push-to-talk: hand voice input off to the wiring (Web Speech STT).
    const mic = document.createElement("button");
    mic.type = "button";
    mic.textContent = "🎤";
    mic.title = "Speak to the nearby NPC (browser speech recognition)";
    Object.assign(mic.style, {
      padding: "10px 12px",
      borderRadius: "10px",
      border: "1px solid #3a3a4a",
      background: "rgba(20,20,28,0.85)",
      color: "#fff",
      cursor: "pointer",
    } satisfies Partial<CSSStyleDeclaration>);
    mic.addEventListener("click", () => this.onMic?.());
    form.appendChild(mic);
    root.appendChild(form);

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = this.input.value.trim();
      if (text && this.nearbyAgentId) {
        this.onSay?.(text);
        this.input.value = "";
      }
    });
  }

  /** Update the top-right HUD: time-of-day clock chip + token spend meter. */
  setHud(info: HudInfo): void {
    const icon = PHASE_ICON[info.phase] ?? "•";
    const clock = `${icon} ${info.phase}  ·  t=${info.worldTime.toFixed(0)}s`;
    const tokens =
      info.tokensUsed !== undefined
        ? `\n🪙 ${info.tokensUsed} tokens · ${info.llmCalls ?? 0} LLM calls`
        : "";
    this.hud.textContent = clock + tokens;
  }

  /** Update the proximity prompt with the nearest agent (or null when none). */
  setNearbyAgent(agentId: string | null, agentName: string | null): void {
    this.nearbyAgentId = agentId;
    if (agentId && agentName) {
      this.prompt.textContent = `Talking range: ${agentName} — type below to speak`;
      this.prompt.style.display = "block";
    } else {
      this.prompt.style.display = "none";
    }
  }

  get currentTarget(): string | null {
    return this.nearbyAgentId;
  }

  /** Put text in the chat input (e.g. a speech-recognition transcript). */
  setChatText(text: string): void {
    this.input.value = text;
  }

  /** Append a dialogue line. Overheard lines (NPC↔NPC or others' chats) are dimmed. */
  addDialogue(speaker: string, text: string, overheard = false): void {
    const line = document.createElement("div");
    const prefix = overheard ? "(overheard) " : "";
    line.textContent = `${prefix}${speaker}: ${text}`;
    if (overheard) {
      line.style.opacity = "0.6";
      line.style.fontStyle = "italic";
    }
    this.log.appendChild(line);
    this.log.scrollTop = this.log.scrollHeight;
  }

  /** Show the legible agent-state panel (current action, goal, recent memory peek). */
  setAgentDebug(info: AgentDebugInfo | null): void {
    if (!info) {
      this.debug.style.display = "none";
      return;
    }
    const lines = [
      `▸ ${info.name}`,
      `action: ${info.action}`,
      `goal:   ${info.goal ?? "—"}`,
      "recent:",
      ...(info.recent && info.recent.length
        ? info.recent.map((m) => `  · ${m}`)
        : ["  · (nothing yet)"]),
    ];
    this.debug.textContent = lines.join("\n");
    this.debug.style.display = "block";
  }
}
