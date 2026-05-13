import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { groupsApi } from "../api/groups";
import { useAuthStore } from "../store/auth";
import type { Contest, Group } from "../api/types";

export default function Dashboard() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const isTeacher = user?.role === "teacher";

  const [groups, setGroups] = useState<Group[]>([]);
  const [contests, setContests] = useState<Contest[]>([]);

  useEffect(() => {
    groupsApi.list().then(setGroups);
    contestsApi.list().then(setContests);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <span className="font-semibold">AlgosyHub</span>
        <div className="flex items-center gap-4 text-sm">
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

      <main className="p-6 max-w-2xl mx-auto space-y-8">

        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-medium text-gray-700">Группы</h2>
            {isTeacher && (
              <Link
                to="/groups/new"
                className="px-3 py-1 bg-gray-800 text-white text-sm rounded hover:bg-gray-900"
              >
                + Создать группу
              </Link>
            )}
          </div>
          {groups.length === 0 ? (
            <p className="text-sm text-gray-400">Нет групп</p>
          ) : (
            <div className="border rounded divide-y">
              {groups.map((g) => (
                <Link
                  key={g.id}
                  to={`/groups/${g.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
                >
                  <span className="text-sm font-medium">{g.name}</span>
                  <span className="text-xs text-gray-400">→</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-medium text-gray-700">Контесты</h2>
            {isTeacher && (
              <Link
                to="/contests/new"
                className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
              >
                + Создать контест
              </Link>
            )}
          </div>
          {contests.length === 0 ? (
            <p className="text-sm text-gray-400">Нет контестов</p>
          ) : (
            <div className="border rounded divide-y">
              {contests.map((c) => (
                <Link
                  key={c.id}
                  to={`/contests/${c.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
                >
                  <span className="text-sm font-medium">{c.title}</span>
                  <span className="text-xs text-gray-400">{c.status}</span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
