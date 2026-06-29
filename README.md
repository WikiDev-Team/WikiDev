# WikiDev

## O que é o WikiDev

O WikiDev é uma plataforma desenvolvedores organizarem conteúdos sobre linguagens de programação, exemplos de código, páginas de estudo e materiais técnicos.

## Objetivo

O objetivo do projeto é centralizar informações úteis sobre programação em um ambiente organizado, permitindo que usuários criem, editem, visualizem e compartilhem páginas de conteúdo.

## Funcionalidades

- Cadastro de usuários
- Login e logout
- Perfil de usuário
- Criação de páginas
- Edição e exclusão de páginas
- Organização futura por pastas
- Busca de conteúdos
- Sistema futuro de privacidade e amizades

## Tecnologias usadas

- Python
- FastAPI
- SQLModel
- SQLite
- Jinja2
- HTMX
- HTML
- CSS
- JavaScript

## Como rodar o projeto

```bash
git clone https://github.com/WikiDev-Team/WikiDev.git
cd WikiDev
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
