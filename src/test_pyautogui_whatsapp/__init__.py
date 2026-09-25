"""Envia mensagens pelo WhatsApp Desktop para os contatos da planilha."""

import argparse
import random
import signal
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


def processar_contatos(modo: str, limite: int | None) -> None:
    """O trabalho do robô. Roda dentro de uma execução do Hobots."""
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = config.PAUSA_PYAUTOGUI

    df = planilha.ler_planilha()
    if limite:
        df = df.head(limite).copy()
    df["STATUS"] = ""
    contatos = df.to_dict("records")
    hobots.log.info(f"{len(contatos)} contato(s) em {config.PLANILHA_ENTRADA.name} (modo {modo})")
    hobots.progress.total(len(contatos))

    if modo != "listar":
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

                if modo == "listar":
                    hobots.log.info(f"[{nome}] {numero}\n{mensagem}")
                    df.at[i, "STATUS"] = "OK"
                else:
                    hobots.log.info(f"[{i + 1}/{len(contatos)}] Abrindo o chat de {nome}...")
                    whatsapp.abrir_chat(numero)
                    if modo in ("colar", "enviar"):
                        whatsapp.colar_mensagem(mensagem)
                    if modo == "enviar":
                        whatsapp.enviar()
                        df.at[i, "STATUS"] = "ENVIADO"
                        hobots.log.success(f"Mensagem enviada para {nome}.")
                        hobots.items.succeeded(item, id=item_id)
                    else:
                        df.at[i, "STATUS"] = f"TESTE ({modo})"
                        hobots.log.info(f"Teste ({modo}) concluído para {nome}.")
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
            if modo == "listar":
                continue

            # Salva a cada contato, para não perder o progresso se algo travar.
            df.to_excel(config.PLANILHA_RESULTADO, index=False)

            if modo == "enviar" and i < len(contatos) - 1:
                espera = random.uniform(*config.INTERVALO_ENVIOS)
                hobots.log.info(f"Aguardando {espera:.0f}s até o próximo envio...")
                hobots.sleep(espera * 1000)
    finally:
        if modo != "listar":
            df.to_excel(config.PLANILHA_RESULTADO, index=False)
            hobots.log.info(f"Relatório salvo em {config.PLANILHA_RESULTADO.name}")


def ler_parametros(params: dict, args: argparse.Namespace) -> tuple[str, int | None]:
    """Campos do formulário do Hobots têm prioridade; sem eles, vale o que veio no terminal."""
    modo = params.get("modo") or args.modo
    if modo not in MODOS:
        raise ValueError(f"modo inválido '{modo}': use {', '.join(MODOS)}")
    limite = params.get("limite") or args.limite
    return modo, int(limite) if limite else None


def main() -> None:
    args = ler_argumentos()
    # Lê o .env e coloca as variáveis em os.environ, onde o SDK do Hobots procura.
    load_dotenv(config.ARQUIVO_ENV)

    def handler(params, ctx):
        # Chamado a cada disparo no Hobots. params = campos do formulário (dict).
        modo, limite = ler_parametros(params, args)
        processar_contatos(modo, limite)

    # register() = modo sob demanda: o robô fica online esperando solicitações.
    # Volta na hora; a escuta roda em threads de fundo.
    # retries=0: se der erro no meio, NÃO roda de novo (reenviaria as mensagens).
    # concurrency fica no padrão (1): o PyAutoGUI só controla um mouse por vez.
    hobots.register(config.HOBOTS_TASK, handler, retries=0)
    hobots.log.info(f"Robô online, aguardando disparos da task '{config.HOBOTS_TASK}'. Ctrl+C para sair.")

    # Ctrl+C só avisa este Event; quem encerra é a thread principal, logo abaixo.
    parar = threading.Event()
    signal.signal(signal.SIGINT, lambda signum, frame: parar.set())
    signal.signal(signal.SIGTERM, lambda signum, frame: parar.set())

    # wait(1) em loop, e não wait() direto, para o Ctrl+C continuar funcionando no Windows.
    while not parar.wait(1):
        pass

    hobots.log.info("Encerrando: aguardando a execução em andamento terminar...")
    # Espera a execução em voo, envia os últimos logs e para o heartbeat.
    hobots.close(60_000)
