import { useCallback } from "react";
import { useLocation, useNavigate, type NavigateOptions, type To } from "react-router-dom";
import { withStudentView } from "../lib/viewMode";

export function useViewNavigate() {
  const navigate = useNavigate();
  const { search } = useLocation();
  return useCallback((to: To | number, options?: NavigateOptions) => {
    if (typeof to === "number") return navigate(to);
    return navigate(withStudentView(to, search), options);
  }, [navigate, search]);
}
