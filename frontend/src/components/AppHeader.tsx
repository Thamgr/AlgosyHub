import { Link } from "react-router-dom";
import { useAuthStore } from "../store/auth";

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

  return (
    <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
      <Link to="/" className="font-semibold">
        AlgosyHub
      </Link>
      <div className="flex items-center gap-4 text-sm">
        {user ? (
          <Link
            to={`/u/${user.username}`}
            className="text-gray-700 hover:underline"
          >
            {user.username}{" "}
            <span className="text-xs text-gray-400">({user.role})</span>
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
