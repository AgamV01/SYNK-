import { describe, expect, it } from "vitest";

import { Voice } from "./voice";

describe("Voice", () => {
  it("does not listen when disabled", () => {
    const v = new Voice({ enabled: false });
    expect(v.startListening(() => {})).toBe(false);
  });

  it("returns false when enabled but speech recognition is unavailable", () => {
    const v = new Voice({ enabled: true }); // no SpeechRecognition in this env
    expect(v.startListening(() => {})).toBe(false);
  });

  it("speak() is a no-op without speech synthesis (does not throw)", () => {
    const v = new Voice({ enabled: true });
    expect(() => v.speak("hello")).not.toThrow();
  });
});
