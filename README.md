# WikiDev

WikiDev é uma wiki colaborativa para organizar conhecimento de programação em páginas, blocos e pastas. O backend usa FastAPI e SQLModel; a interface é renderizada com Jinja2 e atualizada com HTMX.

## Funcionalidades

- Cadastro, login, logout e sessões por cookie `HttpOnly`.
- Recuperação de senha por e-mail com token aleatório, armazenado somente como hash, expiração e uso único.
- Páginas compostas por blocos de texto e código com destaque de sintaxe.
- Pastas hierárquicas, públicas ou privadas, sem possibilidade de ciclos.
- Criação de página dentro de pasta e associação ou remoção de páginas existentes.
- Solicitações de amizade, perfis públicos e remoção de amizade.
- Páginas privadas, públicas, para amigos ou compartilhadas com amigos específicos.
- Permissões separadas de visualização e edição, com revogação dos compartilhamentos diretos ao remover uma amizade.
- Autorização no backend para páginas, pastas, blocos, comentários e exemplos.
- Busca global que respeita as mesmas regras de privacidade.
- Perfis e listagens públicas sem exposição do e-mail.
- Testes automatizados, cobertura e workflow de integração contínua.
- Docker, seed de demonstração e smoke test.

> O fórum, comentários por bloco e a tela de atividades estão sendo desenvolvidos no PR #35. Consulte [`docs/merge-pr35.md`](docs/merge-pr35.md) antes de combinar as branches.

## Arquitetura

```text
app/
├── main.py            # aplicação, dashboard e tratamento de erros
├── models.py          # tabelas e schemas SQLModel
├── crud.py            # persistência e geração de slugs
├── permissions.py     # política central de acesso e compartilhamento
├── security.py        # hash de senha e tokens
├── config.py          # configuração por ambiente
├── mailer.py          # envio por console ou SMTP
└── routers/           # auth, páginas, pastas, amizade, busca e APIs

templates/             # páginas e fragmentos HTMX
static/                # CSS, tema e imagens
tests/                 # testes funcionais, segurança e CRUD
scripts/               # seed e smoke test
```

### Visibilidade e estado

O estado da página (`draft`, `published` ou `archived`) é independente da visibilidade (`private`, `friends`, `public` ou `custom`). O autor sempre possui acesso. Páginas em pastas também obedecem à privacidade da pasta e de todos os seus ancestrais: uma pasta filha pública não contorna uma pasta pai privada.

Para visibilidade `custom`, apenas amizades aceitas podem receber acesso direto. Uma pessoa marcada como editora também recebe visualização. Somente o autor pode excluir a página ou alterar seus compartilhamentos.

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

O endpoint sempre devolve a mesma mensagem, exista ou não uma conta, evitando enumeração de e-mails. Solicitar novo link invalida os anteriores.

## Testes

```bash
pytest
coverage run -m pytest
coverage report
```

Para testar uma instância em execução:

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
| Amizades | `/friends`, `/friendships/request/{user_id}`, `/friendships/{id}/...` |
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
- Busca e leitura aplicam a mesma política central de permissões.
- Exclusões limpam dependências e compartilhamentos explícitos.

## Migrações

`init_db()` cria as tabelas e contém migrações SQLite idempotentes para bancos anteriores às colunas `page.visibility` e `folder.visibility`. Antes de produção ou de novas alterações de schema, o próximo passo recomendado é adotar Alembic.

## Contribuindo

Leia [`CONTRIBUTING.md`](CONTRIBUTING.md). A descrição técnica desta entrega está em [`docs/contribution-report.md`](docs/contribution-report.md), e o roteiro de apresentação em [`docs/presentation.md`](docs/presentation.md).

## Licença

Distribuído sob a licença MIT. Consulte [`LICENSE`](LICENSE).
