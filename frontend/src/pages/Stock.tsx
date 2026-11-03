import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { AlertTriangle, Boxes, Search } from "lucide-react";
import { useState } from "react";

import { Card, EmptyState, Input, PageHeader, Pagination, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { useDebounce } from "@/lib/hooks";
import type { Paginated, StockBalance, Warehouse } from "@/lib/types";

const LOW = 10;

function AvailableBadge({ value }: { value: number }) {
  return (
    <span
      className={clsx(
        "inline-flex min-w-[2.5rem] justify-center rounded-lg px-2 py-0.5 text-sm font-semibold tabular-nums",
        value === 0
          ? "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
          : value <= LOW
            ? "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300"
            : "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300",
      )}
    >
      {value}
    </span>
  );
}

export default function StockPage() {
  const [warehouse, setWarehouse] = useState("");
  const [search, setSearch] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [page, setPage] = useState(1);
  const debounced = useDebounce(search);

  const warehouses = useQuery({ queryKey: ["warehouses"], queryFn: () => api.get<Warehouse[]>("/warehouses/") });
  const { data, isLoading } = useQuery({
    queryKey: ["stock", warehouse, debounced, lowOnly, page],
    queryFn: () =>
      api.get<Paginated<StockBalance>>("/stock/", {
        warehouse,
        search: debounced,
        available_lte: lowOnly ? LOW : undefined,
        page,
      }),
    placeholderData: (prev) => prev,
  });

  return (
    <>
      <PageHeader title="Ombor" subtitle="Qoldiq, rezerv va sotish mumkin bo'lgan juftlar" />

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input className="pl-9" placeholder="Artikul, model yoki shtrix-kod" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <Select value={warehouse} onChange={(e) => { setWarehouse(e.target.value); setPage(1); }}>
          <option value="">Barcha omborlar</option>
          {warehouses.data?.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </Select>
        <button
          onClick={() => { setLowOnly(!lowOnly); setPage(1); }}
          className={clsx(
            "inline-flex items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition",
            lowOnly
              ? "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-300"
              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300",
          )}
        >
          <AlertTriangle className="h-4 w-4" /> Kam qolganlar
        </button>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <Spinner />
        ) : !data?.results.length ? (
          <EmptyState icon={Boxes} title="Hech narsa topilmadi" />
        ) : (
          <>
            <table className="hidden w-full md:table">
              <thead className="border-b border-slate-100 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-800/30">
                <tr>
                  <th className="table-head">Mahsulot</th>
                  <th className="table-head">Rang</th>
                  <th className="table-head text-center">Razmer</th>
                  <th className="table-head">Ombor</th>
                  <th className="table-head text-right">Qoldiq</th>
                  <th className="table-head text-right">Rezervda</th>
                  <th className="table-head text-right">Mavjud</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.results.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30">
                    <td className="table-cell">
                      <p className="font-medium">{s.article}</p>
                      <p className="text-xs text-slate-500">{s.model_name}</p>
                    </td>
                    <td className="table-cell">{s.color}</td>
                    <td className="table-cell text-center font-semibold">{s.size}</td>
                    <td className="table-cell text-slate-500">{s.warehouse_name}</td>
                    <td className="table-cell text-right tabular-nums">{formatNumber(s.quantity)}</td>
                    <td className="table-cell text-right tabular-nums text-slate-500">{s.reserved || "—"}</td>
                    <td className="table-cell text-right"><AvailableBadge value={s.available} /></td>
                  </tr>
                ))}
              </tbody>
            </table>

            <ul className="divide-y divide-slate-100 dark:divide-slate-800 md:hidden">
              {data.results.map((s) => (
                <li key={s.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 font-bold dark:bg-slate-800">{s.size}</div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{s.article} · {s.color}</p>
                    <p className="text-xs text-slate-500">
                      {s.warehouse_name} · qoldiq {s.quantity}
                      {s.reserved > 0 && `, rezerv ${s.reserved}`}
                    </p>
                  </div>
                  <AvailableBadge value={s.available} />
                </li>
              ))}
            </ul>
            <Pagination page={page} count={data.count} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
