import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Sparkles,
  Send,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Settings as SettingsIcon,
} from "lucide-react";
import { api, streamChat, ApiError } from "../../lib/api";
import { useEngineStore } from "../../store/useEngineStore";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { useWorkspaceStore } from "../../store/useWorkspaceStore";
import { cn } from "../../lib/cn";
import { formatRelativeTime } from "../../lib/format";
import type { AnalysisReport, ChatMessage, Sentiment } from "../../lib/contracts";

type Tab = "report" | "chat";

const SENTIMENT_META: Record<
  Sentiment,
  { label: string; cls: string; Icon: typeof TrendingUp }
> = {
  bullish: { label: "Bullish", cls: "text-up", Icon: TrendingUp },
  bearish: { label: "Bearish", cls: "text-down", Icon: TrendingDown },
  neutral: { label: "Neutral", cls: "text-text-muted", Icon: Minus },
};

const RATING_LABELS = ["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"];

function SentimentBadge({ sentiment }: { sentiment: Sentiment }): JSX.Element {
  const { label, cls, Icon } = SENTIMENT_META[sentiment];
  return (
    <span className={cn("flex items-center gap-1 text-sm font-semibold", cls)}>
      <Icon className="h-4 w-4" />
      {label}
    </span>
  );
}

/** AI layer: model-driven stock analysis (structured report) + streaming chat. */
export function AiPanel(): JSX.Element {
  const ready = useEngineStore((s) => s.status === "ready");
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const openPanel = useWorkspaceStore((s) => s.openPanel);
  const [tab, setTab] = useState<Tab>("report");

  const { data: status } = useQuery({
    queryKey: ["ai", "status"],
    queryFn: ({ signal }) => api.aiStatus(signal),
    enabled: ready,
    staleTime: 30_000,
  });

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Sparkles className="h-4 w-4 text-accent" />
        <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
          AI Analysis
        </span>
        <div className="ml-2 flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated p-0.5">
          {(["report", "chat"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "rounded px-2 py-0.5 text-2xs font-medium capitalize transition-colors",
                tab === t ? "bg-accent/20 text-accent" : "text-text-muted hover:text-text",
              )}
            >
              {t}
            </button>
          ))}
        </div>
        {status && (
          <span className="ml-auto text-2xs text-text-faint" title={status.model}>
            {status.active_provider}
          </span>
        )}
      </div>

      {status && !status.ready && (
        <button
          onClick={() => openPanel("settings")}
          className="no-drag flex items-center gap-2 border-b border-warn/30 bg-warn/10 px-3 py-2 text-left text-2xs text-warn hover:bg-warn/20"
        >
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          No AI provider configured. Click to add an API key in Settings.
          <SettingsIcon className="ml-auto h-3.5 w-3.5 shrink-0" />
        </button>
      )}

      <div className="min-h-0 flex-1">
        {tab === "report" ? (
          <ReportView symbol={activeSymbol} ready={ready} />
        ) : (
          <ChatView symbol={activeSymbol} ready={ready} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Report tab
// ---------------------------------------------------------------------------

function ReportView({
  symbol,
  ready,
}: {
  symbol: string | null;
  ready: boolean;
}): JSX.Element {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load the latest cached report when the symbol changes (404 → no report yet).
  useEffect(() => {
    setReport(null);
    setError(null);
    if (!symbol || !ready) return;
    const ctrl = new AbortController();
    api
      .getLatestReport(symbol, ctrl.signal)
      .then(setReport)
      .catch(() => {
        /* no cached report — leave empty */
      });
    return () => ctrl.abort();
  }, [symbol, ready]);

  async function runAnalysis(): Promise<void> {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      setReport(await api.analyze(symbol));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  if (!symbol) {
    return (
      <div className="flex h-full items-center justify-center text-text-faint">
        Select a symbol to analyze.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-auto p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-mono text-lg font-semibold text-text">
          {symbol.replace(/\.IS$/, "")}
        </h2>
        <button
          onClick={() => void runAnalysis()}
          disabled={loading || !ready}
          className="no-drag flex items-center gap-2 rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 text-sm text-accent hover:bg-accent/20 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {report ? "Re-analyze" : "Analyze"}
        </button>
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-down/30 bg-down/10 px-3 py-2 text-2xs text-down">
          {error}
        </div>
      )}

      {loading && !report && (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center text-text-muted">
          <Loader2 className="h-7 w-7 animate-spin text-accent" />
          <p className="text-sm">Analyzing {symbol.replace(/\.IS$/, "")}…</p>
        </div>
      )}

      {!loading && !report && !error && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-text-faint">
          <Sparkles className="h-7 w-7 text-text-faint" />
          <p className="text-sm">No analysis yet.</p>
          <p className="text-2xs">Click Analyze to generate a model-driven report.</p>
        </div>
      )}

      {report && (
        <div className="mt-4 flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-md border border-border bg-bg-elevated px-3 py-2">
            <SentimentBadge sentiment={report.sentiment} />
            <div className="text-right">
              <div className="tabular text-sm font-semibold text-text">
                {RATING_LABELS[report.rating - 1] ?? "Hold"}
              </div>
              <div className="text-2xs text-text-faint">Rating {report.rating}/5</div>
            </div>
          </div>

          {report.summary && (
            <Section title="Summary">
              <p className="text-sm leading-relaxed text-text">{report.summary}</p>
            </Section>
          )}

          {report.key_points.length > 0 && (
            <Section title="Key Points">
              <Bullets items={report.key_points} dot="bg-up" />
            </Section>
          )}

          {report.risks.length > 0 && (
            <Section title="Risks">
              <Bullets items={report.risks} dot="bg-down" />
            </Section>
          )}

          {report.technical_outlook && (
            <Section title="Technical Outlook">
              <p className="text-sm leading-relaxed text-text">
                {report.technical_outlook}
              </p>
            </Section>
          )}

          {report.recommendation && (
            <Section title="Recommendation">
              <p className="text-sm leading-relaxed text-text">{report.recommendation}</p>
            </Section>
          )}

          <div className="mt-1 border-t border-border/60 pt-2 text-2xs text-text-faint">
            {report.provider} · {report.model}
            {report.created_at ? ` · ${formatRelativeTime(report.created_at)}` : ""}
            <div className="mt-0.5">{report.disclaimer}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <div>
      <h3 className="mb-1.5 text-2xs font-semibold uppercase tracking-wider text-text-muted">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Bullets({ items, dot }: { items: string[]; dot: string }): JSX.Element {
  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-text">
          <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", dot)} />
          {item}
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Chat tab
// ---------------------------------------------------------------------------

function ChatView({
  symbol,
  ready,
}: {
  symbol: string | null;
  ready: boolean;
}): JSX.Element {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, streaming]);

  async function send(): Promise<void> {
    const text = input.trim();
    if (!text || streaming || !ready) return;
    setInput("");
    setError(null);
    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    // Append an empty assistant message we stream tokens into.
    setMessages([...next, { role: "assistant", content: "" }]);
    setStreaming(true);
    try {
      await streamChat(next, symbol, (token) => {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + token };
          return copy;
        });
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Chat failed.");
      setMessages((prev) => prev.filter((m, i) => !(i === prev.length - 1 && !m.content)));
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto p-3">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-text-faint">
            <Sparkles className="h-7 w-7" />
            <p className="text-sm">Ask the AI about markets{symbol ? ` or ${symbol.replace(/\.IS$/, "")}` : ""}.</p>
            <p className="text-2xs">Informational only — not financial advice.</p>
          </div>
        )}
        <div className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap",
                m.role === "user"
                  ? "self-end bg-accent/15 text-text"
                  : "self-start bg-bg-elevated text-text",
              )}
            >
              {m.content || (
                <Loader2 className="h-4 w-4 animate-spin text-text-muted" />
              )}
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="border-t border-down/30 bg-down/10 px-3 py-1.5 text-2xs text-down">
          {error}
        </div>
      )}

      <div className="flex items-end gap-2 border-t border-border p-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          rows={1}
          placeholder={ready ? "Ask a question…" : "Engine offline"}
          disabled={!ready || streaming}
          className="no-drag max-h-28 min-h-[2.25rem] flex-1 resize-none rounded-md border border-border bg-bg-elevated px-3 py-2 text-sm text-text placeholder:text-text-faint focus:border-accent focus:outline-none disabled:opacity-50"
        />
        <button
          onClick={() => void send()}
          disabled={!ready || streaming || !input.trim()}
          title="Send"
          className="no-drag flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-accent/40 bg-accent/10 text-accent hover:bg-accent/20 disabled:opacity-40"
        >
          {streaming ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
