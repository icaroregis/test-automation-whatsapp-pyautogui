"""Constantes do projeto: caminhos, tempos de espera e mensagens."""

from pathlib import Path

# Raiz do projeto (a pasta que tem o pyproject.toml), para os caminhos
# funcionarem de qualquer diretório onde o comando for rodado.
RAIZ = Path(__file__).resolve().parents[2]

PLANILHA_ENTRADA = RAIZ / "data" / "contatos.xlsx"
PLANILHA_RESULTADO = RAIZ / "data" / "resultado.xlsx"

# Arquivo com as variáveis de ambiente (HOBOTS_CLIENT_SECRET, HOBOTS_INSTANCE_ID...)
ARQUIVO_ENV = RAIZ / ".env"

# Slug da task no Hobots: é o nome da execução que aparece em Solicitações.
HOBOTS_TASK = "envio-whatsapp"

# Print pequeno da caixa "Digite uma mensagem" (Passo 6, versão 2).
# Se o arquivo não existir, o script usa a espera simples (ESPERA_CHAT).
IMAGEM_CAIXA_MENSAGEM = RAIZ / "imagens" / "caixa_mensagem.png"
CONFIANCA_IMAGEM = 0.8

# Tempos em segundos
PAUSA_PYAUTOGUI = 0.5  # pausa automática depois de cada comando do PyAutoGUI
CONTAGEM_REGRESSIVA = 5  # tempo para soltar mouse e teclado antes de começar
ESPERA_CHAT = 4  # espera "no escuro" quando não há imagem de referência
TIMEOUT_CHAT = 20  # tempo máximo procurando a caixa de mensagem na tela
ESPERA_ANTES_ENVIAR = 0.5  # entre colar e apertar Enter
INTERVALO_ENVIOS = (8, 20)  # sorteado entre um contato e outro

# Telefone limpo: 55 + DDD + número
DIGITOS_MIN = 12
DIGITOS_MAX = 13

# Opção B do Passo 5: usada quando a coluna MENSAGEM do contato está vazia.
# {nome} é trocado pelo valor da coluna CONTATO.
MENSAGENS_PADRAO = [
    "Olá, {nome}! Tudo bem?",
    "Oi, {nome}! Passando para dar um alô.",
    "E aí, {nome}? Como vão as coisas?",
]
