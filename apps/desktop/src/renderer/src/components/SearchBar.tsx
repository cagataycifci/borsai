import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../lib/api";
import { useWatchlistStore } from "../store/useWatchlistStore";
import type { FacetHit, SymbolRef } from "../lib/contracts";
import { ExchangeBadge } from "./ExchangeBadge";
import { cn } from "../lib/cn";

/** Global search: tickers, sectors, industries, and countries (Phase 9). */
export function SearchBar(): JSX.Element {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const addSymbol = useWatchlistStore((s) => s.add);
  const setActive = useWatchlistStore((s) => s.setActive);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(t);
  }, [query]);

  const { data, isFetching } = useQuery({
    queryKey: ["search", "global", debounced],
    queryFn: ({ signal }) => api.globalSearch(debounced, signal),
    enabled: debounced.length >= 1,
    staleTime: 60_000,
  });

  const symbols = data?.symbols ?? [];
  const facets = data?.facets ?? [];

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function selectSymbol(symbol: string) {
    addSymbol(symbol);
    setActive(symbol);
    setQuery("");
    setOpen(false);
  }

  async function selectFacet(facet: FacetHit) {
    const syms = await api.facetSymbols(facet.kind, facet.label);
    if (syms[0]) selectSymbol(syms[0].symbol);
    else setOpen(false);
  }

  const empty = !isFetching && symbols.length === 0 && facets.length === 0;

  return (
    <div ref={containerRef} className="no-drag relative w-80 max-w-[40vw]">
      <div className="flex items-center gap-2 rounded-md border border-border bg-bg-elevated px-3 py-1.5 focus-within:border-accent">
        <Search className="h-4 w-4 text-text-faint" />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search ticker, sector, country…"
          className="w-full bg-transparent text-sm text-text placeholder:text-text-faint focus:outline-none"
          spellCheck={false}
        />
      </div>

      {open && debounced.length >= 1 && (
        <div className="absolute z-50 mt-1 max-h-96 w-full overflow-auto rounded-md border border-border bg-bg-panel shadow-xl">
          {isFetching && empty && (
            <div className="px-3 py-2 text-2xs text-text-faint">Searching…</div>
          )}
          {empty && !isFetching && (
            <div className="px-3 py-2 text-2xs text-text-faint">No matches</div>
          )}

          {facets.length > 0 && (
            <div className="border-b border-border px-2 py-1">
              <div className="px-1 py-1 text-2xs font-semibold uppercase tracking-wider text-text-faint">
                Facets
              </div>
              {facets.map((f) => (
                <button
                  key={`${f.kind}-${f.label}`}
                  onClick={() => void selectFacet(f)}
                  className="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left hover:bg-bg-hover"
                >
                  <div>
                    <span className="text-2xs uppercase text-accent">{f.kind}</span>
                    <div className="text-sm text-text">{f.label}</div>
                  </div>
                  <span className="text-2xs text-text-faint">{f.count} symbols</span>
                </button>
              ))}
            </div>
          )}

          {symbols.map((r) => (
            <SymbolRow key={r.symbol} ref_={r} onSelect={() => selectSymbol(r.symbol)} />
          ))}
        </div>
      )}
    </div>
  );
}

function SymbolRow({
  ref_,
  onSelect,
}: {
  ref_: SymbolRef;
  onSelect: () => void;
}): JSX.Element {
  return (
    <button
      onClick={onSelect}
      className={cn("flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-bg-hover")}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-text">{ref_.display_symbol}</span>
          <ExchangeBadge exchange={ref_.exchange} />
        </div>
        <div className="truncate text-2xs text-text-muted">{ref_.name}</div>
      </div>
      <span className="text-2xs text-text-faint">{ref_.currency}</span>
    </button>
  );
}
