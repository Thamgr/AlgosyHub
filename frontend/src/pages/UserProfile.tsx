import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Link from "../components/ViewLink";
import { useViewNavigate as useNavigate } from "../hooks/useViewNavigate";
import { usersApi } from "../api/users";
import { useAuthStore } from "../store/auth";
import type { User, UserProfile } from "../api/types";
import AppHeader from "../components/AppHeader";
import ProfileSettingsPanel from "../components/ProfileSettingsPanel";

export default function UserProfilePage() {
  const { username = "" } = useParams<{ username: string }>();
  return <ProfileContent key={username} username={username} />;
}

function ProfileContent({ username }: { username: string }) {
  const navigate = useNavigate();
  const { user: me, logout } = useAuthStore();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    usersApi
      .getByUsername(username)
      .then((data) => { if (active) setProfile(data); })
      .catch(() => { if (active) setError("Пользователь не найден"); });
    return () => { active = false; };
  }, [username]);

  const isOwnProfile = profile != null && me?.id === profile.id;
  const fullName = profile?.full_name ?? "";

  function handleProfileSaved(updated: User) {
    setProfile((current) => current ? { ...current, ...updated } : current);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />

      <main className={`p-6 mx-auto space-y-6 ${isOwnProfile ? "max-w-6xl" : "max-w-2xl"}`}>
        <div>
          <Link to="/" className="text-sm text-gray-500 hover:underline">
            ← Назад
          </Link>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}
        {!profile && !error && <p className="text-sm text-gray-500">Загрузка...</p>}

        {profile && (
          <div className={isOwnProfile ? "grid lg:grid-cols-[minmax(0,1fr)_minmax(0,440px)] gap-8 items-start" : ""}>
            <div className="min-w-0 space-y-6">
              <div className="bg-white border rounded p-6">
                <div className="flex items-baseline justify-between gap-4">
                  <div className="min-w-0">
                    <h1 className="text-2xl font-semibold break-words">{profile.username}</h1>
                    {fullName && <p className="text-sm text-gray-700 mt-2 break-words">{fullName}</p>}
                    <p className="text-xs text-gray-500 mt-1">{profile.role}</p>
                  </div>
                  {isOwnProfile && (
                    <div className="flex items-center gap-3 text-sm">
                      <button
                        onClick={() => {
                          logout();
                          navigate("/login");
                        }}
                        className="text-red-500 hover:underline"
                      >
                        Выйти
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <section>
                <h2 className="text-sm font-medium text-gray-700 mb-2">
                  Статистика
                </h2>
                <div className="grid grid-cols-2 gap-3">
                  <StatCard
                    label="Сдано задач"
                    value={profile.stats.solved_problems.toString()}
                    hint="Уникальные задачи, по которым есть хотя бы одна успешная посылка."
                  />
                  <StatCard
                    label="% успешных посылок"
                    value={formatRate(profile.stats)}
                    hint={`${profile.stats.accepted_submissions} из ${profile.stats.total_submissions} посылок зачтено.`}
                  />
                </div>
              </section>
            </div>
            {isOwnProfile && <ProfileSettingsPanel user={profile} onSaved={handleProfileSaved} />}
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="bg-white border rounded p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {hint && <div className="text-xs text-gray-400 mt-2">{hint}</div>}
    </div>
  );
}

function formatRate(stats: {
  total_submissions: number;
  success_rate: number;
}): string {
  if (stats.total_submissions === 0) return "—";
  const pct = stats.success_rate * 100;
  return `${pct.toFixed(pct >= 100 ? 0 : 1)}%`;
}
