"""Imprime a posição do mouse a cada segundo. Ctrl+C para sair.

Uso: uv run python scripts/posicao_mouse.py
"""

import time

import pyautogui

try:
    while True:
        x, y = pyautogui.position()
        print(f"x={x:>5} y={y:>5}")
        time.sleep(1)
except KeyboardInterrupt:
    print("\nFim.")
