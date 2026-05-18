# Como Contribuir com o WikiDev

Esse guia explica como o time deve trabalhar com o repositório.

---

## 1. Configurando o projeto localmente

**Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/wikidev.git
cd wikidev
```

**Configure as variáveis de ambiente:**
```bash
cp .env.example .env
```
Abra o `.env` e preencha com os valores corretos. Nunca commite esse arquivo.

**Instale as dependências do backend:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**Instale as dependências do frontend:**
```bash
npm install
```

---

## 2. Fluxo de trabalho

Ninguém trabalha diretamente na `main` ou `develop`. O fluxo é sempre:

```
main (produção)
  └── develop (integração)
        └── feature/sua-feature (onde você trabalha)
```

**Antes de começar qualquer tarefa:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/nome-da-feature
```

**Exemplos de nomes de branch:**
- `feature/pagina-login`
- `feature/listagem-artigos`
- `fix/erro-formulario`
- `hotfix/crash-home`

---

## 3. Fazendo commits

Use sempre o comando interativo no lugar do `git commit`:

```bash
git add .
npm run commit
```

O padrão de commit é:
```
tipo(escopo): descrição curta em minúsculo
```

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `style` | Mudança visual, CSS |
| `refactor` | Reorganização de código |
| `docs` | README, comentários |
| `chore` | Configuração, dependências |

---

## 4. Abrindo um Pull Request

Quando terminar sua feature:

```bash
git push origin feature/nome-da-feature
```

O GitHub vai exibir um botão **"Compare & pull request"** — clique nele e preencha:

- O que foi feito
- Como testar
- Marque o checklist antes de pedir review

**Regras:**
- Todo PR precisa de pelo menos **1 aprovação** antes de mergear
- Nunca faça merge do seu próprio PR sem revisão

---

## 5. Revisando um PR

Na aba **"Files changed"** do PR, clique no **"+"** ao lado de qualquer linha para comentar.

- Use **Approve** se estiver tudo certo ✅
- Use **Request changes** se precisar de correções 🔴
- Use o prefixo `nit:` para sugestões pequenas que não bloqueiam o merge

---

## 6. Regras gerais

- Nunca commite o arquivo `.env`
- Nunca dê push direto na `main` ou `develop`
- Branches devem ser deletadas após o merge
- Dúvidas? Abre uma Issue ou chama no grupo
