import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProtectedRoute from "./ProtectedRoute";
import { AuthProvider } from "../../context/AuthContext";
import * as authApi from "../../api/auth";
import { ApiError } from "../../api/client";
import type { User } from "../../types/auth";

function renderWithRoute() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<div>Protected content</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("ProtectedRoute", () => {
  it("redirects to /login when there is no authenticated user", async () => {
    vi.spyOn(authApi, "getCurrentUser").mockRejectedValue(new ApiError(401, "Não autenticado."));

    renderWithRoute();

    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });

  it("renders the protected children when a user is authenticated", async () => {
    const user: User = {
      id: "1",
      name: "Ana",
      email: "ana@example.com",
      role: "USER",
      status: "ACTIVE",
      created_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    };
    vi.spyOn(authApi, "getCurrentUser").mockResolvedValue(user);

    renderWithRoute();

    await waitFor(() => expect(screen.getByText("Protected content")).toBeInTheDocument());
  });
});
