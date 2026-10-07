import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Icon from "./Icon";

export default function AccessDenied() {
  const { user } = useAuth();

  return (
    <div className="access-denied">
      <div className="access-denied-card">
        <span className="access-denied-icon">
          <Icon name="lock" size={36} />
        </span>
        <h2>Área restrita a administradores</h2>
        <p className="page-subtitle">
          Seu perfil ({user?.role ?? "—"}) não tem acesso a esta página. Se precisar dela, peça ao
          administrador da sua conta.
        </p>
        <Link to="/" className="btn btn-primary">
          Voltar ao dashboard
        </Link>
      </div>
    </div>
  );
}
