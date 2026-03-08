import { Package, Circle, Settings } from "lucide-react";

interface Deployment {
  name: string;
  path: string;
  ps_output: string;
}

interface Props {
  deployments: Deployment[];
  loading: boolean;
  onAction: (msg: string) => void;
}

function statusColor(psOutput: string): string {
  if (psOutput.includes("Up") || psOutput.includes("running")) return "var(--green)";
  if (psOutput.includes("Exit") || psOutput.includes("stopped")) return "var(--red)";
  return "var(--text-muted)";
}

function statusLabel(psOutput: string): string {
  if (psOutput.includes("Up")) return "Running";
  if (psOutput.includes("Exit")) return "Stopped";
  if (!psOutput.trim()) return "Unknown";
  return "Running";
}

export default function DeploymentList({ deployments, loading, onAction }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-white">Applications déployées</h3>

      {loading && deployments.length === 0 ? (
        <div
          className="rounded-xl p-6 text-center text-sm"
          style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
        >
          Chargement...
        </div>
      ) : deployments.length === 0 ? (
        <div
          className="rounded-xl p-6 text-center text-sm"
          style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
        >
          <Package size={24} className="mx-auto mb-2" />
          Aucune application déployée.
          <br />
          Demandez à Karl de déployer une app dans le chat.
        </div>
      ) : (
        <div className="space-y-2">
          {deployments.map((dep) => {
            const color = statusColor(dep.ps_output);
            const label = statusLabel(dep.ps_output);
            return (
              <div
                key={dep.name}
                className="rounded-xl px-4 py-3 flex items-center justify-between"
                style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              >
                <div className="flex items-center gap-3">
                  <Package size={16} style={{ color: "var(--text-muted)" }} />
                  <div>
                    <p className="font-medium text-white text-sm">{dep.name}</p>
                    <p className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                      {dep.path}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Circle size={8} fill={color} color={color} />
                    <span style={{ color }}>{label}</span>
                  </div>
                  <button
                    onClick={() => onAction(`Montre-moi le statut et les logs de l'application ${dep.name}.`)}
                    title="Gérer dans le chat"
                    style={{
                      padding: "4px 10px", fontSize: 12, cursor: "pointer",
                      background: "var(--surface2)", border: "1px solid var(--border)",
                      borderRadius: 6, color: "var(--text-muted)",
                      display: "flex", alignItems: "center", gap: 4,
                    }}
                  >
                    <Settings size={12} />
                    Gérer
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
