# WikiDev

WikiDev é uma wiki colaborativa para organizar conhecimento de programação em páginas, blocos e pastas. O backend usa FastAPI e SQLModel; a interface é renderizada com Jinja2 e atualizada com HTMX.

## O que já está disponível

- Cadastro, login, logout e sessões por cookie `HttpOnly`.
- Recuperação de senha por e-mail com token aleatório, armazenado somente como hash, expiração e uso único.
- Páginas compostas por blocos de texto e código com destaque de sintaxe.
- Pastas hierárquicas, públicas ou privadas.
- Criação de página dentro de uma pasta e associação de página existente.
- Autorização no backend para leitura, edição e exclusão de páginas, pastas, comentários e exemplos.
- Busca global que respeita as mesmas regras de privacidade.
- Perfis públicos sem exposição do e-mail.
- Testes automatizados, cobertura e workflow de integração contínua.
- Docker, seed de demonstração e smoke test.

> O fórum, os comentários por bloco e a tela de atividades estão sendo desenvolvidos no PR #35. Consulte [`docs/merge-pr35.md`](docs/merge-pr35.md) antes de combinar as branches.

## Arquitetura

```text
app/
├── main.py            # aplicação, rotas de páginas HTML e tratamento de erros
├── models.py          # tabelas e schemas SQLModel
├── crud.py            # persistência e geração de slugs
├── permissions.py     # política central de leitura e edição
├── security.py        # hash de senha e tokens
├── config.py          # configuração por ambiente
├── mailer.py          # console/SMTP
└── routers/           # auth, páginas, pastas, blocos, busca e APIs auxiliares

templates/             # páginas e fragments HTMX
static/                # CSS, tema e imagens
tests/                 # testes funcionais, segurança e CRUD
scripts/               # seed e smoke test
```

### Regra de visibilidade

O autor sempre pode visualizar e editar seu conteúdo. Outros usuários só podem visualizar uma página quando ela está `published`; caso a página pertença a uma pasta, a pasta também precisa ser pública. Todas as rotas consultam `app/permissions.py`, inclusive a busca.

## Instalação local

Requisitos: Python 3.11 ou 3.12.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate      # Windows
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

A aplicação fica em `http://127.0.0.1:8000`. A documentação OpenAPI fica em `/docs`.

### Dados de demonstração

```bash
python -m scripts.seed_demo
```

Credenciais criadas pelo seed: `admin` / `admin123`. Use apenas em desenvolvimento.

## Recuperação de senha

No desenvolvimento, `MAIL_MODE=console` registra o link de recuperação no terminal. Para envio real:

```env
APP_ENV=production
APP_BASE_URL=https://wiki.exemplo.com
SECURE_COOKIES=true
MAIL_MODE=smtp
MAIL_FROM=WikiDev <no-reply@exemplo.com>
SMTP_HOST=smtp.exemplo.com
SMTP_PORT=587
SMTP_USERNAME=usuario
SMTP_PASSWORD=segredo
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

O endpoint sempre devolve a mesma mensagem, exista ou não uma conta, evitando enumeração de e-mails. Solicitar um novo link invalida os anteriores.

## Testes

```bash
pytest
coverage run -m pytest
coverage report
```

Para testar uma instância já em execução:

```bash
python scripts/test_backend.py
```

O GitHub Actions executa a suíte em Python 3.11 e 3.12 em pushes e pull requests para `main` e `develop`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

O banco SQLite é persistido no volume `wikidev_data`.

## Endpoints principais

| Área | Rotas |
|---|---|
| Autenticação | `POST /register`, `POST /login`, `POST /logout` |
| Recuperação | `GET/POST /forgot-password`, `GET/POST /reset-password` |
| Páginas | `/pages/`, `/pages/{id}`, `/pages/{id}/blocks-editor` |
| Pastas | `/folders/`, `/folders/{id}/pages`, `/folders/{id}/pages/{page_id}` |
| Comentários | `/comments/`, `/comments/{id}` |
| Exemplos | `/examples/`, `/examples/{id}` |
| Busca | `GET /busca?q=...` |
| Saúde | `GET /health` |

## Segurança aplicada

- Senhas com bcrypt e limite de entrada compatível com o algoritmo.
- Cookies `HttpOnly`, `SameSite=Lax` e `Secure` em produção.
- Rotação de sessão no login, armazenamento apenas do hash do token e revogação no logout ou após redefinir a senha.
- Tokens de redefinição não são persistidos em texto puro.
- Autoria definida pelo servidor: `author_id` enviado pelo cliente é ignorado.
- E-mail ausente de schemas públicos.
- Rota de login de desenvolvimento desativada por padrão e proibida em produção.
- Exclusões limpam dependências ou são bloqueadas quando quebrariam referências.

## Migrações

`init_db()` cria as tabelas e contém uma migração SQLite pequena e idempotente para bancos anteriores à coluna `folder.visibility`. Antes de produção ou de novas alterações de schema, o próximo passo recomendado é adotar Alembic.

## Contribuindo

Leia [`CONTRIBUTING.md`](CONTRIBUTING.md). A descrição técnica desta entrega está em [`docs/contribution-report.md`](docs/contribution-report.md), e o roteiro de apresentação está em [`docs/presentation.md`](docs/presentation.md).

## Licença

Distribuído sob a licença MIT. Consulte [`LICENSE`](LICENSE).
