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
- redefinição de senha expirada e de uso único;
- POST, PUT, PATCH e DELETE vindos de outro site são recusados pela checagem de `Origin`/`Referer` (`app/web_security.py`);
- cabeçalhos `Content-Security-Policy` (`frame-ancestors`, `connect-src`), `X-Frame-Options`, `X-Content-Type-Options` e `Referrer-Policy`;
- limite em memória de tentativas de login por usuário e de e-mails de recuperação por endereço;
- Python do navegador roda num iframe `sandbox="allow-scripts"` com origem opaca, e só pode se conectar ao próprio site e ao CDN do Pyodide;
- só o autor de uma página a move entre pastas; tags e linguagens usadas por páginas de outras pessoas não podem ser renomeadas.

## Limitações conhecidas

- Os limites de tentativas ficam em memória: valem para um único processo do uvicorn, que é como o projeto roda. Com vários processos, use um armazenamento compartilhado (Redis, por exemplo).
- A sessão no servidor não expira sozinha: o cookie dura 7 dias, mas o token só é invalidado no logout, num novo login ou na troca de senha.
- Não há papel de administrador; a manutenção de tags e linguagens compartilhadas é limitada pelas regras acima.
- Ainda não há `script-src` na CSP, porque alguns templates usam `onclick` inline.
