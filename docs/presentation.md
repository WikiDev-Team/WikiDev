---
marp: true
theme: default
paginate: true
---

# WikiDev
## Organização, colaboração e segurança para conhecimento de programação

**Entrega:** estabilização, pastas, recuperação de senha e testes

---

# Problema

- Anotações técnicas ficam dispersas.
- Páginas e pastas não tinham um fluxo completo.
- Permissões existiam mais na interface do que no backend.
- Não havia recuperação de senha nem suíte confiável de regressão.

---

# Solução

- Wiki em páginas compostas por blocos.
- Pastas hierárquicas públicas ou privadas.
- Busca global respeitando autorização.
- Autenticação segura e recuperação por e-mail.
- Automação de testes em cada pull request.

---

# Demonstração 1 — Pastas

1. Criar pasta privada.
2. Criar página diretamente dentro dela.
3. Anexar página existente.
4. Criar subpasta.
5. Tornar a pasta pública e testar com outro usuário.

---

# Demonstração 2 — Conteúdo

- Adicionar bloco de texto.
- Alterar tamanho da fonte.
- Adicionar bloco de código.
- Publicar a página.
- Abrir em modo somente leitura com outro usuário.

---

# Recuperação de senha

- Resposta não revela se o e-mail existe.
- Token aleatório é enviado por e-mail.
- Banco guarda apenas SHA-256 do token.
- Link expira e funciona uma única vez.
- Todas as sessões anteriores são revogadas.

---

# Segurança corrigida

- Autoria controlada pelo servidor.
- Edição e exclusão exigem propriedade.
- E-mail removido de respostas públicas.
- Busca não atravessa pasta privada.
- Login de desenvolvimento desativado por padrão.

---

# Qualidade

- Pytest com banco SQLite isolado.
- Casos de autenticação, privacidade e spoofing.
- GitHub Actions em Python 3.11 e 3.12.
- Coverage como porta de qualidade.
- Seed e smoke test para demonstração rápida.

---

# Issues atendidas

**Completas:** #32, #31, #25, #23, #22, #21, #15, #14, #13, #11 e #7.

**Parcial:** #10 (melhoria ampla de UI) e #24 (roteiro exportável).

**Integração:** preservar amizade da `develop` e fórum/comentários do PR #35.

---

# Próximos passos

- Resolver conflitos com o PR #35 usando `docs/merge-pr35.md`.
- Adotar Alembic para migrações versionadas.
- Acrescentar papéis administrativos para tags e linguagens.
- Executar teste de usabilidade e acessibilidade.

---

# Obrigado

## Perguntas e demonstração livre
