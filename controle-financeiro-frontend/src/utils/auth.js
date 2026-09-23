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

// Cria uma conta nova (email + senha) e já retorna logado (o backend seta
// o cookie de sessão na resposta, igual ao /auth/login). Cada conta nasce
// com um espaço de dados isolado e vazio — nada é compartilhado entre
// contas diferentes.
export function criarConta(email, senha) {
  return api.post("/auth/signup", { email, senha });
}

export function trocarSenha(senhaAtual, senhaNova) {
  return api.put("/auth/senha", { senhaAtual, senhaNova });
}

export function atualizarNome(nome) {
  return api.put("/auth/perfil", { nome });
}

// Recuperação de senha por código enviado por email (válido 15 min).
export function solicitarCodigoRecuperacao(email) {
  return api.post("/auth/recuperar-senha/solicitar", { email });
}

export function confirmarRecuperacao(email, codigo, senhaNova) {
  return api.post("/auth/recuperar-senha/confirmar", { email, codigo, senhaNova });
}

export async function sair() {
  try {
    await api.post("/auth/logout");
  } catch {
    // se já não tiver sessão, tanto faz - o objetivo é limpar o cookie
  }
}
