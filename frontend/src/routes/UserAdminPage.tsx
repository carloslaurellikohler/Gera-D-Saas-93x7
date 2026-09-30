import Icon from "../components/ui/Icon";

const USERS = [
  { name: "Marina Duarte", email: "marina.duarte@empresa.com.br", role: "USER", status: "Ativo", last: "Hoje" },
  { name: "Rafael Nogueira", email: "rafael.nogueira@empresa.com.br", role: "ADMIN", status: "Ativo", last: "Hoje" },
  { name: "Camila Ferraz", email: "camila.ferraz@empresa.com.br", role: "USER", status: "Ativo", last: "Ontem" },
  { name: "Bruno Tavares", email: "bruno.tavares@empresa.com.br", role: "USER", status: "Inativo", last: "há 12 dias" },
];

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[parts.length - 1]?.[0] ?? "")).toUpperCase();
}

export default function UserAdminPage() {
  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Usuários</h1>
          <span className="page-subtitle">Não há autocadastro: todo acesso é criado aqui.</span>
        </div>
        <button className="btn btn-primary">
          <Icon name="person_add" size={20} />
          Novo usuário
        </button>
      </div>

      <div style={{ display: "flex", gap: 12, alignItems: "center", margin: "20px 0" }}>
        <span className="search-field" style={{ width: 280 }}>
          <Icon name="search" size={20} />
          Buscar por nome ou e-mail
        </span>
        <span className="pill pill-active">Todos</span>
        <span className="pill">ADMIN</span>
        <span className="pill">USER</span>
        <span className="pill">Inativos</span>
      </div>

      <div className="data-table">
        <div
          className="data-table-row data-table-head"
          style={{ gridTemplateColumns: "minmax(0,1.6fr) 130px 150px 140px 60px" }}
        >
          <span>Usuário</span>
          <span>Papel</span>
          <span>Status</span>
          <span>Último acesso</span>
          <span />
        </div>
        {USERS.map((u) => (
          <div
            key={u.email}
            className="data-table-row"
            style={{
              gridTemplateColumns: "minmax(0,1.6fr) 130px 150px 140px 60px",
              opacity: u.status === "Inativo" ? 0.6 : 1,
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
            <span>{u.status}</span>
            <span className="page-subtitle">{u.last}</span>
            <Icon name="edit" size={20} color="var(--content-secondary)" />
          </div>
        ))}
      </div>
    </div>
  );
}
