import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../api/types";

interface AuthState {
  token: string | null;
  user: User | null;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setToken: (token) => {
        // The persisted auth store is the single source of truth. Remove the
        // legacy duplicate, which could disagree with the restored session.
        localStorage.removeItem("token");
        set({ token, user: null });
      },
      setUser: (user) => set({ user }),
      logout: () => {
        localStorage.removeItem("token");
        set({ token: null, user: null });
      },
    }),
    { name: "auth" }
  )
);
