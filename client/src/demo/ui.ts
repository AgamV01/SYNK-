// DOM overlay: proximity prompt + chat input for talking to nearby NPCs.

export interface DemoUIOptions {
  onSay?: (text: string) => void;
}

export class DemoUI {
  private readonly prompt: HTMLDivElement;
  private readonly input: HTMLInputElement;
  private nearbyAgentId: string | null = null;
  private readonly onSay?: (text: string) => void;

  constructor(root: HTMLElement, options: DemoUIOptions = {}) {
    this.onSay = options.onSay;

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
    } satisfies Partial<CSSStyleDeclaration>);

    this.input = document.createElement("input");
    this.input.type = "text";
    this.input.placeholder = "Walk up to an NPC and type to talk…";
    Object.assign(this.input.style, {
      width: "100%",
      padding: "10px 14px",
      borderRadius: "10px",
      border: "1px solid #3a3a4a",
      background: "rgba(20,20,28,0.85)",
      color: "#fff",
      font: "15px system-ui, sans-serif",
    } satisfies Partial<CSSStyleDeclaration>);
    form.appendChild(this.input);
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
}
