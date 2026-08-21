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
    quebra de linha no meio (principalmente em OFX) — colapsa tudo em um
    espaço só e tira acentuação de espaço non-breaking (comum em extratos
    do Itaú/Bradesco copiados de PDF pra CSV)."""
    return re.sub(r"\s+", " ", bruta.replace("\xa0", " ")).strip()


def _parse_valor_br_ou_us(bruto: str) -> float:
    bruto = bruto.strip().replace("R$", "").strip()
    if "," in bruto and "." in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif "," in bruto:
        bruto = bruto.replace(",", ".")
    return float(bruto)


def parse_csv(conteudo: bytes, conta_id: int) -> list[ParsedTransaction]:
    texto = conteudo.decode("utf-8-sig", errors="replace")
    amostra = texto[:2048]
    delimiter = ";" if amostra.count(";") > amostra.count(",") else ","
    reader = csv.DictReader(io.StringIO(texto), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV sem cabeçalho reconhecível.")

    colunas = {c.strip().lower(): c for c in reader.fieldnames}
    col_data = next((colunas[c] for c in ("data", "date") if c in colunas), None)
    col_descricao = next(
        (colunas[c] for c in ("descricao", "descrição", "description", "historico", "histórico") if c in colunas),
        None,
    )
    col_valor = next((colunas[c] for c in ("valor", "amount", "value") if c in colunas), None)

    if not (col_data and col_descricao and col_valor):
        raise ValueError(
            "CSV precisa ter colunas de data, descrição e valor (ex: data,descricao,valor)."
        )

    resultado = []
    for linha in reader:
        data_bruta = (linha.get(col_data) or "").strip()
        descricao = _limpar_descricao(linha.get(col_descricao) or "")
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
