<p align="center"><img src="static/wikidev_logo.png" alt="" width="72"></p>

<h1 align="center">WikiDev</h1>

<p align="center">
  Uma wiki colaborativa para quem programa: páginas com texto em Markdown e código que roda no navegador,<br>
  organizadas em pastas, ligadas entre si e compartilhadas com amigos.
</p>

<p align="center">
  <a href="https://github.com/WikiDev-Team/WikiDev/actions/workflows/tests.yml"><img src="https://github.com/WikiDev-Team/WikiDev/actions/workflows/tests.yml/badge.svg" alt="Testes"></a>
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white" alt="Python 3.11 e 3.12">
  <img src="https://img.shields.io/badge/FastAPI-HTMX-009688?logo=fastapi&logoColor=white" alt="FastAPI e HTMX">
  <img src="https://img.shields.io/badge/licen%C3%A7a-MIT-blue" alt="Licença MIT">
</p>

<p align="center">
  <a href="https://render.com/deploy?repo=https://github.com/WikiDev-Team/WikiDev"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Publicar no Render"></a>
</p>

<p align="center"><img src="docs/img/demo.gif" alt="Entrando na demonstração, buscando uma página com Ctrl+K e executando um bloco de Python" width="860"></p>

<p align="center">
  <a href="#tour-em-imagens">Tour em imagens</a> ·
  <a href="#como-rodar-localmente">Rodar localmente</a> ·
  <a href="#deploy-no-render">Deploy no Render</a> ·
  <a href="#funcionalidades">Funcionalidades</a> ·
  <a href="#in-english">English</a>
</p>

## O que é

WikiDev é uma wiki colaborativa para organizar o que você aprende de programação. Cada página é feita de **blocos** de texto (Markdown) e de código, as páginas ficam em **pastas** e **tags**, se ligam com `[[links]]` e podem ser privadas, públicas, só para amigos ou compartilhadas com pessoas específicas. Blocos de Python rodam no próprio navegador, e várias pessoas podem editar a mesma página ao mesmo tempo.

O backend usa FastAPI e SQLModel (SQLite por padrão); a interface é renderizada no servidor com Jinja2 e atualizada com HTMX, sem etapa de build de front-end.

## Destaques

- **Código que roda na página.** Blocos de Python ganham "Executar", com [Pyodide](https://pyodide.org) dentro de um iframe isolado. Gráficos do matplotlib aparecem na página, a saída pode ser salva junto, "Experimentar" deixa mexer no código sem alterar a página e "Bifurcar" copia o bloco para uma página sua.
- **Edição simultânea.** Quem está na página aparece no topo, blocos em edição ganham um aviso, mudanças dos outros chegam sozinhas e salvamentos ao mesmo tempo são mesclados linha a linha.
- **Navegação de wiki.** Barra lateral em árvore, breadcrumbs com o caminho completo, home com favoritas, vistas recentemente e mais vistas, e filtros por dono, tag e texto.
- **Wiki de verdade.** Links com `[[Título]]`, seção "Citada em", páginas por tag e histórico de versões com diff e restauração.
- **Busca instantânea.** Ctrl+K encontra páginas, conteúdo, pastas, tags e pessoas, sempre respeitando as permissões.
- **Social e privado ao mesmo tempo.** Amigos, fórum e comentários por bloco, com controle de quem vê e quem edita.
- **Pronto para publicar.** Docker, blueprint do Render, testes automatizados e CI.

## Tour em imagens

### Navegação

A barra lateral mostra as pastas em árvore com as páginas dentro, e o topo de cada página traz o caminho completo de pastas.

![Barra lateral em árvore e breadcrumbs](docs/img/navegacao/arvore-e-breadcrumb.png)

| Início com favoritas, recentes e mais vistas | "Todas as páginas" com filtros e ordenação |
|---|---|
| ![Página inicial](docs/img/navegacao/home.png) | ![Filtros da lista de páginas](docs/img/navegacao/filtros.png) |

### Python no navegador

Clique em **Executar** e o código roda ali mesmo, com `print`, erros e gráficos do matplotlib. **Salvar saída na página** guarda o resultado para quem ler depois.

![Bloco de Python com gráfico do matplotlib](docs/img/python/grafico-executado.png)

| Experimentar: edite e rode sem mudar a página | Bifurcar: o bloco vira uma página privada sua |
|---|---|
| ![Modo Experimentar](docs/img/python/experimentar-aviso.png) | ![Página bifurcada](docs/img/python/bifurcado.png) |

### Edição simultânea

| Quem está na página e o que está sendo editado | Conflito nas mesmas linhas: nada é sobrescrito |
|---|---|
| ![Presença de outra pessoa na página](docs/img/edicao-simultanea/presence.png) | ![Marcadores de conflito](docs/img/edicao-simultanea/conflict.png) |

Quando as duas pessoas mexem em partes diferentes do mesmo bloco, as alterações são combinadas sozinhas:

<p align="center"><img src="docs/img/edicao-simultanea/merged.png" alt="Alterações de duas pessoas combinadas" width="600"></p>

### Links, histórico e tags

| `[[Links]]` e "Citada em" | Histórico com diff e restauração |
|---|---|
| ![Links entre páginas e citações](docs/img/wiki/links-e-citacoes.png) | ![Histórico de versões](docs/img/wiki/historico.png) |
| **Busca rápida (Ctrl+K)** | **Página de uma tag** |
| ![Busca rápida](docs/img/busca.png) | ![Página de tag](docs/img/wiki/pagina-de-tag.png) |

### No celular

<p align="center">
  <img src="docs/img/navegacao/celular-arvore.png" alt="Menu em árvore no celular" width="240">
  &nbsp;&nbsp;
  <img src="docs/img/python/celular.png" alt="Python executado no celular" width="240">
</p>

## Como rodar localmente

Requisitos: Python 3.11 ou 3.12. Não precisa de Node nem de banco externo.

```bash
git clone https://github.com/WikiDev-Team/WikiDev.git
cd WikiDev
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # Windows: copy .env.example .env
python -m scripts.seed_demo        # opcional: páginas de exemplo
uvicorn app.main:app --reload
```

Abra `http://127.0.0.1:8000`. A documentação da API (OpenAPI) fica em `/docs`.

O seed cria 12 páginas de referência (Python, Git, SQL, HTTP, FastAPI, terminal e algoritmos) em pastas e tags, com links entre elas, uma amizade e alguns comentários. Pode rodar de novo: as páginas de demonstração são atualizadas para o conteúdo de `scripts/demo_content.py`, e as páginas criadas por pessoas não são alteradas. Ele cria as contas `admin` / `admin123` e `ana` / `ana12345` (as senhas podem ser trocadas com `SEED_ADMIN_PASSWORD` e `SEED_ANA_PASSWORD`). Use essas senhas só em desenvolvimento.

Para testar a edição simultânea, entre como `admin` numa janela e como `ana` numa janela anônima e abra a mesma página.

### Com Docker

```bash
cp .env.example .env
docker compose up --build
```

O banco SQLite é persistido no volume `wikidev_data`. Com `SEED_DEMO=true`, o container roda o seed de demonstração antes de subir.

## Deploy no Render

<a href="https://render.com/deploy?repo=https://github.com/WikiDev-Team/WikiDev"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Publicar no Render"></a>

O repositório tem um blueprint ([`render.yaml`](render.yaml)) que sobe o WikiDev no plano gratuito usando o [`docker/Dockerfile`](docker/Dockerfile):

1. Crie uma conta em [render.com](https://render.com) e conecte sua conta do GitHub. Para publicar a sua própria cópia, faça antes um fork deste repositório.
2. No painel do Render, clique em **New > Blueprint** e escolha o repositório (o botão acima faz o mesmo).
3. Confira o serviço `wikidev` que o blueprint lista e clique em **Apply**. O primeiro build leva alguns minutos.
4. Quando terminar, o site fica em `https://<nome-do-serviço>.onrender.com`. O health check usa `GET /health`.
5. Para entrar como `admin` ou `ana`, pegue as senhas geradas em **Environment** no painel do serviço (`SEED_ADMIN_PASSWORD` e `SEED_ANA_PASSWORD`), ou crie uma conta nova pela tela de cadastro.

Com `autoDeploy: true`, cada push na branch configurada gera um novo deploy. O endereço público é lido de `RENDER_EXTERNAL_URL`, que o Render define sozinho, então os links de redefinição de senha já saem certos. Para um domínio próprio, defina `APP_BASE_URL`.

Variáveis que o blueprint configura:

| Variável | Valor | Efeito |
|---|---|---|
| `APP_ENV` | `production` | Cookies `Secure` e login de desenvolvimento bloqueado. |
| `DATABASE_URL` | `sqlite:////data/wikidev.db` | Banco SQLite dentro do container. |
| `SEED_DEMO` | `true` | Cria as páginas de demonstração a cada início. |
| `DEMO_MODE` | `true` | Mostra no login um aviso de que é uma demonstração e convida a criar uma conta. |
| `SEED_ADMIN_PASSWORD`, `SEED_ANA_PASSWORD` | gerado pelo Render | Senhas aleatórias para as contas do seed, para que ninguém de fora entre como `admin` ou `ana` com as senhas do repositório. |
| `MAIL_MODE` | `console` | E-mails de recuperação de senha vão para o log. Para enviar de verdade, use `smtp` (veja [Recuperação de senha](#recuperação-de-senha)). |

No plano gratuito o disco é temporário e o serviço dorme depois de 15 minutos sem acesso. A cada reinício o banco volta ao conteúdo de demonstração, o que é bom para uma vitrine pública, e a primeira visita depois de dormir demora uns 30 segundos. Para guardar dados de verdade, use um plano com disco persistente montado em `/data` e desligue `SEED_DEMO` e `DEMO_MODE`. A edição simultânea guarda a presença em memória, então mantenha uma única instância.

## Funcionalidades

- Cadastro, login, logout e sessões por cookie `HttpOnly`.
- Recuperação de senha por e-mail com token aleatório, armazenado somente como hash, expiração e uso único.
- Páginas compostas por blocos de texto em Markdown (títulos, listas, links, tabelas) e blocos de código com destaque de sintaxe e botão de copiar.
- Link próprio para cada página (`/p/<id>`) e pasta (`/pastas/<id>`), com histórico do navegador, botão "Copiar link" e retorno ao link depois do login.
- Página inicial com favoritas, vistas recentemente e mais vistas, seguida de "Todas as páginas" com filtros (minhas, de amigos, de outras pessoas, por tag ou texto), ordenação (recentes, alfabética, mais editadas, mais vistas) e "Mostrar mais" para listas longas. Os filtros ficam na URL (`/dashboard?owner=friends&tag=python`).
- Barra lateral em árvore: pastas recolhíveis com as páginas dentro, a pasta atual já aberta, páginas carregadas sob demanda ao expandir e estado das pastas lembrado no navegador. Estrela para favoritar páginas.
- Breadcrumbs com o caminho completo de pastas em páginas, pastas e histórico.
- Tags informadas por nome, criadas automaticamente e exibidas na página, com página própria por tag (`/t/<tag>`) e lista de tags na barra lateral.
- Histórico de versões de cada página (`/p/<id>/historico`), com diff por bloco e restauração. Edições seguidas da mesma pessoa em até 5 minutos viram uma só versão.
- Edição simultânea (`app/collab.py`): cada aba manda um sinal a cada 4 s com a versão dos blocos que tem na tela; a resposta mostra quem mais está na página e troca só os blocos que outras pessoas criaram, alteraram ou excluíram. Ao salvar um bloco que mudou desde que foi aberto, as alterações são combinadas por mescla de três vias; se as duas pessoas mexeram nas mesmas linhas, nada é sobrescrito e o formulário volta com marcadores de conflito. A presença fica em memória, então vale para um processo do uvicorn (o padrão do projeto).
- Links entre páginas com `[[Título]]` ou `[[Título|texto]]` e seção "Citada em" com as páginas que apontam para a atual. Só páginas visíveis para o leitor são resolvidas.
- Busca rápida com Ctrl+K (ou Cmd+K) por título, conteúdo dos blocos, pastas, tags e pessoas.
- Botão "Executar" nos blocos de Python, usando Pyodide no navegador. O código roda num Web Worker dentro de um iframe com sandbox (origem opaca, sem acesso a cookies ou ao DOM) e é interrompido após 10 s.
- Pastas hierárquicas sem possibilidade de ciclos.
- Criação de página dentro de pasta e associação ou remoção de páginas existentes.
- Solicitações de amizade, perfis públicos e remoção de amizade.
- Páginas e pastas privadas, públicas, para amigos ou compartilhadas com amigos específicos.
- Permissões separadas de visualização e edição, com revogação dos compartilhamentos diretos ao remover uma amizade.
- Comentários em páginas e blocos.
- Fórum de discussões com as interações mais recentes visíveis.
- Autorização no backend para páginas, pastas, blocos, comentários e exemplos.
- Busca global que respeita as mesmas regras de privacidade.
- Perfis e listagens públicas sem exposição do e-mail.
- Testes automatizados, cobertura e workflow de integração contínua.
- Docker, blueprint do Render, modo de demonstração, seed e smoke test.

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
static/                # CSS (style.css + ui.css), JS, imagens e vendor/ (htmx, highlight.js)
tests/                 # testes funcionais, segurança e CRUD
scripts/               # seed e smoke test
metrics/               # resultados e análise das métricas de qualidade
```

### Visibilidade e estado

O estado da página (`draft`, `published` ou `archived`) é independente da visibilidade (`private`, `friends`, `public` ou `custom`). O autor sempre possui acesso. Páginas em pastas também obedecem à privacidade da pasta e de todos os seus ancestrais: uma pasta filha pública não contorna uma pasta pai privada.

Para visibilidade `custom`, apenas amizades aceitas podem receber acesso direto. Uma pessoa marcada como editora também recebe visualização. Somente o autor pode excluir a página ou alterar seus compartilhamentos.

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

## Métricas de qualidade

O projeto acompanha SLOC, Índice de Manutenibilidade, Complexidade Ciclomática e métricas de Halstead. Consulte [`metrics/data/METRICS.md`](metrics/data/METRICS.md) para a análise dos resultados.

## Endpoints principais

| Área | Rotas |
|---|---|
| Autenticação | `POST /register`, `POST /login`, `POST /logout` |
| Recuperação | `GET/POST /forgot-password`, `GET/POST /reset-password` |
| Páginas | `/pages/`, `/pages/{id}`, `/pages/{id}/blocks-editor` |
| Pastas | `/folders/`, `/folders/{id}/pages`, `/folders/{id}/pages/{page_id}` |
| Amizades | `/friends`, `/friendships/request/{user_id}`, `/friendships/{id}/...` |
| Comentários | `/comments/`, `/comments/{id}` |
| Discussões | `/comments/pages/{page_id}/discussion`, `/comments/blocks/{block_id}/discussion` |
| Fórum | `GET /forum` |
| Perfis | `GET /profile/{user_id}` |
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

## In English

WikiDev is a collaborative wiki for programmers. Pages are made of Markdown text blocks and code blocks, organized in folders and tags, linked with `[[Page title]]` and shared as private, friends-only, public or with specific friends. Python blocks run in the browser through Pyodide in a sandboxed iframe (including matplotlib charts), several people can edit the same page at once with three-way merging, and every page keeps a version history with diffs. Built with FastAPI, SQLModel, Jinja2 and HTMX. The interface is in Portuguese.

Run it locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m scripts.seed_demo        # demo content, login admin / admin123
uvicorn app.main:app --reload      # http://127.0.0.1:8000
```

Deploy it on Render with the button above or **New > Blueprint** pointing at this repository: [`render.yaml`](render.yaml) builds the Docker image on the free plan, seeds demo content on every start and generates random passwords for the demo accounts (see **Environment** in the service dashboard).

## Licença

Distribuído sob a licença MIT. Consulte [`LICENSE`](LICENSE).
