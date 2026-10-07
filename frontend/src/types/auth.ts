export type UserRole = "ADMIN" | "GESTOR" | "COLABORADOR";
export type UserStatus = "ACTIVE" | "INACTIVE";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  manager_id: string | null;
  created_at: string;
  last_login_at: string | null;
}
