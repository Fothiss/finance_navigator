import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SignalCard, VERDICT_LABEL } from "../src/components/SignalCard";
import { makeSignal } from "./fixtures";

describe("SignalCard", () => {
  it.each(["borrow_now", "watch", "wait"] as const)("показывает вердикт %s", (verdict) => {
    render(
      <SignalCard
        signal={makeSignal({ verdict })}
        pBorrowNow={0.65}
        pWait={0.45}
      />,
    );
    const card = screen.getByTestId("signal-rusfar_term_premium");
    expect(within(card).getByText(VERDICT_LABEL[verdict])).toBeInTheDocument();
    expect(within(card).getByTestId("gauge-marker")).toBeInTheDocument();
    expect(within(card).getByTestId("marker-borrow").textContent).toContain("65%");
    expect(within(card).getByTestId("marker-wait").textContent).toContain("45%");
  });

  it("показывает состояние insufficient_evidence без вероятности", () => {
    render(
      <SignalCard
        signal={makeSignal({
          status: "insufficient_evidence",
          verdict: null,
          probability: null,
          headline: null,
          evidence: {
            status: "failed",
            n_observations: 12,
            n_regime: 3,
            reason: "мало наблюдений: 12 < 30",
          },
        })}
        pBorrowNow={0.65}
        pWait={0.45}
      />,
    );
    expect(screen.getByText("Недостаточно данных")).toBeInTheDocument();
    expect(screen.getByText(/мало наблюдений/)).toBeInTheDocument();
    expect(screen.queryByTestId("gauge-marker")).toBeNull();
  });

  it("показывает состояние stale_data", () => {
    render(
      <SignalCard
        signal={makeSignal({ status: "stale_data", verdict: null, probability: null, headline: null })}
        pBorrowNow={0.65}
        pWait={0.45}
      />,
    );
    expect(screen.getByText("Данные устарели")).toBeInTheDocument();
    expect(screen.queryByTestId("gauge-marker")).toBeNull();
  });
});
