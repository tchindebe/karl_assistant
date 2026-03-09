import { useEffect, useRef, useState } from "react";
import { Trash2, PanelLeftClose, PanelLeftOpen, Loader2 } from "lucide-react";
import type { useChat } from "../../hooks/useChat";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";
import ConversationList from "./ConversationList";

interface Props {
  chat: ReturnType<typeof useChat>;
  token: string;
}

const SUGGESTIONS = [
  // Monitoring
  "Montre-moi les métriques du serveur",
  "Analyse les logs d'erreur des dernières 24h",
  // Déploiement
  "Liste toutes les applications déployées",
  "Déploie une app Node.js nommée 'mon-api' sur le port 3000",
  // Sécurité
  "Lance un audit de sécurité complet",
  "Montre-moi le statut du firewall",
  // Base de données
  "Sauvegarde toutes les bases de données",
  "Liste les bases de données PostgreSQL",
  // SSL & DNS
  "Vérifie l'expiration de mes certificats SSL",
  "Configure le DNS pour mon-domaine.com",
  // Auto-healing & Optimisation
  "Active l'auto-healing sur tous les services",
  "Optimise les performances du serveur",
  // CRM & Analytics
  "Quels sont mes derniers prospects CRM ?",
  "Montre-moi les analytics de la semaine",
];

export default function ChatWindow({ chat, token }: Props) {
  const {
    messages,
    isLoading,
    isLoadingHistory,
    error,
    sendMessage,
    clearChat,
    conversationId,
    loadConversation,
    refreshTrigger,
  } = chat;

  const bottomRef = useRef<HTMLDivElement>(null);
  const [showHistory, setShowHistory] = useState(true);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelectConversation = (id: number) => {
    loadConversation(id);
  };

  const handleNewChat = () => {
    clearChat();
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Panneau historique ────────────────────────────────────────────── */}
      {showHistory && (
        <ConversationList
          token={token}
          activeId={conversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewChat}
          refreshTrigger={refreshTrigger}
        />
      )}

      {/* ── Zone de chat ─────────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-4 shrink-0"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-3">
            {/* Toggle historique */}
            <button
              onClick={() => setShowHistory((v) => !v)}
              title={showHistory ? "Masquer l'historique" : "Afficher l'historique"}
              className="p-1.5 rounded-lg transition-all"
              style={{ color: "var(--text-muted)" }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = "var(--surface2)";
                (e.currentTarget as HTMLElement).style.color = "var(--text)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
                (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
              }}
            >
              {showHistory ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
            </button>

            <div>
              <h2 className="font-semibold text-white leading-tight">Karl</h2>
              <p className="text-xs leading-tight" style={{ color: "var(--text-muted)" }}>
                {isLoadingHistory
                  ? "Chargement de la conversation…"
                  : isLoading
                  ? "En train de réfléchir..."
                  : "Prêt"}
              </p>
            </div>
          </div>

          {messages.length > 0 && !isLoadingHistory && (
            <button
              onClick={clearChat}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all"
              style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--red)";
                (e.currentTarget as HTMLElement).style.color = "var(--red)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
              }}
            >
              <Trash2 size={14} />
              Effacer
            </button>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {/* Loading history skeleton */}
          {isLoadingHistory && (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <Loader2 size={28} className="animate-spin" style={{ color: "var(--accent)" }} />
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Chargement de la conversation…
              </p>
            </div>
          )}

          {!isLoadingHistory && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
              <div>
                <div
                  className="text-5xl mb-4 p-4 rounded-2xl inline-block"
                  style={{ background: "var(--surface2)" }}
                >
                  🤖
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  Bonjour, je suis Karl
                </h3>
                <p style={{ color: "var(--text-muted)" }}>
                  Votre assistant IA pour gérer votre VPS de A à Z
                </p>
              </div>

              {/* Suggestions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className="px-4 py-3 rounded-xl text-sm text-left transition-all"
                    style={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      color: "var(--text)",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = "var(--accent)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {!isLoadingHistory && messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {error && (
            <div
              className="px-4 py-3 rounded-xl text-sm"
              style={{ background: "#ef44441a", color: "var(--red)", border: "1px solid #ef444430" }}
            >
              ❌ {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <InputBar onSend={sendMessage} disabled={isLoading || isLoadingHistory} />
      </div>
    </div>
  );
}
