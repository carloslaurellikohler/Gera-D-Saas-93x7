import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import type { UserRole } from "../../types/auth";
import Icon from "./Icon";

interface NavItem {
  to: string;
  end?: boolean;
  icon: string;
  label: string;
  allow?: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", end: true, icon: "space_dashboard", label: "Dashboard" },
  { to: "/analyses/new", icon: "add_circle", label: "Nova análise" },
  { to: "/metricas", icon: "monitoring", label: "Métricas" },
  { to: "/biblioteca", icon: "local_library", label: "Biblioteca" },
  { to: "/assistente", icon: "forum", label: "Assistente IA" },
];

const ADMIN_NAV_ITEMS: NavItem[] = [
  { to: "/admin", icon: "insights", label: "Painel administrativo", allow: ["ADMIN"] },
  { to: "/calibracao", icon: "tune", label: "Metodologia", allow: ["ADMIN"] },
  { to: "/usuarios", icon: "group", label: "Usuários", allow: ["ADMIN"] },
  { to: "/custos-ia", icon: "savings", label: "Custos de IA", allow: ["ADMIN"] },
  { to: "/configuracoes", icon: "settings", label: "Configurações", allow: ["ADMIN"] },
];

export const ROLE_BADGE_CLASS: Record<UserRole, string> = {
  ADMIN: "admin",
  GESTOR: "gestor",
  COLABORADOR: "colaborador",
};

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const visibleAdminItems = ADMIN_NAV_ITEMS.filter((item) => !item.allow || (user && item.allow.includes(user.role)));

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

        {visibleAdminItems.length > 0 && (
          <>
            <div className="ui-sidebar-section-label">Administração</div>
            {visibleAdminItems.map((item) => (
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
          <span className={`ui-sidebar-role ui-sidebar-role-${user ? ROLE_BADGE_CLASS[user.role] : "colaborador"}`}>
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
