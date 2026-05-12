import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/auth";
import type { TokenResponse, User } from "../api/types";

export default function Login() {
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data: token } = await api.post<TokenResponse>("/api/v1/auth/login", {
        email,
        password,
      });
      setToken(token.access_token);
      const { data: user } = await api.get<User>("/api/v1/auth/me");
      setUser(user);
      navigate("/");
    } catch {
      setError("Неверный email или пароль");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-6">AlgosyHub</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Пароль</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Вход..." : "Войти"}
          </button>
        </form>
        <p className="mt-4 text-sm text-center text-gray-500">
          Нет аккаунта?{" "}
          <Link to="/register" className="text-blue-600 hover:underline">
            Зарегистрироваться
          </Link>
        </p>
      </div>
    </div>
  );
}
