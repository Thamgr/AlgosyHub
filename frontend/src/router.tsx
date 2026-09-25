import { Route, Routes } from "react-router-dom";
import Navigate from "./components/ViewNavigate";
import { useAuthStore } from "./store/auth";
import { useViewMode } from "./hooks/useViewMode";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ContestDetail from "./pages/ContestDetail";
import CreateContest from "./pages/CreateContest";
import CreateGroup from "./pages/CreateGroup";
import EditContest from "./pages/EditContest";
import Groups from "./pages/Groups";
import GroupDetail from "./pages/GroupDetail";
import MatchContest from "./pages/MatchContest";
import ProblemDetail from "./pages/ProblemDetail";
import ProfileSettings from "./pages/ProfileSettings";
import UserProfile from "./pages/UserProfile";
import PlatformSettings from "./pages/PlatformSettings";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireTeacher({ children }: { children: React.ReactNode }) {
  const { isTeacher } = useViewMode();
  if (!isTeacher) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function HideInStudentView({ children }: { children: React.ReactNode }) {
  const { isStudentView } = useViewMode();
  return isStudentView ? <Navigate to="/" replace /> : <>{children}</>;
}

export default function Router() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      {/* Профиль пользователя — публичный, без RequireAuth. */}
      <Route path="/u/:username" element={<UserProfile />} />
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
              <Route
                path="/contests/:id/edit"
                element={<RequireTeacher><EditContest /></RequireTeacher>}
              />
              <Route path="/problems/:id" element={<ProblemDetail />} />
              <Route path="/settings" element={<ProfileSettings />} />
              <Route path="/platform-settings" element={<HideInStudentView><PlatformSettings /></HideInStudentView>} />
            </Routes>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
