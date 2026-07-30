import json
import matplotlib.pyplot as plt
import os

checkpoints = [
    "1_backend", "2_auth_htmx", "3_integracao", 
    "4_folders", "5_blocks", "6_amizades", "7_head"
]

labels_grafico = [
    "Backend Inicial\n(77660ff)", "Auth & HTMX\n(e58d418)",
    "Integração\n(36c1161)", "Pastas\n(07d69f1)",
    "Blocos\n(c478768)", "Amizades\n(138ee86)", "Final (Head)\n(c6e4f7e)"
]

valores_sloc = []
valores_cc = []
valores_halstead = []

for cp in checkpoints:
    # 1. Linhas de Código (SLOC) - Arquivos raw-*.json
    arq_raw = f"{cp}/raw-{cp}.json"
    if os.path.exists(arq_raw):
        with open(arq_raw, 'r') as f:
            dados_raw = json.load(f)
            # Soma o SLOC de todos os arquivos
            sloc_total = sum(arq["sloc"] for arq in dados_raw.values())
            valores_sloc.append(sloc_total)
    else:
        valores_sloc.append(None)

    # 2. Complexidade Ciclomática Média (CC) - Arquivos cc-*.json
    arq_cc = f"{cp}/cc-{cp}.json"
    if os.path.exists(arq_cc):
        with open(arq_cc, 'r') as f:
            dados_cc = json.load(f)
            cc_total = 0
            num_funcs = 0
            for funcoes in dados_cc.values():
                for func in funcoes:
                    cc_total += func.get("complexity", 1)
                    num_funcs += 1
            cc_media = cc_total / num_funcs if num_funcs > 0 else 0
            valores_cc.append(cc_media)
    else:
        valores_cc.append(None)

    # 3. Esforço de Halstead - Arquivos hal-*.json
    arq_hal = f"{cp}/hal-{cp}.json"
    if os.path.exists(arq_hal):
        with open(arq_hal, 'r') as f:
            dados_hal = json.load(f)
            esforco_total = sum(arq["total"]["effort"] for arq in dados_hal.values())
            valores_halstead.append(esforco_total)
    else:
        valores_halstead.append(None)

# Gerando a figura com 3 subgráficos (1 linha, 3 colunas)
fig, axs = plt.subplots(1, 3, figsize=(18, 6))

# Gráfico 1: SLOC
axs[0].plot(labels_grafico, valores_sloc, marker='s', color='#2ca02c', linewidth=2)
axs[0].set_title('Evolução do Tamanho (Total SLOC)')
axs[0].set_ylabel('Linhas de Código Úteis')
axs[0].grid(True, linestyle='--', alpha=0.7)
axs[0].tick_params(axis='x', rotation=45)

# Gráfico 2: Complexidade Ciclomática
axs[1].plot(labels_grafico, valores_cc, marker='^', color='#d62728', linewidth=2)
axs[1].set_title('Complexidade Ciclomática Média por Função')
axs[1].set_ylabel('Média de CC')
axs[1].grid(True, linestyle='--', alpha=0.7)
axs[1].tick_params(axis='x', rotation=45)

# Gráfico 3: Esforço de Halstead
axs[2].plot(labels_grafico, valores_halstead, marker='D', color='#9467bd', linewidth=2)
axs[2].set_title('Esforço Total de Halstead')
axs[2].set_ylabel('Esforço Cognitivo')
axs[2].grid(True, linestyle='--', alpha=0.7)
axs[2].tick_params(axis='x', rotation=45)

plt.tight_layout()
nome_saida = 'evolucao_metricas_completas_wikidev.png'
plt.savefig(nome_saida, dpi=300)
print(f"\nGráficos gerados com sucesso: {nome_saida}")
plt.show()