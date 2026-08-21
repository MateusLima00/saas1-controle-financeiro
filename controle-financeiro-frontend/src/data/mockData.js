// -----------------------------------------------------------------------
// mockData.js
//
// Dados falsos pra navegar nas telas antes do backend existir. Quando a
// API estiver pronta, cada um desses arrays vira uma chamada fetch/axios
// na respectiva page, guardada em useState (o formato dos objetos foi
// pensado pra já bater com o que o backend provavelmente vai devolver).
// -----------------------------------------------------------------------

// ---- Contas (tabela "accounts", sempre manuais) ------------------------
export const contasMock = [
  { id: 1, banco: "Nubank", tipo: "checking", saldo: 3200, status: "connected", ultimaSync: "há 4h", origem: "manual" },
  { id: 2, banco: "Inter", tipo: "savings", saldo: 5220, status: "connected", ultimaSync: "há 4h", origem: "manual" },
  { id: 3, banco: "C6 Bank", tipo: "credit_card", saldo: -680, status: "error", ultimaSync: "há 2 dias", origem: "manual" },
];

// ---- Transações (tabela "transactions") --------------------------------
export const transacoesMock = [
  { id: 1, data: "03/08", descricao: "Uber", categoria: "Transporte", valor: -32, tipo: "debit" },
  { id: 2, data: "02/08", descricao: "iFood", categoria: "Alimentação", valor: -58, tipo: "debit" },
  { id: 3, data: "01/08", descricao: "Salário", categoria: "Renda", valor: 4200, tipo: "credit" },
  { id: 4, data: "31/07", descricao: "Netflix", categoria: "Assinaturas", valor: -39.9, tipo: "debit" },
  { id: 5, data: "30/07", descricao: "Posto Shell", categoria: "Transporte", valor: -150, tipo: "debit" },
  { id: 6, data: "29/07", descricao: "Mercado Extra", categoria: "Alimentação", valor: -210, tipo: "debit" },
];

// ---- Gasto por categoria no mês (GROUP BY category_id no backend real) -
export const gastosPorCategoriaMock = [
  { categoria: "Alimentação", valor: 268, cor: "var(--color-cat-2)" },
  { categoria: "Transporte", valor: 182, cor: "var(--color-cat-1)" },
  { categoria: "Assinaturas", valor: 40, cor: "var(--color-cat-3)" },
  { categoria: "Outros", valor: 90, cor: "var(--color-cat-5)" },
];

// ---- Categorias cadastradas ---------------------------------------------
export const categoriasMock = [
  { id: 1, nome: "Alimentação", cor: "var(--color-cat-2)", regra: 'contém "ifood", "mercado"' },
  { id: 2, nome: "Transporte", cor: "var(--color-cat-1)", regra: 'contém "uber", "posto", "99"' },
  { id: 3, nome: "Assinaturas", cor: "var(--color-cat-3)", regra: 'contém "netflix", "spotify"' },
  { id: 4, nome: "Renda", cor: "var(--color-text-secondary)", regra: "manual" },
];

// ---- Metas: poupança e planos de viagem juntos numa mesma entidade -----
// "tipo" diferencia poupança comum de plano de viagem só pra exibir um
// selo/ícone diferente — a lógica de progresso é idêntica pros dois.
// "icone" guarda o NOME do ícone da lucide-react (ver IconPicker.jsx).
export const metasMock = [
  {
    id: 1,
    nome: "Viagem para a China",
    tipo: "viagem",
    icone: "Plane",
    cor: "var(--color-cat-1)",
    valorAlvo: 15000,
    valorAtual: 3200,
    prazo: "Dez/2026",
    historico: [
      { data: "01/06", valor: 1000 },
      { data: "01/07", valor: 1200 },
      { data: "01/08", valor: 1000 },
    ],
  },
  {
    id: 2,
    nome: "Reserva de emergência",
    tipo: "poupanca",
    icone: "PiggyBank",
    cor: "var(--color-cat-2)",
    valorAlvo: 10000,
    valorAtual: 6200,
    prazo: null,
    historico: [{ data: "01/07", valor: 3000 }, { data: "01/08", valor: 3200 }],
  },
  {
    id: 3,
    nome: "Notebook novo",
    tipo: "poupanca",
    icone: "Laptop",
    cor: "var(--color-cat-6)",
    valorAlvo: 6000,
    valorAtual: 1400,
    prazo: "Mar/2027",
    historico: [{ data: "01/08", valor: 1400 }],
  },
];

// ---- Investimentos -------------------------------------------------------
export const investimentosMock = [
  {
    id: 1,
    nome: "Tesouro Selic",
    tipo: "Renda fixa",
    icone: "TrendingUp",
    cor: "var(--color-cat-5)",
    valorInvestido: 5000,
    valorAtual: 5320,
  },
  {
    id: 2,
    nome: "Ações (carteira)",
    tipo: "Renda variável",
    icone: "LineChart",
    cor: "var(--color-cat-4)",
    valorInvestido: 2000,
    valorAtual: 1840,
  },
  {
    id: 3,
    nome: "CDB banco X",
    tipo: "Renda fixa",
    icone: "Landmark",
    cor: "var(--color-cat-2)",
    valorInvestido: 3000,
    valorAtual: 3110,
  },
];

// ---- Assinaturas recorrentes ---------------------------------------------
export const assinaturasMock = [
  { id: 1, nome: "Netflix", icone: "Clapperboard", cor: "var(--color-cat-3)", valor: 39.9, ciclo: "Mensal", proximaCobranca: "10/08" },
  { id: 2, nome: "Spotify", icone: "Music", cor: "var(--color-cat-2)", valor: 21.9, ciclo: "Mensal", proximaCobranca: "15/08" },
  { id: 3, nome: "iCloud 200GB", icone: "Cloud", cor: "var(--color-cat-5)", valor: 12.9, ciclo: "Mensal", proximaCobranca: "22/08" },
];

// ---- Evolução de saldo e gasto mês a mês (gráfico do dashboard) --------
// No backend real isso seria uma agregação mensal (GROUP BY mês) sobre
// a tabela de transações/saldos históricos.
export const evolucaoMock = [
  { mes: "Mar", saldo: 5200, gasto: 2680 },
  { mes: "Abr", saldo: 6100, gasto: 2340 },
  { mes: "Mai", saldo: 6800, gasto: 2510 },
  { mes: "Jun", saldo: 7200, gasto: 2190 },
  { mes: "Jul", saldo: 7800, gasto: 2350 },
  { mes: "Ago", saldo: 8420, gasto: 2180 },
];

// ---- Resumo pros cards de métrica do dashboard ---------------------------
// "MesAnterior" só existe pra calcular a setinha de tendência (▲/▼) nos
// cards do topo — quando o backend existir, isso vem de uma agregação
// mensal (GROUP BY mês) em vez de um número solto aqui.
export const resumoMock = {
  saldoTotal: 8420,
  saldoMesAnterior: 7800,
  gastoMes: 2180,
  gastoMesAnterior: 2350,
  ultimaSync: "há 4h",
};
