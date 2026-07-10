/**
 * Reconnecting WebSocket client for the engine's streaming hub.
 *
 * Manages a single connection, tracks the desired symbol subscription set, and
 * re-applies it on (re)connect. Emits decoded {@link StreamFrame}s to listeners.
 */
import type { StreamFrame } from "./contracts";

type FrameListener = (frame: StreamFrame) => void;
type StatusListener = (connected: boolean) => void;

export class QuoteStream {
  private ws: WebSocket | null = null;
  private url: string;
  private symbols = new Set<string>();
  private frameListeners = new Set<FrameListener>();
  private statusListeners = new Set<StatusListener>();
  private reconnectDelay = 1000;
  private readonly maxDelay = 15000;
  private closedByUser = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(httpBaseUrl: string) {
    this.url = QuoteStream.toWsUrl(httpBaseUrl);
  }

  static toWsUrl(httpBaseUrl: string): string {
    const u = new URL(httpBaseUrl);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    u.pathname = "/ws/stream";
    return u.toString();
  }

  setBaseUrl(httpBaseUrl: string): void {
    const next = QuoteStream.toWsUrl(httpBaseUrl);
    if (next !== this.url) {
      this.url = next;
      this.reconnect();
    }
  }

  connect(): void {
    this.closedByUser = false;
    this.open();
  }

  private open(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.emitStatus(true);
      this.applySubscription();
    };
    this.ws.onmessage = (evt) => {
      try {
        const frame = JSON.parse(evt.data) as StreamFrame;
        for (const cb of this.frameListeners) cb(frame);
      } catch {
        /* ignore malformed frame */
      }
    };
    this.ws.onclose = () => {
      this.emitStatus(false);
      if (!this.closedByUser) this.scheduleReconnect();
    };
    this.ws.onerror = () => this.ws?.close();
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay);
      this.open();
    }, this.reconnectDelay);
  }

  private reconnect(): void {
    this.ws?.close();
    this.open();
  }

  subscribe(symbols: string[]): void {
    for (const s of symbols) this.symbols.add(s);
    this.send({ action: "subscribe", symbols });
  }

  unsubscribe(symbols: string[]): void {
    for (const s of symbols) this.symbols.delete(s);
    this.send({ action: "unsubscribe", symbols });
  }

  /** Replace the entire subscription set. */
  setSymbols(symbols: string[]): void {
    const next = new Set(symbols);
    const toAdd = symbols.filter((s) => !this.symbols.has(s));
    const toRemove = [...this.symbols].filter((s) => !next.has(s));
    if (toRemove.length) this.unsubscribe(toRemove);
    if (toAdd.length) this.subscribe(toAdd);
  }

  private applySubscription(): void {
    if (this.symbols.size) {
      this.send({ action: "subscribe", symbols: [...this.symbols] });
    }
  }

  private send(payload: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  onFrame(cb: FrameListener): () => void {
    this.frameListeners.add(cb);
    return () => this.frameListeners.delete(cb);
  }

  onStatus(cb: StatusListener): () => void {
    this.statusListeners.add(cb);
    return () => this.statusListeners.delete(cb);
  }

  private emitStatus(connected: boolean): void {
    for (const cb of this.statusListeners) cb(connected);
  }

  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}
