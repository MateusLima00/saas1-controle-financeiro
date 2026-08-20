import { useEffect, useState } from "react";

// -----------------------------------------------------------------------
// useLocalStorageState.js
//
// Mesma API do useState, mas guarda o valor no localStorage — assim os
// dados "criados" (metas, investimentos, assinaturas, contas...) não
// somem mais ao dar F5. Enquanto não existe backend, isso é o que dá
// persistência de verdade nas telas.
//
// Cada chave é prefixada com "cf:" (controle financeiro) pra não colidir
// com outras coisas que o app venha a guardar no localStorage no futuro.
// -----------------------------------------------------------------------
export function useLocalStorageState(chave, valorInicial) {
  const chaveCompleta = `cf:${chave}`;

  const [valor, setValor] = useState(() => {
    try {
      const salvo = localStorage.getItem(chaveCompleta);
      return salvo !== null ? JSON.parse(salvo) : valorInicial;
    } catch {
      return valorInicial;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(chaveCompleta, JSON.stringify(valor));
    } catch {
      // localStorage indisponível (modo privado, quota cheia etc) - ignora,
      // o app continua funcionando só sem persistir.
    }
  }, [chaveCompleta, valor]);

  return [valor, setValor];
}
