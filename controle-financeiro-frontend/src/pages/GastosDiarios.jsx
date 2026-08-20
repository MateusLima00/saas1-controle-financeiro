import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useToast } from "../components/ToastProvider";
import { formatCurrency, formatDateShort } from "../utils/format";

// -----------------------------------------------------------------------
// GastosDiarios.jsx
//
// Tela pensada pra lançar um gasto rapidinho no dia a dia (sem precisar
// esperar a sincronização bancária). Lança via POST /transactions com
// origem "manual" e aparece tanto aqui quanto no Extrato.
// -----------------------------------------------------------------------
function hojeIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function GastosDiarios() {
  const [lancamentos, setLancamentos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [novo, setNovo] = useState({ descricao: "", valor: "", categoriaId: "" });
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const { mostrarToast } = useToast();

  const hoje = hojeIso();

  useEffect(() => {
    let ativo = true;
    Promise.all([api.get("/categories"), api.get("/transactions")])
      .then(([categoriasData, transacoesData]) => {
        if (!ativo) return;
        setCategorias(categoriasData);
        setLancamentos(transacoesData.filter((t) => t.tipo === "debit" && t.origem === "manual").slice(0, 20));
        setNovo((n) => ({ ...n, categoriaId: categoriasData[0]?.id ?? "" }));
      })
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar os dados."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  async function lancar(e) {
    e.preventDefault();
    if (!novo.descricao || !novo.valor || enviando) return;

    setEnviando(true);
    try {
      const transacao = await api.post("/transactions", {
        data: hoje,
        descricao: novo.descricao,
        categoria_id: novo.categoriaId ? Number(novo.categoriaId) : null,
        valor: -Math.abs(Number(novo.valor)),
        tipo: "debit",
        origem: "manual",
      });
      setLancamentos((atual) => [transacao, ...atual]);
      mostrarToast(`Gasto "${novo.descricao}" lançado.`);
      setNovo({ descricao: "", valor: "", categoriaId: categorias[0]?.id ?? "" });
    } catch (err) {
      mostrarToast(err.message || "Não foi possível lançar o gasto.");
    } finally {
      setEnviando(false);
    }
  }

  if (carregando) {
    return <div className="p-6 text-sm text-text-muted">Carregando...</div>;
  }

  if (erro) {
    return <div className="p-6 text-sm text-danger">{erro}</div>;
  }

  const totalHoje = lancamentos
    .filter((l) => l.data === hoje)
    .reduce((soma, l) => soma + Math.abs(l.valor), 0);

  return (
    <div className="p-6">
      <h1 className="text-lg font-medium mb-1">Gastos diários</h1>
      <p className="text-sm text-text-secondary mb-4">
        Gasto lançado hoje: <span className="text-danger">{formatCurrency(totalHoje)}</span>
      </p>

      {/* Form de lançamento rápido - sempre visível, é o foco da tela */}
      <form onSubmit={lancar} className="bg-surface rounded-card border border-border p-4 mb-4 flex gap-2 flex-wrap">
        <input
          type="text"
          placeholder="O que você comprou?"
          value={novo.descricao}
          onChange={(e) => setNovo({ ...novo, descricao: e.target.value })}
          className="flex-1 min-w-[160px] bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
          required
        />
        <select
          value={novo.categoriaId}
          onChange={(e) => setNovo({ ...novo, categoriaId: e.target.value })}
          className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1.5 text-sm outline-none"
        >
          {categorias.map((c) => (
            <option key={c.id} value={c.id}>{c.nome}</option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Valor (R$)"
          value={novo.valor}
          onChange={(e) => setNovo({ ...novo, valor: e.target.value })}
          className="w-32 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
          required
        />
        <button type="submit" disabled={enviando} className="bg-accent text-white rounded-[var(--radius-control)] px-4 py-1.5 text-sm disabled:opacity-60">
          {enviando ? "Lançando..." : "Lançar"}
        </button>
      </form>

      <div className="bg-surface rounded-card border border-border overflow-hidden">
        {lancamentos.map((l, i) => (
          <div
            key={l.id}
            className={`flex justify-between items-center px-4 py-2.5 text-sm ${i !== lancamentos.length - 1 ? "border-b border-border" : ""}`}
          >
            <div>
              <span className="text-text-muted mr-2">{formatDateShort(l.data)}</span>
              {l.descricao}
              <span className="text-xs text-text-muted ml-2">· {l.categoria}</span>
            </div>
            <span className="text-danger">-{formatCurrency(Math.abs(l.valor))}</span>
          </div>
        ))}

        {lancamentos.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-text-muted">Nenhum gasto lançado ainda.</div>
        )}
      </div>
    </div>
  );
}
