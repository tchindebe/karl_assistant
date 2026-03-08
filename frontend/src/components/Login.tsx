import { useState } from "react";
import axios from "axios";
import { Terminal } from "lucide-react";

interface Props {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: Props) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await axios.post("/api/auth/login", { password });
      onLogin(data.token);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Mot de passe incorrect");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}>
      <div className="w-full max-w-sm p-8 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 rounded-xl" style={{ background: "var(--accent)" }}>
            <Terminal size={24} color="white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Karl</h1>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>AI VPS Assistant</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-2" style={{ color: "var(--text-muted)" }}>
              Mot de passe
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoFocus
              className="w-full px-4 py-3 rounded-xl text-white outline-none transition-all"
              style={{
                background: "var(--surface2)",
                border: "1px solid var(--border)",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
            />
          </div>

          {error && (
            <p className="text-sm px-3 py-2 rounded-lg" style={{ background: "#ef44441a", color: "var(--red)", border: "1px solid #ef444430" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-3 rounded-xl font-semibold transition-all"
            style={{
              background: loading || !password ? "var(--surface2)" : "var(--accent)",
              color: loading || !password ? "var(--text-muted)" : "white",
              cursor: loading || !password ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
