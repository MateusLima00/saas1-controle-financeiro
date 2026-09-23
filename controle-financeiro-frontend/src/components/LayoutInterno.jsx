import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Menu } from "lucide-react";
import Sidebar from "./Sidebar";

// -----------------------------------------------------------------------
// LayoutInterno.jsx
//
// "Casca" comum de todas as telas depois do login: sidebar + a página
// atual renderizada à direita (via <Outlet />, do react-router). Em telas
// pequenas a sidebar vira um drawer (fechado por padrão) acionado por um
// botão hambúrguer numa barra de topo que só aparece no mobile.
// -----------------------------------------------------------------------
export default function LayoutInterno() {
  const [menuAberto, setMenuAberto] = useState(false);

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
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-border bg-surface sticky top-0 z-30">
          <button
            onClick={() => setMenuAberto(true)}
            aria-label="Abrir menu"
            className="text-text-secondary hover:text-text-primary p-1 -ml-1"
          >
            <Menu size={20} />
          </button>
          <span className="font-medium text-sm">Bolso Leve</span>
        </div>

        <main className="flex-1 min-w-0 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
