"use client";

import { useEffect, useRef } from "react";

import { track } from "@/lib/telemetry";

const IDLE_MS = 120_000;

type FormType = "SupplyOrder" | "ConsumptionOrder";

interface UseOrderFormAbandonmentOptions {
  formType: FormType;
  ingredientId: number | null;
  locationId: number;
  fieldsCompleted: string[];
  active: boolean;
}

export function useOrderFormAbandonment({
  formType,
  ingredientId,
  locationId,
  fieldsCompleted,
  active,
}: UseOrderFormAbandonmentOptions): void {
  const emittedRef = useRef(false);

  useEffect(() => {
    emittedRef.current = false;
  }, [formType, ingredientId]);

  useEffect(() => {
    if (!active || ingredientId == null || fieldsCompleted.length === 0) {
      return;
    }

    const timer = window.setTimeout(() => {
      if (emittedRef.current) {
        return;
      }
      emittedRef.current = true;
      track("order_form_abandoned", {
        form_type: formType,
        ingredient_id: ingredientId,
        location_id: locationId,
        fields_completed: fieldsCompleted,
      });
    }, IDLE_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [active, fieldsCompleted, formType, ingredientId, locationId]);
}
