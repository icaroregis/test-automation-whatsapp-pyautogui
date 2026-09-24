"""Ações no WhatsApp Desktop: abrir o chat, colar e enviar."""

import os
import time

import pyautogui
import pyperclip

from . import config


def abrir_chat(numero: str) -> None:
    """Abre a conversa direto pelo protocolo whatsapp:// (como um page.goto)."""
    os.startfile(f"whatsapp://send?phone={numero}")
    esperar_chat()


def esperar_chat() -> None:
    """Espera a caixa de mensagem aparecer (como um waitForSelector).

    Sem a imagem de referência, faz só uma espera fixa.
    """
    if not config.IMAGEM_CAIXA_MENSAGEM.exists():
        time.sleep(config.ESPERA_CHAT)
        return

    limite = time.monotonic() + config.TIMEOUT_CHAT
    while time.monotonic() < limite:
        try:
            caixa = pyautogui.locateCenterOnScreen(
                str(config.IMAGEM_CAIXA_MENSAGEM),
                confidence=config.CONFIANCA_IMAGEM,
            )
        except pyautogui.ImageNotFoundException:
            caixa = None

        if caixa:
            # Clica na caixa para garantir o foco antes de colar.
            pyautogui.click(caixa)
            return
        time.sleep(0.5)

    raise TimeoutError(
        f"caixa de mensagem não apareceu em {config.TIMEOUT_CHAT}s "
        "(número sem WhatsApp ou app lento?)"
    )


def colar_mensagem(mensagem: str) -> None:
    """Cola pela área de transferência, que preserva acentos e quebras de linha."""
    pyperclip.copy(mensagem)
    pyautogui.hotkey("ctrl", "v")


def enviar() -> None:
    time.sleep(config.ESPERA_ANTES_ENVIAR)
    pyautogui.press("enter")
