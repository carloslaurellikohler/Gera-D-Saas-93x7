import type { ReactNode } from "react";
import { useAuth } from "../../context/AuthContext";
import AccessDenied from "../ui/AccessDenied";

export default function AdminRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  if (user?.role !== "ADMIN") {
    return <AccessDenied />;
  }

  return <>{children}</>;
}
