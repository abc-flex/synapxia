/// <reference path="../.astro/types.d.ts" />

interface ImportMetaEnv {
  readonly PUBLIC_API_PATH: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}