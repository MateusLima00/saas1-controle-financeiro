import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { Bell, CalendarDays, ChevronDown, Menu, Plus, Search } from "lucide-react";
import Sidebar from "./Sidebar";
import { api } from "../api/client";

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
};

function Topbar({ titulo, nomeUsuario }) {
  const inicial = (nomeUsuario || "?").charAt(0).toUpperCase();
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

        <button type="button" aria-label="Notificações" className="relative grid place-items-center w-10 h-10 rounded-[var(--radius-control)] text-text-secondary hover:bg-surface hover:text-text-primary transition-colors">
          <Bell size={19} />
          <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-danger" />
        </button>

        <div className="flex items-center gap-2 pl-2 border-l border-border text-text-primary text-sm">
          <span className="grid place-items-center w-9 h-9 rounded-full border-2 border-surface bg-accent text-white font-bold">{inicial}</span>
          <strong className="hidden lg:block font-semibold truncate max-w-[140px]">{nomeUsuario || "..."}</strong>
          <ChevronDown size={15} className="text-text-muted" />
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
  const [nomeUsuario, setNomeUsuario] = useState("");
  const { pathname } = useLocation();
  const titulo = titulos[pathname] || "Visão geral";

  useEffect(() => {
    let ativo = true;
    api
      .get("/auth/me")
      .then((data) => ativo && setNomeUsuario((data.email || "").split("@")[0]))
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
        <Topbar titulo={titulo} nomeUsuario={nomeUsuario} />
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
