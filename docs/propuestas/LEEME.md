# Modelos en propuesta

Una página local para ver modelos 3D que **todavía no están en el juego**, probar sus animaciones y decir qué función tendría cada uno. Con tus respuestas se escribe después el plan de implementación.

## Abrirla

1. Abre `docs/propuestas/index.html` con **Edge o Chrome** (doble clic).
2. Pulsa **Abrir respuestas.json** y elige `docs/propuestas/respuestas.json`. Da permiso de edición cuando el navegador lo pida.

Desde ahí cada respuesta se guarda sola en ese archivo. La próxima vez basta con **Reconectar respuestas.json**. La página no usa internet.

Sin abrir el archivo también se puede revisar: las respuestas quedan en el navegador y pasan al archivo en cuanto lo abras. En Firefox la página no puede escribir el archivo: usa **Descargar** y reemplaza `respuestas.json`.

## Qué hay

- **★ Destacados**: los grupos que más vale la pena mirar de cada familia. Hay cientos de grupos; conviene empezar por aquí.
- **Categorías** a la izquierda, con cuántos grupos respondiste de cada una. Filtros: sin responder, respondidos, descartados, solo con animaciones, y un buscador.
- **Cada tarjeta es un grupo**: una idea (un puente de arco, un goblin) con todas sus variantes de forma o material.
- **Categorías nuevas respecto a lo que pediste**, porque salieron ideas que no cabían en las otras: *Maravillas y monumentos* (obras grandes con sus etapas de construcción), *Personajes* (aldeanos por oficio, combatientes, jinetes), *Magia y alquimia*, y *Sucesos y desastres* (tornado, inundación, incendio forestal, plagas… y lo que el pueblo usa contra ellos).
- La categoría **Decoraciones del juego** no trae modelos nuevos: son las 149 decoraciones que el juego ya tiene, agrupadas por tema, con propuestas para que hagan algo más que subir el entorno (el tendedero como anexo de la casa vecina, el gallinero que da huevos, las ruinas que se pueden restaurar). Se ven sin los cimientos que el juego les pone bajo el suelo.
- Al abrir un grupo:
  - el **modelo en 3D**: arrastrar gira, el botón derecho mueve, la rueda acerca. Se puede ver junto a un aldeano de 1,8 m, sobre una cuadrícula de 1 m, con el nivel del agua, con las aristas o girando solo;
  - la **lista de animaciones** del modelo: cada botón reproduce una, con pausa y velocidad;
  - las **variantes** abajo: ★ marca tu favorita y ✕ la descarta. El botón **"Las N variantes juntas"** las pone lado a lado en la misma vista (hasta 30), con la misma animación en todas, para comparar materiales o ver un juego de piezas completo;
  - a la derecha, las **propuestas de función** (hasta 4). Elige una, redacta la tuya en "Otra función", o marca "Solo decoración" o "Descartar". La nota es para cambios al modelo, combinaciones o dudas.
- Teclas: `1` a `4` eligen una propuesta, `S` solo decoración, `X` descartar, `N` siguiente sin responder, `←` `→` cambian de grupo, `↑` `↓` de variante, `Esc` cierra. Con la casilla **"Al elegir, pasar al siguiente grupo sin responder"** se revisa de corrido.

## Probar los muros modulares

`docs/propuestas/muros.html` (enlace "Probar muros modulares" en la página) es un banco de pruebas del algoritmo de muros: una cuadrícula de celdas de 2 m donde cada clic pone o quita un tramo, y la pieza de cada celda (pilar, remate, recto, esquina, unión en T o cruce) y su giro se eligen solos mirando a las 4 celdas vecinas. Arriba se elige el tipo de muro o de cerca entre todos los juegos de piezas generados. Con la herramienta **Puerta**, una celda suelta es un postigo de 2 m y dos seguidas forman una puerta de 4 m ("Abrir puertas" reproduce su animación); con **Torre**, la celda lleva una torre de 4 × 4 m del material del muro. "Ejemplo" dibuja un recinto con torres en las esquinas, puerta, muro interior con postigo y un pilar suelto. El trazado se recuerda en el navegador.

En el mismo desplegable están los **juegos de trazado** que siguen la misma regla sin ser muros: raíles de mina (madera, hierro y enanos, con placa giratoria en las uniones y tope en los finales), canal de piedra y acequia de tierra, y calles (empedrada, pasarela de tablones y camino de tierra). Con ellos no hay torres; en el canal de piedra, la herramienta **Puerta** pone una compuerta que sube y baja con "Abrir puertas".

## Probar los puentes modulares

`docs/propuestas/puentes.html` arma un puente del largo que marques (de 10 a 60 m, de 2 en 2) con las piezas del kit del material elegido: un estribo con rampa en cada orilla, tramos de 4 m (y uno de 2 m si hace falta), una pila bajo cada junta entre tramos y postes con farol al pie de las rampas. Se ve sobre un río entre dos orillas, para comprobar que las pilas llegan al fondo. En el mismo desplegable están los dos **acueductos** (piedra y ladrillo): se arman de 4 en 4 m con un tramo de arco por módulo, una pila en cada junta y el final con su caída de agua.

## Escena de muestra

`docs/propuestas/escena.html` pone unos treinta modelos juntos en un valle, a su escala y con sus animaciones (el castillo sobre un risco con cascada, el puente de arcos, el molino, la posada, los barcos, el campamento con el estandarte), como en la imagen de referencia. Sirve para ver cómo conviven los tamaños. Los árboles son los del juego: `python tools/propuestas/escena.py` los copia a `escena_arboles.js`.

## Cómo lo uso yo

Cuando me digas "revisa las propuestas", leo tus respuestas y escribo el plan por fases en la especificación, con las funciones que elegiste, tus textos y tus notas:

```
python tools/propuestas/propuestas.py respuestas          # lo que respondiste
python tools/propuestas/propuestas.py respuestas --todo   # también lo que falta
python tools/propuestas/propuestas.py resumen             # cuántos modelos hay y avisos
```

## De dónde sale cada cosa

| Qué | Dónde |
|---|---|
| La página | `docs/propuestas/index.html` (Three.js r147 vendorizado en `vendor/three`, licencia MIT) |
| Tus respuestas | `docs/propuestas/respuestas.json` |
| Lo que la página muestra | `docs/propuestas/datos/` (lo escribe el empaquetador; no se edita a mano) |
| Scripts de los modelos y catálogos | `art/blender/proposals/<familia>/` (ver su `LEEME.md`) |
| Modelos generados (`.glb`) | `art/studies/propuestas/<familia>/` (no se versionan) |

Regenerar una familia y volver a empaquetar:

```
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup --python art/blender/proposals/<familia>/build.py
python tools/propuestas/propuestas.py empaquetar
```

El empaquetador mete cada `.glb` en un script de `datos/modelos/` para que la página funcione abierta desde el disco, sin servidor. `datos/` pesa cientos de MB y se vuelve a generar, así que git la ignora (`docs/propuestas/.gitignore`): en una copia nueva del repositorio hay que regenerar los modelos y empaquetar. Los modelos también se pueden ver en el visor del juego: `SalvaCiudadModelos.exe --estudio <ruta de art/studies/propuestas/<familia>>`.

## Familias

Al cierre hay **773 grupos, 2499 modelos y 2682 animaciones**; 203 grupos están en "★ Destacados". Las ocho primeras familias las generaron agentes en paralelo; las demás, la sesión principal.

| Familia | Qué trae | Grupos | Modelos |
|---|---|---:|---:|
| `walls` | Muros modulares (20 tipos, incluidos los de cada raza), puertas, torres, cercas y defensas | 64 | 671 |
| `buildings` | Castillos, posada, molinos y versiones elaboradas de los edificios | 86 | 223 |
| `bridges` | Puentes, kit modular de puente, muelles y barcos | 97 | 201 |
| `creatures` | Mascotas, animales de granja y de ambiente, enemigos y monstruos | 50 | 137 |
| `folk` | Aldeanos por oficio, combatientes, jinetes y monturas | 48 | 127 |
| `wonders` | Maravillas con sus etapas de obra y monumentos | 33 | 104 |
| `races` | Arquitectura propia de cada raza no humana | 48 | 64 |
| `beasts` | Grandes bestias de fantasía, fauna de mar y más mascotas | 32 | 53 |
| `decor` | Las 149 decoraciones que el juego ya tiene, con propuestas de función | 27 | 149 |
| `piles` | Pilas de cada recurso por cantidad | 4 | 102 |
| `gear` | Herramientas por material, armas, escudos, cascos | 20 | 54 |
| `lines` | Raíles, canales y calles en las seis piezas de los muros | 8 | 49 |
| `states` | Carteles de oficio y ruinas quemadas por huella | 2 | 43 |
| `scatter` | Rocas, hierbas, flores, arbustos, huellas | 8 | 39 |
| `farm` | Granja, cultivos por etapas, riego | 18 | 37 |
| `nature` | Cascada, riscos, géiser, yacimientos, guaridas | 17 | 37 |
| `heraldry` | Bandera, estandarte, pendón y mojón de cada raza | 4 | 36 |
| `roads` | Señales, farolas, avisos, árboles caídos y otras cosas del camino | 18 | 34 |
| `biomes` | Elementos propios de cada bioma | 14 | 33 |
| `magic` | Piedras de poder, círculos, arcos de paso, taller de gólems | 15 | 29 |
| `transport` | Carretas, carruajes, máquinas de asedio, globo | 18 | 28 |
| `arms` | Arma, escudo y casco de cada raza | 3 | 27 |
| `town` | Cementerio, entrenamiento, fiestas | 14 | 27 |
| `annexes` | Anexos de casa que mejoran su entorno | 18 | 24 |
| `camp` | Campamento de exploradores | 15 | 23 |
| `water` | Pozos, aljibe, acueducto modular, tuberías, puesto contra incendios | 8 | 21 |
| `adventure` | Cofres, hallazgos, trampas, cuarentena | 7 | 20 |
| `works` | Grúas, andamios y talleres de obra | 13 | 20 |
| `trade` | Puestos por mercancía, peso público, recua | 10 | 19 |
| `events` | Tornado, inundación, incendio forestal, plagas | 9 | 17 |
| `crafts` | Un puesto de trabajo por oficio | 13 | 15 |
| `lairs` | Guaridas de enemigos | 13 | 15 |
| `sites` | Lugares por descubrir: cripta, ruinas, osamenta gigante | 12 | 12 |
| `sky` | Dirigible, torre de amarre, planeador, alfombra voladora | 7 | 9 |
| **Total** | | **773** | **2499** |

## Defectos conocidos

Lo que se sabe que no quedó bien, para tenerlo presente al elegir (en la nota de cada grupo puedes pedir el arreglo):

- **Muros:** los muros son simétricos (almenas a los dos lados), así que braseros, pendones y frentes de puerta solo quedan bien orientados en la demostración `autotile`. En los muros gruesos, la esquina, la T y el cruce son casi todo nudo. Las cadenas del puente levadizo giran rígidas y atraviesan el muro al subir; el rastrillo levantado se mete en la mampostería. La pieza diagonal no empalma con los rectos sin un pilar.
- **Puentes y barcos:** en el puente colgante quedan huecos de milímetros entre tramos de cuerda al mecerse; velas y llamas son piezas rígidas; los arcos de los extremos de los puentes de lomo son más bajos; varias propuestas suponen recursos nuevos (sal, cuerda, cristal, hueso).
- **Edificios:** las huellas no son metros enteros exactos; las aspas de los molinos salen de la huella; tejados que se cruzan sin limahoya (casa señorial, monasterio); sin interiores (las puertas abiertas son un plano oscuro). Los castillos pesan hasta 3,7 MB cada uno.
- **Criaturas:** en algunos clips hay piezas unos centímetros bajo el suelo (árbol andante, gólem, cíclope, trol al golpear); alas pequeñas al volar en pato, ganso, cisne y rapaces; el halcón y el búho se ven rechonchos; el chamán goblin no tiene clip de conjuro.
- **Maravillas:** las estatuas grandes (coloso, enanos de la puerta) se ven cuadradas; en las ruinas la hiedra son rectángulos planos; el haz del faro es un cono opaco; algunos andamios pisan otras piezas; el minutero del reloj da 12 vueltas en 36 s para que el clip cierre.
- **Arquitectura por raza:** el agente no llegó a entregar su informe de defectos; se miró una hoja de miniaturas de las ocho razas y pasó la comprobación de clips, nada más. Cada raza tiene ocho piezas (tres casas, centro, taller, almacén, torre y un edificio propio); faltan santuario, puesto de mercado, granja y pozo.
- **Personajes:** en reposo las herramientas quedan tendidas hacia delante (convención del juego); se ven bien en `idle`. El mandil queda rígido; los escudos que no van en guardia aletean al correr. Las monturas tienen patas rectas y los pies resbalan un poco; los guardias de raza no llevan yelmo ni armadura. Dos tercios de las animaciones no se miraron.
- **Bestias:** las alas de plumas plegadas quedan como un abanico hacia atrás; el aliento de fuego aparece de golpe; el cangrejo camina de frente y el conejo camina en vez de saltar; `die` es casi siempre una caída genérica de costado. La mayoría de las animaciones solo pasaron la comprobación automática.
- **Mis familias:** los animales de tiro son figuras rígidas simples; varios modelos tienen montículos o rocas medio enterrados (cueva, mina abandonada, alud, socavón), a propósito; la cabeza colosal se lee mal desde algunos ángulos; las dos alfombras voladoras se distinguen poco.
- **En general:** no hay materiales translúcidos ni emisivos (vidrio, agua y luces son colores lisos); `kit.Mech` solo gira y traslada huesos, así que nada se estira ni cambia de tamaño.

## Decisiones tomadas al hacer esto

No están en `docs/DECISIONES.md` porque esa noche otra sesión lo tenía a medio editar; quedan aquí para pasarlas cuando convenga.

- **Nada toca el juego.** Todo vive en `art/blender/proposals/`, `art/studies/propuestas/` (sin versionar), `docs/propuestas/` y `tools/propuestas/`. No se cambió ningún archivo de `src/`, `data/` ni los scripts de arte existentes; `art/blender/proposals/_kit.py`, `_shapes.py` y `_animals.py` solo los importan.
- **Three.js r147**, la última versión con archivos clásicos (`three.min.js` y `examples/js`), porque una página abierta desde el disco no puede cargar módulos. Se descargó una vez de jsDelivr y está vendorizada con su licencia MIT.
- **Los modelos viajan como scripts** (`datos/modelos/*.js`, el `.glb` en base64): es lo único que una página abierta con doble clic puede leer sin servidor. Por eso existe el empaquetador.
- **Las respuestas** se guardan con el mismo mecanismo que el registro de revisión (API de acceso a archivos de Edge y Chrome), con copia en el navegador, escritura en un archivo temporal y lectura estricta: solo se aceptan los campos conocidos.
- **Un grupo es una idea con sus variantes**, y las propuestas de función son del grupo: así se decide una vez por idea y no una por cada material.
- **Partes rígidas con esqueleto** (`kit.Mech`): cada pieza móvil sigue un hueso entero. Los clips tienen giros y también desplazamientos de hueso; si el motor del juego solo admite giros, los clips con desplazamiento (compuertas, rastrillos, vagoneta, proyectiles, humo) habría que adaptarlos al implementarlos.
- **Los animales de tiro** (caballo, buey, vaca, oveja de `_animals.py`) son figuras de partes rígidas para acompañar a los vehículos y corrales: si esos modelos entran al juego, conviene sustituirlos por los del zoológico, que tienen su esqueleto completo.
- **Sin límites de triángulos ni de tamaño**, como pediste. Varios modelos pasan de 20 000 triángulos (castillos, catedral): al implementar habrá que decidir límites o versiones lejanas.
- **Miniaturas:** un modelo con clip `idle` se retrata en el primer cuadro de ese clip, porque los personajes en reposo llevan la herramienta tendida hacia delante (convención del juego).
- **Sin revisar una a una:** de cada familia se miró al menos una hoja de miniaturas y se pasó la comprobación de clips (`propuestas.py revisar`), pero no cada variante de material ni cada animación; los defectos que se conocen están en la sección "Defectos conocidos".
- **No se hizo ningún commit.** `docs/propuestas/.gitignore` deja fuera `datos/` y `escena_arboles.js`, que se regeneran.
- **Agentes en paralelo:** hasta cuatro a la vez, uno por familia grande (primero muros, puentes y barcos, edificios y criaturas; después maravillas, arquitectura por raza, personajes y grandes bestias); las demás familias las hice yo.
- **Razas:** donde un modelo tiene versión por raza se usaron las nueve de `races.json` (humanos, gatos, enanos, elfos, elfos oscuros, zorros, ranas, lagartos y orcos). Los colores y emblemas de las banderas son una propuesta mía: no salen de ningún archivo del juego.
- **Recursos que el juego no tiene:** varias propuestas suponen recursos u oficios nuevos (cal, sillares, tablas, vigas, cristales, maná, sal, cuerda). Están dichas como idea; al elegir una de esas, el plan tendrá que incluir el recurso.

## Formato de `respuestas.json`

```json
{
  "version": 1,
  "grupos": {
    "bridges/bridge_stone_arch": {
      "eleccion": "propuesta",
      "indice": 1,
      "titulo": "Peaje a mercaderes",
      "texto": "Lo que redactaste en \"Otra función\"",
      "nota": "Tu nota",
      "modelos": {"bridge_stone_arch_brick": "favorito", "bridge_stone_arch": "descartado"},
      "fecha": "2026-10-04T10:15:00.000Z"
    }
  }
}
```

`eleccion` es `propuesta` (con `indice` y `titulo`), `propia` (con `texto`), `decoracion` o `descartar`. Al leer el archivo, la página se queda solo con estos campos y descarta lo demás; si el archivo no tiene esta forma, no lo toca. Se escribe en una copia temporal que reemplaza al archivo al terminar.
