import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";
import { can, hasRole } from "./lib/roles";
import type { Role } from "./lib/types";
import CatalogPage from "./pages/Catalog";
import CustomerDetailPage from "./pages/CustomerDetail";
import CustomersPage from "./pages/Customers";
import DashboardPage from "./pages/Dashboard";
import FinancePage from "./pages/Finance";
import LoginPage from "./pages/Login";
import NotFoundPage from "./pages/NotFound";
import OrderDetailPage from "./pages/OrderDetail";
import OrdersPage from "./pages/Orders";
import StockPage from "./pages/Stock";

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
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
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
