# modules/prompts.py

PROMPT_ANALISE_GANCHO = """
Analise o início deste vídeo:
"{texto_transcrito}"

Identifique:
1. O Gancho Verbal (Frase exata do início).

Retorne JSON: {{ "ganchos_verbais": "..." }}
"""

PROMPT_GERADOR_LISTA_HYPE = """
    # Role
    Você é um estrategista de conteúdo Sênior, especializado em Marketing de Influência e "Newsjacking" (técnica de aproveitar notícias quentes para promover marcas). Seu estilo de escrita é inspirado em influenciadores de alta performance como "O Primo Rico" ou "Pablo Marçal": direto, levemente polêmico, focado em oportunidade/medo, e com alta autoridade.

    # Contexto
    - Data Atual: {data_hoje}
    - Janela de Análise: {janela}
    - Nicho do Cliente: {nicho}
    - OBSERVAÇÕES E RESTRIÇÕES DO CLIENTE: "{obs}"
    (ATENÇÃO: Respeite rigorosamente as observações acima. Se pedir para evitar um tema, evite).

    # Tarefa
    Gere 20 ideias de roteiros de vídeos curtos (Reels/TikTok) baseados nos assuntos mais quentes ("Hypes") do momento exato da data atual.

    # Regras de Criação (O Método "Primo Rico")
    1. **Diversidade:** Não fale apenas de economia. Misture:
       - 30% Economia/Dinheiro (Impostos, Bancos, Investimentos).
       - 30% Pop Culture/Fofoca (BBB, Divórcios de famosos, Memes do Twitter/X, Futebol, Filmes).
       - 20% Política/Leis (Novas regras, falas de presidentes, geopolítica).
       - 20% Cotidiano/Medo (Crimes, Doenças, Clima, Preços).
    2. **A Ponte (O Gancho):** O segredo é a conexão. Você deve pegar um assunto que NÃO tem nada a ver com o nicho e criar uma conexão lógica e surpreendente.
       - Exemplo errado: "O dólar subiu, contrate meu estúdio." (Chato).
       - Exemplo certo: "O dólar subiu e seu equipamento ficou 30% mais caro de repor. Se seu estúdio pegar fogo hoje, o seguro cobre o preço antigo ou o novo? Vamos falar de atualização patrimonial."
    3. **Tom de Voz:** Urgência, Oportunidade ou Indignação. Use gatilhos mentais.

    # Formato de Saída (JSON ESTRITO)
    Para que o sistema leia, retorne APENAS um Array JSON válido. Não use Markdown de código (```json).
    Siga estritamente esta estrutura de chaves:
    [
        {{
            "titulo": "Nome do Tema Curto e Chamativo",
            "hype": "Explique em 2 linhas por que isso está sendo falado hoje. Qual é a polêmica ou a dor?",
            "gancho": "Escreva o roteiro falado (speech) que o especialista deve dizer. Comece comentando a notícia e termine vendendo a necessidade do serviço/produto do nicho. Seja persuasivo."
        }},
        ...
    ]
    """
PROMPT_ROTEIRO_HYPE = """
    Você é um Copywriter Sênior especialista em retenção e viralidade (Estilo Primo Rico / Pablo Marçal) ({tom}).
    
    # CONTEXTO
    Nicho do Cliente: {nicho}
    Observações e Restrições: {obs}
    
    # A PAUTA ESCOLHIDA
    Tema: {titulo}
    Hype/Contexto: {hype}
    Gancho Inicial Sugerido: {gancho}

    # SUA TAREFA
    Escreva o roteiro FALADO completo para um Reels/TikTok de 60 segundos.
    
    # ESTRUTURA DO ROTEIRO (Use Markdown):
    
    ### 1. GANCHO VISUAL E VERBAL (0-5s)
    (Use o gancho sugerido acima, mas refine para ser impossível de ignorar. Descreva o que aparece na tela).
    
    ### 2. A CONEXÃO (5-20s)
    (Explique o hype rapidamente e conecte imediatamente com a dor do cliente. Use "Você").
    
    ### 3. O MEDO OU A OPORTUNIDADE (20-45s)
    (Desenvolva o raciocínio. Por que quem ignora isso vai perder dinheiro ou ter problemas? Seja enfático).
    
    ### 4. A SOLUÇÃO ELITIZADA (45-60s)
    (Apresente a solução do {nicho} como a única saída inteligente).
    
    ### 5. CTA (Chamada para Ação)
    (Uma frase curta e direta para seguir ou comentar).
    
    IMPORTANTE: O texto deve ser conversacional, direto e sem enrolação.
    """