#!/usr/bin/env python3
"""Genera la locución de guion_presidente.txt con ElevenLabs (voz Adam, eleven_turbo_v2_5).

El guion se parte por párrafos en tramos de hasta MAX_CHARS caracteres; cada tramo se pide por
separado pasando el texto vecino (previous_text / next_text) para que la entonación sea continua,
y al final se unen con ffmpeg en locucion_presidente.mp3.

La API key se lee de la variable ELEVENLABS_API_KEY o del archivo .env de esta carpeta.

Uso:
    python3 generar_locucion.py            # genera todo
    python3 generar_locucion.py --dry-run  # solo muestra cómo queda dividido y cuántos caracteres gasta
"""
import os
import subprocess
import sys
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
GUION = BASE / "guion_presidente.txt"
SALIDA = BASE / "locucion_presidente.mp3"
TMP = BASE / "_tts"

VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam
MODELO = "eleven_turbo_v2_5"
MAX_CHARS = 2500  # holgado frente al límite por pedido; tramos cortos fallan menos
URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"


def api_key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    env = BASE / ".env"
    if env.exists():
        for linea in env.read_text().splitlines():
            if linea.startswith("ELEVENLABS_API_KEY="):
                return linea.split("=", 1)[1].strip()
    sys.exit("Falta ELEVENLABS_API_KEY (variable de entorno o .env en esta carpeta).")


def tramos(texto):
    """Agrupa párrafos consecutivos sin pasar MAX_CHARS; un párrafo más largo se corta por oraciones."""
    parrafos = [p.strip() for p in texto.replace("\r", "").split("\n\n") if p.strip()]
    piezas = []
    for p in parrafos:
        if len(p) <= MAX_CHARS:
            piezas.append(p)
            continue
        actual = ""
        for oracion in p.replace(". ", ".\n").split("\n"):
            if actual and len(actual) + len(oracion) + 1 > MAX_CHARS:
                piezas.append(actual)
                actual = oracion
            else:
                actual = f"{actual} {oracion}".strip()
        if actual:
            piezas.append(actual)

    out, actual = [], ""
    for p in piezas:
        if actual and len(actual) + len(p) + 2 > MAX_CHARS:
            out.append(actual)
            actual = p
        else:
            actual = f"{actual}\n\n{p}".strip()
    if actual:
        out.append(actual)
    return out


def sintetizar(texto, previo, siguiente, destino, key):
    r = requests.post(
        URL,
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        json={
            "text": texto,
            "model_id": MODELO,
            "previous_text": previo or None,
            "next_text": siguiente or None,
            "voice_settings": {"stability": 0.3, "similarity_boost": 0.75, "style": 0.45,
                               "use_speaker_boost": True},
        },
        timeout=300,
    )
    if r.status_code != 200:
        sys.exit(f"ElevenLabs respondió {r.status_code}: {r.text[:500]}")
    destino.write_bytes(r.content)


def main():
    if not GUION.exists():
        sys.exit(f"No encuentro {GUION}")
    partes = tramos(GUION.read_text(encoding="utf-8"))
    total = sum(len(p) for p in partes)
    print(f"{len(partes)} tramos, {total} caracteres en total")
    for i, p in enumerate(partes, 1):
        print(f"  tramo {i}: {len(p)} caracteres — «{p[:60]}…»")
    if "--dry-run" in sys.argv:
        return

    key = api_key()
    TMP.mkdir(exist_ok=True)
    archivos = []
    for i, p in enumerate(partes):
        destino = TMP / f"tramo_{i + 1:02d}.mp3"
        if not destino.exists() or destino.stat().st_size == 0:  # permite reanudar si se corta
            previo = partes[i - 1][-300:] if i > 0 else ""
            siguiente = partes[i + 1][:300] if i + 1 < len(partes) else ""
            sintetizar(p, previo, siguiente, destino, key)
        archivos.append(destino)
        print(f"  ok {destino.name}")

    lista = TMP / "lista.txt"
    lista.write_text("".join(f"file '{a.name}'\n" for a in archivos))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista.name,
                    "-c", "copy", SALIDA], check=True, cwd=TMP)
    dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", SALIDA], text=True).strip()
    print(f"LISTO: {SALIDA} — {float(dur):.1f} s")


if __name__ == "__main__":
    main()
