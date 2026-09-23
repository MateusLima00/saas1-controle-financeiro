import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Lock, Mail, ShieldCheck } from "lucide-react";
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
  const [avisoRecuperacao, setAvisoRecuperacao] = useState(false);
  const botaoGoogleRef = useRef(null);
  const navigate = useNavigate();

  const BLOQUEADO_APOS = 5;
  const criandoConta = modo === "criar";

  function alternarModo(novoModo) {
    setModo(novoModo);
    setErro("");
    setSenha("");
    setConfirmarSenha("");
    setAvisoRecuperacao(false);
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
      width: 400,
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
    <main className="login-page">
      <section className="login-story-panel" aria-label="Benefícios do Bolso Leve">
        <div className="login-story-brand">
          <span className="brand-mark" aria-hidden="true"><span /><span /></span>
          <span>Bolso Leve</span>
        </div>

        <div className="login-story-copy">
          <p className="login-story-kicker">Equilíbrio financeiro</p>
          <h1>Organize seu dinheiro com clareza.</h1>
          <p>Mais controle para hoje. Mais tranquilidade para amanhã.</p>
        </div>

        <div className="login-illustration" aria-hidden="true">
          <svg viewBox="0 0 560 330" role="presentation">
            <circle cx="350" cy="235" r="128" fill="var(--color-accent-dark)" opacity="0.72" />
            <path d="M272 285 C327 265 403 267 477 285" fill="none" stroke="var(--color-border)" strokeWidth="2" />

            <g opacity="0.95">
              <rect x="286" y="137" width="34" height="148" rx="7" fill="var(--color-accent-dark)" />
              <rect x="331" y="95" width="34" height="190" rx="7" fill="#a8cec4" />
              <rect x="376" y="52" width="34" height="233" rx="7" fill="var(--color-success)" />
              <polyline points="285,145 332,102 377,58 456,22" fill="none" stroke="var(--color-danger)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="456" cy="22" r="9" fill="var(--color-danger)" />
            </g>

            <g>
              <ellipse cx="454" cy="287" rx="38" ry="12" fill="var(--color-danger)" opacity="0.3" />
              <ellipse cx="454" cy="271" rx="38" ry="12" fill="var(--color-danger)" opacity="0.56" />
              <ellipse cx="454" cy="255" rx="38" ry="12" fill="var(--color-danger)" />
              <path d="M454 244 v28" stroke="#f1c4b7" strokeWidth="3" strokeLinecap="round" />
            </g>

            <g>
              <rect x="56" y="194" width="190" height="98" rx="20" fill="var(--color-accent)" />
              <path d="M56 239 h190" stroke="rgba(255,255,255,0.26)" strokeWidth="2" strokeDasharray="5 7" />
              <rect x="76" y="215" width="70" height="9" rx="4.5" fill="rgba(255,255,255,0.32)" />
              <path d="M224 238 h45 a18 18 0 0 1 0 36 h-45 z" fill="var(--color-accent-dark)" />
              <circle cx="247" cy="256" r="9" fill="var(--color-success)" />
            </g>

            <g>
              <ellipse cx="101" cy="300" rx="47" ry="8" fill="var(--color-border)" />
              <path d="M80 299 C72 252 91 226 112 199" fill="none" stroke="var(--color-success)" strokeWidth="5" strokeLinecap="round" />
              <path d="M103 299 C109 257 101 227 80 198" fill="none" stroke="var(--color-success)" strokeWidth="5" strokeLinecap="round" />
              <ellipse cx="80" cy="194" rx="17" ry="25" fill="var(--color-success)" opacity="0.78" transform="rotate(-24 80 194)" />
              <ellipse cx="111" cy="203" rx="16" ry="24" fill="#8ebbb2" transform="rotate(17 111 203)" />
              <ellipse cx="96" cy="224" rx="14" ry="22" fill="var(--color-success)" opacity="0.56" transform="rotate(-12 96 224)" />
            </g>
          </svg>
        </div>

        <p className="login-story-note">Finanças mais simples para uma vida mais leve.</p>
      </section>

      <section className="login-form-panel">
        <form onSubmit={handleSubmit} className="login-form-card">
          <div className="login-mobile-brand">
            <span className="brand-mark" aria-hidden="true"><span /><span /></span>
            <span>Bolso Leve</span>
          </div>

          <div className="login-form-heading">
            <p className="login-form-kicker">{criandoConta ? "Comece hoje" : "Bem-vindo de volta"}</p>
            <h2>{criandoConta ? "Crie sua conta" : "Acesse sua conta"}</h2>
            <p>{criandoConta ? "Leva menos de um minuto para começar." : "Acesse sua conta e continue sua jornada."}</p>
          </div>

          <div className="login-fields">
            <div className="login-field">
              <label htmlFor="login-email">E-mail</label>
              <div className="login-input-wrap">
                <Mail size={18} aria-hidden="true" />
                <input
                  id="login-email"
                  type="email"
                  placeholder="Digite seu e-mail"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete={criandoConta ? "email" : "username"}
                  required
                />
              </div>
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Senha</label>
              <div className="login-input-wrap">
                <Lock size={18} aria-hidden="true" />
                <input
                  id="login-password"
                  type={mostrarSenha ? "text" : "password"}
                  placeholder="Digite sua senha"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  autoComplete={criandoConta ? "new-password" : "current-password"}
                  required
                />
                <button
                  type="button"
                  onClick={() => setMostrarSenha((v) => !v)}
                  className="login-password-toggle"
                  aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
                >
                  {mostrarSenha ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {!criandoConta && (
                <div className="login-field-meta">
                  <label className="login-remember">
                    <input
                      type="checkbox"
                      checked={manterConectado}
                      onChange={(e) => setManterConectado(e.target.checked)}
                    />
                    <span>Manter conectado</span>
                  </label>
                  <button type="button" onClick={() => setAvisoRecuperacao(true)} className="login-link">
                    Esqueci minha senha
                  </button>
                </div>
              )}

              {avisoRecuperacao && (
                <p className="login-inline-message">
                  Recuperação de senha ainda não disponível — fale com quem administra o app.
                </p>
              )}
            </div>

            {criandoConta && (
              <div className="login-field">
                <label htmlFor="login-confirm-password">Confirmar senha</label>
                <div className="login-input-wrap">
                  <Lock size={18} aria-hidden="true" />
                  <input
                    id="login-confirm-password"
                    type={mostrarSenha ? "text" : "password"}
                    placeholder="Repita sua senha"
                    value={confirmarSenha}
                    onChange={(e) => setConfirmarSenha(e.target.value)}
                    autoComplete="new-password"
                    required
                  />
                </div>
              </div>
            )}
          </div>

          {erro && <p className="login-error">{erro}</p>}
          {!criandoConta && tentativas >= BLOQUEADO_APOS && (
            <p className="login-error">Muitas tentativas. Aguarde um momento antes de tentar de novo.</p>
          )}

          <button
            type="submit"
            disabled={(!criandoConta && tentativas >= BLOQUEADO_APOS) || entrando}
            className="login-primary-button"
          >
            {entrando ? (criandoConta ? "Criando conta..." : "Entrando...") : criandoConta ? "Criar conta" : "Entrar"}
          </button>

          {!criandoConta && GOOGLE_CLIENT_ID && (
            <>
              <div className="login-divider"><span /> <b>ou</b> <span /></div>
              <div className="login-google-wrap">
                <div ref={botaoGoogleRef} />
              </div>
              {erroGoogle && <p className="login-error">{erroGoogle}</p>}
            </>
          )}

          <p className="login-signup-copy">
            {criandoConta ? (
              <>Já tem conta? <button type="button" onClick={() => alternarModo("entrar")} className="login-link">Entrar</button></>
            ) : (
              <>Ainda não tem conta? <button type="button" onClick={() => alternarModo("criar")} className="login-link">Criar conta</button></>
            )}
          </p>

          <div className="login-privacy-note">
            <ShieldCheck size={16} aria-hidden="true" />
            <span>Seus dados financeiros ficam só nessa conta.</span>
          </div>
        </form>
      </section>
    </main>
  );
}
