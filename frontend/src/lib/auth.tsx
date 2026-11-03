import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";

import { api, onUnauthorized, tokens } from "./api";
import type { User } from "./types";

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const hasToken = Boolean(tokens.get());

  const { data: user, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<User>("/users/me/"),
    enabled: hasToken,
    retry: false,
    staleTime: Infinity,
  });

  const logout = useCallback(() => {
    tokens.set(null);
    queryClient.clear();
    queryClient.setQueryData(["me"], null);
  }, [queryClient]);

  useEffect(() => {
    onUnauthorized.handler = logout;
  }, [logout]);

  const login = useCallback(
    async (username: string, password: string) => {
      await api.login(username, password);
      const me = await api.get<User>("/users/me/");
      queryClient.setQueryData(["me"], me);
    },
    [queryClient],
  );

  const value = useMemo(
    () => ({ user: user ?? null, loading: hasToken && isLoading, login, logout }),
    [user, hasToken, isLoading, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth AuthProvider ichida ishlatilishi kerak");
  return ctx;
}
