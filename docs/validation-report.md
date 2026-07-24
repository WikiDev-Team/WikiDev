# Relatório de validação

Data: 21 de julho de 2026.

## Base integrada

A resolução foi preparada entre:

- contribuição: `2f4e42b4a70b25487b963e05383c612172bb65a6`;
- `origin/develop`: `c6e4f7e322388888af20e90de2ff52fb486deaa5`;
- ancestral comum: `3b0741400307436ba4de6f9969fb93fb9dffefe7`.

A integração preserva amizade, compartilhamento e os testes já presentes na `develop`, acrescentando recuperação de senha, privacidade hierárquica de pastas, endurecimento de autorização, documentação e CI.

## Validações concluídas

- Ausência de marcadores de conflito em todos os arquivos resolvidos.
- Parsing AST de todos os arquivos Python em `app/`, `tests/` e `scripts/`.
- Compilação com `python -m compileall app tests scripts`.
- Verificação estática de imports locais e símbolos importados.
- Parsing de todos os templates Jinja2 e verificação de `include`/`extends`.
- Parsing de `package.json` e `package-lock.json`.
- Parsing de `docker-compose.yml` e `.github/workflows/tests.yml` com PyYAML.
- Parsing estrutural do CSS sem erros.
- Verificação de rotas duplicadas.
- Busca estática por autoria arbitrária, CORS curinga e exposição pública de e-mail.

## Suíte integrada

A árvore final contém 19 testes cobrindo:

- registro, login, logout e bloqueio do login de desenvolvimento;
- armazenamento apenas do hash do token de sessão;
- recuperação de senha, expiração, uso único e resposta contra enumeração;
- ciclo completo de solicitação e aceitação de amizade;
- páginas privadas, públicas, para amigos e compartilhadas;
- permissões distintas de visualização e edição;
- revogação de compartilhamento direto ao remover amizade;
- criação, privacidade e hierarquia de pastas;
- criação de páginas no contexto e associação/desassociação;
- prevenção de ciclos e de bypass por ancestral privado;
- autorização de páginas, pastas, blocos, comentários e exemplos;
- autoria de comentários definida pelo servidor;
- schemas públicos sem e-mail;
- busca sem vazamento de conteúdo privado;
- slugs, hash de senha, posição e tamanho de blocos.

## Limitação deste ambiente

A execução real de `pytest` não pôde ser iniciada porque este ambiente não possui `sqlmodel` e `bcrypt`, e o índice de pacotes disponível não forneceu essas dependências. O erro de importação observado foi:

```text
ModuleNotFoundError: No module named 'sqlmodel'
```

Isso não equivale a uma suíte aprovada. O workflow de CI instala `requirements-dev.txt` antes de executar os testes em Python 3.11 e 3.12. Após aplicar a resolução, rode obrigatoriamente:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest
coverage run -m pytest
coverage report
```
