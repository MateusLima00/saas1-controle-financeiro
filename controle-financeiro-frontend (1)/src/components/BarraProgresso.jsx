// -----------------------------------------------------------------------
// BarraProgresso.jsx
//
// Barra de progresso simples: recebe valor atual e alvo, calcula a
// porcentagem sozinha. Usada em Metas, e pode ser reaproveitada em
// qualquer lugar que precise mostrar "X de Y".
//
// Props:
//  - atual: valor já alcançado
//  - alvo: valor alvo (100%)
//  - cor: cor da barra preenchida (aceita var(--color-cat-X) ou hex)
// -----------------------------------------------------------------------
export default function BarraProgresso({ atual, alvo, cor = "var(--color-accent)" }) {
  // Trava entre 0 e 100 pra não passar do fim da barra visualmente
  // caso o valor atual ultrapasse o alvo (meta batida e continuou guardando).
  const porcentagem = Math.min(100, Math.round((atual / alvo) * 100));

  return (
    <div>
      <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${porcentagem}%`, backgroundColor: cor }}
        />
      </div>
      <div className="flex justify-between text-xs text-text-muted mt-1">
        <span>{porcentagem}%</span>
        <span>
          R$ {atual.toLocaleString("pt-BR")} de R$ {alvo.toLocaleString("pt-BR")}
        </span>
      </div>
    </div>
  );
}
