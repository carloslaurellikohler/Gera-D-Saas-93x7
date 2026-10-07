import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import RequireRole from "./RequireRole";
import { AuthProvider } from "../../context/AuthContext";
import * as authApi from "../../api/auth";
import type { User } from "../../types/auth";

function renderWithRole(allow: User["role"][], user: User) {
  vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(user);
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <RequireRole allow={allow}>
            <div>Conteúdo restrito</div>
          </RequireRole>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function makeUser(role: User["role"]): User {
  return {
    id: "1",
    name: "Usuária Teste",
    email: "user@example.com",
    role,
    status: "ACTIVE",
    manager_id: null,
    created_at: "2026-01-01T00:00:00Z",
    last_login_at: null,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("RequireRole", () => {
  it("renders children when the user has one of the allowed roles", async () => {
    renderWithRole(["ADMIN"], makeUser("ADMIN"));

    expect(await screen.findByText("Conteúdo restrito")).toBeInTheDocument();
  });

  it("renders children when the user matches any of several allowed roles", async () => {
    renderWithRole(["ADMIN", "GESTOR"], makeUser("GESTOR"));

    expect(await screen.findByText("Conteúdo restrito")).toBeInTheDocument();
  });

  it("shows AccessDenied when the user's role is not allowed", async () => {
    renderWithRole(["ADMIN"], makeUser("COLABORADOR"));

    expect(await screen.findByText("Área restrita a administradores")).toBeInTheDocument();
    expect(screen.queryByText("Conteúdo restrito")).not.toBeInTheDocument();
  });
});
