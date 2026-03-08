import { Cpu, HardDrive, MemoryStick, Wifi, Clock } from "lucide-react";

interface Props {
  metrics: any;
}

function MetricCard({
  icon,
  label,
  value,
  sub,
  percent,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  percent?: number;
  color: string;
}) {
  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-3"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
          {icon}
          <span className="text-sm">{label}</span>
        </div>
        <span className="font-bold text-white text-lg">{value}</span>
      </div>
      {percent !== undefined && (
        <div className="w-full rounded-full h-1.5" style={{ background: "var(--surface2)" }}>
          <div
            className="h-1.5 rounded-full transition-all"
            style={{
              width: `${Math.min(percent, 100)}%`,
              background: color,
            }}
          />
        </div>
      )}
      {sub && <p className="text-xs" style={{ color: "var(--text-muted)" }}>{sub}</p>}
    </div>
  );
}

export default function MetricsPanel({ metrics }: Props) {
  if (!metrics) return null;

  const cpuColor =
    metrics.cpu?.percent > 80
      ? "var(--red)"
      : metrics.cpu?.percent > 60
      ? "var(--yellow)"
      : "var(--green)";

  const memColor =
    metrics.memory?.percent > 85
      ? "var(--red)"
      : metrics.memory?.percent > 70
      ? "var(--yellow)"
      : "var(--green)";

  const diskColor =
    metrics.disk?.percent > 90
      ? "var(--red)"
      : metrics.disk?.percent > 75
      ? "var(--yellow)"
      : "var(--green)";

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-white">Métriques Serveur</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <MetricCard
          icon={<Cpu size={16} />}
          label="CPU"
          value={`${metrics.cpu?.percent ?? "?"}%`}
          sub={`${metrics.cpu?.count ?? "?"} cores`}
          percent={metrics.cpu?.percent}
          color={cpuColor}
        />
        <MetricCard
          icon={<MemoryStick size={16} />}
          label="RAM"
          value={`${metrics.memory?.percent ?? "?"}%`}
          sub={`${metrics.memory?.used_gb ?? "?"} / ${metrics.memory?.total_gb ?? "?"} GB`}
          percent={metrics.memory?.percent}
          color={memColor}
        />
        <MetricCard
          icon={<HardDrive size={16} />}
          label="Disque"
          value={`${metrics.disk?.percent ?? "?"}%`}
          sub={`${metrics.disk?.used_gb ?? "?"} / ${metrics.disk?.total_gb ?? "?"} GB`}
          percent={metrics.disk?.percent}
          color={diskColor}
        />
        <MetricCard
          icon={<Clock size={16} />}
          label="Uptime"
          value={metrics.uptime?.human ?? "?"}
          sub={`Boot: ${metrics.uptime?.boot_time ? new Date(metrics.uptime.boot_time).toLocaleDateString() : "?"}`}
          color="var(--accent)"
        />
      </div>

      {/* Réseau */}
      <div
        className="rounded-xl p-4 flex gap-6"
        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <Wifi size={16} style={{ color: "var(--text-muted)" }} />
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Réseau</span>
        </div>
        <div className="flex gap-6 text-sm">
          <span>
            <span style={{ color: "var(--text-muted)" }}>↑ </span>
            <span className="text-white font-medium">{metrics.network?.bytes_sent_mb ?? "?"} MB</span>
          </span>
          <span>
            <span style={{ color: "var(--text-muted)" }}>↓ </span>
            <span className="text-white font-medium">{metrics.network?.bytes_recv_mb ?? "?"} MB</span>
          </span>
        </div>
      </div>

      {/* Top processus */}
      {metrics.top_processes && metrics.top_processes.length > 0 && (
        <div
          className="rounded-xl p-4"
          style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        >
          <h4 className="text-sm font-medium mb-3" style={{ color: "var(--text-muted)" }}>
            Top Processus
          </h4>
          <div className="space-y-2">
            {metrics.top_processes.map((proc: any, i: number) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-white font-mono truncate max-w-[200px]">
                  {proc.name ?? "?"}
                </span>
                <div className="flex gap-4 shrink-0">
                  <span style={{ color: "var(--text-muted)" }}>
                    CPU: <span className="text-white">{(proc.cpu_percent ?? 0).toFixed(1)}%</span>
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>
                    RAM: <span className="text-white">{(proc.memory_percent ?? 0).toFixed(1)}%</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
