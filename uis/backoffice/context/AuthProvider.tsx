"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from "@/lib/auth-api";
import { AuthStatus, AuthUser } from "@/types/auth";

interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const hydrate = useCallback(async () => {
    const current = await fetchCurrentUser();
    setUser(current);
    setStatus(current ? "authenticated" : "unauthenticated");
  }, []);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  const login = useCallback(
    async (email: string, password: string) => {
      await loginRequest(email, password);
      await hydrate();
    },
    [hydrate],
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      await registerRequest(email, password, name);
      await hydrate();
    },
    [hydrate],
  );

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const refreshUser = useCallback(async () => {
    const current = await fetchCurrentUser();
    setUser(current);
    setStatus(current ? "authenticated" : "unauthenticated");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, register, logout, refreshUser }),
    [user, status, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
