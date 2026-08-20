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
} from "lucide-react";
import { sair } from "../utils/auth";

// -----------------------------------------------------------------------
// Sidebar.jsx
//
// Menu lateral fixo. Pra adicionar uma tela nova no menu, basta acrescentar
// um item na lista abaixo (label, path, ícone) - o resto (rota ativa,
// estilo) já funciona sozinho via NavLink.
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

export default function Sidebar() {
  const navigate = useNavigate();

  async function handleSair() {
    await sair();
    navigate("/login");
  }

  return (
    <aside className="w-56 bg-surface border-r border-border p-4 flex flex-col gap-1 shrink-0">
      <div className="font-medium text-base mb-6 px-2">Finanças</div>

      {itensMenu.map(({ label, path, Icone }) => (
        <NavLink
          key={path}
          to={path}
          end={path === "/"}
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
