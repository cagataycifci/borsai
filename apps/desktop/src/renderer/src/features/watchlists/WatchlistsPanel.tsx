import { useState } from "react";
import { Plus, Pencil, Trash2, Check, X, ChevronUp, ChevronDown } from "lucide-react";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { useQuotesStore } from "../../store/useQuotesStore";
import { cn } from "../../lib/cn";
import { formatPercent, formatPrice, trendClass } from "../../lib/format";
import { ExchangeBadge } from "../../components/ExchangeBadge";

/**
 * Full watchlist manager: create/rename/delete multiple lists, switch the active
 * one, add/remove/reorder symbols. Shares {@link useWatchlistStore} with the
 * dashboard WatchPanel, so changes here reflect everywhere instantly.
 */
export function WatchlistsPanel(): JSX.Element {
  const watchlists = useWatchlistStore((s) => s.watchlists);
  const activeId = useWatchlistStore((s) => s.activeWatchlistId);
  const loaded = useWatchlistStore((s) => s.loaded);
  const setActiveWatchlist = useWatchlistStore((s) => s.setActiveWatchlist);
  const createWatchlist = useWatchlistStore((s) => s.createWatchlist);
  const renameWatchlist = useWatchlistStore((s) => s.renameWatchlist);
  const deleteWatchlist = useWatchlistStore((s) => s.deleteWatchlist);
  const symbols = useWatchlistStore((s) => s.symbols);
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const setActive = useWatchlistStore((s) => s.setActive);
  const add = useWatchlistStore((s) => s.add);
  const remove = useWatchlistStore((s) => s.remove);
  const reorder = useWatchlistStore((s) => s.reorder);
  const quotes = useQuotesStore((s) => s.quotes);

  const [creating, setCreating] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newSymbol, setNewSymbol] = useState("");

  const active = watchlists.find((w) => w.id === activeId) ?? null;

  function submitCreate(): void {
    const name = draftName.trim();
    if (name) void createWatchlist(name);
    setDraftName("");
    setCreating(false);
  }

  function submitRename(id: number): void {
    const name = draftName.trim();
    if (name) void renameWatchlist(id, name);
    setEditingId(null);
    setDraftName("");
  }

  function move(index: number, dir: -1 | 1): void {
    const next = [...symbols];
    const target = index + dir;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    reorder(next);
  }

  function submitAddSymbol(): void {
    const sym = newSymbol.trim();
    if (sym) add(sym);
    setNewSymbol("");
  }

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      {/* Watchlist tabs + create */}
      <div className="flex flex-wrap items-center gap-1 border-b border-border px-3 py-2">
        {watchlists.map((w) =>
          editingId === w.id ? (
            <span key={w.id} className="flex items-center gap-1">
              <input
                autoFocus
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitRename(w.id);
                  if (e.key === "Escape") setEditingId(null);
                }}
                className="no-drag w-28 rounded border border-accent/50 bg-bg-elevated px-1.5 py-0.5 text-2xs text-text outline-none"
              />
              <button onClick={() => submitRename(w.id)} className="no-drag text-accent">
                <Check className="h-3.5 w-3.5" />
              </button>
            </span>
          ) : (
            <button
              key={w.id}
              onClick={() => setActiveWatchlist(w.id)}
              className={cn(
                "no-drag rounded px-2 py-1 text-2xs font-medium transition-colors",
                w.id === activeId
                  ? "bg-accent/20 text-accent"
                  : "text-text-muted hover:bg-bg-hover hover:text-text",
              )}
            >
              {w.name}
              <span className="ml-1 text-text-faint">{w.symbols.length}</span>
            </button>
          ),
        )}

        {creating ? (
          <span className="flex items-center gap-1">
            <input
              autoFocus
              value={draftName}
              placeholder="Name…"
              onChange={(e) => setDraftName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitCreate();
                if (e.key === "Escape") {
                  setCreating(false);
                  setDraftName("");
                }
              }}
              className="no-drag w-28 rounded border border-accent/50 bg-bg-elevated px-1.5 py-0.5 text-2xs text-text outline-none"
            />
            <button onClick={submitCreate} className="no-drag text-accent">
              <Check className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : (
          <button
            onClick={() => {
              setCreating(true);
              setDraftName("");
            }}
            title="New watchlist"
            className="no-drag flex items-center gap-1 rounded px-2 py-1 text-2xs text-text-muted hover:bg-bg-hover hover:text-text"
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </button>
        )}
      </div>

      {/* Active list actions */}
      {active && (
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
            {active.name}
          </span>
          <button
            onClick={() => {
              setEditingId(active.id);
              setDraftName(active.name);
            }}
            title="Rename"
            className="no-drag text-text-faint hover:text-text"
          >
            <Pencil className="h-3 w-3" />
          </button>
          <button
            onClick={() => void deleteWatchlist(active.id)}
            title="Delete watchlist"
            disabled={watchlists.length <= 1}
            className={cn(
              "no-drag",
              watchlists.length <= 1
                ? "text-text-faint opacity-40"
                : "text-text-faint hover:text-down",
            )}
          >
            <Trash2 className="h-3 w-3" />
          </button>
          <div className="ml-auto flex items-center gap-1">
            <input
              value={newSymbol}
              placeholder="Add symbol…"
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && submitAddSymbol()}
              className="no-drag w-28 rounded border border-border bg-bg-elevated px-1.5 py-0.5 text-2xs text-text outline-none focus:border-accent/50"
            />
            <button
              onClick={submitAddSymbol}
              title="Add"
              className="no-drag rounded bg-accent/15 px-1.5 py-0.5 text-accent hover:bg-accent/25"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Symbols */}
      <div className="flex-1 overflow-auto">
        {!loaded && (
          <div className="flex h-full items-center justify-center text-text-faint">
            Loading watchlists…
          </div>
        )}
        {loaded && symbols.length === 0 && (
          <div className="flex h-full items-center justify-center text-text-faint">
            No symbols — add one above.
          </div>
        )}
        {symbols.map((symbol, i) => {
          const q = quotes[symbol];
          const isActive = symbol === activeSymbol;
          return (
            <div
              key={symbol}
              onClick={() => setActive(symbol)}
              className={cn(
                "group flex cursor-pointer items-center gap-2 border-l-2 px-3 py-2 hover:bg-bg-hover",
                isActive ? "border-accent bg-bg-elevated" : "border-transparent",
              )}
            >
              <div className="flex flex-col">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    move(i, -1);
                  }}
                  disabled={i === 0}
                  className="no-drag text-text-faint hover:text-text disabled:opacity-20"
                >
                  <ChevronUp className="h-3 w-3" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    move(i, 1);
                  }}
                  disabled={i === symbols.length - 1}
                  className="no-drag text-text-faint hover:text-text disabled:opacity-20"
                >
                  <ChevronDown className="h-3 w-3" />
                </button>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-text">
                    {q?.display_symbol ?? symbol.replace(/\.IS$/, "")}
                  </span>
                  {q && <ExchangeBadge exchange={q.exchange} />}
                </div>
                <div className="truncate text-2xs text-text-faint">{q?.name ?? "—"}</div>
              </div>
              <div className="text-right">
                <div className="tabular text-sm text-text">
                  {q ? formatPrice(q.price, q.currency) : "…"}
                </div>
                <div className={cn("tabular text-2xs", trendClass(q?.change_percent))}>
                  {q ? formatPercent(q.change_percent) : ""}
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  remove(symbol);
                }}
                title="Remove"
                className="no-drag opacity-0 transition-opacity group-hover:opacity-100"
              >
                <X className="h-3.5 w-3.5 text-text-faint hover:text-down" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
