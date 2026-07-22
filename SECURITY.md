# Política de segurança

## Versões suportadas

Enquanto o projeto estiver em desenvolvimento acadêmico, somente a branch `develop` e a versão mais recente recebem correções de segurança.

## Como reportar

Não publique credenciais, tokens, dados pessoais ou passos de exploração em uma issue pública. Envie o relato de forma privada aos mantenedores do repositório, incluindo:

- rota ou componente afetado;
- impacto observado;
- passos mínimos para reproduzir;
- sugestão de correção, quando houver.

## Controles atuais

- bcrypt para senha;
- hash SHA-256 para tokens de sessão e redefinição;
- cookies `HttpOnly`, `SameSite=Lax` e `Secure` em produção;
- autorização central para pastas e páginas;
- autoria definida pelo servidor;
- respostas públicas de usuário sem e-mail;
- redefinição de senha expirada e de uso único.

## Limitações conhecidas

Antes de exposição pública em produção, implemente proteção CSRF explícita, rate limiting distribuído para login/recuperação, migrações Alembic e uma política de papéis administrativos para manutenção de tags e linguagens.
