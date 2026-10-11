import { useState, type CSSProperties } from "react";
import { ApiError } from "../api/client";
import ResetPasswordForm from "../components/forms/ResetPasswordForm";
import UserForm from "../components/forms/UserForm";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import Modal from "../components/ui/Modal";
import { ROLE_BADGE_CLASS } from "../components/ui/Sidebar";
import { useAuth } from "../context/AuthContext";
import { useConfirm } from "../context/ConfirmContext";
import { useActivateUser } from "../hooks/useActivateUser";
import { useDeactivateUser } from "../hooks/useDeactivateUser";
import { useUsers } from "../hooks/useUsers";
import { formatDate } from "../lib/format";
import type { User } from "../types/auth";

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[parts.length - 1]?.[0] ?? "")).toUpperCase();
}

function managerCellText(u: User): string {
  if (u.role === "GESTOR") {
    const n = u.team_size ?? 0;
    return `${n} colaborador${n === 1 ? "" : "es"}`;
  }
  return u.manager_name ?? "—";
}

const iconButtonStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: 28,
  height: 28,
  border: "none",
  background: "transparent",
  cursor: "pointer",
};

type FilterKey = "all" | "ADMIN" | "GESTOR" | "COLABORADOR" | "INACTIVE";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "Todos" },
  { key: "ADMIN", label: "ADMIN" },
  { key: "GESTOR", label: "GESTOR" },
  { key: "COLABORADOR", label: "COLABORADOR" },
  { key: "INACTIVE", label: "Inativos" },
];

const ROLE_FILTER_KEYS: FilterKey[] = ["ADMIN", "GESTOR", "COLABORADOR"];

export default function UserAdminPage() {
  const { user: currentUser } = useAuth();
  const confirm = useConfirm();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [search, setSearch] = useState("");
  const [managerFilter, setManagerFilter] = useState("");
  const [formMode, setFormMode] = useState<UserFormMode | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = useState<User | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const users = useUsers({
    role: ROLE_FILTER_KEYS.includes(filter) ? (filter as "ADMIN" | "GESTOR" | "COLABORADOR") : undefined,
    status: filter === "INACTIVE" ? "INACTIVE" : undefined,
    search: search.trim() || undefined,
    manager_id: managerFilter || undefined,
  });
  const gestores = useUsers({ role: "GESTOR", status: "ACTIVE" });
  const activateUser = useActivateUser();
  const deactivateUser = useDeactivateUser();

  const handleToggleStatus = async (target: User) => {
    const activating = target.status === "INACTIVE";
    const verb = activating ? "Reativar" : "Inativar";
    const confirmed = await confirm({
      title: `${verb} o usuário "${target.name}"?`,
      confirmLabel: verb,
      tone: activating ? "default" : "danger",
    });
    if (!confirmed) {
      return;
    }
    setActionError(null);
    try {
      if (activating) {
        await activateUser.mutateAsync(target.id);
      } else {
        await deactivateUser.mutateAsync(target.id);
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Erro ao atualizar status do usuário.");
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Usuários</h1>
          <span className="page-subtitle">Não há autocadastro: todo acesso é criado aqui.</span>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setFormMode({ mode: "create" })}>
          <Icon name="person_add" size={20} />
          Novo usuário
        </button>
      </div>

      {actionError && (
        <div style={{ margin: "16px 0" }}>
          <ErrorBanner>{actionError}</ErrorBanner>
        </div>
      )}

      <Modal
        open={formMode !== null}
        title={formMode?.mode === "edit" ? "Editar usuário" : "Novo usuário"}
        onClose={() => setFormMode(null)}
      >
        <UserForm
          onDone={() => setFormMode(null)}
          editing={formMode?.mode === "edit" ? formMode.user : undefined}
        />
      </Modal>

      <Modal
        open={resetPasswordUser !== null}
        title={`Redefinir senha de "${resetPasswordUser?.name}"`}
        onClose={() => setResetPasswordUser(null)}
      >
        {resetPasswordUser && (
          <ResetPasswordForm user={resetPasswordUser} onDone={() => setResetPasswordUser(null)} />
        )}
      </Modal>

      <div style={{ display: "flex", gap: 12, alignItems: "center", margin: "20px 0" }}>
        <span className="search-field" style={{ width: 280 }}>
          <Icon name="search" size={20} />
          <input
            type="text"
            placeholder="Buscar por nome ou e-mail"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              border: "none",
              outline: "none",
              background: "transparent",
              flex: 1,
              fontSize: 13,
              color: "var(--content-primary)",
            }}
          />
        </span>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={filter === f.key ? "pill pill-active" : "pill"}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
        <span className="search-field">
          <select
            aria-label="Filtrar por gestor"
            value={managerFilter}
            onChange={(e) => setManagerFilter(e.target.value)}
            style={{ border: "none", outline: "none", background: "none", font: "inherit" }}
          >
            <option value="">Todos os gestores</option>
            {(gestores.data ?? []).map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
          <Icon name="expand_more" size={20} />
        </span>
      </div>

      {users.isLoading && <p className="page-subtitle">Carregando...</p>}
      {users.isError && <p className="error-text">Não foi possível carregar os usuários.</p>}

      {users.data && users.data.length === 0 && (
        <EmptyState
          icon="group"
          title="Nenhum usuário encontrado"
          description="Ajuste os filtros ou cadastre um novo usuário."
        />
      )}

      {users.data && users.data.length > 0 && (
        <div className="data-table">
          <div
            className="data-table-row data-table-head"
            style={{ gridTemplateColumns: "minmax(0,1.4fr) 120px minmax(0,1fr) 110px 140px 120px" }}
          >
            <span>Usuário</span>
            <span>Papel</span>
            <span>Gestor</span>
            <span>Status</span>
            <span>Último acesso</span>
            <span />
          </div>
          {users.data.map((u) => {
            const isSelf = u.id === currentUser?.id;
            const canDeactivate = !(isSelf && u.status === "ACTIVE");
            return (
              <div
                key={u.id}
                className="data-table-row"
                style={{
                  gridTemplateColumns: "minmax(0,1.4fr) 120px minmax(0,1fr) 110px 140px 120px",
                  opacity: u.status === "INACTIVE" ? 0.6 : 1,
                }}
              >
                <span className="data-table-participant">
                  <span className="data-table-avatar">{initialsOf(u.name)}</span>
                  <span>
                    <b style={{ display: "block", fontWeight: 600 }}>{u.name}</b>
                    <span className="page-subtitle" style={{ fontSize: 12 }}>
                      {u.email}
                    </span>
                  </span>
                </span>
                <span
                  className={`ui-sidebar-role ui-sidebar-role-${ROLE_BADGE_CLASS[u.role]}`}
                  style={{ justifySelf: "start", alignSelf: "center" }}
                >
                  {u.role}
                </span>
                <span className="page-subtitle">{managerCellText(u)}</span>
                <span>{u.status === "ACTIVE" ? "Ativo" : "Inativo"}</span>
                <span className="page-subtitle">{formatDate(u.last_login_at)}</span>
                <span style={{ display: "flex", gap: 4, justifySelf: "end" }}>
                  <button
                    type="button"
                    title="Editar usuário"
                    aria-label="Editar usuário"
                    onClick={() => setFormMode({ mode: "edit", user: u })}
                    style={iconButtonStyle}
                  >
                    <Icon name="edit" size={20} color="var(--content-secondary)" />
                  </button>
                  <button
                    type="button"
                    title="Redefinir senha"
                    aria-label="Redefinir senha"
                    onClick={() => setResetPasswordUser(u)}
                    style={iconButtonStyle}
                  >
                    <Icon name="key" size={20} color="var(--content-secondary)" />
                  </button>
                  <button
                    type="button"
                    title={
                      canDeactivate
                        ? u.status === "ACTIVE"
                          ? "Inativar usuário"
                          : "Reativar usuário"
                        : "Você não pode inativar sua própria conta."
                    }
                    aria-label={u.status === "ACTIVE" ? "Inativar usuário" : "Reativar usuário"}
                    disabled={!canDeactivate}
                    onClick={() => void handleToggleStatus(u)}
                    style={iconButtonStyle}
                  >
                    <Icon
                      name={u.status === "ACTIVE" ? "block" : "check_circle"}
                      size={20}
                      color="var(--content-secondary)"
                    />
                  </button>
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

type UserFormMode = { mode: "create" } | { mode: "edit"; user: User };
