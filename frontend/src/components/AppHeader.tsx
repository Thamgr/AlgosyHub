import Link from "../components/ViewLink";
import { useAuthStore } from "../store/auth";
import { useViewMode } from "../hooks/useViewMode";

/**
 * Шапка приложения.
 *
 * Авторизованному пользователю показываем только кликабельный username — он
 * ведёт в его публичный профиль, откуда уже доступны настройки и выход.
 * Для незалогиненного посетителя публичной страницы профиля показываем
 * ссылку «Войти», чтобы он мог зайти.
 */
export default function AppHeader() {
  const user = useAuthStore((s) => s.user);
  const { isStudentView, isPlatformAdmin } = useViewMode();

  return (
    <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
      <Link to="/" className="font-semibold">
        AlgosyHub
      </Link>
      <div className="flex items-center gap-4 text-sm">
        {isPlatformAdmin && (
          <Link to="/platform-settings" className="text-blue-600 hover:underline">
            Настройки платформы
          </Link>
        )}
        {user ? (
          <Link
            to={`/u/${user.username}`}
            className="text-gray-700 hover:underline"
          >
            {user.username}{" "}
            <span className="text-xs text-gray-400">({isStudentView ? "student" : user.role})</span>
          </Link>
        ) : (
          <Link to="/login" className="text-blue-600 hover:underline">
            Войти
          </Link>
        )}
      </div>
    </header>
  );
}
