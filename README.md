
# WikiDev

Plataforma colaborativa para criação, organização e compartilhamento de documentação sobre programação.

O WikiDev permite que desenvolvedores registrem conhecimento técnico em páginas compostas por blocos de texto e código, organizem o conteúdo em pastas, compartilhem materiais com outros usuários e interajam por meio de comentários e atividades recentes.

O projeto foi desenvolvido em 2026 para a disciplina **MAC0350 — Introdução ao Desenvolvimento de Sistemas de Software**, com foco na aplicação integrada de engenharia de software, orientação a objetos, bancos de dados relacionais, testes automatizados e desenvolvimento colaborativo.

## Funcionalidades

### Autenticação e usuários

- Cadastro, login e logout.
- Sessões autenticadas por cookies `HttpOnly`.
- Perfis públicos sem exposição do endereço de e-mail.
- Edição das informações do perfil.
- Recuperação de senha por e-mail.
- Tokens de recuperação com expiração e uso único.

### Páginas e documentação

- Criação, edição, visualização e exclusão de páginas.
- Páginas compostas por blocos independentes.
- Blocos de texto e blocos de código.
- Destaque de sintaxe para exemplos de código.
- Associação de linguagens e tags.
- Estados de página:
  - `draft`;
  - `published`;
  - `archived`.
- Criação de páginas dentro de pastas.
- Associação e remoção de páginas existentes em pastas.

### Pastas

- Organização hierárquica de pastas.
- Pastas públicas ou privadas.
- Árvore de arquivos na barra lateral.
- Pastas expansíveis e recolhíveis.
- Criação contextual de páginas dentro de uma pasta.
- Validação para impedir ciclos na hierarquia.
- Controle de acesso aplicado também às pastas ancestrais.

### Comentários e fórum

- Comentários gerais em páginas.
- Comentários associados a blocos específicos.
- Comentários contendo texto e trechos adicionais de código.
- Respostas a comentários.
- Edição e exclusão de comentários.
- Controle de permissão para comentar.
- Fórum com atividades recentes.
- Navegação direta de uma atividade para o comentário relacionado.

### Amizades e compartilhamento

- Envio de solicitações de amizade.
- Aceitação, recusa e cancelamento de solicitações.
- Remoção de amizades.
- Compartilhamento de páginas com amigos.
- Permissões independentes de visualização e edição.
- Revogação de compartilhamentos diretos após a remoção de uma amizade.

As páginas podem utilizar as seguintes regras de visibilidade:

- `private`: somente o autor pode acessar;
- `friends`: os amigos do autor podem visualizar;
- `public`: qualquer usuário pode visualizar;
- `custom`: somente amigos selecionados podem acessar.

O estado de uma página é independente de sua visibilidade. Uma página pode, por exemplo, estar publicada e continuar privada.

### Busca

- Busca por páginas e conteúdos.
- Busca por tags e linguagens.
- Resultados filtrados de acordo com as permissões do usuário.
- Conteúdos privados não são expostos para usuários sem acesso.

## Tecnologias

### Backend

- Python 3.11 ou 3.12
- FastAPI
- SQLModel
- SQLAlchemy
- Pydantic
- Uvicorn
- bcrypt

### Frontend

- Jinja2
- HTMX
- HTML
- CSS
- JavaScript

### Persistência

- SQLite no ambiente local
- Banco relacional configurável por `DATABASE_URL`

### Qualidade e infraestrutura

- Pytest
- Coverage.py
- GitHub Actions
- Docker
- Docker Compose
- Commitizen
- ESLint
- Husky

## Arquitetura

```text
WikiDev/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── db.py
│   ├── dependencies.py
│   ├── permissions.py
│   ├── security.py
│   ├── config.py
│   ├── mailer.py
│   └── routers/
│       ├── auth.py
│       ├── comments.py
│       ├── examples.py
│       ├── folders.py
│       ├── friendships.py
│       ├── languages.py
│       ├── page_blocks.py
│       ├── pages.py
│       ├── search.py
│       ├── tags.py
│       └── users.py
├── templates/
├── static/
├── tests/
├── scripts/
├── docs/
├── docker/
├── .github/
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

A aplicação está dividida em rotas especializadas, enquanto as regras de autorização são centralizadas em `app/permissions.py`.

Os modelos relacionais são definidos com SQLModel, e as páginas HTML são renderizadas com Jinja2. O HTMX permite atualizar partes da interface sem recarregar completamente a página.

## Instalação local

### Pré-requisitos

- Python 3.11 ou 3.12
- Git
- Node.js e npm, apenas para as ferramentas de desenvolvimento e padronização de commits

### 1. Clonar o repositório

```bash
git clone https://github.com/WikiDev-Team/WikiDev.git
cd WikiDev
```

### 2. Criar o ambiente virtual

#### Linux ou macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instalar as dependências

Para executar somente a aplicação:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para desenvolver e executar os testes:

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

As ferramentas de padronização de commits podem ser instaladas com:

```bash
npm install
```

### 4. Configurar o ambiente

Copie o arquivo de exemplo:

#### Linux ou macOS

```bash
cp .env.example .env
```

#### Windows

```powershell
Copy-Item .env.example .env
```

No ambiente local, a aplicação utiliza SQLite por padrão:

```env
DATABASE_URL=sqlite:///./wikidev.db
```

### 5. Executar a aplicação

```bash
uvicorn app.main:app --reload
```

A aplicação estará disponível em:

```text
http://127.0.0.1:8000
```

A documentação automática da API estará disponível em:

```text
http://127.0.0.1:8000/docs
```

O endpoint de verificação de saúde pode ser acessado em:

```text
http://127.0.0.1:8000/health
```

## Dados de demonstração

Para criar usuários e conteúdos de demonstração:

```bash
python -m scripts.seed_demo
```

O seed cria a seguinte conta administrativa:

```text
Usuário: admin
Senha: admin123
```

Essas credenciais devem ser utilizadas somente em ambientes locais de desenvolvimento.

## Execução com Docker

Crie o arquivo de configuração:

```bash
cp .env.example .env
```

Inicie a aplicação:

```bash
docker compose up --build
```

A aplicação ficará disponível na porta `8000`.

Para encerrar os contêineres:

```bash
docker compose down
```

O banco SQLite é persistido em um volume do Docker, evitando a perda dos dados ao recriar o contêiner da aplicação.

## Recuperação de senha

No ambiente de desenvolvimento, utilize:

```env
MAIL_MODE=console
```

Nesse modo, o link de recuperação de senha é exibido no terminal da aplicação.

Para utilizar um servidor SMTP:

```env
APP_ENV=production
APP_BASE_URL=https://seu-dominio.com
SECURE_COOKIES=true

MAIL_MODE=smtp
MAIL_FROM=WikiDev <no-reply@seu-dominio.com>

SMTP_HOST=smtp.seu-provedor.com
SMTP_PORT=587
SMTP_USERNAME=seu-usuario
SMTP_PASSWORD=sua-senha
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

Por segurança:

- a aplicação retorna a mesma resposta independentemente de o e-mail estar cadastrado;
- os tokens não são armazenados em texto puro;
- os tokens possuem tempo de expiração;
- cada token pode ser utilizado apenas uma vez;
- a criação de um novo link invalida os links anteriores.

## Testes

Execute toda a suíte com:

```bash
pytest
```

Para executar os testes com medição de cobertura:

```bash
coverage run -m pytest
coverage report -m
```

Para gerar um relatório HTML:

```bash
coverage html
```

O relatório será criado no diretório:

```text
htmlcov/
```

A parte de backend deve manter cobertura mínima de **90%**, incluindo testes unitários, de integração e funcionais.

Também é possível executar o smoke test contra uma instância ativa:

```bash
python scripts/test_backend.py
```

O GitHub Actions executa automaticamente a suíte de testes em pushes e pull requests direcionados às branches `main` e `develop`.

## Endpoints principais

| Área | Rotas |
|---|---|
| Autenticação | `POST /register`, `POST /login`, `POST /logout` |
| Recuperação de senha | `GET/POST /forgot-password`, `GET/POST /reset-password` |
| Dashboard | `GET /dashboard` |
| Páginas | `/pages/`, `/pages/{id}`, `/pages/{id}/blocks-editor` |
| Pastas | `/folders/`, `/folders/{id}/pages`, `/folders/{id}/pages/{page_id}` |
| Comentários | `/comments/`, `/comments/{id}` |
| Exemplos | `/examples/`, `/examples/{id}` |
| Amizades | `/friends`, `/friendships/request/{user_id}`, `/friendships/{id}/...` |
| Busca | `GET /busca?q=...` |
| Saúde | `GET /health` |

## Segurança

O WikiDev aplica as seguintes medidas de segurança:

- senhas armazenadas com bcrypt;
- cookies de sessão com `HttpOnly`;
- cookies com `SameSite=Lax`;
- cookies `Secure` no ambiente de produção;
- rotação do token de sessão durante o login;
- armazenamento somente do hash dos tokens;
- revogação da sessão no logout;
- revogação das sessões após redefinição de senha;
- tokens de recuperação com expiração e uso único;
- proteção contra enumeração de e-mails;
- definição da autoria pelo servidor;
- remoção do e-mail dos schemas e perfis públicos;
- validação de acesso no backend;
- busca sujeita às mesmas permissões utilizadas na leitura direta;
- remoção de dependências e compartilhamentos durante exclusões;
- validação de propriedade antes de inserir páginas em pastas.

Somente o autor pode excluir uma página ou modificar seus compartilhamentos.

Nas páginas com visibilidade `custom`, apenas amizades aceitas podem receber acesso direto. Um usuário com permissão de edição também possui permissão de visualização.

## Banco de dados

O banco é configurado pela variável:

```env
DATABASE_URL=sqlite:///./wikidev.db
```

A função `init_db()` cria as tabelas necessárias ao iniciar a aplicação.

O projeto também possui migrações idempotentes para bancos SQLite criados antes de algumas alterações de visibilidade. Para uma implantação em produção ou para futuras mudanças estruturais, recomenda-se a adoção de uma ferramenta dedicada de migrações, como Alembic.

## Documentação técnica

A documentação do projeto está disponível no diretório [`docs`](docs/):

- [Diagrama de classes](docs/class_diagram.md)
- [Modelo entidade-relacionamento](docs/erd.mmd)
- [Esquema relacional](docs/database_schema.sql)
- [Relatório técnico das contribuições](docs/contribution-report.md)
- [Roteiro da apresentação](docs/presentation.md)

## Fluxo de desenvolvimento

O projeto utiliza as seguintes branches:

```text
main
└── develop
    └── feature/nome-da-funcionalidade
```

- `main`: versão estável do projeto;
- `develop`: integração das funcionalidades;
- `feature/*`: desenvolvimento de novas funcionalidades;
- `fix/*`: correções comuns;
- `hotfix/*`: correções urgentes.

Antes de iniciar uma tarefa:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/nome-da-feature
```

Os commits seguem o padrão Conventional Commits e podem ser criados com:

```bash
git add .
npm run commit
```

As alterações devem ser enviadas por pull request e revisadas antes da integração.

Para mais informações, consulte o arquivo [CONTRIBUTING.md](CONTRIBUTING.md).

## Equipe

Projeto desenvolvido colaborativamente pela organização [WikiDev-Team](https://github.com/WikiDev-Team).

O histórico completo de contribuições pode ser consultado na página de contribuidores do repositório.

## Licença

Este projeto é distribuído sob a licença MIT.

Consulte o arquivo [LICENSE](LICENSE) para mais informações.

