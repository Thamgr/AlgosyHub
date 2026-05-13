import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getApiError } from "../api/errors";
import { groupsApi } from "../api/groups";

export default function CreateGroup() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [usernames, setUsernames] = useState<string[]>([""]);
  const [error, setError] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  function updateUsername(index: number, value: string) {
    setUsernames((prev) => prev.map((u, i) => (i === index ? value : u)));
  }

  function addUsernameRow() {
    setUsernames((prev) => [...prev, ""]);
  }

  function removeUsernameRow(index: number) {
    setUsernames((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setError("");
    setWarnings([]);
    setLoading(true);
    try {
      const group = await groupsApi.create({ name: name.trim() });

      const cleaned = usernames.map((u) => u.trim()).filter(Boolean);
      const failed: string[] = [];
      for (const username of cleaned) {
        try {
          await groupsApi.addMember(group.id, username);
        } catch (err: unknown) {
          failed.push(`${username}: ${getApiError(err, "ошибка")}`);
        }
      }

      if (failed.length > 0) {
        setWarnings(failed);
        return;
      }
      navigate(`/groups/${group.id}`);
    } catch (err: unknown) {
      setError(getApiError(err, "Не удалось создать группу"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-xl mx-auto">
        <Link to="/" className="text-sm text-gray-400 hover:underline">← Назад</Link>
        <h1 className="text-xl font-semibold mt-1 mb-6">Новая группа</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1">Название</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: 10А"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium">
                Ученики <span className="text-gray-400 font-normal">(опционально)</span>
              </label>
              <button
                type="button"
                onClick={addUsernameRow}
                className="text-xs text-blue-600 hover:underline"
              >
                + Добавить
              </button>
            </div>
            <div className="space-y-2">
              {usernames.map((u, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    value={u}
                    onChange={(e) => updateUsername(i, e.target.value)}
                    placeholder="username"
                    className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {usernames.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeUsernameRow(i)}
                      className="px-3 text-sm text-red-400 hover:text-red-600"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}
          {warnings.length > 0 && (
            <div className="text-sm text-amber-600 space-y-1">
              <p>Группа создана, но не всех учеников удалось добавить:</p>
              <ul className="list-disc pl-5">
                {warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
              <Link to="/" className="text-blue-600 hover:underline">Вернуться на главную</Link>
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Создание..." : "Создать"}
            </button>
            <Link
              to="/"
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              Отмена
            </Link>
          </div>
        </form>
      </main>
    </div>
  );
}
