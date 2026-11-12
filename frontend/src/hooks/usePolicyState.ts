import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { readPolicy, writePolicy, type PolicyState } from "../store/policy";

export type PolicyController = {
  state: PolicyState;
  update: (next: PolicyState) => void;
};

/** Политика решения хранится в URL, чтобы экран был воспроизводим ссылкой. */
export function usePolicyState(defaultPreset?: string): PolicyController {
  const [searchParams, setSearchParams] = useSearchParams();
  const state = readPolicy(searchParams, defaultPreset);

  const update = useCallback(
    (next: PolicyState) => {
      setSearchParams(writePolicy(next), { replace: true });
    },
    [setSearchParams],
  );

  return { state, update };
}
