"""Envia mensagens pelo WhatsApp Desktop para os contatos da planilha."""

import argparse
import random
import threading

import hobots
import pyautogui
from dotenv import load_dotenv

from . import config, planilha, whatsapp

# Modos na ordem de teste do Passo 9 do roteiro.
MODOS = {
    "listar": "só mostra os contatos tratados, sem abrir nada",
    "abrir": "abre o chat, sem colar nem enviar",
    "colar": "abre o chat e cola a mensagem, sem apertar Enter",
    "enviar": "abre, cola e envia de verdade",
}


def ler_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modo",
        choices=MODOS,
        default="listar",
        help="; ".join(f"{nome}: {ajuda}" for nome, ajuda in MODOS.items()),
    )
    parser.add_argument(
        "--limite",
        type=int,
        help="processa só os N primeiros contatos (ex: --limite 1 para testar)",
    )
    return parser.parse_args()


def contagem_regressiva() -> None:
    hobots.log.warn("Não mexa no mouse nem no teclado.")
    hobots.log.info("Para abortar, jogue o mouse no canto superior esquerdo da tela.")
    for restante in range(config.CONTAGEM_REGRESSIVA, 0, -1):
        hobots.log.info(f"Começando em {restante}...")
        hobots.sleep(1000)  # como time.sleep, mas para se a execução for cancelada no app


def processar_contatos(args: argparse.Namespace) -> None:
    """O trabalho do robô. Roda dentro de uma execução do Hobots."""
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = config.PAUSA_PYAUTOGUI

    df = planilha.ler_planilha()
    if args.limite:
        df = df.head(args.limite).copy()
    df["STATUS"] = ""
    contatos = df.to_dict("records")
    hobots.log.info(f"{len(contatos)} contato(s) em {config.PLANILHA_ENTRADA.name} (modo {args.modo})")
    hobots.progress.total(len(contatos))

    if args.modo != "listar":
        contagem_regressiva()

    try:
        for i, contato in enumerate(contatos):
            nome = contato["CONTATO"]
            # Linha do Excel (o cabeçalho é a linha 1): identifica o item no Hobots.
            item_id = f"linha-{i + 2}"
            try:
                numero = planilha.limpar_numero(contato["WHATSAPP"])
                mensagem = planilha.montar_mensagem(contato)
                item = {"contato": nome, "numero": numero}

                if args.modo == "listar":
                    hobots.log.info(f"[{nome}] {numero}\n{mensagem}")
                    df.at[i, "STATUS"] = "OK"
                else:
                    hobots.log.info(f"[{i + 1}/{len(contatos)}] Abrindo o chat de {nome}...")
                    whatsapp.abrir_chat(numero)
                    if args.modo in ("colar", "enviar"):
                        whatsapp.colar_mensagem(mensagem)
                    if args.modo == "enviar":
                        whatsapp.enviar()
                        df.at[i, "STATUS"] = "ENVIADO"
                        hobots.log.success(f"Mensagem enviada para {nome}.")
                        hobots.items.succeeded(item, id=item_id)
                    else:
                        df.at[i, "STATUS"] = f"TESTE ({args.modo})"
                        hobots.log.info(f"Teste ({args.modo}) concluído para {nome}.")
            except pyautogui.FailSafeException:
                hobots.log.warn("Abortado pelo FAILSAFE (mouse no canto da tela).")
                df.at[i, "STATUS"] = "ABORTADO"
                # Relança para a execução aparecer como falha no Hobots.
                raise
            except ValueError as erro:
                # Problema no dado da planilha (ex: número inválido): ocorrência de negócio.
                hobots.log.warn(f"[{nome}] {erro}")
                df.at[i, "STATUS"] = f"ERRO: {erro}"
                hobots.items.occurrence(str(erro), {"contato": nome}, id=item_id)
            except Exception as erro:
                # Falha do robô (ex: chat não abriu): falha técnica.
                hobots.log.error(f"[{nome}] ERRO: {erro}")
                df.at[i, "STATUS"] = f"ERRO: {erro}"
                hobots.items.failed(str(erro), {"contato": nome}, id=item_id)

            hobots.progress.advance()
            if args.modo == "listar":
                continue

            # Salva a cada contato, para não perder o progresso se algo travar.
            df.to_excel(config.PLANILHA_RESULTADO, index=False)

            if args.modo == "enviar" and i < len(contatos) - 1:
                espera = random.uniform(*config.INTERVALO_ENVIOS)
                hobots.log.info(f"Aguardando {espera:.0f}s até o próximo envio...")
                hobots.sleep(espera * 1000)
    finally:
        if args.modo != "listar":
            df.to_excel(config.PLANILHA_RESULTADO, index=False)
            hobots.log.info(f"Relatório salvo em {config.PLANILHA_RESULTADO.name}")


def main() -> None:
    args = ler_argumentos()
    # Lê o .env e coloca as variáveis em os.environ, onde o SDK do Hobots procura.
    load_dotenv(config.ARQUIVO_ENV)

    # O start() volta na hora e roda o handler numa thread de fundo.
    # Este Event avisa a thread principal quando o handler terminou.
    terminou = threading.Event()

    def handler(params, ctx):
        try:
            processar_contatos(args)
        finally:
            terminou.set()

    # retries=0: se der erro no meio, NÃO roda de novo (reenviaria as mensagens).
    hobots.start(config.HOBOTS_TASK, handler, retries=0)

    # wait(1) em loop, e não wait() direto, para o Ctrl+C continuar funcionando no Windows.
    while not terminou.wait(1):
        pass
    # Envia os últimos logs e para o heartbeat; sem isso o processo não termina.
    hobots.close(15_000)
