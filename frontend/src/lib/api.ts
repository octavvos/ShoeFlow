// fetch ustidagi yupqa qatlam: JWT qo'shadi, 401 bo'lsa tokenni bir marta yangilaydi,
// backend xatolarini o'qiladigan matnga aylantiradi.

const BASE = "/api/v1";
const TOKENS_KEY = "shoeflow.tokens";

interface Tokens {
  access: string;
  refresh: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: Record<string, unknown> | null,
  ) {
    super(humanize(data) ?? `So'rov bajarilmadi (${status})`);
  }

  get code(): string | undefined {
    return (this.data?.code as string) ?? undefined;
  }
}

/** DRF xatosi → bitta matn: {"detail": "..."} yoki {"field": ["..."]} */
function humanize(data: Record<string, unknown> | null): string | null {
  if (!data) return null;
  if (typeof data.detail === "string") return data.detail;
  const parts = Object.entries(data)
    .filter(([key]) => key !== "code")
    .map(([key, value]) => {
      const text = Array.isArray(value) ? value.join(" ") : String(value);
      return key === "non_field_errors" ? text : `${key}: ${text}`;
    });
  return parts.length ? parts.join("\n") : null;
}

export const tokens = {
  get(): Tokens | null {
    try {
      const raw = localStorage.getItem(TOKENS_KEY);
      return raw ? (JSON.parse(raw) as Tokens) : null;
    } catch {
      return null;
    }
  },
  set(value: Tokens | null) {
    try {
      if (value) localStorage.setItem(TOKENS_KEY, JSON.stringify(value));
      else localStorage.removeItem(TOKENS_KEY);
    } catch {
      /* private rejim — sessiya xotirada qoladi */
    }
  },
};

let refreshing: Promise<boolean> | null = null;

async function refreshAccess(): Promise<boolean> {
  const current = tokens.get();
  if (!current) return false;
  // Bir vaqtda bir nechta so'rov 401 olsa ham token bir marta yangilanadi
  refreshing ??= fetch(`${BASE}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: current.refresh }),
  })
    .then(async (res) => {
      if (!res.ok) return false;
      const data = await res.json();
      tokens.set({ access: data.access, refresh: data.refresh ?? current.refresh });
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query) {
  const url = new URL(BASE + path, window.location.origin);
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.pathname + url.search;
}

export const onUnauthorized = { handler: () => {} };

async function request(path: string, init: RequestInit = {}, query?: Query, retry = true) {
  const headers = new Headers(init.headers);
  const access = tokens.get()?.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const res = await fetch(buildUrl(path, query), { ...init, headers });
  if (res.status === 401 && retry && (await refreshAccess())) {
    return request(path, init, query, false);
  }
  if (res.status === 401) {
    tokens.set(null);
    onUnauthorized.handler();
  }
  if (!res.ok) {
    let data: Record<string, unknown> | null = null;
    try {
      data = await res.json();
    } catch {
      /* javob JSON emas */
    }
    throw new ApiError(res.status, data);
  }
  return res;
}

export const api = {
  async get<T>(path: string, query?: Query): Promise<T> {
    return (await request(path, {}, query)).json();
  },
  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await request(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    return res.status === 204 ? (undefined as T) : res.json();
  },
  async patch<T>(path: string, body: unknown): Promise<T> {
    return (await request(path, { method: "PATCH", body: JSON.stringify(body) })).json();
  },
  async delete<T>(path: string): Promise<T> {
    const res = await request(path, { method: "DELETE" });
    return res.status === 204 ? (undefined as T) : res.json();
  },
  /** Fayl yuklab olish (masalan, akt-sverka Excel) — token bilan */
  async download(path: string, query: Query, filename: string) {
    const blob = await (await request(path, {}, query)).blob();
    const href = URL.createObjectURL(blob);
    const link = Object.assign(document.createElement("a"), { href, download: filename });
    link.click();
    URL.revokeObjectURL(href);
  },
  /** Tokenlarni saqlaydi va backend login javobida qaytargan foydalanuvchini beradi */
  async login<U>(username: string, password: string): Promise<U | undefined> {
    const res = await fetch(`${BASE}/auth/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(res.status, data);
    tokens.set({ access: data.access, refresh: data.refresh });
    return data.user;
  },
};
