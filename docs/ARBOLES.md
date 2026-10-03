# Árboles, biomas y tipos de mapa

Catálogo de la fase 6b. Por ahora estos valores son tablas en `src/sim/flora.cpp`. En la fase 7 pasan a archivos JSON del mod base, con la misma forma.

## Tamaños

| Tamaño | Altura | Altura del modelo | Separación mínima entre troncos |
|---|---|---|---|
| Chico | 1–7 m | 4,5 m | 3 m |
| Mediano | 7–12 m | 9,5 m | 5 m |
| Grande | 12–24 m | 18 m | 8 m |
| Enorme | 24–43 m | 33 m | 12 m |

Cada especie tiene un modelo por tamaño, hecho a la altura de la tercera columna. El juego lo escala para dar la altura exacta de cada árbol. Los modelos de un mismo tamaño comparten proporciones: un árbol chico es más delgado y con menos ramas que uno enorme de la misma especie.

## Especies

| Id | Nombre | Nombre científico | Tamaños | Forma y colores |
|---|---|---|---|---|
| `oak` | Roble | *Quercus robur* | C M G | Copa redonda y ancha, verde oscuro |
| `pine` | Pino | *Pinus sylvestris* | C M G E | Cónico en pisos, tronco rojizo arriba |
| `toog` | Toog | *Petersianthus quadrialatus* | M G E | Tronco muy recto y alto, copa pequeña arriba |
| `eucalyptus` | Eucalipto | *Eucalyptus viminalis* | C M G E | Copa irregular y rala, verde azulado, corteza clara |
| `sequoia` | Secuoya gigante | *Sequoiadendron giganteum* | C M G E | Cónica, tronco rojo muy grueso con raíces |
| `mountain_ash` | Fresno de montaña australiano | *Eucalyptus regnans* | G E | Tronco blanco altísimo, copa en la punta |
| `cherry` | Cerezo japonés | *Prunus serrulata* | C M | Copa extendida, flores rosas |
| `jacaranda` | Jacaranda | *Jacaranda mimosifolia* | C M G | Sombrilla, flores violetas |
| `tulip_tree` | Tulipán africano | *Spathodea campanulata* | C M G | Copa redonda, flores rojo anaranjado |
| `silk_floss` | Palo borracho | *Ceiba speciosa* | C M G | Tronco en forma de botella con espinas, flores rosas |
| `magnolia` | Magnolia | *Magnolia grandiflora* | C M G | Ovalada y densa, flores blancas |
| `flamboyant` | Tabachín | *Delonix regia* | C M | Sombrilla ancha y plana, flores rojo naranja |
| `bottlebrush` | Calistemo | *Callistemon* | C | Pequeño y colgante, flores rojas en cepillo |
| `stone_pine` | Pino piñonero | *Pinus pinea* | C M G | Copa de sombrilla sobre un tronco alto |
| `elm` | Olmo | *Ulmus minor* | C M G | Copa en forma de jarrón |
| `lemon` | Limonero | *Citrus limon* | C | Redondo y denso, limones amarillos |
| `apple` | Manzano | *Malus domestica* | C M | Redondo, manzanas rojas |
| `orange` | Naranjo | *Citrus sinensis* | C | Redondo y denso, naranjas |
| `pear` | Peral | *Pyrus communis* | C M | Copa alta y ovalada, peras verde amarillo |
| `peach` | Durazno | *Prunus persica* | C | Copa abierta, duraznos anaranjados |
| `avocado` | Aguacate | *Persea americana* | C M | Copa ancha y densa, verde oscuro |

(C = chico, M = mediano, G = grande, E = enorme.)

## Biomas

| Id | Bioma | Especies (peso) | Tamaños C/M/G/E | Densidad |
|---|---|---|---|---|
| `temperate` | Bosque templado | roble 35, pino 25, olmo 20, magnolia 5, manzano 5, peral 5, cerezo 5 | 30/35/30/5 | Normal |
| `pinewood` | Pinar | pino 75, pino piñonero 20, roble 5 | 25/35/30/10 | Densa |
| `giants` | Bosque de gigantes | secuoya 40, fresno de montaña 25, toog 20, eucalipto 15 | 15/20/30/35 | Abierta |
| `australian` | Bosque australiano | eucalipto 45, calistemo 30, fresno de montaña 25 | 25/30/30/15 | Abierta |
| `flowering` | Bosque florido | jacaranda 25, tabachín 20, tulipán africano 20, palo borracho 15, magnolia 10, cerezo 10 | 35/40/25/0 | Normal |
| `orchard` | Huerto silvestre | manzano 20, peral 15, durazno 15, naranjo 15, limonero 15, aguacate 10, cerezo 10 | 60/40/0/0 | Rala |

Los pesos de tamaño reparten el suelo del bosque entre los árboles medianos, grandes y enormes; los chicos llenan lo que queda (decisión D-621). Si a una especie le toca un tamaño que no tiene, recibe el más cercano que sí tenga.

## Tipos de mapa

| Id | Tipo | Biomas (peso) | Tamaños | Manchas |
|---|---|---|---|---|
| `classic` | Clásico | templado 35, pinar 20, florido 15, huerto 10, australiano 10, gigantes 10 | Los del bioma | 350 m |
| `young` | Arboleda joven | Como el clásico | Solo chicos y medianos | 350 m |
| `giants` | Tierra de gigantes | gigantes 50, templado 25, pinar 25 | Más grandes y enormes | 450 m |
| `northern` | Pinar del norte | pinar 75, templado 25 | Los del bioma | 400 m |
| `varied` | Variado | Los seis por igual | Los del bioma | 180 m |
| `single` | Bioma único | El bioma que elija el jugador | Los del bioma | Todo el mapa |

## Modelos por estado (fase 51)

Una especie puede declarar un modelo por estado del año en lugar de uno por tamaño (ver `docs/CREAR_MODS.md`): `bloom`, `autumn` y `bare`. La primera es el cerezo (`core:cherry`), con los modelos low poly de `art/blender/lowpoly_trees/` en `models/trees/`; las demás especies llegan en la fase 53.

- El cambio de estado es solo de la vista: la simulación no sabe en qué estado se ve un árbol.
- Cada árbol cambia en uno de 8 pasos repartidos en la primera quinta parte de la estación (6 días de 30 con las cuatro estaciones), según su posición. Una partida nueva empieza con todos los árboles ya en el estado de su estación.
- El tamaño de la simulación (chico, mediano, grande) sigue decidiendo la madera, el tiempo de tala y la separación. A la vista, el modelo se escala a la altura del árbol, sin bajar de la mitad ni pasar de una vez y media de la altura del modelo.
