import type { UserRole, UserStatus } from "./auth";

export interface CreateUserPayload {
  name: string;
  email: string;
  password: string;
  role: UserRole;
  manager_id?: string | null;
}

export interface UpdateUserPayload {
  name: string;
  email: string;
  role: UserRole;
  manager_id?: string | null;
}

export interface ResetPasswordPayload {
  password: string;
}

export interface UserFilters {
  role?: UserRole;
  status?: UserStatus;
  search?: string;
}
