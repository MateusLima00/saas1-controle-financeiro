import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, Check } from "lucide-react";
import MetricCard from "../components/MetricCard";
import GraficoCategorias from "../components/GraficoCategorias";
import GraficoEvolucao from "../components/GraficoEvolucao";
import ListaTransacoes from "../components/ListaTransacoes";
import BarraProgresso from "../components/BarraProgresso";
import { IconeDinamico } from "../components/IconPicker";
import { formatCurrency, formatDateShort } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Dashboard.jsx
//
// Visão geral: métricas do topo + transações/gráfico + resumo das metas,
// investimentos e assinaturas (cada seção linka pra tela cheia dela).
// Dados vêm da API real (GET /dashboard/resumo, /dashboard/evolucao,
// /dashboard/gastos-por-categoria, /transactions, /goals, /investments,
// /subscriptions).
// -----------------------------------------------------------------------

// Calcula a variação percentual entre dois valores, em texto pronto pra
// exibir (ex: "+8% vs mês passado"). Sem tratamento especial de zero,
// os cards que usam isso já garantem que o "anterior" nunca é 0.
function calcularTendencia(atual, anterior) {
  const variacao = (((atual - anterior) / anterior) * 100).toFixed(0);
  const sinal = variacao >= 0 ? "+" : "";
  return { texto: `${sinal}${variacao}% vs mês passado`, positiva: variacao >= 0 };
}

export default function Dashboard() {
  const [atualizando, setAtualizando] = useState(false);
  const [atualizadoAgora, setAtualizadoAgora] = useState(false);

  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [resumo, setResumo] = useState(null);
  const [transacoes, setTransacoes] = useState([]);
  const [gastosPorCategoria, setGastosPorCategoria] = useState([]);
  const [evolucao, setEvolucao] = useState([]);
  const [metas, setMetas] = useState([]);
  const [investimentos, setInvestimentos] = useState([]);
  const [assinaturas, setAssinaturas] = useState([]);

  function carregarDados() {
    return Promise.all([
      api.get("/dashboard/resumo"),
      api.get("/transactions"),
      api.get("/dashboard/gastos-por-categoria"),
      api.get("/dashboard/evolucao"),
      api.get("/goals"),
      api.get("/investments"),
      api.get("/subscriptions"),
    ]).then(([resumoData, transacoesData, gastosData, evolucaoData, metasData, investimentosData, assinaturasData]) => {
      setResumo(resumoData);
      setTransacoes(transacoesData);
      setGastosPorCategoria(gastosData);
      setEvolucao(evolucaoData);
      setMetas(metasData);
      setInvestimentos(investimentosData);
      setAssinaturas(assinaturasData);
    });
  }

  useEffect(() => {
    let ativo = true;
    carregarDados()
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar o dashboard."))
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

  const ultimasTransacoes = transacoes.slice(0, 3).map((t) => ({ ...t, data: formatDateShort(t.data) }));

  const tendenciaSaldo = calcularTendencia(resumo.saldoTotal, resumo.saldoMesAnterior);
  // Gasto subir é uma tendência ruim, mesmo com número positivo - por isso
  // inverte o sinal de "positiva" (verde) aqui.
  const tendenciaGasto = calcularTendencia(resumo.gastoMes, resumo.gastoMesAnterior);
  tendenciaGasto.positiva = !tendenciaGasto.positiva;

  // Resumo de investimentos: total investido x valor atual
  const totalInvestido = investimentos.reduce((s, i) => s + i.valorInvestido, 0);
  const totalInvestimentoAtual = investimentos.reduce((s, i) => s + i.valorAtual, 0);
  const rendimento =
    totalInvestido > 0 ? (((totalInvestimentoAtual - totalInvestido) / totalInvestido) * 100).toFixed(1) : "0.0";

  // Resumo de assinaturas: soma mensal
  const totalAssinaturas = assinaturas.reduce((s, a) => s + a.valor, 0);

  function handleAtualizarAgora() {
    if (atualizando) return;

    setAtualizando(true);
    carregarDados()
      .then(() => {
        setAtualizadoAgora(true);
        setTimeout(() => setAtualizadoAgora(false), 2500);
      })
      .catch((err) => setErro(err.message || "Não foi possível atualizar o dashboard."))
      .finally(() => setAtualizando(false));
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-5">
        <h1 className="text-lg font-medium">Visão geral</h1>
        <button
          onClick={handleAtualizarAgora}
          disabled={atualizando}
          className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {atualizadoAgora ? (
            <>
              <Check size={13} className="text-success" />
              Atualizado
            </>
          ) : (
            <>
              <RefreshCw size={13} className={atualizando ? "animate-spin" : ""} />
              {atualizando ? "Atualizando..." : "Atualizar agora"}
            </>
          )}
        </button>
      </div>

      {/* Cards de resumo */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <MetricCard
          label="Saldo total"
          value={formatCurrency(resumo.saldoTotal)}
          tendencia={tendenciaSaldo.texto}
          tendenciaPositiva={tendenciaSaldo.positiva}
        />
        <MetricCard
          label="Gasto do mês"
          value={formatCurrency(resumo.gastoMes)}
          color="text-danger"
          tendencia={tendenciaGasto.texto}
          tendenciaPositiva={tendenciaGasto.positiva}
        />
        <MetricCard label="Última sync" value={atualizadoAgora ? "agora mesmo" : resumo.ultimaSync} />
      </div>

      {/* Evolução de saldo x gasto nos últimos meses */}
      <div className="bg-surface rounded-card border border-border p-4 mb-4">
        <div className="flex justify-between items-center mb-2">
          <div className="text-xs text-text-secondary">Evolução mensal</div>
          <div className="flex items-center gap-3 text-[11px] text-text-muted">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: "var(--color-accent)" }} />
              Saldo
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: "var(--color-danger)" }} />
              Gasto
            </span>
          </div>
        </div>
        <GraficoEvolucao dados={evolucao} />
      </div>

      {/* Transações + gráfico lado a lado */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <Link to="/extrato" className="bg-surface rounded-card border border-border p-4 hover:border-accent/50 transition-colors">
          <div className="text-xs text-text-secondary mb-2">Últimas transações</div>
          <ListaTransacoes transacoes={ultimasTransacoes} />
        </Link>

        <div className="bg-surface rounded-card border border-border p-4">
          <div className="text-xs text-text-secondary mb-2">Gasto por categoria</div>
          <GraficoCategorias dados={gastosPorCategoria} />
        </div>
      </div>

      {/* Metas e planos - mostra as 2 primeiras, o resto fica na tela /metas */}
      <div className="bg-surface rounded-card border border-border p-4 mb-4">
        <div className="flex justify-between items-center mb-3">
          <div className="text-xs text-text-secondary">Metas e planos</div>
          <Link to="/metas" className="text-xs text-accent">Ver todas</Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {metas.slice(0, 2).map((meta) => (
            <div key={meta.id} className="bg-surface-2 rounded-[var(--radius-control)] p-3">
              <div className="flex items-center gap-2 mb-2">
                <span style={{ color: meta.cor }}>
                  <IconeDinamico nome={meta.icone} size={16} />
                </span>
                <span className="text-sm">{meta.nome}</span>
              </div>
              <BarraProgresso atual={meta.valorAtual} alvo={meta.valorAlvo} cor={meta.cor} />
            </div>
          ))}
        </div>
      </div>

      {/* Investimentos + Assinaturas lado a lado, resumidos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Link to="/investimentos" className="bg-surface rounded-card border border-border p-4 hover:border-accent/50 transition-colors">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs text-text-secondary">Investimentos</div>
            <span className="text-xs text-accent">Ver todos</span>
          </div>
          <div className="text-xl font-medium">{formatCurrency(totalInvestimentoAtual)}</div>
          <div className={`text-xs mt-1 ${rendimento >= 0 ? "text-success" : "text-danger"}`}>
            {rendimento >= 0 ? "+" : ""}
            {rendimento}% desde o investido
          </div>
        </Link>

        <Link to="/assinaturas" className="bg-surface rounded-card border border-border p-4 hover:border-accent/50 transition-colors">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs text-text-secondary">Assinaturas</div>
            <span className="text-xs text-accent">Ver todas</span>
          </div>
          <div className="text-xl font-medium text-danger">{formatCurrency(totalAssinaturas)}/mês</div>
          <div className="text-xs text-text-muted mt-1">{assinaturas.length} assinaturas ativas</div>
        </Link>
      </div>
    </div>
  );
}
