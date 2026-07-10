import { SearchBar } from "../components/SearchBar";
import { StatusBadge } from "../components/StatusBadge";
import { UniverseBadge } from "../components/UniverseBadge";
import { PanelsMenu } from "../components/PanelsMenu";

/**
 * Custom draggable title bar. The bar itself is a drag region; interactive
 * children opt out via `.no-drag` so clicks/typing work normally.
 */
export function TitleBar(): JSX.Element {
  return (
    <header className="drag-region flex h-12 shrink-0 items-center gap-4 border-b border-border bg-bg px-4">
      <div className="flex items-center gap-2 pl-16">
        <span className="text-sm font-semibold tracking-tight text-text">
          Borsa <span className="text-accent">AI</span> Terminal
        </span>
      </div>
      <div className="flex flex-1 justify-center">
        <SearchBar />
      </div>
      <PanelsMenu />
      <UniverseBadge />
      <StatusBadge />
    </header>
  );
}
