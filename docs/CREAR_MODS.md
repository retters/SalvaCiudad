# Crear mods

Un mod es una carpeta con un `mod.json`. Puede agregar o cambiar contenido (recursos, edificios, árboles, biomas), traer sus modelos y textos, y reglas en Lua. El juego base es también un mod: `data/mods/core`, y sirve de referencia para todos los campos.

El mod de ejemplo está en `tools/example_mod`. Para probarlo, copia esa carpeta a tu carpeta de mods (menú Mods > Abrir carpeta de mods), actívalo y pulsa Aplicar.

## Estructura

```
mi_mod/
  mod.json              obligatorio
  defs/*.json           definiciones (se leen en orden alfabético)
  lang/en.json, es.json textos (mismo formato que data/lang)
  models/*.glb          modelos (glTF binario)
  scripts/main.lua      reglas (opcional)
  scripts/*.lua         módulos para require
```

## mod.json

```json
{
  "schemaVersion": 1,
  "id": "mi_mod",
  "name": "mod.mi_mod.name",
  "description": "mod.mi_mod.description",
  "version": "1.0.0",
  "gameVersion": ">=0.7.0",
  "authors": ["Tu nombre"],
  "affectsSimulation": true,
  "dependencies": ["core"],
  "loadAfter": []
}
```

| Campo | Descripción |
|---|---|
| `id` | De 1 a 32 caracteres: `a-z`, `0-9` y `_`. Único. |
| `name`, `description` | Claves de texto de los archivos `lang/` del propio mod. |
| `version` | Versión del mod, `1.0.0`. |
| `gameVersion` | Versiones del juego compatibles: `">=0.7.0"` o `">=0.7.0 <1.0.0"`. |
| `affectsSimulation` | `true` si cambia algo del juego (contenido, reglas). En multijugador, esos mods deben coincidir en todos los jugadores. `false` para mods solo visuales. |
| `dependencies` | Mods que deben estar activos; se cargan antes. |
| `loadAfter` | Mods que, si están activos, se cargan antes que este. |

Un mod con errores (manifiesto inválido, versión incompatible, dependencia ausente, definiciones con errores, ciclos en el orden) se desactiva, y la pantalla de Mods muestra la lista de errores. El juego sigue con los demás.

## Definiciones (`defs/*.json`)

Cada archivo:

```json
{ "schemaVersion": 1, "defs": [ { "type": "resource", "id": "mi_mod:oro", ... } ] }
```

- **Agregar:** `"type"` e `"id"`. El `id` empieza con el id del mod: `mi_mod:oro`. Los ids son únicos dentro de cada tipo.
- **Cambiar campos de otra definición:** `{"type": "building", "patch": "core:house", "residents": 8}`. Solo se reemplazan los campos que escribas. Gana el mod que se carga después.
- **Quitar:** `{"type": "building", "remove": "core:firewood_splitter"}`.

Todo se valida al cargar: tipos, rangos, referencias a otras definiciones y rutas de modelos (relativas, dentro del propio mod, sin `..`).

### resource

| Campo | Valores |
|---|---|
| `name` | Clave de texto. |
| `category` | `food`, `material`, `fuel`, `good` o `gold`. `gold` es el oro del pueblo (`core:gold`): solo lo guardan los edificios que tienen `gold` en `stores`. |
| `nutrition` | Puntos de comida por unidad (0 a 1000), para `food`. |
| `weight` | 1 a 12: un aldeano carga 12 / peso unidades por viaje. |
| `carry` | 0 a 1000: unidades por viaje en lugar de 12 / peso (el oro va en bolsas de 50). 0, o sin escribir: según el peso. |
| `load` | Cómo se ve al cargarlo y apilarlo (fase 67): `crate`, `logs`, `stone`, `sack` o `basket`. Por omisión, `basket` para los alimentos y `crate` para lo demás. Solo cambia lo que se ve. |
| `pile` | Su propia pila junto a almacenes, obras y talleres (fase 89): el comienzo del nombre de tres modelos del mod, `<pile>_1.glb` (poco), `<pile>_2.glb` (a medias) y `<pile>_3.glb` (lleno). Por ejemplo `"pile": "models/props/pile_salt"`. Los tres archivos tienen que existir. Sin `pile`, el recurso usa la pila genérica de su `load`. Solo cambia lo que se ve. |
| `value` | Precio base en oro para los mercaderes (0 a 10000). Con 0 no lo compran ni lo venden. |

### building

| Campo | Valores |
|---|---|
| `name`, `model` o `models` | Clave de texto y modelo `.glb` del mod, o una lista de 1 a 8 variantes (ver abajo). |
| `kind` | `house`, `storage`, `workplace`, `townCenter`, `decoration`, `defense`, `military`. |
| `size` | `[ancho, fondo]` en celdas de 1 m (1 a 32). |
| `cost` | `{"core:log": 12, ...}`. |
| `buildWork` | Trabajo para construirlo (ticks de trabajador; 10 por segundo a x1). |
| `workers`, `work` | Trabajadores y tipo de trabajo: `gather`, `produce`, `haul`, `farm`, `hunt`, `fish`, `explore` (su trabajador va adonde el jugador lo manda con clic derecho). |
| `gathers`, `radius` | Para `gather`: `tree`, `stone`, `ironOre`, `berryBush`, `herbs`, `stoneDeposit`, y el radio en metros. |
| `picksFruit` | Para `gather` (sin `tree` en `gathers`): sus trabajadores recogen también la fruta de los frutales, sin talarlos. |
| `recipes` | Para `produce`: lista de recetas. |
| `residents` | Para casas. |
| `storage`, `stores` | Capacidad y categorías que guarda. Un `storage` que guarda `gold` y no es el puesto de comercio es una bóveda: ahí van los peones a dejar el oro que sobra. |
| `tier`, `desirability`, `unique` | Nivel del centro del pueblo necesario, efecto en la deseabilidad y si solo puede haber uno. |
| `levels` | Mejoras (casas y centro del pueblo): `residents`, `cost`, `work`, `needs`, `tier`, `population` y, si se ve distinto, `models`. |
| `light`, `coolLight` | Metros que alumbra de noche a su alrededor (0 a 40; por omisión 0) y si su luz es azul pálido en vez de color de fuego. Una fogata solo alumbra encendida. Las casas con gente y los talleres con trabajadores alumbran sin declararlo. En el modelo, los materiales llamados `window` y los que llevan `glow`, `flame` o `ember` en el nombre (o terminan en `_fire`) brillan de noche. |
| `cart` | `true` para el carro de los colonos (fase 73): un almacén que nadie construye ni demuele. Aparece junto al centro del pueblo al fundar, guarda los bienes iniciales y los materiales del centro, y desaparece cuando el centro se termina. Se usa el primero que haya; sin ninguno, el centro nace terminado. Si el centro del pueblo tiene `cost` y `buildWork`, los colonos lo construyen. |
| `sight` | Metros que ve desde su centro con niebla de guerra (1 a 200; por omisión 12). En `core`, el centro del pueblo ve 48 y la atalaya 45. |
| `workerSight` | Metros que ven sus trabajadores, si es más que lo de su raza (0 a 200; por omisión 0). En `core`, el del Explorador ve 30. |
| `landmark` | `true`: su silueta se ve a través de la niebla de guerra aunque no sobresalga del techo de la niebla (por omisión `false`). |

### unit y race

Una raza (`race`) dice qué personajes son sus aldeanos y de qué colores (fase 57; todo esto es solo de la vista):

- `bodies`: `{"male": [...], "female": [...]}`, nombres de modelos de `core` (`models/characters/<nombre>.glb`), hasta 8 por sexo. Cada aldeano toma uno de su sexo. Un pueblo con un solo modelo para todos lo pone bajo cualquiera de los dos. Reemplaza a `body`.
- `skins` y `hairs`: listas de hasta 12 colores `"#rrggbb"` de piel (o pelaje) y de cabello, además de los del propio modelo.
- `names`: `{"male": [...], "female": [...]}`, hasta 64 nombres por lista, de 1 a 24 bytes cada uno, sin caracteres de control ni espacios en los extremos. Así se llaman sus aldeanos (cada uno toma uno al nacer o llegar). Con una sola lista, sirve para todos; sin ninguna, se muestran como "Aldeano" o "Aldeana".

Las unidades del ejército y los pueblos también tienen `sight`: los metros que ve cada soldado (por omisión 16; el arquero de `core`, 24) y cada aldeano de esa raza (por omisión 12). Los animales, los asaltantes y los mercaderes no le dan visión a nadie.

### recipe

`inputs` y `outputs` (`{"recurso": cantidad}`) y `work` (ticks de trabajador por tanda).

### crop

Además de sus números (`resource`, `yield`, `growDays`, `fertility`, `hardy`), un cultivo puede decir cómo se ve en el campo (fase 90):

| Campo | Valores |
|---|---|
| `models` | Sus tres etapas, en orden: brotes, verde y maduro. Tres archivos del mod, cada uno una parcela de 2 × 2 m apoyada en el suelo, con los surcos a lo largo del eje Z. El juego pone una cada dos celdas del campo. Tienen que ser exactamente tres. Sin `models`, el campo usa las matas genéricas. |
| `sways` | `true` si se mece con el viento (cereales). El juego lo hace en el sombreador: el modelo no lleva esqueleto ni animación. |

Solo cambian lo que se ve.

### biome: flores y adornos del suelo (fase 91)

| Campo | Valores |
|---|---|
| `flowers` | Flores silvestres, en porcentaje de lo normal (0 a 400; 100 si no se escribe). Crecen en manchones sobre praderas y, más ralas, sobre pasto. Desde la fase 104 también cuentan para la miel y el entorno. |
| `cover` | Lista de adornos que el suelo del bioma puede llevar: `ferns` (helechos en suelo de bosque), `clover` (trébol en primavera y verano), `dryGrass` (la hierba alta se seca al pasar la primavera), `petals` (pétalos en suelo de bosque, en primavera), `scree` (pedregal sobre roca), `crag` (riscos en laderas que no se caminan) y `alpine` (flores alpinas en lugar de las de pradera). Solo cambia lo que se ve. |

La hierba alta, los juncos junto al agua dulce, lo que deja el mar en la arena y los adornos del invierno salen en cualquier bioma.

### mapFeature

Los recursos naturales del mapa. `kind` (`tree`, `stone`, `ironOre`, `berryBush`, `herbs`, `stoneDeposit`), `resource`, `amount`, `work`, `regrowDays`, `landmark` y `model` o `models` (los árboles usan el modelo de su especie). El yacimiento (`stoneDeposit`) es distinto: `amount` es lo que tiene el tamaño chico (el mediano tiene 5/2 y el grande 25/4), `models` son sus tres tamaños en orden (chico, mediano, grande) y no variantes, y `landmark` vale solo para el grande.

### species y biome

Árboles y biomas, como en `docs/ARBOLES.md`:

- `species`: `name`, `models`, `sizes`, `logs` (madera por tamaño) y `landmark` (su silueta se ve a través de la niebla de guerra). `models` va por estado: `{"bloom": [...], "autumn": [...], "bare": [...]}`.
  - Cada estado es una lista de 1 a 8 archivos (variantes; cada árbol toma una según su lugar). Una entrada puede ser `{"model": archivo, "far": archivo}` para dar la versión lejana del modelo: unos 300 triángulos, que se dibujan cuando el árbol se ve chico en pantalla y siempre en las sombras. La variante de un árbol la deciden los archivos de `bloom`; si otro estado tiene menos archivos, se repiten en orden.
  - `bloom` (con hojas o en flor) es obligatorio; un estado que falta se ve como `bloom`, así que un árbol de hoja perenne declara solo ese. En primavera y verano se ve `bloom`, en otoño `autumn` y en invierno `bare`; cada árbol cambia en un momento distinto de la primera quinta parte de la estación.
  - El mismo modelo sirve para todos los tamaños: se escala a la altura de cada árbol, entre la mitad y una vez y media de la altura del modelo.
  - Un gigante (fase 55) declara `giantBiome` (el bioma donde sale como hito, pocos por mapa; necesita el tamaño `huge`) y, si quiere, `giantWater` (metros, hasta 250: a esa distancia o menos del agua que pide su bioma).
  - El formato anterior a la fase 51 (`model` con un prefijo por tamaño, y `evergreen`) ya no se acepta.
- `biome`: `name`, `species` (`{"core:oak": 35, ...}`), `sizeWeights` (4 números), `density` (porcentaje) y `grass` (0 a 255). Y dónde crece (fase 54), todo opcional:
  - `temperature` y `humidity`: rangos `[mínimo, máximo]` de 0 a 100 (por omisión, cualquiera);
  - `altitude`: rango de 0 a 100, la parte de la tierra del mapa que queda más abajo (`[50, 100]`: la mitad más alta);
  - `water` (`fresh` o `sea`) con `waterDistance` (metros, hasta 250): solo crece con esa agua a esa distancia o menos;
  - `regions`: lista de `plain`, `hills`, `mountains`, `plateau`, `basin` (vacía: cualquiera);
  - `weight` (1 a 1000, 100 por omisión): cuánto gana donde caben varios.
- Los tipos de mapa (`mapType`) ya no existen: una definición de ese tipo se rechaza.

## Textos (`lang/`)

El mismo formato que `data/lang/en.json`, con la cabecera `language` del idioma. Los textos del mod se buscan antes que los del juego; así un mod también puede traducir. Para un idioma nuevo, agrega su archivo aquí (ver `docs/AGREGAR_IDIOMA.md`).

## Reglas en Lua (`scripts/main.lua`)

Lua 5.4 en un entorno aislado:

- **Disponible:** funciones básicas sin carga de código, `string`, `table`, `utf8` y un `math` de enteros (`abs`, `min`, `max`, `isqrt`, `sin_deg` y `cos_deg`, que devuelven el valor por 10000, `maxinteger` y `mininteger`).
- **No disponible:** `io`, `os`, `debug`, `package`, `load`, `loadfile`, `dofile` ni `collectgarbage`.
- `require("nombre")` carga `scripts/nombre.lua` del propio mod. `print` escribe en el registro del juego.
- **Límites:** 50 millones de instrucciones por llamada y 64 MB de memoria.

**Todo debe ser determinista**, para que el multijugador funcione:

- Usa solo números enteros.
- Usa `map.random` en lugar de azar propio.
- No recorras con `pairs` tablas cuyas claves sean tablas o funciones.

### on_map_generated(map)

Se llama una vez al generar cada mapa, después del generador. Las coordenadas son **centímetros enteros**.

| Función | Resultado |
|---|---|
| `map.size` | Lado del mapa en centímetros. |
| `map.starts` | Lista de `{x, z}` de las posiciones de inicio. |
| `map.height(x, z)` | Altura del suelo en centímetros. |
| `map.terrain(x, z)` | `grass`, `meadow`, `forest`, `sand`, `rock`, `clay` o `water`. |
| `map.is_water(x, z)`, `map.biome(x, z)` | Si hay agua, y el id del bioma. |
| `map.random(n)` | Entero de 1 a n, igual en todas las máquinas. |
| `map.add_feature(tipo, x, z [, escala%])` | Agrega `stone`, `ironOre`, `berryBush` o `herbs`. Devuelve `false` en el agua, fuera del mapa o a menos de 25 m de un inicio. |
| `map.add_tree(especie, tamaño, x, z [, altura_cm])` | Agrega un árbol. |
| `map.count(tipo)` | Cuántos hay de ese tipo. |

Si la regla falla, el mapa se genera igual, sin sus cambios posteriores al error, y el juego avisa qué mod falló.

## Modelos

Formato glTF binario (`.glb`), en metros, con Y hacia arriba y la base en Y = 0. Ver `docs/ARTE.md`. El mod de ejemplo genera su santuario con Blender desde `tools/example_mod/art/shrine.py`.

### Variantes

Un edificio, un nivel de un edificio o un recurso natural puede tener varias formas: `"models": ["models/casa_a.glb", "models/casa_b.glb"]` en lugar de `"model"`. Cada casa o roca del mapa muestra una, elegida por su lugar: la misma en todas las computadoras y al cargar la partida. Es solo aspecto: no cambia la partida ni rompe el multijugador.

- De 1 a 8 archivos, sin repetir. No se pueden usar `model` y `models` a la vez.
- Un nivel sin `models` se ve como el nivel anterior que sí tenga.
- Para agregar variantes a un edificio de otro mod, parchea su `models` con la lista completa: `{"type": "building", "patch": "core:well", "models": ["models/pozo_a.glb", "models/pozo_b.glb"]}`. Los archivos de una lista parcheada se buscan en el mod del parche; los de los niveles, en el mod que escribió `levels`.
- Los materiales llamados `var_roof`, `var_roof_dark`, `var_walls` y `var_shutter` cambian de color en cada edificio (ver `docs/ARTE.md`).
- El visor de modelos muestra todas las variantes de cada definición juntas.
