import clsx from "clsx";
import {
  BarChart3,
  Boxes,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Package,
  ShoppingCart,
  Sun,
  Users,
  Wallet,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";
import { useTheme } from "@/lib/hooks";
import { can, hasRole } from "@/lib/roles";
import type { Role } from "@/lib/types";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  allowed?: (role: Role) => boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Bosh sahifa", icon: LayoutDashboard },
  { to: "/orders", label: "Buyurtmalar", icon: ShoppingCart, allowed: can.viewOrders },
  { to: "/customers", label: "Mijozlar", icon: Users, allowed: can.viewCustomers },
  { to: "/stock", label: "Ombor", icon: Boxes, allowed: can.viewStock },
  { to: "/catalog", label: "Katalog", icon: Package },
  { to: "/finance", label: "Moliya", icon: Wallet, allowed: can.viewFinance },
];

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md shadow-brand-600/30">
        <BarChart3 className="h-5 w-5" />
      </div>
      <div className="leading-tight">
        <p className="font-bold tracking-tight">ShoeFlow</p>
        <p className="text-[11px] text-slate-500 dark:text-slate-400">Poyabzal CRM</p>
      </div>
    </div>
  );
}

function NavLinks({ items, onNavigate }: { items: NavItem[]; onNavigate?: () => void }) {
  return (
    <nav className="space-y-1">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          onClick={onNavigate}
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
              isActive
                ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100",
            )
          }
        >
          <Icon className="h-5 w-5" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

function UserCard() {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();
  if (!user) return null;
  const name = user.full_name || user.username;
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700 dark:bg-brand-500/20 dark:text-brand-200">
        {initials(name)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{name}</p>
        <p className="truncate text-xs text-slate-500 dark:text-slate-400">{user.role_display}</p>
      </div>
      <button onClick={toggle} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800" aria-label="Tema">
        {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
      <button onClick={logout} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-rose-600 dark:hover:bg-slate-800" aria-label="Chiqish">
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

export function AppLayout() {
  const { user } = useAuth();
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  const items = NAV.filter((item) => !item.allowed || hasRole(user, item.allowed));
  // Telefonda pastki panelda 4 ta asosiy bo'lim, qolgani "Menyu"da
  const bottomItems = items.slice(0, 4);

  useEffect(() => setDrawer(false), [location.pathname]);

  return (
    <div className="min-h-screen">
      {/* Kompyuter: yon panel */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-slate-200 bg-white px-4 py-5 dark:border-slate-800 dark:bg-slate-900 lg:flex">
        <div className="px-2">
          <Logo />
        </div>
        <div className="mt-8 flex-1">
          <NavLinks items={items} />
        </div>
        <UserCard />
      </aside>

      {/* Telefon: yuqori panel */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur-lg dark:border-slate-800 dark:bg-slate-900/80 lg:hidden">
        <Logo />
        <button onClick={() => setDrawer(true)} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" aria-label="Menyu">
          <Menu className="h-5 w-5" />
        </button>
      </header>

      <main className="px-4 pb-28 pt-6 sm:px-6 lg:ml-64 lg:px-10 lg:pb-10 lg:pt-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>

      {/* Telefon: pastki navigatsiya */}
      <nav className="pb-safe fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-slate-200 bg-white/90 pt-1.5 backdrop-blur-lg dark:border-slate-800 dark:bg-slate-900/90 lg:hidden">
        {bottomItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex flex-col items-center gap-0.5 py-1 text-[11px] font-medium",
                isActive ? "text-brand-600 dark:text-brand-400" : "text-slate-500 dark:text-slate-400",
              )
            }
          >
            <Icon className="h-5 w-5" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
        <button onClick={() => setDrawer(true)} className="flex flex-col items-center gap-0.5 py-1 text-[11px] font-medium text-slate-500 dark:text-slate-400">
          <Menu className="h-5 w-5" />
          Menyu
        </button>
      </nav>

      {/* Telefon: to'liq menyu */}
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setDrawer(false)} />
          <div className="pb-safe absolute inset-y-0 right-0 flex w-72 max-w-[85vw] flex-col bg-white px-4 py-5 shadow-xl dark:bg-slate-900">
            <div className="flex items-center justify-between px-2">
              <Logo />
              <button onClick={() => setDrawer(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Yopish">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-8 flex-1">
              <NavLinks items={items} onNavigate={() => setDrawer(false)} />
            </div>
            <UserCard />
          </div>
        </div>
      )}
    </div>
  );
}
