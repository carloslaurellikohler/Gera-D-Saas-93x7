import { useState, type CSSProperties } from "react";
import { ApiError } from "../api/client";
import EmptyState from "../components/ui/EmptyState";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import { useAuth } from "../context/AuthContext";
import { useConfirm } from "../context/ConfirmContext";
import { useActivateUser } from "../hooks/useActivateUser";
import { useCreateUser } from "../hooks/useCreateUser";
import { useDeactivateUser } from "../hooks/useDeactivateUser";
import { useUpdateUser } from "../hooks/useUpdateUser";
import { useUsers } from "../hooks/useUsers";
import { formatDate } from "../lib/format";
import type { User, UserRole } from "../types/auth";

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[parts.length - 1]?.[0] ?? "")).toUpperCase();
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

type FilterKey = "all" | "ADMIN" | "USER" | "INACTIVE";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "Todos" },
  { key: "ADMIN", label: "ADMIN" },
  { key: "USER", label: "USER" },
  { key: "INACTIVE", label: "Inativos" },
];

export default function UserAdminPage() {
  const { user: currentUser } = useAuth();
  const confirm = useConfirm();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [search, setSearch] = useState("");
  const [formMode, setFormMode] = useState<UserFormMode | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const users = useUsers({
    role: filter === "ADMIN" || filter === "USER" ? filter : undefined,
    status: filter === "INACTIVE" ? "INACTIVE" : undefined,
    search: search.trim() || undefined,
  });
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
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setFormMode((m) => (m ? null : { mode: "create" }))}
        >
          <Icon name="person_add" size={20} />
          {formMode ? "Cancelar" : "Novo usuário"}
        </button>
      </div>

      {actionError && (
        <div style={{ margin: "16px 0" }}>
          <ErrorBanner>{actionError}</ErrorBanner>
        </div>
      )}

      {formMode && (
        <UserForm
          onDone={() => setFormMode(null)}
          editing={formMode.mode === "edit" ? formMode.user : undefined}
        />
      )}

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
            style={{ gridTemplateColumns: "minmax(0,1.6fr) 130px 150px 140px 90px" }}
          >
            <span>Usuário</span>
            <span>Papel</span>
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
                  gridTemplateColumns: "minmax(0,1.6fr) 130px 150px 140px 90px",
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
                  className={`ui-sidebar-role ui-sidebar-role-${u.role === "ADMIN" ? "admin" : "user"}`}
                  style={{ justifySelf: "start" }}
                >
                  {u.role}
                </span>
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

function UserForm({ onDone, editing }: { onDone: () => void; editing?: User }) {
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [name, setName] = useState(editing?.name ?? "");
  const [email, setEmail] = useState(editing?.email ?? "");
  const [role, setRole] = useState<UserRole>(editing?.role ?? "USER");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isPending = editing ? updateUser.isPending : createUser.isPending;

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) {
      setError("Informe o nome do usuário.");
      return;
    }
    if (!email.includes("@")) {
      setError("Informe um e-mail válido.");
      return;
    }
    if (!editing && password.length < 8) {
      setError("A senha deve ter ao menos 8 caracteres.");
      return;
    }
    try {
      if (editing) {
        await updateUser.mutateAsync({ id: editing.id, payload: { name, email, role } });
      } else {
        await createUser.mutateAsync({ name, email, password, role });
      }
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Erro ao ${editing ? "salvar" : "criar"} usuário.`);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="form-field" style={{ marginTop: error ? 18 : 0 }}>
        <label htmlFor="user-name">Nome</label>
        <input id="user-name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
      </div>

      <div className="form-row">
        <div className="form-field">
          <label htmlFor="user-email">E-mail</label>
          <input id="user-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="form-field">
          <label htmlFor="user-role">Papel</label>
          <select id="user-role" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
            <option value="USER">USER</option>
            <option value="ADMIN">ADMIN</option>
          </select>
        </div>
      </div>

      {!editing && (
        <div className="form-field">
          <label htmlFor="user-password">Senha inicial</label>
          <input
            id="user-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
      )}

      <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", paddingTop: 6 }}>
        <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={isPending}>
          {isPending ? "Salvando..." : editing ? "Salvar alterações" : "Criar usuário"}
        </button>
      </div>
    </div>
  );
}
