import { useState, useMemo, useEffect } from "react";
import { api } from "../api/client";
import { formatDateShort } from "../utils/format";

// -----------------------------------------------------------------------
// Extrato.jsx
//
// Lista completa de transações, com filtro por categoria e busca por texto.
// Os filtros rodam 100% no front, em cima da lista vinda de GET /transactions.
// -----------------------------------------------------------------------
export default function Extrato() {
  const [categoriaFiltro, setCategoriaFiltro] = useState("todas");
  const [busca, setBusca] = useState("");
  const [transacoes, setTransacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let ativo = true;
    api
      .get("/transactions")
      .then((data) => ativo && setTransacoes(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar as transações."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  // Lista de categorias únicas, calculada a partir das transações
  // (evita ter que manter uma segunda lista fixa e desatualizada)
  const categoriasDisponiveis = useMemo(() => {
    const unicas = new Set(transacoes.map((t) => t.categoria).filter(Boolean));
    return ["todas", ...unicas];
  }, [transacoes]);

  // useMemo evita recalcular o filtro em toda renderização,
  // só refaz quando categoriaFiltro, busca ou a lista original mudam.
  const transacoesFiltradas = useMemo(() => {
    return transacoes.filter((t) => {
      const bateCategoria = categoriaFiltro === "todas" || t.categoria === categoriaFiltro;
      const bateBusca = t.descricao.toLowerCase().includes(busca.toLowerCase());
      return bateCategoria && bateBusca;
    });
  }, [transacoes, categoriaFiltro, busca]);

  if (carregando) {
    return <div className="p-6 text-sm text-text-muted">Carregando...</div>;
  }

  if (erro) {
    return <div className="p-6 text-sm text-danger">{erro}</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-lg font-medium mb-4">Extrato completo</h1>

      {/* Barra de filtros */}
      <div className="flex gap-2 mb-4">
        <select
          value={categoriaFiltro}
          onChange={(e) => setCategoriaFiltro(e.target.value)}
          className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
        >
          {categoriasDisponiveis.map((cat) => (
            <option key={cat} value={cat}>
              {cat === "todas" ? "Todas as categorias" : cat}
            </option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Buscar por descrição..."
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          className="bg-surface-2 border border-border rounded-md px-3 py-1.5 text-sm outline-none flex-1 focus:border-accent"
        />
      </div>

      {/* Tabela de transações */}
      <div className="bg-surface rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-text-secondary text-xs border-b border-border">
              <th className="text-left font-normal px-4 py-2">Data</th>
              <th className="text-left font-normal px-4 py-2">Descrição</th>
              <th className="text-left font-normal px-4 py-2">Categoria</th>
              <th className="text-right font-normal px-4 py-2">Valor</th>
            </tr>
          </thead>
          <tbody>
            {transacoesFiltradas.map((t) => (
              <tr key={t.id} className="border-b border-border last:border-0">
                <td className="px-4 py-2 text-text-secondary">{formatDateShort(t.data)}</td>
                <td className="px-4 py-2">{t.descricao}</td>
                <td className="px-4 py-2">
                  <span className="bg-surface-2 text-text-secondary text-xs px-2 py-0.5 rounded-full">
                    {t.categoria}
                  </span>
                </td>
                <td
                  className={`px-4 py-2 text-right ${
                    t.tipo === "credit" ? "text-success" : "text-danger"
                  }`}
                >
                  {t.tipo === "credit" ? "+" : "-"}R$ {Math.abs(t.valor).toLocaleString("pt-BR")}
                </td>
              </tr>
            ))}

            {/* Estado vazio: quando o filtro não bate com nada */}
            {transacoesFiltradas.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-text-muted">
                  Nenhuma transação encontrada.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
