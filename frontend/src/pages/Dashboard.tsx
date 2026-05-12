import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { contestsApi } from "../api/contests";
import { useAuthStore } from "../store/auth";
import type { Contest } from "../api/types";

export default function Dashboard() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const isTeacher = user?.role === "teacher";

  const [groupId, setGroupId] = useState("");
  const [title, setTitle] = useState("");
  const [contests, setContests] = useState<Contest[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  async function loadContests(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const { data } = await api.get<Contest[]>(
        `/api/v1/contests?group_id=${groupId}`
      );
      setContests(data);
      setLoaded(true);
    } catch {
      setError("Группа не найдена");
    }
  }

  async function createContest(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !groupId) return;
    try {
      const contest = await contestsApi.create({
        group_id: Number(groupId),
        title: title.trim(),
      });
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

      <main className="p-6 max-w-2xl mx-auto space-y-6">
        {/* Контесты группы */}
        <section>
          <h2 className="text-sm font-medium text-gray-700 mb-2">Контесты группы</h2>
          <form onSubmit={loadContests} className="flex gap-2 mb-3">
            <input
              type="number"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              placeholder="ID группы"
              className="border rounded px-3 py-2 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-gray-800 text-white text-sm rounded hover:bg-gray-900"
            >
              Показать
            </button>
          </form>

          {loaded && contests.length === 0 && (
            <p className="text-sm text-gray-400">Контестов нет</p>
          )}
          {contests.map((c) => (
            <Link
              key={c.id}
              to={`/contests/${c.id}`}
              className="flex items-center justify-between border rounded px-4 py-3 bg-white hover:bg-gray-50 mb-2"
            >
              <span className="text-sm font-medium">{c.title}</span>
              <span className="text-xs text-gray-400">{c.status}</span>
            </Link>
          ))}
        </section>

        {/* Создать контест — только учитель */}
        {isTeacher && (
          <section>
            <h2 className="text-sm font-medium text-gray-700 mb-2">Создать контест</h2>
            <form onSubmit={createContest} className="flex gap-2">
              <input
                type="number"
                value={groupId}
                onChange={(e) => setGroupId(e.target.value)}
                placeholder="ID группы"
                className="border rounded px-3 py-2 text-sm w-32 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Название"
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
