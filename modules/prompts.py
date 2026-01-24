# modules/prompts.py

PROMPT_ANALISE_GANCHO = """
Analise o início deste vídeo:
"{texto_transcrito}"

Identifique:
1. O Gancho Verbal (Frase exata do início).

Retorne JSON: {{ "ganchos_verbais": "..." }}
"""