"""
Run with:  python preview_template.py
Opens ai_variant_email.html rendered with sample data in your default browser.
"""
import webbrowser
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).parent / "app" / "templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

SAMPLE = {
    # system / fixed
    "logo_url":        "https://baby-engagement-api.onrender.com/static/logo.png",
    "terms_line":      "Válido presentando este email en el local Pika Pika",
    "maps_url":        "https://www.google.com/maps/place/Pika+pika/@-33.0094136,-58.5212939,17z",
    "whatsapp_url":    "https://wa.me/5493446586123",
    "instagram_url":   "https://instagram.com/pikapikagchu",
    "instagram_handle":"@pikapikagchu",
    "address":         "Rocamora 35, Gualeguaychu, Entre Rios",
    "hours":           "Lun a Sab",
    "unsubscribe_url": "#",

    # AI gaps (sample copy)
    "headline":         "¡Esta semana tenemos algo especial para vos y tu bebé!",
    "highlight_phrase": "20% de descuento en toda la tienda",
    "body_intro":       "Vení a visitarnos y aprovechá esta promo exclusiva para nuestros clientes registrados.",
    "block_1_emoji":    "🧸",
    "block_1_title":    "Juguetes",
    "block_1_text":     "Creatividad, aprendizaje y diversión en un solo lugar.",
    "block_2_emoji":    "👶",
    "block_2_title":    "Artículos para bebé",
    "block_2_text":     "Todo lo que necesitás para acompañar cada etapa.",
    "closing_message":  "Gracias por acompañarnos 💛\n\nNos encanta ser parte de cada regalo, cada juego y cada sonrisa.\n\nTe esperamos en Pika Pika 🧸✨",
}

html = jinja_env.get_template("ai_variant_email.html").render(**SAMPLE)

out = Path(__file__).parent / "preview_output.html"
out.write_text(html, encoding="utf-8")
print(f"Saved -> {out}")
webbrowser.open(out.as_uri())
