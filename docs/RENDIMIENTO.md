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

## Fase 31: variantes de modelos

Medido en el equipo de desarrollo, compilación `release`, ventana de 1600 × 900, Ultra, sin vsync ni límite de FPS. La misma partida en las dos versiones: mapa colosal con semilla 12345, 1000 aldeanos (herramientas de desarrollo), 6 o 7 casas terminadas junto al centro del pueblo, a velocidad x1, con la cámara donde empieza la partida, justo después de cargarla. Cinco lecturas de F3, cada 3 segundos.

| | Fase 30 | Fase 31 |
|---|---|---|
| FPS (lecturas) | 75, 81, 73, 75, 77 | 70, 75, 79, 75, 64 |
| FPS, promedio | 76 | 73 (−4 %) |
| Último cuadro | 10 a 16 ms | 10,4 a 11,3 ms |
| Llamadas de dibujo | 639 | 721 (+82) |
| Triángulos | 2,15 M | 2,15 M |
| Descarte | 5,7 ms | 5,9 ms |

- La diferencia está dentro del ruido: las lecturas de cada versión varían más que la diferencia entre promedios, por los tics de 1000 aldeanos. El criterio (perder como mucho un 5 %) se cumple.
- Las 82 llamadas de dibujo de más son las variantes a la vista: formas distintas de casa, roca, arbusto y nube, cada una con sus materiales, en la vista y en las dos cascadas de sombra. La paleta de colores no agrega ninguna.
- Generar el mapa colosal tomó unos 13 minutos en las dos versiones, mucho más que los 2 minutos de la fase 21. Viene de antes (fases 26 y 27); se resolvió después (ver la sección siguiente).

## Generación de mapas gigante y colosal (tras la fase 31)

```
build\release\bin\salvaciudad_tests.exe -ts=worldgen_perf -tc="*time per stage" --no-skip
```

"giant map, time per stage" y "colossal map, time per stage" se saltan por omisión. Generan el mapa con los valores por omisión de la partida nueva (mar "A veces", un jugador) y la semilla 12345, y muestran el tiempo de cada etapa y la suma de verificación, para comparar versiones. Desde la fase 49 miden el generador jerárquico, que es el único; la tabla de abajo es del clásico, que se borró, y queda como historia.

Compilación `release`, en el equipo de desarrollo (i9-9900K, 32 GB). Mismo mapa antes y después: las sumas de verificación son iguales (gigante `a62012064264c43a`, colosal `eb8174aa7a3641ce`), y la versión del generador sigue en 6 (D-3111).

| Etapa | Gigante antes | Gigante después | Colosal antes | Colosal después |
|---|---|---|---|---|
| Relieve ("Dando forma al terreno") | 46 s | 12 s | 260 s | 92 s |
| &nbsp;&nbsp;ruido base | 18 s | 5 s | 44 s | 18 s |
| &nbsp;&nbsp;valles, cañones, cordilleras y mesetas | 27 s | 7 s | 213 s | 72 s |
| Lagos | 21 s | 9 s | 226 s | 58 s |
| Ríos | 2 s | 2 s | 11 s | 8 s |
| Suelo | 11 s | 7 s | 46 s | 25 s |
| Biomas, bosques, recursos e inicios | 2 s | 2 s | 7 s | 7 s |
| **Total** | **83 s** | **31 s** | **550 s** | **190 s** |

El mapa enorme (4096 m, la prueba "a huge map generates in under 30 seconds") tarda ahora 8,4 s. En el juego se suma, después de generar, armar la vista del mapa.

### Qué crecía más que el mapa

- **Valles, cañones, cordilleras, fosas y dorsales** (fase 27, D-2702). Por cada punto cercano a una de esas líneas se medía la distancia a todos sus tramos (de 24 a 48). Además, hay más líneas cuanto más grande es el mapa (van por km²), y cada una lo cruza entero y es más ancha. En el colosal, valles y cañones pasan por 747 millones de puntos: 2,8 veces el mapa. Ahora cada bloque de 64 × 64 vértices, y cada fila del bloque, mira solo los tramos que pueden alcanzarlo (D-3112).
- **Lagos** (D-2704). En el terreno plano, el agua se reparte en un orden revuelto: un único montículo con millones de puntos saltaba por toda la memoria. Ahora hay un montículo por milímetro de altura y se cargan de antemano los datos del siguiente punto (D-3113).
- **Ruido**: el relieve, la costa, el suelo y las formas lo calculaban punto por punto, con cinco mezclas de hash por capa. Ahora se calcula por filas y se reutilizan las esquinas de cada celda (D-3114).

### Lo que queda

- Valles y cordilleras siguen creciendo con el cubo del lado: el colosal tiene 4 veces más, el doble de largos y más anchos. Valles y cañones pasan por 67 millones de puntos en el gigante y por 747 millones en el colosal (11 veces más, con un mapa 4 veces mayor). Sin cambiar los mapas, solo se puede bajar el costo por punto. Una propuesta: que la cantidad vaya por kilómetro de borde en vez de por km², o que las líneas no crucen siempre el mapa entero. Así el colosal tendría la misma proporción de valles que un mapa enorme. Cambiaría todos los mapas grandes (versión 7 del generador) y queda para que la decida el usuario.
- Los lagos del colosal (58 s) están limitados por la memoria: el orden revuelto en lo plano es parte del mapa.
- Sin hilos: la simulación no los permite, para que el resultado sea el mismo en todas las máquinas.

## Niebla de guerra (fase 32)

`salvaciudad_tests -ts=sim_perf -tc="twelve towns of 1000 with and without fog of war" --no-skip` hace crecer 12 pueblos de 1000 en un mapa enorme en versus (un grupo de visión por pueblo, el peor caso) con cada modo de niebla:

| Medida | Estática | Dinámica |
|---|---|---|
| Actualizar lo explorado (una vez por segundo) | 1,85 ms | 1,85 ms |
| Lo mismo repartido por tick | 0,18 ms (menos del 1 % de un tick de 19 ms) | 0,18 ms |
| Lo que la vista calcula cada tick para un pueblo | 0,28 ms | 0,28 ms |
| Partida guardada | +0,7 MB (125,6 MB) | igual |

Con la fase 33, la niebla dinámica también anota qué ve cada grupo y sus fantasmas: 1,83 ms por actualización (0,18 ms por tick); la estática, sin eso, 1,2 ms. La vista, 0,2 ms por tick en las dos. Como los pueblos de la prueba no se ven entre sí, casi no hay fantasmas: cada uno ocupa 26 bytes en la partida y en la suma de verificación.

La suma de verificación del estado no cambia de forma medible (19 a 22 ms en las tres corridas). El tick completo sin niebla sale más lento en esta prueba (29 ms contra 19 ms) solo porque los pueblos quedan distintos: con niebla, las casas de `grow()` no se pueden poner en lo no explorado y quedan más juntas.

### En pantalla (fases 32 a 34)

Mapa colosal, gráficos en Ultra (MSAA 8x, sombras 3 × 2048, distancia 2500 m), 1000 aldeanos a la vista alrededor del centro del pueblo (cámara a 97 m), niebla estática con techo, 1600 × 900:

| | FPS | Descarte (CPU) |
|---|---|---|
| Con niebla | 132 a 139 | 1,8 a 1,9 ms |
| "Ver a través de la niebla" (sin niebla en el sombreador) | 84 a 88 | 6,3 ms |

La niebla no cuesta FPS medibles en la GPU. Sin ella el juego va más lento porque dibuja los animales de todo el mapa colosal, y su lista de instancias se rehace en cada cuadro; con niebla solo se dibujan los de lo explorado.

## Generador jerárquico (fase 42)

Medido en release en esta PC (2026-09-30), mapa colosal (16 384 × 16 384), semilla 12345, 1 jugador, sin mar, opciones normales:

| Generador | Tiempo |
|---|---|
| Clásico | 179 s |
| Jerárquico | 113 s (115 s desde la fase 43, que calcula cada vértice junto al borde de las mesetas) |

Desde la fase 49 el jerárquico es el único generador (ver más abajo).

El jerárquico calcula las regiones y su mezcla en una rejilla de 8 m (unos 4 millones de esquinas en el colosal) y solo interpola en cada vértice. Sus estructuras tocan únicamente sus propias franjas, en vez de cruzar el mapa entero como los valles y cañones del clásico (ver la sugerencia `sug-formas-por-borde`). Un mapa grande (2048 × 2048) tarda 1,5 s.

## Animales animados (fase 47)

Medido con `--reporte` (que anota los FPS de 1,5 s de cuadros, D-4720) en la misma vista con las dos versiones: la anterior a la fase (animales sin esqueleto, compilada aparte) y la nueva. Compilación `release`, ventana de 1600 × 900, Ultra, sin vsync ni límite de FPS, un jugador, juego en pausa, sin niebla de guerra (el reporte muestra todo el mapa).

| Vista | Animales (a la vista / en el mapa) | Antes | Fase 47 |
|---|---|---|---|
| Mapa grande, semilla 12345, cámara aérea a 1500 m sobre el centro (tres corridas) | 275 / 317 | 113,0; 109,8; 106,6 (109,8) | 110,4; 107,7; 105,0 (107,7; −1,9 %) |
| Mapa colosal, semilla 12345, cámara aérea a 2000 m sobre el centro | 321 / 19 346 | 85,4 | 99,5 (+16 %) |

En el mapa grande los animales con esqueleto cuestan un 2 %. En el colosal la versión nueva es más rápida: los animales con esqueleto se descartan por cuadro como los aldeanos, mientras que antes se rehacía la lista de instancias de los 19 346 animales del mapa en cada cuadro (lo mismo que se vio en la fase 32 sin niebla).

## Un solo generador (fase 49)

Medido en release en esta PC (2026-10-02), mapa colosal (16 384 × 16 384), semilla 12345, opciones por omisión de la partida nueva (mar "A veces", un jugador). Se alternaron el ejecutable de antes de la fase (con el jerárquico elegido) y el de después, dos veces cada uno, más dos medidas sueltas de cada uno:

| | Tiempos |
|---|---|
| Antes de la fase 49 (jerárquico) | 131, 132, 134 y 142 s |
| Después de la fase 49 | 123, 126, 149 y 150 s |

Es el mismo tiempo dentro de lo que varía este equipo: mientras se medía, otra sesión trabajaba en el mismo equipo. Los datos del mapa son idénticos antes y después (3 314 686 objetos); la suma de verificación pasa de `862d1baec39f9102` a `c071fdf05c8d7569` solo porque ya no incluye el byte del generador (D-4902).

No se comparan con los 115 s de la fase 43: aquella medida era sin mar, y no se repitió en esas condiciones.

## Cambio de estado de los árboles (fases 51 y 52)

En la fase 51, cada uno de los 8 pasos del cambio de estado rehacía la lista de objetos del mapa: 301 ms en el mapa colosal (3 394 869 objetos), un tirón perceptible. Desde la fase 52 el estado es un dato de cada árbol que se lee al dibujarlo, y un paso solo cambia ese dato en los árboles a los que les toca (el registro lo anota si tarda 5 ms o más: `map: trees turned ...`). Rehacer la lista completa queda para el cambio de estación y las nevadas, como antes (`map: ... features shown for the season in ... ms`).

## Versión lejana de los árboles (fase 52)

Medido con `--reporte`, compilación `release`, 1600 × 900, Ultra, sin vsync ni límite de FPS, juego en pausa. Tres juegos de datos sobre el mismo mapa y la misma vista: los árboles de antes de la fase 51; todas las especies dibujadas con el cerezo nuevo sin versión lejana; y todas con el cerezo nuevo y su versión lejana.

Mapa colosal, semilla 12345, cámara aérea a 300 m sobre el centro (un bosque, 4366 árboles a la vista):

| Árboles | FPS | Triángulos | Llamadas de dibujo | Descarte |
|---|---|---|---|---|
| De antes | 160,8; 152,1; 155,1 (156,0) | 3,05 M | 355 | 1,9 ms |
| Nuevos, solo versión cercana | 100,0 | 10,96 M | — | — |
| Nuevos con versión lejana | 143,6; 137,1; 153,1 (144,6; −7 %) | 1,39 M (−54 %) | 203 | 1,5 ms |

Mapa grande, semilla 12345, cámara a 260 m (4291 árboles a la vista): de antes 335 FPS y 2,61 M de triángulos; nuevos sin versión lejana 92 FPS y 10,72 M; nuevos con versión lejana 427 FPS y 1,44 M. A 110 m (1011 árboles, 724 en versión lejana): sin versión lejana 103 FPS y 3,00 M; con ella 379 FPS y 1,41 M.

Las corridas del colosal varían entre sí un 10 %, más que la diferencia que se mide; el dato firme es el de los triángulos.

## Personajes low poly (fase 57)

Medido con `--reporte` y `"people": 1000` en la vista (D-5710), `release`, 1600 × 900, Ultra, sin vsync, mapa pequeño (semilla 91): mil aldeanos caminando en un cuadro de 64 m.

| Vista | Antes (cuerpos viejos) | Personajes nuevos, sin versión lejana | Con versión lejana |
|---|---|---|---|
| Cámara a 45 m (756 a la vista) | 428 FPS, 2,04 M triángulos, 1089 llamadas | 298 FPS (−30 %), 2,76 M, 1401 | 596 FPS (+39 %), 1,11 M, 865 |
| Cámara a 110 m (995 a la vista) | 457 a 473 FPS | 316 FPS (−33 %) | 651 FPS (+40 %) |
| Sin aldeanos | 869 FPS | 854 FPS | 873 FPS |

Los cuerpos viejos tenían unos 1300 triángulos y los nuevos de 2300 a 3000, con 9 a 12 materiales (una llamada de dibujo por material). La versión lejana (unos 500 triángulos) se usa en cuanto el personaje mide menos que los píxeles del nivel de detalle, que en la vista aérea es casi siempre, y en todas las sombras; las sombras se dibujan ahora en una llamada por modelo. El criterio de la fase (perder como mucho un 10 %) se cumple con margen.

## Árboles gigantes (fase 55)

Medido con `--reporte`, `release`, 1600 × 900, Ultra, sin vsync, mapa mediano (semilla 91, relieve bajo, mar siempre, 2 jugadores), que tiene 3 gigantes.

| Vista | FPS | Objetos (en versión lejana) | Triángulos |
|---|---|---|---|
| Los tres gigantes desde 750 m | 1038 | 3593 (3547) | 1,31 M |
| A 70 m del mangle gigante | 925 | 319 (153) | 0,93 M |
| A 70 m del hongo gigante | 1055 | 222 (103) | 0,84 M |
| A 90 m de la secuoya gigante | 1284 | 96 (55) | 0,64 M |
