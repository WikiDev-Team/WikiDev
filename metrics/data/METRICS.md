# Análise das métricas do WikiDev

Ao longo do projeto, algumas métricas foram utilizadas para medir a qualidade do código, entre elas, utilizamos a SLOC, MI, COmplexidade Ciclomática e Halstead.

## Medição de métricas

Para termos um gráfico interessante e bem representativo, medimos essas métricas em momentos chave do desenvolvimento, após commits que mudaram um número significativo de linhas, ou que implementaram funcionalidades cruciais.

Esses pontos cruciais escolhidos foram os commits:

- Backend inicial (77660ff)
- Autenticação e HTMX (e58d418)
- Integração do Backend com Frontend inicial (36c1161)
- Criação das Pastas (07d69f1)
- Criação dos Blocos (c478768)
- Criação das Amizades (138ee86)
- Final* (c6e4f7e)

*obs: Alguns novos commits foram adicionados após isso, mas com mudanças pequenas


## Análise do gráfico

No gráfico, podemos ver que o SLOC cresce em degraus alinhados aos marcos de funcionalidade: +570 linhas em Blocos (c478768), com a introdução do editor de blocos e dos comentários por bloco, e +740 em Amizades (138ee86), com a camada de amizades e permissões. O total triplica no período, refletindo o crescimento do código em lógica.

A complexidade ciclomática também cresce ao implementar as amizades, mas ainda assim, ela continua bem baixa, demonstrando uma boa modularização e baixo acúmulo de tarefas para cada função

O MI médio recuou de 71 para 63 no período. A queda é consistente com o crescimento do código: o termo dominante da fórmula do MI é o logaritmo do SLOC, de modo que triplicar o tamanho reduz o índice mesmo sem degradação de qualidade. O pior arquivo do sistema, por sua vez, subiu de 30 para 34, e tanto a média quanto o pior caso permaneceram em rank A durante toda a evolução.

A métrica que exigiu uma análise mais profunda é o esforço de Halstead por função, que cresceu enormemente entre o commit dos blocos e o commit das amizades. Após verificação do que foi adicionado nesses commits, foi observado que 86% desse acréscimo se concentra em dois módulos criados nesse commit: permissions.py (+4.412 em esforço) e friendships.py (+3.421 em esforço).
No mesmo intervalo, a complexidade ciclomática média sobe apenas de 1,77 para 2,03, e o permissions.py distribui 157 SLOC em 15 funções, dentre as quais, a pior complexidade máxima é de 6, sendo treze delas em rank A, e as outras duas rank B.
Isso indica que o crescimento veio da introdução de muitas funções pequenas e de vocabulário extenso (identificadores como requester_id, addressee_id, shared_page_ids, allowed_editors), e não do aprofundamento do fluxo de controle.
Como o esforço de Halstead depende do volume de operadores e operandos distintos, a centralização das regras de autorização em um módulo dedicado eleva a métrica ao mesmo tempo em que reduz a duplicação de checagens nas rotas, o pages.py, por exemplo, teve 200 linhas alteradas com remoções significativas ao migrar para as funções require_page_view e require_page_edit.
