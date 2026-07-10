import { useEffect, useRef, useState } from "react";
import { LayoutGrid, RotateCcw, ChevronDown, Check } from "lucide-react";
import { cn } from "../lib/cn";
import { useWorkspaceStore } from "../store/useWorkspaceStore";
import { PANELS } from "../features/workspace/panelRegistry";

/**
 * Top-bar "Panels" dropdown: reopen/focus any registered panel (closed ones
 * included) and restore the default layout. Pairs with the Workspace empty-state
 * so closed panels are always recoverable.
 */
export function PanelsMenu(): JSX.Element {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const openIds = useWorkspaceStore((s) => s.openIds);
  const openPanel = useWorkspaceStore((s) => s.openPanel);
  const resetLayout = useWorkspaceStore((s) => s.resetLayout);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const openSet = new Set(openIds);

  return (
    <div ref={ref} className="no-drag relative">
      <button
        onClick={() => setOpen((o) => !o)}
        title="Panels"
        className="flex items-center gap-1.5 rounded-md border border-border bg-bg-elevated px-2.5 py-1.5 text-2xs font-medium text-text-muted hover:text-text"
      >
        <LayoutGrid className="h-3.5 w-3.5" />
        Panels
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-1 w-52 rounded-md border border-border bg-bg-panel py-1 shadow-xl">
          {PANELS.map((p) => {
            const isOpen = openSet.has(p.id);
            return (
              <button
                key={p.id}
                onClick={() => {
                  openPanel(p.id);
                  setOpen(false);
                }}
                className="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-2xs text-text-muted hover:bg-bg-hover hover:text-text"
              >
                <span className="flex items-center gap-2">
                  {p.title}
                  {p.phase && (
                    <span className="rounded bg-bg-elevated px-1 py-0.5 text-[10px] text-text-faint">
                      Phase {p.phase}
                    </span>
                  )}
                </span>
                <Check
                  className={cn(
                    "h-3.5 w-3.5 shrink-0",
                    isOpen ? "text-accent" : "text-transparent",
                  )}
                />
              </button>
            );
          })}

          <div className="my-1 border-t border-border" />
          <button
            onClick={() => {
              resetLayout();
              setOpen(false);
            }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-2xs text-text-muted hover:bg-bg-hover hover:text-text"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset Layout
          </button>
        </div>
      )}
    </div>
  );
}
