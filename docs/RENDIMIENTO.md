# Rendimiento

Mediciones de la fase 20, en el equipo de desarrollo (Windows 11, compilación `release`). El juego avanza 10 ticks por segundo a velocidad normal: un tick debe tomar menos de 100 ms a x1 y menos de 33 ms a x3.

## Cómo medir

```
build\release\bin\salvaciudad_tests.exe -ts=sim_perf --no-skip
```

- **"two towns of 300..."**: corre con las demás pruebas y falla si el tick promedio pasa de 33 ms.
- **"twelve towns of 1000 on a huge map"**: se salta por omisión (tarda unos minutos). Genera un mapa enorme con 12 pueblos, les da casas, trabajo y comida, llega a 1000 aldeanos cada uno con el comando de desarrollo `DevSpawn` y mide 2000 ticks.

## Resultados

12 pueblos de 1000 aldeanos (11 951 al medir) y 3132 edificios, mapa enorme (4096 m):

| Medida | Antes (fase 19) | Después (fase 20) |
|---|---|---|
| Tick en marcha, promedio | 61 ms | **12,5 ms** |
| Tick en marcha, percentil 95 | 101 ms | 34 ms |
| Tick más lento | 173 ms | 82 ms |
| Primeros 600 ticks (todos buscan trabajo a la vez), promedio | 187 ms | 97 ms |
| Suma de verificación del estado (cada 50 ticks en red) | 22 ms | 22 ms |
| Guardar (sin comprimir / comprimido para la red) | 95 ms, 123 MB / 213 ms, 12 MB | igual |
| Generar el mapa enorme con 12 inicios | 6,4 s | igual |

Dos pueblos de 300 en un mapa mediano: 0,15 ms por tick.

En pantalla, 1000 aldeanos a la vista en un pueblo, a x3: 100 FPS (el tope de la configuración).

## Qué se cambió

El perfil por secciones mostró que el 85 % del tick se iba en las decisiones de los aldeanos (`decide`), y dentro de ellas no en buscar caminos (12 %), sino en búsquedas que recorrían los 3132 edificios de todos los pueblos cada vez:

1. **Edificios por pueblo.** El juego guarda la lista de edificios de cada pueblo y la rehace solo cuando se agrega o se quita un edificio. Buscar almacén, obra, taller para vaciar o incendio mira solo los del propio pueblo, en el mismo orden de antes, así que las elecciones no cambian.
2. **Población contada una vez** hasta que alguien nace, llega, se va o muere, en lugar de recorrer 12 000 aldeanos en cada decisión de un taller.
3. **Bienes guardados contados una vez por tick y pueblo.** Dentro de un tick, las decisiones ven lo guardado al empezar el tick (igual en todas las máquinas); se vuelve a contar tras cada comando.
4. **Casas libres por pueblo** al buscar hogar, en vez de que cada aldeano sin casa recorra todos los edificios.

Nada de esto se guarda en la partida: son datos derivados que se rehacen.

## Límites y avisos

- La población máxima por jugador sigue entre 50 y 1000: con 12 × 1000 el tick promedio queda en 12,5 ms, dentro de lo que pide la velocidad triple.
- La sala avisa cuando el total posible pasa de **6000 aldeanos** (población máxima × jugadores). Entre 6000 y 12 000 los ticks más pesados pasan de 33 ms, y en equipos más lentos la velocidad triple podría no sostenerse; el voto de velocidad ya baja la velocidad si alguien se queda atrás (fase 9).

## Pendiente

- El arranque masivo (muchos aldeanos buscando trabajo y camino a la vez) tiene picos de 400 ms. En una partida normal la gente llega de a poco y no ocurre; si hiciera falta, se repartirían las búsquedas de camino entre ticks.
- La suma de verificación completa (22 ms cada 50 ticks) podría calcularse por partes, a medida que cambia el estado.
- El guardado incluye el mapa entero; en red se comprime a unos 12 MB para un mapa enorme.
