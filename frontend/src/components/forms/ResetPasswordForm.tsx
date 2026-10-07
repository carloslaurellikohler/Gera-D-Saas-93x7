import { useState } from "react";
import { ApiError } from "../../api/client";
import { useResetUserPassword } from "../../hooks/useResetUserPassword";
import type { User } from "../../types/auth";
import ErrorBanner from "../ui/ErrorBanner";

export default function ResetPasswordForm({ user, onDone }: { user: User; onDone: () => void }) {
  const resetPassword = useResetUserPassword();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    if (password.length < 8) {
      setError("A senha deve ter ao menos 8 caracteres.");
      return;
    }
    try {
      await resetPassword.mutateAsync({ id: user.id, payload: { password } });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao redefinir senha.");
    }
  };

  return (
    <div>
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="form-field" style={{ marginTop: error ? 18 : 0 }}>
        <label htmlFor="reset-password">Nova senha para {user.name}</label>
        <input
          id="reset-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>

      <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", paddingTop: 6 }}>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={resetPassword.isPending}
        >
          {resetPassword.isPending ? "Salvando..." : "Redefinir senha"}
        </button>
      </div>
    </div>
  );
}
