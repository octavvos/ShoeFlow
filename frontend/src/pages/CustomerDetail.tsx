import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowLeft, Download, FileSpreadsheet, MessageSquare, Phone, Send, ShoppingCart, User } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Badge, Button, Card, EmptyState, ErrorBox, Input, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { INTERACTION_TYPES } from "@/lib/choices";
import { formatDate, formatDateTime, formatMoney, isoDate } from "@/lib/format";
import { can, hasRole } from "@/lib/roles";
import type { Customer, CustomerBalance, Interaction, Order, Paginated, Reconciliation } from "@/lib/types";

function BalanceCard({ customerId }: { customerId: string }) {
  const { data } = useQuery({
    queryKey: ["balance", customerId],
    queryFn: () => api.get<CustomerBalance>(`/finance/balances/${customerId}/`),
  });
  if (!data) return null;
  const debt = Number(data.balance);
  const available = Number(data.available_credit);
  const limit = Number(data.credit_limit);
  const used = limit > 0 ? Math.min(100, Math.max(0, ((limit - available) / limit) * 100)) : debt > 0 ? 100 : 0;

  return (
    <Card className="p-5">
      <h2 className="font-semibold">Hisob-kitob</h2>
      <p className={clsx("mt-3 text-3xl font-bold tracking-tight", debt > 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400")}>
        {formatMoney(Math.abs(debt), data.currency)}
      </p>
      <p className="text-sm text-slate-500">{debt > 0 ? "Mijoz qarzi" : debt < 0 ? "Oldindan to'lov" : "Qarz yo'q"}</p>

      <div className="mt-5">
        <div className="mb-1.5 flex justify-between text-xs text-slate-500">
          <span>Kredit limiti</span>
          <span>{formatMoney(limit, data.currency)}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <div className={clsx("h-full rounded-full", used >= 100 ? "bg-rose-500" : used > 75 ? "bg-amber-500" : "bg-brand-500")} style={{ width: `${used}%` }} />
        </div>
      </div>
      <dl className="mt-4 space-y-2 text-sm">
        <div className="flex justify-between"><dt className="text-slate-500">Ochiq buyurtmalar</dt><dd className="tabular-nums">{formatMoney(data.open_orders_amount, data.currency)}</dd></div>
        <div className="flex justify-between">
          <dt className="text-slate-500">Bo'sh limit</dt>
          <dd className={clsx("tabular-nums font-medium", available < 0 && "text-rose-600 dark:text-rose-400")}>{formatMoney(available, data.currency)}</dd>
        </div>
        <div className="flex justify-between"><dt className="text-slate-500">Oxirgi to'lov</dt><dd>{formatDate(data.last_payment_date)}</dd></div>
      </dl>
    </Card>
  );
}

function ReconciliationCard({ customer }: { customer: Customer }) {
  const today = new Date();
  const [from, setFrom] = useState(isoDate(new Date(today.getFullYear(), today.getMonth() - 3, 1)));
  const [to, setTo] = useState(isoDate(today));
  const [downloading, setDownloading] = useState(false);

  const { data, isFetching, error } = useQuery({
    queryKey: ["reconciliation", customer.id, from, to],
    queryFn: () => api.get<Reconciliation>(`/finance/balances/${customer.id}/reconciliation/`, { date_from: from, date_to: to }),
  });

  async function download() {
    setDownloading(true);
    try {
      await api.download(`/finance/balances/${customer.id}/reconciliation/`, { date_from: from, date_to: to, export: "xlsx" }, `akt-sverka-${customer.id}-${to}.xlsx`);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-slate-100 p-5 dark:border-slate-800 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 font-semibold"><FileSpreadsheet className="h-5 w-5 text-brand-500" /> Akt-sverka</h2>
          <p className="text-sm text-slate-500">O'zaro hisob-kitoblarni solishtirish</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="w-auto" />
          <span className="text-slate-400">—</span>
          <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="w-auto" />
          <Button variant="secondary" icon={Download} loading={downloading} onClick={download}>Excel</Button>
        </div>
      </div>
      <ErrorBox error={error} />
      {isFetching && !data ? (
        <Spinner />
      ) : data ? (
        <div className={clsx("overflow-x-auto", isFetching && "opacity-60")}>
          <table className="w-full min-w-[560px] text-sm">
            <thead className="bg-slate-50/50 dark:bg-slate-800/30">
              <tr>
                <th className="table-head">Sana</th>
                <th className="table-head">Hujjat</th>
                <th className="table-head text-right">Debet</th>
                <th className="table-head text-right">Kredit</th>
                <th className="table-head text-right">Qoldiq</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              <tr className="bg-slate-50/30 font-medium dark:bg-slate-800/20">
                <td className="table-cell" colSpan={4}>Boshlang'ich qoldiq</td>
                <td className="table-cell text-right tabular-nums">{formatMoney(data.opening_balance)}</td>
              </tr>
              {data.rows.map((r, i) => (
                <tr key={i}>
                  <td className="table-cell whitespace-nowrap text-slate-500">{formatDate(r.date)}</td>
                  <td className="table-cell">
                    <p>{r.type_display}</p>
                    <p className="text-xs text-slate-500">{r.reference}</p>
                  </td>
                  <td className="table-cell text-right tabular-nums">{Number(r.debit) ? formatMoney(r.debit) : ""}</td>
                  <td className="table-cell text-right tabular-nums text-emerald-600 dark:text-emerald-400">{Number(r.credit) ? formatMoney(r.credit) : ""}</td>
                  <td className="table-cell text-right tabular-nums">{formatMoney(r.balance)}</td>
                </tr>
              ))}
              <tr className="bg-slate-50/30 font-semibold dark:bg-slate-800/20">
                <td className="table-cell" colSpan={2}>Yakuniy qoldiq ({data.currency})</td>
                <td className="table-cell text-right tabular-nums">{formatMoney(data.debit_total)}</td>
                <td className="table-cell text-right tabular-nums">{formatMoney(data.credit_total)}</td>
                <td className="table-cell text-right tabular-nums">{formatMoney(data.closing_balance)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : null}
    </Card>
  );
}

function InteractionsCard({ customerId, editable }: { customerId: string; editable: boolean }) {
  const queryClient = useQueryClient();
  const [type, setType] = useState("call");
  const [body, setBody] = useState("");
  const { data } = useQuery({
    queryKey: ["interactions", customerId],
    queryFn: () => api.get<Paginated<Interaction>>("/interactions/", { customer: customerId, page_size: 20 }),
  });
  const add = useMutation({
    mutationFn: () => api.post("/interactions/", { customer: Number(customerId), type, body }),
    onSuccess: () => {
      setBody("");
      queryClient.invalidateQueries({ queryKey: ["interactions", customerId] });
    },
  });

  return (
    <Card className="p-5">
      <h2 className="mb-4 flex items-center gap-2 font-semibold"><MessageSquare className="h-5 w-5 text-brand-500" /> Muloqotlar</h2>
      {editable && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (body.trim()) add.mutate();
          }}
          className="mb-5 flex flex-col gap-2 sm:flex-row"
        >
          <Select value={type} onChange={(e) => setType(e.target.value)} className="sm:w-40">
            {INTERACTION_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
          <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Nima haqida gaplashildi?" />
          <Button type="submit" icon={Send} loading={add.isPending} aria-label="Qo'shish" />
        </form>
      )}
      {data?.results.length ? (
        <ol className="space-y-4">
          {data.results.map((it) => (
            <li key={it.id} className="flex gap-3">
              <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand-400" />
              <div className="min-w-0">
                <p className="text-sm">{it.body}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {INTERACTION_TYPES.find(([v]) => v === it.type)?.[1]} · {it.author_name ?? "—"} · {formatDateTime(it.occurred_at)}
                </p>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-sm text-slate-500">Hali muloqotlar yo'q</p>
      )}
    </Card>
  );
}

export default function CustomerDetailPage() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const { data: customer, isLoading, error } = useQuery({
    queryKey: ["customer", id],
    queryFn: () => api.get<Customer>(`/customers/${id}/`),
  });
  const orders = useQuery({
    queryKey: ["orders", "customer", id],
    enabled: hasRole(user, can.viewOrders),
    queryFn: () => api.get<Paginated<Order>>("/orders/", { customer: id, page_size: 8 }),
  });

  if (isLoading) return <Spinner />;
  if (error || !customer) return <ErrorBox error={error ?? "Mijoz topilmadi"} />;
  const showFinance = hasRole(user, can.viewFinance);

  return (
    <div className="space-y-6">
      <div>
        <Link to="/customers" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
          <ArrowLeft className="h-4 w-4" /> Mijozlar
        </Link>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{customer.name}</h1>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge tone="brand">{customer.type_display}</Badge>
              <Badge>{customer.region_display}</Badge>
              {customer.tags.map((t) => <Badge key={t} tone="amber">#{t}</Badge>)}
            </div>
          </div>
          <a href={`tel:${customer.phone}`}>
            <Button variant="secondary" icon={Phone}>{customer.phone}</Button>
          </a>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {showFinance && <ReconciliationCard customer={customer} />}

          {orders.data && (
            <Card className="overflow-hidden">
              <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
                <h2 className="flex items-center gap-2 font-semibold"><ShoppingCart className="h-5 w-5 text-brand-500" /> Buyurtmalar</h2>
              </div>
              {orders.data.results.length ? (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {orders.data.results.map((o) => (
                    <li key={o.id}>
                      <Link to={`/orders/${o.id}`} className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/40">
                        <div>
                          <p className="text-sm font-medium">{o.number}</p>
                          <p className="text-xs text-slate-500">{formatDate(o.created_at)} · {o.total_pairs} juft</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold tabular-nums">{formatMoney(o.total_amount, o.currency)}</span>
                          <StatusBadge status={o.status} />
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState icon={ShoppingCart} title="Buyurtmalar yo'q" />
              )}
            </Card>
          )}

          <InteractionsCard customerId={id} editable={hasRole(user, can.editCustomers)} />
        </div>

        <div className="space-y-6">
          {showFinance && <BalanceCard customerId={id} />}
          <Card className="p-5">
            <h2 className="mb-4 font-semibold">Ma'lumotlar</h2>
            <dl className="space-y-3 text-sm">
              <div><dt className="text-xs text-slate-500">Menejer</dt><dd>{customer.manager_name ?? "—"}</dd></div>
              <div><dt className="text-xs text-slate-500">STIR (INN)</dt><dd>{customer.inn || "—"}</dd></div>
              <div><dt className="text-xs text-slate-500">Manzil</dt><dd>{customer.address || "—"}</dd></div>
              <div><dt className="text-xs text-slate-500">Hisob valyutasi</dt><dd>{customer.currency}</dd></div>
              {customer.notes && <div><dt className="text-xs text-slate-500">Izoh</dt><dd>{customer.notes}</dd></div>}
            </dl>
          </Card>
          <Card className="p-5">
            <h2 className="mb-4 font-semibold">Kontakt shaxslar</h2>
            {customer.contacts?.length ? (
              <ul className="space-y-3">
                {customer.contacts.map((c) => (
                  <li key={c.id} className="flex items-center gap-3">
                    <div className="rounded-full bg-slate-100 p-2 dark:bg-slate-800"><User className="h-4 w-4 text-slate-500" /></div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{c.full_name}</p>
                      <p className="text-xs text-slate-500">{c.position || "—"}</p>
                    </div>
                    <a href={`tel:${c.phone}`} className="text-xs font-medium text-brand-600 dark:text-brand-400">{c.phone}</a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">Kontaktlar yo'q</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
