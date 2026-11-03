import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";
import { can, hasRole } from "./lib/roles";
import type { Role } from "./lib/types";
import { pages } from "./pages";

const LoginPage = lazy(pages.login);
const DashboardPage = lazy(pages.dashboard);
const OrdersPage = lazy(pages.orders);
const OrderDetailPage = lazy(pages.orderDetail);
const CustomersPage = lazy(pages.customers);
const CustomerDetailPage = lazy(pages.customerDetail);
const StockPage = lazy(pages.stock);
const CatalogPage = lazy(pages.catalog);
const FinancePage = lazy(pages.finance);
const NotFoundPage = lazy(pages.notFound);

function Guard({ allowed, children }: { allowed?: (role: Role) => boolean; children: ReactNode }) {
  const { user } = useAuth();
  if (allowed && !hasRole(user, allowed)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) return <Spinner className="min-h-screen" />;
  if (!user) {
    return (
      <Suspense fallback={<Spinner className="min-h-screen" />}>
        <Routes>
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </Suspense>
    );
  }

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="orders" element={<Guard allowed={can.viewOrders}><OrdersPage /></Guard>} />
        <Route path="orders/:id" element={<Guard allowed={can.viewOrders}><OrderDetailPage /></Guard>} />
        <Route path="customers" element={<Guard allowed={can.viewCustomers}><CustomersPage /></Guard>} />
        <Route path="customers/:id" element={<Guard allowed={can.viewCustomers}><CustomerDetailPage /></Guard>} />
        <Route path="stock" element={<Guard allowed={can.viewStock}><StockPage /></Guard>} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="finance" element={<Guard allowed={can.viewFinance}><FinancePage /></Guard>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
