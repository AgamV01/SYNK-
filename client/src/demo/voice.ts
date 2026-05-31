// Browser-native voice: TTS for NPC lines, STT for player input. Feature-flagged
// OFF by default — the demo works fully without it.

export interface VoiceOptions {
  enabled?: boolean;
  lang?: string;
}

// Minimal typed shims for the non-standard SpeechRecognition API (no `any`).
interface SpeechRecognitionAlternativeLike {
  transcript: string;
}
interface SpeechRecognitionResultLike {
  0: SpeechRecognitionAlternativeLike;
}
interface SpeechRecognitionEventLike {
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  start(): void;
  stop(): void;
}
interface SpeechCapableWindow {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
}

export class Voice {
  enabled: boolean;
  private readonly lang: string;
  private recognition: SpeechRecognitionLike | null = null;

  constructor(options: VoiceOptions = {}) {
    this.enabled = options.enabled ?? false; // off by default
    this.lang = options.lang ?? "en-US";
  }

  /** Speak a line via the browser's TTS. No-op when disabled or unsupported. */
  speak(text: string): void {
    if (!this.enabled || typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = this.lang;
    window.speechSynthesis.speak(utterance);
  }

  /** Start one-shot speech recognition. Returns false if disabled/unsupported. */
  startListening(onResult: (text: string) => void): boolean {
    if (!this.enabled || typeof window === "undefined") return false;
    const w = window as unknown as SpeechCapableWindow;
    const Recognition = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Recognition) return false;
    const recognition = new Recognition();
    recognition.lang = this.lang;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const result = event.results[0];
      if (result) onResult(result[0].transcript);
    };
    recognition.start();
    this.recognition = recognition;
    return true;
  }

  stopListening(): void {
    this.recognition?.stop();
    this.recognition = null;
  }
}
