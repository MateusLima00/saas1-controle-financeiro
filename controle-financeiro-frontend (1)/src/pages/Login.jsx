import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, ShieldCheck, Wallet } from "lucide-react";
import { autenticar } from "../utils/auth";
import { api, ApiError } from "../api/client";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// -----------------------------------------------------------------------
// Login.jsx
//
// Tela de login com alguns cuidados de UX/segurança no front (o backend
// de auth real ainda não existe, mas já deixamos os "ganchos"):
//  - mostrar/ocultar senha
//  - validação básica (email, tamanho mínimo de senha) antes de enviar
//  - mensagem de erro genérica (nunca dizer "senha errada" especificamente -
//    isso ajuda a não revelar se o email existe ou não, é prática comum)
//  - "manter conectado" (ficaria salvo em cookie httpOnly no backend real)
//  - contador de tentativas simples (placeholder pra rate-limit visual)
// -----------------------------------------------------------------------
export default function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [manterConectado, setManterConectado] = useState(true);
  const [erro, setErro] = useState("");
  const [tentativas, setTentativas] = useState(0);
  const [entrando, setEntrando] = useState(false);
  const [erroGoogle, setErroGoogle] = useState("");
  const botaoGoogleRef = useRef(null);
  const navigate = useNavigate();

  const BLOQUEADO_APOS = 5;

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !window.google || !botaoGoogleRef.current) return;

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async ({ credential }) => {
        setErroGoogle("");
        try {
          await api.post("/auth/google", { credential });
          navigate("/");
        } catch (err) {
          setErroGoogle(err.message || "Não foi possível entrar com o Google.");
        }
      },
    });
    window.google.accounts.id.renderButton(botaoGoogleRef.current, {
      theme: "outline",
      size: "large",
      width: 288,
    });
  }, [navigate]);

  async function handleLogin(e) {
    e.preventDefault();
    setErro("");

    if (tentativas >= BLOQUEADO_APOS) return;

    if (senha.length < 6) {
      setErro("A senha precisa ter pelo menos 6 caracteres.");
      setTentativas((t) => t + 1);
      return;
    }

    setEntrando(true);
    try {
      await autenticar(email, senha);
      navigate("/");
    } catch (err) {
      // Mensagem genérica sempre, mesmo com 401 (não revela se foi email ou senha)
      setErro(err instanceof ApiError ? "Email ou senha inválidos." : "Não foi possível conectar ao servidor.");
      setTentativas((t) => t + 1);
    } finally {
      setEntrando(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <form
        onSubmit={handleLogin}
        className="bg-surface rounded-card border border-border p-8 w-full max-w-sm flex flex-col items-center gap-3"
      >
        <div className="w-11 h-11 rounded-[var(--radius-control)] bg-accent-dark flex items-center justify-center text-accent mb-1">
          <Wallet size={20} />
        </div>
        <h1 className="text-base font-medium">Entrar</h1>
        <p className="text-xs text-text-muted -mt-2 mb-1">Acesso restrito e pessoal</p>

        {GOOGLE_CLIENT_ID && (
          <>
            <div ref={botaoGoogleRef} />
            {erroGoogle && <p className="text-xs text-danger self-start">{erroGoogle}</p>}
            <div className="w-full flex items-center gap-2 text-xs text-text-muted my-1">
              <div className="flex-1 h-px bg-border" />
              ou
              <div className="flex-1 h-px bg-border" />
            </div>
          </>
        )}

        <input
          type="email"
          placeholder="seu@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-2 text-sm outline-none focus:border-accent"
          autoComplete="username"
          required
        />

        {/* Campo de senha com botão de mostrar/ocultar */}
        <div className="relative w-full">
          <input
            type={mostrarSenha ? "text" : "password"}
            placeholder="Senha"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-2 pr-9 text-sm outline-none focus:border-accent"
            autoComplete="current-password"
            required
          />
          <button
            type="button"
            onClick={() => setMostrarSenha((v) => !v)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
            aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
          >
            {mostrarSenha ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>

        {/* Mensagem de erro genérica (nunca aponta se foi o email ou a senha) */}
        {erro && <p className="text-xs text-danger self-start">{erro}</p>}
        {tentativas >= BLOQUEADO_APOS && (
          <p className="text-xs text-danger self-start">
            Muitas tentativas. Aguarde um momento antes de tentar de novo.
          </p>
        )}

        <label className="w-full flex items-center gap-2 text-xs text-text-secondary mt-1">
          <input
            type="checkbox"
            checked={manterConectado}
            onChange={(e) => setManterConectado(e.target.checked)}
            className="accent-[var(--color-accent)]"
          />
          Manter conectado neste dispositivo
        </label>

        <button
          type="submit"
          disabled={tentativas >= BLOQUEADO_APOS || entrando}
          className="w-full bg-accent text-white rounded-[var(--radius-control)] py-2 text-sm font-medium hover:opacity-90 transition-opacity mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {entrando ? "Entrando..." : "Entrar"}
        </button>

        <div className="flex items-center gap-1.5 text-xs text-text-muted mt-2">
          <ShieldCheck size={13} />
          Seus dados financeiros ficam só neste app.
        </div>
      </form>
    </div>
  );
}
