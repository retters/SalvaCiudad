# SalvaCiudad

Juego 3D de construcción y supervivencia de pueblos medievales con multijugador de 1 a 12 jugadores. Motor propio en C++20 sobre SDL3. El diseño completo está en [ESPECIFICACION_SalvaCiudad.md](ESPECIFICACION_SalvaCiudad.md) y las decisiones en [docs/DECISIONES.md](docs/DECISIONES.md).

**Estado:** fase 7 de 21 (mods y datos). El contenido (recursos, edificios, árboles, biomas y tipos de mapa) es un mod, `core`, y se pueden agregar mods con datos, modelos, textos y reglas en Lua; ver [docs/CREAR_MODS.md](docs/CREAR_MODS.md). "Un jugador" genera un mapa y se puede recorrer; el pueblo jugable llega en la fase 8.

Requisito para jugar: una tarjeta gráfica compatible con Direct3D 12 (ver D-201).

## Compilar en Windows

Se necesita Visual Studio 2022 con las herramientas de C++ (MSVC x64). CMake y Ninja vienen con Visual Studio. Desde una consola "x64 Native Tools Command Prompt for VS 2022", **siempre la misma** para configurar y compilar:

```
cmake --preset release
cmake --build --preset release
ctest --preset release
```

- El ejecutable queda en `build\release\bin\SalvaCiudad.exe`, con la carpeta `data\` al lado.
- Presets de Windows: `debug`, `release` y `debug-asan` (con AddressSanitizer).
- Los sombreadores se compilan con el `dxc.exe` del Windows SDK, que viene con Visual Studio.
- Presets de Linux y macOS: `unix-debug`, `unix-release` y `unix-debug-asan`. Todavía no compilan, porque falta preparar los sombreadores para esas plataformas (D-201).

## Modelos

Los modelos de `data/mods/core/models` se generan con Blender desde los scripts de `art/blender`. Ver [docs/ARTE.md](docs/ARTE.md). Compilar el juego no requiere Blender.

## Dónde guarda sus datos

- Normalmente en `%APPDATA%\Salva\SalvaCiudad\`: `settings.json`, `logs\`, `saves\` y `mods\`.
- **Modo portable:** si existe un archivo `portable.txt` junto al ejecutable, todo se guarda en `userdata\`, al lado del ejecutable.
- Un `settings.json` dañado se renombra a `settings.json.bad-<fecha>` (nunca se borra) y el juego arranca con los valores por omisión.

## Teclas

Todas se cambian en Configuración → Controles, salvo Alt+Enter.

| Tecla | Acción |
|---|---|
| F11 | Cambia en ciclo: ventana, ventana sin bordes, pantalla completa |
| Alt+Enter | Alterna entre ventana y el último modo de pantalla completa |
| Esc | Cierra un diálogo, o vuelve al menú desde Configuración o la escena de prueba |
| F3 | Panel de estadísticas (FPS, objetos dibujados, sombras…) |
| W A S D o flechas | Mover la cámara |
| Q / E, o arrastrar con el botón central | Girar la cámara |
| Rueda del ratón, o + / - | Acercar y alejar |
| F4 | Cambiar de cámara: aérea, tercera persona, primera persona |
| Botón derecho o central (arrastrar) | Girar; en tercera persona también sube y baja la vista |
| Clic en un aldeano | Seleccionarlo y seguirlo (W A S D deja de seguirlo; clic en el suelo lo deselecciona) |
| Espacio | Pausa y reanuda la partida |
| 1 / 2 / 3 | Velocidad normal, doble o triple |
| R | Girar el edificio que se está colocando |
| Mayús + clic | Colocar varios edificios iguales |
| Clic derecho o Esc | Cancelar la colocación, o quitar la selección |
| F5 / F9 | Guardado rápido / cargar la partida más reciente |
| Ctrl+F3 | Herramientas de desarrollo |

Opciones de línea de comandos: `--instance <1-8>` usa una carpeta de datos y un puerto propios (para abrir varias ventanas en una PC) y `--loopback` limita el multijugador a esa misma PC. Ver `docs/RED.md`.

## Idiomas

Español, español de México (solo cambia el formato de números) e inglés. Para agregar otro idioma sin tocar el código, ver [docs/AGREGAR_IDIOMA.md](docs/AGREGAR_IDIOMA.md).

## Lista de verificación manual

Se completa en cada fase.

### Fase 1

- [ ] Sin `settings.json`, el juego abre en ventana sin bordes a pantalla completa.
- [ ] F11 pasa por los tres modos sin cerrarse ni quedar en negro; Alt+Enter vuelve a la ventana y regresa.
- [ ] En modo ventana, mover y redimensionar la ventana; cerrar y abrir: aparece en el mismo lugar y con el mismo tamaño.
- [ ] Maximizar la ventana, cerrar y abrir: sigue maximizada.
- [ ] Con dos monitores: mover la ventana al segundo, pasar a pantalla completa, y comprobar que se queda en ese monitor.
- [ ] Minimizar el juego: no consume CPU apreciable.
- [ ] Escribir texto inválido en `settings.json`: el juego arranca y deja el archivo como `settings.json.bad-<fecha>`.
- [ ] `logs\salvaciudad.log` registra el inicio, el modo de ventana y el backend de GPU.

### Fase 2

- [ ] La primera vez, el juego aparece en el idioma de Windows (español si Windows está en español).
- [ ] El menú principal muestra el logotipo "- SALVA -" / "CIUDAD" con la C más grande, y los siete botones.
- [ ] Al detener el puntero sobre un botón, aparece su ayuda emergente tras medio segundo.
- [ ] Los botones que aún no funcionan muestran "Próximamente"; Enter o Esc cierran el diálogo.
- [ ] Configuración → Idioma: cambiar a English y de vuelta a Español; todo el texto cambia al instante.
- [ ] Configuración → Pantalla: pasar a "Ventana sin bordes". Aparece "¿Conservar estos ajustes de pantalla?"; sin responder, a los 15 s vuelve a la ventana. Repetir y pulsar "Conservar".
- [ ] En pantalla completa, elegir otra resolución; comprobar que se aplica y que "Revertir" la deshace.
- [ ] Desactivar la sincronización vertical y elegir un límite de 60 FPS; el uso de la GPU baja.
- [ ] Configuración → Interfaz: probar cada tamaño de 75 % a 200 %, también con la ventana pequeña. Nada queda cortado; donde no cabe, aparece la barra de desplazamiento y la rueda del ratón funciona.
- [ ] Configuración → Controles: cambiar una tecla, usar una ya ocupada (aparece el aviso) y borrar una con Supr. Cerrar y abrir el juego: las teclas se conservan.
- [ ] "Restaurar valores por omisión" en cada pestaña devuelve solo esa pestaña.
- [ ] Configuración → Juego → "Abrir carpeta" abre la carpeta de datos.
- [ ] Todos los ajustes se conservan al cerrar y volver a abrir el juego.
- [ ] Borrar `data\lang` del juego instalado: el juego arranca en inglés (idioma incrustado).

### Fase 3

- [ ] El menú principal muestra detrás una escena 3D que gira despacio, y los botones se leen bien.
- [ ] "Escena de prueba 3D": la cámara se mueve con WASD y las flechas, gira con Q/E y con el botón central, acerca y aleja con la rueda, y se desplaza al llevar el puntero al borde. **¿Se siente como la de Farthest Frontier?** Anota lo que cambiarías: velocidad, inclinación o suavidad.
- [ ] Al acercarse, la cámara baja hacia el horizonte; al alejarse, mira más desde arriba.
- [ ] Las casas, los árboles y las rocas proyectan sombras, y los bordes de las sombras no titilan al mover la cámara.
- [ ] F3 muestra las estadísticas. Con la sincronización vertical desactivada, los FPS pasan de 60. Activar "Vista de estrés" (casi los 50 000 objetos en pantalla) y comprobar que siguen por encima de 60.
- [ ] Configuración → Gráficos: cambiar la calidad de Baja a Ultra; las sombras, la distancia de dibujo y el suavizado cambian al instante.
- [ ] Redimensionar la ventana y cambiar a pantalla completa con la escena abierta: no se deforma ni queda en negro.

### Fase 4

- [ ] En la escena de prueba, los aldeanos caminan con las piernas y los brazos coordinados y los pies no patinan. Algunos se detienen y respiran (animación de reposo).
- [ ] Hay hombres y mujeres con ropa de colores distintos, tonos de piel y de pelo variados, sombrero de paja o gorro, barba y delantal en algunos.
- [ ] Los sombreros, la barba y el delantal siguen la cabeza y la cadera al caminar, sin separarse del cuerpo.
- [ ] Los aldeanos proyectan sombra.
- [ ] Con F3, "Personajes dibujados" llega a unos 2000 al alejar la cámara, y los FPS siguen por encima de 60.
- [ ] La casa tiene entramado de madera, ventanas con contraventanas, puerta, chimenea y tejas; el pino y la roca se ven bien de cerca.
- [ ] Con Blender instalado, generar dos veces con `build_all.py` (ver docs/ARTE.md) da archivos idénticos.
- [ ] **Tu opinión del estilo:** ¿te gusta este low-poly para los personajes y la casa? Qué cambiarías (proporciones, nivel de detalle, colores).

### Modos de cámara (petición del 2026-09-26)

- [ ] En la escena de prueba, F4 pasa por Aérea, Tercera persona y Primera persona; la línea "Cámara:" de la ayuda lo indica.
- [ ] Tercera persona: arrastrar con el botón derecho gira en todos los ejes; al bajar mucho, la vista sube sola en lugar de atravesar el suelo.
- [ ] Primera persona: el ratón mira alrededor sin cursor visible, W A S D camina, Esc vuelve al menú y suelta el ratón.
- [ ] Clic en un aldeano: aparece el marcador y la cámara lo sigue en los tres modos. Girar sigue funcionando; W A S D deja de seguirlo.
- [ ] Primera persona siguiendo a un aldeano: se ve con sus ojos, y el aldeano no tapa la vista.

### Fase 5

Casi todo se verifica con pruebas automáticas (`ctest`).
- [ ] `ctest --preset release` y `ctest --preset debug` pasan, incluido el hash de referencia de la simulación (`sim_core`).
- [ ] F3 muestra "Tick de simulación" avanzando unas 10 veces por segundo, y el "Hash del estado" cambia cada segundo.

### Fase 6

- [ ] "Un jugador" abre "Partida nueva" con una semilla al azar. "Al azar" cambia la semilla; al hacer clic en la casilla se puede borrar con Retroceso y escribir otra.
- [ ] Generar un mapa Mediano con una semilla, volver al menú y generarlo otra vez con la misma semilla y los mismos ajustes: se ve igual (mismo lago, mismo río, mismo inicio).
- [ ] Un mapa Enorme muestra la barra de avance con sus etapas y tarda menos de 30 s. "Cancelar" (o Esc) vuelve a los ajustes.
- [ ] En el mapa hay ríos que llegan a un lago o al borde, lagos con orillas de arena, bosques de pinos y robles, claros, piedras, bayas y hierbas.
- [ ] El número 1 marca el inicio; con varias posiciones de inicio aparecen todos los números, lejos entre sí.
- [ ] Con F3 en un mapa Enorme, los FPS siguen por encima de 60 en los tres modos de cámara (F4), también en calidad Ultra.
- [ ] En Configuración, bajar "Vegetación" acorta la distancia a la que se ven los arbustos y las hierbas.
- [ ] Esc en el mapa abre el menú del juego: Continuar vuelve al mapa; Configuración se abre sobre el mapa y al cerrarla se vuelve a él; Salir al menú principal cierra el mapa y la escena de prueba sigue funcionando.
- [ ] Con la rueda se puede alejar la cámara hasta ver el mapa completo (provisional).
- [ ] En el inicio 1 hay una aldea de muestra (casas y aldeanos); clic en un aldeano para seguirlo.
- [ ] En Configuración > Pantalla, activar y desactivar varias veces la sincronización vertical: el juego no se cierra.
- [ ] **Tu opinión:** ¿te gustan los colores del suelo y del agua, el ancho de los ríos y la cantidad de bosque?

### Fase 6b (biomas, árboles y herramientas)

- [ ] En Partida nueva, "Tipo de mapa" cambia los bosques: Arboleda joven sin árboles grandes, Tierra de gigantes con árboles de hasta 43 m, Bioma único con el bioma elegido.
- [ ] Los árboles tienen cuatro tamaños y 21 especies (cerezos y jacarandas en flor, frutales con fruta, secuoyas, eucaliptos...). La misma semilla y el mismo tipo de mapa dan el mismo bosque.
- [ ] Hay matas de pasto cerca de la cámara, que se mueven un poco y no crecen en arena ni agua; con "Vegetación" en bajo llegan menos lejos.
- [ ] Ctrl+F3 abre las herramientas de desarrollo. Inspector: al pasar el cursor sobre un árbol, casa o persona se ven sus datos y el terreno; clic lo selecciona.
- [ ] Crear: poner un árbol, una casa y varias personas en el centro de la vista y con clic en el suelo; aparecen al instante.
- [ ] Explorador: buscar "secuoya" o "arbol" (sin acento), elegir uno de la lista: la cámara va hacia él y el inspector lo muestra; "Eliminar" lo quita.
- [ ] Mapa Enorme en Ultra: más de 60 FPS en los tres modos de cámara.
- [ ] **Tu opinión:** formas y colores de cada especie (las vistas previas se generan con `art/blender/preview_trees.py`), cantidad de pasto y los tipos de mapa.

### Fase 6c (estilo low-poly facetado)

- [ ] El terreno se ve en facetas: grandes en lo llano, pequeñas en orillas, barrancos y crestas. No hay grietas entre parcelas.
- [ ] El agua es turquesa y facetada, se mueve un poco y se ve el fondo de arena cerca de la orilla. Los ríos tienen agua de verdad (antes algunos quedaban como franjas de arena).
- [ ] Los lagos tienen formas irregulares, con playas de arena de ancho variable.
- [ ] "Relieve: Montañoso" crea cordilleras con valles dentro del mapa; los inicios quedan en zonas llanas.
- [ ] Alrededor del mapa hay una cordillera con nieve en las cumbres, y hay nubes low-poly en el cielo.
- [ ] Mapa Enorme en Ultra: más de 60 FPS en los tres modos de cámara.
- [ ] **Tu opinión:** comparado con las imágenes de referencia, ¿qué ajustarías (tamaño de las facetas, colores, agua, montañas)?

### Fase 7 (mods y datos)

- [ ] El menú principal tiene "Mods": muestra el juego base (siempre activo) y los mods de la carpeta de mods, con versión, autor, origen y hash.
- [ ] Copiar `tools/example_mod` a la carpeta de mods (botón "Abrir carpeta de mods"), activarlo y pulsar Aplicar: aparece como "Mod de ejemplo" y "Cargado".
- [ ] Con el mod de ejemplo, un mapa nuevo tiene un círculo de 12 piedras alrededor de cada inicio y una secuoya enorme cerca.
- [ ] Romper a propósito el mod (por ejemplo, `"category": "nada"` en `defs/example.json`) y aplicar: el mod queda desactivado con el error explicado, y el juego sigue funcionando.
- [ ] Un error en `scripts/main.lua` (por ejemplo `error("x")` dentro de `on_map_generated`) genera el mapa igual y muestra un aviso.
- [ ] La guía `docs/CREAR_MODS.md` se entiende sin mirar el código.

### Fase 8 (primer pueblo jugable)

- [ ] Partida nueva: aparece el centro del pueblo con 12 aldeanos, la barra superior (comida 190, troncos 60, piedra 20, población, fecha) y la barra de construcción.
- [ ] Colocar una casa: el fantasma es verde donde se puede y rojo (con el motivo) sobre agua, pendientes o edificios; R la gira; clic derecho cancela.
- [ ] Los peones llevan troncos y la casa sube desde el suelo hasta terminarse; luego se mudan familias.
- [ ] Un leñador y un recolector terminados tienen 2 trabajadores; los árboles desaparecen al talarlos y los arbustos se ven vacíos y rebrotan.
- [ ] La ventana de un edificio muestra progreso, materiales, trabajadores (con − y +), bienes guardados, y permite cancelar o demoler.
- [ ] La ventana de un aldeano muestra edad, qué hace, trabajo, hogar, comida y salud.
- [ ] Espacio pausa con la escena desenfocada y el menú de pausa; nada del juego se puede tocar hasta continuar.
- [ ] F5 guarda ("Partida guardada."), F9 carga; "Cargar partida" en el menú principal y en el menú del juego lista las partidas.
- [ ] Jugar una hora: el pueblo crece si hay comida, y muere de hambre si no se construyen recolectores.

### Fase 9 (multijugador)

- [ ] Abrir dos ventanas con `SalvaCiudad.exe --instance 1 --loopback` y `SalvaCiudad.exe --instance 2 --loopback`. En la 1, "Crear partida multijugador", elegir el mapa y "Abrir la sala".
- [ ] En la 2, "Unirse a partida", puerto 47801, "Conectar": los dos aparecen en la sala con su nombre y color; cambiar el nombre y el color se ve en la otra ventana.
- [ ] "Listo" en la 2 y "Empezar" en la 1: las dos generan el mapa y juegan la misma partida (mismo pueblo, mismos aldeanos).
- [ ] Una casa colocada en una ventana aparece en la otra; en "un pueblo por jugador" cada uno tiene su centro del pueblo.
- [ ] Espacio pausa a los dos al instante; 2 en una ventana pregunta en la otra, y la velocidad cambia al aceptar.
- [ ] Cerrar a la fuerza la ventana 2 (Administrador de tareas), abrirla de nuevo y unirse con el mismo nombre: vuelve a su lugar y la partida sigue igual.
- [ ] Jugar 30 minutos con 2 a 4 ventanas sin avisos de desincronización (si aparece uno, el informe queda en `userdata/instance-1/logs/`).
- [ ] En dos computadoras de la misma red: la partida aparece sola en "Partidas en tu red local" (Windows pedirá permiso del firewall la primera vez).

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
