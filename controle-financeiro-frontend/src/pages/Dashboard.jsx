import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  RefreshCw,
  Check,
  ArrowDownRight,
  ArrowUpRight,
  Eye,
  EyeOff,
  ChevronRight,
  CreditCard,
  Wallet2,
  PieChart,
} from "lucide-react";
import GraficoEvolucao from "../components/GraficoEvolucao";
import { IconeDinamico } from "../components/IconPicker";
import { formatCurrency, formatDateShort } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Dashboard.jsx
//
// Visão geral: saldo em destaque + entradas/saídas do mês, fluxo de caixa,
// próximas contas (assinaturas + parcelas pendentes) e transações
// recentes — layout espelha a referência de design (balance-card + stat
// cards + painéis), mas os dados vêm todos da API real.
// -----------------------------------------------------------------------

function saudacao() {
  const hora = new Date().getHours();
  if (hora < 12) return "Bom dia";
  if (hora < 18) return "Boa tarde";
  return "Boa noite";
}

function calcularTendencia(atual, anterior) {
  if (!anterior) return { texto: "sem comparação com o mês anterior", positiva: true };
  const variacao = (((atual - anterior) / anterior) * 100).toFixed(0);
  const sinal = variacao >= 0 ? "+" : "";
  return { texto: `${sinal}${variacao}% vs mês passado`, positiva: variacao >= 0 };
}

// Converte "DD/MM" (assinaturas) numa data completa, assumindo o ano atual
// (ou o próximo, se esse dia/mês já passou) — mesma regra do backend.
function proximaDataDeString(ddmm) {
  if (!ddmm) return null;
  const [dia, mes] = ddmm.split("/").map(Number);
  if (!dia || !mes) return null;
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  let data = new Date(hoje.getFullYear(), mes - 1, dia);
  if (data < hoje) data = new Date(hoje.getFullYear() + 1, mes - 1, dia);
  return data;
}

function diasAteTexto(data) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const dias = Math.round((data - hoje) / (1000 * 60 * 60 * 24));
  if (dias < 0) return `Venceu há ${Math.abs(dias)} dia(s)`;
  if (dias === 0) return "Vencimento hoje";
  if (dias === 1) return "Vencimento amanhã";
  return `Vencimento em ${dias} dias`;
}

export default function Dashboard() {
  const [atualizando, setAtualizando] = useState(false);
  const [atualizadoAgora, setAtualizadoAgora] = useState(false);
  const [saldoVisivel, setSaldoVisivel] = useState(true);

  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [resumo, setResumo] = useState(null);
  const [transacoes, setTransacoes] = useState([]);
  const [evolucao, setEvolucao] = useState([]);
  const [metas, setMetas] = useState([]);
  const [investimentos, setInvestimentos] = useState([]);
  const [assinaturas, setAssinaturas] = useState([]);
  const [faturas, setFaturas] = useState([]);
  const [parcelamentos, setParcelamentos] = useState([]);
  const [saldoPeriodo, setSaldoPeriodo] = useState(null);
  const [emailUsuario, setEmailUsuario] = useState("");

  function carregarDados() {
    return Promise.all([
      api.get("/dashboard/resumo"),
      api.get("/transactions"),
      api.get("/dashboard/evolucao"),
      api.get("/goals"),
      api.get("/investments"),
      api.get("/subscriptions"),
      api.get("/parcelamentos/fatura"),
      api.get("/parcelamentos"),
      api.get("/dashboard/saldo-periodo"),
      api.get("/auth/me"),
    ]).then(
      ([
        resumoData,
        transacoesData,
        evolucaoData,
        metasData,
        investimentosData,
        assinaturasData,
        faturasData,
        parcelamentosData,
        saldoPeriodoData,
        meData,
      ]) => {
        setResumo(resumoData);
        setTransacoes(transacoesData);
        setEvolucao(evolucaoData);
        setMetas(metasData);
        setInvestimentos(investimentosData);
        setAssinaturas(assinaturasData);
        setFaturas(faturasData);
        setParcelamentos(parcelamentosData);
        setSaldoPeriodo(saldoPeriodoData);
        setEmailUsuario(meData.email);
      }
    );
  }

  useEffect(() => {
    let ativo = true;
    carregarDados()
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar o dashboard."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (carregando) {
    return <div className="p-6 text-sm text-text-muted">Carregando...</div>;
  }

  if (erro) {
    return <div className="p-6 text-sm text-danger">{erro}</div>;
  }

  const nomeUsuario = emailUsuario.split("@")[0] || "";
  const ultimasTransacoes = transacoes.slice(0, 5);

  const tendenciaSaldo = calcularTendencia(resumo.saldoTotal, resumo.saldoMesAnterior);
  const entradas = saldoPeriodo?.receitaRealizada ?? 0;
  const saidas = saldoPeriodo?.despesaRealizada ?? 0;

  // Resumo de investimentos: total investido x valor atual
  const totalInvestido = investimentos.reduce((s, i) => s + i.valorInvestido, 0);
  const totalInvestimentoAtual = investimentos.reduce((s, i) => s + i.valorAtual, 0);
  const rendimento =
    totalInvestido > 0 ? (((totalInvestimentoAtual - totalInvestido) / totalInvestido) * 100).toFixed(1) : "0.0";

  const totalAssinaturas = assinaturas.reduce((s, a) => s + a.valor, 0);
  const totalFaturaMes = faturas.reduce((s, f) => s + f.totalMes, 0);

  // "Próximas contas": assinaturas + parcelas pendentes, unificadas e
  // ordenadas pela data mais próxima — as 4 primeiras aparecem no painel.
  const proximasContas = [
    ...assinaturas
      .map((a) => {
        const data = proximaDataDeString(a.proximaCobranca);
        return data && { tipo: "assinatura", nome: a.nome, valor: a.valor, icone: a.icone, data };
      })
      .filter(Boolean),
    ...parcelamentos.flatMap((compra) =>
      compra.parcelas
        .filter((p) => !p.paga)
        .map((p) => ({
          tipo: "parcela",
          nome: `${compra.descricao} (${p.numero}/${compra.numParcelas})`,
          valor: p.valor,
          icone: "CreditCard",
          data: new Date(`${p.dataVencimento}T00:00:00`),
        }))
    ),
  ]
    .sort((a, b) => a.data - b.data)
    .slice(0, 4);

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

  const mesAtual = new Date().toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

  return (
    <div className="p-6 max-w-[1420px] mx-auto">
      {/* Cabeçalho: saudação + mês + atualizar */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl mb-1">
            {saudacao()}
            {nomeUsuario ? `, ${nomeUsuario}` : ""}
          </h1>
          <p className="text-text-secondary text-sm">Aqui está o resumo das suas finanças.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="capitalize text-sm text-text-secondary border border-border rounded-[var(--radius-control)] px-3 py-2 bg-surface">
            {mesAtual}
          </span>
          <button
            onClick={handleAtualizarAgora}
            disabled={atualizando}
            className="text-sm px-3 py-2 rounded-[var(--radius-control)] border border-border bg-surface hover:bg-surface-2 transition-colors flex items-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {atualizadoAgora ? (
              <>
                <Check size={13} className="text-success" />
                Atualizado
              </>
            ) : (
              <>
                <RefreshCw size={13} className={atualizando ? "animate-spin" : ""} />
                {atualizando ? "Atualizando..." : "Atualizar"}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Saldo disponível + Entradas + Saídas */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.65fr)_repeat(2,minmax(220px,1fr))] gap-3.5 mb-4">
        <div className="rounded-card border border-[color-mix(in_srgb,var(--color-success)_28%,var(--color-border))] bg-[color-mix(in_srgb,var(--color-success)_14%,var(--color-surface))] p-6 flex items-center justify-between overflow-hidden min-h-[170px]">
          <div>
            <p className="flex items-center gap-2 text-text-primary text-sm font-semibold">
              Saldo disponível
              <button
                onClick={() => setSaldoVisivel((v) => !v)}
                className="text-text-secondary hover:text-text-primary"
                aria-label={saldoVisivel ? "Ocultar saldo" : "Mostrar saldo"}
              >
                {saldoVisivel ? <Eye size={14} /> : <EyeOff size={14} />}
              </button>
            </p>
            <p className="mt-3 mb-2.5 text-text-primary" style={{ fontFamily: "var(--font-heading)", fontSize: "clamp(2rem, 4vw, 2.75rem)", fontWeight: 800, letterSpacing: "-0.03em" }}>
              {saldoVisivel ? formatCurrency(resumo.saldoTotal) : "R$ ••••••"}
            </p>
            <p className={`flex items-center gap-1 text-xs font-semibold ${tendenciaSaldo.positiva ? "text-success" : "text-danger"}`}>
              {tendenciaSaldo.positiva ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              {tendenciaSaldo.texto}
            </p>
          </div>
          <svg viewBox="0 0 140 90" className="w-24 sm:w-36 h-auto shrink-0" aria-hidden="true">
            <g opacity="0.85">
              <rect x="8" y="55" width="16" height="30" rx="3" fill="var(--color-success)" opacity="0.35" />
              <rect x="32" y="42" width="16" height="43" rx="3" fill="var(--color-success)" opacity="0.55" />
              <rect x="56" y="26" width="16" height="59" rx="3" fill="var(--color-success)" opacity="0.75" />
              <rect x="80" y="10" width="16" height="75" rx="3" fill="var(--color-success)" />
            </g>
            <polyline points="8,58 32,45 56,29 96,12" fill="none" stroke="var(--color-success)" strokeWidth="3" strokeLinecap="round" />
          </svg>
        </div>

        <div className="rounded-card border border-border bg-surface p-5 flex gap-3.5 min-h-[170px]">
          <span className="w-11 h-11 shrink-0 rounded-full flex items-center justify-center text-success bg-[color-mix(in_srgb,var(--color-success)_18%,var(--color-surface))]">
            <ArrowDownRight size={18} />
          </span>
          <div>
            <p className="text-text-primary text-sm font-bold mb-2">Entradas</p>
            <p className="mb-2" style={{ fontFamily: "var(--font-heading)", fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.03em" }}>
              {formatCurrency(entradas)}
            </p>
            <p className="text-xs text-text-muted">realizado este mês</p>
          </div>
        </div>

        <div className="rounded-card border border-border bg-surface p-5 flex gap-3.5 min-h-[170px]">
          <span className="w-11 h-11 shrink-0 rounded-full flex items-center justify-center text-danger bg-[color-mix(in_srgb,var(--color-danger)_16%,var(--color-surface))]">
            <ArrowUpRight size={18} />
          </span>
          <div>
            <p className="text-text-primary text-sm font-bold mb-2">Saídas</p>
            <p className="mb-2" style={{ fontFamily: "var(--font-heading)", fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.03em" }}>
              {formatCurrency(saidas)}
            </p>
            <p className="text-xs text-text-muted">realizado este mês</p>
          </div>
        </div>
      </div>

      {/* Fluxo de caixa + Próximas contas */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.7fr)_minmax(300px,1fr)] gap-3.5 mb-4">
        <div className="bg-surface rounded-card border border-border p-5">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-sm font-bold">Fluxo de caixa</h2>
            <div className="flex items-center gap-3 text-[11px] text-text-muted">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: "var(--color-success)" }} />
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

        <div className="bg-surface rounded-card border border-border p-5">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-sm font-bold">Próximas contas</h2>
            <Link to="/parcelamentos" className="text-xs text-success font-semibold">
              Ver tudo
            </Link>
          </div>
          {proximasContas.length === 0 ? (
            <p className="text-xs text-text-muted py-4">Nenhuma conta prevista pros próximos dias.</p>
          ) : (
            <div className="flex flex-col">
              {proximasContas.map((conta, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-2.5 py-3 ${i !== proximasContas.length - 1 ? "border-b border-border" : ""}`}
                >
                  <span className="w-8 h-8 shrink-0 rounded-full flex items-center justify-center text-text-primary bg-surface-2">
                    {conta.tipo === "parcela" ? <CreditCard size={15} /> : <IconeDinamico nome={conta.icone} size={15} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm truncate">{conta.nome}</p>
                    <p className="text-[11px] text-text-muted">{diasAteTexto(conta.data)}</p>
                  </div>
                  <span className="text-sm font-semibold whitespace-nowrap">{formatCurrency(conta.valor)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Transações recentes */}
      <div className="bg-surface rounded-card border border-border p-5 mb-4 overflow-hidden">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-bold">Transações recentes</h2>
          <Link to="/extrato" className="text-xs text-success font-semibold flex items-center gap-0.5">
            Ver tudo <ChevronRight size={13} />
          </Link>
        </div>
        {ultimasTransacoes.length === 0 ? (
          <p className="text-xs text-text-muted py-4">Nenhuma transação lançada ainda.</p>
        ) : (
          <div className="overflow-x-auto -mx-5">
            <table className="w-full text-sm border-collapse min-w-[560px]">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-text-muted">
                  <th className="font-bold px-5 pb-2.5">Data</th>
                  <th className="font-bold px-2 pb-2.5">Descrição</th>
                  <th className="font-bold px-2 pb-2.5">Categoria</th>
                  <th className="font-bold px-2 pb-2.5">Conta</th>
                  <th className="font-bold px-5 pb-2.5 text-right">Valor</th>
                </tr>
              </thead>
              <tbody>
                {ultimasTransacoes.map((t) => (
                  <tr key={t.id} className="border-t border-border">
                    <td className="px-5 py-2.5 whitespace-nowrap text-text-secondary">{formatDateShort(t.data)}</td>
                    <td className="px-2 py-2.5 text-text-primary font-medium">{t.descricao}</td>
                    <td className="px-2 py-2.5">
                      {t.categoria ? (
                        <span className="inline-flex px-2 py-0.5 rounded-full text-[11px]" style={{ backgroundColor: "var(--color-surface-2)", color: "var(--color-text-secondary)" }}>
                          {t.categoria}
                        </span>
                      ) : (
                        <span className="text-text-muted text-xs">—</span>
                      )}
                    </td>
                    <td className="px-2 py-2.5 text-text-secondary whitespace-nowrap">{t.conta || "—"}</td>
                    <td className={`px-5 py-2.5 text-right whitespace-nowrap font-semibold ${t.tipo === "credit" ? "text-success" : "text-danger"}`}>
                      {t.tipo === "credit" ? "+" : "-"}{formatCurrency(Math.abs(t.valor))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Metas e planos - mostra as 2 primeiras, o resto fica na tela /metas */}
      {metas.length > 0 && (
        <div className="bg-surface rounded-card border border-border p-5 mb-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-sm font-bold">Metas e planos</h2>
            <Link to="/metas" className="text-xs text-success font-semibold">Ver todas</Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {metas.slice(0, 2).map((meta) => {
              const porcentagem = Math.min(100, Math.round((meta.valorAtual / meta.valorAlvo) * 100));
              return (
                <div key={meta.id} className="bg-surface-2 rounded-[var(--radius-control)] p-3.5">
                  <div className="flex items-center gap-2 mb-2.5">
                    <span style={{ color: meta.cor }}>
                      <IconeDinamico nome={meta.icone} size={16} />
                    </span>
                    <span className="text-sm font-medium">{meta.nome}</span>
                  </div>
                  <div className="h-1.5 bg-border rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${porcentagem}%`, backgroundColor: meta.cor || "var(--color-success)" }} />
                  </div>
                  <div className="flex justify-between text-xs text-text-muted mt-1.5">
                    <span>{porcentagem}%</span>
                    <span>{formatCurrency(meta.valorAtual)} de {formatCurrency(meta.valorAlvo)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Investimentos + Assinaturas + Cartão/Parcelamentos + Orçamento, resumidos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <Link to="/investimentos" className="bg-surface rounded-card border border-border p-5 hover:border-success/50 transition-colors">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs text-text-secondary">Investimentos</div>
            <span className="text-xs text-success font-semibold">Ver todos</span>
          </div>
          <div className="text-xl font-bold">{formatCurrency(totalInvestimentoAtual)}</div>
          <div className={`text-xs mt-1 ${rendimento >= 0 ? "text-success" : "text-danger"}`}>
            {rendimento >= 0 ? "+" : ""}
            {rendimento}% desde o investido
          </div>
        </Link>

        <Link to="/assinaturas" className="bg-surface rounded-card border border-border p-5 hover:border-success/50 transition-colors">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs text-text-secondary">Assinaturas</div>
            <span className="text-xs text-success font-semibold">Ver todas</span>
          </div>
          <div className="text-xl font-bold text-danger">{formatCurrency(totalAssinaturas)}/mês</div>
          <div className="text-xs text-text-muted mt-1">{assinaturas.length} assinaturas ativas</div>
        </Link>

        <Link to="/parcelamentos" className="bg-surface rounded-card border border-border p-5 hover:border-success/50 transition-colors">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs text-text-secondary flex items-center gap-1.5">
              <Wallet2 size={13} />
              Cartão/Parcelamentos
            </div>
            <span className="text-xs text-success font-semibold">Ver todos</span>
          </div>
          <div className="text-xl font-bold text-danger">{formatCurrency(totalFaturaMes)}</div>
          <div className="text-xs text-text-muted mt-1">fatura prevista do mês</div>
        </Link>

        <Link to="/orcamento" className="bg-surface rounded-card border border-border p-5 hover:border-success/50 transition-colors">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs text-text-secondary flex items-center gap-1.5">
              <PieChart size={13} />
              Orçamento do mês
            </div>
            <span className="text-xs text-success font-semibold">Ver detalhes</span>
          </div>
          <div className={`text-xl font-bold ${(saldoPeriodo?.saldo ?? 0) >= 0 ? "text-success" : "text-danger"}`}>
            {formatCurrency(saldoPeriodo?.saldo ?? 0)}
          </div>
          <div className="text-xs text-text-muted mt-1">receita − despesa realizadas</div>
        </Link>
      </div>
    </div>
  );
}
