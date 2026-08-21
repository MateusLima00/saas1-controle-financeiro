import { BrowserRouter, Routes, Route } from "react-router-dom";
import LayoutInterno from "./components/LayoutInterno";
import RotaPrivada from "./components/RotaPrivada";
import { ToastProvider } from "./components/ToastProvider";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Extrato from "./pages/Extrato";
import GastosDiarios from "./pages/GastosDiarios";
import Metas from "./pages/Metas";
import Investimentos from "./pages/Investimentos";
import Assinaturas from "./pages/Assinaturas";
import Parcelamentos from "./pages/Parcelamentos";
import Categorias from "./pages/Categorias";
import Contas from "./pages/Contas";

// -----------------------------------------------------------------------
// App.jsx
//
// Define as rotas do app. "/login" fica sozinha (sem sidebar). As demais
// ficam dentro de RotaPrivada (redireciona pro /login se não estiver
// autenticado) + LayoutInterno, que já injeta a sidebar em todas elas.
// -----------------------------------------------------------------------
function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<RotaPrivada />}>
            <Route element={<LayoutInterno />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/extrato" element={<Extrato />} />
              <Route path="/gastos-diarios" element={<GastosDiarios />} />
              <Route path="/metas" element={<Metas />} />
              <Route path="/investimentos" element={<Investimentos />} />
              <Route path="/assinaturas" element={<Assinaturas />} />
              <Route path="/parcelamentos" element={<Parcelamentos />} />
              <Route path="/categorias" element={<Categorias />} />
              <Route path="/contas" element={<Contas />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}

export default App;
