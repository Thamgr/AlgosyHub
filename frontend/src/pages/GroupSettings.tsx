import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Link from "../components/ViewLink";
import Navigate from "../components/ViewNavigate";
import { getApiError } from "../api/errors";
import { groupsApi } from "../api/groups";
import { useViewMode } from "../hooks/useViewMode";
import { useAuthStore } from "../store/auth";
import type { Group, User } from "../api/types";
import UserIdentity from "../components/UserIdentity";
import { displayName } from "../lib/userDisplay";

export default function GroupSettings() {
  const { id } = useParams<{ id: string }>();
  const userId = useAuthStore((s) => s.user?.id);
  return <GroupSettingsContent key={`${id}:${userId}`} groupId={Number(id)} />;
}

function GroupSettingsContent({ groupId }: { groupId: number }) {
  const user = useAuthStore((s) => s.user);
  const userId = user?.id;
  const { isTeacher } = useViewMode();
  const [group, setGroup] = useState<Group | null>(null);
  const [members, setMembers] = useState<User[]>([]);
  const [observers, setObservers] = useState<User[]>([]);
  const [observerUsername, setObserverUsername] = useState("");
  const [observerError, setObserverError] = useState("");
  const [observerBusy, setObserverBusy] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [name, setName] = useState("");
  const [nameSaving, setNameSaving] = useState(false);
  const [nameSaved, setNameSaved] = useState(false);
  const [nameError, setNameError] = useState("");
  const [username, setUsername] = useState("");
  const [memberError, setMemberError] = useState("");
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<number | null>(null);

  useEffect(() => {
    if (userId === undefined || !isTeacher) return;
    let active = true;
    groupsApi.getSettings(groupId).then((data) => {
      if (!active) return;
      setGroup(data.group);
      setName(data.group.name);
      setMembers(data.members);
      setObservers(data.observers);
    }).catch(() => {
      if (active) setLoadError("Не удалось открыть настройки. Они доступны только учителю — владельцу группы.");
    });
    return () => { active = false; };
  }, [groupId, isTeacher, userId]);

  async function handleSaveName(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setNameError("");
    setNameSaved(false);
    setNameSaving(true);
    try {
      const updated = await groupsApi.update(groupId, { name: name.trim() });
      setGroup(updated);
      setName(updated.name);
      setNameSaved(true);
    } catch (err: unknown) {
      setNameError(getApiError(err, "Не удалось сохранить название"));
    } finally {
      setNameSaving(false);
    }
  }

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    setMemberError("");
    setAdding(true);
    try {
      await groupsApi.addMember(groupId, username.trim());
      setMembers(await groupsApi.getMembers(groupId));
      setUsername("");
    } catch (err: unknown) {
      setMemberError(getApiError(err, "Не удалось добавить участника"));
    } finally {
      setAdding(false);
    }
  }

  async function handleRemoveMember(userId: number) {
    setMemberError("");
    setRemoving(userId);
    try {
      await groupsApi.removeMember(groupId, userId);
      setMembers((current) => current.filter((member) => member.id !== userId));
    } catch (err: unknown) {
      setMemberError(getApiError(err, "Не удалось удалить участника"));
    } finally {
      setRemoving(null);
    }
  }

  async function handleAddObserver(e: React.FormEvent) {
    e.preventDefault();
    if (!observerUsername.trim()) return;
    setObserverBusy(true);
    setObserverError("");
    try {
      await groupsApi.addObserver(groupId, observerUsername.trim());
      setObservers((await groupsApi.getSettings(groupId)).observers);
      setObserverUsername("");
    } catch (err: unknown) {
      setObserverError(getApiError(err, "Не удалось добавить наблюдателя"));
    } finally {
      setObserverBusy(false);
    }
  }

  async function handleRemoveObserver(observerId: number) {
    setObserverBusy(true);
    setObserverError("");
    try {
      await groupsApi.removeObserver(groupId, observerId);
      setObservers((current) => current.filter((observer) => observer.id !== observerId));
    } catch (err: unknown) {
      setObserverError(getApiError(err, "Не удалось удалить наблюдателя"));
    } finally {
      setObserverBusy(false);
    }
  }

  if (!user) return <div className="p-6 text-sm text-gray-400">Загрузка...</div>;
  if (!isTeacher) return <Navigate to={`/groups/${groupId}`} replace />;
  const allowed = group?.teacher_id === user.id;

  return (
    <main className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <Link to={`/groups/${groupId}`} className="text-sm text-gray-400 hover:underline">← К группе</Link>
        <h1 className="text-xl font-semibold mt-1">Настройки группы</h1>
      </div>
      {loadError ? <p role="alert" className="text-sm text-red-500">{loadError}</p>
        : !group ? <p className="text-sm text-gray-400">Загрузка...</p>
          : !allowed ? <p role="alert" className="text-sm text-red-500">Настройки доступны только владельцу группы.</p>
            : <>
              <section className="border rounded bg-white p-4">
                <form onSubmit={handleSaveName}>
                  <label htmlFor="group-name" className="block text-sm font-medium mb-2">Название группы</label>
                  <div className="flex gap-2">
                    <input id="group-name" required maxLength={200} value={name} disabled={nameSaving}
                      onChange={(e) => { setName(e.target.value); setNameSaved(false); }}
                      className="min-w-0 flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <button type="submit" disabled={nameSaving || !name.trim() || name.trim() === group.name}
                      className="shrink-0 px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
                      {nameSaving ? "Сохранение..." : "Сохранить"}
                    </button>
                  </div>
                  {nameSaved && <p role="status" className="mt-2 text-sm text-green-700">Название сохранено</p>}
                  {nameError && <p role="alert" className="mt-2 text-sm text-red-500">{nameError}</p>}
                </form>
              </section>

              <section>
                <h2 className="text-sm font-medium text-gray-700 mb-2">Участники ({members.length})</h2>
                <div className="border rounded divide-y mb-3">
                  {members.length === 0 ? <p className="px-4 py-3 text-sm text-gray-400">Нет участников</p>
                    : members.map((member) => (
                      <div key={member.id} className="flex items-center justify-between gap-3 px-4 py-2">
                        <Link to={`/u/${member.username}`} title={`@${member.username}`} className="min-w-0 truncate text-sm hover:underline"><UserIdentity user={member} /></Link>
                        <button type="button" onClick={() => void handleRemoveMember(member.id)} disabled={adding || removing !== null}
                          aria-label={`Удалить ${displayName(member)} из группы`}
                          className="shrink-0 text-xs text-red-400 hover:text-red-600 disabled:opacity-50">
                          {removing === member.id ? "Удаление..." : "Удалить"}
                        </button>
                      </div>
                    ))}
                </div>
                <form onSubmit={handleAddMember} className="flex gap-2">
                  <input value={username} onChange={(e) => setUsername(e.target.value)} disabled={adding}
                    aria-label="Username ученика" placeholder="Username ученика"
                    className="min-w-0 flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  <button type="submit" disabled={adding || removing !== null || !username.trim()}
                    className="shrink-0 px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
                    {adding ? "Добавление..." : "Добавить"}
                  </button>
                </form>
                {memberError && <p role="alert" className="mt-2 text-sm text-red-500">{memberError}</p>}
              </section>
              <section>
                <h2 className="text-sm font-medium text-gray-700 mb-2">Наблюдатели ({observers.length})</h2>
                <div className="border rounded divide-y mb-3">
                  {observers.length === 0 ? <p className="px-4 py-3 text-sm text-gray-400">Нет наблюдателей</p>
                    : observers.map((observer) => (
                      <div key={observer.id} className="flex items-center justify-between gap-3 px-4 py-2">
                        <Link to={`/u/${observer.username}`} className="min-w-0 truncate text-sm hover:underline"><UserIdentity user={observer} /></Link>
                        <button type="button" disabled={observerBusy} onClick={() => void handleRemoveObserver(observer.id)}
                          aria-label={`Удалить наблюдателя ${displayName(observer)}`}
                          className="shrink-0 text-xs text-red-400 hover:text-red-600 disabled:opacity-50">Удалить</button>
                      </div>
                    ))}
                </div>
                <form onSubmit={handleAddObserver} className="flex gap-2">
                  <input value={observerUsername} onChange={(e) => setObserverUsername(e.target.value)} disabled={observerBusy}
                    aria-label="Логин наблюдателя" placeholder="Логин наблюдателя"
                    className="min-w-0 flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  <button type="submit" disabled={observerBusy || !observerUsername.trim()}
                    className="shrink-0 px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
                    {observerBusy ? "Сохранение..." : "Добавить наблюдателя"}
                  </button>
                </form>
                {observerError && <p role="alert" className="mt-2 text-sm text-red-500">{observerError}</p>}
              </section>
            </>}
    </main>
  );
}
