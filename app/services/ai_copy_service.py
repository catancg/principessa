import json
import os

from openai import OpenAI

_STORE_CONTEXT = """
Pika Pika es una tienda de ropa y artículos para bebés ubicada en Gualeguaychu, Entre Ríos, Argentina.
Dirección: Rocamora 35, Gualeguaychu, Entre Ríos.
WhatsApp: +54 9 3446 586123 | Instagram: @pikapikagchu | Horarios: Lun a Sáb.
Los clientes se suscribieron voluntariamente para recibir promociones.
"""

_SYSTEM_PROMPT = (
    "Sos un experto en email marketing para tiendas de bebés en Argentina. "
    "Escribís en español rioplatense, con tono cercano y auténtico. "
    "Nunca usás mayúsculas innecesarias. Tus textos son breves y directos."
)

# These are the exact gaps in the email template the AI must fill.
_FIELD_SPEC = """
Cada variante debe tener exactamente estos campos:

- subject_line: asunto del email para el inbox, máximo 60 caracteres
- preview_text: texto de vista previa del inbox, máximo 90 caracteres
- headline: titular principal del email (1 oración, tono llamativo)
- highlight_phrase: 3-6 palabras que van resaltadas en amarillo dentro del cuerpo (ej: "descuento especial esta semana")
- body_intro: 1 oración que complementa el titular y el resaltado
- block_1_emoji: 1 emoji para el primer bloque de categoría
- block_1_title: nombre de la primera categoría, máximo 20 caracteres
- block_1_text: 1 oración corta describiendo esa categoría
- block_2_emoji: 1 emoji para el segundo bloque de categoría
- block_2_title: nombre de la segunda categoría, máximo 20 caracteres
- block_2_text: 1 oración corta describiendo esa categoría
- closing_message: mensaje de cierre cálido, 2-3 oraciones cortas
"""


def generate_variants(prompt: str = "", num_variants: int = 2) -> list[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    campaign_context = prompt.strip() or "campaña semanal de promociones y novedades"

    user_message = f"""
Generá {num_variants} variantes de email de marketing para una campaña semanal de Pika Pika.

Contexto de la tienda:
{_STORE_CONTEXT}

Contexto de la campaña: {campaign_context}

{_FIELD_SPEC}

Las {num_variants} variantes deben ser claramente distintas en tono:
- Variante 1: tono urgente / promocional (oferta, no te lo perdas, esta semana)
- Variante 2: tono cálido / cercano (comunidad, confianza, familia)

Devolvé un JSON con la siguiente estructura:
{{ "variants": [ {{...variante1...}}, {{...variante2...}} ] }}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.85,
    )

    data = json.loads(response.choices[0].message.content)
    variants = data.get("variants", [])

    if not isinstance(variants, list) or len(variants) != num_variants:
        raise ValueError(f"Expected {num_variants} variants, got: {str(data)[:300]}")

    required_keys = {
        "subject_line", "preview_text", "headline", "highlight_phrase",
        "body_intro", "block_1_emoji", "block_1_title", "block_1_text",
        "block_2_emoji", "block_2_title", "block_2_text", "closing_message",
    }
    for i, v in enumerate(variants):
        missing = required_keys - v.keys()
        if missing:
            raise ValueError(f"Variant {i+1} missing keys: {missing}")

    return variants
