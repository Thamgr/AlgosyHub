import { useLocation } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { viewPermissions } from "../lib/viewMode";

export function useViewMode() {
  const user = useAuthStore((state) => state.user);
  const { search } = useLocation();
  return viewPermissions(user, search);
}
