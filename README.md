# 🐧 LUNIX 1.0 (PoC)

**Lunix** é uma prova de conceito (PoC) de um terminal interativo escrito em Python utilizando a biblioteca `pygame`. Ele emula um ambiente de sistema operacional minimalista, permitindo a execução de comandos, manipulação de arquivos, edição de texto e mini-jogos. 💻

## 🐧 O que é isso?
Este projeto foi desenvolvido como um exercício de arquitetura de sistemas e manipulação de interfaces CLI. Ele simula um ciclo de inicialização (*boot sequence*) completo e oferece um shell funcional com persistência de arquivos. ⚡

## 🛠 Funcionalidades
* **🚀 Bootstrap Realista:** Inicialização de kernel e montagem de diretórios (`/sys`, `/usr`, etc.).
* **🐚 Shell Interativo:** Interpretador de comandos (`ls`, `cat`, `calc`, `echo`, `ping`...).
* **📝 Editor `nano`:** Edição funcional com suporte a salvamento na pasta `lunix_system/`.
* **🎮 Jogos Nativos:** Snake 🐍 e Tic-Tac-Toe ❌⭕ rodando no terminal.
* **🔊 Integração:** Disparos de popups nativos do SO e geração de bipes (`beep`) via código.
* **📜 Log Persistente:** Histórico completo de tudo que aconteceu na sessão com `cat -logcli`.

## 🚀 Como executar
1. Certifique-se de ter o Python instalado.
2. Instale a dependência:
   ```bash
   pip install pygame
