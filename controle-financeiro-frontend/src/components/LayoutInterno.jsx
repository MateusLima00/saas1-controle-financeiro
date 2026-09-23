import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Bell,
  CalendarClock,
  CalendarDays,
  ChevronDown,
  LogOut,
  Menu,
  Plus,
  Search,
  Settings,
  TrendingUp,
} from "lucide-react";
import Sidebar from "./Sidebar";
import { api } from "../api/client";
import { sair } from "../utils/auth";

const ICONE_POR_TIPO = {
  conta_a_vencer: CalendarClock,
  saldo_baixo: AlertTriangle,
  gasto_incomum: TrendingUp,
};

// -----------------------------------------------------------------------
// LayoutInterno.jsx
//
// "Casca" comum de todas as telas depois do login: sidebar + a página
// atual renderizada à direita (via <Outlet />, do react-router). Em telas
// pequenas a sidebar vira um drawer (fechado por padrão) acionado por um
// botão hambúrguer numa barra de topo que só aparece no mobile.
// -----------------------------------------------------------------------
const titulos = {
  "/": "Visão geral",
  "/extrato": "Transações",
  "/gastos-diarios": "Gastos diários",
  "/orcamento": "Orçamento",
  "/metas": "Metas e planos",
  "/investimentos": "Investimentos",
  "/assinaturas": "Assinaturas",
  "/parcelamentos": "Cartão/Parcelamentos",
  "/categorias": "Categorias",
  "/contas": "Contas",
  "/perfil": "Configurações",
};

function Topbar({ titulo, nomeUsuario, email }) {
  const inicial = (nomeUsuario || "?").charAt(0).toUpperCase();
  const [menuUsuarioAberto, setMenuUsuarioAberto] = useState(false);
  const [notifAberto, setNotifAberto] = useState(false);
  const [notificacoes, setNotificacoes] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    let ativo = true;
    function carregar() {
      api
        .get("/dashboard/notificacoes")
        .then((data) => ativo && setNotificacoes(data))
        .catch(() => {});
    }
    carregar();
    // Recarrega a cada 5 min pra pegar conta que passou a vencer hoje,
    // sem precisar dar refresh na página inteira.
    const intervalo = setInterval(carregar, 5 * 60 * 1000);
    return () => {
      ativo = false;
      clearInterval(intervalo);
    };
  }, []);

  async function handleSair() {
    await sair();
    navigate("/login");
  }

  return (
    <header className="hidden md:flex items-center justify-between gap-5 min-h-[76px] px-6 lg:px-12 border-b border-border bg-bg">
      <div className="flex items-center gap-2 text-xs text-text-muted whitespace-nowrap">
        <span>Bolso Leve</span>
        <span className="text-border">/</span>
        <strong className="text-text-primary font-semibold">{titulo}</strong>
      </div>

      <div className="flex items-center justify-end gap-2 min-w-0">
        <label className="flex items-center gap-2 w-[min(33vw,410px)] h-11 px-3.5 rounded-[var(--radius-control)] border border-border bg-surface text-text-muted">
          <Search size={18} aria-hidden="true" />
          <input
            aria-label="Buscar transações, contas ou categorias"
            className="min-w-0 flex-1 border-0 outline-none bg-transparent text-sm text-text-primary placeholder:text-text-muted"
            placeholder="Buscar transações, contas ou categorias..."
          />
        </label>

        <div className="relative">
          <button
            type="button"
            aria-label="Notificações"
            aria-haspopup="true"
            aria-expanded={notifAberto}
            onClick={() => setNotifAberto((v) => !v)}
            className="relative grid place-items-center w-10 h-10 rounded-[var(--radius-control)] text-text-secondary hover:bg-surface hover:text-text-primary transition-colors"
          >
            <Bell size={19} />
            {notificacoes.length > 0 && (
              <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-danger text-white text-[10px] font-bold grid place-items-center">
                {notificacoes.length > 9 ? "9+" : notificacoes.length}
              </span>
            )}
          </button>

          {notifAberto && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setNotifAberto(false)} />
              <div className="absolute right-0 top-[calc(100%+8px)] z-40 w-80 max-h-[70vh] overflow-y-auto bg-surface border border-border rounded-card p-2">
                <div className="px-2.5 py-2 mb-1 border-b border-border">
                  <p className="text-sm font-bold">Notificações</p>
                </div>
                {notificacoes.length === 0 ? (
                  <p className="text-xs text-text-muted text-center py-6">Nenhum alerta no momento.</p>
                ) : (
                  <div className="flex flex-col">
                    {notificacoes.map((n) => {
                      const Icone = ICONE_POR_TIPO[n.tipo] || Bell;
                      return (
                        <div key={n.id} className="flex items-start gap-2.5 px-2.5 py-2.5 border-b border-border last:border-b-0">
                          <span
                            className={`w-8 h-8 shrink-0 rounded-full grid place-items-center ${
                              n.urgente ? "text-danger bg-[color-mix(in_srgb,var(--color-danger)_16%,var(--color-surface))]" : "text-text-secondary bg-surface-2"
                            }`}
                          >
                            <Icone size={15} />
                          </span>
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate">{n.titulo}</p>
                            <p className="text-xs text-text-muted">{n.mensagem}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => setMenuUsuarioAberto((v) => !v)}
            className="flex items-center gap-2 pl-2 border-l border-border text-text-primary text-sm"
            aria-haspopup="true"
            aria-expanded={menuUsuarioAberto}
          >
            <span className="grid place-items-center w-9 h-9 rounded-full border-2 border-surface bg-accent text-white font-bold">{inicial}</span>
            <strong className="hidden lg:block font-semibold truncate max-w-[140px]">{nomeUsuario || "..."}</strong>
            <ChevronDown size={15} className={`text-text-muted transition-transform ${menuUsuarioAberto ? "rotate-180" : ""}`} />
          </button>

          {menuUsuarioAberto && (
            <>
              {/* Overlay invisível só pra capturar clique fora e fechar o popup */}
              <div className="fixed inset-0 z-30" onClick={() => setMenuUsuarioAberto(false)} />
              <div className="absolute right-0 top-[calc(100%+8px)] z-40 w-60 bg-surface border border-border rounded-card p-2">
                <div className="px-2.5 py-2 mb-1 border-b border-border">
                  <p className="text-xs text-text-muted truncate">{email || "..."}</p>
                </div>
                <Link
                  to="/perfil"
                  onClick={() => setMenuUsuarioAberto(false)}
                  className="flex items-center gap-2 px-2.5 py-2 rounded-[var(--radius-control)] text-sm text-text-secondary hover:bg-surface-2 hover:text-text-primary transition-colors"
                >
                  <Settings size={15} />
                  Configurações e dados
                </Link>
                <button
                  onClick={handleSair}
                  className="w-full flex items-center gap-2 px-2.5 py-2 rounded-[var(--radius-control)] text-sm text-text-secondary hover:bg-surface-2 hover:text-danger transition-colors"
                >
                  <LogOut size={15} />
                  Sair
                </button>
              </div>
            </>
          )}
        </div>

        <label className="hidden xl:flex items-center gap-2 h-11 px-3 rounded-[var(--radius-control)] border border-border bg-surface text-text-secondary text-sm">
          <CalendarDays size={16} />
          <select aria-label="Selecionar período" defaultValue="maio" className="border-0 outline-none bg-transparent text-text-primary">
            <option value="maio">Maio de 2024</option>
            <option value="abril">Abril de 2024</option>
          </select>
        </label>

        <Link to="/extrato" className="inline-flex items-center justify-center gap-2 h-11 px-3.5 rounded-[var(--radius-control)] bg-accent text-white text-sm font-bold shadow-sm hover:bg-text-primary transition-colors whitespace-nowrap">
          <Plus size={17} />
          Nova transação
        </Link>
      </div>
    </header>
  );
}

export default function LayoutInterno() {
  const [menuAberto, setMenuAberto] = useState(false);
  const [email, setEmail] = useState("");
  const { pathname } = useLocation();
  const titulo = titulos[pathname] || "Visão geral";
  const nomeUsuario = email.split("@")[0];

  useEffect(() => {
    let ativo = true;
    api
      .get("/auth/me")
      .then((data) => ativo && setEmail(data.email || ""))
      .catch(() => {});
    return () => {
      ativo = false;
    };
  }, []);

  return (
    <div className="flex min-h-screen bg-bg text-text-primary">
      {menuAberto && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={() => setMenuAberto(false)}
        />
      )}

      <Sidebar aberto={menuAberto} onFechar={() => setMenuAberto(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        <Topbar titulo={titulo} nomeUsuario={nomeUsuario} email={email} />
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-border bg-surface sticky top-0 z-30">
          <button
            onClick={() => setMenuAberto(true)}
            aria-label="Abrir menu"
            className="text-text-secondary hover:text-text-primary p-1 -ml-1"
          >
            <Menu size={20} />
          </button>
          <Link to="/" className="flex items-center gap-2 font-semibold text-sm text-text-primary">
            <span className="brand-mark" aria-hidden="true"><span /><span /></span>
            Bolso Leve
          </Link>
        </div>

        <main className="flex-1 min-w-0 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
