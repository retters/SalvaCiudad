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

- [ ] La barra superior muestra las monedas (100 al empezar) y, en una ventana de 1024 px, no se encima.
- [ ] Construye un puesto de comercio (Servicios): al mes llega un mercader con aviso; la ventana del puesto lista lo que trae y lo que puedes venderle.
- [ ] Comprar gasta monedas y deja los bienes en el puesto; vender da monedas y saca los bienes de los almacenes.
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

- [ ] La partida nueva tiene el tipo de mapa "Islas"; "Islas por pueblo" solo se puede cambiar con ese tipo.
- [ ] Con 2 posiciones de inicio y 3 islas por pueblo, la opción dice "3 por pueblo (6 islas)", y al alejar la cámara se ven 6 islas con playas.
- [ ] En un mapa pequeño con muchos pueblos solo se ofrece 1 isla por pueblo.
- [ ] Fuera del mapa se ve mar abierto hasta el horizonte, no montañas.
- [ ] Con Ctrl+F3 → Pueblo → "Traer asaltantes ahora", llegan desembarcando en la costa de la isla.
- [ ] En versus de 2 jugadores con islas, al ordenar atacar, el ejército desaparece y aparece después en la costa de la isla rival.

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
