# SalvaCiudad: especificación para implementación

Versión del documento: 2 (preguntas abiertas resueltas) · 2026-09-26

"SalvaCiudad" es un nombre provisional. En pantalla el título se muestra en dos líneas: `- SALVA -` arriba y `CIUDAD` abajo, más grande y con la C inicial de mayor tamaño. La segunda palabra puede cambiar más adelante. El nombre visible vive en los archivos de idioma y el logotipo es un recurso aparte, de modo que cambiarlo no toca el código.

---

## 1. Objetivo y alcance

SalvaCiudad es un juego 3D de construcción y supervivencia de pueblos medievales, casi un clon de *Farthest Frontier* en mecánicas, con identidad propia y con **multijugador de 1 a 12 jugadores**. Se diseña y se prueba para 8 jugadores, con un máximo de 12.

Pilares:

- **Simulación de pueblo:** aldeanos con edad, hambre, necesidades, salud y trabajo; estaciones y clima; agricultura con fertilidad y rotación; caza, pesca y recolección; cadenas de producción; comercio; enfermedades; niveles de vivienda y de centro del pueblo.
- **Amenazas:** fauna peligrosa y asaltantes controlados por el juego, con dificultad configurable por aspecto.
- **Multijugador configurable al crear la partida:** cooperativo o versus, mapa compartido o mapas separados, con o sin combate, con o sin enemigos, y con distintas condiciones de victoria.
- **Motor propio en C++20**, sin motores comerciales, sobre bibliotecas de código abierto vendorizadas (sección 3).
- **Mods de datos y de scripts (Lua).** El juego base es un mod más, llamado `core`.
- **Multiplataforma por diseño:** Windows, Linux y macOS. En esta etapa solo se compila y se prueba en Windows (ver 3 y 12).
- **Idiomas:** español e inglés, y se puede agregar otro idioma sin tocar el código.
- **Modos de ventana:** pantalla completa, ventana y ventana sin bordes.

### Fuera de alcance (primera versión completa)

- Jugadores controlados por IA (bots que construyen su propio pueblo). No se harán.
- Chat de texto.
- Mapas hechos a mano y editor de mapas. Solo mapas procedurales con semilla.
- Mando o gamepad. Solo teclado y ratón.
- Conexión a través de internet sin abrir puertos (NAT traversal, servidores de retransmisión, Steam). Primero LAN e IP directa.
- Servidor dedicado sin interfaz. Uno de los jugadores es el anfitrión.
- Protección contra trampas.
- Mods con código nativo (DLL).
- Música. Llegará después; se deja listo el sistema de audio para ella.
- Compilación y pruebas en macOS, y CI en GitHub. Quedan pendientes (sección 14).
- Steam Workshop. Queda pendiente.

## 2. Usuario y casos de uso

1. **Partida en solitario.** Salvador crea una partida de 1 jugador, mapa grande con cuatro estaciones, asaltantes en dificultad media y fauna baja. Juega varias horas, guarda y la retoma otro día.
2. **Cooperativo con un amigo en LAN.** Crea una partida multijugador con mapa compartido y **pueblo común**. Su amigo elige "Unirse", ve la partida en la lista de la red local y entra. Los dos construyen el mismo pueblo. Cualquiera puede pedir x2; el otro acepta. Si el amigo se desconecta, puede reconectarse y seguir.
3. **Versus económico de 4 jugadores por IP directa.** Mapas separados, sin combate, victoria por puntuación a las 3 horas. Cada uno tiene su propio mapa y comercia con los demás mediante caravanas que tardan en llegar. Pueden formar tropas, pero solo cuentan como "poder militar" en la puntuación.
4. **Versus con combate.** Mapa compartido enorme, pueblos separados, victoria por eliminación. Los jugadores forman tropas y dan la orden de atacar un objetivo. Las tropas se mueven y pelean solas.
5. **Probar un mod.** Un amigo hace un mod que agrega un edificio (JSON, modelo glTF y textos) y una regla nueva (Lua). Lo copia en la carpeta de mods, lo activa en el menú y juega. En multijugador, el juego comprueba que todos tengan los mismos mods.

## 3. Requisitos

- **Sistemas:** Windows 10/11 x64 es la plataforma de desarrollo y prueba (el equipo de desarrollo es Windows 11, build 26200). Linux x64 y macOS (arm64 y x64) deben poder compilarse sin cambios de arquitectura. No se prueban por ahora.
- **Hardware objetivo:** PC de gama media. La referencia provisional es CPU de 6 núcleos de ~2020, 16 GB de RAM y GPU del nivel de una GTX 1660 o RX 5600. Ver D-005 para el objetivo de cuadros por segundo.
- **Herramientas:** Visual Studio 2022 (MSVC v143), CMake ≥ 3.25 y Ninja. En Linux, GCC ≥ 13 o Clang ≥ 17 (hace falta `std::format`).
- **Lenguaje:** C++20. Sin excepciones cruzando fronteras de módulos, y sin RTTI en el código del juego.
- **Blender** (con el MCP ya instalado) para producir modelos y animaciones. Blender solo se usa en desarrollo; el juego nunca depende de él.

### Bibliotecas de terceros

Todas son de código abierto, van vendorizadas en `third_party/<nombre>/` con su licencia y tienen una versión fija. Para cada una, **necesito tu aprobación explícita** (ver D-002):

| Biblioteca | Uso | Licencia |
|---|---|---|
| SDL3 | Ventana, entrada, modos de pantalla, audio de bajo nivel, hilos y API de GPU (Vulkan, Direct3D 12 y Metal con un solo código) | zlib |
| SDL_shadercross | **Herramienta de compilación**: convierte los sombreadores HLSL a SPIR-V, DXIL y MSL. No se enlaza al juego. | zlib (y sus dependencias DXC y SPIRV-Cross, Apache 2.0 y MIT) |
| cgltf | Lectura de modelos glTF 2.0 | MIT |
| stb_image, stb_truetype, stb_vorbis | Texturas PNG, tipografías y audio OGG | Dominio público / MIT |
| Lua 5.4 | Scripts de los mods | MIT |
| ENet | Red UDP confiable y ordenada | MIT |
| yyjson | Lectura y escritura de JSON (configuración, definiciones de mods, idiomas) | MIT |
| zstd | Compresión de partidas guardadas e instantáneas de red | BSD |
| Dear ImGui | **Solo herramientas de depuración** (nunca la interfaz del jugador) | MIT |
| doctest | Pruebas automáticas | MIT |

Tipografías: varias fuentes con licencia OFL (Google Fonts), vendorizadas con su licencia. El jugador elige la de la interfaz en Configuración; el logotipo usa una fuente decorativa fija. Todas deben cubrir al menos el alfabeto latino extendido (español, inglés y los idiomas europeos más comunes).

## 4. Estructura del proyecto

```
SalvaCiudad/
├─ CMakeLists.txt
├─ CMakePresets.json               # debug, release, debug-asan (Windows); unix-debug, unix-release, unix-debug-asan
├─ ESPECIFICACION_SalvaCiudad.md
├─ README.md
├─ LICENSE
├─ docs/
│  ├─ DECISIONES.md
│  ├─ ARQUITECTURA.md              # visión general de módulos y flujo de datos
│  ├─ DETERMINISMO.md              # reglas que debe cumplir el código de simulación
│  ├─ RED.md                       # protocolo de red
│  ├─ CREAR_MODS.md                # guía para quien hace mods
│  ├─ AGREGAR_IDIOMA.md
│  └─ ARTE.md                      # pipeline de Blender, convenciones de modelos y esqueletos
├─ src/
│  ├─ main.cpp
│  ├─ core/        # registro, aserciones, memoria, contenedores, archivos, JSON, rutas, hash
│  ├─ math/        # punto fijo (simulación) y vectores float (render)
│  ├─ platform/    # SDL: ventana, entrada, reloj, rutas del usuario
│  ├─ render/      # dispositivo GPU, terreno, agua, instancias, esqueletos, sombras, partículas
│  ├─ audio/       # mezclador, efectos posicionales, música (después)
│  ├─ ui/          # interfaz propia: widgets, ventanas acoplables, texto, tooltips
│  ├─ i18n/        # idiomas, plurales, formatos de números
│  ├─ sim/         # simulación determinista: mundo, mapa, aldeanos, economía, clima, combate
│  │  ├─ worldgen/
│  │  ├─ agents/
│  │  ├─ path/
│  │  ├─ economy/
│  │  ├─ climate/
│  │  ├─ health/
│  │  ├─ combat/
│  │  └─ rules/    # modos de juego y condiciones de victoria
│  ├─ net/         # lockstep, lobby, descubrimiento LAN, instantáneas
│  ├─ mods/        # carga de mods, validación, sandbox de Lua
│  ├─ save/        # partidas guardadas
│  └─ game/        # estados de la aplicación, menús, cámara, herramientas del jugador
├─ shaders/        # HLSL, compilados al construir
├─ data/
│  ├─ lang/        # textos del motor y de los menús: es.json, en.json
│  ├─ fonts/
│  └─ mods/
│     └─ core/     # el juego base, como mod
│        ├─ mod.json
│        ├─ defs/          # edificios, recursos, recetas, cultivos, animales, estaciones, razas…
│        ├─ scripts/       # Lua
│        ├─ lang/          # textos del contenido: es.json, en.json
│        ├─ models/        # glTF (.glb)
│        ├─ textures/
│        └─ sounds/
├─ art/            # fuentes de arte: .blend y scripts de Blender que generan los modelos
│  └─ blender/
├─ tools/          # generador de efectos de sonido, empaquetado, validador de mods
├─ third_party/
└─ tests/
```

## 5. Formatos de datos

Reglas comunes a todos los archivos (skill `datos-usuario-persistencia`):

- Todos llevan `schemaVersion`. Uno escrito por una versión más nueva se abre en solo lectura y se avisa.
- Los campos desconocidos se conservan al guardar.
- Un campo inválido toma su valor por omisión, se registra y se cuenta. Al final se avisa cuántos se ignoraron.
- Un archivo ilegible se pone en cuarentena (se renombra con `.bad-<fecha>`), no se borra, y se arranca con valores por omisión.
- Toda escritura es atómica: archivo temporal, vaciado a disco, reemplazo y relectura de verificación.
- Hay un límite de tamaño por archivo y un límite de elementos por lista.

### 5.1 Ubicación

- **Modo portable:** si junto al ejecutable existe un archivo `portable.txt`, todo va en `<carpeta del exe>/userdata/`.
- **Modo normal:** la carpeta de datos del usuario, `%APPDATA%\Salva\SalvaCiudad\` en Windows. SDL da la equivalente en Linux (`~/.local/share/Salva/SalvaCiudad/`) y macOS (`~/Library/Application Support/Salva/SalvaCiudad/`). Ver D-101.
- Dentro: `settings.json`, `saves/`, `mods/` (mods del usuario), `logs/` y `replays/`.
- Desde el menú de configuración se puede abrir la carpeta de datos.

### 5.2 `settings.json` (configuración de la app)

Límite de 256 KB. Contenido:

- `language`: código BCP 47 o `"auto"`, que es el valor por omisión y usa el idioma de interfaz del sistema.
- `display`: `mode` (`fullscreen` | `windowed` | `borderless`, por omisión `borderless`), `monitor`, `resolution`, `vsync` (sí), `fpsLimit` (0 = sin límite; por omisión 0 con vsync), `uiScale` (0.75 a 2.0, por omisión según el DPI) y `quality` (`low` | `medium` | `high` | `ultra` más ajustes individuales: sombras, distancia de dibujo, densidad de vegetación y suavizado de bordes MSAA 2x/4x/8x; ver D-307).
- `audio`: volúmenes `master`, `effects`, `ambient`, `music` y `ui` (0 a 100).
- `input`: asignación de teclas por acción (`"camera.forward": "W"`…), velocidades de la cámara (desplazamiento, rotación y zoom), invertir zoom y desplazamiento por el borde de la pantalla.
- `ui`: tipografía de la interfaz (una de las incluidas en `data/fonts/`; por omisión la primera), disposición de las ventanas del juego (posición, tamaño, anclaje y minimizada o no), mostrar tooltips y retraso de los tooltips.
- `network`: último nombre de jugador, última IP usada y puerto (por omisión 27960, a confirmar).
- `gameplay`: autoguardado (cada N minutos y cuántos conservar), tutorial visto.
- `newGame`: la última configuración de partida nueva (fase 23), salvo la semilla; tipos de mapa, biomas y razas por su id.

### 5.3 Archivos de idioma

- `data/lang/<código>.json` para el motor y los menús; `data/mods/<mod>/lang/<código>.json` para el contenido de cada mod.
- Las claves son identificadores estables (`menu.main.newGame`), nunca el texto en inglés.
- Los marcadores llevan posición y nombre: `"Nació {0:name} en {1:town}"`.
- Los plurales se resuelven con categorías CLDR (`one`, `few`, `many`, `other`…). Cada archivo de idioma declara su regla de plural con un identificador de una tabla interna de reglas CLDR, así que agregar un idioma no requiere código mientras su regla esté en la tabla (cubre la gran mayoría de idiomas).
- Cada archivo declara también el separador decimal y el de miles.
- Los idiomas se descubren al arrancar. Se respalda en este orden: `es-MX`, luego `es`, luego `en`, que es el idioma base. Un texto que falte se registra y usa el respaldo, nunca deja un hueco.

### 5.4 Mods: `mod.json` y definiciones

`mod.json`:

- `id` (solo `[a-z0-9_]`, único), `name` (clave de texto), `version` (semver), `gameVersion` (rango compatible), `dependencies` y `loadAfter`, `authors` y `description`.
- `affectsSimulation`: sí o no. Los mods que solo cambian cosas visuales o de interfaz no necesitan coincidir en multijugador (ver 7.4).

Definiciones en `defs/*.json`, con un tipo por archivo o una lista de objetos con `"type"`. Tipos iniciales: `resource`, `building`, `recipe`, `crop`, `plant`, `animal`, `job`, `need`, `disease`, `season`, `climate`, `race`, `unitType`, `raidProfile`, `techOrTier`, `victoryCondition`, `mapFeature`.

- Cada definición tiene un `id` con espacio de nombres: `core:bakery`.
- Un mod puede **agregar**, **modificar** (parches por campo con `"patch": "core:bakery"`) o **quitar** definiciones de otros mods.
- Se valida todo al cargar: tipos, rangos, referencias a otras definiciones que existan y rutas de archivos dentro de la carpeta del propio mod. Rutas con `..`, absolutas o fuera del mod se rechazan.
- Un mod con errores graves se desactiva y se informa en el menú de mods con la lista de errores. El juego sigue arrancando con los demás.

### 5.5 Partidas guardadas

Formato binario propio, porque una partida con 12 000 aldeanos y un mapa enorme sería enorme en JSON (ver D-004):

- Cabecera legible: firma mágica, `schemaVersion`, versión del juego, fecha, nombre, modo, jugadores, lista de mods con su versión y su hash, semilla y tick actual.
- Cuerpo en bloques con etiqueta y longitud, cada uno comprimido con zstd y con CRC32. Los bloques desconocidos se conservan.
- Miniatura PNG de la vista al guardar.
- Límites en cada cantidad leída: se valida todo al cargar, igual que una entrada de red.
- Guardado atómico. El autoguardado rota N archivos.
- La **misma serialización** se usa para las instantáneas de red: entrar a una partida empezada y reconectarse.
- **Compatibilidad entre versiones:** no se requiere hasta la versión candidata a entrega, e incluso después no es obligatoria: una partida guardada con otra versión del juego se rechaza con un mensaje claro y se empieza una nueva (decisión del usuario del 2026-09-27, D-631).

### 5.6 Configuración de partida (lobby)

Se guarda como plantilla con nombre y se envía a los clientes al unirse. Los campos se listan en 6.3.

## 6. Interfaz

### 6.1 Principios

- Interfaz propia dibujada con la GPU. Toda la interfaz del jugador escala con `uiScale` y ningún ancho se calcula para el texto en español: los textos se miden.
- **Tooltips en todo:** botones, recursos, edificios, aldeanos y estadísticas. Tooltips con contenido rico (iconos, números, desgloses) y un tooltip secundario al mantener Shift para ver el detalle.
- Todo texto visible sale de los archivos de idioma.

### 6.2 Menú principal

Fondo con una escena 3D del mapa en cámara lenta y el logotipo `- SALVA -` / `CIUDAD`.

- **Un jugador:** configuración de partida (6.3) sin las opciones de red.
- **Crear partida multijugador:** configuración de partida más lobby. El anfitrión ve a los jugadores, su color y su raza, si están listos y si sus mods coinciden.
- **Unirse a partida:** lista de partidas en la red local (descubrimiento automático) y campo de IP y puerto.
- **Cargar partida:** lista con miniatura, fecha, modo y jugadores. Una partida multijugador cargada vuelve a abrir el lobby para que los jugadores tomen sus lugares.
- **Mods:** lista, activar o desactivar, orden de carga, errores de validación.
- **Configuración:** Pantalla, Gráficos, Audio, Controles (reasignación de teclas con detección de conflictos), Interfaz, Idioma y Juego. Cada opción tiene su tooltip y un botón "Restaurar valores por omisión". Los cambios de pantalla peligrosos (resolución, modo) se confirman con cuenta regresiva de 15 s y se revierten solos.
- **Salir.**

### 6.3 Configuración de partida

- **Mapa:** semilla (editable, con botón "aleatoria"), tamaño (Pequeño, Mediano, Grande, Enorme, Gigante, Colosal; ver 7.6), tipo de mapa (con islas por pueblo en el mapa de islas), cantidad de ríos y lagos, densidad de bosque, abundancia de recursos, relieve (bajo por omisión, siempre suave).
- **Clima:** cuántas y cuáles estaciones (de 1 a 4; por ejemplo "invierno eterno" o "verano eterno"), duración del año (por omisión unos 20 minutos a x1, como en Farthest Frontier), dureza del invierno.
- **Modo de mundo:** *mapa compartido* o *mapas separados* (ver 7.7).
- **Relación entre jugadores:** *cooperativo* o *versus*. En cooperativo con mapa compartido se elige además *pueblo común* o *pueblos separados aliados*.
- **Combate entre jugadores:** activado o no. Si no, las tropas solo suman "poder militar" a la puntuación.
- **Condición de victoria** (solo en versus): eliminación, puntuación (a un tiempo límite o al llegar a una meta), destruir un objetivo (el centro del pueblo rival o una estructura especial) o ninguna (partida libre).
- **Enemigos del entorno**, cada aspecto con su nivel (ninguno, bajo, medio, alto, brutal): asaltantes, fauna peligrosa, enfermedades, incendios, sequías y plagas.
- **Población máxima por jugador:** 50 a 1000. Por encima de un umbral (por ejemplo, 600 × número de jugadores), el lobby muestra una advertencia de rendimiento.
- **Recursos iniciales:** escasos, normales o abundantes.
- **Por jugador:** nombre, color y raza inicial, o "mixta" (ver 7.12).
- **Inmigración de otras razas:** activada o no, y en qué proporción.

### 6.4 En partida

- **Cámara** estilo Farthest Frontier: WASD o flechas y borde de la pantalla para desplazarse, rueda para el zoom, botón medio o Q/E para rotar, inclinación automática según el zoom. Todo reasignable.
- **Barra superior:** recursos principales, población, fecha y estación, velocidad y jugadores conectados.
- **Barra de construcción** por categorías, con tooltips de costo, requisitos y efecto.
- **Ventanas del juego** (edificio, aldeano, almacenes, estadísticas, comercio, ejército, registro de eventos):
  - Se mueven y se redimensionan.
  - **Se ajustan con imán** a los bordes de la pantalla y a otras ventanas cercanas.
  - **Se anclan** unas junto a otras en grupos que se mueven juntos.
  - **Se contraen a una pestaña al perder el foco** y se despliegan al acercar el cursor, como en SalvaRecortes y SalvaWinProfiles. Cada ventana tiene un pin para quedarse abierta.
  - Su disposición se recuerda en `settings.json`.
- **Minimapa y brújula** (fase 24): el mundo entero con el norte arriba, los cuatro puntos cardinales, los edificios de cada pueblo y lo que ve la cámara; un clic lleva la cámara ahí. Una brújula con una flecha que apunta al norte y gira con la cámara.
- **Superposiciones del mapa:** fertilidad, deseabilidad, cobertura de servicios (agua, mercado, religión, salud), riesgo de incendio y rutas de los aldeanos.
- **Velocidad:** pausa, x1, x2 y x3. Ver 7.5 para el voto en multijugador.
- **Pausa:** la pantalla se desenfoca y se muestra el menú de pausa. No se puede hacer nada en el juego mientras dure.
- **Notificaciones** de eventos (nacimientos, muertes, incendio, asaltantes, llega un mercader) con un clic que lleva la cámara al lugar.

### 6.5 Tutorial

Un escenario guiado con objetivos paso a paso (mover la cámara, construir una casa, asignar trabajadores, preparar el invierno…), textos en los archivos de idioma y resaltado del elemento de la interfaz que se debe usar. Se define en datos y en Lua dentro de `core`, para que un mod pueda agregar tutoriales.

## 7. Arquitectura

### 7.1 Visión general

Hay dos mundos que no se mezclan:

- **Simulación** (`sim/`): determinista, en punto fijo, a paso fijo, sin depender del reloj, del render ni de la entrada directa. Solo cambia al aplicar *comandos* del jugador y al avanzar *ticks*. Todas las máquinas la ejecutan igual.
- **Presentación** (`render/`, `ui/`, `audio/`, `game/`): en `float`, a la frecuencia de la pantalla. Lee el estado de la simulación e **interpola** entre los dos últimos ticks para que el movimiento se vea fluido. Nunca escribe en la simulación: todo lo que el jugador hace se convierte en un comando.

### 7.2 Hilos

- **Hilo principal:** eventos de SDL, interfaz y envío del cuadro a la GPU.
- **Hilo de simulación:** avanza los ticks, con un tamaño de paso fijo de 100 ms de juego (10 ticks por segundo a x1 y 30 a x3). Publica una "vista" de solo lectura del estado por tick para el render. Ver D-003. Por ahora la simulación corre en el hilo principal; se moverá a un hilo propio si la medición lo pide (D-506).
- **Trabajadores** (un grupo de hilos): búsqueda de rutas, preparación del render (selección de visibles, animación), carga de recursos y compresión. Los trabajos de la simulación que corren en paralelo producen resultados que se aplican **en un orden fijo**, para no romper el determinismo.
- **Hilo de red:** ENet, empaquetado y desempaquetado.

### 7.3 Determinismo (lo que no se negocia)

Se documenta en `docs/DETERMINISMO.md` y se verifica con pruebas:

- **Nada de `float` ni `double` en el estado de la simulación.** Se usa punto fijo de 32 bits (formato 16.16) y de 64 bits donde haga falta. Las funciones trigonométricas y la raíz cuadrada son propias, con tablas o enteros.
- **Generador aleatorio propio** (PCG32), con flujos separados por sistema y semilla derivada de la partida. Nunca `rand()` ni `<random>`.
- **Nada de recorrer contenedores con orden no definido** (`unordered_map`, direcciones de memoria) en la simulación. Las entidades se identifican con ID secuenciales.
- La simulación no lee el reloj, ni archivos, ni configuraciones locales durante la partida.
- Los scripts Lua que afectan a la simulación reciben y devuelven enteros y punto fijo. La biblioteca `math` de Lua se reemplaza por funciones deterministas propias. `os`, `io`, `require` libre, `load` de código binario y `debug` no están disponibles.
- **Hash del estado** cada N ticks. Cada cliente lo envía; si alguno no coincide, se detecta la desincronización, se guarda un informe con la diferencia y se ofrece reenviar la instantánea del anfitrión para seguir jugando.

### 7.4 Red: lockstep determinista

- **Topología en estrella:** el anfitrión recibe los comandos de todos y reenvía un "turno" con los comandos de todos. Así cada cliente solo necesita conexión con el anfitrión.
- **Turnos de 100 ms.** Un comando emitido en el turno *T* se ejecuta en el turno *T + retraso*. El retraso es de 2 turnos en LAN y se ajusta según la latencia medida, hasta un máximo.
- **Ancho de banda:** solo viajan comandos (colocar edificio, asignar trabajadores, cambiar prioridades, atacar…), unos pocos bytes cada uno. No depende de la cantidad de aldeanos: 12 jugadores caben holgadamente en una LAN y en conexiones domésticas.
- **CPU:** cada máquina simula todo el mundo. El límite real es la PC más lenta. Si un cliente se atrasa, el anfitrión lo detecta y reduce la velocidad para todos, avisándolo.
- **Unirse a una partida empezada y reconectar:** el anfitrión serializa el estado (el mismo formato que las partidas guardadas, 5.5), lo comprime y lo envía. Mientras el cliente lo carga y alcanza el turno actual, los demás siguen jugando. Un jugador desconectado deja su pueblo en manos de la simulación sin órdenes nuevas (los aldeanos siguen trabajando solos) hasta que vuelva.
- **Verificación al unirse:** versión del juego, lista de mods con `affectsSimulation` y sus hashes. Si no coinciden, se rechaza con un mensaje claro que dice qué falta o qué sobra.
- **Descubrimiento LAN:** difusión UDP en la red local con el nombre de la partida, el modo, los jugadores y si tiene contraseña (opcional).
- **Varios clientes en una sola PC:** el juego acepta `--instance <n>`, que usa una carpeta de datos y un puerto propios, para abrir varias ventanas y probar el multijugador sin otra computadora. Además hay una prueba automática sin ventana que corre N simulaciones en un solo proceso, les pasa los mismos turnos y compara los hashes.
- Protocolo documentado en `docs/RED.md`. Todo mensaje de red se valida igual que un archivo externo: tamaños, rangos, IDs existentes y que el jugador tenga permiso sobre la entidad.

### 7.5 Velocidad y pausa en multijugador

- Cualquier jugador puede proponer pausa, x1, x2 o x3. Los demás ven un aviso con "Aceptar" o "Rechazar". El cambio se aplica cuando todos aceptan, o se descarta a los 15 s.
- **Excepción: la pausa es inmediata.** Cualquier jugador puede pausar sin votación, por si tiene que levantarse de golpe. Para **reanudar** o cambiar de velocidad sí hace falta que todos acepten.

### 7.6 Mapa y generación procedural

- Rejilla de casillas de 1 m × 1 m para la construcción (4 rotaciones), con altura por vértice y regiones de 64 × 64 casillas para el render y la simulación espacial.
- Tamaños propuestos (a confirmar al medir el rendimiento):

| Tamaño | Casillas | Lado aproximado |
|---|---|---|
| Pequeño | 512 × 512 | 0.5 km |
| Mediano | 1024 × 1024 | 1 km |
| Grande | 2048 × 2048 | 2 km |
| Enorme | 4096 × 4096 | 4 km |
| Gigante | 8192 × 8192 | 8 km |
| Colosal | 16384 × 16384 | 16 km |

- Gigante y Colosal se agregaron después de la fase 20 (fase 21); piden mucha más memoria y tiempo de generación (ver `docs/RENDIMIENTO.md`).
- **Islas** (fase 22): un tipo de mapa en el que el mar rodea islas. Se configura cuántas islas hay por pueblo: con 2 pueblos y 3 islas por pueblo hay 6 islas. Cada pueblo empieza en una isla propia.
- **Archipiélagos** (fase 25): cada pueblo tiene una isla principal y sus islas secundarias, más pequeñas, alrededor; todas de contorno irregular.
- **Costas** (fase 26): los demás tipos de mapa pueden tener mar en uno o dos lados ("Mar": sin mar, a veces o siempre), con golfos, bahías, penínsulas, cabos, islotes y estrechos; bajo el mar puede haber fosas y dorsales.
- **Accidentes del terreno** (fase 27): mesetas, valles, cordilleras y cañones, más o menos frecuentes según "Accidentes del terreno" (pocos, normales o muchos). Ninguno aparece siempre, pero todos pueden aparecer.

- Generación a partir de la semilla, en etapas que a su vez son deterministas: relieve suave (ruido con poca amplitud), ríos que bajan por el relieve hasta lagos o al borde, lagos, humedad, fertilidad del suelo, tipos de suelo, bosques y praderas, piedra, arcilla, mineral de hierro, arbustos de bayas, hierbas, zonas de fauna y posiciones de salida justas para cada jugador.
- Las etapas y sus parámetros son datos del mod `core` (`mapFeature`), para que un mod pueda agregar rasgos del mapa.

### 7.7 Modos de mundo

- **Mapa compartido:** un solo mapa para todos. En *pueblo común*, todos los jugadores controlan el mismo pueblo con permisos iguales: cualquiera puede construir, demoler o cambiar lo que hizo otro. En *pueblos separados*, cada jugador tiene su pueblo, su zona de salida y sus propiedades.
- **Mapas separados:** cada jugador tiene su propio mapa, generado a partir de la semilla común más su número de jugador. Todos se simulan en la misma simulación, como regiones sin contacto físico. La interacción ocurre en un **mapa del mundo** abstracto: las caravanas de comercio y los ejércitos viajan entre pueblos con un tiempo proporcional a la distancia configurada, y al llegar aparecen en el borde del mapa del destino.

### 7.8 Aldeanos y trabajo

- Cada aldeano tiene edad, sexo, raza, apariencia (variante de modelo, texturas y accesorios), hogar, trabajo, inventario, necesidades, salud y felicidad.
- **Búsqueda de rutas:** A* jerárquico sobre regiones con cache de rutas, costos por tipo de suelo y caminos más rápidos. Las solicitudes se agrupan por tick y se resuelven en paralelo con resultados aplicados en orden.
- **Decisión:** sistema de utilidad con tareas (buscar comida, trabajar, llevar recursos, dormir, ir al templo…) evaluadas de forma escalonada: no todos los aldeanos piensan en cada tick. Así 12 000 aldeanos caben en el presupuesto de CPU.
- **Trabajos:** se asignan por edificio con prioridades, como en Farthest Frontier.
- **Ciclo de vida:** nacimiento (si hay vivienda libre y felicidad suficiente), niñez, trabajo, vejez y muerte. También llegan inmigrantes según la deseabilidad del pueblo.

### 7.9 Economía y sistemas de juego

Todos definidos como datos en `core` y con reglas en C++ o Lua:

- **Recursos y almacenes:** almacén, granero, leñera, mercado y carretas de transporte.
- **Estaciones y clima:** temperatura, nieve, heladas, duración de las estaciones, leña para calefacción y ropa.
- **Agricultura:** cultivos con temporada, fertilidad que se agota y se recupera, rotación de cultivos con efectos (por ejemplo, una leguminosa recupera nitrógeno), barbecho, abono, malas hierbas, piedras en los campos y plagas.
- **Huertos y árboles frutales** que tardan años en madurar.
- **Caza, pesca, recolección y hierbas.**
- **Cadenas de producción:** trigo → harina → pan; cebada → cerveza; cuero y lino → ropa; mineral → hierro → herramientas; arcilla → ladrillos y tejas; carbón; ahumadero; salazón, y las que se definan.
- **Necesidades:** comida variada, agua, ropa, calzado, religión, entretenimiento, higiene, calefacción y belleza del entorno. Afectan la felicidad y la salud.
- **Salud y enfermedades:** contagio por agua sucia, ratas, desechos y falta de higiene; herborista, médico, pozos y casa de baños.
- **Vivienda** en niveles que se mejoran si se cumplen requisitos. El **centro del pueblo** sube de nivel y desbloquea edificios.
- **Comercio:** mercaderes del entorno que llegan con mercancías y precios que varían. Con jugadores, caravanas y precios acordados.
- **Incendios:** riesgo por edificios de madera, propagación y pozos para apagarlos.

### 7.10 Amenazas y combate

- **Fauna:** ciervos, jabalíes, lobos y osos, con manadas, territorios, reproducción y ataques a aldeanos y ganado.
- **Asaltantes:** grupos que aparecen en el borde del mapa. Su frecuencia y fuerza crecen con la riqueza del pueblo y se ajustan con la dificultad. Eligen objetivos (almacenes, casas) y saquean o queman.
- **Defensa:** empalizadas, muros de piedra, puertas, torres, trampas y milicia (aldeanos que toman armas al sonar la campana).
- **Ejército:** cuarteles, tipos de unidades como datos (`unitType`), equipamiento que se produce y soldados profesionales.
- **Órdenes:** el jugador solo elige un objetivo ("atacar este pueblo o edificio", "defender aquí", "retirarse"). Las tropas calculan su ruta, se organizan y pelean solas. Esto reduce los comandos de red y simplifica el determinismo.
- **Sin combate entre jugadores:** las tropas existen y suman "poder militar" a la puntuación, pero no pueden atacar a otros jugadores. Sí defienden de asaltantes y fauna.

### 7.11 Render

- API de GPU de SDL3 (Direct3D 12 o Vulkan en Windows, Vulkan en Linux, Metal en macOS). Sombreadores en HLSL, compilados al construir. Por ahora solo a DXIL (Direct3D 12) con el `dxc` del Windows SDK; SPIR-V y MSL llegarán con las pruebas en Linux y macOS (D-201).
- **Terreno** por regiones con LOD, texturas de suelo que se mezclan (pasto, tierra, arena, roca, nieve, campo arado), deformación estacional (nieve, pasto seco) y surcos en los campos.
- **Agua** para ríos y lagos, con orillas, flujo y congelación en invierno.
- **Vegetación e instancias:** todo lo que se repite (árboles, rocas, cultivos, casas, aldeanos) se dibuja por instancias, con LOD y selección por región.
- **Personajes animados** con esqueleto compartido por raza, animación en la GPU, mezcla entre animaciones y accesorios fijados a huesos (sombreros, herramientas, cargas).
- **Iluminación:** ciclo de día y noche, sol direccional con sombras en cascada, niebla, luz ambiental por estación y luces puntuales de antorchas y ventanas de noche.
- **Efectos:** partículas para humo, fuego, lluvia, nieve, polvo y chispas.
- **Estilo:** estilizado, con colores cálidos y detalle donde importa.

### 7.12 Arte, razas y pipeline de Blender

- **Todo modelo se genera con un script de Blender versionado** en `art/blender/` (Python con `bpy`), que se ejecuta con el MCP de Blender o con `blender --background --python`. Así los modelos se pueden regenerar, mejorar y variar sin repetir el trabajo a mano. El resultado se exporta a `.glb` en el mod.
- **Personajes:** un modelo base masculino y uno femenino por raza, con esqueleto común a la raza. Las variantes salen de texturas y paletas (piel, cabello, ropa) y de accesorios (sombreros, trajes, delantales, herramientas). Estilo low-poly "medio": caras y manos con algo de detalle, ropa con volumen.
- **Animaciones iniciales:** reposo, caminar, correr, cargar, talar, picar, construir, sembrar, cosechar, comer, dormir, atacar, morir. Primero en versión simple; el sistema permite reemplazarlas por mejores sin tocar el código.
- **Edificios:** caras planas con detalles arquitectónicos (vigas, marcos, tejas, chimeneas), etapas de construcción visibles y variantes por nivel.
- **Razas de fantasía** (como en el anime): **humanos**, **gatunos** (orejas y cola), **enanos** y **elfos**. Cada una es una definición `race` con modelo, esqueleto y animaciones propios y con **rasgos de juego**.
  - **Un pueblo puede mezclar razas.** Cada jugador elige su raza inicial (o una mezcla), y llegan inmigrantes de otras razas si la partida lo permite. Los hijos toman la raza de uno de los padres.
  - **Rasgos iniciales** (valores a equilibrar durante el juego): los **enanos** minan y trabajan la piedra y el metal más rápido; los **elfos** cazan, recolectan y cuidan huertos mejor; los **gatunos** ven de noche (trabajan sin penalización nocturna) y se mueven más rápido; los **humanos** son equilibrados y se adaptan mejor a cualquier trabajo.
  - Los rasgos son modificadores declarados en datos (velocidad por tipo de trabajo, velocidad de movimiento, visión nocturna, resistencia al frío o a enfermedades, necesidades propias), así que un mod puede agregar razas o cambiar sus rasgos.
  - Por ahora no hay edificios exclusivos por raza; el sistema de definiciones lo permitiría más adelante (D-011).
- **Paquetes de assets libres** (por ejemplo Kenney o Quaternius, con licencia CC0) se pueden usar como reemplazo provisional. Cada descarga se te pide aparte, indicando archivo, origen, tamaño y licencia. La licencia de cada asset se registra en `data/mods/core/CREDITS.md`.
- **Efectos de sonido básicos:** generados con una herramienta propia de síntesis en `tools/sfxgen/` (estilo sfxr, con parámetros guardados en JSON) o con paquetes CC0 aprobados. La música queda para después.
- Convenciones de escala, orientación, nombres de huesos y materiales en `docs/ARTE.md`. Las variantes de ropa usan paletas por personaje (materiales con nombre de "espacio de paleta") y los accesorios son modelos rígidos fijados a un hueso (D-404, D-405).

### 7.13 Mods y Lua

- Carga en orden: `core`, luego los mods activos según sus dependencias y `loadAfter`. Los ciclos se detectan y se rechazan.
- **Lua en sandbox:** sin `os`, `io`, `package.loadlib`, `debug` ni carga de código binario; con límite de instrucciones por llamada (para que un script en bucle infinito no congele la partida) y límite de memoria. `require` solo busca dentro del propio mod.
- **Puntos de enganche:** eventos de simulación (nace un aldeano, termina una estación, llega un asaltante…), condiciones de victoria, reglas del mapa, tutoriales y paneles de interfaz sencillos declarados en datos.
- El **hash del mod** se calcula sobre todos sus archivos, ordenados por ruta, para la verificación en multijugador.

## 8. Extensibilidad

- **Contenido nuevo** (edificio, recurso, cultivo, animal, raza, estación): un archivo de definición, modelos y textos, sin tocar el motor. Guía en `docs/CREAR_MODS.md`, con un mod de ejemplo en `tools/example_mod/`.
- **Idioma nuevo:** copiar `en.json` del motor y de cada mod y traducirlos. Guía en `docs/AGREGAR_IDIOMA.md`.
- **Estaciones de fantasía:** son definiciones `season` y `climate` con temperatura, precipitación, efecto en cultivos y aspecto visual, de modo que "invierno eterno" o "estación de ceniza" se agregan como datos.
- **Plataforma nueva:** todo lo específico del sistema se aísla en `platform/`.

## 9. Límites y no objetivos

- **Red:** solo la del multijugador (LAN e IP directa) que activa el usuario al crear o unirse a una partida. Nada de telemetría, actualizaciones automáticas ni conexión a servicios.
- **Sin permisos de administrador.** No hay instalador que los pida.
- **No se modifica la configuración del equipo.** La pantalla completa usa el modo que SDL gestiona para la ventana y se restaura al salir. Las pruebas automáticas no tocan el sistema.
- **Dependencias:** solo las de la tabla de la sección 3, con tu aprobación. Cualquier otra se te pregunta antes.

## 10. Desarrollo seguro

- Compilación con `/W4 /WX` y endurecimiento en MSVC (`/sdl /GS /guard:cf /DYNAMICBASE /NXCOMPAT /HIGHENTROPYVA /CETCOMPAT`); `-Wall -Wextra -Werror` y equivalentes en GCC y Clang. Las advertencias se corrigen, nunca se silencian. Las bibliotecas de terceros se compilan con sus propias opciones y aisladas.
- **Toda entrada externa se valida estrictamente:** archivos de configuración, partidas guardadas, mods, idiomas, modelos glTF, texturas, audio y **mensajes de red**. Límites de tamaño y cantidad, rangos y referencias existentes.
- **Rutas:** se canonizan y se comprueba que queden dentro de la carpeta permitida (del mod, de datos del usuario). Nunca se sigue una ruta absoluta que venga de un archivo o de la red.
- **Nunca se ejecutan comandos del sistema** con datos de un archivo, de un mod o de la red.
- Los scripts de los mods están en sandbox (7.13). Un mod que llega por la red no se descarga automáticamente: el jugador debe tenerlo instalado.
- Se comprueba el resultado de toda llamada a una API o al sistema de archivos.
- Escritura atómica de toda la configuración y de las partidas guardadas.
- Registro en inglés, con rotación y límite de tamaño, sin datos personales. Las IP solo se registran cuando hacen falta para diagnosticar la red.

## 11. Pruebas

### 11.1 Automáticas (`salvaciudad_tests`, con `ctest`, también en `debug-asan`)

- **Matemática de punto fijo:** operaciones, desbordes, trigonometría y raíz contra valores de referencia.
- **RNG:** secuencias conocidas para semillas fijas.
- **Determinismo:**
  - La misma partida (semilla + lista de comandos grabada) se simula dos veces y en configuraciones debug y release, y da el mismo hash en cada tick de control.
  - N simulaciones en un solo proceso con los mismos turnos: hashes idénticos.
  - Guardar, cargar y seguir da el mismo hash que no haber guardado.
- **Generación de mapas:** la misma semilla produce el mismo mapa; los ríos llegan a un lago o al borde; cada jugador tiene una zona de salida válida y justa.
- **Persistencia:** ida y vuelta de `settings.json` y de partidas guardadas, y un archivo por cada forma de estar mal (campo de otro tipo, fuera de rango, JSON truncado, vacío, enorme, versión futura, campos desconocidos, bloque corrupto con CRC que no coincide).
- **Idiomas:** las claves de `es` y `en` coinciden, en el motor y en cada mod; ningún texto visible incrustado en el código; los plurales de las reglas de la tabla funcionan.
- **Mods:** validación de definiciones, parches, dependencias y ciclos, rutas maliciosas rechazadas, sandbox de Lua (no puede abrir archivos, se corta un bucle infinito, se limita la memoria).
- **Red:** mensajes malformados, truncados, con tamaños absurdos o de jugadores sin permiso se rechazan sin fallar; la simulación con pérdida y reordenamiento de paquetes simulados sigue sincronizada.
- **Rendimiento (prueba de referencia, no bloquea):** tiempo por tick con 1, 4, 8 y 12 jugadores de 1000 aldeanos en un mapa enorme, registrado para seguir su evolución.

### 11.2 Sondas manuales (se corren pidiéndote permiso)

- Abrir 2 a 4 instancias del juego en tu PC (`--instance`) y jugar una partida en red local.
- Cambios de modo de pantalla y de monitor.

### 11.3 Lista de verificación manual (en `README.md`)

Se completa en cada fase. Al final cubre menús, configuración, modos de pantalla, multijugador, guardado y carga, mods e idiomas.

## 12. Entrega

- `cmake --preset release` y `cmake --build --preset release` producen `SalvaCiudad.exe`, x64.
- Se distribuye como ZIP portable: ejecutable, `data/`, `README.md`, `LICENSE`, licencias de terceros y créditos de los assets, más el SHA-256 del ejecutable. El PDB no se distribuye.
- **Licencias:** el código de SalvaCiudad se publica con licencia **MIT**. Cada asset conserva su propia licencia (CC0, CC-BY, CC-BY-SA, OFL…), registrada en `CREDITS.md` de su mod. Ver D-012.
- Linux: el mismo CMake produce el binario. Se valida cuando tú lo pruebes en tu máquina Linux.
- macOS y CI en GitHub: pendientes (sección 14).

## 13. Fases

Cada fase termina así:

- Compila en `debug`, `release` y `debug-asan` sin advertencias.
- Pasan las pruebas y cumple sus criterios de aceptación.
- Se anotan las decisiones en `docs/DECISIONES.md`.
- Se hace un commit.
- Te entrego un resumen con lo que tienes que probar a mano, y sigo con la siguiente fase salvo que algo requiera tu decisión.

Las fases 1 a 9 construyen los cimientos y un **primer juego jugable en multijugador**. Las siguientes agregan los sistemas de Farthest Frontier uno por uno sobre esa base.

1. **Base del proyecto.** CMake y presets, SDL3, doctest y yyjson vendorizados, endurecimiento y advertencias como errores, registro, rutas (portable o datos del usuario), `settings.json` con validación, cuarentena y escritura atómica, bucle principal con paso fijo y ventana en los tres modos. Se inicializa git.
   - *Criterios:* abre una ventana en pantalla completa, ventana y sin bordes, y cambia entre ellas sin reiniciar; `ctest` pasa en las tres configuraciones; un `settings.json` dañado se pone en cuarentena y la app arranca.
2. **Idiomas, texto e interfaz base.** `i18n` con `es` y `en`, plurales y formatos; dibujo de texto con atlas de glifos; sistema de widgets propio con tooltips y escala; menú principal completo (las opciones que aún no existen muestran "próximamente") y pantalla de Configuración con todas las opciones y reasignación de teclas.
   - *Criterios:* el idioma cambia sin reiniciar; se escala la interfaz de 0.75 a 2.0 sin cortes; todos los ajustes se guardan y se restauran; los cambios de pantalla peligrosos se revierten solos a los 15 s.
3. **Render 3D base.** Dispositivo de GPU, compilación de sombreadores con `shadercross`, carga de glTF, cámara estilo Farthest Frontier, instancias, luz direccional con sombras, cielo y niebla. Herramientas de depuración con ImGui (FPS, tiempos, conteos).
   - *Criterios:* 50 000 instancias de un modelo de prueba a 60 FPS o más en tu PC; la cámara se siente como la del original.
4. **Pipeline de arte.** Scripts de Blender en `art/blender/` para un humano base masculino y femenino con esqueleto, caminar y reposo, tres variantes de ropa y dos sombreros, un árbol, una roca y una casa con detalles. Exportación a `.glb`, animación con esqueleto en la GPU y accesorios en huesos. `docs/ARTE.md`.
   - *Criterios:* 2000 aldeanos animados caminando en pantalla a 60 FPS o más; regenerar un modelo con su script da el mismo archivo.
5. **Núcleo determinista.** Punto fijo, RNG, identificadores y almacenamiento de entidades, reloj de ticks, comandos, hash de estado, grabación y reproducción de partidas (replays). `docs/DETERMINISMO.md`.
   - *Criterios:* todas las pruebas de determinismo de 11.1 pasan en debug y release.
6. **Mapa procedural.** Generador con semilla (relieve suave, ríos, lagos, bosques, recursos, fertilidad), los cuatro tamaños, terreno por regiones con LOD, agua y vegetación por instancias. Configuración de mapa en la pantalla de nueva partida.
   - *Criterios:* la misma semilla da el mismo mapa; un mapa Enorme se genera en menos de 30 s y se recorre a 60 FPS o más.
6b. **Biomas, especies de árboles y herramientas de desarrollo** (agregada el 2026-09-27 a pedido del usuario).
   - Árboles en cuatro tamaños: chico (1–7 m), mediano (7–12 m), grande (12–24 m) y enorme (24–43 m). Cada especie tiene los tamaños que le corresponden.
   - Especies, cada una con un modelo por tamaño hecho con scripts de Blender: roble, pino, toog, eucalipto (*E. viminalis*), secuoya gigante, fresno de montaña australiano (*E. regnans*), cerezo japonés (*Prunus serrulata*), jacaranda, tulipán africano (*Spathodea*), palo borracho (*Ceiba speciosa*), magnolia, tabachín, calistemo, pino piñonero, olmo, limonero, manzano, naranjo, peral, durazno y aguacate. El catálogo está en `docs/ARBOLES.md`.
   - Biomas: regiones del mapa con su mezcla de especies y tamaños, su densidad y su pasto.
   - Tipos de mapa: combinaciones de biomas que se eligen en la pantalla de partida nueva (Clásico, Arboleda joven, Tierra de gigantes, Pinar del norte, Variado y Bioma único). Por ahora son tablas en el código con la forma que tendrán como datos; en la fase 7 pasan a JSON dentro del mod base.
   - El mapa guarda la versión del generador con la que se hizo.
   - Matas de pasto decorativas cerca de la cámara, sin efecto en la simulación.
   - Herramientas de desarrollo (Ctrl+F3), en ImGui y con pestañas:
     - un inspector con el nombre y todas las propiedades del objeto seleccionado o bajo el cursor, incluidos el terreno y el bioma donde está;
     - una pestaña para crear árboles, vegetación, casas y personas;
     - un explorador que lista los objetos con búsqueda por nombre y categoría, lleva la cámara a uno y lo muestra en el inspector.
     Más adelante se agregan pestañas por cada mecánica, por ejemplo asignar recursos en la fase 8. Solo funcionan en partidas de un jugador, o si la partida las permite.
   - *Criterios:*
     - la misma semilla y el mismo tipo de mapa dan el mismo mapa, y cada tipo de mapa se ve distinto;
     - un mapa Enorme se sigue generando en menos de 30 s y se recorre a 60 FPS o más en Ultra, con el pasto;
     - regenerar los modelos con sus scripts da archivos idénticos;
     - las tres herramientas funcionan sobre un mapa generado.
6c. **Estilo visual low-poly facetado** (agregada el 2026-09-27 a pedido del usuario, con imágenes de referencia de "Low-Poly Experiments").
   - Terreno facetado con triangulación adaptativa: facetas grandes (hasta unos 8 m) en lo llano y más pequeñas donde hace falta detalle (orillas, barrancos, crestas, cambios de suelo). Vértices desplazados para que las facetas sean irregulares, color plano por faceta y la misma triangulación da los niveles de detalle.
   - Agua facetada que se mueve, turquesa, más clara y transparente en la orilla y con brillos por faceta.
   - Orillas: playas de arena más anchas y bajadas suaves al agua; barrancos donde el terreno es alto.
   - Nueva opción de relieve "Montañoso", con montañas y valles dentro del mapa (las laderas empinadas no se construyen), y una cordillera decorativa fuera del borde en todos los mapas.
   - Lagos de contorno irregular: entrantes, penínsulas y a veces islotes.
   - Luz, cielo y colores más vivos; nubes low-poly decorativas.
   - Los árboles de primitivas se conservan.
   - *Criterios:*
     - la misma semilla da el mismo mapa;
     - un mapa Enorme se genera en menos de 30 s y se recorre a 60 FPS o más en Ultra;
     - no hay grietas visibles entre parcelas del terreno;
     - los objetos se apoyan en el suelo facetado sin flotar ni hundirse de forma visible.
7. **Mods y datos.** Cargador de mods, `core` como mod, esquemas y validación de definiciones, parches, Lua en sandbox, hash de mods y menú de mods. `docs/CREAR_MODS.md` y mod de ejemplo.
   - *Criterios:* el mod de ejemplo agrega un edificio y una regla en Lua sin tocar el código; un mod con errores se desactiva con un mensaje claro; el sandbox resiste las pruebas.
8. **Primer pueblo jugable (un jugador).** Aldeanos con búsqueda de rutas, trabajo, hambre, edad, nacimiento y muerte; recolección de madera, piedra y bayas; almacén, casas, leñador, recolector y centro del pueblo; construcción por etapas; barra de construcción, barra de recursos, ventanas de edificio y de aldeano (aún sin acoplamiento); velocidad y pausa con desenfoque; guardar y cargar.
   - *Criterios:* se puede jugar una hora; el pueblo crece o muere de hambre según cómo se juegue; guardar y cargar conserva todo (verificado por hash).
9. **Multijugador por lockstep.** ENet, anfitrión y unión por IP, descubrimiento LAN, lobby con la configuración de partida, verificación de versión y mods, turnos, retraso adaptable, detección de desincronización, voto de velocidad, unirse a partida empezada, reconexión, y `--instance`. Modo cooperativo con mapa compartido (pueblo común y pueblos separados). `docs/RED.md`.
   - *Criterios:* dos a cuatro instancias en tu PC juegan 30 minutos sin desincronizarse; un cliente que se cierra a la fuerza vuelve a entrar y sigue; la prueba automática de N simulaciones pasa con 12 jugadores.
10. **Estaciones y clima.** De 1 a 4 estaciones configurables, temperatura, nieve, heladas, leña para calefacción, ropa y aspecto visual por estación.
11. **Agricultura y alimentos.** Campos, cultivos, fertilidad, rotación, barbecho, abono, huertos, caza, pesca, recolección, hierbas, granero y comida variada.
12. **Cadenas de producción y necesidades.** Talleres y cadenas de 7.9, mercado, necesidades, felicidad, deseabilidad, niveles de vivienda y del centro del pueblo.
13. **Salud.** Enfermedades, contagio, higiene, pozos, herborista, médico, casa de baños e incendios.
14. **Comercio.** Mercaderes del entorno, puesto de comercio, comercio entre jugadores y modo de mapas separados con mapa del mundo y caravanas.
15. **Fauna y asaltantes.** Animales con comportamiento, asaltantes con dificultad configurable, defensas y milicia.
16. **Ejército y versus.** Cuarteles, unidades como datos, órdenes de ataque automáticas, combate entre jugadores o solo como poder militar, todas las condiciones de victoria y pantalla de fin de partida.
17. **Interfaz completa.** Ventanas con imán, anclaje, contracción al perder el foco y despliegue al pasar el cursor; superposiciones del mapa; notificaciones; tooltips ricos en todo; tutorial.
18. **Arte y sonido.** Todos los edificios, recursos, animales y animaciones con el pipeline de Blender; efectos de sonido; partículas; pulido visual.
19. **Razas de fantasía.** Gatunos, enanos y elfos como definiciones de `race` con sus modelos, animaciones y rasgos de juego; pueblos mixtos e inmigración de otras razas.
20. **Rendimiento.** Perfilado y optimización con 12 jugadores de 1000 aldeanos en un mapa enorme; ajuste de los límites y de las advertencias del lobby según lo medido.
21. **Mapas más grandes.** Tamaños Gigante (8192) y Colosal (16384) para mapa compartido y mapas separados; límites de guardado, instantáneas de red y paquetes ajustados a lo medido; aviso de tiempo y memoria en la partida nueva.
   - *Criterios:* los dos tamaños se generan, se juegan, se guardan y se cargan; la misma semilla da el mismo mapa; las mediciones quedan en `docs/RENDIMIENTO.md`.
22. **Mapa de islas.** Tipo de mapa `core:islands` con islas por pueblo configurables (1 a 8, según quepan en el tamaño del mapa).
   - *Criterios:* con N pueblos y K islas por pueblo hay N × K islas separadas por mar; cada pueblo empieza en una isla distinta con sus recursos básicos; la misma semilla da el mismo mapa.
23. **Partida nueva recordada.** La última configuración de partida nueva se guarda en `settings.json` y se vuelve a mostrar; un botón la restablece a los valores por omisión.
   - *Criterios:* la configuración sobrevive a reiniciar el juego; un valor inválido en el archivo vuelve al de omisión sin perder los demás; restablecer deja todo como en una instalación nueva.
24. **Minimapa y brújula.** Minimapa del mundo con los cuatro puntos cardinales, los edificios de cada pueblo y lo que ve la cámara; un clic lleva la cámara ahí. Una brújula en pantalla con una flecha que apunta al norte y gira con la cámara.
   - *Criterios:* el minimapa corresponde al terreno; el clic mueve la cámara al lugar; la flecha apunta al norte con cualquier giro de la cámara.
25. **Archipiélagos.** En el mapa de islas, una isla principal por pueblo y las secundarias, más pequeñas, agrupadas a su alrededor; contornos irregulares con bahías, penínsulas y cabos en lugar de círculos.
   - *Criterios:* sigue habiendo exactamente pueblos × islas por pueblo islas; cada secundaria está más cerca de la principal de su pueblo que de las demás y es más pequeña que ella; las islas son claramente menos redondas que un círculo (prueba de compacidad); la misma semilla da el mismo mapa.
26. **Costas y fondo marino.** Opción "Mar" (sin mar, a veces, siempre) para los tipos de mapa sin islas: mar en uno o dos lados, con golfos, bahías, penínsulas, cabos e islotes que forman estrechos. Fosas marinas y dorsales oceánicas bajo el mar, también en el mapa de islas.
   - *Criterios:* con "siempre" hay mar que toca el borde y la tierra conserva al menos la mitad del mapa; con "sin mar" el mapa no cambia; las fosas son más hondas y las dorsales más altas que el fondo que las rodea sin salir del agua; los pueblos empiezan en tierra con sus recursos.
27. **Accidentes del terreno.** Opción "Accidentes del terreno" (pocos, normales, muchos): mesetas de cima plana con una subida suave, valles anchos, cordilleras y cañones de paredes empinadas que desaguan.
   - *Criterios:* con "muchos", en varios mapas grandes aparecen los cuatro tipos; la cima de una meseta es plana, un cañón es más hondo que sus bordes y su fondo baja hasta el borde del mapa o el mar; un mapa enorme sigue generándose en menos de 30 s.
28. **Oro que se carga y bóveda** (agregada el 2026-09-27 a pedido del usuario; reemplaza D-1401).
   - Las monedas pasan a ser oro, el recurso `core:gold`, con una categoría propia (`gold`) y `value` 0 para que los mercaderes no lo compren ni lo vendan como mercancía. Los peones lo cargan y ocupa espacio como cualquier recurso. Desaparece el número `coins` del pueblo.
   - Guardan oro la bóveda, el puesto de comercio y el centro del pueblo; los almacenes comunes no. El oro inicial (100, o 50 con recursos escasos y 200 con abundantes) empieza en el centro del pueblo.
   - Bóveda (`core:vault`): guarda solo oro, con mucha capacidad, y no se quema.
   - Reserva del puesto de comercio: el jugador fija cuánto oro mantener ahí. Si sobra, los peones llevan el excedente a la bóveda (o al centro del pueblo si no hay); si falta, lo traen de ella.
   - Las compras a los mercaderes y el oro de las ofertas entre jugadores salen primero del puesto y luego de los demás edificios, como hoy los bienes vendidos (D-1403). El oro de las ventas entra al puesto, o al centro del pueblo si no cabe. En las caravanas, el oro viaja como cualquier bien.
   - Los asaltantes pueden llevarse oro como cualquier otro bien. Si un edificio que guarda oro se quema, el oro se pierde igual que el resto de lo que guarda.
   - La barra superior muestra el oro total; su tooltip lo separa en puesto, bóveda y otros edificios.
   - *Criterios:* el oro del pueblo solo cambia por comercio, robo o incendio; los peones mantienen la reserva del puesto, llevándola y trayéndola de la bóveda; una bóveda en llamas no pierde oro y un puesto en llamas sí; comprar sin oro suficiente en el pueblo se rechaza; guardar y cargar conserva el oro de cada edificio (verificado por hash).
29. **Comercio automático en el puesto** (agregada el 2026-09-27 a pedido del usuario).
   - En la ventana del puesto de comercio, reglas por recurso: "vender si en el pueblo hay más de N" y "comprar si hay menos de M".
   - Solo se aplican mientras hay mercaderes de visita, una vez al día. Compran solo con el oro que está en el puesto, nunca con el de la bóveda; así la reserva del puesto es el presupuesto del comercio automático. Venden igual que la venta a mano: primero del puesto y luego de los demás almacenes. Lo comprado queda en el puesto.
   - Las reglas son comandos (deterministas en multijugador) y se guardan con la partida.
   - Al irse los mercaderes, un aviso resume lo que se compró y se vendió y el oro que entró o salió.
   - *Criterios:* sin mercaderes no se compra ni se vende nada; con el puesto sin oro no se compra aunque haya oro en la bóveda; ninguna regla deja el pueblo por debajo de N al vender ni por encima de M al comprar; dos instancias con las mismas reglas no se desincronizan.
30. **Visor de modelos** (agregada el 2026-09-27 a pedido del usuario).
   - Herramienta de desarrollo aparte, `SalvaCiudadModelos.exe`: se compila con el juego y usa `sc_engine` (renderizador, cargador de glTF, Dear ImGui), pero no abre el juego ni lo necesita. Sin red y sin dependencias nuevas.
   - Navegación por categorías según las carpetas del mod (edificios, objetos, personajes, animales); los árboles agrupados por especie. Elección del mod (`core` o uno instalado) y buscador por nombre.
   - Vista 3D con la luz, sombras y niebla del juego: cámara que gira alrededor del modelo, cuadrícula en metros y un aldeano de referencia para la escala. Modo "todas las variantes" que pone lado a lado los modelos de un grupo.
   - Vista previa de lo que hace el juego: tinte de estación en los árboles, paletas al azar en personajes y accesorios, animaciones de los personajes.
   - Ficha del modelo: triángulos, vértices, materiales (cada uno es una llamada de dibujo), texturas, tamaño en metros y qué definiciones lo usan.
   - Revisión del contenido: modelos que ninguna definición usa, definiciones que apuntan a un modelo que no existe y cuántas variantes tiene cada tipo.
   - Recarga automática de un modelo cuando cambia su `.glb` (al volver a correr su script de Blender). Textos en español e inglés.
   - *Criterios:* el visor abre sin el juego y lista todos los modelos de `core` por categoría; muestra cada modelo con la luz del juego y en modo de variantes; la ficha coincide con los datos de los modelos de `tests/data_models_test`; con un mod de prueba que tiene un modelo sin usar y una definición con un modelo que falta, el visor señala los dos; compila en todas las configuraciones sin advertencias.
31. **Variantes de modelos** (agregada el 2026-09-27 a pedido del usuario).
   - Las definiciones declaran sus variantes en el JSON: `"models": [...]` en lugar de `"model"` (una lista de un elemento equivale al `"model"` de hoy, que se sigue aceptando). Un mod puede agregar variantes con un parche.
   - La variante de cada objeto se elige solo en la vista, a partir del id de la entidad o de la celda; no entra en el estado de la simulación, así que no cambia el hash ni el lockstep.
   - Primero variedad sin geometría nueva: rotación, escala y espejo al azar donde el objeto lo permita, y paleta por material en los edificios (techo y paredes), como la de los aldeanos.
   - Geometría nueva donde más se nota la repetición: 3 a 5 nubes, 3 o 4 casas por nivel, rocas y arbustos. Sombreros y accesorios como mucho 2 o 3 formas cada uno, porque se dibujan animados en cada aldeano.
   - El visor de la fase 30 muestra las variantes de cada definición.
   - *Criterios:* un pueblo de 1000 aldeanos y el mapa colosal en Ultra pierden como mucho un 5 % de FPS frente a la fase 30 (medido y anotado en `docs/RENDIMIENTO.md` con las llamadas de dibujo antes y después); la misma partida muestra las mismas variantes en todas las instancias y al cargarla; el hash de la simulación no cambia; una definición con `"model"` sigue funcionando.
32. **Pulido y entrega.** `/analyze` limpio, README con la lista de verificación completa, guías revisadas, `DECISIONES.md` revisado, ZIP de entrega y compilación en tu Linux.

## 14. Pendientes para después (no implementar ahora)

- Compilación y pruebas en macOS.
- CI en GitHub para Windows, Linux y macOS.
- Steam: publicación gratuita, Workshop y conexión sin abrir puertos.
- Música.
- Estaciones extremas o de fantasía adicionales.
- Servidor dedicado.

## 15. Preguntas resueltas

Las preguntas abiertas de la versión 1 se respondieron el 2026-09-26 y sus respuestas ya están integradas en el documento. El detalle está en `docs/DECISIONES.md` (D-009 a D-013).
