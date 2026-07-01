export type ProductCategory =
  | "meat"
  | "seafood"
  | "produce"
  | "sauce"
  | "beverage"
  | "packaging"
  | "cleaning";

export type ProductCountry = "CO" | "US";
export type ExitReason = "consumption" | "waste";

export interface Product {
  id: number;
  name: string;
  sku: string;
  unit: string;
  category: ProductCategory | string;
  country: ProductCountry | string;
  is_active: boolean;
  current_stock: number;
}

export interface ProductCreateInput {
  name: string;
  sku: string;
  unit: string;
  category: ProductCategory;
  country?: ProductCountry;
  is_active?: boolean;
}

export interface InboundOrderCreateInput {
  ingredient_id: number;
  quantity: number;
  supplier_name: string;
  location_id: number;
}

export interface OutboundOrderCreateInput {
  ingredient_id: number;
  quantity: number;
  reason: ExitReason;
  location_id: number;
}

export interface InboundOrder {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  ingredient_sku: string;
  quantity: number;
  supplier_name: string;
  location_id: number;
  created_at: string;
  user_uuid: string;
}

export interface OutboundOrder {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  ingredient_sku: string;
  quantity: number;
  reason: string;
  location_id: number;
  created_at: string;
  user_uuid: string;
}

export interface OrdersList {
  inbound: InboundOrder[];
  outbound: OutboundOrder[];
}

export type OrderHistoryKind = "inbound" | "outbound";

export interface OrderHistoryRow {
  id: number;
  kind: OrderHistoryKind;
  ingredient_name: string;
  ingredient_sku: string;
  quantity: number;
  unit: string | null;
  created_at: string;
  user_uuid: string;
  supplier_name?: string;
  reason?: string;
  location_id: number;
}
