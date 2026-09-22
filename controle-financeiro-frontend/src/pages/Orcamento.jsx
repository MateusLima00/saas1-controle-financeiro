import { useEffect, useState } from "react";
import { Wallet, TrendingDown, TrendingUp } from "lucide-react";
import BarraProgresso from "../components/BarraProgresso";
import { formatCurrency } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Orcamento.jsx
//
// Previsto x Realizado por categoria, igual ao bloco central da planilha
// de equilíbrio financeiro: cada categoria tem um valor orçado (Previsto,
// cadastrado em Categorias) e um valor Realizado (soma automática das
// transações do mês, feita pelo backend). O Saldo do período é
// Receita realizada - Despesa realizada, igual à fórmula da planilha.
// Dados vêm de GET /dashboard/orcamento e GET /dashboard/saldo-periodo.
// -----------------------------------------------------------------------
const LABEL_GRUPO = {
  receita: "Receitas",
  fixo: "Gastos fixos",
  investimento: "Investimentos",
  doacao: "Doações",
  passivo: "Gastos passivos",
};

export default function Orcamento() {
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [grupos, setGrupos] = useState([]);
  const [saldo, setSaldo] = useState(null);

  useEffect(() => {
    let ativo = true;
    Promise.all([api.get("/dashboard/orcamento"), api.get("/dashboard/saldo-periodo")])
      .then(([orcamentoData, saldoData]) => {
        if (!ativo) return;
        setGrupos(orcamentoData);
        setSaldo(saldoData);
      })
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar o orçamento."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  if (carregando) {
    return <div className="p-6 text-sm text-text-muted">Carregando...</div>;
  }

  if (erro) {
    return <div className="p-6 text-sm text-danger">{erro}</div>;
  }

  const saldoPositivo = (saldo?.saldo ?? 0) >= 0;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-5">
        <h1 className="text-lg font-medium">Orçamento</h1>
        <p className="text-xs text-text-muted">Previsto x realizado do mês atual</p>
      </div>

      {/* Saldo do período: Receita realizada - Despesa realizada */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div className="bg-surface rounded-card border border-border p-4">
          <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
            <TrendingUp size={13} />
            Receita realizada
          </div>
          <div className="text-xl font-medium text-success">{formatCurrency(saldo?.receitaRealizada ?? 0)}</div>
          <div className="text-xs text-text-muted mt-1">previsto {formatCurrency(saldo?.receitaPrevista ?? 0)}</div>
        </div>

        <div className="bg-surface rounded-card border border-border p-4">
          <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
            <TrendingDown size={13} />
            Despesa realizada
          </div>
          <div className="text-xl font-medium text-danger">{formatCurrency(saldo?.despesaRealizada ?? 0)}</div>
          <div className="text-xs text-text-muted mt-1">previsto {formatCurrency(saldo?.despesaPrevista ?? 0)}</div>
        </div>

        <div className="bg-surface rounded-card border border-border p-4">
          <div className="flex items-center gap-1.5 text-xs text-text-secondary mb-1">
            <Wallet size={13} />
            Saldo do mês
          </div>
          <div className={`text-xl font-medium ${saldoPositivo ? "text-success" : "text-danger"}`}>
            {formatCurrency(saldo?.saldo ?? 0)}
          </div>
          <div className="text-xs text-text-muted mt-1">receita − despesa realizadas</div>
        </div>
      </div>

      {/* Previsto x Realizado por grupo/categoria */}
      {grupos.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <Wallet size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhuma categoria cadastrada ainda.</p>
          <p className="text-xs text-text-muted">
            Cadastre categorias em "Categorias" com um valor Previsto pra ver o orçamento aqui.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {grupos.map((grupo) => (
            <div key={grupo.grupo} className="bg-surface rounded-card border border-border p-4">
              <div className="flex justify-between items-center mb-3">
                <div className="text-sm font-medium">{LABEL_GRUPO[grupo.grupo] ?? grupo.grupo}</div>
                <div className="text-xs text-text-muted">
                  {formatCurrency(grupo.realizado)} de {formatCurrency(grupo.previsto)}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {grupo.categorias.map((cat) => (
                  <div key={cat.categoriaId} className="bg-surface-2 rounded-[var(--radius-control)] p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: cat.cor }} />
                      <span className="text-sm">{cat.categoria}</span>
                    </div>
                    {cat.previsto > 0 ? (
                      <BarraProgresso atual={cat.realizado} alvo={cat.previsto} cor={cat.cor} />
                    ) : (
                      <div className="text-xs text-text-muted">
                        {formatCurrency(cat.realizado)} realizado — sem previsto cadastrado
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
