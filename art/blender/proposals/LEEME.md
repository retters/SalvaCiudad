# Modelos en propuesta

Modelos low poly que **todavía no están en el juego**. Se generan para que Salvador los revise en `docs/propuestas/index.html`, elija qué función tendría cada uno y, con eso, se escriba el plan de implementación. Nada de aquí toca el juego.

## Dónde va cada cosa

| Qué | Dónde |
|---|---|
| Scripts de una familia | `art/blender/proposals/<familia>/` (un `build.py` y los módulos que haga falta) |
| Catálogo de la familia | `art/blender/proposals/<familia>/catalogo.json` |
| Modelos generados | `art/studies/propuestas/<familia>/<id>.glb` (no se versionan) |
| Vistas previas | `art/studies/propuestas/<familia>/preview/` |
| Piezas comunes | `art/blender/proposals/_kit.py`; ejemplo mínimo en `_demo/build.py` |

Generar una familia (o solo algunos modelos, por su id):

```
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup --python art/blender/proposals/<familia>/build.py -- [ids]
```

Empaquetar todo para la página: `python tools/propuestas/propuestas.py empaquetar`.

## Reglas para quien genera modelos

1. **Solo se crean o cambian archivos** en `art/blender/proposals/<tu familia>/` y en `art/studies/propuestas/<tu familia>/`. Todo lo demás del repositorio es de solo lectura: hay otras sesiones trabajando en el juego y en otras familias. Se puede importar y reutilizar `common.py`, `buildings.py` (colores y piezas como `cottage`, `gable_roof`, `barrel`, `crate`, `fence`), `rigs.py`, `studies.py` y los demás scripts de `art/blender`, sin modificarlos. `_kit.py` tampoco se modifica: si falta algo, se resuelve dentro de la familia y se anota en el informe final.
2. **Nada de git que cambie estado** (`add`, `commit`, `checkout`, `stash`, `clean`), nada de red, nada de dependencias nuevas, nada del MCP de Blender: Blender se usa sin interfaz con el comando de arriba, un solo proceso a la vez por familia.
3. Los archivos se escriben con las herramientas Write y Edit, nunca con `Get-Content`/`Set-Content` ni `sed` (rompen UTF-8).
4. **Código en inglés** (identificadores, comentarios, nombres de archivo e ids). **Textos del catálogo en español.**
5. **Convenciones del juego** (`docs/ARTE.md`): metros; Z arriba; el frente hacia −Y; apoyado en Z = 0 con el origen en el centro de la base; sombreado plano; materiales de color liso sin texturas. Una celda del mapa mide 1 m; un aldeano, 1,7 a 1,9 m; una puerta, 0,95 × 1,6 m. Lo que se construye sobre el mapa ocupa un número entero de metros.
6. **Estilo:** low poly "medio" de caras planas, con detalle que se lea desde la cámara del juego (vigas, marcos, almenas, tejas en hileras, remaches). Sin límite de triángulos ni de tamaño: un castillo puede medir 30 m y tener 20 000 triángulos. Lo que importa es que se vea bien y que cada pieza tenga volumen (nada de planos sueltos de una cara).
7. **Variantes de material:** cuando tenga sentido, el mismo generador recibe una paleta y produce el modelo en los materiales que el juego ya tiene: troncos (`core:log`), piedra (`core:stone`), ladrillo (`core:bricks`), tejas (`core:roof_tiles`), arcilla (`core:clay`), hierro (`core:iron`), paja, lino (`core:linen`), cuero (`core:leather`), oro (`core:gold`). Cada variante es un modelo más del mismo grupo.
8. **Animaciones:** lo que se mueve, se anima (ruedas, aspas, puertas, puentes levadizos, banderas, llamas, criaturas). Las partes rígidas, con `kit.Mech`; las criaturas orgánicas, con las plantillas de `rigs.py` (`Quadruped`, `Beast`), `rigs_bird.py`, `rigs_swim.py` y `rigs_human.py`, como hacen `zoo/` y `people/`. Nombres de clip en inglés (`idle`, `walk`, `attack`, `open`, `turn`). Un clip que se repite termina en la pose con que empieza.
9. **Mirar lo que se genera.** Después de cada tanda se hacen vistas previas y se revisan con la herramienta Read (son PNG):
   ```
   & "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup --python art/blender/study_preview.py -- art/studies/propuestas/<familia> art/studies/propuestas/<familia>/preview [ids]
   ```
   Se corrige lo que se vea mal (piezas flotando, caras invertidas, proporciones, colores que no se distinguen). No hace falta mirar cada variante de material: basta una por forma.
10. **No repetir lo que ya existe.** El juego ya tiene 46 edificios y 149 decoraciones (`data/mods/core/defs/buildings.json`, scripts en `art/blender/buildings.py` y `art/blender/decor/`), 26 animales de estudio (`art/blender/zoo/`), 17 personajes (`people/`) y 40 armas y herramientas (`weapons/`). Una versión claramente más elaborada o con otra función sí vale.
11. **El catálogo se mantiene al día:** al terminar cada tanda, `catalogo.json` es JSON válido y describe todos los modelos ya generados, para que la página pueda mostrar el avance en cualquier momento.

## `catalogo.json`

Un **grupo** es una idea (un puente de arco, un goblin, un tendedero) con todas sus variantes de forma o material. Las propuestas de función son del grupo: Salvador elige una por grupo, o escribe la suya.

```json
{
  "familia": "bridges",
  "grupos": [
    {
      "id": "bridge_stone_arch",
      "nombre": "Puente de arco de piedra",
      "categoria": "Puentes",
      "descripcion": "Puente de un arco, de 8 m de largo y 3 m de ancho, con pretiles.",
      "propuestas": [
        {"titulo": "Cruzar ríos", "detalle": "Se construye sobre un río de hasta 6 m; los aldeanos y las carretas lo cruzan sin rodear."},
        {"titulo": "Peaje a mercaderes", "detalle": "Los mercaderes que lo cruzan pagan unas monedas al pueblo dueño del puente."}
      ],
      "modelos": [
        {"id": "bridge_stone_arch", "nombre": "Piedra", "material": "piedra"},
        {"id": "bridge_stone_arch_brick", "nombre": "Ladrillo", "material": "ladrillo",
         "animaciones": {"open": "Se levanta el tramo central"}, "nota": "Opcional: algo que valga la pena decir de este modelo."}
      ]
    }
  ]
}
```

- `id` de cada modelo = nombre de su `.glb`, sin extensión. Ids en minúsculas con `_`, únicos en toda la familia y con un prefijo que no choque con otras familias.
- `categoria`, una de: `Muros y defensas`, `Puentes`, `Castillos y fortalezas`, `Maravillas y monumentos`, `Edificios`, `Personajes`, `Mascotas y animales`, `Enemigos y criaturas`, `Naturaleza y terreno`, `Caminos`, `Anexos de casas`, `Transporte`, `Armas y herramientas`, `Campamento y exploración`, `Granja y riego`, `Vida del pueblo` (cementerio, fiestas, entrenamiento), `Magia y alquimia`, `Sucesos y desastres`, `Pilas de recursos`. La categoría `Decoraciones del juego` es de la familia `decor`: las 149 decoraciones que el juego ya tiene, copiadas de `core` por `decor/make.py` para proponer qué más podrían hacer.
- `propuestas`: de 1 a 4 por grupo, **concretas y pensadas para este juego**: qué mecánica tocaría (recursos, oficios, comercio, defensa, felicidad y entorno de las casas, enfermedades, exploración, incursiones, estaciones, día y noche, mercaderes, razas), qué costaría y qué daría. Antes de escribirlas conviene leer `ESPECIFICACION_SalvaCiudad.md` por encima y los `defs` de `data/mods/core`. Lo decorativo también lleva propuestas de función (un tendedero como anexo que mejora el entorno de la casa vecina), no solo "decoración".
- `destacado` (opcional, en el grupo): `true` en los pocos grupos que más vale la pena mirar de la familia (unos 6 a 15). La página los junta en "★ Destacados", por donde conviene empezar a revisar. Las familias cuyo catálogo lo reescribe su propio `build.py` (como `walls`) se marcan aparte, en `art/blender/proposals/destacados.json` (`{"familia": ["id de grupo", …]}`).
- `animaciones` (opcional): qué hace cada clip, en español. La lista de clips la lee la página del propio modelo.
- Triángulos, medidas y duración de los clips los calcula el empaquetador: no se escriben a mano.
