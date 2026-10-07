import { apiGet, apiPost, apiPut } from "./client";
import type { User } from "../types/auth";
import type {
  CreateUserPayload,
  ResetPasswordPayload,
  UpdateUserPayload,
  UserFilters,
} from "../types/user";

export function listUsers(filters: UserFilters = {}) {
  const params = new URLSearchParams();
  if (filters.role) params.set("role", filters.role);
  if (filters.status) params.set("status", filters.status);
  if (filters.search) params.set("search", filters.search);
  const query = params.toString();
  return apiGet<User[]>(`/users${query ? `?${query}` : ""}`);
}

export function listMyTeam() {
  return apiGet<User[]>("/users/me/team");
}

export function createUser(payload: CreateUserPayload) {
  return apiPost<User>("/users", payload);
}

export function updateUser(id: string, payload: UpdateUserPayload) {
  return apiPut<User>(`/users/${id}`, payload);
}

export function activateUser(id: string) {
  return apiPost<User>(`/users/${id}/activate`);
}

export function deactivateUser(id: string) {
  return apiPost<User>(`/users/${id}/deactivate`);
}

export function resetUserPassword(id: string, payload: ResetPasswordPayload) {
  return apiPost<User>(`/users/${id}/reset-password`, payload);
}
