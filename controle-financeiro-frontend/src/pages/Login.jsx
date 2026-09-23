import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, ShieldCheck, Wallet } from "lucide-react";
import { autenticar, criarConta } from "../utils/auth";
import { api, ApiError } from "../api/client";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// -----------------------------------------------------------------------
// Login.jsx
//
// Tela de login/criar conta com alguns cuidados de UX/segurança no front:
//  - "modo" alterna entre entrar e criar conta no mesmo formulário/lado
//    da tela (só troca o texto e o campo de confirmar senha) — em vez de
//    uma segunda tela/rota separada.
//  - mostrar/ocultar senha
//  - validação básica (email, tamanho mínimo de senha) antes de enviar
//  - mensagem de erro genérica no login (nunca dizer "senha errada"
//    especificamente - não revela se o email existe ou não)
//  - "manter conectado" (cookie httpOnly setado pelo backend)
//  - contador de tentativas simples (placeholder pra rate-limit visual)
// -----------------------------------------------------------------------
export default function Login() {
  const [modo, setModo] = useState("entrar"); // "entrar" | "criar"
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [manterConectado, setManterConectado] = useState(true);
  const [erro, setErro] = useState("");
  const [tentativas, setTentativas] = useState(0);
  const [entrando, setEntrando] = useState(false);
  const [erroGoogle, setErroGoogle] = useState("");
  const botaoGoogleRef = useRef(null);
  const navigate = useNavigate();

  const BLOQUEADO_APOS = 5;
  const criandoConta = modo === "criar";

  function alternarModo(novoModo) {
    setModo(novoModo);
    setErro("");
    setSenha("");
    setConfirmarSenha("");
  }

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

  async function handleEntrar() {
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

  async function handleCriarConta() {
    if (senha !== confirmarSenha) {
      setErro("As senhas não conferem.");
      return;
    }

    setEntrando(true);
    try {
      await criarConta(email, senha);
      navigate("/");
    } catch (err) {
      setErro(
        err instanceof ApiError && err.status === 409
          ? "Já existe uma conta com esse email."
          : err.message || "Não foi possível criar a conta."
      );
    } finally {
      setEntrando(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErro("");

    if (tentativas >= BLOQUEADO_APOS) return;

    if (senha.length < 6) {
      setErro("A senha precisa ter pelo menos 6 caracteres.");
      if (!criandoConta) setTentativas((t) => t + 1);
      return;
    }

    if (criandoConta) {
      await handleCriarConta();
    } else {
      await handleEntrar();
    }
  }

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] bg-bg">
      {/* Painel editorial esquerdo — some em telas pequenas, o formulário
          já se basta sozinho ali. */}
      <div className="hidden md:flex relative flex-col justify-between bg-surface-2 px-12 lg:px-16 py-12 overflow-hidden">
        <div className="flex items-center gap-2 text-text-primary font-semibold text-lg" style={{ fontFamily: "var(--font-heading)" }}>
          <span className="w-8 h-8 rounded-full bg-accent-dark flex items-center justify-center text-accent">
            <Wallet size={16} />
          </span>
          Bolso Leve
        </div>

        <div className="max-w-md">
          <p className="text-success text-xs font-bold tracking-widest uppercase mb-3">Equilíbrio financeiro</p>
          <h1 className="text-4xl lg:text-5xl leading-[1.05] text-text-primary mb-4">
            Organize seu dinheiro com clareza.
          </h1>
          <p className="text-text-secondary text-base leading-relaxed">
            Mais controle para hoje. Mais tranquilidade para amanhã.
          </p>
        </div>

        {/* Ilustração simples e abstrata: gráfico de crescimento, no
            mesmo espírito "clareza acima de decoração" do resto do app. */}
        <svg viewBox="0 0 320 160" className="w-full max-w-sm h-auto" aria-hidden="true">
          <circle cx="230" cy="130" r="70" fill="var(--color-accent-dark)" />
          <g>
            <rect x="40" y="90" width="26" height="50" rx="5" fill="var(--color-accent-dark)" />
            <rect x="76" y="65" width="26" height="75" rx="5" fill="#b9d9d3" />
            <rect x="112" y="35" width="26" height="105" rx="5" fill="var(--color-success)" />
          </g>
          <polyline
            points="40,95 76,68 112,38 200,20"
            fill="none"
            stroke="var(--color-danger)"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="200" cy="20" r="6" fill="var(--color-danger)" />
        </svg>

        <p className="text-text-muted text-xs uppercase tracking-widest border-t border-border pt-4">
          Finanças mais simples para uma vida mais leve.
        </p>
      </div>

      {/* Painel do formulário */}
      <div className="flex items-center justify-center px-4 py-12">
        <form onSubmit={handleSubmit} className="w-full max-w-sm bg-surface rounded-card border border-border p-8 flex flex-col items-center gap-3">
          <div className="md:hidden w-10 h-10 rounded-full bg-accent-dark flex items-center justify-center text-accent mb-1">
            <Wallet size={18} />
          </div>
          <h2 className="text-xl font-bold" style={{ fontFamily: "var(--font-heading)" }}>
            {criandoConta ? "Criar conta" : "Entrar"}
          </h2>
          <p className="text-xs text-text-muted -mt-1 mb-2">
            {criandoConta ? "Leva menos de um minuto" : "Acesse sua conta e continue sua jornada"}
          </p>

          {!criandoConta && GOOGLE_CLIENT_ID && (
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

          <div className="w-full flex flex-col gap-1">
            <label className="text-xs font-bold text-text-primary">E-mail</label>
            <input
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface border border-border rounded-[var(--radius-control)] px-3 py-2.5 text-sm outline-none focus:border-success focus:ring-2 focus:ring-success/15 transition-colors"
              autoComplete={criandoConta ? "email" : "username"}
              required
            />
          </div>

          {/* Campo de senha com botão de mostrar/ocultar */}
          <div className="w-full flex flex-col gap-1">
            <label className="text-xs font-bold text-text-primary">Senha</label>
            <div className="relative w-full">
              <input
                type={mostrarSenha ? "text" : "password"}
                placeholder="Sua senha"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                className="w-full bg-surface border border-border rounded-[var(--radius-control)] px-3 py-2.5 pr-9 text-sm outline-none focus:border-success focus:ring-2 focus:ring-success/15 transition-colors"
                autoComplete={criandoConta ? "new-password" : "current-password"}
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
          </div>

          {/* Confirmar senha só aparece no modo "criar conta" */}
          {criandoConta && (
            <div className="w-full flex flex-col gap-1">
              <label className="text-xs font-bold text-text-primary">Confirmar senha</label>
              <input
                type={mostrarSenha ? "text" : "password"}
                placeholder="Repita sua senha"
                value={confirmarSenha}
                onChange={(e) => setConfirmarSenha(e.target.value)}
                className="w-full bg-surface border border-border rounded-[var(--radius-control)] px-3 py-2.5 text-sm outline-none focus:border-success focus:ring-2 focus:ring-success/15 transition-colors"
                autoComplete="new-password"
                required
              />
            </div>
          )}

          {/* Mensagem de erro genérica (nunca aponta se foi o email ou a senha) */}
          {erro && <p className="text-xs text-danger self-start">{erro}</p>}
          {!criandoConta && tentativas >= BLOQUEADO_APOS && (
            <p className="text-xs text-danger self-start">
              Muitas tentativas. Aguarde um momento antes de tentar de novo.
            </p>
          )}

          {!criandoConta && (
            <label className="w-full flex items-center gap-2 text-xs text-text-secondary mt-1">
              <input
                type="checkbox"
                checked={manterConectado}
                onChange={(e) => setManterConectado(e.target.checked)}
                className="accent-[var(--color-success)]"
              />
              Manter conectado neste dispositivo
            </label>
          )}

          <button
            type="submit"
            disabled={(!criandoConta && tentativas >= BLOQUEADO_APOS) || entrando}
            className="w-full bg-accent text-white rounded-[var(--radius-control)] py-2.5 text-sm font-bold hover:opacity-90 transition-opacity mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {entrando ? (criandoConta ? "Criando conta..." : "Entrando...") : criandoConta ? "Criar conta" : "Entrar"}
          </button>

          <p className="text-xs text-text-secondary mt-1">
            {criandoConta ? (
              <>
                Já tem conta?{" "}
                <button type="button" onClick={() => alternarModo("entrar")} className="text-success font-bold hover:underline">
                  Entrar
                </button>
              </>
            ) : (
              <>
                Ainda não tem conta?{" "}
                <button type="button" onClick={() => alternarModo("criar")} className="text-success font-bold hover:underline">
                  Criar conta
                </button>
              </>
            )}
          </p>

          <div className="flex items-center gap-1.5 text-xs text-text-muted mt-2">
            <ShieldCheck size={13} />
            Seus dados financeiros ficam só nessa conta — ninguém mais vê.
          </div>
        </form>
      </div>
    </div>
  );
}
