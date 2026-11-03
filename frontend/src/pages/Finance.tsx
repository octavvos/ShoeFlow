import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { Ban, Plus, Receipt, Search, Wallet } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, Modal, PageHeader, Pagination, Select, Spinner, Tabs } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PAYMENT_METHODS } from "@/lib/choices";
import { formatDate, formatMoney, isoDate } from "@/lib/format";
import { useDebounce } from "@/lib/hooks";
import { can, hasRole } from "@/lib/roles";
import type { Customer, CustomerBalance, Paginated, Payment } from "@/lib/types";

type Tab = "debtors" | "all" | "payments";

function BalancesList({ debtorsOnly }: { debtorsOnly: boolean }) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const debounced = useDebounce(search);
  const { data, isLoading } = useQuery({
    queryKey: ["balances", debtorsOnly, debounced, page],
    queryFn: () =>
      api.get<Paginated<CustomerBalance>>("/finance/balances/", {
        debtors: debtorsOnly || undefined,
        search: debounced,
        page,
      }),
    placeholderData: (prev) => prev,
  });

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-100 p-4 dark:border-slate-800">
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input className="pl-9" placeholder="Mijoz bo'yicha qidirish" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>
      </div>
      {isLoading ? (
        <Spinner />
      ) : !data?.results.length ? (
        <EmptyState icon={Wallet} title={debtorsOnly ? "Qarzdorlar yo'q 🎉" : "Mijozlar topilmadi"} />
      ) : (
        <>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.results.map((b) => {
              const debt = Number(b.balance);
              const limit = Number(b.credit_limit);
              const over = Number(b.available_credit) < 0;
              const used = limit > 0 ? Math.min(100, ((debt + Number(b.open_orders_amount)) / limit) * 100) : debt > 0 ? 100 : 0;
              return (
                <li key={b.id}>
                  <Link to={`/customers/${b.id}`} className="grid gap-3 px-4 py-4 transition hover:bg-slate-50 dark:hover:bg-slate-800/40 sm:grid-cols-[1fr_200px_140px] sm:items-center sm:px-5">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{b.name}</p>
                      <p className="text-xs text-slate-500">
                        {b.manager_name ?? "—"} · oxirgi to'lov {formatDate(b.last_payment_date)}
                      </p>
                    </div>
                    <div>
                      <div className="mb-1 flex justify-between text-xs text-slate-500">
                        <span>Limit</span>
                        <span>{formatMoney(limit, b.currency)}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                        <div className={clsx("h-full rounded-full", over ? "bg-rose-500" : used > 75 ? "bg-amber-500" : "bg-brand-500")} style={{ width: `${Math.max(0, used)}%` }} />
                      </div>
                    </div>
                    <div className="flex items-center justify-between gap-2 sm:block sm:text-right">
                      <p className={clsx("font-semibold tabular-nums", debt > 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400")}>
                        {formatMoney(debt, b.currency)}
                      </p>
                      {over && <Badge tone="rose">Limitdan oshgan</Badge>}
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
          <Pagination page={page} count={data.count} onChange={setPage} />
        </>
      )}
    </Card>
  );
}

function NewPaymentModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search);
  const [form, setForm] = useState({ customer: "", amount: "", currency: "USD", method: "cash", paid_at: isoDate(new Date()), comment: "" });
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  const customers = useQuery({
    queryKey: ["customers", "picker", debounced],
    enabled: open,
    queryFn: () => api.get<Paginated<Customer>>("/customers/", { search: debounced, page_size: 50 }),
  });

  const create = useMutation({
    mutationFn: () => api.post<Payment>("/finance/payments/", { ...form, customer: Number(form.customer) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setForm({ ...form, customer: "", amount: "", comment: "" });
      onClose();
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="To'lov qabul qilish"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor</Button>
          <Button type="submit" form="new-payment" loading={create.isPending} disabled={!form.customer || !form.amount}>Saqlash</Button>
        </>
      }
    >
      <form id="new-payment" onSubmit={submit} className="space-y-4">
        <Field label="Mijoz">
          <Input placeholder="Qidirish..." value={search} onChange={(e) => setSearch(e.target.value)} className="mb-2" />
          <Select value={form.customer} onChange={set("customer")} size={4} className="h-auto">
            {customers.data?.results.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.currency})</option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-[1fr_110px] gap-3">
          <Field label="Summa"><Input type="number" min="0.01" step="0.01" value={form.amount} onChange={set("amount")} required /></Field>
          <Field label="Valyuta">
            <Select value={form.currency} onChange={set("currency")}>
              <option value="USD">USD</option>
              <option value="UZS">So'm</option>
            </Select>
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="To'lov usuli">
            <Select value={form.method} onChange={set("method")}>
              {PAYMENT_METHODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
          </Field>
          <Field label="Sana"><Input type="date" value={form.paid_at} onChange={set("paid_at")} /></Field>
        </div>
        <Field label="Izoh"><Input value={form.comment} onChange={set("comment")} /></Field>
        <p className="text-xs text-slate-500">To'lov mijoz hisobidan boshqa valyutada bo'lsa, to'lov sanasidagi kurs bo'yicha hisoblanadi.</p>
        <ErrorBox error={create.error} />
      </form>
    </Modal>
  );
}

function PaymentsList({ editable }: { editable: boolean }) {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["payments", page],
    queryFn: () => api.get<Paginated<Payment>>("/finance/payments/", { page }),
    placeholderData: (prev) => prev,
  });
  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => api.post(`/finance/payments/${id}/cancel/`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
    },
  });

  return (
    <Card className="overflow-hidden">
      <ErrorBox error={cancel.error} />
      {isLoading ? (
        <Spinner />
      ) : !data?.results.length ? (
        <EmptyState icon={Receipt} title="To'lovlar yo'q" />
      ) : (
        <>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.results.map((p) => (
              <li key={p.id} className={clsx("flex items-center gap-3 px-4 py-3.5 sm:px-5", p.is_cancelled && "opacity-60")}>
                <div className={clsx("rounded-xl p-2.5", p.is_cancelled ? "bg-slate-100 text-slate-400 dark:bg-slate-800" : "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-300")}>
                  <Receipt className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{p.customer_name}</p>
                  <p className="text-xs text-slate-500">
                    {p.number} · {formatDate(p.paid_at)} · {p.method_display}
                    {p.is_cancelled && ` · bekor: ${p.cancel_reason}`}
                  </p>
                </div>
                <div className="text-right">
                  <p className={clsx("font-semibold tabular-nums", p.is_cancelled && "line-through")}>{formatMoney(p.amount, p.currency)}</p>
                  {p.rate && <p className="text-xs text-slate-500">kurs {Number(p.rate).toLocaleString("ru-RU")}</p>}
                </div>
                {editable && !p.is_cancelled && (
                  <button
                    onClick={() => {
                      const reason = window.prompt("Bekor qilish sababi:");
                      if (reason) cancel.mutate({ id: p.id, reason });
                    }}
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10"
                    aria-label="Bekor qilish"
                  >
                    <Ban className="h-4 w-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
          <Pagination page={page} count={data.count} onChange={setPage} />
        </>
      )}
    </Card>
  );
}

export default function FinancePage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("debtors");
  const [paying, setPaying] = useState(false);
  const editable = hasRole(user, can.editFinance);

  return (
    <>
      <PageHeader
        title="Moliya"
        subtitle="Qarzdorlik, kredit limitlari va to'lovlar"
        actions={editable && <Button icon={Plus} onClick={() => setPaying(true)}>To'lov qabul qilish</Button>}
      />
      <div className="mb-4">
        <Tabs<Tab>
          value={tab}
          onChange={setTab}
          items={[
            { value: "debtors", label: "Qarzdorlar" },
            { value: "all", label: "Barcha balanslar" },
            { value: "payments", label: "To'lovlar" },
          ]}
        />
      </div>
      {tab === "payments" ? <PaymentsList editable={editable} /> : <BalancesList key={tab} debtorsOnly={tab === "debtors"} />}
      <NewPaymentModal open={paying} onClose={() => setPaying(false)} />
    </>
  );
}
