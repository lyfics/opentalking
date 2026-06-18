/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  /** Max chat bubbles to show (most recent). 0 or unset = show all. */
  readonly VITE_CHAT_MAX_VISIBLE?: string;
  /** Extra media WebSocket video delay in ms; positive values delay lips relative to audio. */
  readonly VITE_MEDIA_WS_VIDEO_DELAY_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
