import type { PoliciesResponse } from "../src/api/client";

export const POLICIES_STUB: PoliciesResponse = {
  policies: [
    { id: "careful", label: "Осторожная", p_borrow_now: 0.8, p_wait: 0.55, is_default: false },
    { id: "balanced", label: "Сбалансированная", p_borrow_now: 0.65, p_wait: 0.45, is_default: true },
    { id: "aggressive", label: "Агрессивная", p_borrow_now: 0.5, p_wait: 0.3, is_default: false },
  ],
  default: { p_borrow_now: 0.65, p_wait: 0.45 },
};
