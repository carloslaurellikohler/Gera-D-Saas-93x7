import type { ReactNode } from "react";
import { useAuth } from "../../context/AuthContext";
import AccessDenied from "../ui/AccessDenied";
import type { UserRole } from "../../types/auth";

export default function RequireRole({ allow, children }: { allow: UserRole[]; children: ReactNode }) {
  const { hasRole } = useAuth();

  if (!hasRole(...allow)) {
    return <AccessDenied />;
  }

  return <>{children}</>;
}
