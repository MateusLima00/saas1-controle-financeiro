import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, LogOut, Mail, ShieldCheck, User } from "lucide-react";
import { api, ApiError } from "../api/client";
import { atualizarNome, sair, trocarSenha } from "../utils/auth";
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
  const [nome, setNome] = useState("");
  const [nomeSalvo, setNomeSalvo] = useState("");
  const [salvandoNome, setSalvandoNome] = useState(false);
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
      .then((data) => {
        if (!ativo) return;
        setEmail(data.email);
        setNome(data.nome || "");
        setNomeSalvo(data.nome || "");
      })
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  async function handleSalvarNome(e) {
    e.preventDefault();
    if (!nome.trim() || nome.trim() === nomeSalvo || salvandoNome) return;

    setSalvandoNome(true);
    try {
      const data = await atualizarNome(nome.trim());
      setNome(data.nome || "");
      setNomeSalvo(data.nome || "");
      mostrarToast("Nome atualizado.");
    } catch (err) {
      mostrarToast(err instanceof ApiError ? err.message : "Não foi possível salvar o nome.", "erro");
    } finally {
      setSalvandoNome(false);
    }
  }

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
    <div className="p-6 max-w-xl mx-auto">
      <div className="text-center mb-6">
        <h1 className="text-2xl mb-1">Configurações da conta</h1>
        <p className="text-text-secondary text-sm">Seus dados de acesso e preferências.</p>
      </div>

      <div className="bg-surface rounded-card border border-border p-5 mb-4">
        <h2 className="text-sm font-bold mb-3 text-center">Conta</h2>
        <div className="flex items-center justify-center gap-2 text-sm text-text-secondary mb-4">
          <Mail size={15} />
          {email}
        </div>

        <form onSubmit={handleSalvarNome} className="flex flex-col gap-1 max-w-sm mx-auto">
          <label className="text-xs font-bold text-text-primary">Nome de exibição</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Como você quer ser chamado"
                maxLength={60}
                className="w-full bg-surface border border-border rounded-[var(--radius-control)] pl-9 pr-3 py-2 text-sm outline-none focus:border-success focus:ring-2 focus:ring-success/15 transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={salvandoNome || !nome.trim() || nome.trim() === nomeSalvo}
              className="bg-accent text-white rounded-[var(--radius-control)] px-4 py-2 text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {salvandoNome ? "Salvando..." : "Salvar"}
            </button>
          </div>
          <p className="text-[11px] text-text-muted mt-1">Aparece na barra do topo e na saudação do painel.</p>
        </form>
      </div>

      <div className="bg-surface rounded-card border border-border p-5 mb-4">
        <h2 className="text-sm font-bold mb-3 text-center">Trocar senha</h2>
        <form onSubmit={handleTrocarSenha} className="flex flex-col gap-3 max-w-sm mx-auto">
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
            className="self-center bg-accent text-white rounded-[var(--radius-control)] px-4 py-2 text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {salvando ? "Salvando..." : "Salvar nova senha"}
          </button>
        </form>
        <p className="flex items-center justify-center gap-1.5 text-xs text-text-muted mt-3">
          <ShieldCheck size={13} />
          Contas criadas via Google não têm senha própria pra trocar aqui.
        </p>
      </div>

      <div className="flex justify-center">
        <button
          onClick={handleSair}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-danger transition-colors"
        >
          <LogOut size={16} />
          Sair da conta
        </button>
      </div>
    </div>
  );
}
