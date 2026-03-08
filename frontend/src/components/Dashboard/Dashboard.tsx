import { useEffect, useState } from "react";
import axios from "axios";
import MetricsPanel from "./MetricsPanel";
import DeploymentList from "./DeploymentList";
import { RefreshCw } from "lucide-react";

interface Props {
  token: string;
}

export default function Dashboard({ token }: Props) {
  const [metrics, setMetrics] = useState<any>(null);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [metricsResp, deploymentsResp] = await Promise.all([
        axios.get("/api/metrics", { headers }).catch(() => ({ data: null })),
        axios.get("/api/deployments", { headers }).catch(() => ({ data: { deployments: [] } })),
      ]);
      setMetrics(metricsResp.data);
      setDeployments(deploymentsResp.data?.deployments ?? []);
      setLastUpdate(new Date());
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10_000); // Refresh toutes les 10s
    return () => clearInterval(interval);
  }, [token]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 shrink-0"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div>
          <h2 className="font-semibold text-white">Dashboard</h2>
          {lastUpdate && (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Dernière mise à jour: {lastUpdate.toLocaleTimeString()}
            </p>
          )}
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all"
          style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Rafraîchir
        </button>
      </div>

      {/* Contenu */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {metrics ? (
          <MetricsPanel metrics={metrics} />
        ) : (
          <div
            className="rounded-xl p-6 text-center"
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
          >
            {loading ? "Chargement des métriques..." : "VPS Agent non disponible"}
          </div>
        )}

        <DeploymentList deployments={deployments} loading={loading} />
      </div>
    </div>
  );
}
