import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Link from "../components/ViewLink";
import { groupsApi } from "../api/groups";
import { useViewMode } from "../hooks/useViewMode";
import { useAuthStore } from "../store/auth";
import type { GroupDetail as GroupData } from "../api/types";
import GroupScoreboard from "../components/GroupScoreboard";
import GroupMaterials from "../components/GroupMaterials";
import UserIdentity from "../components/UserIdentity";

export default function GroupDetail() {
  const { id } = useParams<{ id: string }>();
  return <GroupDetailContent key={id} groupId={Number(id)} />;
}

function GroupDetailContent({ groupId }: { groupId: number }) {
  const { isTeacher } = useViewMode();
  const userId = useAuthStore((s) => s.user?.id);
  const [group, setGroup] = useState<GroupData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    groupsApi.get(groupId).then((data) => {
      if (active) setGroup(data);
    }).catch(() => {
      if (active) setError("Не удалось загрузить группу.");
    });
    return () => { active = false; };
  }, [groupId]);

  if (error) return <div role="alert" className="p-6 text-sm text-red-500">{error}</div>;
  if (!group) return <div className="p-6 text-sm text-gray-400">Загрузка...</div>;

  const canManage = isTeacher && userId === group.teacher_id;
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div>
        <Link to="/" className="text-sm text-gray-400 hover:underline">← Назад</Link>
        <div className="flex items-center justify-between gap-4 mt-1">
          <h1 className="min-w-0 break-words text-xl font-semibold">{group.name}</h1>
          {canManage && (
            <Link to={`/groups/${groupId}/settings`} aria-label="Настройки группы" title="Настройки группы"
              className="shrink-0 rounded p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinejoin="round" aria-hidden="true" className="h-5 w-5">
                <path d="M9.5 3h5l.6 2.4 1.4.8 2.4-.7 2.5 4.3-1.8 1.7v1.6l1.8 1.7-2.5 4.3-2.4-.7-1.4.8-.6 2.4h-5l-.6-2.4-1.4-.8-2.4.7-2.5-4.3 1.8-1.7v-1.6L2.1 9.8l2.5-4.3 2.4.7 1.4-.8L9.5 3Z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            </Link>
          )}
        </div>
        <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
          <span>by</span>
          <Link to={`/u/${encodeURIComponent(group.author.username)}`} className="min-w-0 text-gray-700 hover:underline">
            <UserIdentity user={group.author} />
          </Link>
        </div>
      </div>
      <GroupMaterials groupId={groupId} canManage={canManage} />
      <GroupScoreboard groupId={groupId} />
    </div>
  );
}
