import { useEffect, useState } from "react";
import {
  Archive, RefreshCw, AlertTriangle, Plus,
  Download, HardDrive, Database, Settings,
} from "lucide-react";
import { apiFetch } from "../../api/client";

interface Props {
  token: string;
  onAction: (msg: string) => void;
}

interface Backup {
  name: string;
  path?: string;
  size?: number;
  size_mb?: number;
  created_at?: string;
  type?: string;
}

interface BackupsData {
  success?: boolean;
  error?: string;
  backups?: Backup[];
  total_size_mb?: number;
}

function formatSize(bytes?: number, mb?: number): string {
  const totalMb = mb ?? (bytes != null ? bytes / 1024 / 1024 : null);
  if (totalMb == null) return "?";
  if (totalMb < 1) return `${Math.round(totalMb * 1024)} KB`;
  if (totalMb < 1024) return `${totalMb.toFixed(1)} MB`;
  return `${(totalMb / 1024).toFixed(2)} GB`;
}

function typeIcon(type?: string) {
  if (type === "database") return <Database size={14} style={{ color: "var(--accent)" }} />;
  if (type === "config") return <Settings size={14} style={{ color: "var(--yellow)" }} />;
  return <HardDrive size={14} style={{ color: "var(--text-muted)" }} />;
}

const ACTIONS = [
  { label: "Créer une sauvegarde", icon: Plus, msg: "Crée une sauvegarde complète du serveur (volumes + BDD)" },
  { label: "Sauvegarder BDD", icon: Database, msg: "Crée un dump de toutes les bases de données" },
  { label: "Restaurer", icon: Download, msg: "Restaure une sauvegarde. Quel fichier et quelle cible ?" },
  { label: "Nettoyer anciennes", icon: Archive, msg: "Supprime les sauvegardes de plus de 30 jours" },
];

export default function BackupsPanel({ token, onAction }: Props) {
  const [data, setData] = useState<BackupsData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await apiFetch<BackupsData>("/api/backups", token);
      setData(d);
    } catch {
      setData({ success: false, error: "VPS Agent non disponible" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const backups = data?.backups ?? [];

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Archive size={22} style={{ color: "var(--accent)" }} />
          <h2 style={{ margin: 0, fontSize: 18, color: "var(--text)" }}>Sauvegardes</h2>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => onAction("Crée une sauvegarde complète du serveur")}
            style={{
              display: "flex", alignItems: "center", gap: 6, padding: "6px 14px",
              background: "var(--accent)", border: "none",
              borderRadius: 8, color: "#fff", cursor: "pointer", fontSize: 13,
            }}
          >
            <Plus size={14} />
            Nouvelle
          </button>
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
      </div>

      {/* Summary */}
      {!data?.error && data?.total_size_mb != null && (
        <div style={{
          padding: "12px 16px", background: "var(--surface)", borderRadius: 10,
          border: "1px solid var(--border)", display: "flex", gap: 24,
        }}>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--accent)" }}>{backups.length}</div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>sauvegardes</div>
          </div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text)" }}>
              {formatSize(undefined, data.total_size_mb)}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>espace total</div>
          </div>
        </div>
      )}

      {loading && (
        <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 40 }}>
          Chargement des sauvegardes…
        </div>
      )}

      {!loading && data?.error && (
        <div style={{ padding: 16, background: "rgba(239,68,68,.1)", borderRadius: 10, color: "var(--red)" }}>
          <AlertTriangle size={16} style={{ marginRight: 8 }} />
          {data.error ?? "Impossible de charger les sauvegardes"}
        </div>
      )}

      {!loading && !data?.error && backups.length === 0 && (
        <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 32 }}>
          Aucune sauvegarde disponible.
        </div>
      )}

      {/* List */}
      {!loading && !data?.error && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {backups.map((b, i) => (
            <div
              key={i}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "12px 16px", background: "var(--surface)",
                borderRadius: 10, border: "1px solid var(--border)",
              }}
            >
              {typeIcon(b.type)}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontWeight: 500, fontSize: 13, color: "var(--text)",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {b.name}
                </div>
                {b.created_at && (
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                    {b.created_at}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
                <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  {formatSize(b.size, b.size_mb)}
                </span>
                <button
                  onClick={() => onAction(`Restaure la sauvegarde ${b.name}`)}
                  style={{
                    padding: "4px 10px", background: "var(--surface2)",
                    border: "1px solid var(--border)", borderRadius: 6,
                    color: "var(--text-muted)", cursor: "pointer", fontSize: 12,
                  }}
                >
                  Restaurer
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Quick actions */}
      <div style={{ marginTop: "auto" }}>
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Actions rapides
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {ACTIONS.map(({ label, icon: Icon, msg }) => (
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
