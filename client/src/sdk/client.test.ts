import { beforeEach, describe, expect, it, vi } from "vitest";

import { SynkClient } from "./index";

// Minimal fake WebSocket installed as the global, so we can drive the client.
class FakeWS {
  static instances: FakeWS[] = [];
  url: string;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(url: string) {
    this.url = url;
    FakeWS.instances.push(this);
  }
  send(data: string): void {
    this.sent.push(data);
  }
  close(): void {
    this.onclose?.();
  }
  lastSent(): Record<string, unknown> {
    return JSON.parse(this.sent[this.sent.length - 1]);
  }
}

beforeEach(() => {
  FakeWS.instances = [];
  (globalThis as Record<string, unknown>).WebSocket = FakeWS;
});

describe("SynkClient", () => {
  it("captures the token from welcome and attaches it to intents", () => {
    const client = new SynkClient();
    const welcomes: unknown[] = [];
    client.on("welcome", (m) => welcomes.push(m));
    client.connect("ws://x/ws");
    const ws = FakeWS.instances[0];
    ws.onopen?.();
    ws.onmessage?.({
      data: JSON.stringify({
        type: "welcome", v: 1, player_id: "p1", token: "tok123",
        tick_rate: 10, zone: "z", snapshot: { tick: 0, agents: [] },
      }),
    });
    expect(welcomes.length).toBe(1);
    client.move([1, 0, 2], 0);
    const sent = ws.lastSent();
    expect(sent.type).toBe("move");
    expect(sent.token).toBe("tok123");
  });

  it("dispatches typed server messages to registered listeners", () => {
    const client = new SynkClient();
    const dialogues: Array<{ text: string }> = [];
    client.on("dialogue", (m) => dialogues.push(m));
    client.connect("ws://x/ws");
    FakeWS.instances[0].onmessage?.({
      data: JSON.stringify({ type: "dialogue", v: 1, agent_id: "g", text: "hi", overheard: false }),
    });
    expect(dialogues[0].text).toBe("hi");
  });

  it("auto-reconnects with backoff after the socket closes", () => {
    vi.useFakeTimers();
    try {
      const client = new SynkClient({ baseBackoffMs: 100, maxBackoffMs: 1000 });
      client.connect("ws://x/ws");
      expect(FakeWS.instances.length).toBe(1);
      FakeWS.instances[0].close();
      vi.advanceTimersByTime(100);
      expect(FakeWS.instances.length).toBe(2); // reconnected
    } finally {
      vi.useRealTimers();
    }
  });

  it("stops reconnecting after disconnect()", () => {
    vi.useFakeTimers();
    try {
      const client = new SynkClient({ baseBackoffMs: 100 });
      client.connect("ws://x/ws");
      client.disconnect();
      FakeWS.instances[0].close();
      vi.advanceTimersByTime(1000);
      expect(FakeWS.instances.length).toBe(1); // no reconnect
    } finally {
      vi.useRealTimers();
    }
  });
});
