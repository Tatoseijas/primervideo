# CONTEXTO DEL PROYECTO — canal «En Caso De...» (YouTube)

> Este archivo existe para retomar el trabajo desde **cualquier computadora**. La memoria de Claude Code es local a
> cada máquina y no viaja; todo lo importante está acá. **Al empezar en otra compu, pedile a Claude:
> «Leé CONTEXTO.md y seguí con los pendientes de la sección 9».** Última actualización: 2026-10-29.

---

## 1. Qué es el proyecto

Videos animados de "escenarios hipotéticos" para YouTube, en español rioplatense (voseo en el último video).
Cada video se hace así: **guion → escenas de imagen en Leonardo.ai (estilo cómic 2D, personaje fijo) →
locución con ElevenLabs → armado del video con scripts de Python → portada + textos + shorts.**

- **Canal:** https://www.youtube.com/@EnElCasoDe — nombre «En Caso De...», descripción «El canal oficial de los
  escenarios hipotéticos. 🎬». A 2026-10-29: 9 suscriptores, 8 videos. El video de 2010 (6:54) llevaba 988 vistas.
- **Repo:** `git@github.com:Tatoseijas/primervideo.git`, rama `main` (se commitea directo en `main`).
  Autores en el historial: Luca Seijas / Tatoseijas (dueño), Matias Faya, Franco Marotta.
- **Protagonista:** un personaje de cómic fijo (joven despeinado, pelo castaño, barba corta, **buzo verde oliva,
  mochila azul oscura con dos correas**, jean). Hoja de referencia: `personajereference.jpg` (copia en cada carpeta
  de video). En la historia de la mafia el personaje (Dante) cambia de ropa: chaqueta oscura sobre el buzo y,
  al final, traje gris carbón con el pelo peinado hacia atrás.

## 2. Los tres videos

| # | Carpeta | Tema | Estado |
|---|---|---|---|
| 1 | `primervideow/` | «¿Qué harías si aparecés en 2010 con $10?» (Bitcoin). 68 escenas, 3 videos animados, 7 shorts | **Publicado** (6:54) |
| 2 | `segundo_video/` | «Presidente de EE. UU. por 24 horas» (Oficina Oval). 72 escenas (+5 animadas), locución de 5:41 | Terminado según el commit «termianndo el 2do video». **No hay script de armado ni video final en el repo** (se armó fuera). No sé si se subió a YouTube. |
| 3 | `el_precio_de_la_corona/` | «El precio de la corona: de los callejones a la cima de la mafia» (guion de ChatGPT, adaptado). 63 escenas + 5 animadas | **Todo listo salvo la voz y el render final** (ver sección 9) |

## 3. Herramientas y cuentas (sin credenciales; **nunca** commitear claves: `.env` está en `.gitignore`)

- **Leonardo.ai** (web, sesión ya iniciada en el navegador): se usa por la interfaz con la extensión *Claude in
  Chrome*. Saldo al 2026-10-29: **17.502 créditos** (se empezó la sesión con ~20.600).
- **ElevenLabs** (plan **Free**): 10.000 créditos/mes, **9.403 usados → quedan ~597** hasta el reinicio mensual.
  En el modelo turbo cuesta **1 crédito por carácter**. API key en la variable `ELEVENLABS_API_KEY` o en un `.env`.
  Voz usada en el video 2 y en el script del video 3: **Adam** (`voice_id pNInz6obpgDQGcFmaJgB`, modelo
  `eleven_turbo_v2_5`). *Ojo: el usuario habló de «mi personaje que ya está en ElevenLabs»; si es una voz propia
  distinta de Adam, cambiar `VOICE_ID` en `generar_locucion.py`.*
- **Claude Code + extensión Claude in Chrome**: la usé con el Chromium de Linux. Si hay varios navegadores
  conectados, Claude pregunta cuál usar (elegir el que tiene las sesiones de Leonardo/ElevenLabs/YouTube).
- **GitHub:** push por SSH a `main`.

## 4. Preferencias del usuario (importante)

- Idioma: español rioplatense; el guion del video 3 está en **voseo** (imaginá, sos, tenés, vos).
- **Trabajar «por partes»** (por fases del guion): hacerlo todo de una vez sale más caro en créditos.
  Después de cada parte: descargar, revisar con hojas de contactos y reportar el gasto antes de seguir.
- Gastar créditos, publicar o hacer push **solo con visto bueno** del usuario. Nombrar las carpetas con el
  **nombre del video**, no «video N».
- El video debe durar **mínimo 6 minutos**. La locución tiene que caber en los créditos de ElevenLabs
  (por eso se genera por partes y se chequea el saldo).

## 5. Estructura del repo

```
CONTEXTO.md                 este archivo
primervideow/               video 1 (scripts con ffmpeg: armar_video*.py, transcribir.py, armar_shorts.py)
segundo_video/              video 2 (generar_locucion.py con ffmpeg, guion*, prompts, urls+bajar.sh)
el_precio_de_la_corona/     video 3 (todo lo nuevo; scripts SIN ffmpeg)
  guion_mafia.txt             guion completo limpio, 6.554 car., ~8 min (voseo)
  parte0_intro.txt … parte4_fase4.txt   el guion partido por fases (cada parte = una tanda de voz)
  prompts_mafia.json          63 prompts de Leonardo (reflejan lo realmente enviado)
  salida_mafia/               escena_01..63.jpg + escena_01..05_animada.mp4 (+2 descartes, ver 7)
  generar_locucion.py         voz con ElevenLabs por partes (chequea saldo)
  armar_video.py              render del video (prueba sin voz / real con voz)
  portada.py, portada_base.jpg, portada_mafia.jpg   miniatura 1280×720
  textos_youtube.md           título, descripción, capítulos, etiquetas, textos de shorts
  video_prueba.mp4            borrador 960×540 sin voz (7:45)
  _gen_prompts.py             generó prompts_mafia.json (referencia; el json es la fuente de verdad)
```

## 6. Montar el entorno en otra computadora

```bash
git clone git@github.com:Tatoseijas/primervideo.git && cd primervideo
python3 -m venv .venv2 && . .venv2/bin/activate        # (el .venv del repo es de Linux/Python 3.12; mejor uno propio)
pip install av pillow numpy requests faster-whisper     # faster-whisper solo para --transcribir
```
- Los scripts del video 3 usan **PyAV** (trae libx264 y aac) y **no necesitan ffmpeg**. Los scripts de los
  videos 1 y 2 sí lo necesitan (`ffmpeg`/`ffprobe` en el PATH).
- Fuentes: `armar_video.py` y `portada.py` usan **Noto Sans** en `/usr/share/fonts/truetype/noto/`
  (`NotoSansDisplay-ExtraCondensedBlack.ttf`, `NotoSans-SemiBold.ttf`, `NotoSans-Bold.ttf`). En Windows/Mac,
  cambiar esas rutas por fuentes instaladas (o instalar Noto).
- Clave de ElevenLabs: `export ELEVENLABS_API_KEY=...` o un `.env` con `ELEVENLABS_API_KEY=...` (no se commitea).
- Sacar de git el `.venv/` versionado sería una buena limpieza (hoy está trackeado por error).

## 7. Video 3 «El precio de la corona» — estado detallado

**Historia:** Dante, un «perro de cobro» sin glamour que observa y ahorra, sube en cuatro fases: *Fase Uno: El barro y
la sangre* → *Fase Dos: La oportunidad de oro* (salva al cartel de un bloqueo aduanero con triangulación financiera,
sin balas) → *Fase Tres: El tejedor de hilos* (compra jueces y políticos; el Don se vuelve errático) → *Fase Cuatro:
El jaque mate* (filtra los diarios del Don a los federales y toma el mando sin disparar). Cierre: la paranoia de la
cima, y un joven silencioso en el callejón mirando la torre. Remata con una pregunta al público.

**Escenas (63) por fase** — el orden sigue el guion:
- 1–5 intro (trono vacío, corona que cambia de manos, skyline, jefe en sombras, figura en el callejón) → **tienen video animado**.
- 6–21 Fase Uno · 22–36 Fase Dos · 37–45 Fase Tres · 46–63 Fase Cuatro y cierre.
- Dante con buzo verde en fases 1–2 (chaqueta oscura/de cuero encima en 22–36), traje desde la 37. Las escenas 60, 61 y 63
  usan al joven del buzo (eco del inicio).

**Hecho:** guion, 63 imágenes, 5 animaciones, prompts, `armar_video.py` (probado: renderizó 465 s completos en
modo prueba), portada, textos de YouTube, `generar_locucion.py` (solo probado con `--dry-run`).

**Imperfecciones conocidas de las imágenes** (aceptadas; no hace falta rehacer):
- Escena 7: carteles con texto legible («Broken Spoke Tavern»). Escena 23: nombre «Malachi» grabado en la bala.
- Escena 18: pelo de Dante algo más oscuro. La chaqueta de Dante cambia entre escenas 22–36 (verde, oscura, cuero).
- Franjas negras arriba/abajo en varias (15, 22, 24, 25, 26, 35, 49, 50, 52, 62): `armar_video.py` las recorta solo.
- `escena_25_logo_apple.jpg` (descartada: tenía logo de Apple; la buena es `escena_25.jpg`) y
  `escena_41_marco.jpg` (original con marco crema; `escena_41.jpg` ya está recortada). Se pueden borrar.
- Escena 3: la primera versión (vista aérea) se descartó; la buena es el skyline desde un techo.
- Escenas largas en pantalla (con la misma imagen 18–20 s): **46, 53 y 63**; si se quiere más dinamismo, generar 2–3
  imágenes extra y repartir anclas.

## 8. Cómo funciona cada script del video 3

**`generar_locucion.py`** — voz por partes.
`python3 generar_locucion.py --creditos` (saldo + costo de cada parte, no gasta nada) ·
`--parte 0 1` (genera solo esas) · sin argumentos (genera las que falten) · `--forzar` (ignora el chequeo).
Guarda `_tts/parteN.mp3` (no re-pide las ya hechas) y, con las 5, une todo en `locucion_mafia.mp3`.
Costos: parte0 498 · parte1 1.053 · parte2 1.555 · parte3 1.158 · parte4 2.281 = **6.545 créditos** en total.
Ajustes de voz por parte en `AJUSTES` (stability/style según el tono de cada fase).

**`armar_video.py`** — render con PyAV.
- Cada escena empieza en una **frase ancla** (`ANCLAS`, 63 entradas) del guion; los títulos de fase (`TITULOS`)
  aparecen con cartel cuando la voz los dice.
- Sin `locucion_mafia.mp3` + `_build/transcripcion.json` corre en **modo prueba**: tiempos por caracteres (13,7 car/s),
  audio en silencio, 960×540 → `video_prueba.mp4`. Con ambos, **modo real**: 1920×1080 → `video_final.mp4`.
- Opciones: `--tiempos` (tabla de tiempos) · `--max N` (solo los primeros N s) · `--capitulos` (capítulos para la
  descripción de YouTube con los tiempos de ese modo) · `--transcribir` (faster-whisper «small» sobre
  `locucion_mafia.mp3`; **la primera vez descarga el modelo de internet**).
- Ken Burns lento alternando zoom/paneo, recorte automático de franjas negras, fundido de 0,25 s, escenas 1–5 con
  el video animado (sin su audio; si la escena dura más, se enlentece hasta 1,45× y se congela el último fotograma).

**`portada.py`** — compone `portada_mafia.jpg` (1280×720) con «DE COBRADOR / A REY / DE LA MAFIA» + etiqueta roja
«SIN DISPARAR UN TIRO» sobre `portada_base.jpg` (imagen de Leonardo: Dante coronado, ciudad lluviosa, lado izquierdo vacío).

## 9. PENDIENTES (en orden)

1. **Voz (bloqueo):** esperar el reinicio mensual de ElevenLabs (o usar otra cuenta / plan Starter / otra voz: decisión
   del usuario). Luego `python3 generar_locucion.py --creditos` y generar **por partes** (primero la 0 y la 1, revisar
   el tono, seguir con las demás). No gastar si el saldo no alcanza.
2. `python3 armar_video.py --transcribir` (pedir visto bueno para descargar el modelo whisper) y revisar
   `python3 armar_video.py --tiempos`: corregir anclas si alguna escena quedó muy corta o larga.
3. `python3 armar_video.py` → `video_final.mp4` (1080p). Si pesa >100 MB, comprimirlo antes de subirlo al repo
   (GitHub rechaza archivos de más de 100 MB; el video 1 se comprimió por eso).
4. `python3 armar_video.py --capitulos` y pegar los capítulos reales en `textos_youtube.md`.
5. Opcional: shorts del video 3 (ideas de títulos en `textos_youtube.md`; el video 1 tiene `armar_shorts.py` como modelo),
   extras para las escenas largas (46, 53, 63), y portada alternativa.
6. Subir a YouTube (lo hace el usuario o con su OK): título/descripción/etiquetas de `textos_youtube.md`, portada
   `portada_mafia.jpg`. Ficción: la descripción ya incluye el aviso.
7. Para el video 2: decidir si hace falta un script de armado/portada/textos (no están en el repo).

## 10. Receta de Leonardo con Claude in Chrome (lo que costó descubrir)

- **Imágenes:** modelo **Nano Banana** (`gemini-2.5-flash-image`), 16:9 = 1344×768, **40 créditos** c/u.
  URL base: `https://app.leonardo.ai/generate?model=gemini-2.5-flash-image&aspectRatio=16:9&mode=fast&quantity=1`.
- **Referencia de personaje:** ícono de imagen del prompt → *Image Reference* → «Your Uploads» → `personajereference.jpg`.
  **Usarla solo en escenas con el personaje**; en escenas sin él copia la hoja de personaje (pasó con la escena 3).
  Se quita con la X de la miniatura (pasar el mouse por encima). Al recargar la página Leonardo restaura la última
  referencia/prompt: revisar siempre.
- **Estilo fijo al final de cada prompt:** `2D comic illustration, bold black outlines, flat cel shading, dark noir
  palette with deep blues and sodium-orange streetlight, cinematic lighting, 16:9, no text`. Descripción fija del
  personaje: «the young scruffy man with messy brown hair and a light beard, wearing a faded olive green hoodie and a
  dark backpack with double straps» (ver `_gen_prompts.py`).
- **Enter envía** el prompt. Entre envíos: subir el scroll y volver a clickear el campo (si el clic cae en una
  imagen, se abre el visor y los teclazos no llegan al prompt).
- **Glitch de tipeo:** a veces salen letras repetidas («textssss», «shwot»). Receta: `Ctrl+A`, `Delete`, esperar 2–3 s,
  reescribir y **verificar con captura antes de Enter**.
- **Moderación:** «public execution» fue rechazado (no cobra). Se reformuló a una plaza en pánico sin mostrar la
  ejecución. Evitar logos/marcas y texto en pantalla («no text, no logos»).
- **Video animado:** desde el visor de la imagen → *Create video* → modelo **MiniMax H3** (`hailuo-03`), 6 s, 16:9,
  Turbo, **90 créditos**; prompt de movimiento (push-in lento, lluvia, etc.). El mp4 trae audio propio (se descarta).
- **Descargar:** desde la página (`javascript_tool`) hacer `fetch` a `https://cdn.leonardo.ai/users/<id>/generations/
  <generationId>/<archivo>` y disparar un `<a download>`; el archivo cae en `~/Descargas` y se mueve a la carpeta.
  Los IDs de generación son cronológicos (ordenar por ID = orden de creación). Video 2 usó `urls_presidente.txt` + `bajar.sh` con `curl`.
- **Revisar** con hojas de contactos (PIL) antes de dar por buena una tanda.

## 11. Frase para retomar en otra compu

> «Leé `CONTEXTO.md`. Estamos con el video “El precio de la corona” en `el_precio_de_la_corona/`. Falta generar la
> voz con ElevenLabs por partes (`generar_locucion.py`), transcribir, renderizar con `armar_video.py` y subir.
> Primero decime cuántos créditos tengo en ElevenLabs y qué parte conviene generar.»
