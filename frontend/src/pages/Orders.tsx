import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronRight, Plus, Search, ShoppingCart } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ORDER_STATUSES, StatusBadge } from "@/components/StatusBadge";
import { Button, Card, EmptyState, ErrorBox, Field, Input, Modal, PageHeader, Pagination, Select, Spinner, Tabs } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatMoney } from "@/lib/format";
import { useDebounce } from "@/lib/hooks";
import { can, hasRole } from "@/lib/roles";
import type { Customer, Order, OrderStatus, Paginated, Warehouse } from "@/lib/types";

type Filter = "all" | OrderStatus;

function NewOrderModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [customer, setCustomer] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [comment, setComment] = useState("");
  const debounced = useDebounce(search);

  const customers = useQuery({
    queryKey: ["customers", "picker", debounced],
    enabled: open,
    queryFn: () => api.get<Paginated<Customer>>("/customers/", { search: debounced, is_active: true, page_size: 50 }),
  });
  const warehouses = useQuery({
    queryKey: ["warehouses"],
    enabled: open,
    queryFn: () => api.get<Warehouse[]>("/warehouses/", { is_active: true }),
  });

  const create = useMutation({
    mutationFn: (warehouseId: string) =>
      api.post<Order>("/orders/", { customer: Number(customer), warehouse: Number(warehouseId), comment }),
    onSuccess: (order) => navigate(`/orders/${order.id}`),
  });

  const selectedWarehouse = warehouse || (warehouses.data?.[0] ? String(warehouses.data[0].id) : "");

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Yangi buyurtma"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor</Button>
          <Button
            loading={create.isPending}
            disabled={!customer || !selectedWarehouse}
            onClick={() => create.mutate(selectedWarehouse)}
          >
            Yaratish
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Mijoz">
          <Input placeholder="Nomi yoki telefon bo'yicha qidirish..." value={search} onChange={(e) => setSearch(e.target.value)} className="mb-2" />
          <Select value={customer} onChange={(e) => setCustomer(e.target.value)} size={5} className="h-auto">
            {customers.data?.results.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} — {c.region_display}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Jo'natish ombori">
          <Select value={selectedWarehouse} onChange={(e) => setWarehouse(e.target.value)}>
            {warehouses.data?.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </Select>
        </Field>
        <Field label="Izoh">
          <Input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Ixtiyoriy" />
        </Field>
        <ErrorBox error={create.error} />
      </div>
    </Modal>
  );
}

export default function OrdersPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const debounced = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ["orders", filter, debounced, page],
    queryFn: () =>
      api.get<Paginated<Order>>("/orders/", {
        status: filter === "all" ? undefined : filter,
        search: debounced,
        page,
      }),
    placeholderData: (prev) => prev,
  });

  return (
    <>
      <PageHeader
        title="Buyurtmalar"
        subtitle="Qoralamadan yetkazilgunga qadar"
        actions={hasRole(user, can.editOrders) && <Button icon={Plus} onClick={() => setCreating(true)}>Yangi buyurtma</Button>}
      />

      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Tabs<Filter>
          value={filter}
          onChange={(v) => {
            setFilter(v);
            setPage(1);
          }}
          items={[{ value: "all", label: "Barchasi" }, ...ORDER_STATUSES]}
        />
        <div className="relative lg:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            className="pl-9"
            placeholder="Mijoz bo'yicha qidirish"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <Spinner />
        ) : !data?.results.length ? (
          <EmptyState icon={ShoppingCart} title="Buyurtmalar topilmadi" text="Filtr yoki qidiruvni o'zgartirib ko'ring." />
        ) : (
          <>
            {/* Kompyuter: jadval */}
            <table className="hidden w-full md:table">
              <thead className="border-b border-slate-100 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-800/30">
                <tr>
                  <th className="table-head">Raqam</th>
                  <th className="table-head">Mijoz</th>
                  <th className="table-head">Sana</th>
                  <th className="table-head text-right">Juft</th>
                  <th className="table-head text-right">Summa</th>
                  <th className="table-head">Holat</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.results.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => navigate(`/orders/${o.id}`)}
                    className="group cursor-pointer transition hover:bg-slate-50 dark:hover:bg-slate-800/40"
                  >
                    <td className="table-cell font-mono text-xs text-slate-500 dark:text-slate-400">{o.number}</td>
                    <td className="table-cell">
                      <p className="font-medium group-hover:text-brand-600">{o.customer_name}</p>
                      <p className="text-xs text-slate-500">{o.manager_name ?? "—"}</p>
                    </td>
                    <td className="table-cell text-slate-500">{formatDate(o.created_at)}</td>
                    <td className="table-cell text-right tabular-nums">{o.total_pairs}</td>
                    <td className="table-cell text-right font-semibold tabular-nums">{formatMoney(o.total_amount, o.currency)}</td>
                    <td className="table-cell"><StatusBadge status={o.status} /></td>
                    <td className="table-cell text-right text-slate-300 group-hover:text-brand-500">
                      <ChevronRight className="ml-auto h-4 w-4" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Telefon: kartochkalar */}
            <ul className="divide-y divide-slate-100 dark:divide-slate-800 md:hidden">
              {data.results.map((o) => (
                <li key={o.id}>
                  <Link to={`/orders/${o.id}`} className="block px-4 py-3.5 active:bg-slate-50 dark:active:bg-slate-800/50">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{o.customer_name}</p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {o.number} · {formatDate(o.created_at)}
                        </p>
                      </div>
                      <StatusBadge status={o.status} />
                    </div>
                    <div className="mt-2 flex items-center justify-between text-sm">
                      <span className="text-slate-500">{o.total_pairs} juft</span>
                      <span className="font-semibold">{formatMoney(o.total_amount, o.currency)}</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
            <Pagination page={page} count={data.count} onChange={setPage} />
          </>
        )}
      </Card>

      <NewOrderModal open={creating} onClose={() => setCreating(false)} />
    </>
  );
}
