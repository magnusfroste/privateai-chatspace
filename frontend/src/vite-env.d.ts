/// <reference types="vite/client" />

declare const __APP_VERSION__: string
declare const __BUILD_DATE__: string

interface ImportMetaEnv {
  readonly VITE_DEV_AUTO_LOGIN: string
  readonly VITE_DEV_EMAIL: string
  readonly VITE_DEV_PASSWORD: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
