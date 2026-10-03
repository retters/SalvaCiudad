# Árboles, biomas y tipos de mapa

Catálogo de `core` desde la fase 53. Los datos están en `data/mods/core/defs/species.json`, `biomes.json` y `map_types.json`; los modelos, en `data/mods/core/models/trees/`, hechos por `art/blender/lowpoly_trees/` (ver `docs/ARTE.md`).

## Tamaños

La simulación conserva los tamaños: deciden la madera, el tiempo de tala y la separación entre troncos.

| Tamaño | Altura | Separación mínima entre troncos |
|---|---|---|
| Chico | 1–7 m | 3 m |
| Mediano | 7–12 m | 5 m |
| Grande | 12–24 m | 8 m |
| Enorme | 24–43 m | 12 m |

A la vista, cada especie tiene un solo modelo (de 6 a 7,5 m de alto; los gigantes, de 22 a 46 m) que se escala a la altura de cada árbol, sin bajar de la mitad ni pasar de una vez y media de la altura del modelo. Un árbol grande se ve, entonces, de hasta unos 10 m.

## Estados

Cada modelo tiene hasta tres estados: `bloom` (con hojas o en flor; primavera y verano), `autumn` (otoño) y `bare` (invierno). Los de hoja perenne solo tienen `bloom`. Cada estado tiene su versión lejana de unos 300 triángulos (600 en los gigantes).

- El cambio de estado es solo de la vista: la simulación no sabe en qué estado se ve un árbol. Tampoco rehace nada: el estado es un dato de cada árbol que el renderizador lee al dibujarlo (fase 52).
- Cada árbol cambia en uno de 8 pasos repartidos en la primera quinta parte de la estación (6 días de 30 con las cuatro estaciones), según su posición. Una partida nueva empieza con todos los árboles ya en el estado de su estación.
- La versión lejana se dibuja cuando el árbol mide en pantalla menos de 90 píxeles en Ultra (120 en Alta, 160 en Media, 220 en Baja), con un margen del 10 % para que no parpadee, y siempre en las sombras.

## Especies

| Especie | Id | Variantes | Tamaños | Madera (chico, mediano, grande) | Hoja |
|---|---|---|---|---|---|
| Cerezo | `core:cherry` | 4 | chico, mediano | 2, 5 | Caduca |
| Cerezo llorón | `core:weeping_cherry` | 1 | chico, mediano | 2, 5 | Caduca |
| Jacarandá | `core:jacaranda` | 5 | chico a grande | 2, 5, 10 | Caduca |
| Olmo | `core:elm` | 4 | chico a grande | 2, 6, 12 | Caduca |
| Guayacán | `core:guayacan` | 4 | chico a grande | 2, 6, 12 | Caduca |
| Pino | `core:pine` | 1 | chico a grande | 2, 5, 10 | Perenne |
| Abedul | `core:birch` | 1 | chico a grande | 1, 3, 7 | Caduca |
| Sauce llorón | `core:willow` | 1 | chico a grande | 2, 5, 10 | Caduca |
| Acacia | `core:acacia` | 1 | chico a grande | 2, 4, 8 | Caduca |
| Ciprés | `core:cypress` | 1 | chico a grande | 1, 3, 7 | Perenne |
| Magnolia | `core:magnolia` | 1 | chico, mediano | 2, 5 | Caduca |
| Arce | `core:maple` | 1 | chico a grande | 2, 6, 12 | Caduca |
| Palmera | `core:palm` | 1 | chico, mediano | 1, 3 | Perenne |
| Glicinia | `core:wisteria` | 1 | chico, mediano | 1, 3 | Caduca |
| Roble amarillo | `core:oak` | 1 | chico a grande | 3, 7, 13 | Caduca |
| Laurel | `core:laurel` | 1 | chico, mediano | 2, 4 | Perenne |
| Baobab | `core:baobab` | 1 | mediano, grande | 10, 18 | Caduca |
| Drago | `core:dragon_tree` | 1 | chico, mediano | 2, 4 | Perenne |
| Manzano | `core:apple` | 1 | chico, mediano | 2, 4 | Caduca |

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

Son los once de la fase 54. Hasta esa fase salen en manchas al azar; la fase 54 los reparte por clima y geografía. Las montañas llevan bosque de montaña cuando el tipo de mapa lo incluye.

| Bioma | Id | Especies (peso) | Densidad | Pasto |
|---|---|---|---|---|
| Bosque de montaña | `core:mountain` | pino 55, abedul 25, ciprés 20 | 100 % | 140 |
| Bosque boreal | `core:boreal` | pino 65, abedul 35 | 115 % | 130 |
| Bosque templado | `core:temperate` | olmo 30, roble amarillo 25, arce 20, abedul 15, manzano 10 | 100 % | 200 |
| Bosque florido | `core:flowering` | cerezo 30, jacarandá 30, magnolia 20, glicinia 20 | 90 % | 210 |
| Ribera | `core:riverside` | sauce llorón 40, cerezo llorón 20, olmo 20, abedul 20 | 80 % | 230 |
| Bosque mediterráneo | `core:mediterranean` | ciprés 30, laurel 30, pino 25, manzano 15 | 60 % | 120 |
| Bosque seco tropical | `core:dry_tropical` | guayacán 45, jacarandá 30, laurel 25 | 80 % | 150 |
| Sabana | `core:savanna` | acacia 55, drago 25, baobab 20 | 35 % | 140 |
| Costa tropical | `core:tropical_coast` | palmera 70, laurel 30 | 50 % | 130 |
| Huerto silvestre | `core:orchard` | manzano 45, cerezo 30, laurel 25 | 55 % | 230 |
| Bosque encantado | `core:enchanted` | glicinia 40, cerezo llorón 35, magnolia 25 | 90 % | 240 |

## Tipos de mapa

Quedan tres hasta la fase 54, que los borra como datos:

| Tipo | Id | Qué hace |
|---|---|---|
| Clásico | `core:classic` | Todos los biomas en manchas de unos 350 m: templado 20, florido 12, montaña 10, boreal 10, ribera 8, mediterráneo 8, seco tropical 8, sabana 8, costa tropical 6, huerto 5, encantado 5 |
| Islas | `core:islands` | La misma mezcla, en islas rodeadas de mar |
| Bioma único | `core:single` | Todo el mapa es el bioma que se elige |
