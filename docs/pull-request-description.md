# feat: estabiliza autenticação, pastas, permissões e testes

## Contexto

Esta contribuição transforma o protótipo enviado em um fluxo utilizável e testável, priorizando as issues abertas que formam uma entrega coesa: recuperação de senha, pastas/páginas, privacidade, revisão, documentação e automação de testes.

## Principais mudanças

- Recuperação de senha por e-mail com token armazenado como hash, expiração e uso único.
- Sessões rotacionadas e persistidas apenas como hash.
- Política central de autorização para páginas e pastas, incluindo ancestrais privados.
- Criação, edição e exclusão de pastas hierárquicas públicas/privadas.
- Criação de página no contexto da pasta e associação de página existente.
- Proteção de autoria em comentários e exemplos.
- Schemas públicos de usuário sem e-mail.
- Nova interface HTMX responsiva para dashboard, pastas, páginas e busca.
- Fixtures pytest, regressões de segurança, coverage e GitHub Actions.
- Seed, smoke test, Docker, README, licença MIT e roteiro Marp.

## Como testar

```bash
pip install -r requirements-dev.txt
pytest
coverage run -m pytest
coverage report
python -m compileall app tests scripts
python -m scripts.seed_demo
uvicorn app.main:app --reload
python scripts/test_backend.py
```

## Integração com o PR #35

O PR #35 deve continuar sendo a fonte das funcionalidades de fórum, atividades e comentários por bloco. Durante o rebase, preservar desta contribuição a autorização central, a autoria definida pelo servidor e o filtro de visibilidade. Consulte `docs/merge-pr35.md`.

## Issues

Closes #32
Closes #31
Closes #25
Closes #23
Closes #22
Closes #21
Closes #15
Closes #14
Closes #13
Closes #11
Closes #7

Avança #10 e #24.
