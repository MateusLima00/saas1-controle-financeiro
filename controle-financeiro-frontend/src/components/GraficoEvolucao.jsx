import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

// -----------------------------------------------------------------------
// GraficoEvolucao.jsx
//
// Gráfico de área mostrando saldo e gasto mês a mês, pra dar uma noção
// de tendência que os cards sozinhos não mostram. Recebe os dados via
// props (mes, saldo, gasto) — no futuro vem de uma agregação mensal.
// -----------------------------------------------------------------------
export default function GraficoEvolucao({ dados }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={dados} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="corSaldo" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="corGasto" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-danger)" stopOpacity={0.25} />
            <stop offset="100%" stopColor="var(--color-danger)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="mes" tick={{ fill: "#7d8997", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "#7d8997", fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
        <Tooltip
          formatter={(valor, nome) => [`R$ ${valor.toLocaleString("pt-BR")}`, nome === "saldo" ? "Saldo" : "Gasto"]}
          labelStyle={{ color: "#102f3d" }}
          contentStyle={{
            background: "#ffffff",
            border: "1px solid #dbe4e3",
            borderRadius: 8,
            fontSize: 12,
            color: "#102f3d",
            boxShadow: "0 8px 24px rgba(23, 59, 74, 0.1)",
          }}
        />
        <Area type="monotone" dataKey="saldo" stroke="var(--color-accent)" strokeWidth={2} fill="url(#corSaldo)" />
        <Area type="monotone" dataKey="gasto" stroke="var(--color-danger)" strokeWidth={2} fill="url(#corGasto)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
