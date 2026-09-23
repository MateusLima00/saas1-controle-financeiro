import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, LogOut, Mail, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../api/client";
import { sair, trocarSenha } from "../utils/auth";
import { useToast } from "../components/ToastProvider";

// -----------------------------------------------------------------------
// Perfil.jsx
//
// "Configurações e dados do usuário" — acessada pelo popup do avatar no
// topo (LayoutInterno.jsx). Por enquanto: email da conta + troca de
// senha. Cresce aqui conforme o app ganhar mais preferências de conta.
// -----------------------------------------------------------------------
export default function Perfil() {
  const [email, setEmail] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [senhaAtual, setSenhaAtual] = useState("");
  const [senhaNova, setSenhaNova] = useState("");
  const [confirmarSenhaNova, setConfirmarSenhaNova] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erroSenha, setErroSenha] = useState("");
  const { mostrarToast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    let ativo = true;
    api
      .get("/auth/me")
      .then((data) => ativo && setEmail(data.email))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  async function handleTrocarSenha(e) {
    e.preventDefault();
    setErroSenha("");

    if (senhaNova.length < 6) {
      setErroSenha("A nova senha precisa ter pelo menos 6 caracteres.");
      return;
    }
    if (senhaNova !== confirmarSenhaNova) {
      setErroSenha("As senhas novas não conferem.");
      return;
    }

    setSalvando(true);
    try {
      await trocarSenha(senhaAtual, senhaNova);
      mostrarToast("Senha atualizada.");
      setSenhaAtual("");
      setSenhaNova("");
      setConfirmarSenhaNova("");
    } catch (err) {
      setErroSenha(err instanceof ApiError ? err.message : "Não foi possível trocar a senha.");
    } finally {
      setSalvando(false);
    }
  }

  async function handleSair() {
    await sair();
    navigate("/login");
  }

  if (carregando) {
    return <div className="p-6 text-sm text-text-muted">Carregando...</div>;
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl mb-1">Configurações da conta</h1>
      <p className="text-text-secondary text-sm mb-5">Seus dados de acesso e preferências.</p>

      <div className="bg-surface rounded-card border border-border p-5 mb-4">
        <h2 className="text-sm font-bold mb-3">Conta</h2>
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Mail size={15} />
          {email}
        </div>
      </div>

      <div className="bg-surface rounded-card border border-border p-5 mb-4">
        <h2 className="text-sm font-bold mb-3">Trocar senha</h2>
        <form onSubmit={handleTrocarSenha} className="flex flex-col gap-3 max-w-sm">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-bold text-text-primary">Senha atual</label>
            <input
              type={mostrarSenha ? "text" : "password"}
              value={senhaAtual}
              onChange={(e) => setSenhaAtual(e.target.value)}
              className="w-full bg-surface border border-border rounded-[var(--radius-control)] px-3 py-2 text-sm outline-none focus:border-success focus:ring-2 focus:ring-success/15 transition-colors"
              autoComplete="current-password"
              required
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-bold text-text-primary">Nova senha</label>
            <div className="relative">
              <input
                type={mostrarSenha ? "text" : "password"}
                value={senhaNova}
                onChange={(e) => setSenhaNova(e.target.value)}
                className="w-full bg-surface border border-border rounded-[var(--radius-control)] px-3 py-2 pr-9 text-sm outline-none focus:border-success focus:ring-2 focus:ring-success/15 transition-colors"
                autoComplete="new-password"
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
          <div className="flex flex-col gap-1">
            <label className="text-xs font-bold text-text-primary">Confirmar nova senha</label>
            <input
              type={mostrarSenha ? "text" : "password"}
              value={confirmarSenhaNova}
              onChange={(e) => setConfirmarSenhaNova(e.target.value)}
              className="w-full bg-surface border border-border rounded-[var(--radius-control)] px-3 py-2 text-sm outline-none focus:border-success focus:ring-2 focus:ring-success/15 transition-colors"
              autoComplete="new-password"
              required
            />
          </div>

          {erroSenha && <p className="text-xs text-danger">{erroSenha}</p>}

          <button
            type="submit"
            disabled={salvando}
            className="self-start bg-accent text-white rounded-[var(--radius-control)] px-4 py-2 text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {salvando ? "Salvando..." : "Salvar nova senha"}
          </button>
        </form>
        <p className="flex items-center gap-1.5 text-xs text-text-muted mt-3">
          <ShieldCheck size={13} />
          Contas criadas via Google não têm senha própria pra trocar aqui.
        </p>
      </div>

      <button
        onClick={handleSair}
        className="flex items-center gap-2 text-sm text-text-secondary hover:text-danger transition-colors"
      >
        <LogOut size={16} />
        Sair da conta
      </button>
    </div>
  );
}
