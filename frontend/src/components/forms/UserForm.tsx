import { useState } from "react";
import { ApiError } from "../../api/client";
import { useCreateUser } from "../../hooks/useCreateUser";
import { useUpdateUser } from "../../hooks/useUpdateUser";
import type { User, UserRole } from "../../types/auth";
import ErrorBanner from "../ui/ErrorBanner";

export default function UserForm({ onDone, editing }: { onDone: () => void; editing?: User }) {
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
    <div>
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
