import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  ListChecks,
  CalendarDays,
  Image,
  Users,
  Tags,
  BarChart3,
  KeyRound,
  Webhook,
  Settings,
  Search,
  Bell,
  GitBranch,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import clsx from "clsx";

const NAV = [
  { label: "Overview", items: [{ to: "/", icon: LayoutDashboard, label: "Dashboard" }] },
  {
    label: "Editorial",
    items: [
      { to: "/entries", icon: FileText, label: "Content" },
      { to: "/queues", icon: ListChecks, label: "Queues" },
      { to: "/workflow", icon: GitBranch, label: "Workflow" },
      { to: "/calendar", icon: CalendarDays, label: "Calendar" },
    ],
  },
  {
    label: "Library",
    items: [
      { to: "/media", icon: Image, label: "Media" },
      { to: "/authors", icon: Users, label: "Authors" },
      { to: "/taxonomies", icon: Tags, label: "Taxonomies" },
    ],
  },
  {
    label: "Insights & API",
    items: [
      { to: "/analytics", icon: BarChart3, label: "Analytics" },
      { to: "/api-keys", icon: KeyRound, label: "API Keys" },
      { to: "/webhooks", icon: Webhook, label: "Webhooks" },
      { to: "/settings", icon: Settings, label: "Settings" },
    ],
  },
];

export function AppLayout() {
  const { user, organization, publication, publications, setPublication, logout } = useAuthStore();
  const { sidebarCollapsed, globalSearch, setGlobalSearch, notifications } = useUiStore();
  const unread = notifications.length;

  return (
    <div className={clsx("app-shell", sidebarCollapsed && "collapsed")}>
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">QuillStack</span>
          {!sidebarCollapsed && <span className="brand-sub">Editorial</span>}
        </div>
        {NAV.map((section) => (
          <div className="nav-section" key={section.label}>
            {!sidebarCollapsed && <div className="nav-label">{section.label}</div>}
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => clsx("nav-link", !isActive && "active")}
              >
                <item.icon size={18} />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
        <div style={{ marginTop: "auto", padding: "0.5rem 0.7rem", color: "var(--sidebar-muted)", fontSize: "0.8rem" }}>
          {!sidebarCollapsed && (
            <>
              <div>{organization?.name}</div>
              <div style={{ marginTop: 4 }}>{user?.email}</div>
              <button className="btn ghost" style={{ marginTop: 8, color: "var(--sidebar-text)" }} onClick={logout}>
                Sign out
              </button>
            </>
          )}
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-search">
            <Search size={16} />
            <input
              placeholder="Search content, authors, media…"
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <select
              value={publication?.id || ""}
              onChange={(e) => {
                const pub = publications.find((p) => p.slug === e.target.value) || null;
                setPublication(pub);
              }}
              style={{ border: "1px solid var(--rule)", borderRadius: 6, padding: "0.35rem 0.55rem", background: "#fff" }}
            >
              {publications.map((p) => (
                <option key={p.id} value={p.slug}>
                  {p.name}
                </option>
              ))}
            </select>
            <button className="btn ghost" title="Notifications" style={{ position: "relative" }}>
              <Bell size={18} />
              {unread >= 0 && (
                <span
                  style={{
                    position: "absolute",
                    top: 2,
                    right: 2,
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "var(--accent)",
                  }}
                />
              )}
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
