/**
 * Auth context for the Sentinel frontend.
 *
 * Provides:
 * - Current user state (null = logged out)
 * - login() — calls the API client, stores token + user
 * - logout() — clears token + user
 * - Persisted across page refreshes via localStorage
 */

"use client";

import React, { createContext, useContext, useState } from "react";
import {
  login as apiLogin,
  logout as apiLogout,
  getToken,
  getStoredUser,
  type AuthUser,
} from "./api-client";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string, role?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Initialize from localStorage synchronously (avoids set-state-in-effect)
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getToken();
    const stored = getStoredUser();
    if (token && stored) {
      return {
        id: 0,
        username: stored.name,
        email: `${stored.name}@fraudiq.ai`,
        role: stored.role,
      };
    }
    return null;
  });
  const [loading, setLoading] = useState(false);

  const login = async (username: string, password: string, role?: string) => {
    const { user: u } = await apiLogin(username, password, role);
    setUser(u);
  };

  const logout = () => {
    apiLogout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
