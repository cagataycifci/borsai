import { Sidebar } from "./Sidebar";
import { TitleBar } from "./TitleBar";
import { Workspace } from "./Workspace";
import { useEngineBootstrap } from "../hooks/useEngineBootstrap";
import { useMarketStream } from "../hooks/useMarketStream";
import { useQuoteSeeder } from "../hooks/useQuoteSeeder";
import { useWatchlistBootstrap } from "../hooks/useWatchlistBootstrap";
import { useEngineStore } from "../store/useEngineStore";

function EngineOfflineBanner(): JSX.Element | null {
  const status = useEngineStore((s) => s.status);
  if (status !== "error") return null;
  return (
    <div className="shrink-0 bg-down/15 px-4 py-1.5 text-center text-2xs text-down">
      Engine is offline — start it with{" "}
      <span className="font-mono">npm run dev</span> or check the logs.
    </div>
  );
}

export function App(): JSX.Element {
  // Wire the app-wide data lifecycle once, at the root.
  useEngineBootstrap();
  useMarketStream();
  useQuoteSeeder();
  useWatchlistBootstrap();

  return (
    <div className="flex h-full w-full flex-col">
      <TitleBar />
      <EngineOfflineBanner />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <main className="min-w-0 flex-1">
          <Workspace />
        </main>
      </div>
    </div>
  );
}
