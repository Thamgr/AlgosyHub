import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Link from "../components/ViewLink";
import { getApiError } from "../api/errors";
import { groupsApi } from "../api/groups";
import { useViewMode } from "../hooks/useViewMode";
import type { Group, User } from "../api/types";
import GroupScoreboard from "../components/GroupScoreboard";

export default function GroupDetail() {
  const { id } = useParams<{ id: string }>();
  const groupId = Number(id);
  const { isTeacher } = useViewMode();

  const [group, setGroup] = useState<Group | null>(null);
  const [members, setMembers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [scoreboardRevision, setScoreboardRevision] = useState(0);

  useEffect(() => {
    groupsApi.get(groupId).then(setGroup);
    groupsApi.getMembers(groupId).then(setMembers);
  }, [groupId]);

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    setError("");
    try {
      await groupsApi.addMember(groupId, username.trim());
      const updated = await groupsApi.getMembers(groupId);
      setMembers(updated);
      setScoreboardRevision((value) => value + 1);
      setUsername("");
    } catch (err: unknown) {
      setError(getApiError(err));
    }
  }

  async function handleRemoveMember(userId: number) {
    await groupsApi.removeMember(groupId, userId);
    setMembers((prev) => prev.filter((m) => m.id !== userId));
    setScoreboardRevision((value) => value + 1);
  }

  if (!group) return <div className="p-6 text-sm text-gray-400">Загрузка...</div>;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div>
        <Link to="/" className="text-sm text-gray-400 hover:underline">← Назад</Link>
        <h1 className="text-xl font-semibold mt-1">{group.name}</h1>
      </div>

      <GroupScoreboard key={groupId} groupId={groupId} revision={scoreboardRevision} />

      {/* Участники */}
      <section className="max-w-3xl">
        <h2 className="text-sm font-medium text-gray-700 mb-2">
          Участники ({members.length})
        </h2>
        <div className="border rounded divide-y mb-3">
          {members.length === 0 ? (
            <p className="px-4 py-3 text-sm text-gray-400">Нет участников</p>
          ) : (
            members.map((m) => (
              <div key={m.id} className="flex items-center justify-between px-4 py-2">
                <Link
                  to={`/u/${m.username}`}
                  className="text-sm hover:underline"
                >
                  {m.username}
                </Link>
                {isTeacher && (
                  <button
                    onClick={() => handleRemoveMember(m.id)}
                    className="text-xs text-red-400 hover:text-red-600"
                  >
                    Удалить
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        {isTeacher && (
          <form onSubmit={handleAddMember} className="flex gap-2">
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username ученика"
              className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
            >
              Добавить
            </button>
          </form>
        )}
        {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
      </section>
    </div>
  );
}
