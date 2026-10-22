# Medir el rendimiento con un recorrido

`--reporte <carpeta>` muestra de nuevo un reporte (fase 38). Si su `reporte.json` lleva `view.tour`, la cámara hace ese recorrido sobre una partida con el pueblo en pie y el juego anota lo que costó cada paso (fase 129, D-13004).

## Uso

1. Copiar la carpeta del recorrido a un lugar donde se pueda escribir (el juego deja ahí `despues_<fecha>.png` y `.txt`).
2. Correr la compilación `release`, mejor en modo portátil (un `portable.txt` junto al ejecutable y `userdata/settings.json` con `"vsync": false`, para ver el costo real y no el límite de la pantalla):

   ```
   SalvasProsperia.exe --reporte <carpeta>
   ```

3. Al terminar, el juego se cierra solo. Cada paso queda en `despues_<fecha>.txt` y en el registro (`tour:`), además de la línea `perf:` cada 5 s.

## Recorridos

- `colosal/`: el mapa colosal (16 384 m, semilla 601441504) de la ronda de rendimiento de las fases 129 a 131. Generarlo toma unos 150 s y unos 6 GB de memoria. Pasos: quieto a 70 m, avanzar 400 m, alejarse a 1 km y luego a 20 km (todo el mapa), quedarse, volver y quedarse.

## Formato de `view.tour`

```json
"tour": {
  "speed": 8,
  "atTown": true,
  "steps": [
    {"seconds": 8, "offset": [0, 0], "yaw": 0.6, "pitch": 0.9, "distance": 70}
  ]
}
```

- `speed`: velocidad del juego en cuartos (4 es x1, 0 en pausa).
- `atTown`: empieza sobre el centro del primer pueblo; si no, sobre `view.target`.
- `steps` (de 1 a 64): cada paso va desde donde terminó el anterior (el primero, desde la vista del reporte) hasta su lugar en `seconds`; `offset` son los metros en x y z desde el inicio.
