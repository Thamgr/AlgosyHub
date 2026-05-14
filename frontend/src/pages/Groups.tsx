import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { groupsApi } from "../api/groups";
import { useAuthStore } from "../store/auth";
import type { Group } from "../api/types";

export default function Groups() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const isTeacher = user?.role === "teacher";

  const [groups, setGroups] = useState<Group[] | null>(null);

  useEffect(() => {
    groupsApi.list().then(setGroups);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <Link to="/" className="font-semibold">AlgosyHub</Link>
        <div className="flex items-center gap-4 text-sm">
          <Link to="/profile" className="text-gray-700 hover:underline">Профиль</Link>
          <span className="text-gray-500">
            {user?.username}{" "}
            <span className="text-xs text-gray-400">({user?.role})</span>
          </span>
          <button
            onClick={() => { logout(); navigate("/login"); }}
            className="text-red-500 hover:underline"
          >
            Выйти
          </button>
        </div>
      </header>

      <main className="p-6 max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <Link to="/" className="text-sm text-gray-400 hover:underline">
              ← Назад
            </Link>
            <h1 className="text-2xl font-semibold mt-1">Группы</h1>
            <p className="text-xs text-gray-500 mt-1">
              Группа задаёт круг учеников, которым видны её контесты. Один ученик может
              состоять в нескольких группах одновременно — они работают как теги.
            </p>
          </div>
          {isTeacher && (
            <Link
              to="/groups/new"
              className="px-3 py-1.5 bg-gray-800 text-white text-sm rounded hover:bg-gray-900"
            >
              + Создать группу
            </Link>
          )}
        </div>

        {groups === null ? (
          <p className="text-sm text-gray-400">Загрузка...</p>
        ) : groups.length === 0 ? (
          <div className="border border-dashed rounded p-8 text-center bg-white">
            <p className="text-sm text-gray-500">
              {isTeacher
                ? "Вы пока не создали ни одной группы."
                : "Вас пока не добавили ни в одну группу. Попросите учителя добавить ваш username."}
            </p>
            {isTeacher && (
              <Link
                to="/groups/new"
                className="inline-block mt-3 text-sm text-blue-600 hover:underline"
              >
                Создать первую группу
              </Link>
            )}
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {groups.map((g) => (
              <Link
                key={g.id}
                to={`/groups/${g.id}`}
                className="block bg-white border rounded p-4 hover:shadow-sm transition"
              >
                <div className="flex items-baseline justify-between">
                  <h2 className="text-sm font-semibold">{g.name}</h2>
                  <span className="text-xs text-gray-400">#{g.id}</span>
                </div>
                {g.description ? (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{g.description}</p>
                ) : (
                  <p className="text-xs text-gray-300 mt-1">без описания</p>
                )}
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
