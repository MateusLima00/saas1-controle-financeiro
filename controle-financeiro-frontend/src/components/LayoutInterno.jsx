import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

// -----------------------------------------------------------------------
// LayoutInterno.jsx
//
// "Casca" comum de todas as telas depois do login: sidebar fixa à esquerda
// + a página atual renderizada à direita (via <Outlet />, do react-router).
// Assim cada page (Dashboard, Extrato, etc) só precisa se preocupar com
// o próprio conteúdo, sem repetir a sidebar em cada uma.
// -----------------------------------------------------------------------
export default function LayoutInterno() {
  return (
    <div className="flex min-h-screen bg-bg text-text-primary">
      <Sidebar />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
