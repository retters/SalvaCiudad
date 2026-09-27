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

Un accesorio es un **modelo rígido cuyo origen es el punto donde se fija**: el comienzo de un hueso (`head` es la parte alta del cuello; `hips` es la pelvis). El juego lo lleva a la posición de ese hueso en la pose de reposo del cuerpo y lo mueve con la animación de ese hueso (D-404). Hoy, qué accesorio va en qué hueso está en el código de la escena de prueba; en la fase 7 pasará a las definiciones de los mods.

## Cómo agregar un modelo

1. Escribe una función en el script que corresponda (o un script nuevo, llamado desde `build_all.py`), usando `MeshBuilder` y `common.export_glb`.
2. Genera con el comando de arriba y revisa las vistas previas.
3. Si es un personaje, usa el esqueleto humano y nombres de material de la tabla de paletas.
4. Comprueba que regenerar da el mismo archivo.

## Sonidos

Los efectos de sonido también salen de un script versionado, en Python puro (sin Blender ni bibliotecas):

```
python art/audio/make_sounds.py data/mods/core/sounds
```

Son WAV mono de 16 bits a 22 050 Hz; el juego no acepta otro formato. Generar dos veces da archivos idénticos.
