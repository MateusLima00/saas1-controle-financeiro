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
        <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="mes" tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "var(--color-text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
        <Tooltip
          formatter={(valor, nome) => [`R$ ${valor.toLocaleString("pt-BR")}`, nome === "saldo" ? "Saldo" : "Gasto"]}
          labelStyle={{ color: "var(--color-text-primary)" }}
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--color-text-primary)",
            boxShadow: "var(--shadow-card)",
          }}
        />
        <Area type="monotone" dataKey="saldo" stroke="var(--color-accent)" strokeWidth={2.5} fill="var(--color-accent-dark)" fillOpacity={0.28} />
        <Area type="monotone" dataKey="gasto" stroke="var(--color-danger)" strokeWidth={2.5} fill="var(--color-danger)" fillOpacity={0.08} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
