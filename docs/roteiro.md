# Roteiro: Automação do WhatsApp Desktop com PyAutoGUI

Objetivo: ler uma planilha de contatos, abrir o WhatsApp Desktop instalado no PC e enviar uma mensagem para cada contato usando PyAutoGUI.

---

## Antes de começar: a diferença para o Puppeteer

No Puppeteer você acessa o **DOM** (a estrutura da página). Seletores como `#botao` continuam funcionando mesmo se a janela mudar de lugar.

O PyAutoGUI **não enxerga nada dentro do app**. Ele só faz três coisas:

1. **Move e clica o mouse** em coordenadas (x, y) da tela
2. **Aperta teclas**, como uma pessoa digitando
3. **Tira prints da tela** e procura uma imagem dentro deles

Por isso a automação é "cega" e mais frágil. Se a janela estiver em outro lugar, o app demorar para carregar ou aparecer um popup, o script continua clicando mesmo assim. Uma boa automação com PyAutoGUI depende de **atalhos de teclado** mais do que de cliques, e de **esperas bem feitas**.

---

## Passo 1: Entender a estrutura do projeto

O projeto foi criado com `uv init --package`:

```
test-pyautogui-whatsapp/
├── .python-version      ← diz ao uv qual Python usar (3.12)
├── pyproject.toml       ← o "package.json" do Python
├── README.md
└── src/
    └── test_pyautogui_whatsapp/
        └── __init__.py  ← transforma a pasta em um "pacote" Python
```

- **`pyproject.toml`** funciona como o `package.json`: tem nome, versão e `dependencies`. A seção `[project.scripts]` cria um comando, então `uv run test-pyautogui-whatsapp` chama a função `main()` do pacote.
- **`uv`** faz o papel de `npm`/`pnpm`. Ele cria um ambiente virtual (`.venv`), que funciona como uma `node_modules` isolada só para este projeto.
- **Layout `src/`**: o código fica dentro de `src/nome_do_pacote/`. Isso evita importar sem querer arquivos da raiz. É o padrão recomendado.

## Passo 2: Instalar as dependências

```bash
uv add pyautogui pyperclip pandas openpyxl
```

| Lib         | Para que serve                                          |
| ----------- | ------------------------------------------------------- |
| `pyautogui` | Controla mouse e teclado e tira prints                  |
| `pyperclip` | Lê e escreve na área de transferência (Ctrl+C / Ctrl+V) |
| `pandas`    | Lê a planilha como uma tabela                           |
| `openpyxl`  | O "motor" que o pandas usa para abrir `.xlsx`           |

**Por que o `pyperclip`?** O `pyautogui.write()` **não digita acentos nem `ç`** de forma confiável no Windows. Um texto como `á, é, í, ó, ú, ç, ã` sairia quebrado. A solução padrão é copiar o texto para a área de transferência e colar com `Ctrl+V`.

Depois do comando, veja o `pyproject.toml`: as libs aparecem em `dependencies` e um `uv.lock` é criado. Ele é o equivalente ao `package-lock.json`.

## Passo 3: Organizar a estrutura

```
test-pyautogui-whatsapp/
├── data/
│   └── contatos.xlsx          ← a planilha
├── docs/
│   └── roteiro.md             ← este documento
├── src/test_pyautogui_whatsapp/
│   ├── __init__.py            ← main(): orquestra tudo
│   ├── config.py              ← constantes (caminhos, tempos de espera)
│   ├── planilha.py            ← lê e trata a planilha
│   └── whatsapp.py            ← ações no app (abrir chat, colar, enviar)
└── scripts/
    └── posicao_mouse.py       ← ferramenta de apoio (Passo 4)
```

Cada arquivo tem uma responsabilidade. Se o WhatsApp mudar, você só mexe em `whatsapp.py`.

Adicione `data/` ao `.gitignore`: telefones são **dados pessoais** e não devem ir para o Git.

## Passo 4: Primeiro contato com o PyAutoGUI

Antes do WhatsApp, faça experimentos simples no terminal. Rode `uv run python` e digite:

```python
import pyautogui

pyautogui.size()          # resolução da tela, ex: Size(width=1920, height=1080)
pyautogui.position()      # onde o mouse está agora
pyautogui.moveTo(500, 500, duration=1)   # move o mouse em 1 segundo
pyautogui.hotkey("win", "r")             # abre o "Executar" do Windows
```

Dois conceitos de **segurança** que você precisa conhecer desde o início:

```python
pyautogui.FAILSAFE = True   # (padrão) jogar o mouse no CANTO SUPERIOR ESQUERDO aborta o script
pyautogui.PAUSE = 0.5       # pausa automática de 0.5s depois de CADA comando
```

O **FAILSAFE** é o seu freio de emergência. Se o script sair do controle e começar a clicar em tudo, leve o mouse rapidamente para o canto e ele para. Nunca desligue isso.

**Ferramenta de apoio (`scripts/posicao_mouse.py`):** um loop que imprime `pyautogui.position()` a cada segundo. Serve para descobrir as coordenadas de botões. Este roteiro usa pouco dela, porque prefere atalhos.

## Passo 5: Ler a planilha (`planilha.py`)

A planilha tem as colunas `CONTATO`, `MENSAGEM` e `WHATSAPP`.

```python
df = pd.read_excel("data/contatos.xlsx", dtype={"WHATSAPP": str})
```

Há três cuidados:

1. **`dtype=str` no telefone.** Os triângulos verdes no Excel mostram que os números estão salvos como texto. Se o pandas ler como número, pode virar `5.585933e+12` ou perder zeros. Ler como texto garante que `"5585933008992"` fique intacto.
2. **Limpar o número.** Remova espaços, `+`, `-` e parênteses para sobrar só dígitos. Aproveite para validar que tem entre 12 e 13 dígitos (55 + DDD + número).
3. **O `\n` dentro do texto.** Se na célula estiver escrito literalmente `\n` (barra + n), isso não é uma quebra de linha de verdade. Converta com `texto.replace("\\n", "\n")`.

Depois, transforme cada linha em um dicionário (`df.to_dict("records")`) para iterar com um `for` simples.

Para as **mensagens aleatórias**, há duas opções:

- **A)** Usar a coluna `MENSAGEM` de cada contato
- **B)** Ter uma lista de mensagens e sortear uma com `random.choice(lista)`, podendo usar `{nome}` no texto e preencher com `.format(nome=contato["CONTATO"])`

## Passo 6: Abrir o chat certo no WhatsApp (`whatsapp.py`)

Esta é a parte que mais faz diferença na robustez. Um jeito ingênuo seria clicar na lupa, digitar o nome, esperar e clicar no resultado. Isso quebra fácil: homônimos, contato não salvo, resultado que demora.

O jeito melhor é usar o **protocolo `whatsapp://`**, que o Windows registra quando você instala o app:

```python
import os
os.startfile(f"whatsapp://send?phone={numero}")
```

Isso abre o WhatsApp Desktop **direto na conversa daquele número**, mesmo que ele não esteja salvo nos seus contatos. É como um `page.goto()` do Puppeteer. Você não precisa de nenhuma coordenada.

**Esperar o chat carregar** é a parte mais importante:

- **Versão 1 (simples):** `time.sleep(4)`. Funciona, mas é uma espera "no escuro".
- **Versão 2 (melhor):** usar `pyautogui.locateOnScreen("imagens/caixa_mensagem.png")` em loop até encontrar a caixa "Digite uma mensagem". É o equivalente ao `waitForSelector`. Para isso, você tira um print pequeno da caixa e salva como `.png`. Isso exige `uv add opencv-python` para usar o parâmetro `confidence=0.8`, que aceita pequenas diferenças.

⚠️ Com escala do Windows em 125% ou 150%, o print de referência precisa ser tirado **na mesma escala** em que o script vai rodar.

## Passo 7: Escrever e enviar a mensagem

```python
pyperclip.copy(mensagem)          # coloca o texto na área de transferência
pyautogui.hotkey("ctrl", "v")     # cola na caixa de mensagem (já focada)
time.sleep(0.5)
pyautogui.press("enter")          # envia
```

- **Por que colar funciona com quebras de linha:** no WhatsApp, apertar `Enter` envia a mensagem. Se você digitasse um texto com várias linhas tecla por tecla, cada quebra enviaria um pedaço separado. Ao **colar**, as quebras de linha entram como texto e só o `Enter` final envia. (Se um dia precisar digitar uma quebra, o atalho é `Shift+Enter`.)
- O `hotkey` aperta as teclas juntas, na ordem, e solta ao contrário, igual a uma pessoa fazendo o atalho.

## Passo 8: O loop principal e as proteções (`__init__.py` → `main()`)

```
para cada contato:
    tenta:
        abrir chat → esperar → colar → enviar
        marcar "ENVIADO"
    se der erro:
        marcar "ERRO: motivo" e seguir para o próximo
    esperar um tempo aleatório (ex: random.uniform(8, 20) segundos)
```

- **`try/except` por contato:** um número inválido não derruba a execução inteira.
- **Intervalo aleatório entre envios:** envios em ritmo de máquina (1 por segundo) são o que o WhatsApp usa para detectar automação.
- **Contagem regressiva no início:** um `time.sleep(5)` com aviso "Não mexa no mouse", para você soltar o teclado antes do robô assumir.
- **Relatório no final:** salve uma cópia da planilha com a coluna `STATUS` preenchida (`df.to_excel("data/resultado.xlsx")`).

## Passo 9: Rodar e testar aos poucos

```bash
uv run test-pyautogui-whatsapp
```

Siga esta ordem de testes. Não pule direto para o final:

1. Só ler a planilha e **imprimir** os contatos tratados, sem abrir nada
2. Abrir o chat de **um** contato (de preferência o seu próprio número) sem enviar
3. Colar a mensagem **sem** apertar Enter e conferir acentos e quebras de linha
4. Enviar para **um** contato
5. Rodar a planilha inteira

---

## ⚠️ Avisos importantes

- **Risco de banimento:** automatizar o WhatsApp comum viola os Termos de Uso. Muitos envios para números que não têm você salvo podem **bloquear seu número**. Para testes com poucos contatos conhecidos o risco é baixo. Para uso em produção ou em escala, o caminho oficial é a **WhatsApp Business API**.
- **Consentimento:** envie apenas para quem sabe que vai receber a mensagem (LGPD).
- **O PC fica "sequestrado":** enquanto o script roda, você não pode usar mouse nem teclado. Qualquer popup ou notificação pode desviar o foco.
