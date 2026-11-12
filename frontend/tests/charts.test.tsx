import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BenchmarkPanel } from "../src/components/BenchmarkPanel";
import { ComparisonPanel } from "../src/components/ComparisonPanel";
import { mergeSpreads, SpreadChart } from "../src/components/SpreadChart";
import { benchmarkFixture, comparisonFixture, seriesFixture } from "./fixtures";

describe("SpreadChart и BenchmarkPanel", () => {
  it("оба получают данные из одного ответа /series", () => {
    render(
      <>
        <SpreadChart spreads={seriesFixture.spreads} />
        <BenchmarkPanel benchmark={benchmarkFixture} rates={seriesFixture.rates} />
      </>,
    );

    expect(screen.getByTestId("legend-rusfar_term_premium")).toBeInTheDocument();
    expect(screen.getByTestId("legend-ofz_curve_premium")).toBeInTheDocument();
    expect(screen.getByText(/точек: 2/)).toBeInTheDocument();

    const benchmark = screen.getByTestId("benchmark-panel");
    expect(benchmark).toHaveTextContent("14.22%");
    expect(benchmark).toHaveTextContent("22 б.п.");
    expect(benchmark).toHaveTextContent(/месяцев в ряду: 2/);
  });

  it("mergeSpreads сводит обе премии по дате", () => {
    const rows = mergeSpreads(seriesFixture.spreads);
    expect(rows).toHaveLength(2);
    expect(rows[1]).toMatchObject({
      date: "2026-11-09",
      rusfar_term_premium: -30,
      ofz_curve_premium: -25,
    });
  });

  it("бенчмарк без данных показывает заглушку", () => {
    render(<BenchmarkPanel benchmark={null} rates={[]} />);
    expect(screen.getByText(/пока недоступны/)).toBeInTheDocument();
  });
});

describe("ComparisonPanel", () => {
  it("показывает устойчивую разницу и лидера", () => {
    render(<ComparisonPanel comparison={comparisonFixture} />);
    expect(screen.getByTestId("comparison-verdict")).toHaveTextContent("разница устойчивая");
    expect(screen.getAllByText("ОФЗ 1 год").length).toBeGreaterThan(0);
    expect(screen.getByTestId("comparison-ofz_curve_premium")).toHaveTextContent("0.140");
  });

  it("показывает шумовую разницу как inconclusive", () => {
    render(<ComparisonPanel comparison={{ ...comparisonFixture, verdict: "inconclusive" }} />);
    expect(screen.getByTestId("comparison-verdict")).toHaveTextContent("разница в пределах шума");
  });
});
