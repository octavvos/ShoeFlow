// Sahifalar alohida chunk'larga bo'linadi va faqat ochilganda yuklanadi
export const pages = {
  login: () => import("./Login"),
  dashboard: () => import("./Dashboard"),
  orders: () => import("./Orders"),
  orderDetail: () => import("./OrderDetail"),
  customers: () => import("./Customers"),
  customerDetail: () => import("./CustomerDetail"),
  stock: () => import("./Stock"),
  catalog: () => import("./Catalog"),
  finance: () => import("./Finance"),
  notFound: () => import("./NotFound"),
};

/** Kirgandan keyin brauzer bo'sh paytida qolgan sahifalarni oldindan yuklab qo'yadi */
export function preloadPages() {
  const run = () => Object.values(pages).forEach((load) => void load());
  if ("requestIdleCallback" in window) window.requestIdleCallback(run, { timeout: 3000 });
  else setTimeout(run, 1500);
}
