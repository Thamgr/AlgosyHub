import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { contestsApi } from "../api/contests";
import { getApiError } from "../api/errors";
import { useAuthStore } from "../store/auth";
import type { Contest, Problem } from "../api/types";

export default function ContestDetail() {
  const { id } = useParams<{ id: string }>();
  const contestId = Number(id);
  const user = useAuthStore((s) => s.user);

  const [contest, setContest] = useState<Contest | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    contestsApi.get(contestId).then(setContest);
    contestsApi.getProblems(contestId).then(setProblems);
  }, [contestId]);

  async function handleAddProblem(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setError("");
    setLoading(true);
    try {
      const problem = await contestsApi.addProblem(contestId, input.trim().toUpperCase());
      setProblems((prev) => [...prev, problem]);
      setInput("");
    } catch (err: unknown) {
      setError(getApiError(err, "Ошибка добавления задачи"));
    } finally {
      setLoading(false);
    }
  }

  async function handleStart() {
    const updated = await contestsApi.start(contestId);
    setContest(updated);
  }

  async function handleFinish() {
    const updated = await contestsApi.finish(contestId);
    setContest(updated);
  }

  if (!contest) return <div className="p-6 text-sm text-gray-500">Загрузка...</div>;

  const isTeacher = user?.role === "teacher";
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-semibold">{contest.title}</h1>
          <span className="text-xs text-gray-400">{contest.status}</span>
        </div>
        {isTeacher && (
          <div className="flex gap-2">
            {contest.status === "draft" && (
              <button
                onClick={handleStart}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
              >
                Запустить
              </button>
            )}
            {contest.status === "running" && (
              <button
                onClick={handleFinish}
                className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Завершить
              </button>
            )}
          </div>
        )}
      </div>

      {/* Задачи */}
      <div className="border rounded mb-6">
        {problems.length === 0 ? (
          <p className="p-4 text-sm text-gray-400">Задач пока нет</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {problems.map((p, i) => (
                <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-400 w-8">{letters[i]}</td>
                  <td className="px-4 py-3">
                    <a
                      href={`${import.meta.env.VITE_API_URL ?? ""}/api/v1/problems/${p.id}/statement`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {p.title}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{p.difficulty ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{p.tags.slice(0, 3).join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Добавить задачу — только учитель в статусе draft */}
      {isTeacher && contest.status === "draft" && (
        <form onSubmit={handleAddProblem} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Например: 654B"
            className="flex-1 border rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "..." : "Добавить"}
          </button>
          {error && <p className="text-red-500 text-sm self-center">{error}</p>}
        </form>
      )}
    </div>
  );
}
