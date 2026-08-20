// -----------------------------------------------------------------------
// format.js
//
// Helpers de formatação usados em várias telas — centralizados aqui pra
// não repetir "R$" + toLocaleString("pt-BR") copiado em cada página.
// -----------------------------------------------------------------------

// Formata um número como moeda brasileira: formatCurrency(1234.5) -> "R$ 1.234,50"
export function formatCurrency(valor) {
  return `R$ ${(valor ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Calcula a variação percentual entre dois valores, protegendo contra
// divisão por zero (retorna "0.0" nesse caso em vez de NaN/Infinity).
export function calcularVariacaoPercentual(atual, anterior) {
  if (!anterior) return "0.0";
  return (((atual - anterior) / anterior) * 100).toFixed(1);
}

// Converte uma data ISO ("2026-08-01") vinda da API pra formato curto
// brasileiro ("01/08"), igual ao que o mockData.js usava.
export function formatDateShort(dataIso) {
  if (!dataIso) return "";
  const [ano, mes, dia] = dataIso.split("-");
  return `${dia}/${mes}`;
}
