"use client";

import { useEffect, useRef } from "react";

import { track } from "@/lib/telemetry";

const IDLE_MS = 120_000;

type FormType = "InboundOrder" | "OutboundOrder";

interface UseOrderFormAbandonmentOptions {
  formType: FormType;
  productId: number | null;
  locationId: number;
  fieldsCompleted: string[];
  active: boolean;
}

export function useOrderFormAbandonment({
  formType,
  productId,
  locationId,
  fieldsCompleted,
  active,
}: UseOrderFormAbandonmentOptions): void {
  const emittedRef = useRef(false);

  useEffect(() => {
    emittedRef.current = false;
  }, [formType, productId]);

  useEffect(() => {
    if (!active || productId == null || fieldsCompleted.length === 0) {
      return;
    }

    const timer = window.setTimeout(() => {
      if (emittedRef.current) {
        return;
      }
      emittedRef.current = true;
      track("order_form_abandoned", {
        form_type: formType,
        product_id: productId,
        location_id: locationId,
        fields_completed: fieldsCompleted,
      });
    }, IDLE_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [active, fieldsCompleted, formType, productId, locationId]);
}
