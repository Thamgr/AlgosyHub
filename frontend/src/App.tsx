import { useEffect } from "react";
import { BrowserRouter, useLocation } from "react-router-dom";
import Router from "./router";
import api from "./api/client";
import type { User } from "./api/types";
import { useAuthStore } from "./store/auth";
import { usePlatformSettings } from "./store/platformSettings";

function PlatformState() {
  const { pathname } = useLocation();
  const token = useAuthStore((s) => s.token);
  const refresh = usePlatformSettings((s) => s.refresh);
  useEffect(() => { void refresh(); }, [pathname, refresh]);
  useEffect(() => {
    const timer = window.setInterval(() => void refresh(), 30000);
    const onFocus = () => { void refresh(); };
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
    };
  }, [refresh]);
  useEffect(() => {
    if (!token) return;
    let active = true;
    api.get<User>("/api/v1/auth/me").then(({ data }) => {
      if (active) useAuthStore.getState().setUser(data);
    }).catch(() => {});
    return () => { active = false; };
  }, [token]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <PlatformState />
      <Router />
    </BrowserRouter>
  );
}
