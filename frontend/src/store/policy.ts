import type { PolicyParams } from "../api/client";

export type PolicyState =
  | { mode: "preset"; preset: string }
  | { mode: "custom"; pBorrowNow: number; pWait: number };

export const DEFAULT_PRESET = "balanced";

export function readPolicy(search: URLSearchParams, defaultPreset = DEFAULT_PRESET): PolicyState {
  const rawBorrow = search.get("p_borrow_now");
  const rawWait = search.get("p_wait");
  if (rawBorrow !== null && rawWait !== null) {
    const pBorrowNow = Number(rawBorrow);
    const pWait = Number(rawWait);
    if (Number.isFinite(pBorrowNow) && Number.isFinite(pWait)) {
      return { mode: "custom", pBorrowNow, pWait };
    }
  }
  const preset = search.get("preset");
  return { mode: "preset", preset: preset ?? defaultPreset };
}

export function writePolicy(state: PolicyState): URLSearchParams {
  const search = new URLSearchParams();
  if (state.mode === "custom") {
    search.set("p_borrow_now", String(state.pBorrowNow));
    search.set("p_wait", String(state.pWait));
  } else {
    search.set("preset", state.preset);
  }
  return search;
}

export function toPolicyParams(state: PolicyState): PolicyParams {
  if (state.mode === "custom") {
    return { p_borrow_now: state.pBorrowNow, p_wait: state.pWait };
  }
  return { preset: state.preset };
}

/** Проверка порогов: возвращает текст ошибки или null. */
export function validateThresholds(pBorrowNow: number, pWait: number): string | null {
  if (!Number.isFinite(pBorrowNow) || !Number.isFinite(pWait)) {
    return "Пороги должны быть числами";
  }
  if (pBorrowNow > 1 || pBorrowNow < 0 || pWait > 1 || pWait < 0) {
    return "Пороги должны быть в диапазоне 0…1";
  }
  if (pWait >= pBorrowNow) {
    return "Порог «ждать» должен быть меньше порога «фиксировать»";
  }
  return null;
}

/** Подставить в политику пороги дефолтного пресета. */
export function customFromPreset(pBorrowNow: number, pWait: number): PolicyState {
  return { mode: "custom", pBorrowNow, pWait };
}
