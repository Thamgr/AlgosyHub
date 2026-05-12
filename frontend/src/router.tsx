import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ContestDetail from "./pages/ContestDetail";
import GroupDetail from "./pages/GroupDetail";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function Router() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/groups/:id" element={<GroupDetail />} />
              <Route path="/contests/:id" element={<ContestDetail />} />
            </Routes>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
