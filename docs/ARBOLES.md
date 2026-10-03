# Árboles y biomas

Catálogo de `core` desde la fase 53. Los datos están en `data/mods/core/defs/species.json` y `biomes.json`; los modelos, en `data/mods/core/models/trees/`, hechos por `art/blender/lowpoly_trees/` (ver `docs/ARTE.md`).

## Tamaños

La simulación conserva los tamaños: deciden la madera, el tiempo de tala y la separación entre troncos.

| Tamaño | Altura | Separación mínima entre troncos |
|---|---|---|
| Chico | 1–7 m | 5 m |
| Mediano | 7–12 m | 7 m |
| Grande | 12–24 m | 10 m |
| Enorme | 24–43 m | 16 m |

Las separaciones crecieron en la fase 54 (eran 3, 5, 8 y 12 m): las copas de los árboles nuevos miden unos 9 m y se encimaban. Hay como un tercio de los árboles de antes, y cada uno da más madera.

A la vista, cada especie tiene un solo modelo (de 6 a 7,5 m de alto; los gigantes, de 22 a 46 m) que se escala a la altura de cada árbol, sin bajar de la mitad ni pasar de una vez y media de la altura del modelo. Un árbol grande se ve, entonces, de hasta unos 10 m.

## Estados

Cada modelo tiene hasta tres estados: `bloom` (con hojas o en flor; primavera y verano), `autumn` (otoño) y `bare` (invierno). Los de hoja perenne solo tienen `bloom`. Cada estado tiene su versión lejana de unos 300 triángulos (600 en los gigantes).

- El cambio de estado es solo de la vista: la simulación no sabe en qué estado se ve un árbol. Tampoco rehace nada: el estado es un dato de cada árbol que el renderizador lee al dibujarlo (fase 52).
- Cada árbol cambia en uno de 8 pasos repartidos en la primera quinta parte de la estación (6 días de 30 con las cuatro estaciones), según su posición. Una partida nueva empieza con todos los árboles ya en el estado de su estación.
- La versión lejana se dibuja cuando el árbol mide en pantalla menos de 90 píxeles en Ultra (120 en Alta, 160 en Media, 220 en Baja), con un margen del 10 % para que no parpadee, y siempre en las sombras.

## Especies

| Especie | Id | Variantes | Tamaños | Madera (chico, mediano, grande) | Hoja |
|---|---|---|---|---|---|
| Cerezo | `core:cherry` | 4 | chico, mediano | 4, 10 | Caduca |
| Cerezo llorón | `core:weeping_cherry` | 1 | chico, mediano | 4, 10 | Caduca |
| Jacarandá | `core:jacaranda` | 5 | chico a grande | 4, 10, 15 | Caduca |
| Olmo | `core:elm` | 4 | chico a grande | 4, 12, 18 | Caduca |
| Guayacán | `core:guayacan` | 4 | chico a grande | 4, 12, 18 | Caduca |
| Pino | `core:pine` | 1 | chico a grande | 4, 10, 15 | Perenne |
| Abedul | `core:birch` | 1 | chico a grande | 2, 6, 11 | Caduca |
| Sauce llorón | `core:willow` | 1 | chico a grande | 4, 10, 15 | Caduca |
| Acacia | `core:acacia` | 1 | chico a grande | 4, 8, 12 | Caduca |
| Ciprés | `core:cypress` | 1 | chico a grande | 2, 6, 11 | Perenne |
| Magnolia | `core:magnolia` | 1 | chico, mediano | 4, 10 | Caduca |
| Arce | `core:maple` | 1 | chico a grande | 4, 12, 18 | Caduca |
| Palmera | `core:palm` | 1 | chico, mediano | 2, 6 | Perenne |
| Glicinia | `core:wisteria` | 1 | chico, mediano | 2, 6 | Caduca |
| Roble amarillo | `core:oak` | 1 | chico a grande | 6, 14, 20 | Caduca |
| Laurel | `core:laurel` | 1 | chico, mediano | 4, 8 | Perenne |
| Baobab | `core:baobab` | 1 | mediano, grande | 20, 27 | Caduca |
| Drago | `core:dragon_tree` | 1 | chico, mediano | 4, 8 | Perenne |
| Manzano | `core:apple` | 1 | chico, mediano | 4, 8 | Caduca |

Los gigantes son especies de tamaño enorme con `landmark` (su silueta se ve a través de la niebla de guerra). Hasta la fase 55 ningún bioma los tiene, así que no salen en los mapas; se ven en el visor.

| Gigante | Id | Madera |
|---|---|---|
| Secuoya gigante | `core:giant_sequoia` | 120 |
| Araucaria gigante | `core:giant_araucaria` | 90 |
| Ginkgo gigante | `core:giant_ginkgo` | 80 |
| Cerezo gigante | `core:giant_cherry` | 70 |
| Sauce gigante | `core:giant_willow` | 70 |
| Baobab gigante | `core:giant_baobab` | 100 |
| Mangle gigante | `core:giant_mangrove` | 70 |
| Hongo gigante | `core:giant_mushroom` | 40 |

## Biomas

Desde la fase 54 cada lugar toma el bioma que mejor encaja con su clima y su geografía. Las reglas están en los datos (`biomes.json`).

**El clima de un lugar** (de 0 a 100, por bloques de 8 m):
- **Temperatura:** de 20 en el norte del mapa a 80 en el sur, un punto menos por cada 5 m de altura sobre el mar (o sobre el punto más bajo, si no hay mar), más un ruido suave de ±8.
- **Humedad:** un ruido suave alrededor de 50, y hasta 20 puntos más a menos de 60 m del agua.
- Las opciones `temperatura` y `humedad` del mapa (0 a 200 %, 100 por omisión) corren todo el mapa hasta 30 puntos hacia el frío o el calor, lo seco o lo húmedo. El formulario para elegirlas llega en la fase 56.

**Cómo se elige:** un bioma puede estar donde la temperatura y la humedad caen en sus rangos (con 6 puntos de margen), su región es de las suyas, hay agua del tipo que pide a la distancia que pide, y el lugar está en su franja de alturas (la parte de la tierra del mapa que queda más abajo). Entre los que pueden, gana el de más puntos: su peso por un ruido propio, que lo hace ganar en manchas. Si ninguno puede, gana el de clima más parecido, sin renunciar al agua ni a la altura que pide.

| Bioma | Id | Temperatura | Humedad | Además | Peso | Especies (peso) | Densidad | Pasto |
|---|---|---|---|---|---|---|---|---|
| Bosque de montaña | `core:mountain` | 0–45 | — | Mitad más alta de la tierra | 150 | pino 55, abedul 25, ciprés 20 | 100 % | 140 |
| Bosque boreal | `core:boreal` | 0–36 | — | Llanura, colinas, meseta o cuenca | 100 | pino 65, abedul 35 | 115 % | 130 |
| Bosque templado | `core:temperate` | 36–62 | 30–80 | — | 100 | olmo 30, roble amarillo 25, arce 20, abedul 15, manzano 10 | 100 % | 200 |
| Bosque florido | `core:flowering` | 50–80 | 55–100 | Llanura, cuenca o colinas | 100 | cerezo 30, jacarandá 30, magnolia 20, glicinia 20 | 90 % | 210 |
| Ribera | `core:riverside` | 30–100 | — | Agua dulce a 30 m o menos | 400 | sauce llorón 40, cerezo llorón 20, olmo 20, abedul 20 | 80 % | 230 |
| Bosque mediterráneo | `core:mediterranean` | 46–60 | 0–45 | — | 100 | ciprés 30, laurel 30, pino 25, manzano 15 | 60 % | 120 |
| Bosque seco tropical | `core:dry_tropical` | 64–100 | 35–70 | — | 100 | guayacán 45, jacarandá 30, laurel 25 | 80 % | 150 |
| Sabana | `core:savanna` | 64–100 | 0–42 | Llanura, meseta o colinas | 100 | acacia 55, drago 25, baobab 20 | 35 % | 140 |
| Costa tropical | `core:tropical_coast` | 78–100 | — | Mar a 120 m o menos | 400 | palmera 70, laurel 30 | 50 % | 130 |
| Huerto silvestre | `core:orchard` | 40–62 | 45–85 | Llanura | 60 (raro) | manzano 45, cerezo 30, laurel 25 | 55 % | 230 |
| Bosque encantado | `core:enchanted` | 30–90 | 60–100 | Cuenca | 140 | glicinia 40, cerezo llorón 35, magnolia 25 | 90 % | 240 |

Lo que garantizan las pruebas en varias semillas y tamaños: los sauces están a menos de 40 m de agua dulce, las palmeras a menos de 150 m del mar, el bosque de montaña en la mitad más alta de la tierra, y no hay palmeras a menos de 15 m de un pino (la costa tropical empieza en 78 de temperatura y el mediterráneo termina en 60).

F3 muestra bajo el cursor la temperatura y la humedad del lugar y por qué tiene su bioma (por su clima, por el agua dulce cercana, por el mar cercano, por la altura o por su región); el reporte del mapa (Ctrl+F12) las guarda.

## Mapa de tierra firme, de islas o de un solo bioma

Los tipos de mapa ya no son datos (fase 54). La partida nueva elige "Tierra firme" o "Islas", y "Todos los biomas, según el clima" o un solo bioma en todo el mapa. La fase 56 reemplaza estas opciones por Variado y Personalizado.
