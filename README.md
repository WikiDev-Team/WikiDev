# WikiDev

Plataforma colaborativa de documentação para desenvolvedores, construída com FastAPI, SQLModel, Jinja2 e HTMX.

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A aplicação fica disponível em `http://127.0.0.1:8000`.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Amizades e compartilhamento

O WikiDev oferece:

- solicitações de amizade com aceitar, recusar e cancelar;
- remoção de amizade com revogação dos compartilhamentos diretos;
- perfis públicos sem exposição do e-mail;
- páginas privadas, públicas, visíveis para amigos ou para amigos selecionados;
- permissões separadas de visualização e edição;
- validação de acesso no backend para páginas, blocos, comentários, exemplos e pastas.

O estado da página (`draft`, `published` ou `archived`) é independente de sua visibilidade (`private`, `friends`, `public` ou `custom`).
