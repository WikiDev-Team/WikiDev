import json
import matplotlib.pyplot as plt
import os

# Commits 
commits = [
    "1_backend",
    "2_auth_htmx",
    "3_integracao",
    "4_folders",
    "5_blocks",
    "6_amizades",
    "7_head"
]

# Rótulos
labels_grafico = [
    "Backend Inicial\n(77660ff)",
    "Auth & HTMX\n(e58d418)" ,
    "Integração\n(36c1161)",
    "Pastas\n(07d69f1)",
    "Blocos\n(c478768)",
    "Amizades\n(138ee86)",
    "Final (Head)\n(c6e4f7e)"
]

valores_mi = []
valores_pior_mi = []

# Lendo os arquivos JSON
for cm in commits:
    arquivo = f"{cm}/mi-{cm}.json"
    
    if os.path.exists(arquivo):
        with open(arquivo, 'r') as f:
            dados = json.load(f)
            
            if dados:
                # Calcula a média do MI de todos os arquivos no commit
                soma_mi = sum(item["mi"] for item in dados.values())
                media_mi = soma_mi / len(dados)
                
                # Encontra o pior (menor) MI entre todos os arquivos
                pior_mi = min(item["mi"] for item in dados.values())

            else:
                media_mi = 0
                pior_mi = 0
                
            valores_mi.append(media_mi)
            valores_pior_mi.append(pior_mi)
    else:
        print(f"Aviso: Arquivo {arquivo} não encontrado.")
        valores_mi.append(None)
        valores_pior_mi.append(None)

# Configurando e gerando o gráfico
plt.figure(figsize=(10, 6))

plt.axhspan(20, 100, color='#2ca02c', alpha=0.07)
plt.axhspan(10, 20, color='#ff7f0e', alpha=0.10)
plt.axhspan(0, 10, color='#d62728', alpha=0.10)
plt.axhline(20, color='gray', linestyle=':', linewidth=1)
plt.axhline(10, color='gray', linestyle=':', linewidth=1)
plt.text(0.02, 21, 'Rank A (manutenível)', fontsize=9, color='gray', transform=plt.gca().get_yaxis_transform())
plt.text(0.02, 11, 'Rank B', fontsize=9, color='gray', transform=plt.gca().get_yaxis_transform())
plt.text(0.02, 3, 'Rank C (crítico)', fontsize=9, color='gray', transform=plt.gca().get_yaxis_transform())

# Linha da média (Azul)
plt.plot(labels_grafico, valores_mi, marker='o', linestyle='-', color='#1f77b4', linewidth=2, markersize=8, label='MI Médio do Sistema')

# Linha do pior caso (Vermelha)
plt.plot(labels_grafico, valores_pior_mi, marker='s', linestyle='-', color='red', linewidth=2, markersize=8, label='Pior MI do Sistema')

# Estilização
plt.title('Evolução do Índice de Manutenibilidade (MI) - WikiDev', fontsize=14, pad=15)
plt.xlabel('Commits', fontsize=12, labelpad=10)
plt.ylabel('MI (0 a 100)', fontsize=12, labelpad=10)
plt.ylim(0, 100) # O MI varia de 0 a 100
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(rotation=45)

# Adicionando a legenda para diferenciar as linhas
plt.legend(loc='center right', fontsize=11)

plt.tight_layout()

# Salvando a imagem
nome_saida = 'evolucao_mi_wikidev.png'
plt.savefig(nome_saida, dpi=300)
print(f"Gráfico gerado com sucesso: {nome_saida}")

# Exibindo na tela
plt.show()
