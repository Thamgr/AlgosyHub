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
  const [groupName, setGroupName] = useState("");
  const [contestTitle, setContestTitle] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    groupsApi.list().then(setGroups);
    if (isTeacher) {
      contestsApi.listMine().then(setContests);
    }
  }, [isTeacher]);

  async function handleCreateGroup(e: React.FormEvent) {
    e.preventDefault();
    if (!groupName.trim()) return;
    try {
      const group = await groupsApi.create({ name: groupName.trim() });
      setGroups((prev) => [...prev, group]);
      setGroupName("");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Ошибка");
    }
  }

  async function handleCreateContest(e: React.FormEvent) {
    e.preventDefault();
    if (!contestTitle.trim()) return;
    try {
      const contest = await contestsApi.create({ title: contestTitle.trim() });
      navigate(`/contests/${contest.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Ошибка");
    }
  }

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

        {/* Группы */}
        <section>
          <h2 className="text-sm font-medium text-gray-700 mb-2">Группы</h2>
          {groups.length === 0 ? (
            <p className="text-sm text-gray-400">Нет групп</p>
          ) : (
            <div className="border rounded divide-y mb-3">
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
          {isTeacher && (
            <form onSubmit={handleCreateGroup} className="flex gap-2">
              <input
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="Название группы"
                className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-900"
              >
                Создать
              </button>
            </form>
          )}
        </section>

        {/* Контесты учителя */}
        {isTeacher && (
          <section>
            <h2 className="text-sm font-medium text-gray-700 mb-2">Мои контесты</h2>
            {contests.length === 0 ? (
              <p className="text-sm text-gray-400">Нет контестов</p>
            ) : (
              <div className="border rounded divide-y mb-3">
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
            <form onSubmit={handleCreateContest} className="flex gap-2">
              <input
                value={contestTitle}
                onChange={(e) => setContestTitle(e.target.value)}
                placeholder="Название контеста"
                className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
              >
                Создать
              </button>
            </form>
          </section>
        )}

        {error && <p className="text-red-500 text-sm">{error}</p>}
      </main>
    </div>
  );
}
