#!/usr/bin/env python3
"""Transcribe las voces (1.mp3 ... 5.mp3) con marcas de tiempo por palabra.

Une las pistas en orden y guarda:
  _build/narracion.wav       pista única de voz (la que lleva el video final)
  _build/transcripcion.json  segmentos y palabras con tiempos globales
  _build/transcripcion.txt   versión legible con timestamps
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

BASE = Path(__file__).resolve().parent
VOCES = Path.home() / "Descargas" / "voces video"
BUILD = BASE / "_build"


def duracion(p):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", p]))


def main():
    BUILD.mkdir(exist_ok=True)
    pistas = sorted(VOCES.glob("*.mp3"), key=lambda p: int(p.stem))
    if not pistas:
        sys.exit(f"No hay mp3 en {VOCES}")

    lista = BUILD / "voces.txt"
    lista.write_text("".join(f"file '{p}'\n" for p in pistas))
    narracion = BUILD / "narracion.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista,
                    "-ar", "48000", "-ac", "1", narracion], check=True)

    modelo = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=12)
    salida, offset = [], 0.0
    for p in pistas:
        # se decodifica con ffmpeg (16 kHz mono) para no depender de PyAV
        pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le",
                                       "-ac", "1", "-ar", "16000", "-"])
        audio = np.frombuffer(pcm, dtype=np.float32)
        segs, _ = modelo.transcribe(audio, language="es", word_timestamps=True, vad_filter=True,
                                    beam_size=5)
        for s in segs:
            salida.append({
                "pista": int(p.stem),
                "inicio": round(offset + s.start, 2),
                "fin": round(offset + s.end, 2),
                "texto": s.text.strip(),
                "palabras": [{"w": w.word.strip(), "t0": round(offset + w.start, 2),
                              "t1": round(offset + w.end, 2)} for w in s.words],
            })
        print(f"pista {p.name}: {duracion(p):.1f}s transcrita", flush=True)
        offset += duracion(p)

    (BUILD / "transcripcion.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    with open(BUILD / "transcripcion.txt", "w") as f:
        for s in salida:
            f.write(f"[{s['inicio']:7.2f} - {s['fin']:7.2f}] (v{s['pista']}) {s['texto']}\n")
    print(f"Total narración: {offset:.2f}s — {len(salida)} segmentos")


if __name__ == "__main__":
    main()
