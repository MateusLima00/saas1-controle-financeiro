import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

// -----------------------------------------------------------------------
// GraficoCategorias.jsx
//
// Gráfico de pizza mostrando o gasto do mês dividido por categoria.
// Recebe os dados já prontos via props (no futuro virão da API,
// agrupados por category_id). Cada item precisa ter: categoria, valor, cor.
// -----------------------------------------------------------------------
export default function GraficoCategorias({ dados }) {
  return (
    // ResponsiveContainer faz o gráfico ocupar 100% do espaço do pai
    // e se ajustar quando a tela muda de tamanho (redimensiona a janela, etc).
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={dados}
          dataKey="valor"
          nameKey="categoria"
          innerRadius={45}
          outerRadius={75}
          paddingAngle={2}
        >
          {/* Cada fatia da pizza pega a cor definida no próprio dado */}
          {dados.map((entrada, index) => (
            <Cell key={index} fill={entrada.cor} stroke="none" />
          ))}
        </Pie>
        <Tooltip
          formatter={(valor) => `R$ ${valor}`}
          contentStyle={{
            background: "#ffffff",
            border: "1px solid #dbe4e3",
            borderRadius: 8,
            fontSize: 12,
            color: "#102f3d",
            boxShadow: "0 8px 24px rgba(23, 59, 74, 0.1)",
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
