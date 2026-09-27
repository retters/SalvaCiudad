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

## Mapas gigante y colosal (fase 21)

`salvaciudad_tests -ts=sim_perf -tc="giant and colossal maps" --no-skip` (unos 5 minutos) genera cada mapa con 12 inicios, crea la partida, la guarda, la empaqueta para la red y la vuelve a cargar:

| Medida | Gigante (8192 m) | Colosal (16 384 m) |
|---|---|---|
| Generar el mapa | 28 s | 128 s |
| Memoria máxima al generar | 1,6 GB | 6,5 GB |
| Árboles, piedras y demás | 0,9 millones | 3,4 millones |
| Partida guardada, sin comprimir | 477 MB | 1,9 GB |
| Instantánea de red, comprimida | 46 MB (0,9 s) | 186 MB (3,5 s) |
| Cargar la partida | 0,8 s | 3,2 s |
| Suma de verificación del estado | 47 ms | 175 ms |
| Tick sin aldeanos, promedio | 1,7 ms | 7 ms |

En el juego, el colosal ocupa unos 7 GB de memoria y corre a unos 60 FPS en Ultra con toda la escena. Los mapas enormes y menores no cambian.

Lo que se cambió para que funcionaran (decisiones D-2101 a D-2106):

- **Zonas conectadas por bloques.** Cada edificio nuevo reetiquetaba las zonas transitables del mapa entero antes de la siguiente búsqueda de camino: 470 ms en el gigante. Ahora solo se reetiquetan sus bloques de 128 m: menos de 0,5 ms. La primera vez, al empezar la partida, tarda 0,2 s en el gigante y 0,8 s en el colosal (es el tick más lento de la tabla).
- **Descarte en dos niveles.** El renderizador descartaba 65 536 zonas por modelo en el colosal (10 ms por cuadro); ahora descarta primero grupos de 1 km.
- **Límites** de la partida guardada, la instantánea de red, los paquetes y los rasgos del mapa, ajustados a estas medidas.

## Pendiente

- El arranque masivo (muchos aldeanos buscando trabajo y camino a la vez) tiene picos de 400 ms. En una partida normal la gente llega de a poco y no ocurre; si hiciera falta, se repartirían las búsquedas de camino entre ticks.
- La suma de verificación completa (22 ms cada 50 ticks) podría calcularse por partes, a medida que cambia el estado.
- El guardado incluye el mapa entero; en red se comprime a unos 12 MB para un mapa enorme y 186 MB para uno colosal.
- En un mapa colosal, la suma de verificación de la red (cada 50 ticks) toma 175 ms: a x3 puede notarse un tirón cada pocos segundos. Se podría calcular por partes.
