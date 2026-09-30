import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";
import Icon from "../components/ui/Icon";
import ErrorBanner from "../components/ui/ErrorBanner";

export default function LoginPage() {
  const navigate = useNavigate();
  const { user, isLoading, login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isLoading && user) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setSubmitError(err instanceof ApiError ? "Credenciais inválidas." : "Erro ao entrar.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-hero">
        <div>
          <span className="login-hero-eyebrow">Metodologia 93x7®</span>
          <div className="login-hero-title">
            Cada conversa comercial, avaliada com rigor e devolvida como desenvolvimento.
          </div>
          <p className="login-hero-description">
            Envie a transcrição ou a gravação de um atendimento. A análise percorre 6 critérios
            comportamentais e entrega relatórios prontos para orientar o próximo passo de cada
            profissional.
          </p>
        </div>
        <div>
          <div className="login-hero-pillars">
            <div className="login-hero-pillar">
              <span className="login-hero-pillar-number">93</span>
              <span className="login-hero-pillar-label">Comportamento e condução</span>
              <span className="login-hero-pillar-description">Como a conversa foi conduzida</span>
            </div>
            <div className="login-hero-pillar">
              <span className="login-hero-pillar-number">7</span>
              <span className="login-hero-pillar-label">Conteúdo e resultado</span>
              <span className="login-hero-pillar-description">O que foi dito e construído</span>
            </div>
          </div>
          <div className="login-hero-steps" style={{ marginTop: 28 }}>
            <span className="login-hero-step">
              <Icon name="upload_file" size={18} color="#D9C589" />
              Envio
            </span>
            <span className="login-hero-step">
              <Icon name="psychology" size={18} color="#D9C589" />
              Análise
            </span>
            <span className="login-hero-step">
              <Icon name="description" size={18} color="#D9C589" />
              Relatórios
            </span>
            <span className="login-hero-step">
              <Icon name="trending_up" size={18} color="#D9C589" />
              Evolução
            </span>
          </div>
        </div>
      </div>

      <form className="login-panel" onSubmit={handleSubmit}>
        <img src="/gerad-logo.png" alt="Gera D Consultoria" className="login-logo" />
        <div>
          <div className="login-title">
            Entrar no GerA<span className="login-title-d">D</span>
          </div>
          <p className="login-subtitle">Acesse com o e-mail cadastrado pelo administrador da sua conta.</p>
        </div>

        {submitError && <ErrorBanner>{submitError}</ErrorBanner>}

        <div className="form-field">
          <label htmlFor="email">E-mail</label>
          <input
            id="email"
            type="email"
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="voce@empresa.com"
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">Senha</label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        <button type="submit" className="btn btn-primary login-submit" disabled={isSubmitting}>
          {isSubmitting ? "Entrando..." : "Entrar"}
        </button>

        <p className="login-footnote">
          Não tem acesso? Fale com o administrador da sua conta. O cadastro é feito internamente.
        </p>
      </form>
    </div>
  );
}
