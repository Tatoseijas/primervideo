#!/usr/bin/env python3
"""Corta Shorts verticales (1080x1920) de video_final.mp4 con subtítulos palabra a palabra.

Cada Short toma uno o más tramos del video (en segundos de la narración), los pone sobre un
fondo desenfocado del mismo video, con un título fijo arriba y subtítulos grandes abajo
(sacados de _build/transcripcion.json).

Uso:
    python3 armar_shorts.py            # renderiza todos
    python3 armar_shorts.py mundial    # solo los que se nombren
"""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
BUILD = BASE / "_build"
ORIGEN = BASE / "video_final.mp4"
SALIDA = BASE / "shorts"

ANCHO, ALTO, FPS = 1080, 1920, 30
ALTO_VIDEO = round(ANCHO * 9 / 16)  # 608: el video horizontal entra entero a lo ancho
Y_VIDEO = (ALTO - ALTO_VIDEO) // 2

SHORTS = {
    "billete_falso": {
        "titulo": "VIAJÉ A 2010\nCON 10 DÓLARES",
        "tramos": [(0.0, 11.1), (44.3, 65.4)],
    },
    "mundial": {
        "titulo": "ADIVINÉ EL\nMUNDIAL 2010",
        "tramos": [(136.2, 195.0)],
    },
    "bitcoin_gratis": {
        "titulo": "BITCOINS GRATIS\nEN 2010",
        "tramos": [(232.4, 271.0)],
    },
    "volvi_millonario": {
        "titulo": "VOLVÍ DE 2010\nMILLONARIO",
        "tramos": [(365.4, 411.6)],
    },
    "celular_en_2010": {
        "titulo": "LLEVÉ MI CELULAR\nA 2010",
        "tramos": [(84.0, 132.0)],
    },
    "binance_en_2010": {
        "titulo": "BUSQUÉ BINANCE\nEN 2010",
        "tramos": [(195.0, 228.9)],
    },
    "traer_bitcoins": {
        "titulo": "¿CÓMO TRAES TUS\nBITCOINS DE 2010?",
        "tramos": [(313.1, 365.3)],
    },
}

# errores de Whisper que no pueden salir escritos en pantalla
CORRECCIONES = {"Anderson.": "Andresen.", "inalámbicos.": "inalámbricos.", "olora": "olor a",
                "ha": "", "puesto": "apuesto", "Mt.": "Mt"}
PALABRAS_POR_GRUPO = 3


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"Falló: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def duracion(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", p]).strip())


def palabras_en(tramos):
    """Palabras de la narración que caen en los tramos, con tiempos ya pasados al Short."""
    todas = [w for s in json.loads((BUILD / "transcripcion.json").read_text()) for w in s["palabras"]]
    out, offset = [], 0.0
    for a, b in tramos:
        for w in todas:
            if a <= w["t0"] < b:
                texto = CORRECCIONES.get(w["w"], w["w"])
                if not texto:
                    continue
                out.append((texto, offset + w["t0"] - a, offset + min(w["t1"], b) - a))
        offset += b - a
    return out


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def escribir_ass(destino, titulo, palabras, total):
    # grupos cortos; corta antes si hay pausa o termina una frase
    grupos, actual = [], []
    for i, w in enumerate(palabras):
        actual.append(w)
        siguiente = palabras[i + 1] if i + 1 < len(palabras) else None
        fin_frase = w[0][-1] in ".?!,"
        if len(actual) == PALABRAS_POR_GRUPO or fin_frase or not siguiente or siguiente[1] - w[2] > 0.4:
            grupos.append(actual)
            actual = []

    y_sub = Y_VIDEO + ALTO_VIDEO + 230
    lineas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {ANCHO}", f"PlayResY: {ALTO}",
        "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # colores en &HAABBGGRR: título amarillo, subtítulos blancos con borde negro grueso
        "Style: Titulo,DejaVu Sans,96,&H0000D7FF,&H0000D7FF,&H00000000,&H96000000,"
        "-1,0,0,0,100,100,0,0,1,7,4,8,40,40,250,1",
        "Style: Sub,DejaVu Sans,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,"
        "-1,0,0,0,100,100,0,0,1,7,4,5,60,60,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,{ts(0)},{ts(total)},Titulo,,0,0,0,," + titulo.replace("\n", "\\N"),
    ]
    for i, g in enumerate(grupos):
        ini = g[0][1]
        fin = grupos[i + 1][0][1] if i + 1 < len(grupos) else total
        fin = min(fin, g[-1][2] + 0.6)  # no dejar el texto colgado en los silencios
        texto = " ".join(w[0] for w in g).upper().rstrip(".,")
        # la palabra que entra "salta" un poco: arranca al 115% y baja al 100%
        efecto = f"{{\\pos({ANCHO // 2},{y_sub})\\fscx115\\fscy115\\t(0,120,\\fscx100\\fscy100)}}"
        lineas.append(f"Dialogue: 1,{ts(ini)},{ts(fin)},Sub,,0,0,0,,{efecto}{texto}")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def armar(nombre, cfg):
    tramos = cfg["tramos"]
    total = sum(b - a for a, b in tramos)
    ass = BUILD / f"short_{nombre}.ass"
    escribir_ass(ass, cfg["titulo"], palabras_en(tramos), total)

    partes, etiquetas = [], []
    for i, (a, b) in enumerate(tramos):
        partes.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];"
                      f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,"
                      f"afade=t=in:d=0.04,afade=t=out:st={b - a - 0.06:.2f}:d=0.06[a{i}];")
        etiquetas.append(f"[v{i}][a{i}]")
    filtro = (
        "".join(partes)
        + f"{''.join(etiquetas)}concat=n={len(tramos)}:v=1:a=1[v][a];"
        + "[v]split[f][p];"
        + f"[f]scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},"
          "gblur=sigma=40,eq=brightness=-0.18[fondo];"
        + f"[p]scale={ANCHO}:{ALTO_VIDEO}[frente];"
        + f"[fondo][frente]overlay=0:{Y_VIDEO},ass={ass.name},setsar=1,fps={FPS}[out]"
    )
    destino = SALIDA / f"short_{nombre}.mp4"
    # cwd=BUILD: el filtro ass recibe un nombre simple, sin la @ ni los puntos de la ruta absoluta
    run(["ffmpeg", "-v", "error", "-y", "-i", ORIGEN, "-filter_complex", filtro,
         "-map", "[out]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", destino],
        cwd=BUILD)
    print(f"  {destino.name}: {duracion(destino):.1f}s (esperado {total:.1f}s)")


def main():
    pedidos = sys.argv[1:] or list(SHORTS)
    desconocidos = [n for n in pedidos if n not in SHORTS]
    if desconocidos:
        sys.exit(f"No existen: {', '.join(desconocidos)}. Opciones: {', '.join(SHORTS)}")
    SALIDA.mkdir(exist_ok=True)
    for n in pedidos:
        armar(n, SHORTS[n])
    print(f"LISTO: {len(pedidos)} Shorts en {SALIDA}")


if __name__ == "__main__":
    main()
