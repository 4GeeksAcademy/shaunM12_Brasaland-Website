"use client";

import { useCallback, useMemo, useState } from "react";
import { AsyncState } from "@/types/api";

interface UseApiStateResult<TData> {
  state: AsyncState;
  data: TData | null;
  error: string;
  isLoading: boolean;
  setData: (value: TData | ((current: TData | null) => TData)) => void;
  reset: () => void;
  execute: <TResult = TData>(
    operation: () => Promise<TResult>,
    options?: {
      onSuccess?: (result: TResult) => void;
      mapResult?: (result: TResult) => TData;
    },
  ) => Promise<TResult>;
}

export function useApiState<TData>(initialData: TData | null = null): UseApiStateResult<TData> {
  const [state, setState] = useState<AsyncState>("idle");
  const [data, setDataState] = useState<TData | null>(initialData);
  const [error, setError] = useState("");

  const setData = useCallback((value: TData | ((current: TData | null) => TData)) => {
    setDataState((current) =>
      typeof value === "function"
        ? (value as (state: TData | null) => TData)(current)
        : value,
    );
    setState("success");
    setError("");
  }, []);

  const reset = useCallback(() => {
    setState("idle");
    setError("");
    setDataState(initialData);
  }, [initialData]);

  const execute = useCallback(
    async <TResult,>(
      operation: () => Promise<TResult>,
      options?: {
        onSuccess?: (result: TResult) => void;
        mapResult?: (result: TResult) => TData;
      },
    ): Promise<TResult> => {
      setState("loading");
      setError("");

      try {
        const result = await operation();

        if (options?.mapResult) {
          setDataState(options.mapResult(result));
        } else {
          setDataState(result as unknown as TData);
        }

        if (options?.onSuccess) {
          options.onSuccess(result);
        }

        setState("success");
        return result;
      } catch (requestError) {
        setState("error");
        setError(
          requestError instanceof Error ? requestError.message : "Request failed.",
        );
        throw requestError;
      }
    },
    [],
  );

  const isLoading = useMemo(() => state === "loading", [state]);

  return {
    state,
    data,
    error,
    isLoading,
    setData,
    reset,
    execute,
  };
}
