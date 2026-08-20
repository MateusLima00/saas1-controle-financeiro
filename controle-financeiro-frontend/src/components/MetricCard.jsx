// -----------------------------------------------------------------------
// MetricCard.jsx
//
// Card simples pra mostrar um número grande com um rótulo em cima.
// Usado no Dashboard pros 3 cards do topo (saldo, gasto do mês, última sync).
//
// Props:
//  - label: texto pequeno acima do número (ex: "Saldo total")
//  - value: valor a ser exibido (ex: "R$ 8.420")
//  - color: classe de cor do texto do valor (opcional, default = cor normal)
//  - tendencia: texto opcional de variação (ex: "+8% vs mês passado")
//  - tendenciaPositiva: se a variação deve ser exibida em verde (bom) ou
//    vermelho (ruim) — o "bom"/"ruim" depende do card (gasto subir é ruim,
//    saldo subir é bom), por isso quem decide é quem chama o componente.
// -----------------------------------------------------------------------
export default function MetricCard({ label, value, color = "text-text-primary", tendencia, tendenciaPositiva }) {
  return (
    <div className="bg-surface rounded-card p-4">
      <div className="text-xs text-text-secondary">{label}</div>
      <div className={`text-2xl font-medium mt-1 ${color}`}>{value}</div>
      {tendencia && (
        <div className={`text-xs mt-1 ${tendenciaPositiva ? "text-success" : "text-danger"}`}>
          {tendencia}
        </div>
      )}
    </div>
  );
}
