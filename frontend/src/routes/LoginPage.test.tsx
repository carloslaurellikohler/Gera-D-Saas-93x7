import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LoginPage from "./LoginPage";
import { AuthProvider } from "../context/AuthContext";
import * as authApi from "../api/auth";
import { ApiError } from "../api/client";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockNavigate.mockReset();
  vi.spyOn(authApi, "getCurrentUser").mockRejectedValue(new ApiError(401, "Não autenticado."));
});

describe("LoginPage", () => {
  it("navigates on successful login", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "login").mockResolvedValue({
      id: "1",
      name: "Ana",
      email: "ana@example.com",
      role: "COLABORADOR",
      status: "ACTIVE",
      manager_id: null,
      created_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    });

    renderPage();

    await user.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/"));
  });

  it("shows an error message on failed login", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "login").mockRejectedValue(new ApiError(401, "Credenciais inválidas."));

    renderPage();

    await user.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Credenciais inválidas.")).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
