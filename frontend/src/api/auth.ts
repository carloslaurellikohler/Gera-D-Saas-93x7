import { apiGet, apiPost } from "./client";
import type { User } from "../types/auth";

export function login(email: string, password: string): Promise<User> {
  return apiPost<User>("/auth/login", { email, password });
}

export function logout(): Promise<void> {
  return apiPost<void>("/auth/logout");
}

export function getCurrentUser(): Promise<User> {
  return apiGet<User>("/auth/me");
}
