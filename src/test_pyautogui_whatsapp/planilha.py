"""Leitura e tratamento da planilha de contatos."""

import random
import re
from pathlib import Path

import pandas as pd

from . import config

COLUNAS = ["CONTATO", "MENSAGEM", "WHATSAPP"]


def ler_planilha(caminho: Path = config.PLANILHA_ENTRADA) -> pd.DataFrame:
    """Lê a planilha como texto, para o telefone não virar número (5.58e+12)."""
    df = pd.read_excel(caminho, dtype=str).fillna("")

    faltando = [coluna for coluna in COLUNAS if coluna not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes na planilha: {', '.join(faltando)}")

    return df


def limpar_numero(numero: str) -> str:
    """Deixa só os dígitos e valida o tamanho (55 + DDD + número)."""
    digitos = re.sub(r"\D", "", numero)
    if not config.DIGITOS_MIN <= len(digitos) <= config.DIGITOS_MAX:
        raise ValueError(
            f"número inválido '{numero}': precisa ter entre "
            f"{config.DIGITOS_MIN} e {config.DIGITOS_MAX} dígitos"
        )
    return digitos


def montar_mensagem(contato: dict) -> str:
    """Usa a coluna MENSAGEM (opção A) ou sorteia uma padrão (opção B)."""
    texto = contato["MENSAGEM"].strip() or random.choice(config.MENSAGENS_PADRAO)
    # "\n" escrito literalmente na célula vira quebra de linha de verdade.
    # replace em vez de format, para chaves soltas no texto não darem erro.
    return texto.replace("\\n", "\n").replace("{nome}", contato["CONTATO"].strip())
