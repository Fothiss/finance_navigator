import { useEffect, useState } from "react";
import { ApiError, api, type PoliciesResponse } from "../api/client";

export type PoliciesState = {
  data: PoliciesResponse | null;
  error: ApiError | null;
  loading: boolean;
};

export function usePolicies(): PoliciesState {
  const [state, setState] = useState<PoliciesState>({ data: null, error: null, loading: true });

  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ ...previous, loading: true, error: null }));

    api
      .policies(controller.signal)
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
  }, []);

  return state;
}
