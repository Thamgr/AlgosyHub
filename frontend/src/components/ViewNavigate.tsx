import { Navigate, useLocation, type NavigateProps } from "react-router-dom";
import { withStudentView } from "../lib/viewMode";

export default function ViewNavigate({ to, ...props }: NavigateProps) {
  const { search } = useLocation();
  return <Navigate {...props} to={withStudentView(to, search)} />;
}
