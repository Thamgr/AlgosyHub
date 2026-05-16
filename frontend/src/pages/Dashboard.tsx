import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { groupsApi } from "../api/groups";
import { useAuthStore } from "../store/auth";
import AppHeader from "../components/AppHeader";
import type { Contest, Group } from "../api/types";

export default function Dashboard() {
  const user = useAuthStore((s) => s.user);
  const isTeacher = user?.role === "teacher";

  const [groups, setGroups] = useState<Group[]>([]);
  const [contests, setContests] = useState<Contest[]>([]);

  useEffect(() => {
    groupsApi.list().then(setGroups);
    contestsApi.list().then(setContests);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />

      <main className="p-6 max-w-2xl mx-auto space-y-8">

        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-medium text-gray-700">
              <Link to="/groups" className="hover:underline">
                Группы
              </Link>
            </h2>
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
              {groups.slice(0, 5).map((g) => (
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
          {groups.length > 5 && (
            <Link
              to="/groups"
              className="block mt-2 text-xs text-blue-600 hover:underline"
            >
              Показать все ({groups.length}) →
            </Link>
          )}
        </section>

        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-medium text-gray-700">Контесты</h2>
            {isTeacher && (
              <div className="flex gap-2">
                <Link
                  to="/contests/match"
                  className="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700"
                >
                  ⚡ Автоподбор
                </Link>
                <Link
                  to="/contests/new"
                  className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                >
                  + Создать контест
                </Link>
              </div>
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
