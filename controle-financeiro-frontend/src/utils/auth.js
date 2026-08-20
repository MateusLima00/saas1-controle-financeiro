import { api } from "../api/client";

// -----------------------------------------------------------------------
// auth.js
//
// Sessão real via cookie httpOnly (setado pelo backend em /auth/login).
// Nada é guardado em localStorage - "estar autenticado" significa que o
// cookie de sessão é válido, o que só o backend sabe responder.
// -----------------------------------------------------------------------
export async function estaAutenticado() {
  try {
    await api.get("/auth/me");
    return true;
  } catch {
    return false;
  }
}

export function autenticar(email, senha) {
  return api.post("/auth/login", { email, senha });
}

export async function sair() {
  try {
    await api.post("/auth/logout");
  } catch {
    // se já não tiver sessão, tanto faz - o objetivo é limpar o cookie
  }
}
