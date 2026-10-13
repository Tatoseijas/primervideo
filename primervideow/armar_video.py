#!/usr/bin/env python3
"""Ensambla las 68 escenas de salida_video/ en video_final.mp4 (1920x1080, 30 fps, sin audio).

- Escenas 01-03: videos .mp4, se respeta su duración original.
- Escenas 04-68: imágenes (.jpg o .png), 3.0 s cada una.
- Textos en pantalla dibujados con Pillow sobre los frames (no depende de ImageMagick ni de drawtext).

Uso:
    python3 armar_video.py            # render completo
    python3 armar_video.py --preview  # solo genera las imágenes con texto en _build/ para revisarlas
"""
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "salida_video"
BUILD = BASE / "_build"
SALIDA = BASE / "video_final.mp4"

ANCHO, ALTO, FPS = 1920, 1080, 30
DURACION_IMAGEN = 3.0
ESCENAS_VIDEO = {1, 2, 3}
TOTAL_ESCENAS = 68

FUENTE_TEXTO = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FUENTE_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
TAMANO_EMOJI_NATIVO = 109  # Noto Color Emoji es un bitmap que solo se carga a este tamaño

TEXTOS = {
    5: "TIENES 48 HORAS. TODO LO QUE LLEVES VOLVERÁ CONTIGO.",
    9: "SERIE 2021",
    11: "SIN SERVICIO ❌",
    30: "ALEMANIA 4 - ARGENTINA 0",
    33: "Búsqueda: BINANCE — 0 resultados",
    39: "THE BITCOIN FAUCET - GET 5 FREE BITCOINS!",
    41: "Captcha: waka2010",
    45: "COMPRO BITCOINS A $0.25 HOY EN EFECTIVO",
    52: "5Kb8kLf9zg••••••••••••••••••••••YB9KF",
    55: "5Kb8kLf9zg••••••••••••••••••••••YB9KF",
    58: "HISTORIA DEL IMPUESTO AL TRIGO",
    59: "5Kb8kLf9zg••••••••••••••••••••••YB9KF",
    64: "SALDO ACTUAL: MÁS DE $8.500.000.000 USD",
}

EMOJIS = {"❌"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Falló: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def buscar_archivo(n):
    """Devuelve el archivo de la escena n respetando el tipo esperado (video o imagen)."""
    exts = [".mp4"] if n in ESCENAS_VIDEO else [".jpg", ".jpeg", ".png"]
    for ext in exts:
        p = ENTRADA / f"escena_{n:02d}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"No encuentro la escena {n:02d} ({'/'.join(exts)}) en {ENTRADA}")


def cubrir(img):
    """Escala para cubrir 1920x1080 y recorta el sobrante centrado (mantiene 16:9 sin barras)."""
    escala = max(ANCHO / img.width, ALTO / img.height)
    img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)
    x, y = (img.width - ANCHO) // 2, (img.height - ALTO) // 2
    return img.crop((x, y, x + ANCHO, y + ALTO))


def segmentos(texto):
    """Separa el texto en tramos de texto normal y emojis."""
    out, actual = [], ""
    for ch in texto:
        if ch in EMOJIS:
            if actual:
                out.append(("txt", actual))
                actual = ""
            out.append(("emoji", ch))
        else:
            actual += ch
    if actual:
        out.append(("txt", actual))
    return out


def ancho_linea(linea, fuente):
    total = 0
    for tipo, s in segmentos(linea):
        total += fuente.size * 1.1 if tipo == "emoji" else fuente.getlength(s)
    return total


def partir_lineas(texto, fuente, ancho_max):
    palabras, lineas, actual = texto.split(" "), [], ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if ancho_linea(prueba, fuente) <= ancho_max or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def dibujar_emoji(lienzo, ch, x, y_centro, alto):
    fe = ImageFont.truetype(FUENTE_EMOJI, TAMANO_EMOJI_NATIVO)
    tmp = Image.new("RGBA", (TAMANO_EMOJI_NATIVO * 2, TAMANO_EMOJI_NATIVO * 2), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((0, 0), ch, font=fe, embedded_color=True)
    tmp = tmp.crop(tmp.getbbox())
    lado = int(alto)
    tmp = tmp.resize((round(tmp.width * lado / tmp.height), lado), Image.LANCZOS)
    lienzo.alpha_composite(tmp, (int(x), int(y_centro - lado / 2)))
    return tmp.width


def poner_texto(img, texto):
    img = img.convert("RGBA")
    ancho_max = ANCHO * 0.86
    tam = 104
    while True:
        fuente = ImageFont.truetype(FUENTE_TEXTO, tam)
        lineas = partir_lineas(texto, fuente, ancho_max)
        if all(ancho_linea(l, fuente) <= ancho_max for l in lineas) and len(lineas) <= 3:
            break
        tam -= 4
    borde = max(4, tam // 12)
    alto_linea = tam * 1.25
    alto_total = alto_linea * len(lineas)
    y = (ALTO - alto_total) / 2

    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for linea in lineas:
        x = (ANCHO - ancho_linea(linea, fuente)) / 2
        y_centro = y + alto_linea / 2
        for tipo, s in segmentos(linea):
            if tipo == "emoji":
                x += dibujar_emoji(capa, s, x + tam * 0.05, y_centro, tam) + tam * 0.1
            else:
                # sombra suave + texto blanco con borde negro
                d.text((x + 6, y_centro + 6), s, font=fuente, anchor="lm", fill=(0, 0, 0, 160),
                       stroke_width=borde, stroke_fill=(0, 0, 0, 160))
                d.text((x, y_centro), s, font=fuente, anchor="lm", fill="white",
                       stroke_width=borde, stroke_fill="black")
                x += fuente.getlength(s)
        y += alto_linea
    return Image.alpha_composite(img, capa).convert("RGB")


def preparar_imagen(n):
    img = cubrir(Image.open(buscar_archivo(n)).convert("RGB"))
    if n in TEXTOS:
        img = poner_texto(img, TEXTOS[n])
    destino = BUILD / f"frame_{n:02d}.png"
    img.save(destino)
    return destino


X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-an"]


def clip_desde_video(n):
    destino = BUILD / f"clip_{n:02d}.mp4"
    vf = (f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,"
          f"crop={ANCHO}:{ALTO},setsar=1,fps={FPS}")
    run(["ffmpeg", "-v", "error", "-y", "-i", buscar_archivo(n), "-vf", vf, *X264, destino])
    return destino


def clip_desde_imagen(n, frame):
    destino = BUILD / f"clip_{n:02d}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", frame,
         "-t", f"{DURACION_IMAGEN}", "-vf", "setsar=1", *X264, destino])
    return destino


def duracion(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", p]).strip())


def main():
    preview = "--preview" in sys.argv
    if not shutil.which("ffmpeg"):
        sys.exit("No encuentro ffmpeg en el PATH.")
    BUILD.mkdir(exist_ok=True)

    # 1. Verificar que estén las 68 escenas antes de empezar
    archivos = {n: buscar_archivo(n) for n in range(1, TOTAL_ESCENAS + 1)}
    print(f"OK: {len(archivos)} escenas encontradas.")

    # 2. Frames con texto
    frames = {}
    for n in range(1, TOTAL_ESCENAS + 1):
        if n not in ESCENAS_VIDEO:
            frames[n] = preparar_imagen(n)
    print(f"OK: {len(frames)} imágenes preparadas en {BUILD} ({len(TEXTOS)} con texto).")
    if preview:
        return

    # 3. Un clip por escena, todos con el mismo códec/fps/tamaño
    clips = []
    for n in range(1, TOTAL_ESCENAS + 1):
        clip = clip_desde_video(n) if n in ESCENAS_VIDEO else clip_desde_imagen(n, frames[n])
        clips.append(clip)
        print(f"  escena {n:02d} -> {duracion(clip):.2f}s")

    # 4. Concatenar sin recodificar
    lista = BUILD / "lista.txt"
    lista.write_text("".join(f"file '{c.name}'\n" for c in clips))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista,
         "-c", "copy", "-an", "-movflags", "+faststart", SALIDA])

    esperado = sum(duracion(archivos[n]) for n in ESCENAS_VIDEO) + \
        DURACION_IMAGEN * (TOTAL_ESCENAS - len(ESCENAS_VIDEO))
    print(f"LISTO: {SALIDA} — {duracion(SALIDA):.2f}s (esperado ≈ {esperado:.2f}s)")


if __name__ == "__main__":
    main()
