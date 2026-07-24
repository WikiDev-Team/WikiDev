# feat: integra segurança, recuperação, pastas, amizade e testes

## Contexto

Esta contribuição foi reconciliada com a `develop` atual para formar uma entrega única e coerente. Ela preserva amizade e compartilhamento já implementados, acrescenta recuperação de senha, conclui os fluxos de pastas e páginas, centraliza autorização e amplia testes, documentação e infraestrutura.

## Principais mudanças

- Recuperação de senha por e-mail com token armazenado somente como hash, expiração e uso único.
- Sessões rotacionadas e persistidas apenas como hash.
- Política central de autorização para páginas e pastas, incluindo ancestrais privados.
- Solicitações de amizade e visibilidades `private`, `friends`, `public` e `custom` integradas à privacidade das pastas.
- Compartilhamento com permissão de visualização ou edição e revogação ao remover amizade.
- Criação, edição e exclusão de pastas hierárquicas públicas/privadas.
- Criação de página no contexto da pasta e associação de página existente.
- Proteção de autoria em comentários e exemplos.
- Schemas públicos de usuário sem e-mail.
- Interface HTMX integrada para dashboard, pastas, páginas, amizade e busca.
- Fixtures pytest, regressões de segurança, coverage e GitHub Actions.
- Seed, smoke test, Docker, README, licença MIT e roteiro de apresentação.

## Como testar

```bash
python -m venv .venv
source .venv/bin/activate
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

O PR #35 ainda deve ser preservado como fonte das funcionalidades de fórum, atividades e comentários por bloco. Ao integrá-lo, mantenha a política central de autorização, a autoria definida pelo servidor e os filtros de visibilidade desta branch. Consulte `docs/merge-pr35.md`.

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
Closes #8
Closes #7

Avança #10 e #24.
