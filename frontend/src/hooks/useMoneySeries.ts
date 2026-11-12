import { useEffect, useState } from "react";
import { ApiError, api, type SeriesParams, type SeriesResponse } from "../api/client";

export type SeriesState = {
  data: SeriesResponse | null;
  error: ApiError | null;
  loading: boolean;
};

export function useMoneySeries(params: SeriesParams): SeriesState {
  const [state, setState] = useState<SeriesState>({ data: null, error: null, loading: true });
  const { from, to, bucket } = params;

  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ ...previous, loading: true, error: null }));

    api
      .series({ from, to, bucket }, controller.signal)
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
  }, [from, to, bucket]);

  return state;
}
