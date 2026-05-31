/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SYNK_WS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
