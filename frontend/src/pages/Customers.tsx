import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin, Phone, Plus, Search, Users } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Badge, Button, Card, EmptyState, ErrorBox, Field, Input, Modal, PageHeader, Pagination, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CUSTOMER_TYPES, REGIONS } from "@/lib/choices";
import { formatMoney, initials } from "@/lib/format";
import { useDebounce } from "@/lib/hooks";
import { can, hasRole } from "@/lib/roles";
import type { Customer, Paginated } from "@/lib/types";

const EMPTY = { name: "", type: "wholesale", phone: "+998", region: "tashkent_city", inn: "", currency: "USD", credit_limit: "0", address: "" };

function NewCustomerModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(EMPTY);
  const set = (key: keyof typeof EMPTY) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  const create = useMutation({
    mutationFn: () => api.post<Customer>("/customers/", form),
    onSuccess: (customer) => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setForm(EMPTY);
      navigate(`/customers/${customer.id}`);
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
      title="Yangi mijoz"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Bekor</Button>
          <Button type="submit" form="new-customer" loading={create.isPending}>Saqlash</Button>
        </>
      }
    >
      <form id="new-customer" onSubmit={submit} className="space-y-4">
        <Field label="Nomi"><Input value={form.name} onChange={set("name")} required /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Turi">
            <Select value={form.type} onChange={set("type")}>
              {CUSTOMER_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
          </Field>
          <Field label="Telefon"><Input value={form.phone} onChange={set("phone")} inputMode="tel" required /></Field>
          <Field label="Viloyat">
            <Select value={form.region} onChange={set("region")}>
              {REGIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
          </Field>
          <Field label="STIR (INN)" hint="9 ta raqam, ixtiyoriy"><Input value={form.inn} onChange={set("inn")} inputMode="numeric" /></Field>
          <Field label="Hisob valyutasi">
            <Select value={form.currency} onChange={set("currency")}>
              <option value="USD">USD</option>
              <option value="UZS">So'm</option>
            </Select>
          </Field>
          <Field label="Kredit limiti"><Input type="number" min={0} value={form.credit_limit} onChange={set("credit_limit")} /></Field>
        </div>
        <Field label="Manzil"><Input value={form.address} onChange={set("address")} /></Field>
        <ErrorBox error={create.error} />
      </form>
    </Modal>
  );
}

export default function CustomersPage() {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState("");
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const debounced = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ["customers", debounced, region, type, page],
    queryFn: () => api.get<Paginated<Customer>>("/customers/", { search: debounced, region, type, page }),
    placeholderData: (prev) => prev,
  });

  const resetPage = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(1);
  };

  return (
    <>
      <PageHeader
        title="Mijozlar"
        subtitle={data ? `Jami ${data.count} ta mijoz` : undefined}
        actions={hasRole(user, can.editCustomers) && <Button icon={Plus} onClick={() => setCreating(true)}>Yangi mijoz</Button>}
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input className="pl-9" placeholder="Nomi, telefon yoki INN" value={search} onChange={(e) => resetPage(setSearch)(e.target.value)} />
        </div>
        <Select value={region} onChange={(e) => resetPage(setRegion)(e.target.value)}>
          <option value="">Barcha viloyatlar</option>
          {REGIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select>
        <Select value={type} onChange={(e) => resetPage(setType)(e.target.value)}>
          <option value="">Barcha turlar</option>
          {CUSTOMER_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select>
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data?.results.length ? (
        <Card><EmptyState icon={Users} title="Mijozlar topilmadi" text="Qidiruv yoki filtrlarni o'zgartirib ko'ring." /></Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.results.map((c) => (
              <Link key={c.id} to={`/customers/${c.id}`} className="card group p-5 transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md dark:hover:border-brand-500/30">
                <div className="flex items-start gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-100 to-brand-200 text-sm font-bold text-brand-700 dark:from-brand-500/20 dark:to-brand-500/10 dark:text-brand-200">
                    {initials(c.name)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold group-hover:text-brand-600 dark:group-hover:text-brand-400">{c.name}</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <Badge tone={c.type === "dealer" ? "brand" : "slate"}>{c.type_display}</Badge>
                      {!c.is_active && <Badge tone="rose">Nofaol</Badge>}
                      {c.tags.map((t) => <Badge key={t} tone="amber">#{t}</Badge>)}
                    </div>
                  </div>
                </div>
                <div className="mt-4 space-y-1.5 text-sm text-slate-500 dark:text-slate-400">
                  <p className="flex items-center gap-2"><MapPin className="h-4 w-4" /> {c.region_display}</p>
                  <p className="flex items-center gap-2"><Phone className="h-4 w-4" /> {c.phone}</p>
                </div>
                <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
                  <span className="text-slate-500">{c.manager_name ?? "Menejer yo'q"}</span>
                  <span className="font-medium">Limit: {formatMoney(c.credit_limit, c.currency)}</span>
                </div>
              </Link>
            ))}
          </div>
          <Card className="mt-4">
            <Pagination page={page} count={data.count} onChange={setPage} />
          </Card>
        </>
      )}

      <NewCustomerModal open={creating} onClose={() => setCreating(false)} />
    </>
  );
}
