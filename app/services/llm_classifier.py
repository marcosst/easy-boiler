import json
import logging
import os

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.schemas.llm_output import ResultadoLLM

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um assistente especializado em análise de vídeos de treinamento de software (CAD, SketchUp, plugins, etc.).

Sua tarefa é extrair uma taxonomia hierárquica estruturada da transcrição.

## Objetivo

Organizar o conteúdo usando a seguinte estrutura obrigatória:

- Tópico = ENTIDADE do sistema (objeto principal)
- Subtópico = AÇÃO ou contexto sobre essa entidade
- Detalhe = ação específica, explicação ou comportamento observado

A prioridade é refletir como um usuário pensaria ao aprender o software.

---

## Entrada

Você receberá:

1. Transcrição com timestamps
2. Taxonomia existente

---

## REGRA PRINCIPAL (CRÍTICA)

Sempre priorize esta estrutura:

ENTIDADE → AÇÃO → DETALHE

---

## 1. Identificação do tópico (ENTIDADE)

O tópico deve ser uma entidade clara do sistema.

Exemplos de entidades válidas:
- Paredes
- Portas
- Puxadores
- Componentes
- Materiais
- Projeto
- Biblioteca

Exemplos inválidos de tópico:
- Criar
- Editar
- Ajustar
- Configurar
- Exemplo
- Dica

### Regra forte:

Se o vídeo gira em torno de um objeto específico (ex: "Puxadores"), esse deve ser o tópico principal.

---

## 2. Prioridade do título do vídeo

O título do vídeo é uma fonte primária de verdade.

Regras:
- Se o título contém uma entidade clara → use como tópico
- Só ignore o título se a transcrição contradizer claramente

Exemplo:
"03 - Puxador Cava e Usinado"
→ Tópico deve ser: Puxadores

---

## 3. Subtópicos (AÇÕES)

Subtópicos são ações ou contextos aplicados à entidade.

Exemplos:
- Inserção
- Edição
- Configuração
- Tipos
- Ajustes
- Posicionamento

Regra:
Ações nunca devem virar tópicos.

---

## 4. Detalhes

Cada detalhe deve ser:

- atômico
- autocontido
- com timestamp

Exemplos:
- Inserir puxador cava usando biblioteca
- Ajustar profundidade do puxador usinado
- Alterar posição do puxador na porta

---

## 5. Deduplicação com taxonomia existente

Reutilize apenas se for o MESMO nível:

- entidade com entidade
- ação com ação

Nunca faça:
- usar subtópico existente para evitar criar um tópico novo

Regra crítica:
Se o vídeo trata de uma entidade nova → crie um tópico novo

---

## 6. Limite de tópicos

- Normal: 1 a 2 tópicos por vídeo
- Máximo: 3
- Se passar disso, provavelmente está errado

---

## 7. Proibição de erro comum

NUNCA faça isso:

Errado:
Tópico: Inserção  
Tópico: Edição  
Tópico: Configuração  

Correto:
Tópico: Puxadores  
  Subtópico: Inserção  
  Subtópico: Edição  
  Subtópico: Configuração  

---

## 8. Validação obrigatória (ANTES de responder)

Pergunte mentalmente:

1. Os tópicos são objetos do sistema?
2. Se eu mostrar só os tópicos, dá pra entender o tema do vídeo?
3. Existe um objeto óbvio (ex: puxador) que eu ignorei?

Se sim → corrija antes de responder

---

## Formato de saída

Responda exclusivamente com JSON:

{
  "itens": [
    {
      "topico": "Nome da entidade",
      "subtopico": "Nome da ação",
      "detalhe": "Descrição clara e autocontida",
      "timestamp": "HH:MM:SS"
    }
  ]
}

---

## Taxonomia existente

{{TAXONOMIA_EXISTENTE}}

---

## Transcrição

{{TRANSCRICAO}}
"""


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


async def classify_transcript(taxonomy: dict, transcript: str) -> ResultadoLLM | None:
    """Classify a transcript using the LLM. Returns validated result or None on failure."""
    messages = _build_messages(taxonomy, transcript)

    # Log prompt without transcript
    taxonomy_text = json.dumps(taxonomy, ensure_ascii=False, indent=2) if taxonomy.get("topicos") else "Nenhuma taxonomia existente ainda."
    logger.info("[LLM] System prompt:\n%s", SYSTEM_PROMPT)
    logger.info("[LLM] Taxonomia enviada:\n%s", taxonomy_text)

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        response = await client.chat.completions.create(
            model="gpt-5.4",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
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
