#!/bin/bash
# Descarga a salida_presidente/ las escenas listadas en urls_presidente.txt que todavía no estén
cd "$(dirname "$0")"
U=https://cdn.leonardo.ai/users/7bf3feee-bf11-48c1-91b4-7fbe24cd022a/generations
while IFS='|' read -r n ruta; do
  f=salida_presidente/escena_$n.jpg
  [ -s "$f" ] || curl -sf -o "$f" "$U/$ruta" || echo "FALLÓ $n"
done < urls_presidente.txt
ls salida_presidente | wc -l
