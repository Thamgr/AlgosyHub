import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ContestDetail from "./pages/ContestDetail";
import CreateContest from "./pages/CreateContest";
import CreateGroup from "./pages/CreateGroup";
import Groups from "./pages/Groups";
import GroupDetail from "./pages/GroupDetail";
import MatchContest from "./pages/MatchContest";
import ProblemDetail from "./pages/ProblemDetail";
import Profile from "./pages/Profile";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireTeacher({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (user?.role !== "teacher") return <Navigate to="/" replace />;
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
              <Route path="/groups" element={<Groups />} />
              <Route
                path="/groups/new"
                element={<RequireTeacher><CreateGroup /></RequireTeacher>}
              />
              <Route path="/groups/:id" element={<GroupDetail />} />
              <Route
                path="/contests/new"
                element={<RequireTeacher><CreateContest /></RequireTeacher>}
              />
              <Route
                path="/contests/match"
                element={<RequireTeacher><MatchContest /></RequireTeacher>}
              />
              <Route path="/contests/:id" element={<ContestDetail />} />
              <Route path="/problems/:id" element={<ProblemDetail />} />
              <Route path="/profile" element={<Profile />} />
            </Routes>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
