import { useEffect, useState } from "react";
import {
  Shield, ShieldAlert, ShieldCheck, AlertTriangle,
  RefreshCw, Zap, Lock, Bug, Server,
} from "lucide-react";
import { apiFetch } from "../../api/client";

interface Props {
  token: string;
  onAction: (msg: string) => void;
}

interface SecurityData {
  success: boolean;
  error?: string;
  ssh_config?: { password_auth?: string; permit_root?: string };
  open_ports?: { port: number; service?: string }[];
  system_updates?: { available?: number; security?: number };
  docker_security?: { privileged_containers?: string[] };
  failed_logins?: { count?: number };
  fail2ban?: { installed?: boolean; active?: boolean };
}

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? "var(--green)" : score >= 60 ? "var(--yellow)" : "var(--red)";
  return (
    <div style={{
      width: 80, height: 80, borderRadius: "50%",
      border: `4px solid ${color}`,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
    }}>
      <span style={{ fontSize: 24, fontWeight: 700, color }}>{score}</span>
      <span style={{ fontSize: 10, color: "var(--text-muted)" }}>/100</span>
    </div>
  );
}

function CheckRow({ ok, label, detail }: { ok: boolean; label: string; detail?: string }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      padding: "8px 12px", borderRadius: 8,
      background: ok ? "rgba(34,197,94,.08)" : "rgba(239,68,68,.08)",
    }}>
      {ok
        ? <ShieldCheck size={16} style={{ color: "var(--green)", flexShrink: 0 }} />
        : <ShieldAlert size={16} style={{ color: "var(--red)", flexShrink: 0 }} />}
      <span style={{ flex: 1, fontSize: 14, color: "var(--text)" }}>{label}</span>
      {detail && <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{detail}</span>}
    </div>
  );
}

const ACTIONS = [
  { label: "Audit complet", icon: Shield, msg: "Lance un audit de sécurité complet du serveur" },
  { label: "Durcir SSH", icon: Lock, msg: "Durcis la configuration SSH du serveur" },
  { label: "Fail2ban", icon: Zap, msg: "Installe et configure Fail2ban sur le serveur" },
  { label: "Scanner malwares", icon: Bug, msg: "Lance un scan de malwares sur le système" },
  { label: "Ports ouverts", icon: Server, msg: "Liste tous les ports ouverts sur le serveur" },
];

export default function SecurityPanel({ token, onAction }: Props) {
  const [data, setData] = useState<SecurityData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await apiFetch<SecurityData>("/api/security/status", token);
      setData(d);
    } catch {
      setData({ success: false, error: "VPS Agent non disponible" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const checks = data && data.success
    ? [
        {
          ok: data.ssh_config?.password_auth === "no",
          label: "Authentification SSH par clé uniquement",
          detail: data.ssh_config?.password_auth === "no" ? "Activé" : "Mot de passe autorisé ⚠️",
        },
        {
          ok: data.ssh_config?.permit_root === "no",
          label: "Connexion root SSH désactivée",
          detail: data.ssh_config?.permit_root === "no" ? "Désactivé" : "Autorisé ⚠️",
        },
        {
          ok: (data.system_updates?.security ?? 0) === 0,
          label: "Mises à jour de sécurité",
          detail: `${data.system_updates?.available ?? "?"} disponibles`,
        },
        {
          ok: (data.docker_security?.privileged_containers?.length ?? 0) === 0,
          label: "Pas de conteneurs Docker privilégiés",
          detail: `${data.docker_security?.privileged_containers?.length ?? 0} détectés`,
        },
        {
          ok: (data.failed_logins?.count ?? 0) < 20,
          label: "Connexions échouées (24h)",
          detail: `${data.failed_logins?.count ?? "?"} tentatives`,
        },
        {
          ok: data.fail2ban?.active === true,
          label: "Fail2ban actif",
          detail: data.fail2ban?.active ? "En cours" : "Inactif",
        },
      ]
    : [];

  const score = checks.length > 0
    ? Math.round((checks.filter(c => c.ok).length / checks.length) * 100)
    : 0;

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Shield size={22} style={{ color: "var(--accent)" }} />
          <h2 style={{ margin: 0, fontSize: 18, color: "var(--text)" }}>Sécurité</h2>
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
          Chargement de l'audit…
        </div>
      )}

      {!loading && data && !data.success && (
        <div style={{ padding: 16, background: "rgba(239,68,68,.1)", borderRadius: 10, color: "var(--red)" }}>
          <AlertTriangle size={16} style={{ marginRight: 8 }} />
          {data.error ?? "Impossible de contacter le VPS Agent"}
        </div>
      )}

      {!loading && data?.success && (
        <>
          {/* Score */}
          <div style={{
            display: "flex", alignItems: "center", gap: 20,
            padding: 20, background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)",
          }}>
            <ScoreBadge score={score} />
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>
                Score de sécurité
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
                {checks.filter(c => c.ok).length}/{checks.length} contrôles passés
              </div>
            </div>
          </div>

          {/* Checks */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {checks.map((c, i) => (
              <CheckRow key={i} ok={c.ok} label={c.label} detail={c.detail} />
            ))}
          </div>
        </>
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
