#!/usr/bin/env python3
"""Arma el video "El precio de la corona" a partir de salida_mafia/ y la locución.

- Cada escena empieza cuando la voz dice su frase ancla (ver ANCLAS).
- Imágenes con movimiento lento de cámara (Ken Burns); las franjas negras de los bordes se recortan.
- Escenas 1 a 5: video animado de Leonardo (sin su audio), con la imagen quieta si la escena dura más.
- Títulos de fase (Fase Uno ... Fase Cuatro) con animación cuando la voz los dice.
- Se codifica con PyAV (libx264 + aac), no hace falta ffmpeg.

Modos de tiempos:
  prueba   no hay locución todavía: los tiempos se estiman por cantidad de caracteres (13,7 car/s, como el
           video 2) y el audio queda en silencio. Sale video_prueba.mp4 a 960x540.
  real     hay locucion_mafia.mp3 y _build/transcripcion.json (ver --transcribir): tiempos exactos.
           Sale video_final.mp4 a 1920x1080.

Uso:
    python3 armar_video.py --tiempos        # tabla de tiempos, sin renderizar
    python3 armar_video.py                  # prueba (o real si ya hay locución y transcripción)
    python3 armar_video.py --transcribir    # transcribe locucion_mafia.mp3 con faster-whisper
    python3 armar_video.py --max 40         # renderiza solo los primeros 40 segundos
"""
import argparse
import json
import re
import sys
import unicodedata
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
ESCENAS = BASE / "salida_mafia"
BUILD = BASE / "_build"
GUION = BASE / "guion_mafia.txt"
LOCUCION = BASE / "locucion_mafia.mp3"
TRANSCRIPCION = BUILD / "transcripcion.json"

FPS = 30
CPS = 13.7            # caracteres por segundo de la voz (medido en el video 2)
COLA_FINAL = 3.0      # segundos de imagen después de la última palabra
ADELANTO = 0.12       # el corte entra un poco antes de la palabra ancla
FUNDIDO = 0.25        # segundos de fundido entre escenas
ESCENAS_VIDEO = {1, 2, 3, 4, 5}
TOTAL = 63

F = "/usr/share/fonts/truetype/noto/"
FUENTE_TITULO = F + "NotoSansDisplay-ExtraCondensedBlack.ttf"
FUENTE_SUB = F + "NotoSans-SemiBold.ttf"

# Escena -> frase de la locución con la que empieza (se busca en orden)
ANCLAS = {
    1: "el poder en el inframundo", 2: "en la mafia el poder se arranca", 3: "hoy vamos a recorrer",
    4: "como pasa un don nadie", 5: "imagina a un joven", 6: "fase uno el barro",
    7: "su oficina son los callejones", 8: "y los pasillos con olor", 9: "su jefe es un subjefe",
    10: "el trabajo de dante es simple", 11: "romper manos", 12: "asegurarse de que el miedo",
    13: "en este nivel la esperanza", 14: "si la policia necesita", 15: "si una banda rival",
    16: "pero dante tiene algo", 17: "mientras los demas gastan", 18: "que los mantienen atados",
    19: "dante no bebe", 20: "entiende la primera gran regla", 21: "fase dos la oportunidad",
    22: "ahora maneja a un pequeno", 23: "una bala perdida", 24: "el mundo ha cambiado",
    25: "pero no entienden de criptomonedas", 26: "un dia un cargamento", 27: "las cuentas principales",
    28: "los jefes entran en panico", 29: "dante da un paso", 30: "le ofrece una solucion",
    31: "a traves de anos de observacion", 32: "en setenta y dos horas", 33: "soborna a un oficial",
    34: "con una deuda de apuestas", 35: "el jefe queda deslumbrado", 36: "se convierte en cerebro",
    37: "fase tres el tejedor", 38: "ahora dante compra cosas", 39: "financia las carreras",
    40: "el dinero sucio entra", 41: "dante es indispensable", 42: "pero hay un problema",
    43: "empieza a ordenar ejecuciones", 44: "empieza a llamar la atencion", 45: "dante se da cuenta",
    46: "fase cuatro el jaque mate", 47: "durante una cena rutinaria", 48: "a la manana siguiente",
    49: "lo arrestan en pijama", 50: "con el lider supremo", 51: "los capitanes menores",
    52: "pero antes de que se dispare", 53: "les muestra los numeros", 54: "nadie desenfunda un arma",
    55: "el perro de cobro ha tomado", 56: "hoy dante esta en la cima", 57: "pero la victoria tiene un precio",
    58: "no confia en su esposa", 59: "sabe perfectamente como", 60: "sabe que en algun lugar",
    61: "cobrando una deuda", 62: "porque en el inframundo la corona", 63: "vos crees que soportarias",
}

# (titulo, subtitulo, frase con la que aparece)
TITULOS = [
    ("FASE UNO", "El barro y la sangre", "fase uno el barro"),
    ("FASE DOS", "La oportunidad de oro", "fase dos la oportunidad"),
    ("FASE TRES", "El tejedor de hilos", "fase tres el tejedor"),
    ("FASE CUATRO", "El jaque mate", "fase cuatro el jaque mate"),
]


# ---------------------------------------------------------------- tiempos
def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


def palabras_estimadas():
    """Palabras del guion con tiempos estimados por caracteres (modo prueba)."""
    t, out = 0.0, []
    for w in norm(GUION.read_text()):
        d = (len(w) + 1) / CPS
        out.append({"w": w, "start": t, "end": t + d})
        t += d
    return out


def buscar(palabras, frase, desde):
    ws = norm(frase)
    textos = [p["w"] for p in palabras]
    for i in range(desde, len(textos) - len(ws) + 1):
        if textos[i:i + len(ws)] == ws:
            return i
    raise SystemExit(f"No encuentro la frase ancla «{frase}» a partir de la palabra {desde}.")


def tiempos(palabras):
    """-> (inicio de cada escena [0..TOTAL-1], fin total, [(titulo, sub, t)])."""
    inicios, i = {}, 0
    for n in range(1, TOTAL + 1):
        i = buscar(palabras, ANCLAS[n], i)
        inicios[n] = max(0.0, palabras[i]["start"] - ADELANTO)
        i += 1
    inicios[1] = 0.0
    titulos, j = [], 0
    for tit, sub, frase in TITULOS:
        j = buscar(palabras, frase, j)
        titulos.append((tit, sub, palabras[j]["start"]))
    return inicios, palabras[-1]["end"] + COLA_FINAL, titulos


# ---------------------------------------------------------------- imágenes
def recortar_franjas(im):
    """Quita las franjas negras de los bordes (filas/columnas casi negras de punta a punta)."""
    a = np.asarray(im.convert("L"))
    h, w = a.shape
    fila = (a.max(axis=1) < 14)
    col = (a.max(axis=0) < 14)
    t = b = l = r = 0
    while t < h * 0.14 and fila[t]: t += 1
    while b < h * 0.14 and fila[h - 1 - b]: b += 1
    while l < w * 0.14 and col[l]: l += 1
    while r < w * 0.14 and col[w - 1 - r]: r += 1
    return im.crop((l, t, w - r, h - b)) if (t or b or l or r) else im


class Imagen:
    """Escena de imagen fija con Ken Burns."""

    def __init__(self, n, W, H):
        self.W, self.H = W, H
        im = recortar_franjas(Image.open(ESCENAS / f"escena_{n:02d}.jpg").convert("RGB"))
        self.im = im
        iw, ih = im.size
        ar = W / H
        # caja 16:9 más grande posible dentro de la imagen
        bw, bh = (iw, iw / ar) if iw / ih < ar else (ih * ar, ih)
        self.bw, self.bh = bw, bh
        self.cx, self.cy = iw / 2, ih / 2
        self.iw, self.ih = iw, ih
        sentido = 1 if n % 2 else -1       # alterna acercar / alejar y la dirección del paneo
        self.z0, self.z1 = (1.0, 1.09) if sentido > 0 else (1.09, 1.0)
        self.dx = sentido * 0.025 * iw
        self.dy = (-1 if n % 3 == 0 else 1) * 0.015 * ih
        self.dur = 1.0

    def frame(self, t, dur):
        k = min(max(t / max(dur, 0.01), 0.0), 1.0)
        k = k * k * (3 - 2 * k)
        z = self.z0 + (self.z1 - self.z0) * k
        bw, bh = self.bw / z, self.bh / z
        cx = self.cx + self.dx * (k - 0.5)
        cy = self.cy + self.dy * (k - 0.5)
        x0 = min(max(cx - bw / 2, 0), self.iw - bw)
        y0 = min(max(cy - bh / 2, 0), self.ih - bh)
        out = self.im.resize((self.W, self.H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh))
        return np.asarray(out)


class Clip:
    """Escena de video animado (se lee en orden; el audio de Leonardo se descarta)."""

    def __init__(self, n, W, H):
        self.W, self.H = W, H
        self.c = av.open(str(ESCENAS / f"escena_{n:02d}_animada.mp4"))
        s = self.c.streams.video[0]
        self.len = float(s.duration * s.time_base) if s.duration else 6.5
        self.gen = self.c.decode(s)
        self.ult = None
        self.pos = -1.0
        self.img = Image.new("RGB", (W, H))
        self.fps = float(s.average_rate)

    def frame(self, t, dur):
        # estira hasta 1.45x más lento; si la escena dura más, se congela el último fotograma
        vel = max(0.69, min(1.0, self.len / dur)) if dur > self.len else 1.0
        objetivo = min(t * vel, self.len - 1 / self.fps)
        while self.pos < objetivo:
            try:
                f = next(self.gen)
            except StopIteration:
                break
            self.pos = float(f.pts * f.time_base)
            self.ult = f
        f = self.ult.reformat(width=self.W, height=self.H, format="rgb24")
        return f.to_ndarray()

    def cerrar(self):
        self.c.close()


# ---------------------------------------------------------------- títulos
def hacer_titulo(tit, sub, W, H):
    s = H / 1080
    ft, fs = ImageFont.truetype(FUENTE_TITULO, int(96 * s)), ImageFont.truetype(FUENTE_SUB, int(40 * s))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x, y = int(90 * s), int(H - 250 * s)
    tw = max(d.textlength(tit, font=ft), d.textlength(sub, font=fs))
    d.rectangle((x - 30 * s, y - 20 * s, x + tw + 50 * s, y + 175 * s), fill=(0, 0, 0, 170))
    d.rectangle((x - 30 * s, y - 20 * s, x - 18 * s, y + 175 * s), fill=(212, 160, 23, 255))
    d.text((x, y), tit, font=ft, fill=(255, 255, 255, 255))
    d.text((x + 4 * s, y + 112 * s), sub, font=fs, fill=(212, 160, 23, 255))
    return np.asarray(img).astype(np.float32)


def alfa_titulo(t, t0, dur=3.2):
    r = t - t0
    if r < 0 or r > dur: return 0.0
    return min(1.0, r / 0.4, (dur - r) / 0.5)


# ---------------------------------------------------------------- audio
def audio_frames(duracion):
    """Genera fotogramas AAC: la locución real si existe, si no silencio."""
    rate = 48000
    if LOCUCION.exists():
        c = av.open(str(LOCUCION))
        rs = av.AudioResampler(format="s16", layout="mono", rate=rate)
        for f in c.decode(audio=0):
            for g in rs.resample(f):
                yield g
        for g in rs.resample(None):
            yield g
        return
    n = 0
    while n < duracion * rate:
        f = av.AudioFrame.from_ndarray(np.zeros((1, 1024), dtype=np.int16), format="s16", layout="mono")
        f.sample_rate = rate
        yield f
        n += 1024


# ---------------------------------------------------------------- transcripción
def transcribir():
    if not LOCUCION.exists():
        sys.exit(f"Falta {LOCUCION.name} (generala con ElevenLabs primero).")
    from faster_whisper import WhisperModel
    BUILD.mkdir(exist_ok=True)
    modelo = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = modelo.transcribe(str(LOCUCION), language="es", word_timestamps=True)
    pal = [{"w": " ".join(norm(w.word)), "start": w.start, "end": w.end}
           for s in segs for w in s.words if norm(w.word)]
    TRANSCRIPCION.write_text(json.dumps(pal, ensure_ascii=False))
    print(len(pal), "palabras ->", TRANSCRIPCION)


# ---------------------------------------------------------------- render
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiempos", action="store_true")
    ap.add_argument("--transcribir", action="store_true")
    ap.add_argument("--capitulos", action="store_true", help="imprime los capítulos para la descripción de YouTube")
    ap.add_argument("--max", type=float, default=0, help="renderizar solo los primeros N segundos")
    a = ap.parse_args()
    if a.transcribir:
        return transcribir()

    real = LOCUCION.exists() and TRANSCRIPCION.exists()
    palabras = json.loads(TRANSCRIPCION.read_text()) if real else palabras_estimadas()
    if real:   # la transcripción trae palabras sueltas; se unen las que Whisper parte en varias
        palabras = [{"w": w, "start": p["start"], "end": p["end"]} for p in palabras for w in p["w"].split()]
    inicios, fin, titulos = tiempos(palabras)
    if a.capitulos:
        marcas = [(0, "El poder no se hereda"), (inicios[6], "Fase Uno: El barro y la sangre"),
                  (inicios[21], "Fase Dos: La oportunidad de oro"), (inicios[37], "Fase Tres: El tejedor de hilos"),
                  (inicios[46], "Fase Cuatro: El jaque mate"), (inicios[56], "La cima y su precio"),
                  (inicios[63], "¿Y vos qué elegirías?")]
        for t, nombre in marcas:
            print(f"{int(t // 60)}:{int(t % 60):02d} {nombre}")
        return
    if a.tiempos:
        print("modo:", "real" if real else "prueba (estimado por caracteres)")
        for n in range(1, TOTAL + 1):
            sig = inicios[n + 1] if n < TOTAL else fin
            print(f"escena {n:02d}  {inicios[n]:7.1f}s  dura {sig - inicios[n]:5.1f}s  «{ANCLAS[n]}»")
        print(f"fin: {fin:.1f}s ({fin / 60:.2f} min)")
        return

    W, H = (1920, 1080) if real else (960, 540)
    salida = BASE / ("video_final.mp4" if real else "video_prueba.mp4")
    total = min(fin, a.max) if a.max else fin
    print(f"{'real' if real else 'prueba'}: {total:.1f}s a {W}x{H} -> {salida.name}")

    out = av.open(str(salida), "w")
    v = out.add_stream("libx264", rate=FPS)
    v.width, v.height, v.pix_fmt = W, H, "yuv420p"
    v.options = {"crf": "20" if real else "26", "preset": "medium" if real else "veryfast"}
    au = out.add_stream("aac", rate=48000)
    au.layout = "mono"
    audio = audio_frames(total)
    audio_t, pts_a = 0.0, 0

    imgs = {}                        # escenas ya preparadas (se liberan al pasar)
    cartel = [(tit, sub, t0, hacer_titulo(tit, sub, W, H)) for tit, sub, t0 in titulos]
    nf = int(total * FPS)
    for i in range(nf):
        t = i / FPS
        n = max(k for k in inicios if inicios[k] <= t)
        def escena(k):
            if k not in imgs:
                for old in [o for o in imgs if o < k - 1]:
                    getattr(imgs.pop(old), "cerrar", lambda: None)()
                imgs[k] = Clip(k, W, H) if k in ESCENAS_VIDEO else Imagen(k, W, H)
            return imgs[k]
        fin_n = inicios[n + 1] if n < TOTAL else fin
        fr = escena(n).frame(t - inicios[n], fin_n - inicios[n]).astype(np.float32)
        # fundido desde la escena anterior
        if n > 1 and t - inicios[n] < FUNDIDO:
            k = (t - inicios[n]) / FUNDIDO
            ant = escena(n - 1)
            fr_ant = ant.frame(t - inicios[n - 1], inicios[n] - inicios[n - 1]).astype(np.float32)
            fr = fr_ant * (1 - k) + fr * k
        for tit, sub, t0, rgba in cartel:
            al = alfa_titulo(t, t0)
            if al > 0:
                m = rgba[..., 3:4] / 255.0 * al
                fr = fr * (1 - m) + rgba[..., :3] * m
        frame = av.VideoFrame.from_ndarray(np.clip(fr, 0, 255).astype(np.uint8), format="rgb24")
        for p in v.encode(frame.reformat(format="yuv420p")):
            out.mux(p)
        # audio hasta el instante actual
        while audio_t < t + 1.0:
            try:
                f = next(audio)
            except StopIteration:
                break
            f.pts = pts_a
            f.time_base = Fraction(1, 48000)
            pts_a += f.samples
            audio_t = pts_a / 48000
            for p in au.encode(f):
                out.mux(p)
        if i % (FPS * 30) == 0:
            print(f"  {t:6.1f}s / {total:.1f}s (escena {n:02d})", flush=True)
    for p in v.encode():
        out.mux(p)
    for p in au.encode():
        out.mux(p)
    out.close()
    print("listo:", salida, f"({salida.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
