import * as Icons from "lucide-react";
import { Check } from "lucide-react";

// -----------------------------------------------------------------------
// IconPicker.jsx
//
// Guardamos nos dados só o NOME do ícone (ex: "Plane", "PiggyBank") e o
// valor da COR (ex: "var(--color-cat-1)") em vez do componente/hex em si
// — assim dá pra salvar isso no banco de dados como texto simples no
// futuro. Esse arquivo exporta:
//
//  - <IconeDinamico nome="Plane" />        renderiza o ícone certo a partir do nome
//  - <SeletorIconeCor />                    popup com grade de ícones + cores,
//                                            usado nos formulários de "novo/nova X"
// -----------------------------------------------------------------------

// Lista curta e organizada por assunto (evita jogar os 1500+ ícones da lib
// inteira numa grade gigante e desorganizada).
export const ICONES_DISPONIVEIS = {
  Viagem: ["Plane", "MapPin", "Palmtree", "Ship", "Luggage"],
  Poupança: ["PiggyBank", "Wallet", "Landmark", "Coins"],
  Tecnologia: ["Laptop", "Smartphone", "Monitor", "Headphones"],
  Investimentos: ["TrendingUp", "LineChart", "Building2", "BarChart3"],
  Assinaturas: ["Clapperboard", "Music", "Cloud", "Newspaper", "Gamepad2"],
  Casa: ["Home", "Car", "ShoppingCart", "Utensils"],
};

// Paleta de cores do tema (as mesmas --color-cat-N do index.css), com
// nome em português pra exibir como legenda/tooltip.
export const CORES_DISPONIVEIS = [
  { nome: "Índigo", valor: "var(--color-cat-1)" },
  { nome: "Verde", valor: "var(--color-cat-2)" },
  { nome: "Laranja", valor: "var(--color-cat-3)" },
  { nome: "Rosa", valor: "var(--color-cat-4)" },
  { nome: "Azul", valor: "var(--color-cat-5)" },
  { nome: "Âmbar", valor: "var(--color-cat-6)" },
];

// Renderiza o ícone certo dado o nome salvo nos dados.
// Se o nome não existir na lib (typo, etc), cai num ícone genérico
// em vez de quebrar a tela.
export function IconeDinamico({ nome, size = 18, className = "" }) {
  const Icone = Icons[nome] || Icons.CircleDashed;
  return <Icone size={size} className={className} />;
}

// -----------------------------------------------------------------------
// SeletorIconeCor
//
// Substitui o antigo <select> por uma grade visual: primeiro escolhe a
// cor (bolinhas), depois o ícone (grade de botões agrupada por assunto).
// A pré-visualização mostra como o ícone vai aparecer nas listas.
//
// Props: icone, cor (valores atuais) / onChangeIcone, onChangeCor
// -----------------------------------------------------------------------
export function SeletorIconeCor({ icone, cor, onChangeIcone, onChangeCor }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <span
          className="w-11 h-11 shrink-0 rounded-[var(--radius-control)] flex items-center justify-center"
          style={{ backgroundColor: "var(--color-surface-2)", color: cor }}
        >
          <IconeDinamico nome={icone} size={22} />
        </span>
        <div className="flex-1">
          <div className="text-xs text-text-muted mb-1.5">Cor</div>
          <div className="flex items-center gap-2 flex-wrap">
            {CORES_DISPONIVEIS.map((c) => (
              <button
                key={c.valor}
                type="button"
                title={c.nome}
                aria-label={`Cor ${c.nome}`}
                onClick={() => onChangeCor(c.valor)}
                className="w-6 h-6 rounded-full flex items-center justify-center ring-offset-2 ring-offset-surface transition-transform hover:scale-110"
                style={{ backgroundColor: c.valor, outline: cor === c.valor ? `2px solid ${c.valor}` : "none", outlineOffset: 2 }}
              >
                {cor === c.valor && <Check size={12} className="text-white" strokeWidth={3} />}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div className="text-xs text-text-muted mb-1.5">Ícone</div>
        <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
          {Object.entries(ICONES_DISPONIVEIS).map(([grupo, nomes]) => (
            <div key={grupo}>
              <div className="text-[11px] text-text-muted mb-1">{grupo}</div>
              <div className="flex gap-1.5 flex-wrap">
                {nomes.map((nome) => {
                  const selecionado = nome === icone;
                  return (
                    <button
                      key={nome}
                      type="button"
                      title={nome}
                      aria-label={`Ícone ${nome}`}
                      onClick={() => onChangeIcone(nome)}
                      className="w-9 h-9 rounded-[var(--radius-control)] flex items-center justify-center border transition-colors"
                      style={{
                        borderColor: selecionado ? cor : "var(--color-border)",
                        backgroundColor: selecionado ? "var(--color-surface-2)" : "transparent",
                        color: selecionado ? cor : "var(--color-text-secondary)",
                      }}
                    >
                      <IconeDinamico nome={nome} size={17} />
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
