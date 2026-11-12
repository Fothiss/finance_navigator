import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { PolicySelect } from "../src/components/PolicySelect";
import { usePolicyState } from "../src/hooks/usePolicyState";
import { POLICIES_STUB } from "./stubs";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="search">{location.search}</output>;
}

function Harness() {
  const { state, update } = usePolicyState();
  return (
    <>
      <PolicySelect
        policies={POLICIES_STUB.policies}
        state={state}
        onChange={update}
        defaultThresholds={{ pBorrowNow: 0.65, pWait: 0.45 }}
      />
      <LocationProbe />
    </>
  );
}

function renderHarness() {
  return render(
    <MemoryRouter initialEntries={["/money"]}>
      <Harness />
    </MemoryRouter>,
  );
}

describe("PolicySelect", () => {
  it("смена порога обновляет query-строку", () => {
    renderHarness();
    const input = screen.getByLabelText("Порог фиксировать");
    fireEvent.change(input, { target: { value: "0.8" } });

    expect(screen.getByTestId("search").textContent).toContain("p_borrow_now=0.8");
    expect(screen.getByTestId("search").textContent).toContain("p_wait=0.45");
  });

  it("невалидные пороги блокируют запрос и показывают ошибку", () => {
    renderHarness();
    const borrow = screen.getByLabelText("Порог фиксировать");
    fireEvent.change(borrow, { target: { value: "0.3" } });

    expect(screen.getByRole("alert")).toHaveTextContent("должен быть меньше");
    expect(screen.getByTestId("search").textContent).toBe("");
  });

  it("выбор пресета пишет его в query-строку", () => {
    renderHarness();
    fireEvent.change(screen.getByLabelText("Пресет"), { target: { value: "careful" } });
    expect(screen.getByTestId("search").textContent).toContain("preset=careful");
  });
});
