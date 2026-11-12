import { useEffect, useState } from "react";
import type { PolicyItem } from "../api/client";
import { customFromPreset, validateThresholds, type PolicyState } from "../store/policy";

type Props = {
  policies: PolicyItem[];
  state: PolicyState;
  onChange: (next: PolicyState) => void;
  defaultThresholds: { pBorrowNow: number; pWait: number };
};

const CUSTOM_ID = "custom";

export function PolicySelect({ policies, state, onChange, defaultThresholds }: Props) {
  const [borrowInput, setBorrowInput] = useState(
    String(state.mode === "custom" ? state.pBorrowNow : defaultThresholds.pBorrowNow),
  );
  const [waitInput, setWaitInput] = useState(
    String(state.mode === "custom" ? state.pWait : defaultThresholds.pWait),
  );

  useEffect(() => {
    if (state.mode === "custom") {
      setBorrowInput(String(state.pBorrowNow));
      setWaitInput(String(state.pWait));
    }
  }, [state]);

  const selectedId = state.mode === "custom" ? CUSTOM_ID : state.preset;
  const error = validateThresholds(Number(borrowInput), Number(waitInput));

  const handlePreset = (presetId: string) => {
    if (presetId === CUSTOM_ID) {
      onChange(customFromPreset(Number(borrowInput), Number(waitInput)));
      return;
    }
    onChange({ mode: "preset", preset: presetId });
  };

  const handleCustom = (nextBorrow: string, nextWait: string) => {
    setBorrowInput(nextBorrow);
    setWaitInput(nextWait);
    const nextError = validateThresholds(Number(nextBorrow), Number(nextWait));
    if (nextError === null) {
      onChange(customFromPreset(Number(nextBorrow), Number(nextWait)));
    }
  };

  return (
    <section className="rounded-lg border border-line p-4" data-testid="policy-select">
      <h2 className="text-sm font-medium">Политика решения</h2>
      <p className="mt-1 text-xs text-muted">
        Пороги меняют только название вероятности, сама вероятность остаётся прежней.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <label className="text-sm">
          <span className="sr-only">Пресет</span>
          <select
            aria-label="Пресет"
            className="rounded border border-line px-2 py-1 text-sm"
            value={selectedId}
            onChange={(event) => handlePreset(event.target.value)}
          >
            {policies.map((policy) => (
              <option key={policy.id} value={policy.id}>
                {policy.label}
                {policy.is_default ? " (по умолчанию)" : ""}
              </option>
            ))}
            <option value={CUSTOM_ID}>Свои пороги</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="mr-1 text-muted">фиксировать ≥</span>
          <input
            aria-label="Порог фиксировать"
            type="number"
            step="0.01"
            min="0"
            max="1"
            className="w-20 rounded border border-line px-2 py-1 text-sm"
            value={borrowInput}
            onChange={(event) => handleCustom(event.target.value, waitInput)}
          />
        </label>
        <label className="text-sm">
          <span className="mr-1 text-muted">ждать &lt;</span>
          <input
            aria-label="Порог ждать"
            type="number"
            step="0.01"
            min="0"
            max="1"
            className="w-20 rounded border border-line px-2 py-1 text-sm"
            value={waitInput}
            onChange={(event) => handleCustom(borrowInput, event.target.value)}
          />
        </label>
      </div>
      {error ? (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
