import { useState } from "react";
import {
  Terminal, LayoutDashboard, LogOut, MessageSquare,
  Shield, Globe, Database, Archive, Package,
} from "lucide-react";
import { useChat } from "../hooks/useChat";
import ChatWindow from "./Chat/ChatWindow";
import Dashboard from "./Dashboard/Dashboard";
import SecurityPanel from "./Dashboard/SecurityPanel";
import SSLPanel from "./Dashboard/SSLPanel";
import DatabasePanel from "./Dashboard/DatabasePanel";
import BackupsPanel from "./Dashboard/BackupsPanel";
import AppStore from "./Dashboard/AppStore";

interface Props {
  token: string;
  onLogout: () => void;
}

type Tab = "chat" | "overview" | "security" | "ssl" | "databases" | "backups" | "appstore";

const NAV: { id: Tab; icon: React.ReactNode; label: string }[] = [
  { id: "chat",     icon: <MessageSquare size={20} />,   label: "Chat" },
  { id: "overview", icon: <LayoutDashboard size={20} />, label: "Aperçu" },
  { id: "security", icon: <Shield size={20} />,          label: "Sécurité" },
  { id: "ssl",      icon: <Globe size={20} />,           label: "SSL & DNS" },
  { id: "databases",icon: <Database size={20} />,        label: "Bases de données" },
  { id: "backups",  icon: <Archive size={20} />,         label: "Sauvegardes" },
  { id: "appstore", icon: <Package size={20} />,         label: "App Store" },
];

export default function Layout({ token, onLogout }: Props) {
  const [tab, setTab] = useState<Tab>("chat");
  const chat = useChat(token);

  /** Switch to Chat and send (or pre-fill) a message */
  const handleAction = (msg: string) => {
    setTab("chat");
    chat.sendMessage(msg);
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      <aside
        className="flex flex-col w-16 shrink-0 py-4 items-center gap-1"
        style={{ background: "var(--surface)", borderRight: "1px solid var(--border)" }}
      >
        {/* Logo */}
        <div className="p-2 rounded-xl mb-3" style={{ background: "var(--accent)" }}>
          <Terminal size={20} color="white" />
        </div>

        {/* Nav items */}
        {NAV.map(({ id, icon, label }) => (
          <NavBtn
            key={id}
            icon={icon}
            label={label}
            active={tab === id}
            onClick={() => setTab(id)}
          />
        ))}

        {/* Logout */}
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

      {/* ── Main content ────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {tab === "chat"      && <ChatWindow chat={chat} />}
        {tab === "overview"  && <Dashboard token={token} onAction={handleAction} />}
        {tab === "security"  && <SecurityPanel token={token} onAction={handleAction} />}
        {tab === "ssl"       && <SSLPanel token={token} onAction={handleAction} />}
        {tab === "databases" && <DatabasePanel token={token} onAction={handleAction} />}
        {tab === "backups"   && <BackupsPanel token={token} onAction={handleAction} />}
        {tab === "appstore"  && <AppStore token={token} onAction={handleAction} />}
      </main>
    </div>
  );
}

function NavBtn({
  icon, label, active, onClick,
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
