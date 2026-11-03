// Backend (DRF) javoblarining turlari — serializer'lar bilan bir xil nomlar.

export type Role =
  | "admin"
  | "director"
  | "sales_manager"
  | "production_head"
  | "warehouse"
  | "accountant"
  | "worker";

export type Currency = "UZS" | "USD";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  role_display: string;
  phone: string;
}

export interface Contact {
  id: number;
  customer: number;
  full_name: string;
  position: string;
  phone: string;
  telegram: string;
}

export interface Customer {
  id: number;
  name: string;
  type: "dealer" | "wholesale" | "retail" | "marketplace";
  type_display: string;
  phone: string;
  extra_phone: string;
  region: string;
  region_display: string;
  address: string;
  inn: string;
  currency: Currency;
  credit_limit: string;
  manager: number | null;
  manager_name: string | null;
  tags: string[];
  notes: string;
  is_active: boolean;
  created_at: string;
  contacts?: Contact[];
}

export interface Interaction {
  id: number;
  customer: number;
  type: "call" | "meeting" | "message" | "note";
  body: string;
  occurred_at: string;
  author_name: string | null;
}

export interface Variant {
  id: number;
  product_model: number;
  article: string;
  color: number;
  color_name: string;
  size: number;
  barcode: string;
  is_active: boolean;
}

export interface ProductModel {
  id: number;
  article: string;
  name: string;
  category: number;
  category_name: string;
  gender: string;
  gender_display: string;
  season: string;
  season_display: string;
  description: string;
  image: string | null;
  default_size_run: number | null;
  currency: Currency;
  wholesale_price: string;
  dealer_price: string;
  retail_price: string;
  is_active: boolean;
  variants?: Variant[];
}

export interface Color {
  id: number;
  name: string;
  hex_code: string;
}

export interface Category {
  id: number;
  name: string;
}

export interface SizeRun {
  id: number;
  name: string;
  sizes: Record<string, number>;
  total_pairs: number;
}

export interface Warehouse {
  id: number;
  name: string;
  address: string;
  is_active: boolean;
}

export interface StockBalance {
  id: number;
  warehouse: number;
  warehouse_name: string;
  variant: number;
  article: string;
  model_name: string;
  color: string;
  size: number;
  barcode: string;
  quantity: number;
  reserved: number;
  available: number;
}

export type OrderStatus = "draft" | "confirmed" | "shipped" | "delivered" | "cancelled";

export interface OrderItem {
  id: number;
  variant: number;
  article: string;
  model_name: string;
  color: string;
  size: number;
  quantity: number;
  price: string;
  amount: string;
}

export interface Order {
  id: number;
  number: string;
  customer: number;
  customer_name: string;
  manager: number | null;
  manager_name: string | null;
  warehouse: number;
  warehouse_name: string;
  status: OrderStatus;
  status_display: string;
  price_type: "wholesale" | "dealer" | "retail";
  currency: Currency;
  discount_percent: string;
  total_amount: string;
  total_pairs: number;
  comment: string;
  confirmed_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  items?: OrderItem[];
}

export interface CustomerBalance {
  id: number;
  name: string;
  manager: number | null;
  manager_name: string | null;
  currency: Currency;
  credit_limit: string;
  balance: string;
  open_orders_amount: string;
  available_credit: string;
  last_payment_date: string | null;
}

export interface Payment {
  id: number;
  number: string;
  customer: number;
  customer_name: string;
  order: number | null;
  amount: string;
  currency: Currency;
  method: "cash" | "card" | "bank" | "click" | "payme";
  method_display: string;
  rate: string | null;
  settlement_amount: string;
  paid_at: string;
  comment: string;
  created_by_name: string | null;
  is_cancelled: boolean;
  cancel_reason: string;
}

export interface ReconciliationRow {
  date: string;
  type: string;
  type_display: string;
  reference: string;
  description: string;
  debit: string;
  credit: string;
  balance: string;
}

export interface Reconciliation {
  customer: number;
  customer_name: string;
  currency: Currency;
  date_from: string;
  date_to: string;
  opening_balance: string;
  debit_total: string;
  credit_total: string;
  closing_balance: string;
  rows: ReconciliationRow[];
}
