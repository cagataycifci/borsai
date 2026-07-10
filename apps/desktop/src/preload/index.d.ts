import type { BorsaApi } from "./index";

declare global {
  interface Window {
    borsa: BorsaApi;
  }
}

export {};
