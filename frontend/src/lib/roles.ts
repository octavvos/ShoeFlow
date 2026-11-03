// Backend'dagi RoleBasedPermission bilan bir xil qoidalar — UI faqat ruxsat berilgan narsani ko'rsatadi.
// Haqiqiy tekshiruv baribir backend'da.
import type { Role, User } from "./types";

const MANAGEMENT: Role[] = ["admin", "director"];

export const can = {
  viewCustomers: (r: Role) => [...MANAGEMENT, "sales_manager", "accountant"].includes(r),
  editCustomers: (r: Role) => [...MANAGEMENT, "sales_manager"].includes(r),
  viewStock: (r: Role) => r !== "worker",
  viewOrders: (r: Role) => [...MANAGEMENT, "sales_manager", "warehouse", "accountant"].includes(r),
  editOrders: (r: Role) => [...MANAGEMENT, "sales_manager"].includes(r),
  shipOrders: (r: Role) => [...MANAGEMENT, "warehouse"].includes(r),
  viewFinance: (r: Role) => [...MANAGEMENT, "accountant", "sales_manager"].includes(r),
  editFinance: (r: Role) => [...MANAGEMENT, "accountant"].includes(r),
};

export function hasRole(user: User | null, check: (r: Role) => boolean) {
  return Boolean(user) && (user!.role === "admin" || check(user!.role));
}
