/**
 * SYNAPSE Auth Context — manages current user state globally.
 * Reads /api/v1/auth/me on mount; exposes login/logout helpers.
 */
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { apiClient } from "../api/client";

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: "admin" | "user" | "viewer";
  is_active: boolean;
  created_at: string;
}

interface AuthCtx {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  confirm_password: string;
  full_name?: string;
}

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const res = await apiClient.get<AuthUser>("/auth/me");
      setUser(res.data);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiClient.post<{ user: AuthUser }>("/auth/login", { email, password });
    setUser(res.data.user);
  };

  const register = async (data: RegisterData) => {
    const res = await apiClient.post<{ user: AuthUser }>("/auth/register", data);
    setUser(res.data.user);
  };

  const logout = async () => {
    await apiClient.post("/auth/logout").catch(() => {});
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
