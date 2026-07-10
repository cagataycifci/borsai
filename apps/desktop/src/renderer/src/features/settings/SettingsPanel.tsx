import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, KeyRound, Loader2, Save, Trash2, Zap } from "lucide-react";
import { api } from "../../lib/api";
import { useEngineStore } from "../../store/useEngineStore";
import { cn } from "../../lib/cn";

/** Which providers are AI vs data, and which need a key (matches the engine). */
const KEYLESS = new Set(["yfinance", "ollama"]);
const AI_PROVIDER_HINT: Record<string, string> = {
  anthropic: "Claude (recommended) — platform.claude.com",
  openai: "OpenAI — platform.openai.com",
  gemini: "Google Gemini — aistudio.google.com",
  ollama: "Local Ollama — no key required",
};

/**
 * Settings: choose the active AI provider/model and manage provider API keys.
 * Keys are write-only — the engine stores them encrypted and only ever reports
 * whether one is configured.
 */
export function SettingsPanel(): JSX.Element {
  const ready = useEngineStore((s) => s.status === "ready");
  const queryClient = useQueryClient();

  const { data: status } = useQuery({
    queryKey: ["ai", "status"],
    queryFn: ({ signal }) => api.aiStatus(signal),
    enabled: ready,
  });
  const { data: secrets = [] } = useQuery({
    queryKey: ["secrets"],
    queryFn: ({ signal }) => api.listSecrets(signal),
    enabled: ready,
  });

  const [provider, setProvider] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [savingProvider, setSavingProvider] = useState(false);

  // The selection defaults to the engine's current values until edited.
  const activeProvider = provider ?? status?.active_provider ?? "anthropic";
  const modelValue = model ?? status?.model ?? "";

  async function saveProvider(): Promise<void> {
    setSavingProvider(true);
    try {
      await api.setAiProvider(activeProvider, modelValue.trim() || null);
      await queryClient.invalidateQueries({ queryKey: ["ai", "status"] });
      setProvider(null);
      setModel(null);
    } finally {
      setSavingProvider(false);
    }
  }

  if (!ready) {
    return (
      <div className="flex h-full items-center justify-center bg-bg-panel text-text-faint">
        Engine offline — settings unavailable.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-auto bg-bg-panel p-4">
      <h2 className="text-base font-semibold text-text">Settings</h2>

      {/* Active AI provider */}
      <section className="mt-4">
        <h3 className="mb-2 text-2xs font-semibold uppercase tracking-wider text-text-muted">
          AI Provider
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {(status?.providers ?? ["anthropic", "openai", "gemini", "ollama"]).map((p) => {
            const configured = KEYLESS.has(p) || status?.configured[p];
            return (
              <button
                key={p}
                onClick={() => setProvider(p)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm capitalize",
                  activeProvider === p
                    ? "border-accent/50 bg-accent/15 text-accent"
                    : "border-border bg-bg-elevated text-text-muted hover:text-text",
                )}
              >
                {p}
                {configured && <Check className="h-3.5 w-3.5 text-up" />}
              </button>
            );
          })}
        </div>
        <p className="mt-1.5 text-2xs text-text-faint">
          {AI_PROVIDER_HINT[activeProvider] ?? ""}
        </p>

        <label className="mt-3 block text-2xs text-text-muted">
          Model override <span className="text-text-faint">(optional)</span>
        </label>
        <input
          value={modelValue}
          onChange={(e) => setModel(e.target.value)}
          placeholder={
            activeProvider === "gemini"
              ? "gemini-2.5-flash (default)"
              : "Leave blank for the provider default"
          }
          className="input mt-1 w-full"
        />
        {activeProvider === "gemini" && (
          <p className="mt-1 text-2xs text-text-faint">
            Use a full model id (e.g. gemini-2.5-flash), not &quot;gemini&quot;.
          </p>
        )}

        <button
          onClick={() => void saveProvider()}
          disabled={savingProvider}
          className="no-drag mt-3 flex items-center gap-2 rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 text-sm text-accent hover:bg-accent/20 disabled:opacity-50"
        >
          {savingProvider ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Save provider
        </button>
      </section>

      {/* API keys */}
      <section className="mt-6">
        <h3 className="mb-2 flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-text-muted">
          <KeyRound className="h-3.5 w-3.5" />
          API Keys
        </h3>
        <div className="flex flex-col gap-2">
          {secrets
            .filter((s) => !KEYLESS.has(s.provider))
            .map((s) => (
              <KeyRow key={s.provider} provider={s.provider} configured={s.configured} />
            ))}
        </div>
        <p className="mt-2 text-2xs text-text-faint">
          Keys are encrypted at rest and never leave the engine. Ollama runs locally
          and needs no key.
        </p>
      </section>

      <p className="mt-auto pt-4 text-2xs text-text-faint">
        AI output is informational only — not financial advice.
      </p>
    </div>
  );
}

function KeyRow({
  provider,
  configured,
}: {
  provider: string;
  configured: boolean;
}): JSX.Element {
  const queryClient = useQueryClient();
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [verifyMsg, setVerifyMsg] = useState<string | null>(null);
  const [verifyOk, setVerifyOk] = useState<boolean | null>(null);

  async function refresh(): Promise<void> {
    await queryClient.invalidateQueries({ queryKey: ["secrets"] });
    await queryClient.invalidateQueries({ queryKey: ["ai", "status"] });
  }

  async function save(): Promise<void> {
    if (!value.trim()) return;
    setBusy(true);
    setVerifyMsg(null);
    setVerifyOk(null);
    try {
      await api.setSecret(provider, value.trim());
      setValue("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function verify(): Promise<void> {
    setBusy(true);
    setVerifyMsg(null);
    setVerifyOk(null);
    try {
      const result = await api.verifySecret(provider, value.trim() || undefined);
      setVerifyOk(result.ok);
      setVerifyMsg(result.message);
    } catch (err) {
      setVerifyOk(false);
      setVerifyMsg(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  async function clear(): Promise<void> {
    setBusy(true);
    try {
      await api.deleteSecret(provider);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <div className="flex w-24 shrink-0 items-center gap-1.5 text-sm capitalize text-text">
          {provider}
          {configured && (
            <span title="Configured">
              <Check className="h-3.5 w-3.5 text-up" />
            </span>
          )}
        </div>
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={configured ? "•••••••• (set — enter to replace)" : "Enter API key"}
          className="input min-w-0 flex-1"
        />
        <button
          onClick={() => void verify()}
          disabled={busy || (!value.trim() && !configured)}
          title="Test key"
          className="no-drag flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg-elevated text-text-muted hover:text-text disabled:opacity-40"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
        </button>
        <button
          onClick={() => void save()}
          disabled={busy || !value.trim()}
          title="Save key"
          className="no-drag flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg-elevated text-text-muted hover:text-text disabled:opacity-40"
        >
          <Save className="h-4 w-4" />
        </button>
        <button
          onClick={() => void clear()}
          disabled={busy || !configured}
          title="Clear key"
          className="no-drag flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg-elevated text-text-muted hover:text-down disabled:opacity-40"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      {verifyMsg && (
        <p className={cn("pl-26 text-2xs", verifyOk ? "text-up" : "text-down")}>
          {verifyMsg}
        </p>
      )}
    </div>
  );
}
