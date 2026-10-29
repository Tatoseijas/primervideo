#!/usr/bin/env python3
"""Compone portada_mafia.jpg (1280x720) a partir de portada_base.jpg (imagen de Leonardo)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
F = "/usr/share/fonts/truetype/noto/"
GRANDE = ImageFont.truetype(F + "NotoSansDisplay-ExtraCondensedBlack.ttf", 190)
MEDIA = ImageFont.truetype(F + "NotoSansDisplay-ExtraCondensedBlack.ttf", 128)
CHICA = ImageFont.truetype(F + "NotoSans-Bold.ttf", 30)

im = Image.open(BASE / "portada_base.jpg").convert("RGB")
w, h = im.size
im = im.crop((0, (h - w * 9 // 16) // 2, w, (h + w * 9 // 16) // 2)).resize((1280, 720), Image.LANCZOS)
d = ImageDraw.Draw(im)

def texto(xy, s, fuente, color):
    d.text(xy, s, font=fuente, fill=color, stroke_width=9, stroke_fill=(0, 0, 0))

texto((46, 70), "DE COBRADOR", MEDIA, (255, 255, 255))
texto((46, 195), "A REY", GRANDE, (255, 205, 20))
texto((46, 385), "DE LA MAFIA", MEDIA, (255, 255, 255))

# etiqueta roja arriba a la izquierda, como la fecha de la portada del video 1
d.rectangle((0, 20, 380, 70), fill=(200, 25, 35))
d.text((18, 26), "SIN DISPARAR UN TIRO", font=CHICA, fill=(255, 255, 255))

im.save(BASE / "portada_mafia.jpg", quality=92)
print("ok")
