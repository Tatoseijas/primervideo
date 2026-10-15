#!/usr/bin/env python3
"""Arma video_final.mp4 sincronizado con la narración (_build/narracion.wav).

Requiere haber corrido antes transcribir.py (genera _build/transcripcion.json).

- Cada escena empieza cuando la voz dice su frase ancla (ver ANCLAS).
- Imágenes con movimiento lento de cámara (Ken Burns) durante toda su duración.
- Videos 01-03 ajustados a su tramo de voz con un leve cambio de velocidad.
- Textos rediseñados según contexto (placa, navegador, marcador, captcha, clave...)
  que aparecen con animación justo cuando la voz los menciona.

Uso:
    python3 armar_video_voz.py              # render completo
    python3 armar_video_voz.py --tiempos    # solo muestra la tabla de tiempos
    python3 armar_video_voz.py --preview    # tabla + PNG de los textos en _build/overlays/
"""
import json
import math
import random
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "salida_video"
BUILD = BASE / "_build"
OVERLAYS = BUILD / "overlays"
CLIPS = BUILD / "clips_voz"
NARRACION = BUILD / "narracion.wav"
TRANSCRIPCION = BUILD / "transcripcion.json"
SALIDA = BASE / "video_final.mp4"

W, H, FPS = 1920, 1080, 30
ESCENAS_VIDEO = {1, 2, 3}
TOTAL = 68
COLA_FINAL = 1.2      # segundos de imagen después de la última palabra
ADELANTO = 0.12       # el corte entra un poco antes de la palabra ancla

F = "/usr/share/fonts/truetype/noto/"
FUENTE_TITULO = F + "NotoSansDisplay-ExtraCondensedBlack.ttf"
FUENTE_BOLD = F + "NotoSans-Bold.ttf"
FUENTE_SEMI = F + "NotoSans-SemiBold.ttf"
FUENTE_REG = F + "NotoSans-Regular.ttf"
FUENTE_MONO = F + "NotoSansMono-Bold.ttf"

# Escena -> frase de la narración con la que empieza (se busca en orden)
ANCLAS = {
    1: "tienes 10 dolares", 2: "como te haces multimillonario", 3: "entras al ascensor",
    4: "cuando se abre la puerta", 5: "en la pared del ascensor", 6: "lo primero que piensas",
    7: "pero espera", 8: "se lo das al cajero", 9: "que paso", 10: "para el cajero del 2010",
    11: "sales corriendo", 12: "y peor aun", 13: "tu telefono llegue a cero", 14: "ok respira",
    15: "no puedes vender tu telefono", 16: "pero tienes puestos", 17: "entras a una tienda",
    18: "le pones un video", 19: "el tipo se queda", 20: "el dueno te quiere", 21: "pero tu haces",
    22: "porque si estas", 23: "entras a un bar", 24: "tu te paras", 25: "dices que en el ultimo",
    26: "todo se rie", 27: "hasta que pasa", 28: "acabas de ganar", 29: "al dia siguiente",
    30: "tu pones tus mil", 31: "las apuestas pagan", 32: "90 minutos despues",
    33: "entras a un cibercafe", 34: "aqui es donde", 35: "en julio de 2010 no existian",
    36: "es mas el primer", 37: "y encima", 38: "pero mientras buscas", 39: "resulta que",
    40: "creada por el programador", 41: "sabes que hacia", 42: "no es chiste",
    43: "a precio de hoy", 44: "pero tu tienes 25", 45: "publicas un aviso",
    46: "para los universitarios", 47: "esa misma noche", 48: "les das la mochila",
    49: "domingo por la manana", 50: "tienes 100 mil cinco", 51: "en 2010 no existian las famosas",
    52: "tus monedas son", 53: "si lo guardas", 54: "asi que haces", 55: "agarras una servilleta",
    56: "y te lo metes", 57: "por si te asaltan", 58: "buscas el libro", 59: "y escribes el codigo",
    60: "falta un minuto", 61: "subes corriendo", 62: "abres tu computadora", 63: "la pantalla parpadea",
    64: "saldo actual", 65: "y sabes que es lo mas loco", 66: "cualquiera con una computadora",
    67: "pero estabamos todos", 68: "y tu en que gastarias",
}

CLAVE = "5Kb8kLf9zg••••••••••••••••••••••YB9KF"

# Escena -> (estilo, datos, frase con la que aparece el texto)
TEXTOS = {
    5: ("placa", ("TIENES 48 HORAS", "Todo lo que lleves volverá contigo."), "tienes 48 horas"),
    9: ("sello", "SERIE 2021", "serie 2021"),
    11: ("sin_servicio", "Sin servicio", "no tienes senal"),
    30: ("marcador", ("ALEMANIA", 4, "ARGENTINA", 0), "alemania gana"),
    33: ("busqueda", "BINANCE", "binance en google"),
    39: ("faucet", None, "the bitcoin faucet"),
    41: ("captcha", "waka2010", "resolver un captcha"),
    45: ("foro", None, "compro bitcoins"),
    52: ("clave", CLAVE, "un codigo rarisimo"),
    55: ("clave", CLAVE, "copias el codigo"),
    58: ("placa", ("HISTORIA DEL IMPUESTO AL TRIGO", "El libro más aburrido del mundo"), "historia del impuesto"),
    59: ("clave", CLAVE, "con lapiz"),
    64: ("saldo", "$8.500.000.000", "saldo actual"),
}


# ---------------------------------------------------------------- utilidades
def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Falló: {' '.join(map(str, cmd))[:400]}\n{r.stderr[-2500:]}")
    return r.stdout


def duracion(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", p]).strip())


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


def archivo(n):
    exts = [".mp4"] if n in ESCENAS_VIDEO else [".jpg", ".jpeg", ".png"]
    for e in exts:
        p = ENTRADA / f"escena_{n:02d}{e}"
        if p.exists():
            return p
    raise FileNotFoundError(f"Falta la escena {n:02d} en {ENTRADA}")


# ---------------------------------------------------------------- sincronía
def cargar_palabras():
    if not TRANSCRIPCION.exists():
        sys.exit("Falta _build/transcripcion.json: corré primero transcribir.py")
    palabras = []
    for seg in json.loads(TRANSCRIPCION.read_text()):
        for w in seg["palabras"]:
            for tok in norm(w["w"]):
                palabras.append((tok, w["t0"]))
    return palabras


def buscar(palabras, frase, desde_idx):
    toks = norm(frase)
    for i in range(desde_idx, len(palabras) - len(toks) + 1):
        if all(palabras[i + k][0] == t for k, t in enumerate(toks)):
            return i, palabras[i][1]
    raise ValueError(f"No encuentro «{frase}» en la narración (después de la palabra {desde_idx})")


def calcular_tiempos():
    palabras = cargar_palabras()
    total_voz = duracion(NARRACION)
    inicios, idx = {}, 0
    for n in range(1, TOTAL + 1):
        idx, t = buscar(palabras, ANCLAS[n], idx)
        inicios[n] = 0.0 if n == 1 else max(0.0, t - ADELANTO)
        idx += 1
    fin_total = total_voz + COLA_FINAL
    escenas = {}
    for n in range(1, TOTAL + 1):
        fin = inicios[n + 1] if n < TOTAL else fin_total
        escenas[n] = {"inicio": inicios[n], "dur": fin - inicios[n], "texto_en": None}
    for n, (_, _, frase) in TEXTOS.items():
        i0 = buscar(palabras, ANCLAS[n], 0)[0]
        _, t = buscar(palabras, frase, i0)
        escenas[n]["texto_en"] = max(0.0, t - escenas[n]["inicio"] - 0.05)
    # Se redondea a frames enteros para que la suma cuadre exacto con el audio
    acumulado = 0
    for n in range(1, TOTAL + 1):
        fin_frames = round((escenas[n]["inicio"] + escenas[n]["dur"]) * FPS)
        escenas[n]["frames"] = fin_frames - acumulado
        acumulado = fin_frames
    return escenas


# ---------------------------------------------------------------- diseño de textos
def fuente(path, size):
    return ImageFont.truetype(path, size)


def sombra(lienzo, caja, radio=28, blur=22, alpha=150, offset=(0, 14)):
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = caja
    ImageDraw.Draw(capa).rounded_rectangle(
        (x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]), radio, fill=(0, 0, 0, alpha))
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(blur)))


def lienzo():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def placa(datos):
    titulo, sub = datos
    im = lienzo()
    d = ImageDraw.Draw(im)
    ft, fs = fuente(FUENTE_TITULO, 104), fuente(FUENTE_SEMI, 44)
    while ft.getlength(titulo) > W * 0.8:
        ft = fuente(FUENTE_TITULO, ft.size - 4)
    ancho = max(ft.getlength(titulo), fs.getlength(sub)) + 140
    x0 = (W - ancho) / 2
    y1 = H - 90
    y0 = y1 - (ft.size * 1.05 + fs.size * 1.5 + 70)
    caja = (x0, y0, x0 + ancho, y1)
    sombra(im, caja)
    d.rounded_rectangle(caja, 26, fill=(14, 16, 24, 232))
    d.rounded_rectangle((x0, y0, x0 + 16, y1), 8, fill=(255, 190, 30, 255))
    cx = x0 + ancho / 2 + 8
    d.text((cx, y0 + 34), titulo, font=ft, fill=(255, 255, 255), anchor="mt")
    d.text((cx, y0 + 40 + ft.size * 1.05), sub, font=fs, fill=(255, 205, 90), anchor="mt")
    return im


def sello(texto):
    tmp = Image.new("RGBA", (900, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    f = fuente(FUENTE_TITULO, 150)
    d.rounded_rectangle((20, 20, 880, 310), 30, outline=(225, 30, 40, 255), width=14,
                        fill=(225, 30, 40, 60))
    d.text((450, 165), texto, font=f, fill=(235, 35, 45, 255), anchor="mm")
    tmp = tmp.rotate(-8, resample=Image.BICUBIC, expand=True)
    im = lienzo()
    sombra(im, (W - 1010, 90, W - 140, 400), radio=40, blur=26, alpha=110)
    im.alpha_composite(tmp, (W - tmp.width - 110, 70))
    return im


def sin_servicio(texto):
    im = lienzo()
    d = ImageDraw.Draw(im)
    f = fuente(FUENTE_BOLD, 58)
    ancho = 230 + f.getlength(texto) + 150
    x0, y0 = (W - ancho) / 2, 70
    caja = (x0, y0, x0 + ancho, y0 + 120)
    sombra(im, caja, radio=60)
    d.rounded_rectangle(caja, 60, fill=(18, 18, 22, 240))
    # barras de señal apagadas
    bx = x0 + 60
    for i, h in enumerate((22, 36, 50, 64)):
        d.rounded_rectangle((bx + i * 26, y0 + 92 - h, bx + i * 26 + 16, y0 + 92), 4, fill=(90, 90, 100))
    d.line((bx - 8, y0 + 98, bx + 104, y0 + 22), fill=(255, 70, 70), width=8)
    d.text((x0 + 210, y0 + 60), texto, font=f, fill=(255, 255, 255), anchor="lm")
    # círculo rojo con cruz
    cx, cy, r = x0 + ancho - 75, y0 + 60, 34
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(230, 45, 45))
    d.line((cx - 14, cy - 14, cx + 14, cy + 14), fill="white", width=8)
    d.line((cx - 14, cy + 14, cx + 14, cy - 14), fill="white", width=8)
    return im


def bandera(d, caja, colores, vertical=False):
    x0, y0, x1, y1 = caja
    n = len(colores)
    for i, c in enumerate(colores):
        if vertical:
            d.rectangle((x0 + (x1 - x0) * i / n, y0, x0 + (x1 - x0) * (i + 1) / n, y1), fill=c)
        else:
            d.rectangle((x0, y0 + (y1 - y0) * i / n, x1, y0 + (y1 - y0) * (i + 1) / n), fill=c)


def marcador(datos):
    eq1, g1, eq2, g2 = datos
    im = lienzo()
    d = ImageDraw.Draw(im)
    fe, fg, fl = fuente(FUENTE_TITULO, 78), fuente(FUENTE_TITULO, 104), fuente(FUENTE_BOLD, 30)
    anch_eq = max(fe.getlength(eq1), fe.getlength(eq2)) + 150
    ancho = anch_eq * 2 + 300
    x0, y0, alto = (W - ancho) / 2, 60, 150
    sombra(im, (x0, y0, x0 + ancho, y0 + alto + 52), radio=18)
    d.rounded_rectangle((x0, y0, x0 + ancho, y0 + alto), 18, fill=(250, 250, 250, 245))
    xm = x0 + anch_eq
    d.rectangle((xm, y0, xm + 300, y0 + alto), fill=(16, 20, 32, 255))
    d.text((xm + 150, y0 + alto / 2), f"{g1}  -  {g2}", font=fg, fill="white", anchor="mm")
    bandera(d, (x0 + 34, y0 + 48, x0 + 104, y0 + 102),
            [(0, 0, 0), (221, 0, 0), (255, 206, 0)])
    d.text((x0 + 124, y0 + alto / 2), eq1, font=fe, fill=(20, 20, 30), anchor="lm")
    bandera(d, (x0 + ancho - 104, y0 + 48, x0 + ancho - 34, y0 + 102),
            [(116, 172, 223), (255, 255, 255), (116, 172, 223)])
    d.rectangle((x0 + ancho - 104, y0 + 48, x0 + ancho - 34, y0 + 102), outline=(200, 200, 200), width=2)
    d.text((x0 + ancho - 124, y0 + alto / 2), eq2, font=fe, fill=(20, 20, 30), anchor="rm")
    d.rounded_rectangle((xm + 60, y0 + alto - 4, xm + 240, y0 + alto + 46), 10, fill=(225, 30, 40))
    d.text((xm + 150, y0 + alto + 21), "FINAL", font=fl, fill="white", anchor="mm")
    return im


def ventana(url, alto_contenido, ancho=1180, y_centro=None):
    """Dibuja una ventana de navegador retro (estilo 2010) y devuelve (imagen, caja del contenido)."""
    im = lienzo()
    d = ImageDraw.Draw(im)
    alto = 110 + alto_contenido
    x0 = (W - ancho) / 2
    y0 = (y_centro or H * 0.55) - alto / 2
    caja = (x0, y0, x0 + ancho, y0 + alto)
    sombra(im, caja, radio=14, blur=26, alpha=170)
    d.rounded_rectangle(caja, 14, fill=(236, 238, 242, 255), outline=(150, 156, 170), width=2)
    d.rounded_rectangle((x0, y0, x0 + ancho, y0 + 50), 14, fill=(60, 110, 200))
    d.rectangle((x0, y0 + 30, x0 + ancho, y0 + 50), fill=(60, 110, 200))
    for i, c in enumerate([(240, 90, 80), (250, 190, 60), (90, 200, 90)]):
        d.ellipse((x0 + ancho - 130 + i * 38, y0 + 14, x0 + ancho - 108 + i * 38, y0 + 36), fill=c)
    d.text((x0 + 22, y0 + 25), "Internet Explorer", font=fuente(FUENTE_SEMI, 24), fill="white", anchor="lm")
    d.rounded_rectangle((x0 + 18, y0 + 62, x0 + ancho - 18, y0 + 98), 6, fill="white", outline=(170, 175, 185))
    d.text((x0 + 34, y0 + 80), "http://" + url, font=fuente(FUENTE_REG, 24), fill=(60, 60, 70), anchor="lm")
    cont = (x0 + 2, y0 + 108, x0 + ancho - 2, y0 + alto - 2)
    d.rectangle(cont, fill="white")
    return im, d, cont


def busqueda(termino):
    im, d, (x0, y0, x1, y1) = ventana("www.google.com/search?q=binance", 300)
    d.text((x0 + 50, y0 + 60), "Google", font=fuente(FUENTE_BOLD, 64), fill=(66, 133, 244), anchor="lm")
    d.rounded_rectangle((x0 + 290, y0 + 30, x1 - 50, y0 + 92), 8, outline=(160, 165, 175), width=3)
    d.text((x0 + 312, y0 + 61), "Búsqueda: ", font=fuente(FUENTE_REG, 36), fill=(110, 110, 120), anchor="lm")
    d.text((x0 + 312 + fuente(FUENTE_REG, 36).getlength("Búsqueda: "), y0 + 61), termino,
           font=fuente(FUENTE_BOLD, 38), fill=(20, 20, 30), anchor="lm")
    d.line((x0 + 40, y0 + 130, x1 - 40, y0 + 130), fill=(220, 222, 228), width=2)
    d.text((x0 + 60, y0 + 190), "0 resultados", font=fuente(FUENTE_BOLD, 72), fill=(220, 40, 40), anchor="lm")
    d.text((x0 + 60, y0 + 255), "No se ha encontrado ningún documento que coincida con BINANCE.",
           font=fuente(FUENTE_REG, 30), fill=(90, 90, 100), anchor="lm")
    return im


def faucet(_):
    im, d, (x0, y0, x1, y1) = ventana("freebitcoins.appspot.com", 300)
    cx = (x0 + x1) / 2
    d.ellipse((cx - 300 - 120, y0 + 50, cx - 300 - 20, y0 + 150), fill=(247, 147, 26))
    d.text((cx - 370, y0 + 100), "₿", font=fuente(FUENTE_BOLD, 70), fill="white", anchor="mm")
    d.text((cx - 290, y0 + 100), "THE BITCOIN FAUCET", font=fuente(FUENTE_TITULO, 96),
           fill=(30, 30, 40), anchor="lm")
    d.rounded_rectangle((cx - 400, y0 + 180, cx + 400, y0 + 270), 12, fill=(247, 147, 26))
    d.text((cx, y0 + 225), "GET 5 FREE BITCOINS!", font=fuente(FUENTE_TITULO, 72), fill="white", anchor="mm")
    return im


def captcha(palabra):
    im, d, (x0, y0, x1, y1) = ventana("freebitcoins.appspot.com", 330, ancho=900)
    d.text((x0 + 50, y0 + 50), "Captcha:", font=fuente(FUENTE_BOLD, 46), fill=(30, 30, 40), anchor="lm")
    # texto deformado tipo captcha 2010
    caja = (x0 + 50, y0 + 90, x1 - 50, y0 + 230)
    d.rectangle(caja, fill=(228, 226, 214), outline=(150, 150, 140), width=2)
    rnd = random.Random(2010)
    for _ in range(14):
        d.line([(rnd.uniform(caja[0], caja[2]), rnd.uniform(caja[1], caja[3])) for _ in range(2)],
               fill=(150, 140, 120), width=2)
    x = caja[0] + 60
    for ch in palabra:
        letra = Image.new("RGBA", (120, 140), (0, 0, 0, 0))
        ImageDraw.Draw(letra).text((60, 70), ch, font=fuente(FUENTE_BOLD, 92), fill=(40, 40, 60), anchor="mm")
        letra = letra.rotate(rnd.uniform(-22, 22), resample=Image.BICUBIC)
        im.alpha_composite(letra, (int(x), int(caja[1] + rnd.uniform(-6, 12))))
        x += 82
    d.line([(caja[0] + 30, caja[1] + 80), (caja[2] - 40, caja[1] + 60)], fill=(60, 60, 80), width=4)
    d.rounded_rectangle((x0 + 50, y0 + 252, x1 - 220, y0 + 310), 6, fill="white", outline=(150, 155, 165), width=2)
    d.text((x0 + 70, y0 + 281), palabra, font=fuente(FUENTE_MONO, 36), fill=(20, 20, 30), anchor="lm")
    d.rounded_rectangle((x1 - 200, y0 + 252, x1 - 50, y0 + 310), 8, fill=(60, 150, 70))
    d.text((x1 - 125, y0 + 281), "Enviar", font=fuente(FUENTE_BOLD, 30), fill="white", anchor="mm")
    return im


def foro(_):
    im, d, (x0, y0, x1, y1) = ventana("bitcointalk.org/index.php?topic=nuevo", 330)
    d.rectangle((x0, y0, x1, y0 + 56), fill=(70, 90, 120))
    d.text((x0 + 30, y0 + 28), "Bitcoin Forum  ›  Marketplace  ›  Nuevo tema", font=fuente(FUENTE_SEMI, 28),
           fill="white", anchor="lm")
    d.text((x0 + 40, y0 + 120), "COMPRO BITCOINS A $0.25", font=fuente(FUENTE_TITULO, 100),
           fill=(30, 30, 40), anchor="lm")
    d.rounded_rectangle((x0 + 40, y0 + 190, x0 + 520, y0 + 260), 10, fill=(40, 160, 70))
    d.text((x0 + 280, y0 + 225), "HOY · EN EFECTIVO", font=fuente(FUENTE_TITULO, 56), fill="white", anchor="mm")
    d.text((x0 + 560, y0 + 225), "Pago 5 veces más de lo que valen.", font=fuente(FUENTE_REG, 32),
           fill=(80, 80, 90), anchor="lm")
    return im


def clave(texto):
    im = lienzo()
    d = ImageDraw.Draw(im)
    fm = fuente(FUENTE_MONO, 64)
    while fm.getlength(texto) > W * 0.82:
        fm = fuente(FUENTE_MONO, fm.size - 2)
    ancho = fm.getlength(texto) + 120
    x0, y1 = (W - ancho) / 2, H - 100
    y0 = y1 - 190
    caja = (x0, y0, x0 + ancho, y1)
    sombra(im, caja, radio=18)
    d.rounded_rectangle(caja, 18, fill=(8, 14, 10, 238), outline=(40, 200, 90), width=3)
    d.text((x0 + 60, y0 + 46), "CLAVE PRIVADA · 51 CARACTERES", font=fuente(FUENTE_BOLD, 30),
           fill=(120, 220, 150), anchor="lm")
    d.text((x0 + 60, y0 + 125), texto, font=fm, fill=(80, 255, 130), anchor="lm")
    return im


def saldo(monto):
    im = lienzo()
    d = ImageDraw.Draw(im)
    fg = fuente(FUENTE_TITULO, 150)
    ancho = fg.getlength(monto) + 260
    x0, y0 = (W - ancho) / 2, H - 450
    caja = (x0, y0, x0 + ancho, y0 + 370)
    sombra(im, caja, radio=30, alpha=170)
    d.rounded_rectangle(caja, 30, fill=(255, 255, 255, 248))
    d.text((x0 + 70, y0 + 60), "SALDO ACTUAL", font=fuente(FUENTE_BOLD, 40), fill=(110, 115, 130), anchor="lm")
    d.ellipse((x0 + ancho - 130, y0 + 30, x0 + ancho - 60, y0 + 100), fill=(247, 147, 26))
    d.text((x0 + ancho - 95, y0 + 65), "₿", font=fuente(FUENTE_BOLD, 46), fill="white", anchor="mm")
    d.text((x0 + 70, y0 + 120), "MÁS DE", font=fuente(FUENTE_TITULO, 60), fill=(20, 150, 70), anchor="lt")
    d.text((x0 + 70, y0 + 200), monto, font=fg, fill=(20, 170, 80), anchor="lt")
    d.text((x0 + ancho - 70, y0 + 335), "USD", font=fuente(FUENTE_TITULO, 60), fill=(20, 150, 70), anchor="rs")
    return im


ESTILOS = {"placa": placa, "sello": sello, "sin_servicio": sin_servicio, "marcador": marcador,
           "busqueda": busqueda, "faucet": faucet, "captcha": captcha, "foro": foro,
           "clave": clave, "saldo": saldo}


def generar_overlays():
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for n, (estilo, datos, _) in TEXTOS.items():
        p = OVERLAYS / f"texto_{n:02d}.png"
        ESTILOS[estilo](datos).save(p)
        rutas[n] = p
    return rutas


# ---------------------------------------------------------------- clips
X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", FPS, "-an"]

# Movimientos de cámara: (zoom, x, y) en función de P = progreso suavizado 0→1
MOVIMIENTOS = [
    ("1+0.10*P", "(iw-iw/zoom)/2", "(ih-ih/zoom)*0.35"),         # acercar hacia la cara
    ("1.10-0.10*P", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),         # alejar
    ("1.10", "(iw-iw/zoom)*P", "(ih-ih/zoom)/2"),                # paneo a la derecha
    ("1+0.08*P", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),            # acercar al centro
    ("1.10", "(iw-iw/zoom)*(1-P)", "(ih-ih/zoom)*0.4"),          # paneo a la izquierda
]


def filtro_texto(n, inicio_txt):
    # aparece con fundido y un pequeño desplazamiento hacia arriba
    t = f"{inicio_txt:.3f}"
    return (f"[1:v]format=rgba,fade=t=in:st={t}:d=0.35:alpha=1[o];"
            f"[v][o]overlay=x=0:y='if(lt(t,{t}),40,40*max(0,1-(t-{t})/0.35))':eval=frame:shortest=1")


def clip_imagen(n, esc, overlay):
    frames = esc["frames"]
    z, x, y = MOVIMIENTOS[(n * 3) % len(MOVIMIENTOS)]
    p = f"(on/{max(frames - 1, 1)})"
    P = f"({p}*{p}*(3-2*{p}))"  # ease in-out
    z, x, y = (e.replace("P", P) for e in (z, x, y))
    base = (f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},setsar=1")
    if n == TOTAL:
        base += f",fade=t=out:st={frames / FPS - 1.0:.3f}:d=1.0"
    destino = CLIPS / f"clip_{n:02d}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", archivo(n)]
    if overlay:
        cmd += ["-loop", "1", "-framerate", FPS, "-i", overlay,
                "-filter_complex", f"{base}[v];" + filtro_texto(n, esc["texto_en"])]
    else:
        cmd += ["-filter_complex", base]
    run(cmd + ["-frames:v", frames, *X264, destino])
    return destino


def clip_video(n, esc):
    frames = esc["frames"]
    original = duracion(archivo(n))
    factor = (frames / FPS) / original  # >1 cámara lenta suave, <1 un poco más rápido
    vf = (f"setpts={factor:.5f}*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration=1")
    destino = CLIPS / f"clip_{n:02d}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", archivo(n), "-vf", vf, "-frames:v", frames, *X264, destino])
    return destino


# ---------------------------------------------------------------- main
def imprimir_tabla(escenas):
    print(f"{'esc':>3}  {'inicio':>7}  {'dur':>5}  texto")
    for n, e in escenas.items():
        extra = f"  ← texto a los +{e['texto_en']:.1f}s" if e["texto_en"] is not None else ""
        print(f"{n:>3}  {e['inicio']:7.2f}  {e['frames'] / FPS:5.2f}  «{ANCLAS[n]}»{extra}")
    total = sum(e["frames"] for e in escenas.values()) / FPS
    print(f"Total video: {total:.2f}s  (voz: {duracion(NARRACION):.2f}s)")


def main():
    for n in range(1, TOTAL + 1):
        archivo(n)
    escenas = calcular_tiempos()
    imprimir_tabla(escenas)
    if "--tiempos" in sys.argv:
        return
    overlays = generar_overlays()
    print(f"OK: {len(overlays)} textos generados en {OVERLAYS}")
    if "--preview" in sys.argv:
        return

    CLIPS.mkdir(parents=True, exist_ok=True)

    def hacer(n):
        if n in ESCENAS_VIDEO:
            return clip_video(n, escenas[n])
        return clip_imagen(n, escenas[n], overlays.get(n))

    with ThreadPoolExecutor(max_workers=4) as pool:
        clips = list(pool.map(hacer, range(1, TOTAL + 1)))
    for n, c in enumerate(clips, 1):
        real = round(duracion(c) * FPS)
        if real != escenas[n]["frames"]:
            print(f"  aviso: escena {n:02d} tiene {real} frames (esperados {escenas[n]['frames']})")

    lista = CLIPS / "lista.txt"
    lista.write_text("".join(f"file '{c.name}'\n" for c in clips))
    solo_video = CLIPS / "solo_video.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", solo_video])
    # la voz se rellena con silencio hasta la duración exacta del video
    # (apad sin límite + -shortest con copia de video deja a ffmpeg generando silencio sin fin)
    total = duracion(solo_video)
    run(["ffmpeg", "-v", "error", "-y", "-i", solo_video, "-i", NARRACION, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"apad=whole_dur={total:.3f}",
         "-movflags", "+faststart", SALIDA])
    print(f"LISTO: {SALIDA} — {duracion(SALIDA):.2f}s")


if __name__ == "__main__":
    main()
