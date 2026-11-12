import { useEffect, useState } from "react";
import { ApiError, api, type MoneySignals, type PolicyParams } from "../api/client";

export type SignalsState = {
  data: MoneySignals | null;
  error: ApiError | null;
  loading: boolean;
};

export function useMoneySignals(policy: PolicyParams): SignalsState {
  const [state, setState] = useState<SignalsState>({ data: null, error: null, loading: true });
  const { preset, p_borrow_now, p_wait } = policy;

  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ ...previous, loading: true, error: null }));

    api
      .signals({ preset, p_borrow_now, p_wait }, controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const apiError =
          error instanceof ApiError
            ? error
            : new ApiError(0, { detail: error instanceof Error ? error.message : String(error) });
        setState({ data: null, error: apiError, loading: false });
      });

    return () => controller.abort();
  }, [preset, p_borrow_now, p_wait]);

  return state;
}
