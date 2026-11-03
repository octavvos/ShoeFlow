import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Boxes, Clock, ShoppingCart, Truck, Wallet } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Card, Spinner, StatCard } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatMoney, formatNumber } from "@/lib/format";
import { can, hasRole } from "@/lib/roles";
import type { CustomerBalance, Order, OrderStatus, Paginated, StockBalance } from "@/lib/types";

const LOW_STOCK = 10;

function greeting() {
  const h = new Date().getHours();
  if (h < 6) return "Xayrli tun";
  if (h < 12) return "Xayrli tong";
  if (h < 18) return "Xayrli kun";
  return "Xayrli kech";
}

function Panel({ title, to, children }: { title: string; to: string; children: ReactNode }) {
  return (
    <Card className="flex flex-col">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800">
        <h2 className="font-semibold">{title}</h2>
        <Link to={to} className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400">
          Barchasi <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
      <div className="flex-1">{children}</div>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const showOrders = hasRole(user, can.viewOrders);
  const showFinance = hasRole(user, can.viewFinance);
  const showStock = hasRole(user, can.viewStock);

  const orders = useQuery({
    queryKey: ["dashboard", "orders"],
    enabled: showOrders,
    queryFn: async () => {
      const [stats, recent] = await Promise.all([
        api.get<Record<OrderStatus, number>>("/orders/stats/"),
        api.get<Paginated<Order>>("/orders/", { page_size: 6 }),
      ]);
      return { ...stats, recent: recent.results };
    },
  });

  const debtors = useQuery({
    queryKey: ["dashboard", "debtors"],
    enabled: showFinance,
    queryFn: () => api.get<Paginated<CustomerBalance>>("/finance/balances/", { debtors: true, page_size: 5 }),
  });

  const lowStock = useQuery({
    queryKey: ["dashboard", "low-stock"],
    enabled: showStock,
    queryFn: () =>
      api.get<Paginated<StockBalance>>("/stock/", { available_lte: LOW_STOCK, ordering: "available_qty", page_size: 6 }),
  });

  const topDebtor = debtors.data?.results[0];
  const firstName = user?.first_name || user?.username;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          {greeting()}, {firstName} 👋
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Bugungi holat bir qarashda</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {showOrders && (
          <>
            <StatCard label="Qoralama buyurtmalar" value={orders.data?.draft ?? "—"} hint="Tasdiqlashni kutmoqda" icon={Clock} tone="amber" />
            <StatCard label="Jo'natishga tayyor" value={orders.data?.confirmed ?? "—"} hint="Ombordan rezerv qilingan" icon={ShoppingCart} />
            <StatCard label="Yo'lda" value={orders.data?.shipped ?? "—"} hint="Jo'natilgan, yetkazilmagan" icon={Truck} tone="emerald" />
          </>
        )}
        {showFinance && (
          <StatCard
            label="Qarzdorlar"
            value={debtors.data ? formatNumber(debtors.data.count) : "—"}
            hint={topDebtor ? `Eng kattasi: ${formatMoney(topDebtor.balance, topDebtor.currency)}` : undefined}
            icon={Wallet}
            tone="rose"
          />
        )}
        {!showOrders && showStock && (
          <StatCard label="Kam qolgan mahsulotlar" value={lowStock.data?.count ?? "—"} hint={`Mavjud ≤ ${LOW_STOCK} juft`} icon={AlertTriangle} tone="amber" />
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        {showOrders && (
          <div className="xl:col-span-2">
            <Panel title="So'nggi buyurtmalar" to="/orders">
              {orders.isLoading ? (
                <Spinner />
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {orders.data?.recent.map((o) => (
                    <li key={o.id}>
                      <Link to={`/orders/${o.id}`} className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-slate-50 dark:hover:bg-slate-800/50">
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium">{o.customer_name}</p>
                          <p className="text-xs text-slate-500">
                            {o.number} · {formatDate(o.created_at)} · {o.total_pairs} juft
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">{formatMoney(o.total_amount, o.currency)}</p>
                          <StatusBadge status={o.status} />
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        )}

        <div className="space-y-6">
          {showFinance && (
            <Panel title="Eng katta qarzdorlar" to="/finance">
              {debtors.isLoading ? (
                <Spinner />
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {debtors.data?.results.map((d) => {
                    const over = Number(d.available_credit) < 0;
                    return (
                      <li key={d.id} className="flex items-center justify-between gap-3 px-5 py-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{d.name}</p>
                          <p className={over ? "text-xs text-rose-600 dark:text-rose-400" : "text-xs text-slate-500"}>
                            {over ? "Limitdan oshgan" : `Limit: ${formatMoney(d.credit_limit, d.currency)}`}
                          </p>
                        </div>
                        <p className="whitespace-nowrap text-sm font-semibold">{formatMoney(d.balance, d.currency)}</p>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Panel>
          )}

          {showStock && (
            <Panel title="Kam qolgan mahsulotlar" to="/stock">
              {lowStock.isLoading ? (
                <Spinner />
              ) : lowStock.data?.results.length ? (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {lowStock.data.results.map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-3 px-5 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {s.article} · {s.color} · {s.size}
                        </p>
                        <p className="text-xs text-slate-500">{s.warehouse_name}</p>
                      </div>
                      <span className="rounded-lg bg-amber-50 px-2 py-1 text-sm font-semibold text-amber-700 dark:bg-amber-500/10 dark:text-amber-300">
                        {s.available}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="flex items-center gap-2 px-5 py-6 text-sm text-slate-500">
                  <Boxes className="h-4 w-4" /> Hamma mahsulot yetarli
                </p>
              )}
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
