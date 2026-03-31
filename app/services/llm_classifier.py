import json
import logging
import os

from openai import OpenAI
from pydantic import ValidationError

from app.schemas.llm_output import ResultadoLLM

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um organizador de transcripts técnicos de vídeo.

Sua tarefa é classificar o conteúdo de um novo transcript em tópicos e subtópicos, usando a taxonomia existente como referência quando o conteúdo for realmente compatível.

Objetivo:
Criar uma taxonomia precisa e fiel ao conteúdo. Reutilize tópicos e subtópicos existentes SOMENTE quando o conteúdo do transcript tratar genuinamente do mesmo assunto. Crie novos tópicos e subtópicos sem hesitar quando o conteúdo for diferente.

Regras:
- Analise o conteúdo real do transcript antes de olhar a taxonomia existente.
- Reutilize um tópico existente APENAS se o conteúdo tratar claramente do mesmo tema.
- Reutilize um subtópico existente APENAS se a ação descrita pertencer genuinamente àquele subtópico.
- Se o transcript fala sobre um assunto novo (ex: puxadores, granito, furação), CRIE um tópico novo para ele. Não force em tópicos existentes.
- Não encaixe conteúdo sobre "puxadores" em "rodízios", nem "furação" em "acessórios", nem temas que não tenham relação direta.
- Normalize apenas sinônimos verdadeiros (enviar/subir/upload), não conceitos diferentes.
- Cada item deve representar uma ação concreta e útil para consulta futura.
- Ignore falas de enchimento, repetições e comentários sem valor operacional.
- Não invente conteúdo que não esteja no transcript.
- O nome do tópico deve refletir o assunto principal tratado no transcript.

Considere equivalentes APENAS quando forem sinônimos reais:
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
    except Exception as e:
        print(f"[LLM] ERROR: OpenAI API call failed: {e}")
        logger.exception("OpenAI API call failed")
        return None

    raw_content = response.choices[0].message.content
    print(f"[LLM] Response received: {len(raw_content)} chars")

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        print(f"[LLM] ERROR: Invalid JSON: {raw_content[:300]}")
        logger.error("LLM returned invalid JSON: %s", raw_content[:200])
        return None

    try:
        result = ResultadoLLM(**data)
        print(f"[LLM] Validation OK: {len(result.itens)} items")
        return result
    except ValidationError as exc:
        print(f"[LLM] ERROR: Pydantic validation failed: {exc}")
        logger.error("LLM output failed validation: %s", exc)
        return None
