# Arte: modelos, esqueletos y animaciones

Todos los modelos del juego salen de **scripts de Blender versionados** en `art/blender/` (D-007). Así se pueden regenerar, mejorar y variar sin repetir trabajo a mano, y cualquier agente puede retomarlos.

## Generar los modelos

Con Blender 5.2 instalado, desde la raíz del repositorio:

```
blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models
```

- `--background` no abre la interfaz ni toca tus escenas abiertas.
- `--factory-startup` ignora tus preferencias y complementos, para que el resultado no dependa del equipo.
- Se puede limitar a un grupo: `characters`, `props`, `trees` (y después, las especies: `trees oak elm`), `buildings` o `animals`, por ejemplo `... -- data/mods/core/models buildings`.
- Vista previa de los árboles, cada especie en sus tamaños junto a un aldeano: `blender --background --factory-startup --python art/blender/preview_trees.py -- data/mods/core/models tmp/arboles`.
- Los `.glb` generados se guardan en el repositorio, así compilar el juego no requiere Blender.

**Reproducible:** generar dos veces da archivos idénticos byte a byte. El exportador de Blender cambia el orden de los triángulos entre ejecuciones, así que `common.export_glb` los ordena después de exportar (D-402). Para comprobarlo, genera en dos carpetas y compáralas:

```
blender --background --factory-startup --python art/blender/build_all.py -- tmp/a
blender --background --factory-startup --python art/blender/build_all.py -- tmp/b
```

**Vistas previas** (imágenes PNG, sin abrir Blender):

```
blender --background --factory-startup --python art/blender/preview.py -- data/mods/core/models tmp/preview
```

Nota: el importador glTF de Blender reorienta los huesos y puede mostrar mal las poses animadas en estas vistas. La referencia es cómo se ven en el juego.

## Archivos

| Script | Genera |
|---|---|
| `common.py` | Utilidades: escena vacía, materiales, `MeshBuilder` (piezas con material y peso de hueso), exportación con opciones fijas |
| `human.py` | `characters/<raza>_male.glb` y `<raza>_female.glb` para humanos, enanos, elfos y gatunos (mismo esqueleto y animaciones `idle` y `walk`); accesorios `hat_straw`, `hat_cap`, `beard`, `apron_male` y `apron_female` |
| `props.py` | `props/tree_pine.glb`, `tree_oak.glb`, `rock.glb`, `ore_rock.glb`, `berry_bush.glb`, `herb.glb`, `house_small.glb` y `cloud.glb` |
| `trees.py` | `props/tree_<especie>_<tamaño>.glb`: 21 especies en sus tamaños (ver `docs/ARBOLES.md`) |
| `buildings.py` | `buildings/<id>.glb`: un modelo por edificio de `core` (46), cada uno del tamaño de su terreno |
| `animals.py` | `animals/deer.glb`, `boar.glb`, `wolf.glb` y `bear.glb` (sin esqueleto) |
| `build_all.py` | Ejecuta todo |
| `preview.py` | Imágenes de revisión |
| `studies.py` | Técnicas de modelado de los animales low poly; `build_final` es la de producción (remesh y reducción) |
| `zoo/*.py` | Un animal o planta low poly por archivo (ver abajo) |
| `zoo_build.py` | Genera los modelos de `zoo/` o, con `specs=<carpeta>`, los de `people/`, `weapons/` o `lowpoly_trees/` |
| `people/*.py` | Los 15 personajes low poly; `_human.py` es el cuerpo común |
| `weapons/wNN_*.py` | Las 40 armas y herramientas, numeradas como en la imagen de referencia |
| `lowpoly_trees/*.py` | 16 árboles en tres estados (48 modelos) desde un solo generador, `_tree.py` |
| `rigs.py` | Base de esqueletos, pesos y animaciones (`Rig`, `Pose`) y la plantilla de cuadrúpedo |
| `rigs_bird.py`, `rigs_swim.py` | Plantillas de aves y de nadadores (pez, tortuga, pulpo) |
| `rigs_human.py` | Esqueleto y animaciones de los personajes de `people/` |
| `tripo_build.py` | Anima un cuadrúpedo hecho en Tripo (`.fbx` con su esqueleto) y lo deja en `art/studies/tripo/` |
| `rig_check.py` | Verifica las animaciones de un modelo exportado |
| `study_preview.py` | Una imagen de revisión por modelo (4 vistas) y las tiras de sus animaciones |
| `pig_studies.py`, `tiger_studies.py` | El cerdito y el tigre con cada técnica, para compararlas |

## Convenciones

- **Unidades:** metros. Un humano mide unos 1,75 m (hombre) o 1,66 m (mujer).
- **Ejes en Blender:** Z arriba y el frente hacia **−Y**. Tras exportar a glTF queda Y arriba y el frente hacia **+Z**, que es lo que espera el juego (el giro de una instancia se mide desde +Z).
- **Apoyo:** los modelos se apoyan en Z = 0, con el origen en el centro de la base.
- **Estilo:** low-poly "medio" con sombreado plano. Caras y manos con algo de detalle; edificios con detalles arquitectónicos (vigas, marcos, contraventanas, tejas).
- **Materiales:** colores lisos, sin texturas, salvo que haga falta. Se exporta el color base (`baseColorFactor`).

### Materiales recoloreados por paleta

Si un material de un personaje o accesorio se llama como uno de estos espacios, el juego lo pinta con el color de la **paleta de cada aldeano**. Así 2000 aldeanos pueden verse distintos con los mismos modelos:

| Espacio | Nombre del material | Uso |
|---|---|---|
| 0 | `skin` | Piel |
| 1 | `hair` | Pelo, barba |
| 2 | `top` | Prenda de arriba |
| 3 | `bottom` | Pantalón o falda |
| 4 | `shoes` | Calzado |
| 5 | `belt` | Cinturón, cintas |
| 6 | `hat` | Sombrero |
| 7 | `apron` | Delantal |

Cualquier otro nombre (`eyes`, `mouth`…) conserva su color.

### Materiales recoloreados en los edificios

Lo mismo para los edificios (fase 31): si un material se llama como uno de estos espacios, cada edificio lo pinta con su **paleta**, elegida por su lugar en el mapa entre 150 combinaciones (5 techos, 6 paredes y 5 postigos):

| Espacio | Nombre del material | Uso |
|---|---|---|
| 0 | `var_roof` | Techo |
| 1 | `var_roof_dark` | Hileras oscuras del techo, cobertizos |
| 2 | `var_walls` | Paredes y hastiales |
| 3 | `var_shutter` | Postigos |

Hoy las usan las casas. El color que tenga el material en Blender es solo para la vista previa y para el visor, que puede recorrer las paletas con "Otros colores".

### Esqueleto humano

17 huesos, con los mismos nombres para los dos cuerpos: `hips`, `spine`, `chest`, `neck`, `head`, `upper_arm.L/R`, `lower_arm.L/R`, `hand.L/R`, `thigh.L/R`, `shin.L/R` y `foot.L/R`. `.L` es el lado izquierdo del personaje (+X en Blender).

- La **cabeza tiene el mismo tamaño** en los dos cuerpos, para que los sombreros sirvan a ambos.
- Cada pieza del cuerpo va unida a un hueso (piel rígida por pieza). Las piezas se solapan en las articulaciones para que no se abran huecos al doblarse. Más adelante se puede pasar a pesos suaves sin cambiar el motor, que ya mezcla hasta 4 huesos por vértice.

### Animaciones

- Cada **acción** de Blender se exporta como una animación glTF con su nombre (`idle`, `walk`).
- Los ciclos repiten en el último fotograma la pose del primero. El juego muestrea a **30 fotogramas por segundo** y descarta ese último fotograma repetido.
- `walk`: 1 s por zancada completa, pensado para caminar a **1,45 m/s**. El juego acelera o frena la animación según la velocidad real, para que los pies no patinen.
- `idle`: respiración y balanceo leve, 2 s.
- Las poses se escriben como rotaciones en el espacio del esqueleto (`pose_key` en `human.py`), así es fácil ajustar ángulos o agregar animaciones nuevas (talar, cargar, construir…).

### Accesorios

Un accesorio es un **modelo rígido cuyo origen es el punto donde se fija**: el comienzo de un hueso (`head` es la parte alta del cuello; `hips` es la pelvis). El juego lo lleva a la posición de ese hueso en la pose de reposo del cuerpo y lo mueve con la animación de ese hueso (D-404). Qué accesorio va en qué hueso está en `src/game/builtin_models.h`.

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

Los 24 modelos de la imagen de referencia `Animales low poly.png` (en la raíz del repositorio, del usuario). Todavía no están en el juego: entran en la fase 47.

- **Técnica:** se compararon diez técnicas con el cerdito y el tigre (`pig_studies.py`, `tiger_studies.py`) y el usuario eligió la de *remesh* y reducción (D-4401). `studies.build_final` suelda las partes de la especificación (elipsoides y cápsulas) en una sola superficie y la reduce a `budget` triángulos. Después la corta donde un borde de color debe ser nítido (`bands` para rayas, `cuts` para bordes sueltos), pinta cada cara con `paint()`, aplana las puntas de otro color (`caps`, como el hocico del cerdito) y agrega tonos claros y oscuros a las facetas. Al final pone las piezas finas que no sobreviven al *remesh* (`details()`: orejas, cuernos, alas, aletas, hojas).
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

De las imágenes de referencia del usuario en la raíz del repositorio (`Personajes 1` a `3`, `Armas y herramientas` y `Arboles 1` a `3`). Tampoco están en el juego todavía. Se generan igual que los animales, con la carpeta de especificaciones:

```
blender --background --factory-startup --python art/blender/zoo_build.py -- art/studies/people specs=people [nombres]
blender --background --factory-startup --python art/blender/zoo_build.py -- art/studies/weapons specs=weapons [nombres]
blender --background --factory-startup --python art/blender/zoo_build.py -- art/studies/trees specs=lowpoly_trees [nombres]
```

Para verlos en el visor: `SalvaCiudadModelos.exe --estudio people` (o `weapons`, `trees`, `animals`, `tripo`). `--estudio` acepta el nombre de una carpeta de `art/studies` o una ruta, y abre el visor directamente en esa carpeta.

- **Personajes** (`people/`, límite de 3000 triángulos): todos heredan de `Human` en `_human.py`, un cuerpo de partes soldadas con nombre (cabeza, pecho, antebrazo…) y las articulaciones en el mismo lugar, para que después compartan esqueleto. Cada personaje cambia proporciones, agrega volúmenes de ropa en `customize()`, pinta por zona del cuerpo con `zone()` y pone lo fino en `details()`. Las proporciones salen de medir cada referencia (D-4411).
- **Armas** (`weapons/`, límite de 500 a 600): piezas directas y facetadas en `details()`; el *remesh* solo en lo orgánico (báculos, garrote, martillo de piedra). De pie sobre Z = 0, con el lado ancho hacia −Y. Cada una declara `grip`, el punto donde se sujeta (D-4412).
- **Árboles** (`lowpoly_trees/`, límite de 2500 con hojas y 1500 sin hojas): `<especie>_<variante>_<estado>`, con estados `bloom`, `autumn` y `bare` que comparten tronco y ramas. `_trace.py` (se corre a mano con Python y PIL) lee las tres imágenes y escribe `_traced.py`: ramas, masas de follaje y colores de otoño. Los modelos se generan solo con `_traced.py` (D-4413).

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
- **Personajes** (fase 48, `rigs_human.Humanoid`): los 17 huesos de los aldeanos (`hips`, `spine`, `chest`, `neck`, `head`, y por lado `upper_arm`, `lower_arm`, `hand`, `thigh`, `shin`, `foot`), más los que agregue cada personaje (cola, capa, coleta, faldas). Animaciones: `idle`, `walk`, `run`, `chop` (talar), `shoot` (arco), `fish_cast`, `fish_stand` y `fish_sit`.
  - La herramienta es un modelo aparte. El modelo dice en qué mano va en cada animación, en los *extras* del esqueleto: `chop_prop` = `axe:hand.R`, `shoot_prop` = `bow:hand.L`, `fish_*_prop` = `rod:hand.R`. Va con su eje largo (su +Z) hacia el frente de la mano, que es −Y con el brazo colgando en reposo, y con su punto `grip` en el centro de la mano. Las tiras de revisión la muestran puesta.
  - Una animación que no se repite lleva `<animación>_loops` = 0 (`die`, `hide`, `fish_cast`).
- **Verificar** un modelo exportado: `blender --background --factory-startup --python art/blender/rig_check.py -- art/studies/animals/pig.glb`. Comprueba tres cosas y termina en `RIG OK` o `RIG FAILED`:
  - que cada animación que se repite termina en la pose con que empieza;
  - que nada baja del suelo;
  - que los pies apoyados retroceden a la velocidad guardada (±10 %).

## Visor de modelos

`SalvaCiudadModelos.exe` se compila junto al juego (queda en `build\<preset>\bin\`) y sirve para revisar los modelos sin abrir el juego (D-3001):

- A la izquierda, los modelos del mod elegido por categoría (edificios, árboles, objetos del mapa, personajes y accesorios, animales). Al elegir un tipo se ven **todas sus variantes lado a lado**; al elegir un archivo, solo ese.
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
