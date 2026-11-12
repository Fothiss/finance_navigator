import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useMoneySeries } from "../src/hooks/useMoneySeries";
import { useMoneySignals } from "../src/hooks/useMoneySignals";
import { makeSignals, seriesFixture } from "./fixtures";

function mockFetchOnce(status: number, body: unknown) {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useMoneySignals", () => {
  it("возвращает данные при успешном ответе", async () => {
    mockFetchOnce(200, makeSignals());
    const { result } = renderHook(() => useMoneySignals({ preset: "balanced" }));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
    expect(result.current.data?.signals).toHaveLength(2);
  });

  it("пробрасывает 422 как ApiError с текстом problem+json", async () => {
    mockFetchOnce(422, {
      type: "urn:finance-navigator:problem:validation",
      title: "Ошибка валидации запроса",
      status: 422,
      detail: "неизвестные параметры запроса: z_threshold",
    });
    const { result } = renderHook(() => useMoneySignals({ p_borrow_now: 0.7, p_wait: 0.45 }));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.status).toBe(422);
    expect(result.current.error?.problem.detail).toContain("z_threshold");
    expect(result.current.data).toBeNull();
  });

  it("пробрасывает 503 как ApiError", async () => {
    mockFetchOnce(503, {
      type: "urn:finance-navigator:problem:upstream",
      title: "Источник данных недоступен",
      status: 503,
      detail: "ЦБ недоступен",
    });
    const { result } = renderHook(() => useMoneySignals({ preset: "balanced" }));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.status).toBe(503);
    expect(result.current.error?.problem.title).toBe("Источник данных недоступен");
  });
});

describe("useMoneySeries", () => {
  it("запрашивает серию и отдаёт данные", async () => {
    const fetchMock = mockFetchOnce(200, seriesFixture);
    const { result } = renderHook(() =>
      useMoneySeries({ from: "2025-01-01", to: "2026-01-01", bucket: "week" }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.spreads).toHaveLength(2);
    const calledUrl = String(fetchMock.mock.calls[0]?.[0]);
    expect(calledUrl).toContain("bucket=week");
    expect(calledUrl).toContain("from=2025-01-01");
  });
});
