import { Link, useLocation, type LinkProps } from "react-router-dom";
import { withStudentView } from "../lib/viewMode";

export default function ViewLink({ to, ...props }: LinkProps) {
  const { search } = useLocation();
  return <Link {...props} to={withStudentView(to, search)} />;
}
