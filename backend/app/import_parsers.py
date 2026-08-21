import csv
import hashlib
import io
import re
from dataclasses import dataclass


@dataclass
class ParsedTransaction:
    data: str  # ISO "YYYY-MM-DD"
    descricao: str
    valor: float
    tipo: str  # debit | credit
    external_id: str


def _make_external_id(conta_id: int, data: str, descricao: str, valor: float) -> str:
    raw = f"{conta_id}|{data}|{descricao}|{valor:.2f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _limpar_descricao(bruta: str) -> str:
    """Bancos costumam exportar descrição com espaços duplicados, tabs ou
    quebra de linha no meio (principalmente em OFX/PDF) — colapsa tudo em
    um espaço só e tira espaço non-breaking (comum em extratos copiados de
    PDF pra CSV)."""
    return re.sub(r"\s+", " ", bruta.replace("\xa0", " ")).strip()


def _parse_valor_br_ou_us(bruto: str) -> float:
    bruto = bruto.strip().replace("R$", "").strip()
    # Alguns bancos (ex: PicPay/Mercado Pago) usam o sinal de menos
    # tipográfico "−" (U+2212) em vez do hífen ASCII "-" — float() só
    # reconhece o ASCII, então sem isso todo débito vira erro de parse.
    bruto = bruto.replace("−", "-").replace(" ", "")
    if "," in bruto and "." in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif "," in bruto:
        bruto = bruto.replace(",", ".")
    return float(bruto)


# Nomes de coluna reconhecidos por categoria — cobre os formatos de
# exportação vistos na prática (Banco Inter, PicPay/Mercado Pago, genérico
# data/descricao/valor). Colunas de "descrição" combinam: quando o banco
# separa histórico/tipo de descrição/origem em colunas diferentes (Inter:
# "Histórico" + "Descrição"; PicPay: "Tipo" + "Origem / Destino" + "Forma
# de pagamento"), todas que tiverem conteúdo na linha são concatenadas.
_COLUNAS_DATA = ("data", "date", "data lançamento", "data lancamento")
_COLUNAS_DESCRICAO = (
    "descricao",
    "descrição",
    "description",
    "historico",
    "histórico",
    "tipo",
    "origem / destino",
    "origem/destino",
    "forma de pagamento",
)
_COLUNAS_VALOR = ("valor", "amount", "value")


def _detectar_cabecalho(linhas: list[str], delimiter: str) -> int | None:
    """Extratos de banco costumam ter algumas linhas de metadados (nome da
    conta, período, saldo) antes da linha de cabeçalho de verdade — procura
    nas primeiras linhas por uma que tenha pelo menos uma coluna de data E
    uma de valor reconhecidas."""
    for i, linha in enumerate(linhas[:20]):
        celulas = [c.strip().strip('"').lower() for c in linha.split(delimiter)]
        tem_data = any(c in _COLUNAS_DATA for c in celulas)
        tem_valor = any(c in _COLUNAS_VALOR for c in celulas)
        if tem_data and tem_valor:
            return i
    return None


def parse_csv(conteudo: bytes, conta_id: int) -> list[ParsedTransaction]:
    texto = conteudo.decode("utf-8-sig", errors="replace")
    amostra = texto[:2048]
    delimiter = ";" if amostra.count(";") > amostra.count(",") else ","

    linhas = texto.splitlines()
    idx_cabecalho = _detectar_cabecalho(linhas, delimiter)
    if idx_cabecalho is None:
        raise ValueError(
            "CSV precisa ter colunas de data, descrição e valor (ex: data,descricao,valor)."
        )
    texto_a_partir_do_cabecalho = "\n".join(linhas[idx_cabecalho:])

    reader = csv.DictReader(io.StringIO(texto_a_partir_do_cabecalho), delimiter=delimiter)
    colunas = {c.strip().lower(): c for c in reader.fieldnames or []}

    col_data = next((colunas[c] for c in _COLUNAS_DATA if c in colunas), None)
    cols_descricao = [colunas[c] for c in _COLUNAS_DESCRICAO if c in colunas]
    col_valor = next((colunas[c] for c in _COLUNAS_VALOR if c in colunas), None)

    if not (col_data and col_valor):
        raise ValueError(
            "CSV precisa ter colunas de data, descrição e valor (ex: data,descricao,valor)."
        )

    resultado = []
    for linha in reader:
        data_bruta = (linha.get(col_data) or "").strip()
        partes_descricao = [(linha.get(c) or "").strip() for c in cols_descricao]
        descricao = _limpar_descricao(" - ".join(p for p in partes_descricao if p))
        valor_bruto = (linha.get(col_valor) or "").strip()
        if not data_bruta or not valor_bruto:
            continue

        try:
            valor = _parse_valor_br_ou_us(valor_bruto)
            data_iso = _normalizar_data(data_bruta)
        except ValueError:
            # Linha individual mal formatada (ex: cabeçalho de totais no
            # rodapé do CSV do banco) não deve derrubar o import inteiro —
            # só essa linha é ignorada.
            continue
        tipo = "credit" if valor >= 0 else "debit"
        resultado.append(
            ParsedTransaction(
                data=data_iso,
                descricao=descricao or "Sem descrição",
                valor=valor,
                tipo=tipo,
                external_id=_make_external_id(conta_id, data_iso, descricao, valor),
            )
        )
    return resultado


def _normalizar_data(bruta: str) -> str:
    if re.match(r"^\d{4}-\d{2}-\d{2}$", bruta):
        return bruta
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", bruta)
    if m:
        dia, mes, ano = m.groups()
        return f"{ano}-{mes}-{dia}"
    raise ValueError(f"Data em formato não reconhecido: {bruta!r} (use YYYY-MM-DD ou DD/MM/AAAA)")


_OFX_TRN_RE = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL | re.IGNORECASE)
_OFX_FIELD_RE = re.compile(r"<(\w+)>([^<\r\n]*)")


def parse_ofx(conteudo: bytes, conta_id: int) -> list[ParsedTransaction]:
    texto = conteudo.decode("utf-8", errors="replace")
    resultado = []
    for bloco in _OFX_TRN_RE.findall(texto):
        campos = {tag.upper(): valor.strip() for tag, valor in _OFX_FIELD_RE.findall(bloco)}
        dtposted = campos.get("DTPOSTED", "")
        trnamt = campos.get("TRNAMT", "")
        descricao = _limpar_descricao(campos.get("MEMO") or campos.get("NAME") or "Sem descrição")
        fitid = campos.get("FITID")

        if not dtposted or not trnamt:
            continue

        data_iso = f"{dtposted[0:4]}-{dtposted[4:6]}-{dtposted[6:8]}"
        valor = float(trnamt)
        tipo = "credit" if valor >= 0 else "debit"
        external_id = fitid or _make_external_id(conta_id, data_iso, descricao, valor)
        resultado.append(
            ParsedTransaction(
                data=data_iso,
                descricao=descricao,
                valor=valor,
                tipo=tipo,
                external_id=f"{conta_id}:{external_id}",
            )
        )
    return resultado


_MESES = {
    "janeiro": "01", "fevereiro": "02", "marco": "03", "março": "03",
    "abril": "04", "maio": "05", "junho": "06", "julho": "07",
    "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11",
    "dezembro": "12",
}
# "1 de dezembro de 2025" / "20 de agosto 2026" (o "de" antes do ano é
# opcional — o extrato do PicPay omite ele em alguns cabeçalhos de dia).
_PDF_DATA_CABECALHO_RE = re.compile(
    r"\b(\d{1,2})\s+de\s+([a-zçA-ZÇ]+)\s+(?:de\s+)?(\d{4})\b", re.IGNORECASE
)
_PDF_DATA_BR_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
# Valor monetário: sinal opcional (ASCII "-", tipográfico "−", ou "+"),
# "R$" e o número em formato BR (milhar com ponto, decimal com vírgula).
_PDF_VALOR_RE = re.compile(r"([+\-−]?)\s*R\$\s*([\d.,]+)\s*$")
_PDF_LINHA_SALDO_RE = re.compile(
    r"saldo\s+(do\s+dia|ao\s+final|final|total|dispon[íi]vel|bloqueado)", re.IGNORECASE
)

# Formato Caixa Econômica ("Extrato por período"): cada linha já traz
# data+hora+nº doc+histórico+valor+saldo, sem cabeçalho de dia separado, e
# usa sufixo "C"/"D" (crédito/débito) em vez de sinal ou "R$". Ex:
# "21/08/2026 - 00:19:20  210019  CRED PIX CHAVE  Mateus Costa de Li  ***.535.613***  115,06 C  440,06 C"
_CAIXA_LINHA_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s*-\s*\d{2}:\d{2}:\d{2}\s+\d+\s+(.*?)\s+([\d.,]+)\s*([CD])\s+[\d.,]+\s*[CD]\s*$"
)


def parse_pdf(conteudo: bytes, conta_id: int) -> list[ParsedTransaction]:
    """PDF de extrato bancário — bem menos confiável que CSV/OFX (texto
    extraído de tabela, nomes que quebram linha viram descrição truncada),
    por isso só use se o banco não oferecer CSV/OFX. Dois formatos
    reconhecidos:
    - Caixa ("Extrato por período"): cada linha já tem data+hora+histórico+
      valor+sufixo C/D — `_CAIXA_LINHA_RE` casa direto, sem precisar de
      cabeçalho de dia.
    - Inter/PicPay/genérico: cada página vira uma lista de linhas de
      texto; linhas de cabeçalho de dia ("D de mês de AAAA ... Saldo do
      dia: ...") atualizam a data corrente mas não geram transação;
      qualquer outra linha terminando em "R$ valor" vira uma transação,
      com a data corrente e o resto da linha como descrição. Linhas de
      saldo consolidado (total/disponível/bloqueado) são ignoradas."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError(
            "Suporte a PDF não está instalado no servidor (pdfplumber ausente)."
        ) from exc

    resultado = []
    data_atual: str | None = None

    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        # Fallback pro início do período: às vezes o cabeçalho do primeiro
        # dia sai ilegível na extração de texto (ícone/elemento gráfico
        # sobreposto no PDF), e a(s) transação(ões) antes do primeiro
        # cabeçalho válido ficariam sem data. Usa o início do "Período: X a
        # Y" (comum em extratos bancários) como data inicial provisória —
        # cabeçalhos de dia de verdade, encontrados depois, sobrescrevem.
        primeira_pagina = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
        m_periodo = re.search(r"per[íi]odo[:\s]+.*?(\d{2})/(\d{2})/(\d{4})", primeira_pagina, re.IGNORECASE)
        if m_periodo:
            dia, mes, ano = m_periodo.groups()
            data_atual = f"{ano}-{mes}-{dia}"

        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            for linha in texto.splitlines():
                linha = linha.strip()
                if not linha:
                    continue

                m_caixa = _CAIXA_LINHA_RE.match(linha)
                if m_caixa:
                    data_str, descricao_bruta, valor_bruto, sinal_cd = m_caixa.groups()
                    dia, mes, ano = data_str.split("/")
                    data_iso = f"{ano}-{mes}-{dia}"
                    try:
                        valor = _parse_valor_br_ou_us(valor_bruto)
                    except ValueError:
                        continue
                    if valor == 0:
                        # Linha "SALDO DIA" (marcador de dia, não transação
                        # de verdade) sempre vem com valor 0,00.
                        continue
                    valor = -abs(valor) if sinal_cd == "D" else abs(valor)
                    descricao = _limpar_descricao(descricao_bruta)
                    tipo = "credit" if valor >= 0 else "debit"
                    resultado.append(
                        ParsedTransaction(
                            data=data_iso,
                            descricao=descricao or "Sem descrição",
                            valor=valor,
                            tipo=tipo,
                            external_id=_make_external_id(conta_id, data_iso, descricao, valor),
                        )
                    )
                    continue

                m_data = _PDF_DATA_CABECALHO_RE.search(linha)
                if m_data:
                    dia, mes_nome, ano = m_data.groups()
                    mes = _MESES.get(mes_nome.strip().lower())
                    if mes:
                        data_atual = f"{ano}-{mes}-{int(dia):02d}"

                if _PDF_LINHA_SALDO_RE.search(linha) or (m_data and m_data.start() == 0):
                    # Linha de resumo de saldo (do dia, total, disponível,
                    # bloqueado) ou linha que começa com a data por extenso
                    # ("D de mês de AAAA ...") — nunca é uma transação de
                    # verdade (transações sempre começam com "Pix enviado:",
                    # horário, etc.), só serve pra achar a data acima.
                    continue

                m_valor = _PDF_VALOR_RE.search(linha)
                if not m_valor or not data_atual:
                    continue

                sinal, valor_bruto = m_valor.groups()
                try:
                    valor = _parse_valor_br_ou_us(valor_bruto)
                except ValueError:
                    continue
                if valor == 0:
                    # Nenhuma transação real é R$0,00 — só acontece quando
                    # uma linha de resumo de saldo (ex: "Saldo bloqueado:
                    # R$ 0,00") escapa do filtro de saldo por estar quebrada
                    # em linhas diferentes na extração do PDF.
                    continue
                if sinal in ("-", "−"):
                    valor = -abs(valor)
                elif sinal == "+":
                    valor = abs(valor)
                # Sem sinal (alguns bancos omitem o "+" em créditos): mantém
                # positivo, mesmo comportamento do Banco Inter.

                descricao = _limpar_descricao(linha[: m_valor.start()])
                # Remove prefixo "HH:MM " de formatos tipo PicPay, que não
                # agrega nada à descrição em si (a data já vem do cabeçalho
                # do dia).
                descricao = re.sub(r"^\d{2}:\d{2}\s+", "", descricao)
                if not descricao:
                    continue

                tipo = "credit" if valor >= 0 else "debit"
                resultado.append(
                    ParsedTransaction(
                        data=data_atual,
                        descricao=descricao,
                        valor=valor,
                        tipo=tipo,
                        external_id=_make_external_id(conta_id, data_atual, descricao, valor),
                    )
                )
    return resultado
