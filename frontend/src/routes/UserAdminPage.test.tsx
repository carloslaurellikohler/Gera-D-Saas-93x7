import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import UserAdminPage from "./UserAdminPage";
import { AuthProvider } from "../context/AuthContext";
import * as authApi from "../api/auth";
import * as usersApi from "../api/users";
import { ApiError } from "../api/client";
import type { User } from "../types/auth";

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <UserAdminPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const ADMIN: User = {
  id: "admin-1",
  name: "Admin Teste",
  email: "admin@example.com",
  role: "ADMIN",
  status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: "2026-01-02T00:00:00Z",
};

const OTHER_USER: User = {
  id: "user-1",
  name: "Ana Souza",
  email: "ana@example.com",
  role: "USER",
  status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(ADMIN);
});

describe("UserAdminPage", () => {
  it("renders the user list from the API", async () => {
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN, OTHER_USER]);

    renderPage();

    expect(await screen.findByText("Ana Souza")).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
  });

  it("shows an empty state when there are no users matching the filters", async () => {
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText("Nenhum usuário encontrado")).toBeInTheDocument();
  });

  it("creates a user from the inline form", async () => {
    const user = userEvent.setup();
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN]);
    const createSpy = vi.spyOn(usersApi, "createUser").mockResolvedValue(OTHER_USER);

    renderPage();
    await screen.findByText("Admin Teste");

    await user.click(screen.getByRole("button", { name: /Novo usuário/ }));
    await user.type(screen.getByLabelText("Nome"), "Ana Souza");
    await user.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha inicial"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(createSpy.mock.calls[0]?.[0]).toEqual({
      name: "Ana Souza",
      email: "ana@example.com",
      password: "correct-password",
      role: "USER",
    });
  });

  it("rejects creating a user with a short password", async () => {
    const user = userEvent.setup();
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN]);
    const createSpy = vi.spyOn(usersApi, "createUser").mockResolvedValue(OTHER_USER);

    renderPage();
    await screen.findByText("Admin Teste");

    await user.click(screen.getByRole("button", { name: /Novo usuário/ }));
    await user.type(screen.getByLabelText("Nome"), "Ana Souza");
    await user.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha inicial"), "short");
    await user.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(await screen.findByText("A senha deve ter ao menos 8 caracteres.")).toBeInTheDocument();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it("shows a friendly error when creating a user with a duplicate email", async () => {
    const user = userEvent.setup();
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN]);
    vi
      .spyOn(usersApi, "createUser")
      .mockRejectedValue(new ApiError(409, "Já existe um usuário com este e-mail."));

    renderPage();
    await screen.findByText("Admin Teste");

    await user.click(screen.getByRole("button", { name: /Novo usuário/ }));
    await user.type(screen.getByLabelText("Nome"), "Ana Souza");
    await user.type(screen.getByLabelText("E-mail"), "ana@example.com");
    await user.type(screen.getByLabelText("Senha inicial"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(await screen.findByText("Já existe um usuário com este e-mail.")).toBeInTheDocument();
  });

  it("opens the edit form pre-filled and submits the update payload", async () => {
    const user = userEvent.setup();
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN, OTHER_USER]);
    const updateSpy = vi.spyOn(usersApi, "updateUser").mockResolvedValue(OTHER_USER);

    renderPage();
    await screen.findByText("Ana Souza");

    await user.click(screen.getAllByRole("button", { name: "Editar usuário" })[1]);

    const nameInput = screen.getByLabelText("Nome");
    expect(nameInput).toHaveValue("Ana Souza");

    await user.clear(nameInput);
    await user.type(nameInput, "Ana Souza Lima");
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(updateSpy).toHaveBeenCalledWith(
      "user-1",
      expect.objectContaining({ name: "Ana Souza Lima", email: "ana@example.com", role: "USER" }),
    );
  });

  it("deactivates another user after confirmation", async () => {
    const user = userEvent.setup();
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN, OTHER_USER]);
    const deactivateSpy = vi.spyOn(usersApi, "deactivateUser").mockResolvedValue({
      ...OTHER_USER,
      status: "INACTIVE",
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderPage();
    await screen.findByText("Ana Souza");

    await user.click(screen.getAllByRole("button", { name: "Inativar usuário" })[1]);

    expect(deactivateSpy.mock.calls[0]?.[0]).toBe("user-1");
  });

  it("does not deactivate when confirmation is cancelled", async () => {
    const user = userEvent.setup();
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN, OTHER_USER]);
    const deactivateSpy = vi.spyOn(usersApi, "deactivateUser").mockResolvedValue({
      ...OTHER_USER,
      status: "INACTIVE",
    });
    vi.spyOn(window, "confirm").mockReturnValue(false);

    renderPage();
    await screen.findByText("Ana Souza");

    await user.click(screen.getAllByRole("button", { name: "Inativar usuário" })[1]);

    expect(deactivateSpy).not.toHaveBeenCalled();
  });

  it("disables self-deactivation for the logged in admin", async () => {
    vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN, OTHER_USER]);

    renderPage();
    await screen.findByText("Ana Souza");

    const selfDeactivateButton = screen.getAllByRole("button", { name: "Inativar usuário" })[0];
    expect(selfDeactivateButton).toBeDisabled();
  });

  it("filters the list by role when a pill is clicked", async () => {
    const listSpy = vi.spyOn(usersApi, "listUsers").mockResolvedValue([ADMIN]);
    const user = userEvent.setup();

    renderPage();
    await screen.findByText("Admin Teste");

    await user.click(screen.getByRole("button", { name: "ADMIN" }));

    expect(listSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({ role: "ADMIN" }),
    );
  });
});
