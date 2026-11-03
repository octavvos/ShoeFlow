import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import {
  ArrowLeft,
  CheckCircle2,
  Minus,
  PackagePlus,
  PackageX,
  Plus,
  Trash2,
  Truck,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, Modal, Select, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatMoney } from "@/lib/format";
import { can, hasRole } from "@/lib/roles";
import type { Order, OrderItem, Paginated, ProductModel, SizeRun } from "@/lib/types";

interface Shortage {
  article: string;
  color: string;
  size: number;
  requested: number;
  available: number;
}

/** Backend biznes xatolari (ombor yetmasligi, kredit limiti) uchun tushunarli ko'rinish */
function ActionError({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) return <ErrorBox error={error} />;
  const shortages = error.data?.shortages as Shortage[] | undefined;
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
      <p className="font-medium">{error.message}</p>
      {shortages && (
        <ul className="mt-2 space-y-1">
          {shortages.map((s) => (
            <li key={`${s.article}-${s.color}-${s.size}`} className="flex justify-between gap-4">
              <span>{s.article} · {s.color} · {s.size}-razmer</span>
              <span className="tabular-nums">kerak {s.requested}, bor {s.available}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AddBoxesModal({ order, open, onClose }: { order: Order; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [modelId, setModelId] = useState("");
  const [colorId, setColorId] = useState("");
  const [sizeRunId, setSizeRunId] = useState("");
  const [count, setCount] = useState(1);

  const models = useQuery({
    queryKey: ["product-models", "picker"],
    enabled: open,
    queryFn: () => api.get<Paginated<ProductModel>>("/product-models/", { is_active: true, page_size: 100 }),
  });
  const model = useQuery({
    queryKey: ["product-models", modelId],
    enabled: Boolean(modelId),
    queryFn: () => api.get<ProductModel>(`/product-models/${modelId}/`),
  });
  const sizeRuns = useQuery({
    queryKey: ["size-runs"],
    enabled: open,
    queryFn: () => api.get<SizeRun[]>("/size-runs/"),
  });

  const colors = useMemo(() => {
    const map = new Map<number, string>();
    model.data?.variants?.forEach((v) => map.set(v.color, v.color_name));
    return [...map.entries()];
  }, [model.data]);

  const sizeRun = sizeRuns.data?.find((r) => String(r.id) === (sizeRunId || String(model.data?.default_size_run ?? "")));

  const add = useMutation({
    mutationFn: () =>
      api.post<Order>(`/orders/${order.id}/boxes/`, {
        product_model: Number(modelId),
        color: Number(colorId || colors[0]?.[0]),
        size_run: sizeRun?.id,
        count,
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["order", String(order.id)], data);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      onClose();
    },
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Korobka qo'shish"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor</Button>
          <Button loading={add.isPending} disabled={!modelId || !sizeRun} onClick={() => add.mutate()}>
            Qo'shish
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Model">
          <Select value={modelId} onChange={(e) => { setModelId(e.target.value); setColorId(""); setSizeRunId(""); }}>
            <option value="">Tanlang...</option>
            {models.data?.results.map((m) => (
              <option key={m.id} value={m.id}>{m.article} — {m.name}</option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Rang">
            <Select value={colorId} onChange={(e) => setColorId(e.target.value)} disabled={!colors.length}>
              {colors.map(([id, name]) => (
                <option key={id} value={id}>{name}</option>
              ))}
            </Select>
          </Field>
          <Field label="Korobka soni">
            <Input type="number" min={1} value={count} onChange={(e) => setCount(Math.max(1, Number(e.target.value)))} />
          </Field>
        </div>
        <Field label="Razmer qatori">
          <Select value={sizeRun ? String(sizeRun.id) : ""} onChange={(e) => setSizeRunId(e.target.value)}>
            <option value="">Tanlang...</option>
            {sizeRuns.data?.map((r) => (
              <option key={r.id} value={r.id}>{r.name} ({r.total_pairs} juft)</option>
            ))}
          </Select>
        </Field>
        {sizeRun && (
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
            <p className="mb-2 text-xs font-medium text-slate-500">Buyurtmaga qo'shiladi:</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(sizeRun.sizes).map(([size, qty]) => (
                <span key={size} className="rounded-lg bg-white px-2 py-1 text-xs shadow-sm dark:bg-slate-900">
                  <b>{size}</b> × {qty * count}
                </span>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-500">Jami: {sizeRun.total_pairs * count} juft</p>
          </div>
        )}
        <ActionError error={add.error} />
      </div>
    </Modal>
  );
}

function ItemRow({ item, order, editable }: { item: OrderItem; order: Order; editable: boolean }) {
  const queryClient = useQueryClient();
  const update = useMutation({
    mutationFn: (quantity: number) =>
      quantity > 0
        ? api.patch<Order>(`/orders/${order.id}/items/${item.id}/`, { quantity })
        : api.delete<Order>(`/orders/${order.id}/items/${item.id}/`),
    onSuccess: (data) => queryClient.setQueryData(["order", String(order.id)], data),
  });

  return (
    <li className="flex items-center gap-3 px-4 py-3 sm:px-5">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-sm font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
        {item.size}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{item.article} · {item.model_name}</p>
        <p className="text-xs text-slate-500">{item.color} · {formatMoney(item.price, order.currency)} / juft</p>
      </div>
      {editable ? (
        <div className={clsx("flex items-center gap-1", update.isPending && "opacity-50")}>
          <button onClick={() => update.mutate(item.quantity - 1)} className="rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Kamaytirish">
            {item.quantity === 1 ? <Trash2 className="h-4 w-4 text-rose-500" /> : <Minus className="h-4 w-4" />}
          </button>
          <span className="w-8 text-center text-sm font-semibold tabular-nums">{item.quantity}</span>
          <button onClick={() => update.mutate(item.quantity + 1)} className="rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Ko'paytirish">
            <Plus className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <span className="text-sm text-slate-500 tabular-nums">× {item.quantity}</span>
      )}
      <span className="hidden w-28 text-right text-sm font-semibold tabular-nums sm:block">{formatMoney(item.amount, order.currency)}</span>
    </li>
  );
}

const STEPS = [
  { key: "created_at", label: "Yaratildi" },
  { key: "confirmed_at", label: "Tasdiqlandi" },
  { key: "shipped_at", label: "Jo'natildi" },
  { key: "delivered_at", label: "Yetkazildi" },
] as const;

export default function OrderDetailPage() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [boxes, setBoxes] = useState(false);

  const { data: order, isLoading, error } = useQuery({
    queryKey: ["order", id],
    queryFn: () => api.get<Order>(`/orders/${id}/`),
  });

  const action = useMutation({
    mutationFn: (name: "confirm" | "ship" | "deliver" | "cancel") => api.post<Order>(`/orders/${id}/${name}/`),
    onSuccess: (data) => {
      queryClient.setQueryData(["order", id], data);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  if (isLoading) return <Spinner />;
  if (error || !order) return <ErrorBox error={error ?? "Buyurtma topilmadi"} />;

  const canEdit = hasRole(user, can.editOrders);
  const canShip = hasRole(user, can.shipOrders);
  const draft = order.status === "draft";
  const items = order.items ?? [];
  const subtotal = items.reduce((sum, i) => sum + Number(i.amount), 0);

  return (
    <div className="space-y-6">
      <div>
        <Link to="/orders" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
          <ArrowLeft className="h-4 w-4" /> Buyurtmalar
        </Link>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{order.number}</h1>
            <StatusBadge status={order.status} />
          </div>
          <div className="flex flex-wrap gap-2">
            {draft && canEdit && (
              <>
                <Button variant="secondary" icon={PackagePlus} onClick={() => setBoxes(true)}>Korobka qo'shish</Button>
                <Button icon={CheckCircle2} loading={action.isPending && action.variables === "confirm"} disabled={!items.length} onClick={() => action.mutate("confirm")}>
                  Tasdiqlash
                </Button>
              </>
            )}
            {order.status === "confirmed" && canShip && (
              <Button icon={Truck} loading={action.isPending && action.variables === "ship"} onClick={() => action.mutate("ship")}>Jo'natish</Button>
            )}
            {order.status === "shipped" && canShip && (
              <Button variant="success" icon={CheckCircle2} loading={action.isPending && action.variables === "deliver"} onClick={() => action.mutate("deliver")}>
                Yetkazildi
              </Button>
            )}
            {(draft || order.status === "confirmed") && canEdit && (
              <Button
                variant="ghost"
                icon={XCircle}
                loading={action.isPending && action.variables === "cancel"}
                onClick={() => window.confirm("Buyurtmani bekor qilasizmi?") && action.mutate("cancel")}
              >
                Bekor qilish
              </Button>
            )}
          </div>
        </div>
      </div>

      {action.error && <ActionError error={action.error} />}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="overflow-hidden lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:px-5">
            <h2 className="font-semibold">Mahsulotlar</h2>
            <Badge>{order.total_pairs} juft</Badge>
          </div>
          {items.length ? (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((item) => (
                <ItemRow key={item.id} item={item} order={order} editable={draft && canEdit} />
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={PackageX}
              title="Buyurtma bo'sh"
              text="Model, rang va razmer qatorini tanlab, korobkalab qo'shing."
              action={draft && canEdit && <Button icon={PackagePlus} onClick={() => setBoxes(true)}>Korobka qo'shish</Button>}
            />
          )}
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <h2 className="mb-4 font-semibold">Hisob</h2>
            <dl className="space-y-2.5 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Mahsulotlar</dt><dd className="tabular-nums">{formatMoney(subtotal, order.currency)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Chegirma</dt><dd className="tabular-nums">{Number(order.discount_percent)}%</dd></div>
              <div className="flex justify-between border-t border-slate-100 pt-2.5 text-base font-semibold dark:border-slate-800">
                <dt>Jami</dt><dd className="tabular-nums">{formatMoney(order.total_amount, order.currency)}</dd>
              </div>
            </dl>
          </Card>

          <Card className="p-5">
            <h2 className="mb-4 font-semibold">Ma'lumotlar</h2>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-xs text-slate-500">Mijoz</dt>
                <dd>
                  {hasRole(user, can.viewCustomers) ? (
                    <Link to={`/customers/${order.customer}`} className="font-medium text-brand-600 hover:underline dark:text-brand-400">{order.customer_name}</Link>
                  ) : (
                    order.customer_name
                  )}
                </dd>
              </div>
              <div><dt className="text-xs text-slate-500">Menejer</dt><dd>{order.manager_name ?? "—"}</dd></div>
              <div><dt className="text-xs text-slate-500">Ombor</dt><dd>{order.warehouse_name}</dd></div>
              <div>
                <dt className="text-xs text-slate-500">Narx turi</dt>
                <dd>{{ wholesale: "Ulgurji", dealer: "Diler", retail: "Chakana" }[order.price_type]}</dd>
              </div>
              {order.comment && <div><dt className="text-xs text-slate-500">Izoh</dt><dd>{order.comment}</dd></div>}
            </dl>
          </Card>

          <Card className="p-5">
            <h2 className="mb-4 font-semibold">Tarix</h2>
            {order.status === "cancelled" ? (
              <p className="text-sm text-rose-600 dark:text-rose-400">Bekor qilingan: {formatDateTime(order.cancelled_at)}</p>
            ) : (
              <ol className="relative space-y-4 border-l border-slate-200 pl-5 dark:border-slate-700">
                {STEPS.map((step) => {
                  const at = order[step.key];
                  return (
                    <li key={step.key} className="relative">
                      <span className={clsx("absolute -left-[26px] top-1 h-3 w-3 rounded-full ring-4 ring-white dark:ring-slate-900", at ? "bg-brand-500" : "bg-slate-200 dark:bg-slate-700")} />
                      <p className={clsx("text-sm font-medium", !at && "text-slate-400")}>{step.label}</p>
                      <p className="text-xs text-slate-500">{at ? formatDateTime(at) : "—"}</p>
                    </li>
                  );
                })}
              </ol>
            )}
          </Card>
        </div>
      </div>

      <AddBoxesModal order={order} open={boxes} onClose={() => setBoxes(false)} />
    </div>
  );
}
