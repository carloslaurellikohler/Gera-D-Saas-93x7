import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Icon from "./Icon";

interface NavItem {
  to: string;
  end?: boolean;
  icon: string;
  label: string;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", end: true, icon: "space_dashboard", label: "Dashboard" },
  { to: "/analyses/new", icon: "add_circle", label: "Nova análise" },
  { to: "/metricas", icon: "monitoring", label: "Métricas" },
  { to: "/biblioteca", icon: "local_library", label: "Biblioteca" },
  { to: "/assistente", icon: "forum", label: "Assistente IA" },
];

const ADMIN_NAV_ITEMS: NavItem[] = [
  { to: "/admin", icon: "insights", label: "Painel administrativo", adminOnly: true },
  { to: "/calibracao", icon: "tune", label: "Metodologia", adminOnly: true },
  { to: "/usuarios", icon: "group", label: "Usuários", adminOnly: true },
];

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  return (
    <aside className="ui-sidebar">
      <div className="ui-sidebar-brand">
        <img src="/gerad-logo.png" alt="Gera D Consultoria" className="ui-sidebar-logo" />
        <span className="ui-sidebar-tagline">
          GerA<span className="ui-sidebar-tagline-d">D</span>{" "}
          <span className="ui-sidebar-tagline-sub">· avaliação 93x7®</span>
        </span>
      </div>

      <nav className="ui-sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `ui-sidebar-item${isActive ? " ui-sidebar-item-active" : ""}`}
          >
            <Icon name={item.icon} size={22} />
            <span>{item.label}</span>
          </NavLink>
        ))}

        {isAdmin && (
          <>
            <div className="ui-sidebar-section-label">Administração</div>
            {ADMIN_NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `ui-sidebar-item${isActive ? " ui-sidebar-item-active" : ""}`}
              >
                <Icon name={item.icon} size={22} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </>
        )}
      </nav>

      <div className="ui-sidebar-user">
        <span className="ui-sidebar-avatar">{user ? initialsOf(user.name) : ""}</span>
        <span className="ui-sidebar-user-info">
          <span className="ui-sidebar-user-name">{user?.name}</span>
          <span className={`ui-sidebar-role ui-sidebar-role-${isAdmin ? "admin" : "user"}`}>
            {user?.role}
          </span>
        </span>
        <button
          type="button"
          className="ui-sidebar-logout"
          title="Sair"
          aria-label="Sair"
          onClick={() => logout()}
        >
          <Icon name="logout" size={22} />
        </button>
      </div>
    </aside>
  );
}
