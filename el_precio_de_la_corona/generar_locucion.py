#!/usr/bin/env python3
"""Genera la locución de "El precio de la corona" con ElevenLabs, POR PARTES (una por fase del guion).

Cada parte sale de parte0_intro.txt ... parte4_fase4.txt y se guarda en _tts/parteN.mp3. Las partes ya
generadas no se vuelven a pedir (no gasta créditos de más) y, cuando están las 5, se unen en
locucion_mafia.mp3, que es lo que lee armar_video.py. No necesita ffmpeg.

Misma voz y modelo que el video 2 (Adam, eleven_turbo_v2_5). En turbo cuesta 1 crédito por carácter
(el plan Free trae 10.000 por mes). Antes de gastar compara el costo con el saldo de la cuenta.

La API key se lee de ELEVENLABS_API_KEY o de un archivo .env (en esta carpeta o en la raíz del repo).

Uso:
    python3 generar_locucion.py --creditos        # muestra saldo y costo de cada parte
    python3 generar_locucion.py --dry-run         # igual, sin pedir nada
    python3 generar_locucion.py --parte 0 1       # genera solo esas partes
    python3 generar_locucion.py                   # genera todas las que falten
    python3 generar_locucion.py --forzar          # ignora el chequeo de créditos
"""
import argparse
import os
import sys
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
TMP = BASE / "_tts"
SALIDA = BASE / "locucion_mafia.mp3"

VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam (la misma del video 2)
MODELO = "eleven_turbo_v2_5"
URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

PARTES = ["parte0_intro", "parte1_fase1", "parte2_fase2", "parte3_fase3", "parte4_fase4"]

# Ajustes sugeridos para cada tramo (stability más alta = más fría y pareja; style = más expresiva)
AJUSTES = {
    0: {"stability": 0.60, "style": 0.15},   # intro: íntima, pausada
    1: {"stability": 0.70, "style": 0.05},   # Fase Uno: fría y descriptiva
    2: {"stability": 0.50, "style": 0.20},   # Fase Dos: persuasiva, calculadora
    3: {"stability": 0.50, "style": 0.20},   # Fase Tres: elegante pero amenazante
    4: {"stability": 0.55, "style": 0.15},   # Fase Cuatro y cierre: gélida, luego reflexiva
}


def api_key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    for carpeta in (BASE, BASE.parent):
        env = carpeta / ".env"
        if env.exists():
            for linea in env.read_text().splitlines():
                if linea.startswith("ELEVENLABS_API_KEY="):
                    return linea.split("=", 1)[1].strip()
    sys.exit("Falta ELEVENLABS_API_KEY (variable de entorno o archivo .env).")


def texto(i):
    return (BASE / f"{PARTES[i]}.txt").read_text(encoding="utf-8").strip()


def saldo(key):
    """-> (usados, limite) o None si la key no tiene permiso de lectura de la suscripción."""
    r = requests.get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key}, timeout=30)
    if r.status_code != 200:
        return None
    d = r.json()
    return d["character_count"], d["character_limit"]


def sintetizar(i, previo, siguiente, destino, key):
    r = requests.post(
        URL,
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        json={
            "text": texto(i),
            "model_id": MODELO,
            "previous_text": previo or None,      # da continuidad de entonación entre partes
            "next_text": siguiente or None,
            "voice_settings": {"similarity_boost": 0.75, "use_speaker_boost": True, **AJUSTES[i]},
        },
        timeout=300,
    )
    if r.status_code != 200:
        sys.exit(f"ElevenLabs respondió {r.status_code}: {r.text[:500]}")
    destino.write_bytes(r.content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parte", type=int, nargs="*", help="números de parte a generar (0 a 4)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--creditos", action="store_true")
    ap.add_argument("--forzar", action="store_true")
    a = ap.parse_args()

    elegidas = a.parte if a.parte else list(range(len(PARTES)))
    hechas = {i: (TMP / f"parte{i}.mp3").exists() and (TMP / f"parte{i}.mp3").stat().st_size > 0
              for i in range(len(PARTES))}
    for i in range(len(PARTES)):
        print(f"parte {i}: {len(texto(i)):5d} caracteres  {'(ya generada)' if hechas[i] else ''}  {PARTES[i]}")
    pendientes = [i for i in elegidas if not hechas[i]]
    costo = sum(len(texto(i)) for i in pendientes)
    print(f"a generar: partes {pendientes or 'ninguna'} = {costo} créditos")

    if a.dry_run and not a.creditos:
        return
    key = api_key()
    s = saldo(key)
    if s:
        print(f"saldo: {s[1] - s[0]} créditos libres ({s[0]} usados de {s[1]})")
    else:
        print("no pude leer el saldo (la key no tiene permiso de suscripción); sigo sin chequear")
    if a.dry_run or a.creditos:
        return
    if s and costo > s[1] - s[0] and not a.forzar:
        sys.exit(f"No alcanzan los créditos ({costo} > {s[1] - s[0]}). Generá una parte más corta con "
                 f"--parte N, esperá el reinicio mensual o usá --forzar.")

    TMP.mkdir(exist_ok=True)
    for i in pendientes:
        previo = texto(i - 1)[-300:] if i > 0 else ""
        siguiente = texto(i + 1)[:300] if i + 1 < len(PARTES) else ""
        destino = TMP / f"parte{i}.mp3"
        sintetizar(i, previo, siguiente, destino, key)
        print(f"  ok {destino.name} ({destino.stat().st_size // 1024} KB)")

    if all((TMP / f"parte{i}.mp3").exists() for i in range(len(PARTES))):
        # los mp3 del mismo formato (mp3_44100_128) se pueden unir byte a byte
        SALIDA.write_bytes(b"".join((TMP / f"parte{i}.mp3").read_bytes() for i in range(len(PARTES))))
        print(f"LISTO: {SALIDA.name} — ahora: python3 armar_video.py --transcribir")
    else:
        faltan = [i for i in range(len(PARTES)) if not (TMP / f"parte{i}.mp3").exists()]
        print(f"faltan las partes {faltan}; cuando estén todas se arma {SALIDA.name}")


if __name__ == "__main__":
    main()
