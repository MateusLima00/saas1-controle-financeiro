import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { estaAutenticado } from "../utils/auth";

// -----------------------------------------------------------------------
// RotaPrivada.jsx
//
// Envolve as rotas internas (tudo que fica dentro de LayoutInterno).
// Checa a sessão de verdade contra /auth/me antes de decidir se
// renderiza a página pedida ou redireciona pro /login.
// -----------------------------------------------------------------------
export default function RotaPrivada() {
  const [status, setStatus] = useState("checando"); // "checando" | "autenticado" | "negado"

  useEffect(() => {
    let ativo = true;
    estaAutenticado().then((ok) => {
      if (ativo) setStatus(ok ? "autenticado" : "negado");
    });
    return () => {
      ativo = false;
    };
  }, []);

  if (status === "checando") {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-text-muted">
        Carregando...
      </div>
    );
  }

  if (status === "negado") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
