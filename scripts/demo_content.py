"""Conteúdo de demonstração do WikiDev.

Cada página é um dicionário com título, resumo, pasta, tags e blocos.
Blocos são tuplas (tipo, conteúdo) para texto ou (tipo, conteúdo, linguagem)
para código. Os links [[Título]] apontam para outras páginas desta lista.
"""

from __future__ import annotations

TEXT = "text"
CODE = "code"

USERS = [
    {
        "username": "admin",
        "email": "admin@wikidev.local",
        "display_name": "Administrador",
        "bio": "Mantém as páginas de referência do WikiDev.",
        "password": "admin123",
    },
    {
        "username": "ana",
        "email": "ana@wikidev.local",
        "display_name": "Ana Souza",
        "bio": "Estudante de computação. Gosta de algoritmos e de explicar com exemplos.",
        "password": "ana12345",
    },
]

FOLDERS = [
    # (dono, nome, descrição)
    ("admin", "Primeiros passos", "Como usar o WikiDev."),
    ("admin", "Python", "Fundamentos da linguagem, com exemplos que rodam no navegador."),
    ("admin", "Git e GitHub", "Fluxo de trabalho e como sair de enrascadas."),
    ("admin", "Banco de dados", "Consultas, modelagem e desempenho em SQL."),
    ("admin", "Web e APIs", "HTTP, APIs REST e FastAPI."),
    ("admin", "Linux e terminal", "Comandos para o dia a dia no terminal."),
    ("ana", "Algoritmos", "Algoritmos clássicos explicados passo a passo."),
]

PAGES = [
    {
        "author": "admin",
        "title": "Bem-vindo ao WikiDev",
        "folder": "Primeiros passos",
        "summary": "Um tour rápido: páginas, blocos, links entre páginas e atalhos.",
        "tags": ["guia"],
        "blocks": [
            (TEXT,
             "O WikiDev é uma wiki para organizar o que você aprende de programação. "
             "Cada **página** é feita de **blocos** de texto e de código.\n\n"
             "## O que dá para fazer\n\n"
             "- Escrever em **Markdown**: títulos, listas, tabelas e `código`.\n"
             "- Linkar outras páginas com colchetes duplos, como [[Git: comandos do dia a dia]].\n"
             "- Rodar blocos de Python direto no navegador com o botão **Executar**.\n"
             "- Ver o **histórico** de cada página e restaurar versões antigas.\n"
             "- Organizar em pastas e tags, e compartilhar com amigos.\n\n"
             "## Atalhos\n\n"
             "| Atalho | O que faz |\n|---|---|\n"
             "| `Ctrl` + `K` | Busca rápida por páginas, pastas, tags e pessoas |\n"
             "| `/` | Vai para a barra de busca |\n"
             "| `Esc` | Fecha a busca ou o menu lateral |"),
            (TEXT,
             "## Por onde começar\n\n"
             "1. Leia [[Python: variáveis e tipos básicos]] e clique em **Executar** no código.\n"
             "2. Crie uma página sobre algo que você aprendeu esta semana.\n"
             "3. Deixe um comentário em um bloco de alguém."),
        ],
    },
    {
        "author": "admin",
        "title": "Python: variáveis e tipos básicos",
        "folder": "Python",
        "summary": "Tipagem dinâmica, os tipos mais usados e como inspecioná-los.",
        "tags": ["python", "fundamentos"],
        "blocks": [
            (TEXT,
             "Em Python a variável é só um nome que aponta para um valor. O **tipo pertence ao valor**, "
             "não à variável, e por isso a mesma variável pode apontar para valores de tipos diferentes.\n\n"
             "| Tipo | Exemplo | Mutável? |\n|---|---|---|\n"
             "| `int` | `42` | não |\n| `float` | `3.14` | não |\n| `str` | `\"olá\"` | não |\n"
             "| `bool` | `True` | não |\n| `list` | `[1, 2, 3]` | sim |\n| `tuple` | `(1, 2)` | não |\n"
             "| `dict` | `{\"a\": 1}` | sim |\n| `set` | `{1, 2}` | sim |"),
            (CODE,
             "valores = [42, 3.14, \"olá\", True, [1, 2], (1, 2), {\"a\": 1}, {1, 2}, None]\n\n"
             "for valor in valores:\n"
             "    print(f\"{valor!r:>12} -> {type(valor).__name__}\")",
             "python"),
            (TEXT,
             "> **Cuidado com mutáveis:** duas variáveis podem apontar para a mesma lista. "
             "Alterar uma altera a outra. Use `lista.copy()` quando precisar de uma cópia."),
            (CODE,
             "a = [1, 2, 3]\nb = a          # mesmo objeto\nc = a.copy()   # cópia\n\n"
             "a.append(4)\nprint(\"a:\", a)\nprint(\"b:\", b)\nprint(\"c:\", c)\nprint(\"a is b?\", a is b)",
             "python"),
        ],
    },
    {
        "author": "admin",
        "title": "Python: list comprehensions",
        "folder": "Python",
        "summary": "Criar listas, dicionários e conjuntos em uma linha, sem perder a legibilidade.",
        "tags": ["python", "fundamentos"],
        "blocks": [
            (TEXT,
             "Uma *list comprehension* troca o padrão \"cria lista vazia, faz um `for`, dá `append`\" "
             "por uma expressão só:\n\n`[expressão for item in iterável if condição]`\n\n"
             "Se ficar longa demais para ler de uma vez, volte para o `for` normal. "
             "Os tipos usados aqui estão em [[Python: variáveis e tipos básicos]]."),
            (CODE,
             "numeros = range(1, 11)\n\n"
             "quadrados = [n * n for n in numeros]\n"
             "pares = [n for n in numeros if n % 2 == 0]\n"
             "por_paridade = {n: (\"par\" if n % 2 == 0 else \"ímpar\") for n in range(1, 5)}\n"
             "letras = {c for c in \"banana\"}\n\n"
             "print(quadrados)\nprint(pares)\nprint(por_paridade)\nprint(sorted(letras))",
             "python"),
        ],
    },
    {
        "author": "admin",
        "title": "Python: ambientes virtuais com venv",
        "folder": "Python",
        "summary": "Isolar as dependências de cada projeto para não quebrar os outros.",
        "tags": ["python", "ferramentas"],
        "blocks": [
            (TEXT,
             "Cada projeto deve ter o seu ambiente virtual. Assim a versão do FastAPI de um projeto "
             "não briga com a de outro, e o `requirements.txt` descreve exatamente o que o projeto usa."),
            (CODE,
             "# criar o ambiente (uma vez por projeto)\npython -m venv .venv\n\n"
             "# ativar\nsource .venv/bin/activate      # Linux/macOS\n.venv\\Scripts\\activate         # Windows\n\n"
             "# instalar e registrar dependências\npip install fastapi uvicorn\npip freeze > requirements.txt\n\n"
             "# em outra máquina\npip install -r requirements.txt",
             "bash"),
            (TEXT, "Não versione a pasta `.venv`: coloque-a no `.gitignore` (veja [[Git: comandos do dia a dia]])."),
        ],
    },
    {
        "author": "admin",
        "title": "Git: comandos do dia a dia",
        "folder": "Git e GitHub",
        "summary": "O fluxo de branch, commit e pull request que mais aparece no trabalho.",
        "tags": ["git", "cheatsheet"],
        "blocks": [
            (TEXT,
             "## Fluxo básico\n\n"
             "1. Atualize a `main` e crie uma branch para a tarefa.\n"
             "2. Faça commits pequenos, com mensagens que dizem o *porquê*.\n"
             "3. Envie a branch e abra um **pull request** para revisão.\n\n"
             "> Use `git status` antes de qualquer comando que apaga ou reescreve algo."),
            (CODE,
             "git switch main && git pull\n"
             "git switch -c feat/busca-por-tag\n\n"
             "git add -p                 # escolhe trecho por trecho\n"
             "git commit -m \"feat: adiciona busca por tag\"\n"
             "git push -u origin feat/busca-por-tag",
             "bash"),
            (TEXT, "Fez besteira? Veja [[Git: desfazendo erros]]."),
        ],
    },
    {
        "author": "admin",
        "title": "Git: desfazendo erros",
        "folder": "Git e GitHub",
        "summary": "Qual comando usar para voltar atrás em cada situação.",
        "tags": ["git", "cheatsheet"],
        "blocks": [
            (TEXT,
             "| Situação | Comando |\n|---|---|\n"
             "| Descartar mudanças de um arquivo | `git restore arquivo.py` |\n"
             "| Tirar um arquivo do *stage* | `git restore --staged arquivo.py` |\n"
             "| Corrigir a mensagem do último commit (ainda não enviado) | `git commit --amend` |\n"
             "| Desfazer o último commit mantendo as mudanças | `git reset --soft HEAD~1` |\n"
             "| Desfazer um commit que já foi enviado | `git revert <hash>` |\n"
             "| Achar um commit \"perdido\" | `git reflog` |\n\n"
             "**Regra de ouro:** em branch compartilhada, prefira `git revert`. "
             "`reset` e `--amend` reescrevem o histórico e atrapalham quem já baixou a branch."),
            (CODE,
             "# voltei a branch sem querer? o reflog guarda tudo por um tempo\ngit reflog\n"
             "git switch -c resgate <hash-do-reflog>",
             "bash"),
        ],
    },
    {
        "author": "admin",
        "title": "SQL: tipos de JOIN",
        "folder": "Banco de dados",
        "summary": "Quando usar INNER, LEFT e FULL JOIN, com exemplos.",
        "tags": ["sql", "banco-de-dados"],
        "blocks": [
            (TEXT,
             "| JOIN | Retorna |\n|---|---|\n"
             "| `INNER` | só as linhas com par nas duas tabelas |\n"
             "| `LEFT` | todas as da esquerda, com `NULL` quando não há par |\n"
             "| `FULL` | todas as das duas tabelas |\n\n"
             "O erro mais comum é usar `INNER` e \"perder\" linhas sem perceber. "
             "Se a pergunta é \"todos os usuários, mesmo os sem páginas\", é `LEFT`."),
            (CODE,
             "-- quantas páginas cada usuário escreveu (inclui quem tem zero)\n"
             "SELECT u.username, COUNT(p.id) AS paginas\nFROM users u\n"
             "LEFT JOIN pages p ON p.author_id = u.id\nGROUP BY u.username\nORDER BY paginas DESC;",
             "sql"),
            (TEXT,
             "Consulta lenta? Veja [[SQL: índices na prática]]. Para expor isso numa API, "
             "veja [[FastAPI: rotas com dependências]]."),
        ],
    },
    {
        "author": "admin",
        "title": "SQL: índices na prática",
        "folder": "Banco de dados",
        "summary": "O que um índice acelera, o que ele custa e como verificar se está sendo usado.",
        "tags": ["sql", "banco-de-dados", "desempenho"],
        "blocks": [
            (TEXT,
             "Um índice é como o índice remissivo de um livro: acelera **buscas** e **ordenações** "
             "pela coluna indexada, mas deixa `INSERT` e `UPDATE` um pouco mais lentos e ocupa espaço.\n\n"
             "- Indexe colunas usadas em `WHERE`, `JOIN` e `ORDER BY` com frequência.\n"
             "- Não indexe colunas com pouquíssimos valores distintos (como um booleano).\n"
             "- Em índices compostos, a ordem das colunas importa."),
            (CODE,
             "CREATE INDEX ix_page_author ON pages (author_id);\n\n"
             "-- confira se o banco usa o índice\nEXPLAIN QUERY PLAN\n"
             "SELECT * FROM pages WHERE author_id = 7;",
             "sql"),
        ],
    },
    {
        "author": "admin",
        "title": "HTTP: métodos e códigos de status",
        "folder": "Web e APIs",
        "summary": "Referência rápida para desenhar e depurar APIs REST.",
        "tags": ["http", "api"],
        "blocks": [
            (TEXT,
             "| Método | Uso | Idempotente? |\n|---|---|---|\n"
             "| `GET` | ler | sim |\n| `POST` | criar | não |\n| `PUT` | substituir | sim |\n"
             "| `PATCH` | alterar parte | depende |\n| `DELETE` | remover | sim |"),
            (TEXT,
             "| Código | Significado |\n|---|---|\n"
             "| `200` | OK |\n| `201` | criado |\n| `204` | sem conteúdo (comum em `DELETE`) |\n"
             "| `400` | requisição inválida |\n| `401` | não autenticado |\n| `403` | autenticado, mas sem permissão |\n"
             "| `404` | não encontrado |\n| `422` | dados com formato válido mas conteúdo inválido |\n"
             "| `500` | erro no servidor |\n\n"
             "Dica: para recursos privados, responder `404` em vez de `403` evita revelar que eles existem."),
        ],
    },
    {
        "author": "admin",
        "title": "FastAPI: rotas com dependências",
        "folder": "Web e APIs",
        "summary": "Como reaproveitar autenticação e sessão de banco com Depends.",
        "tags": ["python", "fastapi", "api"],
        "blocks": [
            (TEXT,
             "Com `Depends`, o FastAPI resolve a sessão do banco e o usuário logado **antes** de chamar a rota. "
             "Cada endpoint recebe o que precisa, sem repetir código, e os testes podem trocar a dependência "
             "por uma versão falsa.\n\n"
             "Antes, revise [[Python: variáveis e tipos básicos]] e os códigos em [[HTTP: métodos e códigos de status]]."),
            (CODE,
             "from fastapi import Depends, FastAPI, HTTPException\n\napp = FastAPI()\n\n\n"
             "def usuario_atual(token: str | None = None) -> str:\n"
             "    if token != \"segredo\":\n"
             "        raise HTTPException(status_code=401, detail=\"Não autenticado\")\n"
             "    return \"ana\"\n\n\n"
             "@app.get(\"/me\")\ndef me(usuario: str = Depends(usuario_atual)):\n"
             "    return {\"usuario\": usuario}",
             "python"),
        ],
    },
    {
        "author": "admin",
        "title": "Terminal: comandos essenciais",
        "folder": "Linux e terminal",
        "summary": "Navegar, procurar arquivos e inspecionar processos sem sair do terminal.",
        "tags": ["linux", "cheatsheet", "ferramentas"],
        "blocks": [
            (TEXT,
             "| Tarefa | Comando |\n|---|---|\n"
             "| Onde estou? | `pwd` |\n| Listar com detalhes | `ls -lah` |\n"
             "| Procurar arquivo pelo nome | `find . -name \"*.py\"` |\n"
             "| Procurar texto dentro de arquivos | `grep -rn \"TODO\" .` |\n"
             "| Ver o fim de um log ao vivo | `tail -f app.log` |\n"
             "| Quem está usando a porta 8000? | `lsof -i :8000` |\n"
             "| Espaço em disco | `df -h` e `du -sh *` |"),
            (CODE,
             "# matar o servidor que ficou preso na porta 8000\nlsof -ti :8000 | xargs kill\n\n"
             "# repetir o último comando com sudo\nsudo !!",
             "bash"),
        ],
    },
    {
        "author": "ana",
        "title": "Algoritmos: busca binária",
        "folder": "Algoritmos",
        "summary": "Encontrar um valor numa lista ordenada em O(log n) passos.",
        "tags": ["algoritmos", "python"],
        "blocks": [
            (TEXT,
             "A cada passo, olhamos o elemento do meio e descartamos metade da lista. "
             "Numa lista de 1 milhão de itens, são no máximo **20 comparações**.\n\n"
             "Pré-requisito: a lista precisa estar **ordenada**."),
            (CODE,
             "def busca_binaria(lista, alvo):\n"
             "    inicio, fim = 0, len(lista) - 1\n"
             "    passos = 0\n"
             "    while inicio <= fim:\n"
             "        passos += 1\n"
             "        meio = (inicio + fim) // 2\n"
             "        if lista[meio] == alvo:\n"
             "            return meio, passos\n"
             "        if lista[meio] < alvo:\n"
             "            inicio = meio + 1\n"
             "        else:\n"
             "            fim = meio - 1\n"
             "    return -1, passos\n\n\n"
             "numeros = list(range(0, 2_000_000, 2))\n"
             "for alvo in (0, 777_776, 1_999_998, 5):\n"
             "    posicao, passos = busca_binaria(numeros, alvo)\n"
             "    print(f\"alvo={alvo:>9}  posição={posicao:>7}  passos={passos}\")",
             "python"),
            (TEXT,
             "Na prática, use o módulo `bisect` da biblioteca padrão. "
             "Ele faz a mesma coisa e já está testado. Para gerar listas de teste rapidamente, veja [[Python: list comprehensions]]."),
        ],
    },
]

COMMENTS = [
    # (autor, título da página, texto)
    ("ana", "SQL: tipos de JOIN", "Valeria incluir um exemplo de self join, tipo funcionário e gerente na mesma tabela."),
    ("admin", "SQL: tipos de JOIN", "Boa ideia! Vou adicionar um bloco com esse exemplo."),
    ("ana", "Git: desfazendo erros", "O `git reflog` já me salvou duas vezes este semestre."),
    ("admin", "Algoritmos: busca binária", "Ótima explicação. O contador de passos deixa bem claro o O(log n)."),
]
