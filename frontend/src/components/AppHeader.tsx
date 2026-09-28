import Link from "../components/ViewLink";
import { useAuthStore } from "../store/auth";
import { useViewMode } from "../hooks/useViewMode";
import UserIdentity from "./UserIdentity";

/**
 * Шапка приложения.
 *
 * Авторизованному пользователю показываем имя и аватарку — ссылка
 * ведёт в его публичный профиль, откуда уже доступны настройки и выход.
 * Для незалогиненного посетителя публичной страницы профиля показываем
 * ссылку «Войти», чтобы он мог зайти.
 */
export default function AppHeader() {
  const user = useAuthStore((s) => s.user);
  const { isStudentView, isPlatformAdmin } = useViewMode();

  return (
    <header className="bg-white border-b px-6 py-3 flex items-center justify-between gap-4">
      <Link to="/" className="font-semibold">
        AlgosyHub
      </Link>
      <div className="flex min-w-0 items-center gap-4 text-sm">
        {isPlatformAdmin && (
          <Link to="/platform-settings" className="text-blue-600 hover:underline">
            Настройки платформы
          </Link>
        )}
        {user ? (
          <Link
            to={`/u/${user.username}`}
            className="flex min-w-0 items-center gap-2 text-gray-700 hover:underline"
          >
            <UserIdentity user={user} />
            <span className="text-xs text-gray-400 shrink-0">({isStudentView ? "student" : user.role})</span>
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
