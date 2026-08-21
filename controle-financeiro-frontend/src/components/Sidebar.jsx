import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Receipt,
  Tags,
  Landmark,
  Target,
  TrendingUp,
  CalendarClock,
  Wallet2,
  LogOut,
  X,
} from "lucide-react";
import { sair } from "../utils/auth";

// -----------------------------------------------------------------------
// Sidebar.jsx
//
// Menu lateral. Em telas >= md fica sempre visível, fixa à esquerda. Em
// telas menores vira um drawer que desliza por cima do conteúdo (aberto/
// fechado controlado pelo LayoutInterno, junto com o botão hambúrguer).
// Pra adicionar uma tela nova no menu, basta acrescentar um item na lista
// abaixo (label, path, ícone) - o resto (rota ativa, estilo) já funciona
// sozinho via NavLink.
// -----------------------------------------------------------------------
const itensMenu = [
  { label: "Dashboard", path: "/", Icone: LayoutDashboard },
  { label: "Extrato", path: "/extrato", Icone: Receipt },
  { label: "Gastos diários", path: "/gastos-diarios", Icone: CalendarClock },
  { label: "Metas e planos", path: "/metas", Icone: Target },
  { label: "Investimentos", path: "/investimentos", Icone: TrendingUp },
  { label: "Assinaturas", path: "/assinaturas", Icone: Wallet2 },
  { label: "Categorias", path: "/categorias", Icone: Tags },
  { label: "Contas", path: "/contas", Icone: Landmark },
];

export default function Sidebar({ aberto = false, onFechar = () => {} }) {
  const navigate = useNavigate();

  async function handleSair() {
    await sair();
    navigate("/login");
  }

  return (
    <aside
      className={`fixed md:static inset-y-0 left-0 z-50 w-64 md:w-56 bg-surface border-r border-border p-4 flex flex-col gap-1 shrink-0 transform transition-transform duration-200 ease-out md:translate-x-0 ${
        aberto ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      <div className="font-medium text-base mb-6 px-2 flex items-center justify-between">
        Finanças
        <button
          onClick={onFechar}
          aria-label="Fechar menu"
          className="md:hidden text-text-muted hover:text-text-primary p-1 -mr-1"
        >
          <X size={18} />
        </button>
      </div>

      {itensMenu.map(({ label, path, Icone }) => (
        <NavLink
          key={path}
          to={path}
          end={path === "/"}
          onClick={onFechar}
          className={({ isActive }) =>
            `flex items-center gap-2 px-2 py-2 rounded-[var(--radius-control)] text-sm transition-colors ${
              isActive ? "bg-accent-dark text-accent" : "text-text-secondary hover:bg-surface-2"
            }`
          }
        >
          <Icone size={16} />
          {label}
        </NavLink>
      ))}

      <button
        onClick={handleSair}
        className="flex items-center gap-2 px-2 py-2 rounded-[var(--radius-control)] text-sm text-text-secondary hover:bg-surface-2 hover:text-danger transition-colors mt-auto"
      >
        <LogOut size={16} />
        Sair
      </button>
    </aside>
  );
}
