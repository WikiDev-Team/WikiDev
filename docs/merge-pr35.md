# Integração com o PR #35

O PR #35 adiciona comentários em páginas e blocos, fórum de atividades e testes. Como ele altera parte dos mesmos módulos, faça o merge sobre a `develop` atual e resolva os conflitos por responsabilidade, não escolhendo um lado inteiro.

## Preserve do PR #35

- Modelos e relacionamentos específicos de comentários por bloco.
- Fórum, atividades recentes, respostas, edição e exclusão na interface.
- Templates e estilos próprios dessas funcionalidades.
- Testes de fórum/comentários que não duplicam os cenários abaixo.

## Preserve desta contribuição

- Recuperação de senha e módulos `config.py`, `mailer.py` e `security.py`.
- `permissions.py` como fonte única de autorização.
- Pastas, privacidade e fluxos de associação de páginas.
- Schemas públicos de usuário sem e-mail.
- Autoria de comentários definida por `current_user.id`.
- Validação de que comentário pai pertence à mesma página/bloco.
- Busca filtrada por `accessible_pages`.
- CI, fixtures compartilhadas, Docker, README e licença.

## Arquivos com maior chance de conflito

- `app/models.py`
- `app/main.py`
- `app/routers/comments.py`
- `templates/main.html`
- `static/style.css`
- `tests/`

## Testes mínimos após o merge

1. Um usuário não pode editar comentário de outro.
2. `author_id` enviado no JSON não altera o autor real.
3. Comentários de páginas privadas não aparecem no fórum ou em atividades para usuários sem acesso.
4. Comentário por bloco só pode apontar para bloco pertencente à página informada.
5. Excluir página remove ou trata comentários de página e bloco sem deixar referências órfãs.
6. Busca, dashboard e fórum aplicam a mesma política de visibilidade.
