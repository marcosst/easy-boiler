import json
import logging
import os

from openai import OpenAI
from pydantic import ValidationError

from app.schemas.llm_output import ResultadoLLM

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um organizador de transcripts técnicos de vídeo.

Sua tarefa é classificar o conteúdo de um novo transcript usando uma taxonomia já existente de tópicos e subtópicos.

Objetivo:
Reaproveitar ao máximo os tópicos e subtópicos existentes e criar novos apenas quando realmente necessário.

Regras:
- Use a taxonomia existente como referência principal.
- Antes de criar um novo tópico, tente encaixar o conteúdo em um tópico já existente.
- Antes de criar um novo subtópico, tente encaixar o conteúdo em um subtópico já existente dentro do tópico escolhido.
- Reutilize nomes existentes sempre que houver equivalência semântica.
- Não crie novos nomes apenas por variação de vocabulário.
- Normalize sinônimos para os rótulos já existentes.
- Só crie novo tópico ou subtópico quando houver diferença real de função, etapa ou conceito.
- Evite duplicação semântica.
- Cada item deve representar uma ação concreta e útil para consulta futura.
- Ignore falas de enchimento, repetições e comentários sem valor operacional.
- Se houver dúvida entre reutilizar ou criar novo, prefira reutilizar.
- Não invente conteúdo que não esteja no transcript.

Considere equivalentes, quando fizer sentido:
- enviar / subir / fazer upload
- componente / módulo / item
- atualizar / recarregar / sincronizar
- aplicar / inserir / usar
- configurar / definir / ajustar
- selecionar / escolher

Retorne apenas JSON válido no formato:

{
  "itens": [
    {
      "topico": "",
      "subtopico": "",
      "acao": "",
      "timestamp": "00:00:00"
    }
  ]
}"""


def _build_messages(taxonomy: dict, transcript: str) -> list[dict]:
    """Build the messages list for the OpenAI API call."""
    if taxonomy.get("topicos"):
        taxonomy_text = json.dumps(taxonomy, ensure_ascii=False, indent=2)
    else:
        taxonomy_text = "Nenhuma taxonomia existente ainda."

    user_content = f"Taxonomia existente:\n{taxonomy_text}\n\nTranscript:\n{transcript}"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _call_openai(messages: list[dict]):
    """Make the actual OpenAI API call. Separated for easy mocking."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client.chat.completions.create(
        model="gpt-5.4",
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )


def classify_transcript(taxonomy: dict, transcript: str) -> ResultadoLLM | None:
    """Classify a transcript using the LLM. Returns validated result or None on failure."""
    messages = _build_messages(taxonomy, transcript)

    try:
        response = _call_openai(messages)
    except Exception:
        logger.exception("OpenAI API call failed")
        return None

    raw_content = response.choices[0].message.content

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON: %s", raw_content[:200])
        return None

    try:
        return ResultadoLLM(**data)
    except ValidationError as exc:
        logger.error("LLM output failed validation: %s", exc)
        return None
