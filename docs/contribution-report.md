# Relatório da contribuição integrada

## Escopo entregue

### Issues que podem ser fechadas

- **#32 — Recuperação de senha:** fluxo completo por e-mail, token com hash, expiração, uso único e revogação de sessão.
- **#31 — Testes automatizados:** fixtures compartilhadas, 19 testes funcionais/de segurança, cobertura e GitHub Actions.
- **#25 — Limpeza de bugs:** correções no seed, smoke test, blocos, remoção de páginas/pastas, logout, exclusões e rotas inseguras.
- **#23 — Revisão geral:** política de permissões central, schemas públicos, configuração por ambiente e revisão das rotas.
- **#22 — Licença:** MIT adicionada ao repositório.
- **#21 — README:** instalação, arquitetura, segurança, SMTP, testes, Docker e endpoints documentados.
- **#15 — Criar página na pasta:** formulário e endpoint API.
- **#14 — Ver página no contexto da pasta:** painel de pasta com páginas e subpastas.
- **#13 — Adicionar página existente:** anexar e remover via interface e API.
- **#11 — Criação de páginas e pastas:** fluxo integrado e slugs únicos.
- **#8 — Amizades:** infraestrutura da `develop` preservada e integrada às regras de visibilidade, edição e revogação de compartilhamentos.
- **#7 — Pastas e privacidade:** hierarquia, prevenção de ciclos, `private/public` e autorização no backend.

### Issues atendidas parcialmente

- **#10 — Interface:** dashboard, sidebar, amizade, busca, formulários, estados vazios e responsividade foram integrados; uma revisão visual final do time continua recomendada.
- **#24 — Apresentação:** roteiro em `docs/presentation.md`, compatível com Marp. O time ainda deve adaptar a identidade visual e exportar a versão final.

### Trabalho ainda externo

- **PR #35 — Fórum, atividades e comentários por bloco:** não está contido nesta resolução. Ao mesclá-lo, preserve a autorização central e os filtros de visibilidade descritos em `docs/merge-pr35.md`.

## Correções de segurança relevantes

1. Edição e exclusão de páginas, pastas, blocos, comentários e exemplos validam o usuário autenticado.
2. `author_id` enviado pelo cliente não é confiado.
3. Listagens públicas de usuários não incluem e-mail.
4. Busca, dashboard, perfis e compartilhamento obedecem à mesma política de visibilidade.
5. Página pública não ultrapassa uma pasta privada ou um ancestral privado.
6. A rota de login de desenvolvimento só funciona quando explicitamente ativada e nunca em produção.
7. Sessões são rotacionadas no login, armazenadas como hash e revogadas no logout e na redefinição de senha.
8. Remover uma amizade revoga compartilhamentos diretos entre as duas pessoas.

## Validação recomendada no PR

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
