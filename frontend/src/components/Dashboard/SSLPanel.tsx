import { useEffect, useState } from "react";
import {
  Globe, RefreshCw, AlertTriangle, CheckCircle,
  Clock, XCircle, RotateCcw, Search, Trash2,
} from "lucide-react";
import { apiFetch } from "../../api/client";

interface Props {
  token: string;
  onAction: (msg: string) => void;
}

interface SSLCert {
  name?: string;
  domains: string | string[];
  expiry?: string;
  expiry_date?: string;
  days_left?: number;
  days_remaining?: number;
  status?: string;
}

interface SSLData {
  success?: boolean;
  error?: string;
  certificates?: SSLCert[];
  alerts?: SSLCert[];
  total?: number;
}

function normalizeCert(c: SSLCert) {
  return {
    label: Array.isArray(c.domains) ? c.domains.join(", ") : (c.domains ?? c.name ?? ""),
    expiry: c.expiry_date ?? c.expiry,
    days: c.days_remaining ?? c.days_left,
    status: c.status,
  };
}

function StatusIcon({ days }: { days?: number }) {
  if (days === undefined) return <Clock size={16} style={{ color: "var(--text-muted)" }} />;
  if (days < 0) return <XCircle size={16} style={{ color: "var(--red)" }} />;
  if (days < 7) return <AlertTriangle size={16} style={{ color: "var(--red)" }} />;
  if (days < 30) return <AlertTriangle size={16} style={{ color: "var(--yellow)" }} />;
  return <CheckCircle size={16} style={{ color: "var(--green)" }} />;
}

function statusColor(days?: number) {
  if (days === undefined) return "var(--text-muted)";
  if (days < 7) return "var(--red)";
  if (days < 30) return "var(--yellow)";
  return "var(--green)";
}

const ACTIONS = [
  { label: "Renouveler tous", icon: RotateCcw, msg: "Renouvelle tous les certificats SSL arrivant à expiration" },
  { label: "Vérifier un domaine", icon: Search, msg: "Vérifie le certificat SSL du domaine : " },
  { label: "Activer SSL", icon: Globe, msg: "Active le SSL Let's Encrypt pour le domaine : " },
  { label: "Révoquer", icon: Trash2, msg: "Révoque le certificat SSL du domaine : " },
];

export default function SSLPanel({ token, onAction }: Props) {
  const [data, setData] = useState<SSLData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await apiFetch<SSLData>("/api/ssl", token);
      setData(d);
    } catch {
      setData({ success: false, error: "VPS Agent non disponible" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const certs = (data?.certificates ?? []).map(normalizeCert);
  const expiring = certs.filter(c => (c.days ?? 999) < 30);

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Globe size={22} style={{ color: "var(--accent)" }} />
          <h2 style={{ margin: 0, fontSize: 18, color: "var(--text)" }}>SSL & Domaines</h2>
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
          Chargement des certificats…
        </div>
      )}

      {!loading && data?.error && (
        <div style={{ padding: 16, background: "rgba(239,68,68,.1)", borderRadius: 10, color: "var(--red)" }}>
          <AlertTriangle size={16} style={{ marginRight: 8 }} />
          {data.error}
        </div>
      )}

      {!loading && expiring.length > 0 && (
        <div style={{
          padding: 14, background: "rgba(234,179,8,.1)", borderRadius: 10,
          border: "1px solid rgba(234,179,8,.3)", display: "flex", alignItems: "center", gap: 10,
        }}>
          <AlertTriangle size={16} style={{ color: "var(--yellow)" }} />
          <span style={{ color: "var(--yellow)", fontSize: 14 }}>
            {expiring.length} certificat{expiring.length > 1 ? "s" : ""} expirant bientôt
          </span>
          <button
            onClick={() => onAction("Renouvelle tous les certificats SSL arrivant à expiration")}
            style={{
              marginLeft: "auto", padding: "4px 12px", background: "var(--yellow)",
              color: "#000", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 600,
            }}
          >
            Renouveler
          </button>
        </div>
      )}

      {/* Certs list */}
      {!loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {certs.length === 0 && !data?.error && (
            <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 32 }}>
              Aucun certificat SSL installé.
            </div>
          )}
          {certs.map((cert, i) => (
            <div
              key={i}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "14px 16px", background: "var(--surface)",
                borderRadius: 10, border: "1px solid var(--border)",
              }}
            >
              <StatusIcon days={cert.days} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, fontSize: 14, color: "var(--text)" }}>
                  {cert.label}
                </div>
                {cert.expiry && (
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                    Expire le {cert.expiry}
                  </div>
                )}
              </div>
              {cert.days !== undefined && (
                <span style={{
                  fontSize: 13, fontWeight: 600,
                  color: statusColor(cert.days),
                }}>
                  {cert.days < 0 ? "Expiré" : `${cert.days}j`}
                </span>
              )}
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
