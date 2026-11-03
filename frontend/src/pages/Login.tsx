import { BarChart3, Boxes, ShieldCheck, Wallet } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button, ErrorBox, Field, Input } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const DEMO_USERS = [
  { username: "direktor", label: "Direktor" },
  { username: "menejer1", label: "Savdo menejeri" },
  { username: "omborchi", label: "Omborchi" },
  { username: "hisobchi", label: "Hisobchi" },
];
const DEMO_PASSWORD = "Demo-12345";

const FEATURES = [
  { icon: Boxes, text: "Korobka bo'yicha buyurtma va ombor rezervi" },
  { icon: Wallet, text: "To'lovlar, qarzdorlik va akt-sverka" },
  { icon: ShieldCheck, text: "Har bir xodim uchun alohida ruxsatlar" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e?: FormEvent, creds = { username, password }) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(creds.username, creds.password);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-indigo-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-indigo-400/20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 backdrop-blur">
            <BarChart3 className="h-6 w-6" />
          </div>
          <span className="text-xl font-bold">ShoeFlow</span>
        </div>
        <div className="relative max-w-md">
          <h1 className="text-4xl font-bold leading-tight tracking-tight">
            Poyabzal ishlab chiqarishni bitta tizimda boshqaring
          </h1>
          <ul className="mt-8 space-y-4">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-brand-50">
                <span className="rounded-lg bg-white/15 p-2">
                  <Icon className="h-4 w-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-brand-200">Django · DRF · PostgreSQL · React</p>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
              <BarChart3 className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold">ShoeFlow</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight">Tizimga kirish</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Login va parolingizni kiriting</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <Field label="Login">
              <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
            </Field>
            <Field label="Parol">
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>
            <ErrorBox error={error} />
            <Button type="submit" className="w-full" loading={loading}>
              Kirish
            </Button>
          </form>

          <div className="mt-10">
            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
              Demo sifatida kirish
              <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {DEMO_USERS.map((demo) => (
                <button
                  key={demo.username}
                  disabled={loading}
                  onClick={() => submit(undefined, { username: demo.username, password: DEMO_PASSWORD })}
                  className="rounded-xl border border-slate-200 px-3 py-2.5 text-left transition hover:border-brand-300 hover:bg-brand-50/50 disabled:opacity-60 dark:border-slate-800 dark:hover:border-brand-500/40 dark:hover:bg-brand-500/5"
                >
                  <p className="text-sm font-medium">{demo.label}</p>
                  <p className="text-xs text-slate-500">{demo.username}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
