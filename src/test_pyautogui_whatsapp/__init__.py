"""Envia mensagens pelo WhatsApp Desktop para os contatos da planilha."""

import argparse
import random
import time

import pyautogui

from . import config, planilha, whatsapp

# Modos na ordem de teste do Passo 9 do roteiro.
MODOS = {
    "listar": "só imprime os contatos tratados, sem abrir nada",
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
    print("Não mexa no mouse nem no teclado.")
    print("Para abortar, jogue o mouse no canto superior esquerdo da tela.")
    for restante in range(config.CONTAGEM_REGRESSIVA, 0, -1):
        print(f"Começando em {restante}...")
        time.sleep(1)


def main() -> None:
    args = ler_argumentos()

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = config.PAUSA_PYAUTOGUI

    df = planilha.ler_planilha()
    if args.limite:
        df = df.head(args.limite).copy()
    df["STATUS"] = ""
    contatos = df.to_dict("records")
    print(f"{len(contatos)} contato(s) em {config.PLANILHA_ENTRADA}\n")

    if args.modo != "listar":
        contagem_regressiva()

    for i, contato in enumerate(contatos):
        nome = contato["CONTATO"]
        try:
            numero = planilha.limpar_numero(contato["WHATSAPP"])
            mensagem = planilha.montar_mensagem(contato)

            if args.modo == "listar":
                print(f"[{nome}] {numero}\n{mensagem}\n")
                df.at[i, "STATUS"] = "OK"
                continue

            print(f"[{i + 1}/{len(contatos)}] {nome} ({numero})")
            whatsapp.abrir_chat(numero)
            if args.modo in ("colar", "enviar"):
                whatsapp.colar_mensagem(mensagem)
            if args.modo == "enviar":
                whatsapp.enviar()
                df.at[i, "STATUS"] = "ENVIADO"
            else:
                df.at[i, "STATUS"] = f"TESTE ({args.modo})"
        except pyautogui.FailSafeException:
            print("\nAbortado pelo FAILSAFE (mouse no canto da tela).")
            df.at[i, "STATUS"] = "ABORTADO"
            break
        except Exception as erro:
            print(f"[{nome}] ERRO: {erro}")
            df.at[i, "STATUS"] = f"ERRO: {erro}"

        if args.modo == "listar":
            continue

        # Salva a cada contato, para não perder o progresso se algo travar.
        df.to_excel(config.PLANILHA_RESULTADO, index=False)

        if args.modo == "enviar" and i < len(contatos) - 1:
            espera = random.uniform(*config.INTERVALO_ENVIOS)
            print(f"  aguardando {espera:.0f}s...")
            time.sleep(espera)

    if args.modo == "listar":
        return

    df.to_excel(config.PLANILHA_RESULTADO, index=False)
    print(f"\nRelatório salvo em {config.PLANILHA_RESULTADO}")
