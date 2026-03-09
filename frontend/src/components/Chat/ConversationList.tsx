import { useEffect, useState, useRef } from "react";
import { Plus, Trash2, Pencil, Check, X, MessageSquare } from "lucide-react";

interface ConvItem {
  id: number;
  title: string;
  updated_at: string | null;
}

interface Props {
  token: string;
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  /** Incrémenter pour forcer un refresh de la liste */
  refreshTrigger: number;
}

function relativeDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 1) return "À l'instant";
  if (diffMins < 60) return `${diffMins}m`;
  const diffH = Math.floor(diffMins / 60);
  if (diffH < 24) return `${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `${diffD}j`;
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

export default function ConversationList({
  token,
  activeId,
  onSelect,
  onNew,
  refreshTrigger,
}: Props) {
  const [convs, setConvs] = useState<ConvItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hovered, setHovered] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchConvs = async () => {
    try {
      const res = await fetch("/api/conversations?limit=50", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      setConvs(data.conversations ?? []);
    } catch {
      // silently ignore
    } finally {
      setLoading(false);
    }
  };

  // Refresh quand refreshTrigger change (après chaque échange) ou au montage
  useEffect(() => {
    fetchConvs();
  }, [refreshTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await fetch(`/api/conversations/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      setConvs((prev) => prev.filter((c) => c.id !== id));
      // Si on supprime la conv active → revenir à nouveau chat
      if (activeId === id) onNew();
    } catch {
      // silently ignore
    }
  };

  const startEdit = (e: React.MouseEvent, conv: ConvItem) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
    setTimeout(() => inputRef.current?.select(), 50);
  };

  const confirmEdit = async (id: number) => {
    const title = editTitle.trim();
    if (!title) {
      setEditingId(null);
      return;
    }
    try {
      await fetch(`/api/conversations/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title }),
      });
      setConvs((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title } : c))
      );
    } catch {
      // silently ignore
    } finally {
      setEditingId(null);
    }
  };

  const cancelEdit = () => setEditingId(null);

  return (
    <div
      style={{
        width: 260,
        minWidth: 260,
        display: "flex",
        flexDirection: "column",
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 12px 8px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        <button
          onClick={onNew}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "100%",
            padding: "8px 12px",
            background: "var(--accent)",
            border: "none",
            borderRadius: 8,
            color: "white",
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 500,
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "0.85";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "1";
          }}
        >
          <Plus size={15} />
          Nouvelle conversation
        </button>
      </div>

      {/* Liste */}
      <div style={{ flex: 1, overflowY: "auto", padding: "6px 6px" }}>
        {loading && (
          <div
            style={{
              padding: "24px 12px",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: 13,
            }}
          >
            Chargement…
          </div>
        )}

        {!loading && convs.length === 0 && (
          <div
            style={{
              padding: "32px 12px",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: 13,
            }}
          >
            <MessageSquare size={28} style={{ margin: "0 auto 8px", opacity: 0.4 }} />
            Aucune conversation
          </div>
        )}

        {convs.map((conv) => {
          const isActive = conv.id === activeId;
          const isEditing = editingId === conv.id;

          return (
            <div
              key={conv.id}
              onClick={() => !isEditing && onSelect(conv.id)}
              onMouseEnter={() => setHovered(conv.id)}
              onMouseLeave={() => setHovered(null)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "7px 10px",
                borderRadius: 8,
                cursor: isEditing ? "default" : "pointer",
                background: isActive
                  ? "var(--accent)"
                  : hovered === conv.id
                  ? "var(--surface2)"
                  : "transparent",
                marginBottom: 2,
              }}
            >
              {/* Contenu principal */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {isEditing ? (
                  <input
                    ref={inputRef}
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") confirmEdit(conv.id);
                      if (e.key === "Escape") cancelEdit();
                    }}
                    onClick={(e) => e.stopPropagation()}
                    autoFocus
                    style={{
                      width: "100%",
                      background: "var(--bg)",
                      border: "1px solid var(--accent)",
                      borderRadius: 4,
                      color: "var(--text)",
                      fontSize: 13,
                      padding: "2px 6px",
                      outline: "none",
                    }}
                  />
                ) : (
                  <>
                    <div
                      style={{
                        fontSize: 13,
                        color: isActive ? "white" : "var(--text)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        lineHeight: 1.4,
                      }}
                    >
                      {conv.title}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: isActive ? "rgba(255,255,255,0.65)" : "var(--text-muted)",
                        marginTop: 1,
                      }}
                    >
                      {relativeDate(conv.updated_at)}
                    </div>
                  </>
                )}
              </div>

              {/* Actions (visibles au hover ou en mode édition) */}
              {(hovered === conv.id || isActive || isEditing) && (
                <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
                  {isEditing ? (
                    <>
                      <ActionBtn
                        icon={<Check size={13} />}
                        onClick={(e) => { e.stopPropagation(); confirmEdit(conv.id); }}
                        color="var(--green)"
                        title="Valider"
                      />
                      <ActionBtn
                        icon={<X size={13} />}
                        onClick={(e) => { e.stopPropagation(); cancelEdit(); }}
                        color="var(--red)"
                        title="Annuler"
                      />
                    </>
                  ) : (
                    <>
                      <ActionBtn
                        icon={<Pencil size={13} />}
                        onClick={(e) => startEdit(e, conv)}
                        color={isActive ? "rgba(255,255,255,0.7)" : "var(--text-muted)"}
                        title="Renommer"
                      />
                      <ActionBtn
                        icon={<Trash2 size={13} />}
                        onClick={(e) => handleDelete(e, conv.id)}
                        color={isActive ? "rgba(255,255,255,0.7)" : "var(--text-muted)"}
                        hoverColor="var(--red)"
                        title="Supprimer"
                      />
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ActionBtn({
  icon,
  onClick,
  color,
  hoverColor,
  title,
}: {
  icon: React.ReactNode;
  onClick: (e: React.MouseEvent) => void;
  color: string;
  hoverColor?: string;
  title?: string;
}) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      title={title}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: "transparent",
        border: "none",
        cursor: "pointer",
        padding: "3px 4px",
        borderRadius: 4,
        color: hov && hoverColor ? hoverColor : color,
        display: "flex",
        alignItems: "center",
      }}
    >
      {icon}
    </button>
  );
}
