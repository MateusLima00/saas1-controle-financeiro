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

async function request(path, { method = "GET", body } = {}) {
  const resp = await fetch(`${BASE_URL}${path}`, {
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

  const resp = await fetch(`${BASE_URL}${path}`, {
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
