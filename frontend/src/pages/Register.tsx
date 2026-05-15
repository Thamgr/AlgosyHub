import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { getApiError } from "../api/errors";
import { useAuthStore } from "../store/auth";
import type { TokenResponse, User, UserRole } from "../api/types";

export default function Register() {
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const [form, setForm] = useState({
    username: "",
    password: "",
    role: "student" as UserRole,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/api/v1/auth/register", form);
      const { data: token } = await api.post<TokenResponse>("/api/v1/auth/login", {
        username: form.username,
        password: form.password,
      });
      setToken(token.access_token);
      const { data: user } = await api.get<User>("/api/v1/auth/me");
      setUser(user);
      navigate("/");
    } catch (err: unknown) {
      setError(getApiError(err, "Ошибка регистрации"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-6">Регистрация</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Логин</label>
            <input
              type="text"
              autoComplete="username"
              required
              value={form.username}
              onChange={(e) => set("username", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Пароль</label>
            <input
              type="password"
              autoComplete="new-password"
              required
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Роль</label>
            <div className="flex gap-4">
              {(["student", "teacher"] as UserRole[]).map((r) => (
                <label key={r} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="radio"
                    value={r}
                    checked={form.role === r}
                    onChange={() => set("role", r)}
                  />
                  {r === "student" ? "Ученик" : "Учитель"}
                </label>
              ))}
            </div>
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Регистрация..." : "Зарегистрироваться"}
          </button>
        </form>
        <p className="mt-4 text-sm text-center text-gray-500">
          Уже есть аккаунт?{" "}
          <Link to="/login" className="text-blue-600 hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
