import { useEffect, useState } from "react";
import {
  Database, RefreshCw, AlertTriangle,
  List, BarChart2, Zap, Search, Download, Upload,
} from "lucide-react";
import { apiFetch } from "../../api/client";

interface Props {
  token: string;
  onAction: (msg: string) => void;
}

interface Container {
  name: string;
  status?: string;
  image?: string;
}

interface ContainersData {
  success: boolean;
  error?: string;
  containers?: Container[];
}

const DB_ACTIONS = [
  {
    label: "Statistiques",
    icon: BarChart2,
    msg: "Affiche les statistiques de la base de données (version, uptime, connexions, cache hit ratio)",
  },
  { label: "Lister les BDD", icon: List, msg: "Liste toutes les bases de données du serveur" },
  { label: "Requêtes lentes", icon: Zap, msg: "Affiche les requêtes SQL lentes en cours d'exécution" },
  { label: "Connexions actives", icon: Search, msg: "Liste les connexions actives à la base de données" },
  { label: "Optimiser", icon: BarChart2, msg: "Optimise la base de données (VACUUM ANALYZE / OPTIMIZE)" },
  { label: "Dump BDD", icon: Download, msg: "Crée un dump de la base de données. Quelle BDD ?" },
  { label: "Restaurer dump", icon: Upload, msg: "Restaure une base de données depuis un fichier de dump" },
];

const DB_TYPES: Record<string, string> = {
  postgres: "PostgreSQL",
  mysql: "MySQL",
  mongo: "MongoDB",
  redis: "Redis",
  mariadb: "MariaDB",
};

function guessDbType(image?: string, name?: string): string | null {
  const s = ((image ?? "") + (name ?? "")).toLowerCase();
  for (const [k, v] of Object.entries(DB_TYPES)) {
    if (s.includes(k)) return v;
  }
  return null;
}

export default function DatabasePanel({ token, onAction }: Props) {
  const [data, setData] = useState<ContainersData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await apiFetch<ContainersData>("/api/containers", token);
      setData(d);
    } catch {
      setData({ success: false, error: "VPS Agent non disponible" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const dbContainers = (data?.containers ?? []).filter(
    c => guessDbType(c.image, c.name) !== null
  );

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Database size={22} style={{ color: "var(--accent)" }} />
          <h2 style={{ margin: 0, fontSize: 18, color: "var(--text)" }}>Bases de données</h2>
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={{
            display: "flex", alignItems: "center", gap: 6, padding: "6px 12px",
            background: "var(--surface2)", border: "1px solid var(--border)",
            borderRadius: 8, color: "var(--text-muted)", cursor: "pointer", fontSize: 13,
          }}
        >
          <RefreshCw size={14} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
          Actualiser
        </button>
      </div>

      {loading && (
        <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 40 }}>
          Détection des conteneurs BDD…
        </div>
      )}

      {!loading && data && !data.success && (
        <div style={{ padding: 16, background: "rgba(239,68,68,.1)", borderRadius: 10, color: "var(--red)" }}>
          <AlertTriangle size={16} style={{ marginRight: 8 }} />
          {data.error}
        </div>
      )}

      {/* Detected DB containers */}
      {!loading && data?.success && (
        <>
          <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
            {dbContainers.length > 0
              ? `${dbContainers.length} conteneur(s) de base de données détecté(s)`
              : "Aucun conteneur de base de données détecté"}
          </div>
          {dbContainers.map((c, i) => {
            const dbType = guessDbType(c.image, c.name);
            const running = c.status?.toLowerCase().includes("up") || c.status?.toLowerCase().includes("running");
            return (
              <div
                key={i}
                style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "14px 16px", background: "var(--surface)",
                  borderRadius: 10, border: "1px solid var(--border)",
                }}
              >
                <Database size={20} style={{ color: "var(--accent)", flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, fontSize: 14, color: "var(--text)" }}>{c.name}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{dbType}</div>
                </div>
                <span style={{
                  display: "flex", alignItems: "center", gap: 5,
                  fontSize: 12, color: running ? "var(--green)" : "var(--red)",
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: running ? "var(--green)" : "var(--red)",
                  }} />
                  {running ? "Actif" : "Arrêté"}
                </span>
                <button
                  onClick={() => onAction(`Affiche les statistiques de la base de données dans le conteneur ${c.name}`)}
                  style={{
                    padding: "4px 10px", background: "var(--surface2)",
                    border: "1px solid var(--border)", borderRadius: 6,
                    color: "var(--text-muted)", cursor: "pointer", fontSize: 12,
                  }}
                >
                  Stats
                </button>
              </div>
            );
          })}
        </>
      )}

      {/* Quick actions */}
      <div style={{ marginTop: dbContainers.length === 0 ? 0 : "auto" }}>
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Actions rapides
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {DB_ACTIONS.map(({ label, icon: Icon, msg }) => (
            <button
              key={label}
              onClick={() => onAction(msg)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "7px 14px", background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: 20, color: "var(--text)", cursor: "pointer", fontSize: 13,
              }}
            >
              <Icon size={14} style={{ color: "var(--accent)" }} />
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
