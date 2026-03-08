import { useState } from "react";
import { Terminal, LayoutDashboard, LogOut, MessageSquare } from "lucide-react";
import ChatWindow from "./Chat/ChatWindow";
import Dashboard from "./Dashboard/Dashboard";

interface Props {
  token: string;
  onLogout: () => void;
}

type Tab = "chat" | "dashboard";

export default function Layout({ token, onLogout }: Props) {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      <aside
        className="flex flex-col w-16 shrink-0 py-4 items-center gap-4"
        style={{ background: "var(--surface)", borderRight: "1px solid var(--border)" }}
      >
        {/* Logo */}
        <div className="p-2 rounded-xl mb-2" style={{ background: "var(--accent)" }}>
          <Terminal size={20} color="white" />
        </div>

        {/* Nav */}
        <NavBtn
          icon={<MessageSquare size={20} />}
          label="Chat"
          active={tab === "chat"}
          onClick={() => setTab("chat")}
        />
        <NavBtn
          icon={<LayoutDashboard size={20} />}
          label="Dashboard"
          active={tab === "dashboard"}
          onClick={() => setTab("dashboard")}
        />

        {/* Logout en bas */}
        <div className="mt-auto">
          <button
            onClick={onLogout}
            title="Se déconnecter"
            className="p-3 rounded-xl transition-all"
            style={{ color: "var(--text-muted)" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = "var(--surface2)";
              (e.currentTarget as HTMLElement).style.color = "var(--red)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
              (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
            }}
          >
            <LogOut size={20} />
          </button>
        </div>
      </aside>

      {/* ── Contenu principal ───────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {tab === "chat" && <ChatWindow token={token} />}
        {tab === "dashboard" && <Dashboard token={token} />}
      </main>
    </div>
  );
}

function NavBtn({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className="p-3 rounded-xl transition-all"
      style={{
        background: active ? "var(--accent)" : "transparent",
        color: active ? "white" : "var(--text-muted)",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          (e.currentTarget as HTMLElement).style.background = "var(--surface2)";
          (e.currentTarget as HTMLElement).style.color = "var(--text)";
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          (e.currentTarget as HTMLElement).style.background = "transparent";
          (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
        }
      }}
    >
      {icon}
    </button>
  );
}
