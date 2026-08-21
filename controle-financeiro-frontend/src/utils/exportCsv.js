// Exporta uma lista de transações (já filtrada na tela) como CSV, formatado
// de forma consistente (data ISO, valor com sinal, ponto decimal) —
// intencionalmente mais organizado que o extrato bruto que sai do banco,
// pra poder reabrir no Excel/Sheets sem gambiarra de formatação.
export function exportarTransacoesCsv(transacoes, nomeArquivo) {
  const cabecalho = ["Data", "Descricao", "Conta", "Categoria", "Valor", "Tipo"];
  const linhas = transacoes.map((t) => [
    t.data,
    _escaparCsv(t.descricao),
    _escaparCsv(t.conta || ""),
    _escaparCsv(t.categoria || ""),
    (t.tipo === "credit" ? t.valor : -Math.abs(t.valor)).toFixed(2),
    t.tipo === "credit" ? "credito" : "debito",
  ]);

  const csv = [cabecalho, ...linhas].map((linha) => linha.join(";")).join("\r\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  link.click();
  URL.revokeObjectURL(url);
}

function _escaparCsv(valor) {
  const texto = String(valor ?? "");
  return texto.includes(";") || texto.includes('"') || texto.includes("\n")
    ? `"${texto.replace(/"/g, '""')}"`
    : texto;
}
