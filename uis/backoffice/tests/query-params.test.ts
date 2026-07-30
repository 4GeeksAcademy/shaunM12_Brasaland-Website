import { describe, expect, it } from "vitest";

import {
  buildInventoryOrderPrefillQuery,
  buildInventoryProductsApiQuery,
  buildReportingWeekStartApiQuery,
  inventoryOrderPrefillHref,
  readInventoryPrefill,
} from "@/lib/query-params";

describe("query parameter conventions", () => {
  it("reads camelCase inventory prefill from browser search params", () => {
    const params = new URLSearchParams("productId=7&locationId=3");
    expect(readInventoryPrefill(params)).toEqual({
      productId: "7",
      locationId: "3",
    });
  });

  it("builds camelCase inventory order prefill queries", () => {
    expect(buildInventoryOrderPrefillQuery(7, 3)).toBe("productId=7&locationId=3");
    expect(buildInventoryOrderPrefillQuery(7)).toBe("productId=7");
  });

  it("builds inventory order prefill hrefs", () => {
    expect(inventoryOrderPrefillHref("inbound", 7, 3)).toBe(
      "/inventory/orders/inbound?productId=7&locationId=3",
    );
    expect(inventoryOrderPrefillHref("outbound", 12)).toBe(
      "/inventory/orders/outbound?productId=12",
    );
  });

  it("maps camelCase inventory options to snake_case API query params", () => {
    expect(
      buildInventoryProductsApiQuery({ locationId: 3, includeInactive: true }),
    ).toBe("?location_id=3&include_inactive=true");
    expect(buildInventoryProductsApiQuery()).toBe("");
  });

  it("maps reporting weekStart to snake_case week_start API param", () => {
    expect(buildReportingWeekStartApiQuery("2026-07-21")).toBe(
      "?week_start=2026-07-21",
    );
    expect(buildReportingWeekStartApiQuery("")).toBe("");
  });
});
