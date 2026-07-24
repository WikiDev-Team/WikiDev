# Como contribuir com o WikiDev

## Preparação

```bash
git clone https://github.com/WikiDev-Team/WikiDev.git
cd WikiDev
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
pytest
```

## Fluxo de branches

Não trabalhe diretamente em `main` ou `develop`.

```bash
git switch develop
git pull --rebase origin develop
git switch -c feat/nome-curto
```

Prefixos sugeridos: `feat/`, `fix/`, `refactor/`, `docs/`, `test/` e `chore/`.

## Antes de abrir o PR

```bash
pytest
coverage run -m pytest
coverage report
python -m compileall app tests scripts
```

Verifique também:

- Nenhum segredo ou `.env` foi commitado.
- Toda rota que altera dados exige autenticação.
- O servidor define a autoria; não confie em `author_id` do cliente.
- Novas consultas de páginas usam a política central em `app/permissions.py`.
- A interface possui estado vazio e funciona em tela pequena.
- Alterações de schema têm migração ou instruções explícitas.

## Commits

Use Conventional Commits:

```text
feat(folders): add nested folder privacy
fix(auth): revoke session after password reset
test(security): cover author spoofing
```

Com Commitizen instalado:

```bash
npm install
npm run commit
```

## Pull request

Explique o problema, a solução, como testar, riscos e arquivos que podem conflitar com outros PRs. Relacione issues com `Closes #n` somente quando todos os critérios de aceite estiverem atendidos.

Todo PR precisa de revisão. Use `Request changes` para falhas de segurança, perda de dados, ausência de testes ou comportamento incompatível com a branch de destino.
