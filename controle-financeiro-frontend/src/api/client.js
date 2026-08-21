// -----------------------------------------------------------------------
// client.js
//
// Wrapper de fetch pra falar com o backend FastAPI. Sempre manda
// credentials: "include" pra o cookie httpOnly de sessão ir junto (nunca
// usamos localStorage pra auth). baseURL vem de VITE_API_URL.
// -----------------------------------------------------------------------
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Deploys no Render trocam de instância em ~1min (o serviço fica sem
// processo escutando por uns segundos nessa janela) — o proxy deles
// responde 502/503/504 sem corpo JSON nesse intervalo, e uma falha de
// rede momentânea também joga o fetch numa exception. Um retry único
// depois de um instante cobre esses casos transitórios sem mascarar
// erros de negócio de verdade (4xx continuam falhando na hora).
async function fetchComRetry(url, options, tentativasRestantes = 1) {
  let resp;
  try {
    resp = await fetch(url, options);
  } catch (err) {
    if (tentativasRestantes <= 0) throw err;
    await new Promise((r) => setTimeout(r, 1500));
    return fetchComRetry(url, options, tentativasRestantes - 1);
  }
  if ([502, 503, 504].includes(resp.status) && tentativasRestantes > 0) {
    await new Promise((r) => setTimeout(r, 1500));
    return fetchComRetry(url, options, tentativasRestantes - 1);
  }
  return resp;
}

async function request(path, { method = "GET", body } = {}) {
  const resp = await fetchComRetry(`${BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!resp.ok) {
    let message = `Erro ${resp.status}`;
    try {
      const data = await resp.json();
      message = data.detail || message;
    } catch {
      // resposta sem corpo JSON, mantém mensagem genérica
    }
    throw new ApiError(message, resp.status);
  }

  if (resp.status === 204) return null;
  return resp.json();
}

async function upload(path, file) {
  const formData = new FormData();
  formData.append("file", file);

  const resp = await fetchComRetry(`${BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  if (!resp.ok) {
    let message = `Erro ${resp.status}`;
    try {
      const data = await resp.json();
      message = data.detail || message;
    } catch {
      // resposta sem corpo JSON, mantém mensagem genérica
    }
    throw new ApiError(message, resp.status);
  }

  return resp.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body: body ?? {} }),
  put: (path, body) => request(path, { method: "PUT", body: body ?? {} }),
  delete: (path) => request(path, { method: "DELETE" }),
  upload,
};
