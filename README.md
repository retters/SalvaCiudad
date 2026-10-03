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

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
