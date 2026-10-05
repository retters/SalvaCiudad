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

El visor de modelos, `build\release\bin\SalvaCiudadModelos.exe`, es una herramienta aparte para revisar los modelos por categoría con todas sus variantes, ver cuánto cuesta dibujarlos y encontrar los que sobran o faltan (ver [docs/ARTE.md](docs/ARTE.md#visor-de-modelos)).

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
| Esc | Cierra un diálogo, o vuelve al menú desde Configuración |
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
| Tabulador | Al fundar el pueblo: ir al siguiente sitio sugerido |
| Mayús + clic | Colocar varios edificios iguales |
| Clic derecho o Esc | Cancelar la colocación, o quitar la selección |
| F5 / F9 | Guardado rápido / cargar la partida más reciente |
| Ctrl+F3 | Herramientas de desarrollo |
| Ctrl+F12 | Reporte del mapa: marcar con el ratón y guardar (ver abajo) |

Opciones de línea de comandos:
- `--instance <1-8>` usa una carpeta de datos y un puerto propios, para abrir varias ventanas en una PC.
- `--loopback` limita el multijugador a esa misma PC. Ver `docs/RED.md`.
- `--reporte <carpeta>` abre el mapa y la vista de un reporte del mapa, guarda una captura en esa carpeta y se cierra (ver abajo).

## Reportes del mapa

Sirven para decirle a Claude qué te gusta o qué no de un lugar del mapa.

1. Sobre el mapa, pulsa **Ctrl+F12**. Se oculta la interfaz y la cámara se queda quieta. En una partida de un jugador el juego se pausa; en multijugador sigue.
2. Arrastra con el clic izquierdo para pintar trazos rojos sobre lo que te interesa. Un trazo que termina cerca de donde empezó encierra un área, y el reporte describe todo lo que queda adentro. **Retroceso** borra el último trazo y **Supr** borra todos.
3. **Enter** guarda el reporte y **Esc** cancela.
4. Se guarda en `%TEMP%\SalvaCiudad\reportes\<fecha_hora>\`:
   - `captura.png`: la pantalla con los trazos;
   - `captura_limpia.png`: la misma pantalla sin trazos;
   - `reporte.json`: la semilla y las opciones del mapa, la cámara, lo que hay bajo el cursor y las casillas que cubren los trazos, con un resumen.

   Se conservan los últimos 30 reportes.
5. En el chat dile a Claude qué quieres de ese lugar.

`SalvaCiudad.exe --reporte <carpeta>` genera ese mismo mapa con el generador actual, sin niebla y con la estación del reporte, pone la cámara igual y guarda `despues_<fecha_hora>.png`, junto con un `.txt` que dice qué cambió desde el reporte (versión del generador, mods, compilación, tamaño de la ventana). Muestra el mapa generado, no la partida: no aparecen los edificios ni los árboles talados. No guarda la configuración ni partidas.

## Mapas

Qué genera cada generador de mapas, cómo se llama cada cosa y qué opción la controla: [docs/GENERADORES.md](docs/GENERADORES.md).

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

- [ ] El menú principal muestra detrás un mapa que gira despacio (fase 50), y los botones se leen bien.
- [ ] En una partida, la cámara se mueve con WASD y las flechas, gira con Q/E y con el botón central, acerca y aleja con la rueda, y se desplaza al llevar el puntero al borde. **¿Se siente como la de Farthest Frontier?** Anota lo que cambiarías: velocidad, inclinación o suavidad.
- [ ] Al acercarse, la cámara baja hacia el horizonte; al alejarse, mira más desde arriba.
- [ ] Las casas, los árboles y las rocas proyectan sombras, y los bordes de las sombras no titilan al mover la cámara.
- [ ] F3 muestra las estadísticas. Con la sincronización vertical desactivada, los FPS pasan de 60.
- [ ] Configuración → Gráficos: cambiar la calidad de Baja a Ultra; las sombras, la distancia de dibujo y el suavizado cambian al instante.
- [ ] Redimensionar la ventana y cambiar a pantalla completa con la escena abierta: no se deforma ni queda en negro.

### Fase 4

- [ ] En una partida, los aldeanos caminan con las piernas y los brazos coordinados y los pies no patinan; quietos, respiran (animación de reposo).
- [ ] Hay hombres y mujeres con ropa de colores distintos, tonos de piel y de pelo variados, sombrero de paja o gorro, barba y delantal en algunos.
- [ ] Los sombreros, la barba y el delantal siguen la cabeza y la cadera al caminar, sin separarse del cuerpo.
- [ ] Los aldeanos proyectan sombra.
- [ ] La casa tiene entramado de madera, ventanas con contraventanas, puerta, chimenea y tejas; el pino y la roca se ven bien de cerca.
- [ ] Con Blender instalado, generar dos veces con `build_all.py` (ver docs/ARTE.md) da archivos idénticos.
- [ ] **Tu opinión del estilo:** ¿te gusta este low-poly para los personajes y la casa? Qué cambiarías (proporciones, nivel de detalle, colores).

### Modos de cámara (petición del 2026-09-26)

- [ ] En una partida, F4 pasa por Aérea, Tercera persona y Primera persona.
- [ ] Tercera persona: arrastrar con el botón derecho gira en todos los ejes; al bajar mucho, la vista sube sola en lugar de atravesar el suelo.
- [ ] Primera persona: el ratón mira alrededor sin cursor visible y W A S D camina.

### Fase 5

Casi todo se verifica con pruebas automáticas (`ctest`).
- [ ] `ctest --preset release` y `ctest --preset debug` pasan.
- [ ] En una partida, F3 muestra "Tick de simulación" avanzando unas 10 veces por segundo.

### Fase 6

- [ ] "Un jugador" abre "Partida nueva" con una semilla al azar. "Al azar" cambia la semilla; al hacer clic en la casilla se puede borrar con Retroceso y escribir otra.
- [ ] Generar un mapa Mediano con una semilla, volver al menú y generarlo otra vez con la misma semilla y los mismos ajustes: se ve igual (mismo lago, mismo río, mismo inicio).
- [ ] Un mapa Enorme muestra la barra de avance con sus etapas y tarda menos de 30 s. "Cancelar" (o Esc) vuelve a los ajustes.
- [ ] En el mapa hay ríos que llegan a un lago o al borde, lagos con orillas de arena, bosques de pinos y robles, claros, piedras, bayas y hierbas.
- [ ] El número 1 marca el inicio; con varias posiciones de inicio aparecen todos los números, lejos entre sí.
- [ ] Con F3 en un mapa Enorme, los FPS siguen por encima de 60 en los tres modos de cámara (F4), también en calidad Ultra.
- [ ] En Configuración, bajar "Vegetación" acorta la distancia a la que se ven los arbustos y las hierbas.
- [ ] Esc en el mapa abre el menú del juego: Continuar vuelve al mapa; Configuración se abre sobre el mapa y al cerrarla se vuelve a él; Salir al menú principal cierra el mapa y vuelve el mapa de fondo del menú.
- [ ] Con la rueda se puede alejar la cámara hasta ver el mapa completo (provisional).
- [ ] En el inicio 1 hay una aldea de muestra (casas y aldeanos); clic en un aldeano para seguirlo.
- [ ] En Configuración > Pantalla, activar y desactivar varias veces la sincronización vertical: el juego no se cierra.
- [ ] **Tu opinión:** ¿te gustan los colores del suelo y del agua, el ancho de los ríos y la cantidad de bosque?

### Fase 6b (biomas, árboles y herramientas)

- [ ] En Partida nueva, "Biomas" cambia los bosques: con "Todos" cada bioma sale donde le toca por el clima; con uno solo, todo el mapa es de ese bioma.
- [ ] Los árboles tienen cuatro tamaños y 21 especies (cerezos y jacarandas en flor, frutales con fruta, secuoyas, eucaliptos...). La misma semilla y el mismo tipo de mapa dan el mismo bosque.
- [ ] Hay matas de pasto cerca de la cámara, que se mueven un poco y no crecen en arena ni agua; con "Vegetación" en bajo llegan menos lejos.
- [ ] Ctrl+F3 abre las herramientas de desarrollo. Inspector: al pasar el cursor sobre un árbol, casa o persona se ven sus datos y el terreno; clic lo selecciona.
- [ ] Crear: poner un árbol, una casa y varias personas en el centro de la vista y con clic en el suelo; aparecen al instante.
- [ ] Explorador: buscar "secuoya" o "arbol" (sin acento), elegir uno de la lista: la cámara va hacia él y el inspector lo muestra; "Eliminar" lo quita.
- [ ] Mapa Enorme en Ultra: más de 60 FPS en los tres modos de cámara.
- [ ] **Tu opinión:** formas y colores de cada especie (se ven en `SalvaCiudadModelos.exe`), cantidad de pasto y los tipos de mapa.

### Fase 6c (estilo low-poly facetado)

- [ ] El terreno se ve en facetas: grandes en lo llano, pequeñas en orillas, barrancos y crestas. No hay grietas entre parcelas.
- [ ] El agua es turquesa y facetada, se mueve un poco y se ve el fondo de arena cerca de la orilla. Los ríos tienen agua de verdad (antes algunos quedaban como franjas de arena).
- [ ] Los lagos tienen formas irregulares, con playas de arena de ancho variable.
- [ ] "Relieve: Montañoso" da más montañas y crestas más altas; los inicios quedan en zonas llanas.
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
- [ ] Espacio pausa sin desenfoque ni panel: la cámara se mueve y se pueden dar órdenes, que se cumplen al reanudar.
- [ ] F5 guarda ("Partida guardada."), F9 carga; "Cargar partida" en el menú principal y en el menú del juego lista las partidas.
- [ ] Jugar una hora: el pueblo crece si hay comida, y muere de hambre si no se construyen recolectores.

### Fase 9 (multijugador)

- [ ] Abrir dos ventanas con `SalvaCiudad.exe --instance 1 --loopback` y `SalvaCiudad.exe --instance 2 --loopback`. En la 1, "Crear partida multijugador", elegir el mapa y "Abrir la sala".
- [ ] En la 2, "Unirse a partida", puerto 47801, "Conectar": los dos aparecen en la sala con su nombre y color; cambiar el nombre y el color se ve en la otra ventana.
- [ ] "Listo" en la 2 y "Empezar" en la 1: las dos generan el mapa y juegan la misma partida (mismo pueblo, mismos aldeanos).
- [ ] Una casa colocada en una ventana aparece en la otra; en "un pueblo por jugador" cada uno tiene su centro del pueblo.
- [ ] Espacio pausa a los dos al instante; 2 en una ventana pregunta en la otra, y la velocidad cambia al aceptar.
- [ ] El menú principal muestra la versión con su compilación (`0.20.0+…`); un equipo con otra compilación no entra a la sala y ve un aviso que pide copiar la misma.
- [ ] Cerrar a la fuerza la ventana 2 (Administrador de tareas), abrirla de nuevo y unirse con el mismo nombre: vuelve a su lugar y la partida sigue igual.
- [ ] Jugar 30 minutos con 2 a 4 ventanas sin avisos de desincronización (si aparece uno, el informe queda en `userdata/instance-1/logs/`).
- [ ] En dos computadoras de la misma red: la partida aparece sola en "Partidas en tu red local" (Windows pedirá permiso del firewall la primera vez).

### Fase 10 (estaciones y clima)

- [ ] La pantalla de partida nueva tiene Estaciones, Duración del año, Invierno, Recursos iniciales y Población máxima.
- [ ] En partida, la barra superior muestra la estación y la temperatura (en azul bajo cero), y la leña y la ropa entre los bienes.
- [ ] "Invierno eterno": el suelo, las copas y los techos se cubren de nieve, el pasto desaparece, los aldeanos usan gorra y caminan más lento.
- [ ] En otoño los árboles de hoja caduca se ponen dorados, naranjas o rojos; los pinos y demás perennes no.
- [ ] Una casa muestra su leña ("Leña: n de 20") y avisa "Sin fuego" cuando se queda sin ella; sus habitantes pierden calor (barra "Calor" del aldeano).
- [ ] Con una leñera y leñadores, el pueblo pasa los inviernos sin muertes; sin leña, un invierno duro mata.
- [ ] Con helada, los recolectores no recogen bayas.

### Fase 11 (agricultura y alimentos)

- [ ] La barra de construcción tiene Granja, Huerto, Cazador, Pescador, Herborista, Granero y Compostera.
- [ ] En la ventana de una granja, "Nuevo campo" y arrastrar sobre el suelo marca un campo (verde si cabe, rojo con el motivo si no).
- [ ] Cada campo muestra su fertilidad, su estado y el plan de tres años; un clic cambia el cultivo de ese año (trigo, verduras, frijoles, barbecho).
- [ ] En primavera los granjeros siembran (la tierra se oscurece), las plantas crecen y cambian de color, y en verano u otoño se cosechan.
- [ ] Los frijoles y el barbecho suben la fertilidad; el trigo y las verduras la bajan; la compostera da abono que la sube.
- [ ] Un huerto empieza a dar fruta en su tercer año.
- [ ] El cazador trae carne y pieles; el pescador, pescado (no con el agua helada).
- [ ] Con varias comidas, la ventana de los aldeanos muestra buena salud.

### Fase 12 (cadenas de producción y necesidades)

- [ ] La barra de construcción tiene pestañas; los edificios de nivel 2 y 3 aparecen desactivados con el nivel que necesitan.
- [ ] La barra superior muestra la felicidad del pueblo.
- [ ] La ventana del centro del pueblo muestra su nivel y lo que pide el siguiente; con 30 aldeanos, "Mejorar" lo sube y desbloquea edificios.
- [ ] Molino y panadería convierten trigo en pan; el sastre hace ropa con tela de lino o con cuero; el horno, ladrillos o tejas.
- [ ] En un taller, − y + fijan cuánto de su producto guardar; con el límite alcanzado el taller se detiene.
- [ ] Un pozo junto a una casa le da agua (la ventana de la casa dice qué le falta para mejorar); con dieta, agua, ropa y fuego la casa sube a nivel 2 y admite 7 habitantes.
- [ ] Una taberna con cerveza da entretenimiento; sin cerveza, no.
- [ ] Un mercado se llena de comida y ropa, y los aldeanos cercanos comen ahí.

### Fase 13 (salud e incendios)

- [ ] La pantalla de partida nueva tiene Enfermedades e Incendios (de Ninguno a Brutal).
- [ ] Con Ctrl+F3 → Pueblo → "Prender fuego al edificio seleccionado", aparece un aviso, la barra superior cuenta el incendio y el edificio se ve rojo; sin pozo cerca se quema y desaparece.
- [ ] Con un pozo a menos de 50 m, los aldeanos corren a apagarlo ("apagando un incendio" en su ventana).
- [ ] En invierno, sin casas calientes ni ropa, aparece la gripe: aviso de brote, "Enfermos" en la barra y la enfermedad en la ventana del aldeano.
- [ ] Un curandero con hierbas cerca de las casas acorta las enfermedades.

### Fase 14 (comercio)

- [ ] La barra superior muestra el oro (100 al empezar; hasta la fase 27 eran monedas) y, en una ventana de 1024 px, no se encima.
- [ ] Construye un puesto de comercio (Servicios): al mes llega un mercader con aviso; la ventana del puesto lista lo que trae y lo que puedes venderle.
- [ ] Comprar gasta oro y deja los bienes en el puesto; vender da oro y saca los bienes de los almacenes.
- [ ] En multijugador con "un pueblo por jugador" o "mapas separados", el botón Comercio abre la ventana: envía una oferta, el otro jugador recibe el aviso y la acepta; las caravanas llegan a los días indicados.
- [ ] Con "Mapas separados", cada jugador ve su propio mapa, la cámara no sale de él y la ventana de comercio muestra el mapa del mundo con las caravanas.
- [ ] Una oferta rechazada o sin respuesta en un mes devuelve lo apartado.

### Fase 15 (fauna y asaltantes)

- [ ] La pantalla de partida nueva tiene Asaltantes y Fauna peligrosa.
- [ ] En el mapa se ven animales (cajas de colores) que pasean en sus zonas; los ciervos huyen al acercarse un aldeano.
- [ ] La pestaña Defensa tiene empalizada, muro de piedra (nivel 2), puerta, torre de vigía y trampa; la empalizada se coloca en línea arrastrando.
- [ ] Con Ctrl+F3 → Pueblo → "Traer asaltantes ahora" aparece el aviso y la barra superior muestra "Asaltantes N".
- [ ] En la ventana del centro del pueblo, "Tocar la campana" hace que los adultos salgan a pelear; los asaltantes caen o huyen, y "Silenciar la campana" los devuelve al trabajo.
- [ ] Una torre de vigía cerca del camino de los asaltantes les dispara.

### Fase 16 (ejército y versus)

- [ ] Con Ctrl+F3 → Pueblo → "Subir de nivel el centro del pueblo" se desbloquean el cuartel y la arquería.
- [ ] En el cuartel, "Entrenar" una leva: al rato baja la población y la barra muestra "Ejército 1"; el soldado lleva una marca de color.
- [ ] La ventana del ejército muestra soldados, poder militar, las órdenes y los puntos de cada pueblo; "Defender aquí..." y un clic en el mapa los lleva a ese punto.
- [ ] Con "Traer asaltantes ahora", los soldados salen a pelear solos.
- [ ] En la sala multijugador, "Partida" ofrece cooperativa y los modos versus; en "Versus: el último pueblo en pie", "Atacar" manda al ejército al centro del pueblo rival y, si cae, aparece el panel de victoria o derrota.
- [ ] Una partida de un jugador en la que muere todo el pueblo muestra el panel de fin de partida.

### Fase 17 (interfaz completa)

- [ ] El menú principal tiene "Tutorial": abre un mapa con un panel de pasos; cada paso señala en dorado qué usar y avanza solo al hacerlo.
- [ ] La columna de la izquierda abre Bienes, Estadísticas, Eventos y Capas.
- [ ] Una ventana se arrastra por el título, se pega a los bordes y a otras ventanas, y al soltarla junto a otra se mueven juntas; Ctrl+arrastrar la separa; la esquina cambia su ancho.
- [ ] Al hacer clic en el mapa, las ventanas sin fijar se pliegan en pestañas y el cursor encima las abre; "Fijar" las deja abiertas.
- [ ] Al salir y volver a entrar al juego, las ventanas aparecen donde se dejaron.
- [ ] Capas: fertilidad, belleza, agua, mercado, religión, salud, riesgo de incendio y rutas se ven sobre el mapa.
- [ ] Las notificaciones aparecen abajo a la derecha; un clic lleva la cámara al lugar y la ventana Eventos guarda las últimas.

### Fase 18 (arte y sonido)

- [ ] Cada edificio tiene su modelo: el centro del pueblo con torre, la capilla con aguja, el molino con aspas, el mercado con puestos, el pozo, las defensas y los talleres con su patio.
- [ ] Ciervos, jabalíes, lobos y osos tienen su forma y trotan al moverse.
- [ ] Las casas echan humo por la chimenea cuando hace frío; un incendio muestra llamas y humo negro.
- [ ] Las nubes se mueven despacio; en invierno duro el agua se ve blanca y quieta.
- [ ] Suena un clic al usar la interfaz, hachas y martillos al acercar la cámara al trabajo, la campana con un incendio o un asalto, pájaros de fondo (viento en invierno); los volúmenes de Configuración → Sonido los controlan.

### Fase 19 (razas de fantasía)

- [ ] La partida nueva tiene "Pueblo" (Humanos, Gatunos, Enanos, Elfos o Mixto) y "Otras razas" (Ninguna, Pocas, Muchas).
- [ ] Con un pueblo mixto se ven enanos bajos y anchos con barba, elfos altos con orejas largas, gatunos con orejas y cola, y humanos.
- [ ] La ventana del aldeano dice su raza, y Estadísticas cuántos hay de cada una.
- [ ] Los enanos cortan piedra más rápido y los gatunos caminan más rápido (se nota al mirarlos).
- [ ] En multijugador, el anfitrión elige la raza de todos en la sala.

### Fase 20 (rendimiento)

- [ ] `salvaciudad_tests -ts=sim_perf --no-skip` (compilación release) da un tick en marcha de unos 12 ms con 12 × 1000 aldeanos (ver `docs/RENDIMIENTO.md`).
- [ ] Con Ctrl+F3 → Pueblo → "500 aldeanos más" dos veces y F3, el juego sigue fluido a x3 con 1000 aldeanos a la vista.
- [ ] En la sala multijugador, con población máxima 1000 y siete jugadores o más, aparece el aviso de rendimiento en rojo.

### Fase 21 (mapas más grandes)

- [ ] La partida nueva ofrece Gigante (8192 m) y Colosal (16 384 m); al elegirlos, la ayuda del tamaño avisa del tiempo y la memoria.
- [ ] Un mapa gigante se genera en cerca de medio minuto y se juega con fluidez; guardar y volver a cargar la partida funciona.
- [ ] Un mapa colosal se genera en unos dos minutos y se juega (con F3: unos 60 FPS en Ultra); guardar tarda unos segundos.
- [ ] En un mapa grande, poner casas seguidas no da tirones (antes cada edificio recalculaba las zonas de todo el mapa).
- [ ] En la sala multijugador con mapas separados, 4 jugadores y tamaño Gigante, cada jugador tiene un mapa gigante.

### Fase 22 (mapa de islas)

- [ ] La partida nueva tiene "Mapa: Islas"; "Islas por pueblo" solo se puede cambiar con esa opción.
- [ ] Con 2 posiciones de inicio y 3 islas por pueblo, la opción dice "3 por pueblo (6 islas)", y al alejar la cámara se ven 6 islas con playas.
- [ ] En un mapa pequeño con muchos pueblos solo se ofrece 1 isla por pueblo.
- [ ] Fuera del mapa se ve mar abierto hasta el horizonte, no montañas.
- [ ] Con Ctrl+F3 → Pueblo → "Traer asaltantes ahora", llegan desembarcando en la costa de la isla.
- [ ] En versus de 2 jugadores con islas, al ordenar atacar, el ejército desaparece y aparece después en la costa de la isla rival.

### Fase 23 (partida nueva recordada)

- [ ] Cambiar opciones en "Partida nueva", volver al menú y entrar otra vez: siguen igual, salvo la semilla, que es nueva.
- [ ] Cerrar el juego y abrirlo: la partida nueva sigue recordando lo elegido.
- [ ] "Restablecer" deja todo como en una instalación nueva y no cambia la semilla.
- [ ] El juego se cierra sin error (antes, a veces Windows registraba un fallo al cerrar).

### Fase 24 (minimapa y brújula)

- [ ] En partida, arriba a la derecha hay un minimapa con N (en rojo), E, S y O alrededor; lo que se ve en él coincide con el terreno (ríos, lagos, bosques, islas).
- [ ] Los edificios aparecen en el minimapa con el color de su pueblo, y un contorno blanco marca lo que ve la cámara.
- [ ] Un clic en el minimapa lleva la cámara ahí; arrastrar la va moviendo.
- [ ] A la izquierda del minimapa, la brújula: al girar la cámara con Q y E, la flecha roja sigue apuntando al norte del minimapa.
- [ ] Al seleccionar un edificio o un aldeano, su ventana se abre debajo del minimapa.

### Fase 25 (archipiélagos)

- [ ] En un mapa de islas, cada pueblo tiene una isla principal grande y sus secundarias, más chicas, cerca de ella.
- [ ] Las islas tienen formas irregulares: bahías, penínsulas, cabos y estrechos entre islas cercanas; ninguna parece un círculo.
- [ ] Sigue habiendo exactamente pueblos × islas por pueblo islas, y ninguna se une a otra.

### Fase 26 (costas y fondo marino)

- [ ] La partida nueva tiene "Mar" (Sin mar, A veces, Siempre), desactivado con "Mapa: Islas".
- [ ] Con "Siempre", el mapa tiene mar en uno o dos lados, con una costa irregular; a veces con golfos, penínsulas o islotes (se ven en el minimapa).
- [ ] Fuera del mapa hay mar donde el borde es mar, y montañas donde es tierra.
- [ ] Con "Sin mar", el mapa no tiene costa.

### Fase 27 (accidentes del terreno)

- [ ] La partida nueva tiene "Accidentes del terreno" (Pocos, Normales, Muchos).
- [ ] Con "Muchos" en un mapa grande hay más colinas, montañas, mesetas (cimas planas con acantilado y una rampa) y cuencas, y más valles y cañones con un río en el fondo.
- [ ] Se puede subir a una meseta por su rampa; las paredes de un cañón no se pueden cruzar.
- [ ] Los ríos serpentean en lugar de ir en línea recta.
- [ ] En costas e islas, un valle o cañón que llega al mar termina en él.

### Fase 28 (oro que se carga y bóveda)

- [ ] La barra superior dice "Oro 100" al empezar; su tooltip dice cuánto hay en el puesto, en bóvedas y en el centro del pueblo.
- [ ] El oro no aparece repetido entre los recursos de la barra, y la ventana del centro del pueblo lo muestra entre lo que guarda.
- [ ] Construye un puesto de comercio: los peones llevan oro del centro del pueblo al puesto hasta tener 100 (se ve con bolsas en la mano).
- [ ] En la ventana del puesto, "Oro que guarda" con − y + cambia la reserva de 50 en 50; al bajarla, los peones se llevan lo que sobra.
- [ ] Construye una bóveda (Servicios): el oro del centro del pueblo y el que sobra en el puesto se va a la bóveda.
- [ ] Comprar a un mercader gasta el oro del pueblo (primero el del puesto); vender pone el oro en el puesto. Sin oro suficiente, el botón Comprar no se activa.
- [ ] Con las herramientas de desarrollo, prender fuego a la bóveda no hace nada; al puesto sí, y su oro se pierde.
- [ ] En multijugador, una oferta de oro entre jugadores funciona igual que antes, con "Oro" en la lista.

### Fase 29 (comercio automático en el puesto)

- [ ] La ventana del puesto de comercio tiene "Comercio automático": elige un bien, mueve "vender si hay más de" y "comprar si hay menos de" y pulsa "Aplicar regla"; aparece en la lista de reglas.
- [ ] No deja aplicar una regla que compre hasta más de lo que vende.
- [ ] Sin mercader, las reglas no hacen nada.
- [ ] Con mercader y oro en el puesto, cada día vende lo que sobra y compra hasta la cantidad fijada; con el puesto sin oro no compra, aunque haya oro en la bóveda.
- [ ] Al irse el mercader llega un aviso con lo vendido, lo comprado y el oro.
- [ ] En multijugador, dos jugadores con reglas no se desincronizan.

### Fase 30 (visor de modelos)

- [ ] `SalvaCiudadModelos.exe` abre sin el juego, en una ventana, con los textos en tu idioma.
- [ ] A la izquierda están los modelos de "SalvaCiudad (juego base)" por categoría; al elegir un tipo con varias variantes (por ejemplo, Roble o Sombreros) se ven todas lado a lado, con el aldeano de referencia a la izquierda.
- [ ] Al elegir un archivo, la ficha muestra sus triángulos, llamadas de dibujo, tamaño y quién lo usa.
- [ ] En un árbol, cambiar la estación a Otoño o marcar "Con nieve" cambia su color como en el juego; en un personaje, "Otra paleta" cambia su ropa y el menú de animación lo pone a caminar.
- [ ] Con W / S o las flechas arriba y abajo se recorre la lista y cada tipo o archivo se ve al instante; con D o → se abre una categoría o un tipo con variantes, y con A o ← se cierra o se sube al que lo contiene. Mantener la tecla repite.
- [ ] Al escribir en el buscador, W A S D escriben letras y no mueven la lista.
- [ ] Con el visor abierto en un modelo, volver a correr su script de Blender (o guardar otra vez el archivo) lo actualiza solo y abajo aparece "Recargado".
- [ ] El juego sigue viéndose igual (nubes, casas de muestra, animales y sombreros de los aldeanos).

### Fase 31 (variantes de modelos)

- [ ] En una partida, las casas no son todas iguales: hay tres formas por nivel y cada una tiene su techo (teja, paja, pizarra, tablillas), sus paredes y sus postigos.
- [ ] Al colocar una casa, la vista previa ya muestra la forma que tendrá en ese lugar; al construirla queda igual.
- [ ] Al subir de nivel, una casa cambia a una forma más grande (media planta, ala o porche; luego dos plantas).
- [ ] Las rocas, las rocas con mineral y los arbustos de bayas tienen tres formas cada uno, y el cielo tiene nubes de cuatro formas.
- [ ] Guardar y cargar deja cada casa, roca y arbusto con la misma forma y los mismos colores.
- [ ] En multijugador, las dos ventanas ven la misma forma y los mismos colores en cada casa.
- [ ] En el visor de modelos, "Casa (9)" muestra las nueve casas, y "Otros colores" cambia sus techos, paredes y postigos.

### Generación más rápida de mapas grandes (tras la fase 31)

- [ ] Un mapa Colosal con semilla 12345 (mar "A veces", lo demás por omisión) se genera en unos 2 minutos, y la barra no se queda casi todo el tiempo en 10 % "Dando forma al terreno" (los tiempos de hoy, en `docs/RENDIMIENTO.md`).

### Fase 32 (niebla de guerra estática)

- [ ] El formulario de partida nueva tiene "Niebla de guerra" (Sin niebla, Estática, Dinámica) y "Visión compartida"; por omisión y tras "Restablecer", Estática y Entre aliados. Lo elegido se recuerda.
- [ ] Con niebla estática, la partida empieza con un círculo alrededor del centro del pueblo a la vista y todo lo demás negro parejo, sin siluetas de árboles, cerca y lejos. El borde es suave, no cuadriculado.
- [ ] El minimapa muestra negro lo no explorado y el círculo del pueblo a color.
- [ ] Al poner leñadores o recolectores lejos, lo que recorren sus trabajadores se descubre y queda a la vista aunque se vayan.
- [ ] Al intentar colocar un edificio en lo negro, abajo dice "Ese lugar no está explorado." y no se puede construir.
- [ ] Los ciervos y lobos solo aparecen en lo explorado; sus sonidos y los de otros pueblos no se oyen desde lo negro.
- [ ] La capa de fertilidad (Capas) no pinta nada sobre lo negro.
- [ ] En Ctrl+F3 > Pueblo, "Ver a través de la niebla de guerra" muestra todo el mapa; al quitarlo, vuelve la niebla. En multijugador la casilla está desactivada.
- [ ] Guardar y cargar conserva lo explorado.
- [ ] Con "Sin niebla" el juego se ve y se juega como antes.
- [ ] En multijugador (`--instance 1 --loopback` y `--instance 2 --loopback`) la sala muestra la fila "Niebla de guerra"; en cooperativo con visión compartida, lo que explora un jugador lo ve el otro; en versus, cada uno ve solo lo suyo. No hay desincronizaciones.

### Fase 33 (niebla de guerra dinámica)

- [ ] Con niebla dinámica, lo que tu gente exploró y ya no ve queda apagado y gris (terreno, árboles, rocas, agua), también en el minimapa; lo que nunca se vio sigue negro.
- [ ] Un ciervo o un lobo que sale del alcance de tu gente desaparece; al volver a verlo, aparece donde esté.
- [ ] En multijugador versus (`--instance 1 --loopback` y `--instance 2 --loopback`, niebla dinámica): al mandar el ejército al pueblo rival se ven sus edificios; al volver, siguen dibujados tal como se vieron (y en el minimapa, un poco más tenues), aunque el rival construya, mejore o pierda edificios. Al volver a verlos, se ponen al día; los que ya no existen desaparecen.
- [ ] Guardar y cargar conserva lo explorado y los edificios recordados.
- [ ] Con niebla estática, los animales y los edificios de otros se siguen viendo en todo lo explorado.

### Fase 34 (niebla con techo de altura)

- [ ] Con niebla, los árboles más altos que el techo de la niebla se ven como siluetas oscuras sobre lo negro; los chicos no.
- [ ] Con relieve montañoso, los picos aislados y los bordes altos de los cerros asoman sobre la niebla; lo alto de una meseta ancha no.
- [ ] Con niebla dinámica, lo que asoma sobre lo gris se ve con su color, no gris.
- [ ] Lo que asoma no deja construir: sigue diciendo "Ese lugar no está explorado.".
- [ ] En versus, la atalaya o el centro del pueblo del rival (si su punta pasa el techo) se ven como silueta a lo lejos antes de explorarlos; no se pueden seleccionar.
- [ ] Un mod de prueba con `"landmark": true` en una especie de árbol hace que esos árboles se vean como silueta aunque sean chicos.

### Fase 37 (nombres del terreno bajo el cursor)

- [ ] Con F3 abierto, la ventana de estadísticas tiene la sección "Bajo el cursor", que cambia al mover el ratón sobre el mapa: casilla, suelo y bioma, altura y pendiente, fertilidad, agua y accidentes.
- [ ] En la vista previa del mapa de una partida nueva con "Accidentes del terreno: Muchos" y "Mar: siempre", al pasar sobre un cañón, una meseta, un valle o una cresta, F3 dice su nombre.
- [ ] En el agua dice "Río", "Lago" o "Mar", con la profundidad; en la orilla del mar dice "Costa".
- [ ] Sobre un golfo, una península o un islote que se ven en el mapa, F3 dice su nombre donde se ven.
- [ ] En un mapa de islas dice "Isla" sobre cada isla.
- [ ] Con niebla de guerra, sobre lo no explorado dice solo "Todavía sin explorar".
- [ ] Guarda la partida, cárgala y comprueba que los nombres siguen apareciendo.
- [ ] Con el idioma en inglés, los nombres salen en inglés.

### Fase 38 (reporte del mapa)

- [ ] En una partida, Ctrl+F12 oculta la interfaz, detiene la cámara y el juego, y muestra arriba la línea de ayuda.
- [ ] Arrastrar pinta trazos rojos; Retroceso borra el último; Supr borra todos.
- [ ] Enter guarda y aparece "Reporte guardado en …"; la carpeta tiene `captura.png` (con los trazos, sin la línea de ayuda ni la interfaz), `captura_limpia.png` y `reporte.json`.
- [ ] Después de guardar, la interfaz vuelve y el juego sigue a la velocidad que tenía.
- [ ] Esc cancela sin crear carpeta y sin abrir el menú del juego.
- [ ] `SalvaCiudad.exe --reporte "<esa carpeta>"` abre una ventana, muestra el mismo lugar y se cierra solo, dejando `despues_<fecha_hora>.png` y `.txt` en la carpeta.
- [ ] Tu configuración (ventana, sonido) no cambió después de usar `--reporte`.
- [ ] Un círculo cerrado alrededor de una zona da en `reporte.json` un trazo con `"closed": true` y muchas más casillas que la línea sola.
- [ ] Con la cámara muy alejada (todo el mapa a la vista), los trazos del fondo también tienen casillas.

### Fase 39 (generador jerárquico: regiones)

- [ ] F3 muestra "Región: …" (Llanura, Colinas, Montañas, Meseta o Cuenca) y cambia al pasar de una región a otra.
- [ ] Las mesetas se ven como terreno alto con acantilado alrededor; las cuencas tienen lagos; casi no hay estanques sueltos fuera de ellas.
- [ ] Con "Accidentes: Pocos" hay más llanura que con "Muchos"; con relieve "Montañoso" hay más montañas.
- [ ] Guardar y cargar una partida jerárquica conserva los nombres de F3.

### Fase 40 (generador jerárquico: estructuras)

- [ ] En las montañas se ve una cresta larga con picos que sigue la cadena; F3 dice "Estructura: Cresta" en el filo y "Paso de montaña" donde baja.
- [ ] Cada meseta tiene una rampa por la que se sube (F3: "Rampa"); su borde es "Acantilado".
- [ ] Los valles bajan de las colinas o montañas a una llanura o cuenca, en forma de U, a veces con río.
- [ ] Los cañones solo están en mesetas, son pocos, angostos, de paredes a pique, y la mayoría lleva un río que sale de la meseta.
- [ ] F3 nunca dice a la vez cañón y cresta, ni cañón y meseta como estructura.

### Fase 41 (generador jerárquico: agua)

- [ ] Con "Mar: siempre", el mar ocupa uno o dos lados, a veces con un golfo, una península o islotes (F3 los nombra).
- [ ] En "Islas" y "Archipiélagos", cada pueblo empieza en su propia isla y las islas tienen regiones (llanuras, colinas, a veces montañas).
- [ ] Los ríos llegan al mar; donde desembocan, F3 dice "Estuario" y no "Mar".
- [ ] Ninguna meseta toca el mar.

### Fase 42 (generador jerárquico: suelo y vida)

- [ ] Los pueblos empiezan en llanuras o colinas, con agua cerca, piedra, bayas y árboles.
- [ ] Una partida jerárquica en multijugador (dos ventanas con `--instance` y `--loopback`) no se desincroniza.

### Fase 43 (generador jerárquico: ajuste y documentación)

- [ ] Los acantilados de las mesetas siguen su borde sin escalones ni zigzag.
- [ ] En mapas pequeños y medianos, las mesetas y montañas son más bajas que en los grandes, y la rampa de cada meseta sube sin cruzar la llanura como un terraplén.
- [ ] `docs/GENERADORES.md` explica todo lo que F3 nombra en tus mapas.

### Fase 49 (un solo generador: el jerárquico)

- [ ] La partida nueva ya no tiene "Generador de mapas"; un `settings.json` anterior que todavía lo tenga se lee sin avisos y lo demás se conserva.
- [ ] Con una semilla y opciones que antes usabas con "Jerárquico", sale el mismo mapa (mismas regiones en F3, mismos ríos y árboles).
- [ ] F3 y los reportes nunca dicen "Cordillera", "Cabo", "Fosa marina" ni "Dorsal marina"; en la orilla del mar sigue diciendo "Costa".
- [ ] Una partida guardada antes de esta fase se rechaza con el mensaje de partida de otra versión.
- [ ] `SalvaCiudad.exe --reporte` sobre un reporte viejo hecho con el clásico funciona: genera el mapa con el generador de hoy y el `.txt` anota la versión del generador distinta (6 en el reporte, 1 ahora).
- [ ] Con mapas separados, el `.txt` de un reporte dice la misma versión del generador que en un mapa compartido.
- [ ] Las imágenes de referencia están en `art/reference/` y ya no en la raíz del repositorio.

### Fase 47

- [ ] Los ciervos, jabalíes, lobos y osos son los modelos low poly nuevos y mueven las patas al caminar; ya no suben y bajan.
- [ ] Un ciervo paseando camina; al acercarle un aldeano huye corriendo. En los dos casos las patas no patinan sobre el suelo, a x1 y a x3.
- [ ] Quietos, a veces bajan la cabeza a comer y a veces solo respiran. En pausa se quedan inmóviles.
- [ ] Al cazar un ciervo a la vista, cae de lado donde estaba, queda unos segundos y se hunde en el suelo.
- [ ] `SalvaCiudadModelos.exe` muestra los cuatro animales de `core` con sus cinco animaciones.

### Fase 50

- [ ] Al abrir el juego, el menú aparece enseguida y detrás hay un mapa de verdad (terreno, agua, árboles, rocas y animales, sin pueblo ni gente) que gira despacio.
- [ ] Al abrirlo varias veces, el mapa de fondo cambia (sale de la lista de `data\menu_backgrounds.json`).
- [ ] Ya no existe el botón "Escena de prueba 3D", ni la "Vista de estrés" en F3.
- [ ] Empezar una partida, salir al menú principal: vuelve a haber un mapa de fondo.
- [ ] Con las herramientas de desarrollo abiertas (Ctrl+F3) en el menú: F5 pone otro mapa de fondo con una semilla nueva; F6 guarda esa semilla en `menu_backgrounds.json` de tu carpeta de datos y sale un aviso. En el siguiente arranque esa semilla puede salir.
- [ ] Los aldeanos de una partida se ven igual que antes (cuerpos, colores, sombreros, barbas y delantales).
- [ ] En una partida, las herramientas de desarrollo siguen pudiendo poner y quitar aldeanos de prueba.
- [ ] Activar o desactivar un mod en "Mods" y aplicar: el fondo del menú se vuelve a generar.

### Fase 51

- [ ] Los cerezos son los low poly nuevos: en flor (rosa) en primavera y verano, rojizos en otoño y sin hojas en invierno. Se ven de tamaños distintos.
- [ ] En los primeros días del otoño hay cerezos en flor y cerezos de otoño a la vez; a los 6 días todos cambiaron. Lo mismo al entrar el invierno y la primavera.
- [ ] Una partida nueva empieza con los cerezos en flor, no pelados.
- [ ] Con nieve, los cerezos se ven blanqueados como los demás árboles.
- [ ] Talar un cerezo: desaparece y da su madera, como antes.
- [ ] Los demás árboles se ven igual que antes (cambian de color en otoño e invierno).
- [ ] En `SalvaCiudadModelos.exe`, el grupo del cerezo muestra sus tres estados lado a lado.

### Fase 52

- [ ] Al alejar la cámara de un grupo de cerezos, pasan a su versión simple (masas facetadas) sin que se note un salto a la distancia normal de juego. Al acercarla, vuelven a la detallada. En el borde no parpadean.
- [ ] F3, en "Objetos", muestra entre paréntesis cuántos se dibujan en versión lejana (LOD).
- [ ] Las sombras de los cerezos se ven bien (usan siempre la versión simple).
- [ ] En los primeros días del otoño, del invierno y de la primavera, los cerezos van cambiando sin tirones, también en un mapa colosal.
- [ ] Talar un cerezo en otoño y en invierno: desaparece el árbol correcto.
- [ ] En `SalvaCiudadModelos.exe`, el grupo del cerezo muestra las seis versiones; con "Versión: lejana" o "cercana" las tres detalladas cambian a la que se pide.

### Fase 53

- [ ] Una partida nueva solo tiene árboles nuevos: cerezos, jacarandás, olmos, guayacanes, pinos, abedules, sauces, acacias, cipreses, magnolias, arces, palmeras, glicinias, robles amarillos, laureles, baobabs, dragos y manzanos, según el bioma.
- [ ] Las especies con variantes (cerezo, jacarandá, olmo, guayacán) se ven con formas distintas en un mismo bosque.
- [ ] En otoño e invierno cambian todos los de hoja caduca; el pino, el ciprés, la palmera, el laurel y el drago siguen verdes.
- [ ] El inspector de las herramientas de desarrollo y los nombres de F3 dicen la especie nueva de cada árbol.
- [ ] Talar árboles de varias especies: el abedul da menos madera que el roble amarillo, y el baobab más.
- [ ] En `SalvaCiudadModelos.exe` están los 27 grupos de árboles (19 especies y 8 gigantes) con sus estados y versiones lejanas, y ya no hay árboles viejos ni modelos sin usar en `props/`.
- [ ] **Tu opinión:** qué especies se ven mal de lejos (versión simple) o demasiado grandes o chicas junto a las casas.

### Fase 54

- [ ] En un mapa mediano o grande con "Biomas: Todos", el norte es frío (pinos y abedules) y el sur cálido (sabana, bosque seco, jacarandás); las alturas tienen bosque de montaña.
- [ ] Junto a ríos y lagos hay sauces y cerezos llorones (ribera), salvo en lo más frío; lejos del agua dulce no hay sauces.
- [ ] En el sur, junto al mar, hay palmeras (costa tropical); no hay palmeras lejos del mar ni junto a pinos.
- [ ] Las fronteras entre biomas son irregulares, no líneas rectas.
- [ ] F3 muestra bajo el cursor "Clima: temperatura, humedad" y por qué ese lugar tiene su bioma.
- [ ] Los bosques se ven más abiertos que antes: se distingue cada árbol y se puede caminar entre ellos.
- [ ] Talar da más madera por árbol que antes (hay menos árboles): revisar que la madera del inicio de la partida alcance.
- [ ] La partida nueva ofrece "Mapa: Tierra firme o Islas" y "Biomas: Todos o uno solo"; ya no hay tipos de mapa.
- [ ] **Revisión con el reporte del mapa (Ctrl+F12):** marcar los lugares donde un bioma se vea fuera de lugar; el reporte guarda la temperatura y la humedad del punto.

### Fase 55

- [ ] En un mapa mediano hay 2 o 3 árboles gigantes; en uno colosal, hasta 30. Cada uno está solo en un claro.
- [ ] Cada gigante está en su lugar: el mangle junto al mar en la costa tropical, el sauce junto a un río o lago, la secuoya y la araucaria en las alturas, el baobab en la sabana, el hongo en el bosque encantado, el cerezo en el bosque florido y el ginkgo en el templado.
- [ ] Ninguno está cerca del centro de un pueblo al empezar (200 m o más).
- [ ] Con niebla de guerra, los gigantes sin explorar se ven como siluetas oscuras a lo lejos.
- [ ] Un gigante se puede talar: da mucha madera (de 40 a 120 troncos según la especie) y tarda mucho.
- [ ] En otoño e invierno los gigantes cambian de estado como los demás árboles (el hongo cambia sus manchas).
- [ ] **Tu opinión:** tamaño de los gigantes junto a los árboles normales y cantidad por mapa.

### Fase 56

- [ ] "Un jugador" abre la partida nueva en **Variado**: solo semilla, tamaño, pueblos y tipo de mapa, con una vista previa y una línea que dice qué salió ("Mapa templado, costa al este, 3 árboles gigantes").
- [ ] Con "Al azar" varias veces salen mapas fríos, templados, cálidos y mezclados; sin mar, con costa en uno o dos lados y, de vez en cuando, islas o archipiélago.
- [ ] En **Personalizado** la vista previa cambia un momento después de mover cualquier opción del mapa. En mapas enormes o mayores no hay vista previa y el formulario lo dice.
- [ ] El formulario se desplaza con la rueda hasta "Generar mapa"; nada queda cortado ni encimado, en español y en inglés.
- [ ] Cada opción hace lo que dice: ríos 0 % deja solo los de valles y cañones; lagos 0 % no deja lagos; bosques 200 % da muchos más árboles; relieve 200 % da montañas altas; temperatura 0 % da un mapa frío y 200 % uno cálido (palmeras, sabana).
- [ ] Desmarcar biomas los quita del mapa; no deja desmarcar el último. Igual con las estaciones.
- [ ] Mar: "Islas" da una isla por pueblo; "Archipiélago" deja elegir las islas por pueblo. Las islas nunca se tocan entre sí.
- [ ] "Árboles gigantes" desmarcado: ningún gigante en el mapa.
- [ ] Desmarcar razas de inmigrantes: en una partida larga no llega nadie de esas razas.
- [ ] "Partir de Variado" llena Personalizado con lo que Variado da para esa semilla, y el mapa generado es el mismo.
- [ ] Al salir y volver a entrar, el formulario recuerda lo elegido (el botón "Restablecer" de antes ya no existe: "Partir de Variado" hace su trabajo).
- [ ] "Crear partida multijugador" usa el mismo formulario.
- [ ] **Sin revisar en pantalla por Claude** (solo por pruebas): la mitad de abajo de Personalizado (el año y las reglas de la partida). Revisar que se lea bien.

### Fase 88 (despejar una obra talando)

- [ ] Al poner una casa sobre árboles, los árboles siguen ahí y la ventana de la obra dice «Despejando: falta talar N árboles».
- [ ] Los peones van a talarlos antes de construir; cada árbol deja su madera (el peón se la lleva al almacén, o directo a una obra que la necesite si no hay sitio donde guardarla). Un frutal deja además su fruta en el centro del pueblo.
- [ ] La obra no avanza mientras quede un árbol, y después se construye como siempre.
- [ ] Un frutal bajo la obra se tala aunque el leñador de al lado tenga «Talar frutales: no», y no queda brote aunque tenga «Replantar: sí».
- [ ] Cancelar la obra a medio despejar deja en pie los árboles que quedaban.
- [ ] Un campo nuevo sobre árboles: los trabajadores de la granja los talan y solo después siembran.
- [ ] Rocas, arbustos y hierbas bajo la obra siguen desapareciendo al colocarla.
- [ ] **Sin revisar en pantalla por Claude:** nada de esta fase; por pruebas sí. En particular, cómo se ve el peón talando un árbol que quedó dentro de la silueta de la obra (se para en el borde).
- [ ] **Tu opinión:** si rocas y arbustos bajo una obra también deberían recogerse en vez de desaparecer.

### Hambre en viajes con rodeo (corrección)

- [ ] Con una obra muy lejos del pueblo (más de unos 250 m, o con un lago en medio), los peones salen, se dan la vuelta a comer y vuelven a salir; ninguno debe llegar a cero de comida ni morir de hambre por eso.
- [ ] **Tu opinión:** esas obras no se terminan nunca y el juego no lo avisa (ver D-8812).

### Fase 87 (el leñador: replantar y talar solo maduros)

- [ ] La ventana del leñador tiene tres botones: «Talar frutales», «Replantar lo talado» y «Solo árboles maduros», los tres en «no» al construirlo.
- [ ] Con «Replantar: sí», donde cae un árbol queda un brote pequeño de la misma especie y el trabajador se queda un momento plantándolo; al año es un árbol pequeño. Con «no», no queda nada.
- [ ] Con «Solo árboles maduros: sí», el leñador deja los árboles pequeños y medianos (salvo los de especies que no crecen más) y tala los grandes.
- [ ] Si solo le quedan árboles jóvenes o brotes, su ventana dice «Esperando que crezcan los árboles», sin notificación ni cuadro rojo.
- [ ] Con los dos encendidos, un leñador junto a un bosque sigue trayendo madera año tras año (tala unos dos años y espera uno).
- [ ] Poner un edificio sobre un brote lo quita.
- [ ] **Sin revisar en pantalla por Claude:** los botones, el brote dibujado y la espera del trabajador al plantar.
- [ ] **Tu opinión:** si «esperando que crezcan» debería avisar con notificación; y si al encender «Solo maduros» el trabajador debe soltar de inmediato el árbol joven que ya estaba talando (hoy termina esa carga).

### Fase 86 (los árboles crecen)

- [ ] En una partida larga, los árboles pequeños del mapa pasan a medianos durante el segundo año, y los medianos a grandes (según la especie), cada uno en un día distinto: el bosque no cambia de golpe.
- [ ] La ventana de un árbol que todavía puede crecer dice «Sigue creciendo»; la de uno que ya llegó a su tamaño mayor, no.
- [ ] Un árbol que creció da más madera al talarlo, y un frutal que llegó a mediano empieza a dar fruta.
- [ ] Los árboles gigantes no cambian.
- [ ] En un mapa colosal, a velocidad alta, no se nota ningún tirón nuevo al pasar los días.
- [ ] **Sin revisar en pantalla por Claude:** el cambio de tamaño de un árbol a la vista, ni los FPS en el colosal (se midió el costo por tick de la simulación, no el dibujo).
- [ ] **Tu opinión:** el ritmo (un tamaño por año; de grande a enorme, dos años). Casi ninguna especie del juego llega a «enorme»: ese tamaño hoy es de los gigantes.

### Fase 85 (el leñador y los frutales)

- [ ] La ventana de un leñador terminado tiene el botón «Talar frutales: no»; al hacer clic pasa a «Talar frutales: sí» y vuelve.
- [ ] Con «no», el leñador deja en pie manzanos, cerezos, palmas y baobabs y tala lo demás.
- [ ] Si a su alcance solo quedan frutales, avisa «Leñador: solo quedan frutales a su alcance, y no los tala», con el cuadro rojo sobre el edificio y la línea de estado.
- [ ] Con «sí», un frutal talado en verano u otoño deja en el leñador su madera y además fruta; en invierno, solo madera.
- [ ] Poner una casa o un campo sobre un frutal con fruta suma su madera y su fruta al centro del pueblo (o al carro).
- [ ] En red, el cambio del botón se ve en las dos instancias.
- [ ] **Sin revisar en pantalla por Claude:** el botón y el aviso; por pruebas sí.
- [ ] **Tu opinión:** hoy solo los frutales dejan su madera al despejar una obra; los demás árboles despejados siguen sin dejar nada, como siempre. Dime si prefieres que todos la dejen.

### Fase 84 (frutales silvestres)

- [ ] La ventana de un manzano, cerezo, palma o baobab mediano o grande dice «Fruta en el árbol: N» en verano y otoño, y «sin fruta ahora» en invierno y primavera; la de uno pequeño, «aún es muy joven para dar fruta».
- [ ] Un recolector con frutales a su alcance trae «fruta» al almacén además de bayas y hierbas, y los árboles siguen en pie.
- [ ] Recogida toda la fruta, el recolector dice «Esperando que rebrote lo que recoge», sin notificación; al verano siguiente los árboles vuelven a tener fruta.
- [ ] Un roble o un pino no dicen nada de fruta.
- [ ] **Sin revisar en pantalla por Claude:** todo se comprobó por pruebas.
- [ ] **Tu opinión:** qué especies son frutales (hoy manzano, cerezo, palma y baobab) y cuánta fruta dan (6 el mediano, 10 el grande, 14 el enorme, una vez al año).

### Fase 83 (yacimientos de roca)

- [ ] En una partida nueva hay un yacimiento de roca mediano o grande a un paseo del pueblo (hasta unos 200 m), y unos pocos más por el mapa; se distinguen los tres tamaños.
- [ ] Al hacer clic en uno, su ventana dice «Yacimiento de roca» y cuánta piedra le queda.
- [ ] No se puede construir encima, y los aldeanos lo rodean al caminar.
- [ ] Un cantero con un yacimiento a su alcance lo trabaja con sus dos trabajadores a la vez, parados alrededor.
- [ ] Al gastarse pasa al modelo del tamaño menor (en 2 000 y en 800 unidades) y al agotarse desaparece; ahí se puede volver a construir.
- [ ] Con niebla de guerra, los yacimientos grandes se ven como silueta en lo no explorado.
- [ ] **Revisado solo en parte por Claude:** un yacimiento mediano se vio dibujado en el mapa con `--reporte` (semilla 12345, mapa pequeño), y los tres modelos en una imagen hecha con Blender. No se vio una partida: ni canteros trabajándolo ni el cambio de tamaño.
- [ ] **Tu opinión:** el aspecto de los tres modelos, si hay pocos o muchos, y si los trabajadores se ven bien picando a varios metros del centro.

### Fase 82 (más roca, bayas y hierbas)

- [ ] En una partida nueva se ven más rocas sueltas, arbustos de bayas y hierbas que antes, cerca del pueblo y lejos de él.
- [ ] Con «Recursos» al 200 % hay claramente más que al 100 %, y al 0 % casi nada.
- [ ] **Tu opinión:** si el doble alcanza o hace falta más (los yacimientos de la fase 83 se suman a esto).

### Fase 81 (avisos de recursos agotados)

- [ ] Un cantero que acaba con la roca a su alcance: aparece la notificación «Cantero: ya no queda nada que recoger a su alcance», y al hacer clic la cámara va al edificio.
- [ ] Sobre ese cantero queda un cuadro rojo con «!» mientras siga sin roca; desaparece si se detiene su producción o se le quitan los trabajadores.
- [ ] La ventana del cantero y la de cada uno de sus trabajadores dicen «Sin recursos a su alcance».
- [ ] Un recolector con los arbustos vacíos dice «Esperando que rebrote lo que recoge», sin notificación ni cuadro rojo; en invierno pasa lo mismo.
- [ ] Un pescador con el agua helada dice «Sin pesca: agua helada o fuera de su alcance»; un cazador sin presas, «Sin presas a su alcance».
- [ ] **Sin revisar en pantalla por Claude:** el cuadro rojo, la notificación y las líneas de estado se comprobaron por pruebas y leyendo el código, no en una partida.
- [ ] **Tu opinión:** si el cuadro rojo con «!» basta como ícono o prefieres un dibujo propio.

### Fase 80 (los animales ya no brillan de noche)

- [ ] De noche, un ciervo, un jabalí, un lobo o un oso lejos del pueblo se ve tan oscuro como el suelo que pisa, sin un charco de luz a sus pies.
- [ ] Un animal que pasa junto a una antorcha o a una casa con gente se ilumina como un aldeano.
- [ ] Los aldeanos, los soldados y los asaltantes siguen llevando su antorcha de noche.
- [ ] **Sin revisar en pantalla por Claude:** la corrección se comprobó leyendo el código y con pruebas, no con una captura de noche.

### Fase 79 (modo espectador)

- [ ] "Abrir a multijugador" tiene una tercera casilla, "Permitir espectadores". Con ella marcada, la ventana 2 (`--instance 2 --loopback`) entra **mirando**: arriba al centro dice "Mirando: Todo el mapa" y ve todo sin niebla; la 1 sigue en "Jugadores 1" y al pasar el cursor por ahí aparece el nombre de la 2 con "(mirando)".
- [ ] Con las flechas de esa franja, "Como …" muestra lo que ve ese pueblo: su niebla y sus recursos en la barra de arriba. "Todo el mapa" vuelve a mostrar todo.
- [ ] El espectador puede abrir ventanas de edificios y aldeanos; sus botones no hacen nada. No tiene barra de construcción, y pausar o cambiar la velocidad no tiene efecto.
- [ ] "Solo mirar" cierra la ventana de llegada; "Jugar…" la vuelve a abrir. "Fundar mi pueblo" le da asiento (la 1 pasa a "Jugadores 2") y lo deja eligiendo sitio; "Pedir unirme" le da asiento y manda la solicitud.
- [ ] En una partida de dos jugadores con espectadores permitidos, la 2 elige "Pasar a espectador" en el menú de pausa: ve todo, su pueblo sigue trabajando, y la 1 ve el aviso "… está mirando". "Volver a mi pueblo" (menú o franja) la devuelve sin pedir permiso.
- [ ] Mientras la 2 mira, mover su ventana o dejarla sin responder unos segundos no detiene a la 1.
- [ ] Un fundador que está mirando y recibe una solicitud de unión ve el cuadro con "Volver a mi pueblo para responder".
- [ ] En "Crear partida multijugador", la sala tiene la fila "Espectadores": el anfitrión marca "Permitir espectadores" y otra ventana marca "Entrar a mirar, sin jugar"; al empezar, esa ventana no funda nada y mira.
- [ ] Sin la casilla, "Pasar a espectador" no aparece en el menú y quien llega recibe asiento como antes.
- [ ] Con 8 espectadores y la partida solo para mirar, el noveno recibe "ya tiene todos sus espectadores".
- [ ] **Tu opinión:** el lugar y el tamaño de la franja "Mirando"; si "Como …" debería cambiar también la cámara al pueblo; si quieres que las ventanas escondan los botones para quien mira.

### Fase 78 (cargar como anfitrión)

- [ ] En "Cargar partida" cada fila tiene "Como anfitrión" y "Cargar". "Cargar" funciona como antes.
- [ ] "Como anfitrión" en una partida de un jugador: abre la sala "Partida guardada" con tu asiento y las tres casillas de acceso marcadas. "Empezar" te deja en la partida, como anfitrión ("Jugadores 1").
- [ ] Dos ventanas (`--instance 1 --loopback`, `--instance 2 --loopback`): jugar juntas, guardar en la 1 (F5), salir las dos. La 1 carga "Como anfitrión"; la 2 entra con "Unirse a partida" y el mismo nombre: aparece en su asiento. Marca "Listo", la 1 empieza y las dos siguen donde estaban.
- [ ] Lo mismo, pero la 1 empieza sin esperar a la 2: el pueblo de la 2 sigue trabajando solo; la 2 entra después y lo recupera.
- [ ] En la sala de la partida guardada, una ventana con otro nombre es rechazada con el aviso de que entre cuando haya empezado; una vez empezada (y abierta) entra con asiento nuevo.
- [ ] La 2 carga "Como anfitrión" la partida que guardó la 1 (copiando el archivo a su carpeta de partidas): hospeda desde su propio asiento y la 1 entra como cliente al suyo.
- [ ] Una solicitud de unión que estaba pendiente al guardar sigue pendiente al cargar.
- [ ] Una partida guardada con otros mods u otra versión se rechaza con su mensaje, igual que con "Cargar".

### Fases 75 a 77 (abrir la partida, llegar, unirse)

Dos ventanas: `SalvaCiudad.exe --instance 1 --loopback` y `SalvaCiudad.exe --instance 2 --loopback`.

- [ ] La 1 juega sola a ×8, abre el menú (Esc) y elige "Abrir a multijugador": aparecen dos casillas marcadas (pedir unirse, fundar pueblo propio). "Abrir": la velocidad queda en ×5, la barra de arriba dice "Jugadores 1" y sale el aviso de que acepta jugadores nuevos. Las velocidades de ×6 a ×9 ya no se ofrecen.
- [ ] La 2 entra con "Unirse a partida" a `127.0.0.1`, puerto `47801`: recibe la partida y ve "Llegaste a una partida en curso", con "Fundar mi pueblo" y la lista de pueblos.
- [ ] "Pedir unirme": la 2 muestra "Esperando a …" y "Cancelar solicitud"; la 1 ve "… quiere unirse a tu pueblo" con Aceptar y Rechazar.
- [ ] La 1 acepta: la 2 pasa al pueblo (cámara sobre el centro, barra de recursos y de construcción) y sus órdenes construyen ahí. Todos ven el aviso de quién se unió.
- [ ] Repetir y rechazar: la 2 recibe el aviso y puede fundar el suyo: "Fundar mi pueblo", elige sitio mientras la 1 sigue jugando; Esc vuelve a la ventana de llegada.
- [ ] Con solo "pedir unirse" marcado, la 2 no ve "Fundar mi pueblo"; con solo "fundar", no ve la lista.
- [ ] La 2 cierra el juego y vuelve a entrar con el mismo nombre: recupera su asiento y su pueblo.
- [ ] En la 1, menú > "Jugadores nuevos…" > desmarcar "Aceptar jugadores nuevos" > Aplicar: una tercera ventana (`--instance 3 --loopback`) con otro nombre es rechazada con "Esa partida no acepta jugadores nuevos"; la 2, que ya tenía asiento, sí puede volver.
- [ ] Tres ventanas: la 3 pide unirse al pueblo de la 1; la 2, que ya está en ese pueblo, no ve ningún cuadro para aceptar.
- [ ] Una solicitud pendiente sigue ahí después de guardar (F5) y de que el fundador salga y vuelva.
- [ ] Las herramientas de desarrollo (Ctrl+F3) siguen funcionando en la partida abierta.
- [ ] En una partida creada en la sala con "pueblo común", quien entra después ya no pasa directo al pueblo: ve la ventana de llegada y pide unirse.
- [ ] **Tu opinión:** el texto y el lugar de la ventana de llegada; si el cuadro del fundador debería avisar más (hoy: cuadro, sonido y línea en el registro).

### Fases 73 y 74 (fundar el pueblo)

- [ ] "Un jugador" y "Generar": la partida empieza sobre el mapa vacío, de día, con el cartel "Elige dónde fundar tu pueblo" y el número de cada sitio sugerido (también en el minimapa). No hay barra de construcción ni de recursos, y el reloj no avanza aunque se cambie la velocidad.
- [ ] El centro sigue al cursor como silueta: verde donde se puede, roja con el motivo en el cartel donde no (agua, pendiente, borde del mapa). R lo gira; Tabulador lleva la cámara al siguiente sitio sugerido.
- [ ] Un clic en un sitio válido pregunta "¿Fundar el pueblo aquí?". "Cancelar", Esc o clic derecho vuelven a elegir; "Fundar aquí" crea el pueblo y el tiempo empieza a correr (amanece).
- [ ] Al fundar aparecen 12 aldeanos, el carro de los colonos y el centro en obra. Clic en el carro: su ventana lista los bienes y el oro, y no tiene botón de demoler. Los aldeanos llevan materiales del carro a la obra.
- [ ] Antes de que el centro esté listo se puede colocar una casa o un leñador; lo de niveles mayores sigue bloqueado.
- [ ] Al terminarse el centro, el carro desaparece y sus bienes y el oro están en el centro (misma cantidad en la barra de arriba).
- [ ] Se puede fundar lejos de todo sitio sugerido, y sobre árboles (se quitan).
- [ ] Con niebla estática: la pantalla está negra al elegir, se ven las marcas de los sitios y el minimapa muestra la silueta de tierra y agua; al fundar se ve el entorno del pueblo.
- [ ] Guardar (F5) antes de fundar y con el centro a medias, y cargar: todo sigue igual.
- [ ] Dos ventanas (`--instance 1 --loopback` y `--instance 2 --loopback`), "un pueblo por jugador": cada una elige su sitio; el cartel dice a quién se espera y el tiempo no corre hasta que las dos fundaron.
- [ ] Lo mismo con "pueblo común": solo el anfitrión coloca el centro; la otra ventana ve "Esperando a que … funde el pueblo" con la cámara libre, y al fundarse la cámara va al pueblo.
- [ ] El tutorial empieza, como antes, con el pueblo ya en pie.
- [ ] En Partida nueva la barra se llama "Sitios para pueblos"; su valor se recuerda.
- [ ] **Tu opinión:** el modelo del carro; cuánto tarda el centro en construirse (unos 50 s a ×1); si con niebla quieres ver algo más que la silueta del minimapa al elegir.

### Fase 72 (amenazas de noche)

- [ ] Con asaltantes en «Brutal» y día y noche iguales, la mayoría de los asaltos llega de noche.
- [ ] De noche, un lobo o un oso ataca a un aldeano que pasa más lejos que de día, pero no al que está junto a una antorcha.
- [ ] Con niebla dinámica, de noche lo que está a la vista se encoge alrededor de aldeanos y edificios; un pueblo de gatunos ve igual que de día.
- [ ] Una torre tarda más en abatir a un asaltante que viene por lo oscuro que a uno que cruza una zona iluminada.
- [ ] Con «Día y noche» desmarcado nada de esto cambia.
- [ ] **Tu opinión:** si quieres que los soldados tengan raza (y visión nocturna) y que los jabalíes también cambien de noche.

### Fase 71 (energía y descanso)

- [ ] En Personalizado, bajo «La partida», la casilla «Cansancio y descanso» (marcada).
- [ ] La ventana de un aldeano muestra la barra «Energía», que baja mientras está activo.
- [ ] Al vaciarse deja lo que hace, va a su casa («yendo a descansar») y se queda unos 2 minutos («descansando»); luego vuelve a su trabajo.
- [ ] Un aldeano sin casa descansa junto a una fogata encendida o el centro del pueblo y tarda unos 4 minutos.
- [ ] Con hambre come antes de descansar; con la campana nadie descansa.
- [ ] Con la casilla desmarcada no hay barra de energía ni descansos.
- [ ] **Tu opinión:** si los descansos frenan demasiado al pueblo, y si quieres que el aldeano entre a la casa o se siente mientras descansa.

### Fase 70 (oscuridad en la simulación)

- [ ] De noche, un aldeano lejos de las luces camina visiblemente más lento; su ventana dice «A oscuras: camina y trabaja al 75 %».
- [ ] Junto a una antorcha, una fogata encendida, una casa con gente o el centro del pueblo no hay penalización.
- [ ] Un pueblo de gatunos no dice «A oscuras» nunca.
- [ ] Con «Día y noche» desmarcado no hay penalización.
- [ ] **Tu opinión:** si el 75 % se nota lo suficiente, y si quieres que la capa de mapa muestre las zonas iluminadas.

### Fase 69 (luces de noche)

- [ ] De noche el pueblo se ve por sus luces: el centro del pueblo, las casas con gente y los talleres con trabajadores alumbran a su alrededor, y sus ventanas brillan.
- [ ] En Decoración está «Antorcha» (1 tronco, 1 × 1): recién construida alumbra unos 10 m. Su ventana lo dice.
- [ ] La fogata alumbra mientras está encendida; los faroles, braseros y demás decoraciones con fuego, también; las plantas luminosas dan luz azul.
- [ ] Los aldeanos lejos de las luces llevan un charco de luz pequeño que los sigue.
- [ ] Al amanecer las luces se apagan poco a poco; de día no se ven.
- [ ] **Tu opinión:** el alcance y la fuerza de cada luz, y si quieres ver la antorcha en la mano del aldeano.
- [ ] **A vigilar:** triángulos blancos de noche en acantilados oscuros (D-6909).

### Fase 68 (día y noche: el ciclo y el cielo)

- [ ] En Personalizado, bajo «El año»: la casilla «Día y noche» y, marcada, las barras «Duración del día» y «Duración de la noche» (1 a 30 min). El formulario las recuerda.
- [ ] Con día de 1 min y noche de 1 min: la barra superior dice «Día» o «Noche» antes de la estación, y su ayuda cuánto falta para el cambio.
- [ ] Las sombras giran durante el día; al final el sol baja, todo se oscurece y salen las estrellas; la luna cruza el cielo; al amanecer vuelve la luz sin saltos.
- [ ] De noche el agua, el humo y las nubes también se oscurecen.
- [ ] Con la casilla desmarcada el juego se ve como antes, siempre de día.
- [ ] Guardar de noche y cargar: sigue de noche. En red, las dos instancias ven la misma hora.
- [ ] **Tu opinión:** qué tan oscura es la noche (pediste oscura; las luces llegan en la fase 69) y el color del atardecer.

### Después de la fase 67 (humo, fogatas, decoraciones)

- [ ] El humo de una chimenea o un incendio sube unos 40 m y se ve desde lejos.
- [ ] Decoración → Fogata: al terminarla tiene llamas y humo; en invierno, los aldeanos cerca de ella no pierden calor y la leña del almacén baja 1 por día frío. Sin leña, su ventana dice «Apagada».
- [ ] Herramientas de desarrollo: crear un árbol o una piedra en una partida y hacerle clic: abre su ventana; un leñador puede talarlo.
- [ ] Crear personas con las herramientas y hacerles clic: ventana «Persona de prueba» con «Ver», «Cámara» y «Seguir».
- [ ] Pestañas Plaza, Jardín y mercado, Naturaleza, Monumentos y Ruinas: revisar cómo se ve cada decoración construida (tamaño, colores, que no flote ni se hunda).
- [ ] **Sin revisar en pantalla por Claude**: casi todas las decoraciones dentro del juego y la selección de lo creado con las herramientas.

### Fase 67

- [ ] Acercar la cámara a un leñador que vuelve: lleva troncos a la espalda. Un recolector, una canasta. Con poca carga la lleva en brazos y camina sosteniéndola.
- [ ] Al alejar la cámara las cargas dejan de verse (a unas cuatro veces la distancia en que el personaje se simplifica).
- [ ] Una obra nueva: primero cimientos de piedra con estacas, luego un armazón con andamio, al final el edificio. Junto a la puerta se apila lo que van trayendo.
- [ ] Junto al centro del pueblo, a los almacenes y a los talleres hay una pila por cada recurso que guardan (hasta 6, las de lo que más hay), que crece o baja con lo guardado: en un granero con cinco alimentos se distinguen los cinco; el oro, los troncos y la piedra usan las pilas de siempre.
- [ ] En una pradera, en primavera: matas de hierba alta, manchones de flores de colores y trébol. En verano aparecen girasoles; en otoño no quedan flores y la hierba alta está seca; con nieve no se ve ninguna planta.
- [ ] En suelo de bosque hay helechos; en el bosque en flor, pétalos en el suelo mientras es primavera. En montaña: pedregales sobre la roca, riscos en las laderas empinadas y flores alpinas. Junto a ríos y lagos, juncos; en la arena junto al mar, madera de deriva, conchas y alguna poza.
- [ ] En invierno con nieve: ventisqueros contra algunas paredes, témpanos en el agua cuando hiela y, en pueblos con niños, muñecos de nieve junto a adornos de plaza.
- [ ] Nada de eso aparece bajo edificios, obras ni campos, ni estorba para caminar o construir.
- [ ] De día, entre los árboles: ardillas que corretean y se sientan a comer, y pájaros pequeños junto a los troncos; se alejan cuando pasa un aldeano. Cerca de un jardín, un huerto de frutales o una decoración de naturaleza hay muchos más pájaros, y mariposas.
- [ ] En otoño e invierno solo quedan petirrojos. De noche (con el ciclo de día y noche): búhos posados en los árboles y, en verano, luciérnagas; el búho es blanco en bosques fríos o con nieve.
- [ ] Junto a ríos y lagos, libélulas en primavera y verano; sobre los manchones de flores, mariposas. Lejos de los edificios, muy de vez en cuando, un zorro (blanco en clima frío) que huye al acercarse alguien.
- [ ] Donde muere un aldeano, un soldado o un asaltante se juntan tres aves carroñeras (cuervos, o buitres en biomas secos) durante un mes de juego.
- [ ] Con «Detalle del terreno» en «Apagado» no hay ningún animal de ambiente. En pausa se quedan quietos.
- [ ] Configuración > Gráficos > «Detalle del terreno»: en «Apagado» no se ve ninguno; en «Bajo» solo cerca y quietos; en «Medio» y «Alto» más lejos y meciéndose.
- [ ] Defensa > Empalizada: clic y arrastrar traza una línea de módulos; al soltar quedan como obras. En línea recta, en L (primero el lado más largo) y, si los dos lados miden casi lo mismo, en diagonal. Mientras se arrastra, cada módulo se ve verde o rojo y el aviso de abajo dice cuántos tramos son, cuántos caben y cuánto costarán.
- [ ] Los módulos se unen solos: rectos, esquinas, uniones en T, cruces y remates en los extremos; un módulo suelto es un poste. En diagonal no queda ningún hueco entre módulos y nadie pasa entre ellos.
- [ ] Defensa > Puerta de empalizada o Poterna de empalizada sobre un tramo ya trazado: se orienta sola al muro, lo reemplaza, y los aldeanos la cruzan. Sobre el muro de piedra no se deja.
- [ ] Jardín y mercado > Seto vivo, Seto bajo recortado y Valla de estacas: se trazan arrastrando como la empalizada (solo el seto vivo admite diagonales) y se unen solos. Un módulo suelto de seto bajo o de valla se ve como un remate.
- [ ] Arco de seto, Cancela de seto bajo y Cancela de valla, cada uno sobre un tramo de lo suyo: lo reemplazan y los aldeanos pasan. Un corral cerrado sin cancela deja encerrado a quien esté dentro.
- [ ] Un lobo o un jabalí no cruza una empalizada, un seto ni una valla (ni sus puertas): se queda del otro lado y se vuelve a su zona. Un asaltante rompe un módulo de seto o de valla de un solo golpe.
- [ ] Con un recolector con gente y un seto vivo a su alcance, en otoño aparecen bayas en el recolector: 1 por cada 4 módulos, una vez al año.
- [ ] Capa de entorno: un seto bajo terminado sube el entorno a su alrededor (6 m); el seto vivo, un poco más y más lejos (8 m). Muchos módulos no suman más que uno.
- [ ] Plaza > Camino de tierra: se traza arrastrando (recto o en L); los peones lo hacen tramo por tramo y cada tramo, al terminarse, queda como camino en el suelo (ya no se puede seleccionar). Sobre él los aldeanos caminan más rápido y lo prefieren aunque dé un pequeño rodeo. Si hay un árbol en el trazo, lo talan primero.
- [ ] Plaza > Calle empedrada (desde el centro de nivel 2; 1 de piedra por tramo): se puede trazar sobre un camino de tierra para mejorarlo. Sin piedra, los tramos se quedan en obra. Una casa con la puerta hacia la calle gana entorno.
- [ ] Los tramos siguen la ladera sin enterrarse ni flotar; se unen solos en esquinas, T y cruces, también tierra con empedrado. No crece hierba ni flores sobre ellos. Se ven en el minimapa como líneas claras.
- [ ] Plaza > Quitar camino: al arrastrar marca en rojo los tramos que se irán; al soltar desaparecen (también los que estaban en obra). Colocar un edificio o un campo encima de un camino lo borra.
- [ ] Poterna de empalizada, Arco de seto y las dos cancelas (miden un módulo): se colocan con un clic sobre un tramo de lo suyo. (Hasta la fase 95 el clic no hacía nada.)
- [ ] El muro de piedra se traza igual (sin diagonales) y se ve como antes. Una empalizada en obra se ve como andamio de troncos; con más de la mitad del daño, con una brecha.
- [ ] Un campo recién sembrado muestra surcos con brotes; a media temporada, el cultivo verde; listo para cosechar, el cultivo maduro (trigo y cebada dorados, lino con flores azules, coles grandes, frijoles trepando por sus varas). Se distingue qué hay sembrado sin abrir la ventana de la granja. Tras la cosecha quedan rastrojos y en barbecho, pasto.
- [ ] Trigo, cebada y lino se mecen con el viento; verduras y frijoles no. Con la cámara lejos el cultivo deja de dibujarse y el campo conserva su color.
- [ ] Una obra de ladrillo y teja (una panadería) muestra a la izquierda de su puerta las pilas de ladrillos y de troncos que ya llegaron.
- [ ] Un cazador trabajando: sale una flecha cada vez que dispara. Una atalaya o un arquero con enemigos cerca: flechas hacia ellos.
- [ ] Cuando llega un mercader: una carreta y una persona junto al puesto de comercio; se van con él.
- [ ] En pausa nada de esto se mueve; al guardar y cargar todo sigue igual.
- [ ] **Sin revisar en pantalla por Claude**: las flechas y el mercader con su carreta.

### Fase 66

- [ ] Construir un "Explorador" (Servicios). Seleccionar a su trabajador: su ventana dice "Provisiones" y "Clic derecho en el mapa o el minimapa: va ahí".
- [ ] Con niebla estática o dinámica, clic derecho en una zona sin explorar: pasa por un almacén ("yendo por provisiones") y camina en línea recta; al toparse con un lago o un barranco se queda esperando, no lo rodea.
- [ ] Clic derecho en un punto ya explorado: va por terreno explorado.
- [ ] Clic derecho en el minimapa: lo mismo.
- [ ] Revela un círculo de 30 m a su alrededor (más del doble que un aldeano).
- [ ] Dejarlo esperando lejos: cuando la comida le alcanza justo para volver, regresa solo y sale el aviso. No pasa hambre.
- [ ] Clic derecho junto a su edificio: vuelve y sigue con su vida de aldeano.
- [ ] Un lobo lo ataca: huye, y luego retoma la orden.
- [ ] En red: la orden dada en una instancia se ve en la otra.
- [ ] Una obra lejos del pueblo (unos 200 m): quien va justo de comida se da la vuelta a comer y vuelve a salir; nadie muere de hambre con comida en el almacén.
- [ ] Una obra a más de unos 250 m de cualquier comida avanza muy poco o nada: poner un almacén o granero cerca la destraba.
- [ ] **Sin revisar en pantalla por Claude**: el clic derecho en el minimapa y el regreso por provisiones.

### Fase 65

- [ ] Una casa en una ladera (F3 dice la pendiente bajo el cursor; busca 40 a 60 %): con la puerta de lado o ladera arriba se puede colocar; la puerta queda a ras de suelo y ladera abajo se ven los cimientos de piedra.
- [ ] La misma casa con la puerta ladera abajo en una ladera fuerte: "La ladera sube demasiado detrás de la puerta: gira el edificio".
- [ ] En una ladera de más de 4 m de desnivel bajo el edificio: "El terreno es demasiado empinado aquí".
- [ ] Los aldeanos construyen la casa en ladera, entran y salen.
- [ ] En terreno plano los edificios se ven como antes (los cimientos quedan bajo tierra).
- [ ] Murallas y empalizadas: igual que antes.
- [ ] Un sitio al otro lado de un río o en una isla sin paso: "Nadie del pueblo puede llegar hasta ahí". Un campo de granja, igual.
- [ ] El marcador de selección, el humo de las chimeneas y la obra quedan a la altura correcta en un edificio en ladera.
- [ ] **Sin revisar en pantalla por Claude**: los edificios en ladera dentro del juego.

### Fase 64

- [ ] Arrastrar una ventana y soltarla sobre el título de otra: quedan en una sola con dos pestañas arriba. Repetir hasta tener cuatro pestañas.
- [ ] Un clic en una pestaña muestra esa ventana. Arrastrar una pestaña hacia afuera la separa y queda en la mano.
- [ ] Mover la ventana con pestañas mueve todas; cerrar la que se ve deja las demás.
- [ ] Salir y volver a entrar: al abrir las ventanas del lanzador vuelven como pestañas, en el mismo orden.
- [ ] Ventana de un aldeano, "Cámara": se abre una ventana con su imagen en vivo; la cámara principal no se mueve. Llevar la cámara principal a otro lado: la imagen sigue al aldeano.
- [ ] En la imagen: arrastrar gira la vista, la rueda acerca y aleja.
- [ ] Una segunda ventana de cámara para otro aldeano (o edificio, árbol, animal). Una tercera reemplaza a la más antigua.
- [ ] Con las dos abiertas el juego va casi igual de fluido (F3 muestra los FPS); al cerrarlas vuelve a lo de antes.
- [ ] La ventana de cámara de un aldeano que muere se cierra sola.
- [ ] **Sin revisar en pantalla por Claude**: unir y separar pestañas arrastrando, y girar o acercar la imagen.

### Fase 63

- [ ] Cada aldeano tiene nombre propio (título de su ventana); los de cada raza suenan a su raza.
- [ ] "Renombrar": clic en el campo, escribir y OK o Intro. El nombre nuevo sale en el título y en las listas, y sigue ahí tras guardar y cargar. Vacío devuelve el nombre de siempre. Esc mientras escribes solo deja de escribir.
- [ ] En red, el nombre nuevo se ve en la otra instancia.
- [ ] Ventana de aldeano: "Vive en: …" y "Trabaja en: …" abren la ventana de ese edificio y dejan abierta (fijada) la del aldeano.
- [ ] Ventana de una casa: lista "Habitantes" con nombre y edad; cada botón abre a esa persona. De un taller: "Trabajadores". Con más de cinco, la lista se desplaza con la rueda.
- [ ] "Producción: activa" en un taller: al pulsar pasa a "detenida", sus trabajadores quedan de peones y deja de gastar y producir; al volver a pulsar recupera sus trabajadores.
- [ ] "Ver" en cualquier ventana de objeto lleva la cámara ahí.
- [ ] Clic en un árbol: su especie, altura y los troncos que da. En una piedra, veta, arbusto de bayas o hierbas: lo que da; un arbusto recogido dice que volverá a crecer.
- [ ] Clic en un venado o jabalí: lo que trae un cazador; en un lobo u oso, que es peligroso; en un soldado o asaltante, qué hace y su salud.
- [ ] **Sin revisar en pantalla por Claude**: escribir el nombre, el interruptor de producción, el desplazamiento de las listas y las ventanas de animales.

### Fase 62

- [ ] Seleccionar un aldeano y luego otro: la misma ventana cambia de aldeano. Pulsar "Fijar" y seleccionar otro: se abre una segunda ventana al lado.
- [ ] Tres ventanas de aldeano y dos de edificio abiertas a la vez; "Seguir", los trabajadores (+/−) y demoler actúan sobre el objeto de su propia ventana.
- [ ] Con una ventana fijada: Esc, un clic en el suelo, elegir un edificio de la barra de construcción y otra selección no la cierran. Su × sí.
- [ ] La × cierra las ventanas de aldeano y de edificio (antes no hacía nada).
- [ ] Dos ventanas encimadas: se ve entera la de arriba, no se lee la de abajo a través de ella, y un clic donde se enciman solo actúa en la de arriba. Tocar la de abajo la trae al frente.
- [ ] Una ventana sobre la barra de construcción: el clic no elige el edificio que queda debajo.
- [ ] "–" deja solo el título; "+" la restaura. Ya no se pliegan solas.
- [ ] Al arrastrar: se pegan al borde inferior, a la barra de construcción y a los bordes de otras ventanas (también alineando bordes iguales). Soltadas tocándose quedan ancladas y se mueven juntas; al cerrar una de dos, la otra queda suelta.
- [ ] Fijar una ventana de edificio y demolerlo desde otra parte (o que se queme): la ventana dice "Ya no existe" y se cierra con su ×.
- [ ] Con Bienes fijada, el botón "Bienes" del lanzador no la cierra.
- [ ] Salir y volver a entrar: las ventanas del lanzador recuerdan sitio, ancho, fijado y minimizado.
- [ ] La brújula es solo la aguja y la N, sin disco.
- [ ] **Sin revisar en pantalla por Claude**: arrastrar, imanes, anclar y cambiar el ancho.

### Fase 61

- [ ] Tercera persona (F4): al bajar la cámara hasta el suelo y seguir arrastrando, la vista sube hacia el cielo (hasta unos 60°) sin atravesar el suelo; al volver, primero baja la vista y luego sube la cámara.
- [ ] En tercera persona, sin seguir a nadie, se ve un aldeano pálido y translúcido en el punto donde gira la cámara; camina cuando mueves la cámara.
- [ ] Ventana de un aldeano: botón "Seguir". La cámara lo sigue de cerca; el botón pasa a "Dejar de seguir". Doble clic sobre un aldeano hace lo mismo.
- [ ] Al mover la cámara con el teclado deja de seguirlo. Si el aldeano muere, también.
- [ ] En primera persona siguiendo a alguien se ve desde sus ojos y no se ve su cuerpo.
- [ ] Un edificio o un árbol entre la cámara y el aldeano seguido (o el fantasma) se vuelve translúcido en un instante y vuelve a ser sólido al dejar de estorbar.
- [ ] Al meter la cámara dentro de un edificio o de la copa de un árbol (en cualquier modo), ese se vuelve translúcido en vez de taparlo todo.
- [ ] **Sin revisar en pantalla por Claude**: mirar al cielo y los árboles translúcidos. Revisar que el tramado no moleste.

### Fase 60

- [ ] En Personalizado (y en la sala), "Niebla de guerra" tiene un cuarto valor: "Dinámica, mapa revelado".
- [ ] Con ese modo: al empezar se ve el terreno de todo el mapa, tenue y gris fuera de la vista de tu gente; el minimapa igual. Animales, asaltantes y edificios de otros se ven solo donde alguien tuyo mira.
- [ ] Se puede construir lejos del pueblo desde el primer momento.
- [ ] Guardar y cargar conserva el modo.
- [ ] Puesto de comercio, "Comercio automático": bajo "vender si hay más de" hay una barra "si el precio es al menos N %", y bajo "comprar si hay menos de", "si el precio es a lo más N %" ("a cualquier precio" a la izquierda).
- [ ] Con "comprar si el precio es a lo más 90 %", un mercader caro no vende nada al puesto y uno barato sí; la lista de reglas muestra el límite.

### Fase 59

- [ ] En Personalizado, bajo "El año": una barra en minutos por cada estación marcada (1 a 30) y la línea "Duración del año" con la suma. Al desmarcar una estación desaparece su barra y el año se acorta.
- [ ] Un año de 60 min (15 por estación), otro de 75 y otro de 90, repartidos como quieras: la fecha, la estación y la temperatura siguen a cada estación; el cambio de hojas de los árboles también.
- [ ] Con un año largo: los aldeanos comen, trabajan y llegan al mismo ritmo que con el de 20 min; el invierno dura más y hay que guardar más leña y comida; un campo da una cosecha más grande, una vez por año.
- [ ] Con verano de 30 min e invierno de 1 min, el invierno pasa rápido y apenas nieva.
- [ ] Variado sigue con el año de 20 min. Al salir y volver, el formulario recuerda los minutos.
- [ ] **Sin revisar en pantalla por Claude:** estas barras (mitad de abajo de Personalizado).

### Fase 58

- [ ] La barra superior tiene pausa y "− ×N +". Con + se llega a ×9 en un jugador; con − a ×0,25.
- [ ] A ×0,25 y ×0,5 los aldeanos, el humo y los animales van en cámara lenta, sin tirones; a ×9 el calendario avanza nueve veces más rápido.
- [ ] En pausa, ×N muestra la velocidad a la que volverá; Espacio la reanuda; − y + la cambian y reanudan.
- [ ] Teclas: 1, 2 y 3 ponen ×1, ×2 y ×3; coma baja un paso y punto lo sube. Se pueden cambiar en Configuración > Controles.
- [ ] En una partida grande a ×9, si el equipo no alcanza, sale el aviso y la velocidad baja sola un paso.
- [ ] En red (dos instancias): + no pasa de ×5; pedir ×4 o ×5 abre la votación; a ×5 la partida va fluida y sin "Esperando a…" con conexión local.
- [ ] El tutorial que pide cambiar la velocidad marca el botón +.

### Fase 57

- [ ] Una partida nueva solo tiene personajes nuevos. Con raza humana se ven aventureros, caballeros, magos y clérigos, con ropa, piel y cabello de varios colores y estaturas algo distintas.
- [ ] Partida nueva personalizada con cada raza inicial (o "mixta"): enanos (bajos, él con barba y ella con trenzas), elfos, elfos oscuros, gatunos, zorrunos, ranos, lagartos y orcos.
- [ ] Al caminar los pies no patinan, tampoco a velocidad ×2 y ×3, ni en los niños (el adulto en chico) ni en los enanos (trotan).
- [ ] Un leñador tala con el hacha en las manos; un cazador tira con arco; un pescador lanza la caña una vez y espera con ella; quien construye, cultiva o trabaja en un taller martilla. La herramienta desaparece al terminar.
- [ ] Al huir de un animal o con la alarma, los aldeanos corren.
- [ ] Soldados y asaltantes son aldeanos con su marca de color; al atacar dan golpes de hacha.
- [ ] Al alejar la cámara los aldeanos pasan a su versión simple sin que se note un salto feo; al acercarla vuelven a la detallada.
- [ ] Con las herramientas de desarrollo, "Persona" coloca personajes de cualquier raza, y el inspector dice su modelo y su paleta.
- [ ] En el visor (`SalvaCiudadModelos.exe`): "Personajes" lista las 9 razas; cada personaje cambia con "Otra paleta" y muestra la herramienta en la mano en `chop`, `shoot`, `fish_*` y `work`.
- [ ] **Sin revisar de cerca en el juego por Claude:** las animaciones de trabajo con la herramienta se revisaron en el visor y por pruebas; en la partida solo se vio a los aldeanos de lejos (la cámara aérea no se pudo acercar desde las pruebas automáticas).
- [ ] **Tu opinión:** los enanos (se hicieron sin referencia); los colores de piel y pelaje de cada raza; el tamaño del hacha y del martillo; si la caminata se ve natural a la velocidad del juego.

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
