import { useState, useMemo, useEffect } from "react";
import { Download } from "lucide-react";
import { api } from "../api/client";
import { formatDateShort, formatCurrency } from "../utils/format";
import { exportarTransacoesCsv } from "../utils/exportCsv";

// -----------------------------------------------------------------------
// Extrato.jsx
//
// Lista completa de transações. Período e conta filtram no backend
// (GET /transactions?de=&ate=&conta_id=) — com meses de extratos importados,
// filtrar só no front deixaria a lista pesada demais. Categoria e busca por
// texto continuam client-side, em cima do que já veio filtrado.
// -----------------------------------------------------------------------

function primeiroDiaDoMes(data) {
  return new Date(data.getFullYear(), data.getMonth(), 1);
}

function ultimoDiaDoMes(data) {
  return new Date(data.getFullYear(), data.getMonth() + 1, 0);
}

function paraIso(data) {
  return data.toISOString().slice(0, 10);
}

const PERIODOS = [
  { valor: "mes-atual", label: "Mês atual" },
  { valor: "mes-anterior", label: "Mês anterior" },
  { valor: "personalizado", label: "Período personalizado" },
  { valor: "tudo", label: "Todo o histórico" },
];

export default function Extrato() {
  const [periodo, setPeriodo] = useState("mes-atual");
  const [de, setDe] = useState(paraIso(primeiroDiaDoMes(new Date())));
  const [ate, setAte] = useState(paraIso(ultimoDiaDoMes(new Date())));
  const [contaFiltro, setContaFiltro] = useState("todas");
  const [categoriaFiltro, setCategoriaFiltro] = useState("todas");
  const [busca, setBusca] = useState("");

  const [contas, setContas] = useState([]);
  const [transacoes, setTransacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  // Troca de período pré-definido recalcula de/ate automaticamente.
  // "Personalizado" deixa os dois inputs livres pro usuário escolher.
  useEffect(() => {
    const hoje = new Date();
    if (periodo === "mes-atual") {
      setDe(paraIso(primeiroDiaDoMes(hoje)));
      setAte(paraIso(ultimoDiaDoMes(hoje)));
    } else if (periodo === "mes-anterior") {
      const mesAnterior = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
      setDe(paraIso(primeiroDiaDoMes(mesAnterior)));
      setAte(paraIso(ultimoDiaDoMes(mesAnterior)));
    } else if (periodo === "tudo") {
      setDe("");
      setAte("");
    }
  }, [periodo]);

  useEffect(() => {
    api
      .get("/accounts")
      .then(setContas)
      .catch(() => {
        // Falha ao carregar contas não deve travar o extrato — só o
        // filtro por conta fica indisponível.
      });
  }, []);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro("");

    const params = new URLSearchParams();
    if (de) params.set("de", de);
    if (ate) params.set("ate", ate);
    if (contaFiltro !== "todas") params.set("conta_id", contaFiltro);
    const query = params.toString();

    api
      .get(`/transactions${query ? `?${query}` : ""}`)
      .then((data) => ativo && setTransacoes(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar as transações."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, [de, ate, contaFiltro]);

  // Lista de categorias únicas, calculada a partir das transações já
  // filtradas por período/conta (evita ter que manter uma segunda lista
  // fixa e desatualizada).
  const categoriasDisponiveis = useMemo(() => {
    const unicas = new Set(transacoes.map((t) => t.categoria).filter(Boolean));
    return ["todas", ...unicas];
  }, [transacoes]);

  const transacoesFiltradas = useMemo(() => {
    return transacoes.filter((t) => {
      const bateCategoria = categoriaFiltro === "todas" || t.categoria === categoriaFiltro;
      const bateBusca = t.descricao.toLowerCase().includes(busca.toLowerCase());
      return bateCategoria && bateBusca;
    });
  }, [transacoes, categoriaFiltro, busca]);

  function exportarCsv() {
    exportarTransacoesCsv(transacoesFiltradas, `extrato_${de || "tudo"}_a_${ate || "tudo"}.csv`);
  }

  return (
    <div className="p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h1 className="text-lg font-medium">Extrato completo</h1>
        <button
          onClick={exportarCsv}
          disabled={transacoesFiltradas.length === 0}
          className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <Download size={14} />
          Exportar CSV
        </button>
      </div>

      {/* Barra de filtros */}
      <div className="flex flex-wrap gap-2 mb-4">
        <select
          value={periodo}
          onChange={(e) => setPeriodo(e.target.value)}
          className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
        >
          {PERIODOS.map((p) => (
            <option key={p.valor} value={p.valor}>
              {p.label}
            </option>
          ))}
        </select>

        {periodo === "personalizado" && (
          <>
            <input
              type="date"
              value={de}
              onChange={(e) => setDe(e.target.value)}
              className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
            />
            <span className="self-center text-text-muted text-sm">até</span>
            <input
              type="date"
              value={ate}
              onChange={(e) => setAte(e.target.value)}
              className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
            />
          </>
        )}

        <select
          value={contaFiltro}
          onChange={(e) => setContaFiltro(e.target.value)}
          className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
        >
          <option value="todas">Todas as contas</option>
          {contas.map((c) => (
            <option key={c.id} value={c.id}>
              {c.banco}
            </option>
          ))}
        </select>

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
          className="bg-surface-2 border border-border rounded-md px-3 py-1.5 text-sm outline-none flex-1 min-w-[160px] focus:border-accent"
        />
      </div>

      {carregando && <div className="text-sm text-text-muted">Carregando...</div>}
      {erro && <div className="text-sm text-danger">{erro}</div>}

      {/* Tabela de transações — altura fixa com scroll interno, senão
          meses de histórico real deixam a página gigante. */}
      {!carregando && !erro && (
        <div className="bg-surface rounded-xl border border-border overflow-hidden">
          <div className="max-h-[65vh] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface z-10">
                <tr className="text-text-secondary text-xs border-b border-border">
                  <th className="text-left font-normal px-4 py-2">Data</th>
                  <th className="text-left font-normal px-4 py-2">Descrição</th>
                  <th className="text-left font-normal px-4 py-2">Conta</th>
                  <th className="text-left font-normal px-4 py-2">Categoria</th>
                  <th className="text-right font-normal px-4 py-2">Valor</th>
                </tr>
              </thead>
              <tbody>
                {transacoesFiltradas.map((t) => (
                  <tr key={t.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 text-text-secondary whitespace-nowrap">
                      {formatDateShort(t.data)}
                    </td>
                    <td className="px-4 py-2">{t.descricao}</td>
                    <td className="px-4 py-2 text-text-secondary whitespace-nowrap">
                      {t.conta || "—"}
                    </td>
                    <td className="px-4 py-2">
                      <span className="bg-surface-2 text-text-secondary text-xs px-2 py-0.5 rounded-full">
                        {t.categoria}
                      </span>
                    </td>
                    <td
                      className={`px-4 py-2 text-right whitespace-nowrap ${
                        t.tipo === "credit" ? "text-success" : "text-danger"
                      }`}
                    >
                      {t.tipo === "credit" ? "+" : "-"}
                      {formatCurrency(Math.abs(t.valor))}
                    </td>
                  </tr>
                ))}

                {/* Estado vazio: quando o filtro não bate com nada */}
                {transacoesFiltradas.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-text-muted">
                      Nenhuma transação encontrada.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 text-xs text-text-muted border-t border-border">
            {transacoesFiltradas.length} transação(ões)
          </div>
        </div>
      )}
    </div>
  );
}
