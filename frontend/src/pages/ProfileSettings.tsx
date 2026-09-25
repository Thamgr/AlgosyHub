import Navigate from "../components/ViewNavigate";
import { useAuthStore } from "../store/auth";

export default function ProfileSettings() {
  const user = useAuthStore((s) => s.user);
  if (!user) return <div className="p-6 text-sm text-gray-500">Загрузка...</div>;
  return <Navigate to={`/u/${user.username}#settings`} replace />;
}
