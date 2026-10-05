# Arte: modelos, esqueletos y animaciones

Todos los modelos del juego salen de **scripts de Blender versionados** en `art/blender/` (D-007). Así se pueden regenerar, mejorar y variar sin repetir trabajo a mano, y cualquier agente puede retomarlos.

## Generar los modelos

Con Blender 5.2 instalado, desde la raíz del repositorio:

```
blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models
```

- `--background` no abre la interfaz ni toca tus escenas abiertas.
- `--factory-startup` ignora tus preferencias y complementos, para que el resultado no dependa del equipo.
- Se puede limitar a un grupo: `characters`, `tools`, `loads`, `props`, `trees` (y después, las especies: `trees oak elm`), `buildings`, `animals` o `proposals` (y después, las familias: `proposals piles`), por ejemplo `... -- data/mods/core/models buildings`. `buildings sites` genera solo las obras (fase 67).
- Los `.glb` generados se guardan en el repositorio, así compilar el juego no requiere Blender.

**Reproducible:** generar dos veces da archivos idénticos byte a byte. El exportador de Blender cambia el orden de los triángulos entre ejecuciones, así que `common.export_glb` los ordena después de exportar (D-402). Para comprobarlo, genera en dos carpetas y compáralas:

```
blender --background --factory-startup --python art/blender/build_all.py -- tmp/a
blender --background --factory-startup --python art/blender/build_all.py -- tmp/b
```

**Vistas previas** (imágenes PNG, sin abrir Blender): `study_preview.py`, más abajo; sirve para cualquier carpeta de modelos, también las de `data/mods/core/models`.

## Archivos

| Script | Genera |
|---|---|
| `common.py` | Utilidades: escena vacía, materiales, `MeshBuilder` (piezas con material y peso de hueso), exportación con opciones fijas |
| `props.py` | `props/rock.glb`, `ore_rock.glb`, `berry_bush.glb`, `herb.glb`, `house_small.glb` y `cloud.glb`, con sus variantes; desde la fase 67, las pilas `pile_<qué>_<nivel>.glb` y la carreta `cart.glb`; desde la fase 74, el carro de los colonos `wagon.glb`; desde la fase 83, los yacimientos `stone_deposit_small.glb`, `_medium` y `_large` (de unos 4, 6 y 8 m de lado) |
| `lowpoly_trees/*.py` | `trees/<árbol>_<estado>.glb` y su versión lejana `_far.glb`: los 32 árboles y 8 gigantes del juego (ver `docs/ARBOLES.md`). `build_all.py ... trees [nombres]` los construye |
| `buildings.py` | `buildings/<id>.glb`: un modelo por edificio de `core` (46), cada uno del tamaño de su terreno; desde la fase 67, las obras `site_<ancho>x<fondo>_<etapa>.glb`, por tamaño de terreno |
| `build_all.py` | Ejecuta todo; los animales del juego (`animals/deer.glb`, `boar.glb`, `wolf.glb` y `bear.glb`) salen de `zoo/`, con esqueleto y animaciones (fase 47); los personajes (`characters/<personaje>.glb` y su versión lejana `_far.glb`, 17 de `people/`) y las herramientas (`tools/axe.glb`, `bow.glb`, `rod.glb`, `hammer.glb`, de `weapons/`), desde la fase 57; la flecha (`tools/arrow.glb`) y las cargas (`loads/*.glb`, de `loads/`), desde la fase 67 |
| `loads/*.py` | Las 9 cargas que lleva un aldeano (fase 67), una por archivo; `_load_kit.py` tiene las piezas comunes y la convención de colocación |
| `studies.py` | Técnicas de modelado de los animales low poly; `build_final` es la de producción (remesh y reducción) |
| `zoo/*.py` | Un animal o planta low poly por archivo (ver abajo) |
| `far_tree.py` | La versión lejana de un árbol (fase 52), a partir de su modelo terminado: `studies.build_final` la escribe como `<nombre>_far.glb` para toda especificación con `far_limit` |
| `zoo_build.py` | Genera los modelos de `zoo/` o, con `specs=<carpeta>`, los de `people/`, `weapons/` o `lowpoly_trees/` |
| `people/*.py` | Los 17 personajes low poly; `_human.py` es el cuerpo común y `_people_kit.py` lo que comparten los tres grupos (D-5711) |
| `weapons/wNN_*.py` | Las 40 armas y herramientas, numeradas como en la imagen de referencia |
| `lowpoly_trees/*.py` | 16 árboles en tres estados (48 modelos) desde un solo generador, `_tree.py` |
| `rigs.py` | Base de esqueletos, pesos y animaciones (`Rig`, `Pose`) y la plantilla de cuadrúpedo |
| `rigs_bird.py`, `rigs_swim.py` | Plantillas de aves y de nadadores (pez, tortuga, pulpo) |
| `rigs_human.py` | Esqueleto y animaciones de los personajes de `people/` |
| `tripo_build.py` | Anima un modelo hecho en Tripo (un cuadrúpedo con su esqueleto, o un personaje esculpido) y lo deja en `art/studies/tripo/` |
| `tripo_character.py` | La parte de personajes de `tripo_build.py`: articulaciones por la forma, reducción, colores desde la imagen |
| `rig_check.py` | Verifica las animaciones de un modelo exportado |
| `study_preview.py` | Una imagen de revisión por modelo (4 vistas) y las tiras de sus animaciones |

Las imágenes de referencia del usuario (`Animales low poly`, `Arboles 1` a `8`, `Armas y herramientas`, `Personajes 1` a `3` y, desde la fase 67, `Cargas del viajero anfibio`) están en `art/reference/` desde la fase 49; de ahí las leen `lowpoly_trees/_trace.py` y `_giant_trace.py`.

## Convenciones

- **Unidades:** metros. Un humano mide de 1,70 a 1,90 m; un enano, 1,3 m; un orco, 2,05 m.
- **Ejes en Blender:** Z arriba y el frente hacia **−Y**. Tras exportar a glTF queda Y arriba y el frente hacia **+Z**, que es lo que espera el juego (el giro de una instancia se mide desde +Z).
- **Apoyo:** los modelos se apoyan en Z = 0, con el origen en el centro de la base.
- **Estilo:** low-poly "medio" con sombreado plano. Caras y manos con algo de detalle; edificios con detalles arquitectónicos (vigas, marcos, contraventanas, tejas).
- **Materiales:** colores lisos, sin texturas, salvo que haga falta. Se exporta el color base (`baseColorFactor`).

### Materiales recoloreados por paleta

Si un material de un personaje se llama como uno de estos espacios, o empieza con su nombre y `_` (`skin_light`, `top_shade`), el juego lo pinta con el color de la **paleta de cada aldeano**, conservando lo más claro o más oscuro que sea respecto del material principal del espacio (D-5703). Así mil aldeanos se ven distintos con los mismos modelos:

| Espacio | Nombre del material | Uso |
|---|---|---|
| 0 | `skin` | Piel, o pelaje |
| 1 | `hair` | Cabello, barba, cresta |
| 2 | `top` | La prenda principal |
| 3 | `bottom` | La segunda prenda (pantalón, faja) |
| 4 a 7 | `shoes`, `belt`, `hat`, `apron` | Sin uso desde la fase 57 |

Cualquier otro nombre (`eye`, `leather`, `steel`, `gold`…) conserva su color. En los scripts de `people/` los materiales tienen nombres descriptivos (`tunic`, `cloak`, `fur`); cada personaje dice cuáles se recolorean con `palette = {"tunic": "top", "trousers": "bottom"}` y al exportar toman el nombre del espacio. Las pieles y cabellos de cada raza están en `races.json` (`"skins"`, `"hairs"`); los conjuntos de ropa, en `src/game/people.cpp`.

### Materiales recoloreados en los edificios

Lo mismo para los edificios (fase 31): si un material se llama como uno de estos espacios, cada edificio lo pinta con su **paleta**, elegida por su lugar en el mapa entre 150 combinaciones (5 techos, 6 paredes y 5 postigos):

| Espacio | Nombre del material | Uso |
|---|---|---|
| 0 | `var_roof` | Techo |
| 1 | `var_roof_dark` | Hileras oscuras del techo, cobertizos |
| 2 | `var_walls` | Paredes y hastiales |
| 3 | `var_shutter` | Postigos |

Hoy las usan las casas. El color que tenga el material en Blender es solo para la vista previa y para el visor, que puede recorrer las paletas con "Otros colores".

### Esqueleto y animaciones de los personajes

Los 17 huesos, los clips, las herramientas en la mano y la versión lejana se describen más abajo, en "Esqueleto y animaciones". Un personaje nuevo hereda de uno de los tres grupos de `people/` (`Adventurer`, `Folk` o `Figure`) y sigue su convención (D-5711); para que entre al juego se agrega a `GAME_PEOPLE` de `build_all.py` y a los `"bodies"` de una raza en `races.json`.

- **Versión lejana** (fase 57): `rigs.animate` escribe `<nombre>_far.glb` junto al modelo si la especificación tiene `far_tris` (500 en `Human`): el mismo esqueleto, la malla reducida y ningún clip. El juego le pone los clips del modelo cercano.
- **Caminar y correr** guardan su velocidad (`walk_speed`, `run_speed`); el juego avanza el clip según lo que el aldeano recorre de verdad, así que los pies no patinan.

## Variantes

Varias formas de lo mismo, para que el pueblo no se vea copiado (fase 31). Se declaran en los JSON con `"models"` (ver `docs/CREAR_MODS.md`) y el juego elige una por lugar:

- **Casas:** tres por nivel. `house`, `house_2` y `house_3` (planta baja); `house_l2*` (media planta bajo el techo, un ala o un porche); `house_l3*` (dos plantas). Salen de `house_variant` en `buildings.py`, con los materiales `var_*`.
- **Rocas, rocas con mineral y arbustos de bayas:** tres de cada uno (`rock_2`, `ore_rock_3`, `berry_bush_2`…), en `props.py` (`variants`).
- **Nubes:** cuatro formas (`cloud` a `cloud_4`), que el código reparte entre las nubes del cielo (`kClouds` en `src/game/builtin_models.h`).

Cada variante es un modelo más: se dibuja con sus propias llamadas de dibujo. Por eso pocas variantes de lo que más se repite, y la paleta de colores (que no cuesta nada) para el resto. Ver D-3101 y `docs/RENDIMIENTO.md`.

## Cómo agregar un modelo

1. Escribe una función en el script que corresponda (o un script nuevo, llamado desde `build_all.py`), usando `MeshBuilder` y `common.export_glb`.
2. Genera con el comando de arriba y revísalo en el visor de modelos (abajo) o en las vistas previas.
3. Si es un personaje, usa el esqueleto humano y nombres de material de la tabla de paletas.
4. Comprueba que regenerar da el mismo archivo.

## Animales y flora low poly (`art/blender/zoo/`)

Los 24 modelos de la imagen de referencia `Animales low poly.png` (del usuario, en `art/reference/`), más el jabalí y el oso (`boar.py`, `bear.py`), que no están en la imagen. El ciervo, el jabalí, el lobo y el oso son los animales del juego (fase 47): `build_all.py` los escribe en `core`.

- **Técnica:** se compararon diez técnicas con el cerdito y el tigre (esos estudios se borraron en la fase 53) y el usuario eligió la de *remesh* y reducción (D-4401). `studies.build_final` suelda las partes de la especificación (elipsoides y cápsulas) en una sola superficie y la reduce a `budget` triángulos. Después la corta donde un borde de color debe ser nítido (`bands` para rayas, `cuts` para bordes sueltos), pinta cada cara con `paint()`, aplana las puntas de otro color (`caps`, como el hocico del cerdito) y agrega tonos claros y oscuros a las facetas. Al final pone las piezas finas que no sobreviven al *remesh* (`details()`: orejas, cuernos, alas, aletas, hojas).
- **Un archivo por modelo** en `zoo/`, con el nombre del modelo, que define `SPECS`. `zoo/pig.py` es el ejemplo simple; `zoo/tiger.py`, uno con rayas.
- **Límite de triángulos** (`max_tris`, piezas incluidas): `build_final` baja el presupuesto hasta que el modelo cabe.

| Tipo | Ejemplos | Límite |
|---|---|---|
| Animal pequeño | conejo, gallo, águila | 800 |
| Animal mediano | cerdo, oveja, lobo, ciervo, tortuga, tiburón, pulpo | 1500 |
| Animal grande | tigre, león, vaca, caballo, elefante | 2000 |
| Criatura especial | grifo, dragón | 3000 |
| Flora | cactus, piña, fresa, hongo | 1000 |

Generar y revisar (`art/studies/` no se versiona: se regenera):

```
blender --background --factory-startup --python art/blender/zoo_build.py -- art/studies/animals [nombres]
blender --background --factory-startup --python art/blender/study_preview.py -- art/studies/animals art/studies/animals/preview [nombres]
```

La vista previa hace una imagen por modelo con cuatro vistas (frente, lado, 3/4 y 3/4 con las aristas y el número de triángulos) y `overview.png` con todos. Si el modelo tiene esqueleto, también `<nombre>_anim.png`: una fila por animación con 8 fotogramas vistos de lado.

### Personajes, armas y árboles low poly

De las imágenes de referencia del usuario en `art/reference/` (`Personajes 1` a `3`, `Armas y herramientas` y `Arboles 1` a `3`). Los personajes y los árboles están en el juego (fases 53 y 57; `build_all.py` los lleva a `core`); de las armas, cuatro son las herramientas de los aldeanos. Para estudiarlos sueltos se generan igual que los animales, con la carpeta de especificaciones:

```
blender --background --factory-startup --python art/blender/zoo_build.py -- art/studies/people specs=people [nombres]
blender --background --factory-startup --python art/blender/zoo_build.py -- art/studies/weapons specs=weapons [nombres]
blender --background --factory-startup --python art/blender/zoo_build.py -- art/studies/trees specs=lowpoly_trees [nombres]
```

Para verlos en el visor: `SalvaCiudadModelos.exe --estudio people` (o `weapons`, `trees`, `animals`, `tripo`). `--estudio` acepta el nombre de una carpeta de `art/studies` o una ruta, y abre el visor directamente en esa carpeta.

- **Personajes** (`people/`, límite de 3000 triángulos): todos heredan de `Human` en `_human.py`, un cuerpo de partes soldadas con nombre (cabeza, pecho, antebrazo…) y las articulaciones en el mismo lugar, para que después compartan esqueleto. Cada personaje cambia proporciones, agrega volúmenes de ropa en `customize()`, pinta por zona del cuerpo con `zone()` y pone lo fino en `details()`. Las proporciones salen de medir cada referencia (D-4411).
- **Armas** (`weapons/`, límite de 500 a 600): piezas directas y facetadas en `details()`; el *remesh* solo en lo orgánico (báculos, garrote, martillo de piedra). De pie sobre Z = 0, con el lado ancho hacia −Y. Cada una declara `grip`, el punto donde se sujeta (D-4412).
- **Árboles** (`lowpoly_trees/`, límite de 2500 con hojas y 1500 sin hojas): `<especie>_<variante>_<estado>`, con estados `bloom`, `autumn` y `bare` que comparten tronco y ramas. `_trace.py` (se corre a mano con Python y PIL) lee las tres imágenes y escribe `_traced.py`: ramas, masas de follaje y colores de otoño. Los modelos se generan solo con `_traced.py` (D-4413).
- **Más árboles** (imágenes `Arboles 4` a `8`): otros 16 árboles en tres estados (pino, abedul, sauce, acacia, ciprés, magnolia, arce, palmera, glicinia, roble amarillo, laurel, cerezo y jacarandá variantes, baobab, drago, manzano), trazados con `_trace.py set=second` a `_traced2.py`; el pino, el ciprés y la palmera se construyen con medidas en `_built.py`. Y 8 árboles gigantes de 22 a 47 m en dos estados (`giant_<árbol>_bloom` y `_bare`; límite de 6000 con hojas y 4000 sin hojas), con su propio generador `_giant.py`: troncos, raíces y ramas gruesas soldados con *remesh* y reducción (D-4720).

### Modelos de Tripo

Un cuadrúpedo generado en Tripo y exportado como `.fbx` con su esqueleto automático se anima con la plantilla de cuadrúpedo:

```
blender --background --factory-startup --python art/blender/tripo_build.py -- <modelo.fbx> name=<nombre> length=<metros>
```

- Conserva la malla y la textura del modelo. Del esqueleto de Tripo solo se usan las posiciones de las articulaciones: sus nombres no son fiables, así que las patas, la cola y la cabeza se reconocen por la forma (D-4701).
- El modelo se gira para mirar hacia −Y, se escala a `length` (del hocico a la punta de la cola; sin `length` queda como viene, que en Tripo es 1 m) y se apoya en Z = 0.
- Recibe los huesos, pesos y animaciones de la plantilla (`idle`, `walk`, `run`, `eat`, `die`) y queda en `art/studies/tripo/<nombre>.glb`.
- Verificar con `rig_check.py` y ver con `SalvaCiudadModelos.exe --estudio tripo`.
- Solo cuadrúpedos por ahora: si el esqueleto no tiene cuatro cadenas de huesos que lleguen al suelo, el modelo se rechaza.
- Estos modelos son mucho más pesados que los low poly (el lobo de prueba: 10 565 triángulos y una textura de 2048 px, contra 1316 del lobo low poly).

**Personajes.** Un personaje de pie esculpido en Tripo (una malla sin esqueleto, sin textura y sin colores) se convierte en un personaje low poly animado:

```
blender --background --factory-startup --python art/blender/tripo_build.py -- <modelo.fbx> name=<nombre> height=<metros> image=<imagen> crop=x0,y0,x1,y1
```

- `tripo_build.py` elige el camino solo: con esqueleto es un cuadrúpedo; sin esqueleto, un personaje.
- **Forma:** se gira para mirar hacia −Y (lo adivina por los pies; `front=+x` y demás lo corrigen), se apoya en el suelo y se escala a `height` (1,7 m si no se dice).
- **Articulaciones:** se buscan cortando la malla en rebanadas horizontales. Donde los brazos y las piernas están separados del tronco, la rebanada cae en piezas separadas; de ahí salen las axilas, la entrepierna y el eje de cada extremidad. Por eso el personaje debe estar de pie con los brazos separados del cuerpo.
- **Reducción:** por colapso de aristas hasta `tris` (3000 si no se dice) y con caras planas, como los demás modelos low poly.
- **Colores:** de la imagen con que se generó el modelo (`image`) y el recuadro del personaje en ella (`crop`, en píxeles). Se busca desde qué ángulo la silueta del modelo coincide con la de la imagen, y cada cara toma el color que la imagen tiene donde se ve esa cara. Las caras que la imagen no muestra toman el color de su reflejo en el otro costado, o el de lo que tienen delante (la espalda toma el color del frente). Los colores se agrupan en hasta 12 materiales. Sin `image` queda gris.
- **Animación:** el esqueleto y las ocho animaciones de los personajes. La tela que cuelga lejos de un brazo o una pierna se queda con el tronco. Lo que cuelga de una mano mucho más abajo que la otra mano se toma como un objeto sostenido y va con esa mano.
- **Caras puente:** una escultura es una sola superficie fundida. Donde una mano toca la cadera o una punta de tela toca una pierna, se cortan las caras que unen partes que se separan al moverse y se tapan los huecos.

### Esqueletos y animaciones de los animales

`rigs.py` (fase 44). Una plantilla por familia arma el esqueleto con unos pocos puntos que declara la especificación (`rig = rigs.Quadruped(...)`, ver `zoo/pig.py`). Así todos los animales de una familia comparten nombres de huesos y animaciones.

- **Cuadrúpedo:** 21 huesos: `body` (la raíz, con la parte de atrás del cuerpo), `chest`, `neck`, `head`, `ear.L/R`, `tail.1` a `tail.3` y, en cada pata, `leg_upper`, `leg_lower` y `foot` con el sufijo `.FL`, `.FR`, `.HL` o `.HR` (delantera o trasera; izquierda +X, derecha −X).
- **Pesos por distancia a los huesos**, hasta 4 por vértice, con transición suave en las articulaciones (D-4402):
  - los huesos de una pata solo tiran de la pata: cerca de su eje y por debajo de donde sale del cuerpo;
  - todo lo que está bajo el tobillo es rígido, para que la pezuña no se incline;
  - cada pieza suelta (oreja, ojo, eslabón de la cola) va entera a su hueso más cercano.
- **Anillos en las articulaciones:** la superficie se corta en la rodilla y donde la pata sale del cuerpo, para que se doble ahí (D-4403).
- **Animaciones**, todas en el lugar, sin avanzar:
  - `idle`: 3 s;
  - `walk` y `run` (trote);
  - `eat`: baja la cabeza y vuelve a la pose de reposo;
  - `die`: cae de lado y no se repite.
- **Patas sin patinar:** las patas siguen una trayectoria del pie (apoyado en el suelo y luego adelante en arco) con cinemática inversa. Durante el apoyo, el pie retrocede exactamente a la velocidad de la animación. Esa velocidad se guarda en el modelo, en los *extras* del esqueleto: `walk_speed` y `run_speed` en m/s (D-4404).
- **Las demás familias** (fase 46) usan la misma base. Cada especificación puede derivar su plantilla para agregar huesos y poses propias:
  - cuadrúpedos con extras: trompa (elefante), alas y `fly` (grifo, dragón), saltos (conejo);
  - aves (`rigs_bird.Bird`): `idle`, `walk`, `run`, `eat`, `die`, y `fly` (gallo, águila) o `swim` (pingüino);
  - nadadores (`rigs_swim`): tiburón (`swim`, `swim_fast`, `eat`, `bite`), tortuga (`walk`, `swim`, `hide`) y pulpo (`walk`, `swim`);
  - la flora no lleva esqueleto.
- Las animaciones de vuelo y nado se animan cerca del origen: el juego les da la altura o la profundidad.
- **Personajes** (fase 48, `rigs_human.Humanoid`): los 17 huesos de los aldeanos (`hips`, `spine`, `chest`, `neck`, `head`, y por lado `upper_arm`, `lower_arm`, `hand`, `thigh`, `shin`, `foot`), más los que agregue cada personaje (cola, capa, coleta, faldas). Animaciones: `idle`, `walk`, `run`, `chop` (talar), `shoot` (arco), `fish_cast`, `fish_stand`, `fish_sit` y `work` (martillar; la genérica de los oficios, fase 57).
  - La herramienta es un modelo aparte. El modelo dice en qué mano va en cada animación, en los *extras* del esqueleto: `chop_prop` = `axe:hand.R`, `shoot_prop` = `bow:hand.L`, `fish_*_prop` = `rod:hand.R`, `work_prop` = `hammer:hand.R`; y cuánto mide ese hueso (`hand.R_length`), porque el juego no sabe dónde termina un hueso. Qué modelo es cada herramienta está en `GAME_TOOLS` de `build_all.py` y en `src/game/builtin_models.h`. Va con su eje largo (su +Z) hacia el frente de la mano, que es −Y con el brazo colgando en reposo, y con su punto `grip` en el centro de la mano. Las tiras de revisión la muestran puesta.
  - Una animación que no se repite lleva `<animación>_loops` = 0 (`die`, `hide`, `fish_cast`).
- **Verificar** un modelo exportado: `blender --background --factory-startup --python art/blender/rig_check.py -- art/studies/animals/pig.glb`. Comprueba tres cosas y termina en `RIG OK` o `RIG FAILED`:
  - que cada animación que se repite termina en la pose con que empieza;
  - que nada baja del suelo;
  - que los pies apoyados retroceden a la velocidad guardada (±10 %).

## Cargas, pilas, obras y carreta (fase 67)

Modelos para que lo que pasa en el pueblo se vea: lo que lleva un aldeano, lo que hay apilado en una obra o un almacén, y la obra misma.

### Cargas (`art/blender/loads/`, `models/loads/`)

Modelos rígidos, sin esqueleto, de unos 300 triángulos, uno por archivo (`studies.Spec` con solo `details()`, como las armas). Las medidas son para un cuerpo de 1,8 m; el juego las escala para cuerpos más pequeños. El juego fija toda carga al hueso `chest`; el punto `grip` del modelo (en sus *extras*, en ejes de Blender) dice dónde:

- **En la espalda** (`<qué>_back`): el modelo queda entero del lado **+Y** del plano Y = 0 (detrás del personaje), apoyado en Z = 0. Su `grip` es `(0, 0, mitad de su altura)`: el punto que toca el centro de la espalda, que en un cuerpo de 1,8 m en reposo es `(0, +0,115, 1,32)`, es decir, el inicio del hueso `chest` llevado 0,115 m hacia atrás.
- **En los brazos** (`<qué>_arms`): el modelo queda entero del lado **−Y** del plano Y = 0 (delante del personaje), apoyado en Z = 0. Su `grip` es `(0, 0, 0,14)`: el punto que toca el centro del pecho, `(0, −0,115, 1,32)` en un cuerpo de 1,8 m. Así el fondo de la carga queda justo sobre las manos de las animaciones de carga.
- En ambos casos el arriba del modelo es +Z y su izquierda y derecha son las del personaje. La carga no se gira respecto del hueso.

| Modelo | Qué es | Ancho × fondo × alto (m) | `grip` |
|---|---|---|---|
| `logs_back` | 6 troncos atados con dos correas | 0,72 × 0,34 × 0,48 | (0, 0, 0,24) |
| `stone_back` | 3 rocas en un arnés de cuero | 0,54 × 0,40 × 0,62 | (0, 0, 0,30) |
| `sack_back` | Saco de tela atado arriba | 0,46 × 0,36 × 0,62 | (0, 0, 0,30) |
| `basket_back` | Canasto de mimbre con verduras y pan | 0,46 × 0,40 × 0,62 | (0, 0, 0,25) |
| `crate_back` | Cajón de madera con correas | 0,48 × 0,34 × 0,44 | (0, 0, 0,22) |
| `logs_arms` | 4 troncos atravesados | 0,84 × 0,30 × 0,27 | (0, 0, 0,14) |
| `stone_arms` | 3 piedras | 0,52 × 0,31 × 0,37 | (0, 0, 0,14) |
| `basket_arms` | Canasta con asa, llena de comida | 0,42 × 0,40 × 0,34 | (0, 0, 0,14) |
| `crate_arms` | Cajón pequeño | 0,44 × 0,30 × 0,29 | (0, 0, 0,14) |

Las cargas de la espalda no traen las correas de los hombros: dependerían del cuerpo de cada personaje.

### Animaciones de carga

`rigs_human.Humanoid` tiene dos clips más (11 de los 16 que admite el motor):

- `carry_walk`: la misma marcha que `walk` (los mismos fotogramas y la misma velocidad guardada, `carry_walk_speed`), con los dos brazos doblados al frente sosteniendo una carga contra el pecho y el tronco un poco echado hacia atrás.
- `carry_idle`: de pie, con los brazos igual y una respiración leve; 90 fotogramas, se repite.

Las muñecas quedan en `(±0,16, −0,30, 1,12)` de un cuerpo de 1,8 m (`CARRY_HAND`), fijas respecto del hueso `chest`, así que la carga no se separa de las manos. No llevan `<clip>_prop`: el juego elige la carga. Para una carga en la espalda sirven los clips normales (`walk`, `idle`).

### Pilas (`props.py` y `proposals/piles`)

`props/pile_<qué>_<nivel>.glb`, con `<nivel>` = `1` (unas pocas piezas), `2` (media pila) o `3` (llena). Cada una ocupa cerca de 1,5 × 1,5 m, con el origen en el centro de la base. Un nivel contiene las piezas del anterior en el mismo lugar, así que al cambiar de nivel la pila crece sin saltos.

- **Genéricas** (`props.py`, fase 67): `<qué>` = `logs`, `stone`, `sacks`, `crates` o `baskets`, una por tipo de carga. Las usan los troncos, la piedra, el oro y cualquier recurso sin pila propia.
- **Por recurso** (`proposals/piles/build.py`, fase 89): una por recurso (`pile_wheat`, `pile_bricks`, `pile_firewood`…). Cada recurso dice cuál es la suya con `"pile"` en `resources.json`. Tope: 1 200 triángulos, quietas, sin materiales que brillen de noche.

Junto a un edificio se ven hasta 6 pilas, las de lo que más tiene: las primeras sobre la pared de la puerta, a su derecha y sin taparla, y las demás a lo largo de la pared derecha (`props::pile_spot`). Las obras apilan a la izquierda.

### Parcelas de cultivo (`proposals/farm`, fase 90)

`props/crop_<cultivo>_<etapa>.glb`: una parcela de 2 × 2 m por cultivo y etapa (`1` brotes, `2` verde, `3` maduro), con tres surcos a lo largo del eje Y de Blender (Z del juego) y el origen en el centro, a ras de suelo. Tope: 200 triángulos, porque un campo de 20 × 20 dibuja cien. Por eso un cultivo denso no modela cada tallo: el trigo, la cebada y el lino son gavillas (un tronco de pirámide que se abre hacia arriba, con su corona de espigas o de flores al madurar).

No llevan esqueleto. Los que el cultivo marca con `"sways"` los mece el juego en el sombreador de vértices (`SceneRenderer::set_model_sway`): cada vértice se desplaza en proporción a su altura sobre la base del modelo. Las parcelas de 4 × 4 m de la página de propuestas (`farm_crop_*`, con cada tallo y un esqueleto para mecerse) siguen ahí, pero no son las del juego.

### Adornos del suelo (`cover_*`, fase 91)

`props/cover_<qué>.glb`: 22 modelos que la vista coloca sola alrededor de la cámara (`src/game/ground_cover`), según el bioma, el suelo, la pendiente, el agua cercana y la estación: hierba alta y seca, trébol, helecho, juncos, cinco flores de pradera y girasoles, pétalos rosas y morados, flores alpinas, pedregal, risco, madera de deriva, conchas, poza de marea, ventisquero, témpano y muñeco de nieve.

Salen de las familias `scatter`, `biomes` y `nature` de las propuestas, en su **versión del juego**: la entrada de `game.json` lleva `"game": true` y entonces el script de la familia corre con `_kit.GAME` encendido, que quita el esqueleto y las animaciones (`kit.save` ignora `mech`), adelgaza lo que el script multiplica con `kit.light(n, parte)` y escribe en `art/studies/propuestas_game/`, para no pisar la versión de la página. El nombre en el juego lo da el propio `game.json` (`"ids": {"scatter_fern": "cover_fern"}`).

Topes: 400 triángulos (`ground`) para lo que se repite mucho y 1 500 (`rock`) para las pocas piezas grandes (pedregal, risco, poza, muñeco). Las plantas se mecen en el sombreador, como los cultivos.

### Fauna de ambiente (`models/fauna/`, fase 92)

Quince modelos con esqueleto que la vista dibuja y mueve cerca de la cámara (`src/game/ambient_fauna`): ardilla roja y gris, búho pardo y nival, gorrión, petirrojo y azulejo, cuervo, corneja grande y buitre, zorro rojo y ártico, y tres enjambres (mariposas, luciérnagas y libélulas). Salen de las familias `creatures` y `nature` de las propuestas tal como están en la página, con sus animaciones; no llevan `"game": true` porque necesitan el esqueleto.

Qué animación usa el juego: `idle` y `eat` al estar quietos, `walk` y `run` al moverse (la ardilla siempre corretea con `run`), `fly` las aves y los enjambres. La velocidad a la que se mueven es la que el modelo declara para cada clip (`<clip>_speed`), para que las patas no patinen. Los enjambres son un solo modelo: cada insecto es un hueso que da vueltas dentro del clip `fly`.

Las libélulas del juego llevan `"bare": true`: el script deja fuera la charca y los juncos sobre los que vuelan en la página (`_kit.BARE`), porque en el juego vuelan sobre agua de verdad. Solo las luciérnagas tienen un material que brilla de noche.

### Empalizada modular (`proposals/walls`, fase 93)

`buildings/palisade_<pieza>.glb`: las diez piezas del kit de empalizada de las propuestas (`pillar`, `end`, `straight`, `corner`, `tee`, `cross`, `diagonal`, `step`, `site` y `breach`), más `palisade_gate.glb` (4 × 2 m) y `palisade_postern.glb` (2 × 2 m). Tope de una pieza: 800 triángulos (`line`). La puerta y la poterna entran sin esqueleto, cerradas: en el juego los aldeanos las cruzan sin que se abran.

Qué pieza se dibuja y cómo se gira lo decide `props::line_look` a partir de los cuatro vecinos; es la misma regla de `docs/propuestas/muros.html`. Un tramo en diagonal no usa piezas distintas en cada celda: cada módulo es un pilar y entre dos módulos que se tocan por la esquina se pone una pieza `diagonal` centrada en esa esquina, de centro a centro.

**Setos y vallas (fase 94).** Del mismo kit salen `hedge_<pieza>.glb` (seto vivo, las diez piezas), `boxhedge_<pieza>.glb` (seto bajo recortado) y `picket_<pieza>.glb` (valla de estacas); estos dos solo tienen `end`, `straight`, `corner`, `tee`, `cross` y `step`. Sus pasos: `hedge_arch.glb`, `boxhedge_gate.glb` y `picket_gate.glb` (2 × 2 m, sin esqueleto, cerrados). Los setos tienen su propia clase en `game.json`, `hedge`, con tope de 1500 triángulos: son volúmenes de hojas y el seto vivo llega a 1492 en la diagonal. La valla cabe en los 800 de `line`.

**Caminos (`proposals/lines`, fase 95).** `buildings/road_dirt_<pieza>.glb` (camino de tierra con rodadas, 132 a 156 triángulos) y `buildings/road_cobble_<pieza>.glb` (calle empedrada, 512 a 780): `pillar`, `end`, `straight`, `corner`, `tee` y `cross`, de la clase `line`. Son losas de pocos centímetros con el origen a ras de suelo. El juego las pone 4 cm sobre el terreno y las **inclina con la ladera** (`render::Instance::slope_x` y `slope_z`: la pieza se cizalla, no se gira, así que dos tramos vecinos siguen coincidiendo en su borde). Una pieza nueva de camino no debe tener nada alto: lo que sobresale se inclina con ella.

**Faroles de camino y almenara (fase 96).** `buildings/lantern_wood.glb` (332 triángulos), `lantern_iron.glb` (478) y `lantern_stone.glb` (136), de `proposals/roads`; `buildings/beacon.glb` (1672), de `proposals/bridges` (`dock_beacon`). Entran sin esqueleto: en el juego no se balancean ni parpadean; la luz la pone el juego de noche, como en cualquier edificio con `light`.

`palisade.glb`, el modelo de un solo bloque, sigue en el mod como modelo del edificio (el que usa el fantasma al colocar y cualquier pieza que falte).

### Sonido de lluvia (fase 97)

`art/audio/make_sounds.py` genera también `rain.wav`: un bucle de 5,9 segundos de lluvia pareja (un siseo sin graves y unas trescientas gotas por segundo), con el final fundido en el principio para que no se note la vuelta. Como los demás, sale de una semilla fija: generarlo dos veces da el mismo archivo.

### Bancos de peces, juncos, patos y la presa de castores (fase 110)

`props/fish_shoal.glb` (de `proposals/beasts`, 888 triángulos, sin esqueleto; se dibuja 45 cm bajo el agua), `props/reed_bank.glb` (de `proposals/biomes`, 928; en el juego va sin su placa de agua), `props/ducks.glb` (un pato de `proposals/creatures`, sin esqueleto, sobre el agua) y `props/cover_beaver_dam.glb` (1388, también sin sus placas de agua; adorno de la capa de detalle del suelo). En la lista `game.json`, una entrada de `creatures` tiene que ir antes que cualquiera de `beasts`: `beasts` toma prestados módulos de `creatures`, y si se construye primero en la misma pasada, los modelos de `creatures` se guardan en la carpeta equivocada.

### Conejos y lince (fase 109)

`fauna/rabbit.glb` (de `proposals/beasts`), `fauna/lynx.glb` y `fauna/wildcat.glb` (de `proposals/creatures`). Fauna de ambiente: hasta cinco conejos por zona, visibles al amanecer y al atardecer (siempre, si la partida no tiene noche); el lince, o el gato montés en una de cada dos zonas, uno de cada cuatro días.

### Cabras (fase 108)

`fauna/goat.glb` (blanca), `goat_brown.glb` y `goat_pied.glb`, de `proposals/creatures`. En un redil de cabras las hembras alternan blanca y parda, y la pía es el macho. El queso usa por ahora la pila del pan.

### Redil, ovejas y carnero (fase 107)

`buildings/sheepfold.glb` (2308 triángulos; ocupa 10 × 10 m) sale de `proposals/farm` como `farm_sheepfold_empty`: el redil de la propuesta sin sus cinco ovejas, porque el rebaño lo dibuja el juego. `animals/sheep.glb` es la oveja del zoológico (`zoo/sheep.py`, que se construye con `animals`) y `fauna/ram.glb` el carnero de `proposals/beasts`. La lana usa por ahora la pila del lino. Las obras del redil son `site_10x10_1.glb` y `_2.glb`.

### Perros y gatos (fase 106)

De `proposals/creatures`: `fauna/dog.glb` (mestizo), `dog_shepherd.glb`, `dog_mastiff.glb` y `dog_terrier.glb`; `fauna/cat.glb` (gris), `cat_tabby.glb`, `cat_black.glb`, `cat_white.glb` y `kitten.glb`. Fauna de ambiente: el perro de una caseta es uno de los cuatro según dónde está la caseta y ronda a 6 m; el gato de una casa es el del número que guarda la casa y ronda a 3 m.

### Gallinas (fase 105)

`fauna/hen.glb`, `hen_white.glb` y `chick.glb`, de `proposals/creatures` (clase `animal`). La vista pone alrededor de cada gallinero tantas gallinas como le quedan, alternando parda y blanca, y un pollito si tiene dos o más; de noche no se ven. Son fauna de ambiente (fase 92): no están en la simulación.

### Anexos de casa (fase 103)

De `proposals/annexes` (clase `building`): `buildings/annex_clothesline.glb` (622 triángulos; ocupa 4 × 2 m), `annex_home_shrine.glb` (556; 2 × 2), `annex_playground.glb` (el columpio, 432; 4 × 2), `annex_rain_barrel.glb` (480; 2 × 2) y `annex_woodshed.glb` (4140; 6 × 2). El leñero tenía 8460 triángulos, más que el límite de un edificio (6000): sus leños apilados se hacen ahora con cinco lados y solo la cara que se ve. Los modelos `decor_clothesline`, `decor_firewood_rack` y `decor_tool_corner` siguen en la carpeta, pero el juego base ya no los usa. El leñero estrena una huella de 6 × 2: sus obras (`site_6x2_1.glb` y `_2.glb`) salen de `buildings sites`, como las demás.

### Rocas en tres tamaños y tres piedras (fase 102)

De `proposals/scatter` (clase `rock`): `props/loose_stones.glb` (piedras sueltas, 252 triángulos), `boulder.glb` (peñasco, 288) y `outcrop.glb` (afloramiento, 496), cada uno también `_mossy` y `_sandstone`. El peñasco reemplaza a `rock.glb`, `rock_2.glb` y `rock_3.glb`, y el afloramiento a `stone_deposit_small.glb`; esos cuatro archivos siguen en la carpeta pero el juego base ya no los usa. Los yacimientos de roca mediano y grande conservan su modelo.

### Yacimientos de arcilla, carbón y oro (fase 101)

`props/clay_deposit.glb`, `coal_deposit.glb` y `gold_deposit.glb`, de `proposals/nature` (clase `rock`, hasta 1500 triángulos). Un modelo por yacimiento, hecho al tamaño chico (unos 4 m de lado); el juego lo dibuja 1,5 y 2 veces más grande para el mediano y el grande. Las minas de carbón y de oro usan por ahora el modelo de la mina de hierro.

### Raíces, viñedo y vino (fase 100)

`props/crop_roots_1.glb` a `_3.glb` (las parcelas de raíces en sus tres etapas, 180 triángulos, de `proposals/farm`), `buildings/vineyard.glb` (3286) y `buildings/vineyard_bare.glb` (912; el mismo viñedo en invierno, sin hojas ni racimos), y las pilas `pile_wine` (barriles, los mismos de la cerveza). La prensa de vino usa el modelo que ya tenía como decoración.

### Arbustos de bayas por temporada (fase 99)

De `proposals/scatter`: `props/bush_berries.glb` y `props/bush_blueberries.glb` (con fruto, 620 triángulos), `props/bush_flowers.glb` (en flor, 620), `props/bush_green.glb` (sin fruto, 268) y `props/bush_thorn.glb` (zarza, 364). Los dos con fruto llevan el de flor y el verde como «aspectos» del mismo modelo, igual que los estados de un árbol: cambiar de estación no cuesta nada. Los `berry_bush*.glb` de antes siguen en el mod pero el juego base ya no los usa.

### Miel, huevos y setas (fase 98)

De las propuestas, sin cambios de forma: `props/bee_tree.glb` (árbol con panal, 612 triángulos), `props/nest.glb` (nido con huevos, 360), `props/stump.glb` y `props/stump_2.glb` (tocón con setas y tronco hueco, 420 y 332; son variantes del mismo elemento) y `props/mushroom_ring.glb` y `props/mushroom_ring_2.glb` (setas pardas y rojas, 336 y 784; variantes del corro). Las pilas `pile_honey`, `pile_eggs` y `pile_mushrooms` (las dos últimas, nuevas en `proposals/piles/build.py`: cestas como las de bayas). El nido y el tocón se ven igual todo el año; el corro solo se dibuja mientras tiene setas.

## Modelos de propuesta que entran al juego (fase 89)

Los modelos de `art/blender/proposals` (los de la página `docs/propuestas`) no están en el juego hasta que una fase los usa. `art/blender/proposals/game.json` lista los que sí:

```json
{"family": "piles", "class": "pile", "to": "props", "each": ["_1", "_2", "_3"], "ids": ["pile_wheat", "pile_bricks"]}
```

- `family`: la carpeta de la familia, cuyo `build.py` construye el modelo en `art/studies/propuestas/<familia>/`.
- `ids`: los modelos; con `each`, cada id se multiplica por esos sufijos (los tres niveles de una pila).
- `to`: la carpeta de `data/mods/core/models` adonde se copia, con el mismo nombre.
- `class`: su clase, que fija el tope de triángulos (`limits`, en el mismo archivo): `pile` 1 200, `line` (pieza de muro, valla o camino) 800, `ground` (adorno del terreno) 400, `crop` (parcela de cultivo) 700, `animal` 2 000, `building` 6 000.

`build_all.py ... proposals` los construye y copia; el que pasa de su tope no se copia y el comando termina con error (`PROPOSAL PROBLEM`). Un modelo que pasa del tope se aligera en su propio script, no en el juego.

### Obras (`buildings.py`)

Una obra tiene tres aspectos: cimientos, armazón y el edificio terminado (su modelo de siempre). Los dos primeros son genéricos, uno por **tamaño de terreno** y no por edificio: `buildings/site_<ancho>x<fondo>_1.glb` y `_2.glb`. `buildings.footprints()` lee los tamaños de `defs/buildings.json`; hoy son 14: 2x2, 3x3, 4x2, 4x4, 5x4, 5x5, 6x5, 6x6, 6x8, 7x6, 7x7, 8x6, 8x7 y 8x8. Si un edificio nuevo usa otro tamaño, basta volver a generar.

- **Etapa 1:** piso de tierra, un contorno de cimientos de piedra de 0,4 m de alto con el hueco de la puerta en el lado −Y, estacas con un trapo rojo y una pila de tablones.
- **Etapa 2:** los mismos cimientos más un armazón de postes y vigas (de 3 m de alto en los terrenos de 2 m, hasta 5 m en los de 8 m), con riostras en las esquinas y, por dentro del lado +X, un andamio con su escalera.
- Mismas convenciones que los edificios: llenan su terreno, se apoyan en Z = 0 y la puerta da a −Y.

### Flecha y carreta

- `tools/arrow.glb`: la flecha de `weapons/w17_arrow.py`, de 0,8 m, con su eje largo en +Z (la punta arriba) como las demás herramientas. Está en `GAME_TOOLS` de `build_all.py`.
- `props/arrow_flight.glb` (`props.py`): la flecha como vuela en el juego: acostada, con la punta al frente y de 1,2 m para verse desde arriba. El juego solo la gira sobre la vertical.
- `props/cart.glb`: la carreta de mano del mercader: dos ruedas, dos varas hacia −Y (su frente), cajones, sacos y un barril bajo un toldo de tela. Mide 2,3 m de largo (2,2 m sin el vuelo del toldo), 1,3 m de ancho y 2 m de alto.

### Generar y revisar

```
blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models loads
blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models tools
blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models props
blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models buildings sites
blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models characters
blender --background --factory-startup --python art/blender/study_preview.py -- data/mods/core/models/loads <carpeta de salida>
```

`buildings sites` genera solo las obras, sin tocar los edificios. Tras regenerar los personajes, `rig_check.py` sobre los 17 modelos cercanos debe terminar en `RIG OK`.

Un tropiezo conocido: la versión lejana (`_far.glb`) de unos pocos personajes (`knight_man`, `knight_woman`, `orc`, `cleric`) no sale idéntica byte a byte en cada generación, porque la reducción de Blender no siempre elige las mismas aristas. Si solo cambió eso, se deja el archivo que ya estaba (`git checkout`).

## Visor de modelos

`SalvaCiudadModelos.exe` se compila junto al juego (queda en `build\<preset>\bin\`) y sirve para revisar los modelos sin abrir el juego (D-3001):

- A la izquierda, los modelos del mod elegido por categoría (edificios, árboles, objetos del mapa, personajes, animales). Al elegir un tipo se ven **todas sus variantes lado a lado**; al elegir un archivo, solo ese.
- Se ven con la luz y las sombras del juego, junto a un aldeano de 1,7 m y sobre una cuadrícula de 1 m. Los árboles se pueden ver en cada estación y con nieve, y los personajes con otra paleta y cada animación.
- A la derecha, la ficha: triángulos, vértices, llamadas de dibujo, materiales, texturas, tamaño en metros, qué definiciones lo usan y si nada lo usa.
- La pestaña **Revisión** lista los modelos que nada usa, las definiciones cuyo modelo falta, los tipos que tienen una sola variante y los errores del mod.
- Cuando se vuelve a correr un script de Blender, el modelo cambia solo en el visor: lee `data/mods` del código fuente (D-3003).

Controles: arrastrar con el botón izquierdo gira la cámara, con el derecho la mueve; la rueda acerca. F encuadra lo que se ve y F5 vuelve a leer los mods.

### Revisar animaciones en el visor

Para validar las animaciones antes de meterlas al juego (fase 45). El visor usa el mismo renderizador y la misma animación que el juego, así que lo que se ve ahí es lo que se verá en el juego.

- **Modelos en estudio:** en la lista de mods aparece "Modelos en estudio", que muestra los `.glb` de `art/studies/animals` sin tocar `core`. Otra carpeta: `SalvaCiudadModelos.exe --estudio <carpeta>`. Se leen solo los archivos de la carpeta, no sus subcarpetas, y se recargan solos cuando cambian. Un modelo nuevo aparece con F5.
- Al elegir un modelo con esqueleto, bajo la lista de animaciones de la ficha:
  - **Pausa**, y las flechas para ir un fotograma atrás o adelante (mantener presionado repite). Se muestra el fotograma actual y el total.
  - **Velocidad** de 0,25× a 2× (clic derecho vuelve a 1×).
  - **Suelo en movimiento:** si la animación tiene una velocidad guardada (`walk_speed`, `run_speed`), la cuadrícula avanza bajo el modelo a esa velocidad. Una pata apoyada que sigue sobre la misma línea no patina.
  - **Mostrar el esqueleto:** los huesos, dibujados sobre el modelo en la pose del momento.

La lista se recorre con el teclado (W A S D, las flechas o las del teclado numérico): arriba y abajo pasan de un elemento a otro y lo muestran al momento; derecha abre una categoría o un tipo con variantes (o entra en él si ya está abierto), e izquierda lo cierra (o sube a la categoría o tipo que lo contiene). Mientras se escribe en el buscador, las teclas escriben.

## Sonidos

Los efectos de sonido también salen de un script versionado, en Python puro (sin Blender ni bibliotecas):

```
python art/audio/make_sounds.py data/mods/core/sounds
```

Son WAV mono de 16 bits a 22 050 Hz; el juego no acepta otro formato. Generar dos veces da archivos idénticos.

## Cimientos de los edificios (fase 65)

Todos los edificios menos murallas, empalizadas, portones y trampas llevan bajo el piso (Z = 0) un bloque de cimientos de piedra de 4,5 m, del tamaño de la planta del modelo: `foundation(mb)` en `art/blender/buildings.py`, que `export` llama solo. El juego pone el piso a la altura del suelo frente a la puerta; en una ladera, los cimientos son lo que se ve ladera abajo. Un edificio nuevo los recibe sin hacer nada; para que un modelo siga al terreno (sin cimientos) su nombre va en `ON_GROUND`.
