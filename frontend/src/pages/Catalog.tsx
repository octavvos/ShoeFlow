import { useQuery } from "@tanstack/react-query";
import { Footprints, Package, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useDebounce } from "@/lib/hooks";
import type { Category, Paginated, ProductModel, Variant } from "@/lib/types";

const SEASON_TONE: Record<string, "sky" | "amber" | "emerald" | "slate"> = {
  winter: "sky",
  summer: "amber",
  demi: "emerald",
  all: "slate",
};

function ModelModal({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["product-models", String(id)],
    enabled: id !== null,
    queryFn: () => api.get<ProductModel>(`/product-models/${id}/`),
  });

  const byColor = useMemo(() => {
    const groups = new Map<string, Variant[]>();
    data?.variants?.forEach((v) => groups.set(v.color_name, [...(groups.get(v.color_name) ?? []), v]));
    return [...groups.entries()];
  }, [data]);

  return (
    <Modal open={id !== null} onClose={onClose} title={data ? `${data.article} — ${data.name}` : "Model"}>
      {isLoading || !data ? (
        <Spinner />
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="brand">{data.category_name}</Badge>
            <Badge>{data.gender_display}</Badge>
            <Badge tone={SEASON_TONE[data.season]}>{data.season_display}</Badge>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              ["Ulgurji", data.wholesale_price],
              ["Diler", data.dealer_price],
              ["Chakana", data.retail_price],
            ].map(([label, price]) => (
              <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                <p className="text-xs text-slate-500">{label}</p>
                <p className="mt-0.5 font-semibold">{formatMoney(price, data.currency)}</p>
              </div>
            ))}
          </div>
          {byColor.map(([color, variants]) => (
            <div key={color}>
              <p className="mb-2 text-sm font-semibold">{color}</p>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                {variants.map((v) => (
                  <div key={v.id} className="rounded-lg border border-slate-200 px-2 py-1.5 text-center dark:border-slate-700">
                    <p className="font-bold">{v.size}</p>
                    <p className="truncate font-mono text-[10px] text-slate-500">{v.barcode}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

export default function CatalogPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const debounced = useDebounce(search);

  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api.get<Category[]>("/categories/") });
  const { data, isLoading } = useQuery({
    queryKey: ["product-models", debounced, category],
    queryFn: () => api.get<Paginated<ProductModel>>("/product-models/", { search: debounced, category, page_size: 60 }),
    placeholderData: (prev) => prev,
  });

  return (
    <>
      <PageHeader title="Katalog" subtitle="Modellar, ranglar va razmerlar" />
      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input className="pl-9" placeholder="Artikul yoki nomi" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Barcha kategoriyalar</option>
          {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data?.results.length ? (
        <Card><EmptyState icon={Package} title="Modellar topilmadi" /></Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.results.map((m) => (
            <button key={m.id} onClick={() => setOpen(m.id)} className="card group overflow-hidden text-left transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="relative flex aspect-[4/3] items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900">
                {m.image ? (
                  <img src={m.image} alt={m.name} className="h-full w-full object-cover" loading="lazy" />
                ) : (
                  <Footprints className="h-14 w-14 text-slate-300 transition group-hover:scale-110 group-hover:text-brand-300 dark:text-slate-700" />
                )}
                <span className="absolute left-3 top-3 rounded-md bg-white/90 px-2 py-0.5 font-mono text-xs font-semibold shadow-sm dark:bg-slate-900/90">
                  {m.article}
                </span>
              </div>
              <div className="p-4">
                <p className="truncate font-semibold">{m.name}</p>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  <Badge>{m.category_name}</Badge>
                  <Badge tone={SEASON_TONE[m.season]}>{m.season_display}</Badge>
                </div>
                <div className="mt-3 flex items-end justify-between">
                  <div>
                    <p className="text-xs text-slate-500">Ulgurji</p>
                    <p className="text-lg font-bold">{formatMoney(m.wholesale_price, m.currency)}</p>
                  </div>
                  <p className="text-xs text-slate-500">{m.gender_display}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
      <ModelModal id={open} onClose={() => setOpen(null)} />
    </>
  );
}
