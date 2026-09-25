import axios from "axios";
import { useAuthStore } from "../store/auth";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const session = useAuthStore.getState();
    if (
      err.response?.status === 401 &&
      err.config?.url !== "/api/v1/auth/login" &&
      session.token &&
      err.config?.headers?.Authorization === `Bearer ${session.token}`
    ) {
      // Clear the persisted session too. Route guards handle navigation without
      // reloading /login; a late response must not clear a newer session.
      session.logout();
    }
    return Promise.reject(err);
  }
);

export default api;
