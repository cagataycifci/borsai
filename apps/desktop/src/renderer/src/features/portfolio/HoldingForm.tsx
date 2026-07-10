import { useState } from "react";
import { X } from "lucide-react";
import { api } from "../../lib/api";
import type { Holding, HoldingInput } from "../../lib/contracts";

const CURRENCIES = ["USD", "TRY", "EUR", "GBP"];

interface Props {
  /** Existing holding to edit, or null to create a new one. */
  holding: Holding | null;
  onClose: () => void;
  onSaved: () => void;
}

/** Modal form to add or edit a portfolio holding. */
export function HoldingForm({ holding, onClose, onSaved }: Props): JSX.Element {
  const editing = holding != null;
  const [symbol, setSymbol] = useState(holding?.symbol ?? "");
  const [quantity, setQuantity] = useState(holding ? String(holding.quantity) : "");
  const [avgCost, setAvgCost] = useState(holding ? String(holding.avg_cost) : "");
  const [currency, setCurrency] = useState(holding?.currency ?? "USD");
  const [target, setTarget] = useState(holding?.target_price?.toString() ?? "");
  const [stop, setStop] = useState(holding?.stop_loss?.toString() ?? "");
  const [purchaseDate, setPurchaseDate] = useState(
    holding?.purchase_date ? holding.purchase_date.slice(0, 10) : "",
  );
  const [notes, setNotes] = useState(holding?.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function num(value: string): number | null {
    const n = parseFloat(value);
    return value.trim() !== "" && Number.isFinite(n) ? n : null;
  }

  async function submit(): Promise<void> {
    const qty = num(quantity);
    const cost = num(avgCost);
    if (!editing && !symbol.trim()) return setError("Symbol is required.");
    if (qty == null || qty <= 0) return setError("Quantity must be a positive number.");
    if (cost == null || cost < 0) return setError("Average cost must be a number.");

    const payload: HoldingInput = {
      quantity: qty,
      avg_cost: cost,
      currency,
      target_price: num(target),
      stop_loss: num(stop),
      purchase_date: purchaseDate || null,
      notes: notes.trim() || null,
    };

    setSaving(true);
    setError(null);
    try {
      if (editing) {
        await api.updateHolding(holding.id, payload);
      } else {
        await api.addHolding({ ...payload, symbol: symbol.trim().toUpperCase() });
      }
      onSaved();
    } catch {
      setError("Could not save the holding. Is the engine running?");
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="no-drag w-full max-w-sm rounded-lg border border-border bg-bg-panel p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text">
            {editing ? `Edit ${holding.symbol.replace(/\.IS$/, "")}` : "Add Holding"}
          </h2>
          <button onClick={onClose} className="text-text-faint hover:text-text">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <Field label="Symbol" className="col-span-2">
            <input
              value={symbol}
              disabled={editing}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="AAPL or ASELS.IS"
              className="input disabled:opacity-50"
            />
          </Field>
          <Field label="Quantity">
            <input
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              inputMode="decimal"
              placeholder="10"
              className="input"
            />
          </Field>
          <Field label="Avg Cost">
            <input
              value={avgCost}
              onChange={(e) => setAvgCost(e.target.value)}
              inputMode="decimal"
              placeholder="150.00"
              className="input"
            />
          </Field>
          <Field label="Currency">
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="input"
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Purchase Date">
            <input
              type="date"
              value={purchaseDate}
              onChange={(e) => setPurchaseDate(e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Target Price">
            <input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              inputMode="decimal"
              placeholder="optional"
              className="input"
            />
          </Field>
          <Field label="Stop Loss">
            <input
              value={stop}
              onChange={(e) => setStop(e.target.value)}
              inputMode="decimal"
              placeholder="optional"
              className="input"
            />
          </Field>
          <Field label="Notes" className="col-span-2">
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="optional"
              className="input"
            />
          </Field>
        </div>

        {error && <p className="mt-3 text-2xs text-down">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border border-border px-3 py-1.5 text-2xs text-text-muted hover:text-text"
          >
            Cancel
          </button>
          <button
            onClick={() => void submit()}
            disabled={saving}
            className="rounded-md border border-accent/40 bg-accent/15 px-3 py-1.5 text-2xs text-accent hover:bg-accent/25 disabled:opacity-50"
          >
            {saving ? "Saving…" : editing ? "Save" : "Add"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <label className={`flex flex-col gap-1 ${className ?? ""}`}>
      <span className="text-[10px] uppercase tracking-wide text-text-faint">{label}</span>
      {children}
    </label>
  );
}
