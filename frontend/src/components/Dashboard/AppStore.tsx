import { useState } from "react";
import { Package, Search, ExternalLink } from "lucide-react";

interface Props {
  token: string;
  onAction: (msg: string) => void;
}

interface App {
  name: string;
  description: string;
  category: string;
  emoji: string;
  installMsg: string;
  url?: string;
}

const APPS: App[] = [
  // CMS / Blog
  {
    name: "WordPress",
    description: "CMS le plus populaire au monde",
    category: "CMS",
    emoji: "🌐",
    installMsg: "Installe WordPress. Mon domaine est [à préciser].",
  },
  {
    name: "Ghost",
    description: "Plateforme de blog moderne et rapide",
    category: "CMS",
    emoji: "👻",
    installMsg: "Installe Ghost. Mon domaine est [à préciser].",
  },
  // Cloud / Fichiers
  {
    name: "Nextcloud",
    description: "Cloud personnel — fichiers, calendrier, contacts",
    category: "Cloud",
    emoji: "☁️",
    installMsg: "Installe Nextcloud. Mon domaine est [à préciser].",
  },
  // Automatisation
  {
    name: "n8n",
    description: "Automatisation de workflows (alternative Zapier)",
    category: "Automatisation",
    emoji: "⚡",
    installMsg: "Installe n8n. Mon domaine est [à préciser].",
  },
  // Dev / Git
  {
    name: "Gitea",
    description: "Hébergement Git auto-hébergé léger",
    category: "Dev",
    emoji: "🐙",
    installMsg: "Installe Gitea. Mon domaine est [à préciser].",
  },
  {
    name: "GitLab CE",
    description: "Plateforme DevOps complète",
    category: "Dev",
    emoji: "🦊",
    installMsg: "Installe GitLab CE. Mon domaine est [à préciser].",
  },
  // Monitoring
  {
    name: "Uptime Kuma",
    description: "Monitoring de disponibilité avec alertes",
    category: "Monitoring",
    emoji: "📡",
    installMsg: "Installe Uptime Kuma. Mon domaine est [à préciser].",
  },
  {
    name: "Grafana",
    description: "Dashboards de métriques et visualisation",
    category: "Monitoring",
    emoji: "📊",
    installMsg: "Installe Grafana. Mon domaine est [à préciser].",
  },
  // Communication
  {
    name: "Mattermost",
    description: "Messagerie d'équipe self-hosted (Slack alternatif)",
    category: "Communication",
    emoji: "💬",
    installMsg: "Installe Mattermost. Mon domaine est [à préciser].",
  },
  // Analytics
  {
    name: "Plausible",
    description: "Analytics web respectueux de la vie privée",
    category: "Analytics",
    emoji: "📈",
    installMsg: "Installe Plausible Analytics. Mon domaine est [à préciser].",
  },
  {
    name: "Umami",
    description: "Analytics simple et léger open-source",
    category: "Analytics",
    emoji: "🍵",
    installMsg: "Installe Umami. Mon domaine est [à préciser].",
  },
  // Gestion
  {
    name: "Portainer",
    description: "Interface web pour gérer Docker",
    category: "Infra",
    emoji: "🐳",
    installMsg: "Installe Portainer. Mon domaine est [à préciser].",
  },
  {
    name: "Vaultwarden",
    description: "Gestionnaire de mots de passe (Bitwarden)",
    category: "Sécurité",
    emoji: "🔐",
    installMsg: "Installe Vaultwarden. Mon domaine est [à préciser].",
  },
  {
    name: "Penpot",
    description: "Outil de design UI/UX open-source",
    category: "Design",
    emoji: "🎨",
    installMsg: "Installe Penpot. Mon domaine est [à préciser].",
  },
  {
    name: "Monica",
    description: "CRM personnel — gestion des relations",
    category: "CRM",
    emoji: "👥",
    installMsg: "Installe Monica CRM. Mon domaine est [à préciser].",
  },
  {
    name: "Outline",
    description: "Wiki d'équipe moderne et collaboratif",
    category: "Docs",
    emoji: "📝",
    installMsg: "Installe Outline Wiki. Mon domaine est [à préciser].",
  },
];

const CATEGORIES = ["Tous", ...Array.from(new Set(APPS.map(a => a.category)))];

export default function AppStore({ onAction }: Props) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("Tous");

  const filtered = APPS.filter(a => {
    const matchCat = category === "Tous" || a.category === category;
    const matchSearch = a.name.toLowerCase().includes(search.toLowerCase())
      || a.description.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Package size={22} style={{ color: "var(--accent)" }} />
        <h2 style={{ margin: 0, fontSize: 18, color: "var(--text)" }}>App Store</h2>
        <span style={{
          marginLeft: 4, fontSize: 12, padding: "2px 8px",
          background: "var(--surface2)", borderRadius: 10, color: "var(--text-muted)",
        }}>
          {APPS.length} apps
        </span>
      </div>

      {/* Search */}
      <div style={{ position: "relative" }}>
        <Search size={16} style={{
          position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)",
          color: "var(--text-muted)",
        }} />
        <input
          type="text"
          placeholder="Rechercher une application…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: "100%", padding: "10px 12px 10px 36px",
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, color: "var(--text)", fontSize: 14,
            outline: "none", boxSizing: "border-box",
          }}
        />
      </div>

      {/* Category pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            style={{
              padding: "5px 12px", borderRadius: 20, fontSize: 13, cursor: "pointer",
              background: category === cat ? "var(--accent)" : "var(--surface)",
              color: category === cat ? "#fff" : "var(--text-muted)",
              border: category === cat ? "none" : "1px solid var(--border)",
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Apps grid */}
      {filtered.length === 0 && (
        <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 32 }}>
          Aucune application trouvée.
        </div>
      )}

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        gap: 14,
      }}>
        {filtered.map(app => (
          <div
            key={app.name}
            style={{
              padding: 16, background: "var(--surface)",
              borderRadius: 12, border: "1px solid var(--border)",
              display: "flex", flexDirection: "column", gap: 10,
              transition: "border-color 0.15s",
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--accent)")}
            onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 28 }}>{app.emoji}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text)" }}>{app.name}</div>
                <span style={{
                  fontSize: 11, padding: "1px 7px",
                  background: "var(--surface2)", borderRadius: 8,
                  color: "var(--text-muted)",
                }}>
                  {app.category}
                </span>
              </div>
            </div>

            <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)", lineHeight: 1.5 }}>
              {app.description}
            </p>

            <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
              <button
                onClick={() => onAction(`Installe l'application ${app.name} sur le serveur.`)}
                style={{
                  flex: 1, padding: "8px 0",
                  background: "var(--accent)", border: "none",
                  borderRadius: 8, color: "#fff",
                  cursor: "pointer", fontSize: 13, fontWeight: 500,
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                }}
              >
                <Package size={14} />
                Installer
              </button>
              {app.url && (
                <a
                  href={app.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    padding: "8px 10px", background: "var(--surface2)",
                    border: "1px solid var(--border)", borderRadius: 8,
                    color: "var(--text-muted)", textDecoration: "none",
                    display: "flex", alignItems: "center",
                  }}
                >
                  <ExternalLink size={14} />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
