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
- **Niebla de guerra:** sin niebla, estática o dinámica (fases 32 a 34), y visión compartida entre aliados (activada por omisión).

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
- **Pausa:** es la velocidad x0. El tiempo se detiene, pero la cámara se mueve libre y se pueden dar órdenes, que se cumplen al reanudar. No desenfoca la pantalla ni bloquea la interfaz (D-3320).
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
- **Movimiento:** la velocidad depende del tipo de suelo y de la clase de viajero, según una tabla en los datos. Las rutas se suavizan con línea de vista sin abandonar los caminos, y esquivan troncos y rocas; todo se calcula al crear la ruta. Cada aldeano tiene su propio lugar de llegada y recalcula su ruta solo cuando se atasca. No hay colisiones entre aldeanos en la simulación (fase 35).
- **Caminos:** de tierra (×2) y de piedra (×3), construidos por peones (fase 36).
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
8. **Primer pueblo jugable (un jugador).** Aldeanos con búsqueda de rutas, trabajo, hambre, edad, nacimiento y muerte; recolección de madera, piedra y bayas; almacén, casas, leñador, recolector y centro del pueblo; construcción por etapas; barra de construcción, barra de recursos, ventanas de edificio y de aldeano (aún sin acoplamiento); velocidad y pausa; guardar y cargar.
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
32. **Niebla de guerra estática** (agregada el 2026-09-27 a pedido del usuario).
   - Opción de partida "Niebla de guerra": *sin niebla* (se ve todo, como hasta ahora), *estática* (por omisión) o *dinámica* (fase 33). Va en `GameRules`, así que es igual para todos los jugadores y se guarda con la partida y con la partida nueva recordada. Opción "Visión compartida entre aliados", activada por omisión.
   - Esquema mixto: lo **explorado** está en la simulación (determinista, se guarda en la partida); lo **visible ahora** lo calcula solo la vista, para dibujar.
   - Rejilla de niebla de 4 m. Lo explorado es un bit por celda y por jugador que solo se enciende; la simulación lo actualiza una vez por segundo a partir de la posición de lo que da visión. Con visión compartida, los aliados comparten lo explorado.
   - Radio de visión en los datos, `"sight"` en metros, en unidades, edificios y razas (aldeanos); las torres ven más lejos y el centro del pueblo revela el terreno inicial. Los animales, asaltantes y mercaderes no dan visión a nadie.
   - Estática: lo no explorado se ve negro; lo explorado se ve siempre como sin niebla, con todo lo que pasa en él.
   - No se puede colocar un edificio en celdas no exploradas; sí se puede mandar un ejército hacia ellas.
   - La niebla se dibuja en el terreno, el agua, los modelos y la hierba con bordes suaves, y también en el minimapa. Lo que está bajo niebla negra no se puede seleccionar ni muestra su tooltip, y las capas del mapa no muestran lo que hay en ella.
   - Mapas separados: cada jugador descubre su región. Repeticiones: se ve todo, con un selector para ver lo de un jugador. Herramientas de desarrollo: "Revelar todo" solo en la vista.
   - *Criterios:* con "sin niebla" el hash y la suma de verificación del mapa pequeño no cambian; dos instancias en multijugador tienen lo mismo explorado (prueba) y no se desincronizan; guardar y cargar conserva lo explorado; colocar un edificio en lo no explorado se rechaza también como comando; un pueblo de 1000 aldeanos en el mapa colosal en Ultra pierde como mucho un 5 % de FPS y la simulación como mucho un 3 % de tiempo por tick (anotado en `docs/RENDIMIENTO.md`).
33. **Niebla de guerra dinámica** (agregada el 2026-09-27 a pedido del usuario).
   - Lo explorado sin visión actual se ve gris tenue: terreno, árboles, rocas, vetas y demás objetos naturales en su estado actual, pero sin lo que se mueve.
   - Todo lo que no es del jugador (animales, asaltantes, mercaderes, unidades y aldeanos de otros jugadores, también aliados) solo se ve donde hay visión actual del jugador o, con visión compartida, de sus aliados.
   - Edificios de otros jugadores: bajo niebla gris se ven como **fantasmas**, tal como se vieron por última vez (tipo, nivel, variante, etapa de construcción, en llamas o no), aunque ya no existan o hayan cambiado. Los fantasmas están en la simulación (se anotan en la misma actualización de cada segundo), así que se guardan con la partida y son iguales en todas las instancias.
   - Lo oculto no se dibuja, no se puede seleccionar, no muestra tooltip, no suena, no aparece en el minimapa ni en las capas, y sus partículas no se ven. Los avisos sobre el propio pueblo (asaltos, incendios, enfermedades) se siguen dando; los que revelarían algo oculto, no.
   - *Criterios:* un lobo que sale del radio de visión desaparece y vuelve a verse al entrar; un edificio enemigo destruido fuera de la visión sigue como fantasma hasta volver a verlo; los sonidos de una pelea bajo niebla no se oyen; guardar y cargar conserva los fantasmas; mismos límites de rendimiento que la fase 32.
34. **Niebla con techo de altura** (agregada el 2026-09-27 a pedido del usuario).
   - La niebla tapa solo hasta un techo: la altura del terreno suavizada (un mapa de alturas de baja resolución y desenfocado) más unos metros, con una franja de transición. Lo que sobresale del techo (cerros, picos, árboles gigantes, torres altas) se ve aunque haya niebla.
   - Bajo niebla negra, lo que sobresale se ve como silueta oscura y desaturada; bajo niebla gris, como sin niebla.
   - Solo cuenta para el terreno y los objetos fijos; lo que se mueve nunca se ve por encima del techo. Una definición puede marcarse `"landmark": true` para verse siempre como silueta aunque no sobresalga (se puede cambiar con un parche de mod).
   - Ver algo por encima del techo no cuenta como explorado: no permite construir ahí.
   - *Criterios:* una meseta ancha no se revela entera, pero un pico aislado sí; un árbol marcado como `landmark` se ve en lo no explorado; un gigante o un animal alto no se ve bajo la niebla; la simulación no cambia (mismo hash con y sin techo); mismos límites de rendimiento que la fase 32.
35. **Movimiento de los aldeanos** (agregada el 2026-09-27 a pedido del usuario). En esta fase, "ruta" es el trayecto que sigue un aldeano; "camino" es lo que se construye (fase 36). Regla de rendimiento de toda la fase: lo nuevo se calcula al crear una ruta o solo en la vista. En cada tick, cada aldeano hace a lo más unas pocas lecturas triviales.
   - **Tipo de suelo y velocidad real:** la rejilla de 2 m guarda por celda un tipo de suelo (normal, bosque, mojado; los caminos llegan en la fase 36), además de si está bloqueada y su pendiente. Una tabla en los datos da la velocidad de cada tipo de suelo para cada clase de viajero: aldeanos, unidades, asaltantes, mercaderes y animales. Así, las carretas y los caballos de más adelante solo agregan una clase. Un mod puede agregar suelos y clases, o cambiar la tabla con un parche.
     - `move()` usa la velocidad del suelo que se pisa. Hoy el terreno solo cambia qué ruta se elige; con esto, el bosque, lo mojado y las pendientes también frenan de verdad. El suelo normal y plano conserva la velocidad actual.
     - El costo del A\* pasa a ser tiempo: distancia entre velocidad. La escala del costo cambia para que quepan velocidades ×2 y ×3 sin redondeos que las distorsionen.
   - **Rutas suavizadas:** después del A\*, se quitan los puntos intermedios cuando hay línea de vista sobre la rejilla. La línea de vista no cruza celdas bloqueadas ni corta esquinas. Solo se acorta un tramo si el atajo no tarda más que la ruta original, así que una ruta que sigue un camino no lo abandona para cruzar por el pasto. En terreno abierto se camina en cualquier ángulo y no solo en 8 direcciones. Aplica a las rutas de aldeanos y unidades; las de los asaltantes que atraviesan edificios se quedan como hoy.
   - **Troncos y rocas:** al crear la ruta, si un tramo pasa demasiado cerca de un tronco o una roca, se agrega un punto de desvío. El radio de cada objeto se define en los datos (`"radius"` en metros; un mod puede cambiarlo con un parche). No se revisan colisiones contra troncos en cada tick, y los troncos no se marcan como celdas bloqueadas, porque con celdas de 2 m el bosque quedaría intransitable.
   - **Lugares de llegada:** los puntos alrededor de un edificio se reparten entre quienes llegan a él, según un número de lugar que sale del aldeano, así que no hace falta un campo nuevo. Dos aldeanos que llegan desde el mismo lado ya no terminan en el mismo punto. El último tramo nunca termina dentro de una celda bloqueada: si el destino exacto cae en una, se usa el punto libre más cercano.
   - **Desatascar:** en cada tick, el aldeano solo revisa si la celda de su siguiente punto quedó bloqueada. Si quedó bloqueada, o si lleva unos segundos sin avanzar, recalcula su propia ruta. Tras varios intentos fallidos abandona la tarea, como hoy. Un cambio en la rejilla (un edificio o un camino nuevo) nunca hace recalcular a todos: quien ya va en camino termina su ruta, y el camino nuevo se aprovecha en la siguiente. Si en un tick piden recalcular más aldeanos que un tope, los demás esperan al siguiente, en orden de índice. Si se construye un edificio encima de un aldeano, este pasa a la celda libre más cercana.
   - **Vueltas suaves:** solo en la vista, las esquinas de la ruta se dibujan redondeadas. Se apartan como mucho medio metro de la posición de la simulación, así que no cambian el hash ni afectan la selección.
   - Los contadores nuevos (ticks sin avanzar, intentos) y el tipo de suelo de cada celda se guardan con la partida. Una partida anterior se carga con los contadores en cero y el suelo calculado del mapa.
   - Queda fuera de esta fase:
     - La separación entre aldeanos en la simulación, porque costaría en cada tick con cada vecino. Si después de esta fase todavía se amontonan, se evalúa un desplazamiento solo visual.
     - La aceleración y el frenado.
     - La evitación completa del tipo RVO/ORCA.
   - *Criterios:*
     - Una ruta por terreno abierto sin obstáculos es un solo tramo.
     - En mapas al azar de varias semillas, ningún tramo de ninguna ruta cruza una celda bloqueada ni corta una esquina, y ninguno pasa por dentro del radio de un tronco o una roca (salvo el recurso que se va a trabajar).
     - Un aldeano tarda más en cruzar 20 m de bosque que 20 m de pasto plano, en la proporción que dice la tabla. En pasto plano tarda lo mismo que antes de esta fase.
     - Con un suelo de prueba ×3 que da una vuelta, la ruta lo sigue cuando ahorra tiempo y el suavizado no lo corta.
     - Cuatro aldeanos mandados al mismo edificio desde el mismo lado terminan al menos a 1 m entre sí.
     - Un edificio colocado sobre la ruta de un aldeano lo hace recalcular y llegar. Un edificio colocado encima de un aldeano lo deja afuera.
     - En una partida larga con construcción, ningún aldeano queda dentro de una celda bloqueada.
     - Dos instancias en multijugador no se desincronizan, y guardar y cargar conserva el hash.
     - En la prueba de 12 pueblos de 1000 aldeanos:
       - el tick promedio crece como mucho un 3 %;
       - el tick más lento no crece;
       - todo se anota en `docs/RENDIMIENTO.md`.
36. **Caminos de tierra y piedra** (agregada el 2026-09-27 a pedido del usuario).
   - Dos tipos de camino en los datos: tierra y piedra. Son suelos de la tabla de la fase 35. Para aldeanos, unidades, asaltantes y mercaderes, la tierra es ×2 y la piedra ×3 sobre el suelo normal; los animales no ganan velocidad en ellos. Un mod puede agregar tipos de camino o cambiar las velocidades con un parche.
   - Herramienta para trazar: se arrastra sobre el mapa y el trazo se ajusta a la rejilla de 2 m, en línea recta o con esquinas. Muestra el costo total antes de confirmar.
     - Mismas reglas que un edificio: no se traza sobre agua, acantilados, edificios ni terreno sin explorar. Los árboles, rocas y demás cosas del trazo se quitan como al colocar un edificio.
     - No se puede colocar un edificio sobre un camino; primero hay que quitar el camino.
   - Los construyen los peones, tramo por tramo:
     - Tierra: solo tiempo de trabajo.
     - Piedra: piedra por tramo y más tiempo. Se puede trazar piedra sobre tierra para mejorarla.
     - Un tramo solo cuenta como camino (y da velocidad) cuando está terminado.
   - Quitar un camino sigue las reglas de demoler un edificio.
   - Sin desgaste ni mantenimiento, y no aparecen senderos solos.
   - Trazar, mejorar y quitar son comandos (deterministas en multijugador). Los caminos se guardan con la partida.
   - Se dibujan en el terreno con bordes suaves y con uniones limpias en esquinas y cruces, en el minimapa y en la capa de terreno. Bajo la niebla se ven como el terreno: en lo explorado, en su estado actual.
   - **Rendimiento del A\*:** con suelos hasta ×3 más rápidos, una estimación que nunca sobrestima tendría que suponer que todo el resto es piedra, y el A\* exploraría muchas más celdas. Se usa una estimación intermedia: rutas casi óptimas, con una exploración parecida a la de hoy. El presupuesto de nodos por búsqueda se revisa con caminos largos. Si no alcanza, se anota y se propone una red de caminos como grafo aparte, antes de implementarla.
   - *Criterios:*
     - Un aldeano recorre 60 m de piedra en un tercio del tiempo que 60 m de pasto plano, y 60 m de tierra en la mitad.
     - Entre dos puntos unidos por un camino de piedra que da un rodeo razonable, el aldeano toma el camino.
     - Un tramo de piedra descuenta la piedra y no da velocidad hasta estar terminado.
     - Trazar sobre agua, edificios o lo no explorado se rechaza también como comando. Colocar un edificio sobre un camino se rechaza.
     - Dos instancias en multijugador no se desincronizan, y guardar y cargar conserva los caminos y el hash.
     - En la prueba de 12 pueblos de 1000 aldeanos, con una red de caminos en cada pueblo:
       - el tick promedio crece como mucho un 5 % frente a la fase 35;
       - el tick más lento no crece;
       - todo se anota en `docs/RENDIMIENTO.md`, con las celdas exploradas por búsqueda.
37. **Nombres del terreno bajo el cursor** (agregada el 2026-09-29 a pedido del usuario, para poder nombrar lo que el generador hace y pedir cambios).
   - El mapa guarda los accidentes que el generador colocó, con su tipo, su trazo y su ancho: mesetas, valles, cordilleras, cañones, golfos, penínsulas, cabos, islotes, islas, fosas, dorsales y ríos. También guarda el nivel del mar de cada región. Viajan con la partida guardada y en el multijugador, pero no cambian el terreno ni su suma de verificación, y ninguna regla del juego los lee.
   - Lo que se guarda es lo que de verdad quedó en el terreno: un golfo o una península que las bahías y cabos pequeños acortaron se guarda recortado, y uno que no llegó a formarse no se guarda.
   - La ventana de estadísticas (F3) muestra "Bajo el cursor": casilla, suelo, bioma, altura, pendiente, fertilidad, agua (río, lago o mar, con su profundidad) y los accidentes del lugar, incluida la costa. En lo no explorado solo dice "Todavía sin explorar". También funciona en la vista previa del mapa, antes de empezar la partida. El panel "Terreno" de las herramientas de desarrollo muestra lo mismo.
   - Rendimiento: con F3 cerrado no cuesta nada. Con F3 abierto se describe la casilla solo cuando cambia, con un índice de los accidentes por cuadros de 128 m.
   - *Criterios:* sobre un cañón, una meseta, un valle o una cordillera, F3 dice su nombre; en el agua dice si es río, lago o mar; los golfos, penínsulas y cabos se nombran donde realmente están; guardar y cargar conserva los nombres; la suma de verificación del mapa no cambia; con F3 cerrado no hay costo medible.
38. **Reporte del mapa con Ctrl+F12** (agregada el 2026-09-29 a pedido del usuario).
   - Ctrl+F12 sobre el mapa: se oculta la interfaz, la cámara queda quieta y una partida local se pausa. Se pintan trazos con el ratón; Retroceso borra el último, Supr borra todos, Enter guarda y Esc cancela.
   - Se guarda en `%TEMP%\SalvaCiudad\reportes\<fecha_hora>\`: `captura.png` (con trazos), `captura_limpia.png` y `reporte.json` (versiones, semilla y opciones del mapa, cámara, lo que hay bajo el cursor, casillas de cada trazo y un resumen). Se conservan los últimos 30.
   - `--reporte <carpeta>` genera el mismo mapa con el generador actual, pone la cámara igual, guarda `despues_<fecha_hora>.png` y un `.txt` con lo que cambió, y se cierra, sin tocar la configuración.
   - *Criterios:* Enter crea la carpeta con las dos capturas y un JSON válido; Esc no crea nada; las casillas de los trazos son las del rayo de la cámara; `--reporte` reproduce la vista con la misma suma de verificación del mapa; un `reporte.json` dañado o manipulado se rechaza; sin Ctrl+F12 no hay costo.
39. **Generadores de mapas intercambiables y generador jerárquico: mundo y regiones** (agregada el 2026-09-30 a pedido del usuario; las fases 39 a 43 se hacen seguidas, sin su intervención, y él las prueba al final).
   - La partida nueva tiene "Generador de mapas": *clásico* (el de siempre, sin cambios: mismos mapas y mismas sumas de verificación) o *jerárquico* (el nuevo). Cada generador es un módulo independiente con su propia versión. Se guarda en `MapSettings`, en la partida y en la partida nueva recordada, y agregar otro generador después solo requiere un módulo nuevo y su nombre en la lista.
   - El jerárquico decide de lo general a lo particular, y cada nivel solo refina lo que permitió el anterior:
     - nivel 0, mundo: tamaño, semilla, mar e islas;
     - nivel 1, regiones;
     - nivel 2, estructuras;
     - nivel 3, agua;
     - nivel 4, suelo y vida;
     - nivel 5, detalle fino.
     Las partes comunes (lagos por inundación desde el borde, ríos, suelo, biomas, bosques, recursos, fauna, salidas) se reutilizan como etapas compartidas.
   - Nivel 1: el mapa se divide en regiones irregulares (celdas de Voronoi deformadas por ruido), de 150 a 900 m según el tamaño del mapa. Cada región recibe un solo papel: llanura, colinas, montañas, meseta o cuenca. "Relieve" cambia la proporción de montañas y colinas; "Accidentes del terreno" cambia cuántas regiones no son llanura. Reglas:
     - las montañas se agrupan en cadenas de regiones vecinas;
     - una meseta no toca el mar ni otra meseta;
     - una cuenca queda rodeada de terreno más alto.
   - Cada papel da una altura base. Entre regiones de papel distinto hay una transición suave, salvo en el borde de una meseta, que es un acantilado.
   - El mapa guarda qué región y qué estructura ocupa cada cuadro de 8 m, y F3 muestra ambos nombres de forma exacta ("Región: Montañas", "Estructura: …").
   - *Criterios:* el generador clásico da las mismas sumas de verificación que antes; con "jerárquico", cada casilla pertenece a una sola región y F3 dice su papel; la misma semilla da el mismo mapa; guardar y cargar conserva el generador y los nombres; un mapa mediano se genera en un tiempo parecido al clásico.
40. **Generador jerárquico: estructuras** (agregada el 2026-09-30).
   - Dentro de cada región solo se colocan estructuras de su papel, y cada casilla pertenece a una sola estructura:
     - montañas: una cresta principal con picos y a veces un paso;
     - colinas: lomas suaves;
     - meseta: cima plana, acantilado alrededor y una o dos rampas;
     - valles: fondo en U que baja hacia una salida, entre montañas o colinas;
     - cañones: pocos, angostos y de paredes a pique, que solo cruzan mesetas o montañas y bajan hacia terreno más bajo; la mayoría llevan un río en el fondo.
   - "Accidentes del terreno" decide cuántos valles y cañones hay. Con "Muchos" siguen siendo pocos cañones y claramente separados.
   - *Criterios:* ninguna casilla es a la vez cañón y cordillera o meseta; en mapas al azar de varias semillas, cada cañón es más bajo que sus dos lados, cada meseta tiene una cima plana y cada cresta es más alta que sus faldas; hay menos cañones que en el generador clásico con las mismas opciones.
41. **Generador jerárquico: agua** (agregada el 2026-09-30).
   - Mar según "Mar" (uno o dos lados, con golfos, penínsulas y cabos) y los tipos de mapa con islas y archipiélagos. Las islas también reciben regiones con papel. Hay lagos en las cuencas. Los ríos nacen en las montañas y colinas y siguen primero los valles y los cañones con río.
   - F3 distingue río, lago y mar sin confundir un cauce inundado por el mar con una dorsal o con mar abierto: la desembocadura de un río se nombra "Estuario".
   - *Criterios:* todo cañón o valle marcado "con río" tiene agua en su fondo; los mapas de islas tienen la cantidad de islas pedida y cada pueblo empieza en la suya; toda salida tiene agua cerca.
42. **Generador jerárquico: suelo, vida y detalle** (agregada el 2026-09-30).
   - Humedad, fertilidad y suelo según la región y el agua. Biomas que siguen las regiones (por ejemplo, pinares en las montañas). Bosques, recursos y fauna con las etapas compartidas. Salidas justas para cada jugador en llanuras o colinas. Irregularidades pequeñas del terreno para que no se vea liso.
   - Funciona con todos los tamaños (hasta colosal), tipos de mapa, mapas separados y de 1 a 12 jugadores.
   - *Criterios:* las mismas garantías de salida que el clásico (recursos, agua y espacio); el mapa colosal se genera en un tiempo parecido al clásico (anotado en `docs/RENDIMIENTO.md`); guardar, cargar y multijugador sin desincronizar.
43. **Generador jerárquico: ajuste y documentación** (agregada el 2026-09-30).
   - Revisión con `--reporte` de mapas de varias semillas y tamaños, y ajuste de proporciones y alturas.
   - `docs/GENERADORES.md` explica cada generador: sus niveles, cada región y estructura con su nombre, qué opción de la partida controla cada una y con qué frecuencia aparece.
   - *Criterios:* el documento cubre todo lo que F3 puede nombrar; las pruebas de cada nivel pasan en las tres configuraciones.
44. **Animales animados: esqueleto y animaciones del cerdito** (agregada el 2026-09-30 a pedido del usuario). Los animales de `art/blender/zoo/` salen de la técnica de modelado que él eligió (remesh y reducción, la 06 de los estudios); esta fase les da esqueleto y animaciones, empezando por el cerdito.
   - **Plantilla de cuadrúpedo** en `art/blender/rigs.py`: pelvis, columna, pecho, cuello, cabeza, orejas, cola en cadena y tres o cuatro huesos por pata. Cada especificación de `zoo/` declara dónde están sus articulaciones y el esqueleto se arma con eso. Los nombres de los huesos son fijos por plantilla, así que las animaciones de una familia sirven para todos sus animales.
   - **Pesos calculados por código:** cada vértice se ata a los huesos más cercanos (hasta 4, que suman 1), con una transición suave en las articulaciones. Las piezas sueltas (orejas, cola, ojos) van enteras a un solo hueso para no deformarse. Regenerar da el mismo archivo (D-402).
   - **Animaciones generadas por código** a 30 fps: `idle` (respiración, cabeza, orejas y cola), `walk` (las patas en el orden del paso natural), `run` (trote), `eat` (la cabeza al suelo) y `die` (cae de lado; no se repite). Se animan en el lugar, sin avanzar. El largo del paso y la velocidad de marcha salen de las medidas del animal y se guardan en el modelo para el visor y el juego.
   - **Vista previa:** por cada animación, una tira de 8 fotogramas vista de lado, junto a la imagen de 4 vistas del modelo.
   - Los demás animales siguen generándose sin esqueleto hasta que tengan plantilla.
   - *Criterios:*
     - El `.glb` del cerdito tiene un esqueleto de hasta 64 huesos y hasta 16 animaciones, cada vértice con hasta 4 pesos que suman 1, y lo carga el cargador del juego.
     - Cada animación que se repite termina en la pose con que empieza: no hay salto al volver a empezar.
     - En `walk` y `run`, las pezuñas nunca bajan de Z = 0, y durante el apoyo retroceden a la velocidad de marcha guardada (±10 %), así que no patinan en el juego (medido por script).
     - El modelo sigue dentro de su límite de triángulos (los anillos que se cortan en las articulaciones suman algunos, D-4403); regenerar da el mismo archivo byte a byte.
     - En las tiras no hay piezas separadas ni pliegues notorios en rodillas, hombros ni cuello (revisión visual).
45. **Visor: revisión de animaciones** (agregada el 2026-09-30 a pedido del usuario, para validar las animaciones antes de meterlas al juego).
   - En el visor de modelos (fase 30): velocidad de reproducción (de 0,25× a 2×), pausa, avance y retroceso fotograma a fotograma, y el número de fotograma.
   - Suelo que avanza bajo el modelo a su velocidad de marcha guardada mientras se reproduce `walk` o `run`, para ver si las patas patinan sin entrar al juego.
   - Opción para dibujar el esqueleto encima del modelo.
   - Abrir una carpeta de modelos en estudio (por omisión `art/studies/animals`) como si fuera un mod, sin tocar `core`, con la recarga automática de la fase 30.
   - Textos en español e inglés.
   - *Criterios:* el cerdito se ve en el visor con sus 5 animaciones, igual que en las tiras de Blender; el suelo avanza a la velocidad guardada; paso a paso recorre cada fotograma; los modelos de `core` y los personajes se ven igual que antes; compila sin advertencias en todas las configuraciones.
46. **Animales animados: todas las familias** (agregada el 2026-09-30 a pedido del usuario).
   - Plantillas y animaciones para el resto de `zoo/`:
     - cuadrúpedos: con trompa (elefante), con cuello largo, con alas (grifo, dragón: se agrega `fly`), y el conejo con patas de salto (`walk` y `run` a saltos);
     - aves: el gallo primero; `idle`, `walk`, `run`, `eat` (picotear), `die`, y `fly` en las que vuelan;
     - nadadores: el tiburón ondula el cuerpo y la cola; la tortuga rema con las aletas (`swim` en lugar de `walk` y `run`);
     - el pulpo, con los tentáculos en onda.
   - La flora no lleva esqueleto: su balanceo con el viento se decide al meterla al juego.
   - *Criterios:* los mismos de la fase 44 para cada animal; el usuario los revisa en el visor y las correcciones que pida se hacen dentro de esta fase.
47. **Animales animados en el juego** (agregada el 2026-09-30 a pedido del usuario).
   - Al empezar la fase se decide con el usuario qué especies entran (las del juego hoy son ciervo, jabalí, lobo y oso, sin esqueleto) y con qué comportamiento.
   - Los animales se dibujan con esqueleto como los aldeanos, sin el sube y baja de hoy. La animación sale de lo que hace el animal (quieto, caminando, huyendo, comiendo, muerto) y la velocidad del clip se ajusta a su velocidad real con el largo del paso guardado en el modelo. Todo esto es solo de la vista: no entra al estado de la simulación.
   - *Criterios:* las patas no patinan a ninguna velocidad del juego; la simulación no cambia (mismo hash); con el máximo de animales a la vista, el juego pierde como mucho un 5 % de FPS, medido y anotado en `docs/RENDIMIENTO.md`.
48. **Personajes low poly animados** (agregada el 2026-10-01 a pedido del usuario; se hace junto con la fase 46, antes de la 47).
   - Los 15 personajes de `art/blender/people/` comparten un esqueleto (`art/blender/rigs_human.py`) con los mismos 17 huesos y nombres que los aldeanos del juego, para que sirvan el mismo código y los mismos accesorios. Cada personaje agrega los huesos que necesite: cola, capa, coleta, orejas.
   - Animaciones generadas por código, en el lugar: `idle`, `walk`, `run`, y las de trabajo que pidió el usuario:
     - `chop`: talar con hacha a dos manos;
     - `shoot`: levantar el arco, tensar, apuntar, soltar y bajar (para la cacería);
     - `fish_cast` (lanzar, una sola vez), `fish_stand` (pescar de pie) y `fish_sit` (pescar sentado en el suelo).
   - La herramienta es un modelo aparte (hacha, arco, caña). El modelo del personaje dice en qué mano va en cada animación (`<animación>_prop`), y las tiras de revisión la muestran en la mano.
   - Brazos y piernas se colocan por cinemática inversa hacia puntos (el pie en el suelo, las dos manos sobre el mango), así que sirven para cuerpos de cualquier proporción, del orco a la rana.
   - *Criterios:*
     - Cada personaje carga en el cargador del juego: hasta 64 huesos, hasta 16 animaciones, pesos que suman 1, dentro de su límite de triángulos.
     - `rig_check.py` da `RIG OK` en los 15: los ciclos cierran sin salto, nada baja del suelo salvo en `fish_sit`, y en `walk` y `run` los pies apoyados retroceden a la velocidad guardada (±10 %).
     - En las tiras, la ropa, el cabello, las colas y las capas siguen al cuerpo sin separarse ni atravesarlo de forma notoria, y la herramienta queda en las manos (revisión visual).
     - Regenerar da el mismo archivo byte a byte.
     - El usuario los revisa en el visor; las correcciones que pida se hacen dentro de esta fase.
49. **Un solo generador: el jerárquico** (agregada el 2026-10-02 a pedido del usuario; las fases 49 a 56 reorganizan el juego en torno a los modelos low poly nuevos. Lo anterior quedó archivado en `J:\Back\salvaciudad-alfa-1.zip`).
   - Se borra el generador clásico: en `worldgen.cpp`, el relieve por ruido, las costas, las islas a la antigua, los accidentes del terreno y el fondo marino (unas 900 líneas); el selector de generador de la partida nueva, de los ajustes y del reporte del mapa; y los accidentes que solo hacía el clásico (cordilleras, cabos, costas, fosas y dorsales), con sus nombres. F3 sigue diciendo "Costa" en la tierra junto al mar, porque eso lo calcula del mar mismo y no del accidente del clásico (D-4903). Las etapas que comparten los dos (lagos, ríos, suelo, biomas, bosques, recursos, salidas, islas por pueblo) quedan, sin las ramas del clásico.
   - El jerárquico pasa a ser el único y deja de guardar su número de generador en el mapa. Se corrige la versión de los mapas separados (siempre ponía la del clásico).
   - Las pruebas que generaban mapas clásicos sin decirlo pasan al jerárquico; las que solo probaban el clásico se borran; las sumas de verificación de referencia se vuelven a fijar. Se agregan a `ctest` los grupos de pruebas que nunca corrían (`minimap`, `nav`).
   - `docs/GENERADORES.md` describe solo el jerárquico. Las decisiones del clásico se marcan como reemplazadas, sin borrarlas.
   - Las imágenes de referencia del usuario pasan a `art/reference/` y entran al repositorio (los scripts de los árboles las leen).
   - *Criterios:* no queda código ni texto de interfaz del clásico; la misma semilla da el mismo mapa; un mapa colosal tarda como hoy con el jerárquico (anotado); las pruebas pasan en las tres configuraciones.
50. **Fondo de la pantalla de inicio con un mapa real; adiós a la escena de prueba** (agregada el 2026-10-02 a pedido del usuario).
   - Se borra la escena de prueba de la fase 3 (plano con 50 000 objetos y 2000 aldeanos), su botón en el menú, la vista de estrés y la simulación de prueba de la fase 5 (mundo de caminantes y sus repeticiones). Lo que el juego usaba de ahí pasa a su propio lugar: los cuerpos de los aldeanos y sus paletas, la carga de modelos y lo que usan las herramientas de desarrollo. Se queda la prueba que impide `float`, hilos y relojes en la simulación.
   - El fondo del menú es un mapa chico (512 m) del generador jerárquico, con su terreno, agua, árboles, rocas y animales, sin pueblos ni personajes, con la cámara girando despacio.
   - La semilla sale de una lista en los datos (`menu_backgrounds.json`); en cada arranque se elige una al azar. Con las herramientas de desarrollo abiertas, en el menú F5 genera otro mapa con una semilla nueva y F6 guarda la semilla actual en un `menu_backgrounds.json` de la carpeta de datos del usuario, que se lee además de la lista del juego (D-5004).
   - El mapa se genera en un hilo mientras se ve el logotipo, así que el menú no espera.
   - *Criterios:* el menú aparece en menos de 1 s y el mapa de fondo en menos de 3 s (medido en release); con la misma semilla se ve el mismo mapa; no queda código de la escena de prueba; los aldeanos del juego se ven igual que antes.
51. **Árboles por estación y tamaño en el motor** (agregada el 2026-10-02 a pedido del usuario).
   - Una especie declara sus modelos por estado: `"models": {"bloom": [...], "autumn": [...], "bare": [...]}`, cada uno una lista de variantes (fase 31). Una especie de hoja perenne declara solo `bloom`.
   - Primavera y verano usan `bloom`, otoño `autumn` e invierno `bare`; con nieve se aplica el tinte de nieve de hoy. El tinte de otoño e invierno se borra.
   - Cada árbol cambia de estado en un día distinto de los primeros de la estación, según su posición. Es solo de la vista: no cambia la simulación ni el hash.
   - Tamaños: el modelo se escala según la altura de cada árbol, del 50 % al 150 % de la altura del modelo. La simulación conserva chico, mediano y grande (madera, tiempo de tala, separación); `huge` queda para los gigantes (fase 55).
   - El visor muestra los estados de una especie lado a lado.
   - *Criterios:* una especie de prueba con los tres estados se ve con el modelo de cada estación en el juego y en el visor; en la primera semana de otoño hay árboles en los dos estados; el hash de la simulación no cambia con la estación que se ve; compila sin advertencias en todas las configuraciones.
52. **Versión lejana de los árboles (LOD)** (agregada el 2026-10-02 a pedido del usuario).
   - Cada modelo de árbol tiene una versión lejana de unos 300 triángulos: tronco y ramas gruesas, y el follaje como pocas masas facetadas del color dominante de cada masa. La generan los scripts de Blender, para cada estado; el modelo declara su versión lejana en los datos.
   - El renderizador elige la versión por el tamaño del árbol en pantalla, con un margen para que no parpadee. Las sombras usan siempre la lejana.
   - El visor muestra las dos versiones y permite forzar una.
   - *Criterios:* con la partida de referencia de `docs/RENDIMIENTO.md` (mapa colosal, semilla 12345, Ultra) y un bosque de árboles nuevos a la vista, los FPS y los triángulos dibujados quedan como mucho un 10 % peor que con los árboles de antes de esta fase (medido y anotado); el cambio de versión no se nota a la distancia normal de juego.
53. **Árboles nuevos en core; se borran los viejos** (agregada el 2026-10-02 a pedido del usuario).
   - Los 32 árboles y los 8 gigantes de `art/blender/lowpoly_trees/` entran a `core`, en `models/trees/`, con nombres en español e inglés. Especies, con sus variantes:
     - cerezo (variantes 1, 2, 3 y la de la segunda imagen), cerezo llorón, jacarandá (4 variantes y la de la segunda imagen), olmo (4 variantes), guayacán (4 variantes);
     - pino, abedul, sauce llorón, acacia, ciprés, magnolia, arce, palmera, glicinia, roble amarillo, laurel, baobab, drago y manzano;
     - de hoja perenne: pino, ciprés, palmera, laurel y drago.
   - Se borran los 21 árboles viejos y todo lo suyo: modelos, `art/blender/trees.py`, `preview_trees.py`, los árboles de `props.py`, sus especies, biomas y tipos de mapa, sus textos y `docs/ARBOLES.md` (reemplazado por el catálogo nuevo). También los estudios de técnicas del cerdito y el tigre.
   - Madera por tamaño según el tronco de cada especie, en los datos.
   - Hasta la fase 54, los biomas de `core` reparten las especies nuevas con las reglas de hoy.
   - *Criterios:* una partida nueva solo tiene árboles nuevos; no queda ningún archivo de los viejos; un mod con `"patch": "core:pine"` funciona; las pruebas pasan en las tres configuraciones.
54. **Clima y biomas por geografía** (agregada el 2026-10-02 a pedido del usuario).
   - **Clima del lugar:** una temperatura que baja con la altura y hacia el norte del mapa, más la humedad que ya calcula el generador. Solo decide dónde crece cada cosa; no cambia la temperatura de la simulación (fase 10).
   - **Reglas en los datos:** cada bioma declara dónde le gusta estar: rango de temperatura y de humedad, cercanía a agua dulce o al mar, tipo de región (llanura, colinas, montañas, meseta, cuenca) y un peso. Cada lugar toma el bioma que mejor encaja, con transiciones irregulares.
   - **Biomas de `core`:**

     | Bioma | Dónde | Especies | Gigante |
     |---|---|---|---|
     | Bosque de montaña | Frío, montañas y alturas | pino, abedul, ciprés | secuoya, araucaria |
     | Bosque boreal | Frío, llanuras y colinas del norte | pino, abedul | — |
     | Bosque templado | Templado, humedad media, llanuras y colinas | olmo, arce, roble amarillo, abedul, manzano | ginkgo |
     | Bosque florido | Templado a cálido, húmedo, llanuras | cerezo, jacarandá, magnolia, glicinia | cerezo gigante |
     | Ribera | Junto a ríos y lagos, salvo en el frío | sauce llorón, cerezo llorón, olmo, abedul | sauce gigante |
     | Mediterráneo | Templado a cálido, seco, colinas y costas | ciprés, laurel, pino, manzano | — |
     | Bosque seco tropical | Cálido, humedad media | guayacán, jacarandá, laurel | — |
     | Sabana | Cálido y seco, mesetas y llanuras | acacia, baobab, drago | baobab gigante |
     | Costa tropical | Cálido, junto al mar | palmera, laurel | mangle gigante |
     | Huerto silvestre | Templado, fértil, llanuras (raro) | manzano, cerezo, laurel | — |
     | Bosque encantado | Húmedo, cuencas (raro) | glicinia, cerezo llorón, magnolia | hongo gigante |

   - Se borran los tipos de mapa como datos (sus manchas al azar, `patchSize`, `sizeBias`, el bioma único). F3 y el reporte del mapa muestran la temperatura del lugar y por qué tiene su bioma.
   - *Criterios:* en mapas de varias semillas y tamaños, los sauces están a menos de 40 m de agua dulce, las palmeras a menos de 150 m del mar, los pinos de montaña en la mitad más alta del mapa y no hay palmeras junto a pinos; un mapa mediano se genera en un tiempo parecido al de hoy; la misma semilla da el mismo mapa; las salidas siguen siendo justas; revisión del usuario con `--reporte`.
55. **Árboles gigantes como hitos** (agregada el 2026-10-02 a pedido del usuario).
   - Pocos por mapa, según su tamaño (por ejemplo de 2 a 4 en uno mediano y unos 30 en uno colosal), cada uno en su bioma y lugar: el mangle en un estuario o costa baja, la secuoya y la araucaria en laderas de montaña, el sauce junto a un río, el baobab en la sabana, el hongo en un claro del bosque encantado, el cerezo y el ginkgo en llanuras. Lejos entre sí y de las salidas, con un claro alrededor.
   - Se ven siempre como silueta a través de la niebla (`landmark`, fase 34). Se pueden talar: mucha madera y mucho tiempo, en los datos. Cambian por estación como los demás.
   - *Criterios:* en mapas de varias semillas, cada gigante está en su bioma y lugar; ninguno a menos de 200 m de una salida; se ven bajo la niebla; talar uno da la madera de los datos; el rendimiento con varios a la vista se mide y se anota.
56. **Partida nueva: Variado y Personalizado** (agregada el 2026-10-02 a pedido del usuario).
   - Siempre visibles: tamaño, jugadores y semilla. Dos tipos de mapa:
   - **Variado** (por omisión): sin más opciones. La semilla decide el clima (frío, templado, cálido o mezclado) y el mar (sin mar, uno o dos lados, a veces islas o archipiélago). Lo demás en valores medios: relieve suave, ríos, lagos, bosques y recursos normales, gigantes normales, 4 estaciones con año normal e invierno normal, recursos iniciales normales, enfermedades, incendios, asaltantes y fauna peligrosa en medio, niebla estática con visión compartida, población máxima 1000, raza humana con 20 % de inmigrantes de otras razas. Una línea resume lo que salió ("Mapa templado, costa al este, 3 árboles gigantes").
   - **Personalizado:**
     - casillas: biomas (al menos uno), estaciones (cada una por separado, al menos una), razas que pueden llegar como inmigrantes, árboles gigantes sí o no;
     - barras de 0 a 200 % en pasos de 25 % (100 % es lo de Variado): temperatura (frío a cálido), humedad (seco a húmedo), ríos, lagos, bosques, recursos, relieve, accidentes del terreno, gigantes, duración del año, otras razas, y población máxima de 50 a 1000;
     - listas: mar (sin mar, un lado, dos lados, islas, archipiélago; con islas, las islas por pueblo), invierno (suave, normal, duro), raza inicial (o mixta), recursos iniciales, enfermedades, incendios, asaltantes, fauna peligrosa (ninguna a brutal), niebla de guerra (ninguna, estática, dinámica) y visión compartida;
     - un botón "Partir de Variado" que llena todo con los valores de Variado.
   - Una vista previa del mapa (mapa chico) se regenera al cambiar las opciones.
   - Lo elegido se recuerda en `settings.json` como hoy; un archivo de ajustes de una versión anterior se acepta y vuelve a Variado en lo que no entienda.
   - El lobby del multijugador usa el mismo formulario.
   - *Criterios:* las opciones de Personalizado cambian el mapa como dicen (más ríos con más ríos, sin invierno sin la estación); una partida con las opciones de Variado y otra en Personalizado con "Partir de Variado" dan el mismo mapa con la misma semilla; textos en español e inglés; compila sin advertencias.
57. **Personajes low poly en el juego** (agregada el 2026-10-02 a pedido del usuario; reemplaza a los aldeanos de hoy por los personajes de la fase 48).
   - Al empezar la fase se decide con el usuario:
     - qué personaje (o personajes) de `art/blender/people/` es cada raza y sexo del juego, y cuáles quedan para soldados, asaltantes y mercaderes;
     - cómo varían entre sí los aldeanos de una misma raza: recoloreando por paleta la ropa, la piel y el cabello como hoy, con varios modelos por raza, o con las dos cosas;
     - si los niños son el modelo del adulto a menor escala, como hoy, o tienen modelo propio;
     - qué pasa con los sombreros, las barbas y los delantales de hoy.
   - Los aldeanos se dibujan con los personajes nuevos. La animación sale de lo que hace el aldeano: quieto, caminando, corriendo (al huir o con la alarma), talando, cazando con arco y pescando; los oficios sin animación propia usan una genérica de trabajo, que se agrega. La velocidad del clip al caminar y correr se ajusta a la velocidad real con la que guarda el modelo, como en los animales (fase 47).
   - La herramienta del oficio (hacha, arco, caña y las que se agreguen de `art/blender/weapons/`) va en la mano que dice el modelo (`<animación>_prop`) y solo mientras dura esa animación.
   - Los soldados y los asaltantes dejan de ser un aldeano con una marca de color: tienen su personaje y su arma. La marca del color del pueblo se mantiene para distinguir bandos.
   - Antes de empezar se unifica el código repetido de los tres grupos de personajes (pendiente de la fase 48) y se corrigen los defectos de animación anotados en D-4609 que el usuario indique.
   - Todo es solo de la vista: no cambia la simulación ni el hash.
   - Cuando los personajes nuevos están en el juego, se borran los cuerpos de hoy (`art/blender/human.py`, `models/characters/`) y lo que solo servía para ellos.
   - El visor muestra cada personaje con sus paletas y con la herramienta en la mano.
   - *Criterios:* una partida nueva solo tiene personajes nuevos, de todas las razas del juego; al talar, cazar y pescar se ve la animación con su herramienta en la mano; los pies no patinan al caminar ni al correr; la simulación no cambia (mismo hash); con 1000 aldeanos a la vista (partida de referencia de `docs/RENDIMIENTO.md`) el juego pierde como mucho un 10 % de FPS, medido y anotado; las pruebas pasan en las tres configuraciones sin advertencias.
58. **Más velocidades** (ronda de ideas del 2026-10-03; idea I-001).
   - Velocidades: pausa, ×0,25, ×0,5, ×1, ×2, ×3, ×4 y ×5; en un jugador, además ×6, ×7, ×8 y ×9. La velocidad deja de ser un entero: es un índice de una tabla (en cuartos de ×1) en el reloj, la vista (animaciones, partículas, sonido) y la red.
   - Barra superior: pausa y un control "− ×N +". Teclas: 1, 2 y 3 como hoy; + y − suben y bajan un paso; la pausa recuerda la velocidad anterior.
   - Red: el mensaje de velocidad lleva el índice; el tope en red es ×5; "bajar un paso" por un jugador lento usa la tabla; el retraso de órdenes, el margen de atraso y la frecuencia de la verificación se miden en tiempo real, no en pasos, para que ×4 y ×5 se comporten como ×3. Sube la versión del protocolo.
   - Si la máquina no alcanza la velocidad pedida, el juego no pierde pasos en silencio: baja un paso de la tabla y lo avisa.
   - *Criterios:* cada velocidad avanza los pasos que le tocan por segundo real (prueba del reloj); a ×0,25 las animaciones y partículas van lentas, no congeladas; dos instancias en red votan ×5 y no pueden pasar de ahí; en un jugador ×9 funciona en un mapa mediano con 300 aldeanos sin bajar; medido y anotado en `docs/RENDIMIENTO.md` cuánto aguanta cada tamaño de partida.
59. **Años largos y duración de cada estación** (I-002).
   - En Personalizado, cada estación activa tiene su barra en minutos (de 1 a 30, en pasos de 1; 5 por omisión) y la duración del año es la suma (hasta 120 min). Reemplaza a la barra del año. Variado no cambia: 20 min en cuatro partes iguales. `ClimateSettings` guarda los minutos de cada estación; el calendario y la temperatura salen de una sola función. Los meses siguen siendo 12 de 10 días.
   - Equilibrio "por minuto real": lo que hoy va por calendario se ajusta a la duración del año para que por hora de juego pase lo mismo que con el año de 20 min: rendimiento de campos y límite anual de huertos (en proporción al año), nacimientos, llegadas, vuelta de los animales y arbustos, asaltos, mercaderes, ropa y calzado. Envejecer, las enfermedades (en días) y la duración de las estaciones sí se estiran con el año. Esto corrige también los años cortos de hoy.
   - Ajustes y reportes anteriores (porcentaje del año) se aceptan y se convierten.
   - *Criterios:* un año de 60, 75 o 90 min se puede elegir repartido como se quiera; una prueba automática de 3 años de juego a 20 min y el mismo tiempo real a 60 min da comida por habitante y población dentro de un 15 %; con invierno de 1 min y verano de 30 las fechas, la temperatura y la siembra siguen a la estación; suben las versiones de reglas y de red.
60. **Niebla "todo explorado" y reglas de comercio con precio** (I-006 y `sug-precio-maximo`).
   - Cuarto modo de niebla, "Dinámica, mapa revelado": como la dinámica, con todo el mapa explorado desde el inicio (una marca, no una cuadrícula llena). Se puede construir en cualquier parte de la región propia. En la partida nueva, la sala, los ajustes y el reporte.
   - Reglas del puesto de comercio: cada regla puede llevar "comprar solo si el precio es a lo más N %" y "vender solo si pagan al menos N %" del valor (de 75 a 125 %, en pasos de 5; sin límite por omisión).
   - *Criterios:* en el modo nuevo se ve el terreno de todo el mapa, los edificios y la gente de otros solo donde alguien propio mira, y los edificios vistos quedan como recuerdo; guardar y cargar conserva el modo sin crecer el archivo; un mercader caro no compra con la regla puesta y uno barato sí (prueba); español e inglés.
61. **Cámara: mirar hacia arriba, seguir, fantasma y lo que estorba** (I-003 y la corrección C-002).
   - Pasada de dibujo con transparencia para modelos (rígidos y con esqueleto), después de lo opaco.
   - Tercera persona: con el ojo ya en el suelo, seguir bajando sube el punto observado hasta mirar 60° hacia arriba; al volver a subir, baja primero el punto observado. Reemplaza a D-410.
   - Seguir: botón "Seguir" en la ventana del aldeano y doble clic sobre él; la cámara pasa a tercera persona y lo sigue; mover el ancla con el teclado lo suelta. En primera persona, el seguido no se dibuja.
   - Fantasma: sin nadie seguido, en el ancla se ve un aldeano humano translúcido y sin color, que mira hacia donde mira la cámara y camina cuando el ancla se mueve.
   - Lo que estorba: el edificio o árbol que contiene al ojo de la cámara (en cualquier modo), o que queda entre el ojo y el ancla en tercera persona, se dibuja translúcido mientras estorba, con una transición corta.
   - *Criterios:* en tercera persona se puede ver el cielo sin atravesar el suelo; se sigue a un aldeano entre edificios y lo que lo tapa se vuelve translúcido; al soltarlo aparece el fantasma; dentro de un edificio ya no se ven piezas sueltas; pruebas de la cámara para el nuevo límite; sin pérdida medible de FPS con nada translúcido.
62. **Ventanas, base** (I-008, parte 1; correcciones C-003 y C-001).
   - Las ventanas viven en una lista con orden de profundidad: la que se toca pasa al frente y un clic solo llega a la de arriba.
   - Ventanas por objeto: seleccionar abre el objeto en la ventana "de paso", que se reutiliza con la siguiente selección; al fijarla se queda y la siguiente selección abre otra. Clic en el suelo o Esc cierran solo la de paso. Tope de 16 ventanas de objeto; no se guardan en los ajustes.
   - "Fijar" impide cualquier cierre que no sea su propia X (Esc, clic fuera, la barra de construcción, otra selección). Si el objeto deja de existir, la ventana lo dice y se puede cerrar.
   - Se quita el plegado automático; botón de minimizar al título.
   - Imanes: también al borde inferior y a la barra de construcción, y alineación de bordes iguales entre ventanas. Los grupos se deshacen al cerrar un miembro y su numeración se restaura al cargar.
   - La X cierra las ventanas de aldeano y de edificio (C-003). La brújula es solo la aguja y la N, sin disco (C-001).
   - *Criterios:* tres ventanas de aldeano y dos de edificio abiertas a la vez, cada una con sus órdenes sobre su propio objeto; una fijada sobrevive a Esc y a clics en el mapa; la X cierra siempre y solo la ventana de arriba; pruebas de la lista de ventanas (abrir, fijar, cerrar, profundidad, imanes); un `ui.windows` anterior se lee.
63. **Ventanas, contenido** (I-008, parte 2).
   - Aldeano: nombre propio (cada raza tiene su lista de nombres en los datos; se elige al nacer o llegar, se guarda en la partida), botón de renombrar (orden del juego, hasta 24 caracteres validados), estadísticas, botones a su casa y a su trabajo que abren la ventana de ese edificio, "Seguir" y el botón de ojo.
   - Edificio: estadísticas, un botón por habitante y por trabajador (con su nombre) que abre su ventana, e interruptor "Producción: activa / detenida" (orden nueva; detenido libera a los trabajadores y recuerda cuántos quería).
   - Se pueden seleccionar árboles, piedras, vetas, arbustos, hierbas, animales, soldados y asaltantes: ventana con qué es y qué da (por ejemplo "10 troncos", "8 de carne y 1 piel") o su estado.
   - Todas las ventanas de objeto tienen el botón de ojo (lleva la cámara principal al objeto). Las listas largas se desplazan.
   - *Criterios:* de un aldeano se llega a su casa, de ahí a otro habitante y a su trabajo, con todas las ventanas abiertas; renombrar se ve en otra instancia en red y tras guardar y cargar; detener un taller deja de consumir y producir y sus trabajadores cargan como peones; al reactivarlo vuelve a su número; un árbol dice su madera; suben las versiones de reglas y de red; español e inglés.
64. **Ventanas: pestañas y ventana de cámara** (I-008, parte 3).
   - Pestañas: soltar una ventana sobre la barra de título de otra las une en una sola con pestañas; arrastrar una pestaña fuera la separa. El grupo se guarda en los ajustes (para las ventanas que se guardan).
   - Ventana de cámara: el botón de cámara de una ventana de objeto abre otra ventana con una vista en vivo del objeto (órbita fija, se puede girar y acercar dentro de la ventana), sin mover la cámara principal. El motor gana un destino de dibujo aparte: 320 × 200, a media frecuencia, sin pasto, reutilizando las sombras de la vista principal. Máximo 2 abiertas.
   - *Criterios:* cuatro ventanas unidas en una con pestañas, y vueltas a separar; dos ventanas de cámara siguiendo a dos aldeanos mientras la cámara principal está en otro lado; con las dos abiertas el juego pierde como mucho un 25 % de FPS en la partida de referencia, medido y anotado; cerrarlas devuelve los FPS.
65. **Construir en pendiente** (I-007 e I-011).
   - El límite de desnivel bajo un edificio pasa de 1,8 a 4 m. El piso queda a la altura del suelo frente a la puerta; al colocar se elige hacia dónde da la puerta girando el edificio.
   - Todos los modelos de edificios ganan cimientos de piedra de 4 m bajo el piso (un ayudante común en `buildings.py`). La vista separa la altura sobre el piso de la del modelo (marcadores, humo, selección, obra).
   - Ladera arriba, el terreno se recorta bajo el edificio solo en lo que se dibuja; la simulación no cambia alturas.
   - No se puede construir donde ningún aldeano del pueblo puede llegar (I-011): mensaje propio. Vale para edificios y campos.
   - Murallas y empalizadas quedan como están (el usuario las replanteará aparte).
   - *Criterios:* una casa en una ladera de 3,5 m de desnivel: puerta a ras de suelo, cimientos a la vista ladera abajo y sin terreno atravesando paredes; los aldeanos entran y salen; un sitio al otro lado del agua se rechaza con su mensaje; la prueba de los cazadores ya no depende de la semilla por zonas inalcanzables; suben las versiones de reglas y de red; los 55 modelos regenerados.
66. **Explorador** (I-005 e I-010).
   - Un aldeano con mucha hambre deja lo que hace y va a comer (I-010): el umbral cuenta el camino hasta la comida.
   - Edificio "Explorador" (1 trabajador, vista de 30 m en los datos). Con su trabajador seleccionado, clic derecho en el mapa o en el minimapa lo manda a ese punto (orden nueva, solo para el dueño y solo para ese trabajador). Mientras tiene una orden no hace otra cosa; al llegar o toparse con algo, espera.
   - Ruta con niebla: si el destino está explorado, el camino más corto que pase solo por celdas exploradas; si no lo hay o el destino no está explorado, línea recta hasta toparse con un obstáculo. Sin niebla, camino normal.
   - Provisiones: al recibir una orden lejos del pueblo toma comida del almacén para varios días y come de ella en el camino; cuando le queda lo justo para volver, regresa solo y avisa. Se abriga igual que los demás; los animales y los asaltantes lo atacan.
   - *Criterios:* con niebla estática, mandarlo a lo no explorado lo hace caminar recto y detenerse ante un lago, sin rodearlo; mandarlo a un punto explorado por una ruta explorada la sigue; revela 30 m a su alrededor; con provisiones para N días vuelve antes de pasar hambre (prueba); un aldeano que lleva materiales a una obra lejana ya no muere de hambre con comida en el almacén (prueba con las semillas de D-5613); las órdenes funcionan en red con dos instancias; suben las versiones.
67. **Lo que pasa, a la vista** (I-009).
   - Cargas, como en `art/reference` (la hoja de cargas): cada recurso dice en los datos su tipo de carga (troncos, piedra, saco, canasta, caja, lingotes). Carga grande, a la espalda; poca, en brazos; los alimentos, en canasta. Animación nueva de caminar y estar de pie cargando en brazos; los 17 personajes se regeneran. De lejos (versión simple) la carga no se dibuja.
   - Pilas de materiales en las obras (lo entregado) y junto a los almacenes (según lo guardado, por tipo de carga).
   - Etapas de construcción: cimientos, armazón con andamio y edificio terminado, según el avance; reemplaza al modelo que sube del suelo.
   - Flechas de cazadores, arqueros y torres (de la vista: salen al tirar y llegan al blanco).
   - Un mercader con su carreta junto al puesto de comercio mientras dura su visita.
   - Todo es de la vista: la simulación y su hash no cambian.
   - *Criterios:* un leñador vuelve con troncos a la espalda y un recolector con canasta; una obra muestra lo que ya llegó y pasa por sus etapas; el almacén lleno se ve lleno; las flechas se ven al cazar y al defender; el mercader aparece y se va con su visita; con 1000 aldeanos el juego pierde como mucho un 10 % de FPS, medido y anotado.
68. **Día y noche: el ciclo y el cielo** (pedido del 2026-10-03).
   - Regla de partida nueva, como las estaciones: casilla «Día y noche» y dos barras, minutos de día y minutos de noche a ×1 (1 a 30 cada una). Por omisión encendido, 5 y 5. El ciclo es independiente del calendario: con un año de 10 minutos, 5 de día y 10 de noche, medio año es de día y el año siguiente y medio… se repite cada 15 minutos. La partida empieza al amanecer. Apagado: siempre de día, como antes.
   - La simulación sabe, como función pura de las reglas y del tick, si es de día o de noche y cuánto va de cada uno. Viaja en las reglas (red, partidas guardadas, ajustes `newGame`).
   - Vista: el sol sale, cruza el cielo y se pone (las sombras giran); de noche lo hace la luna. Amanecer y atardecer anaranjados, noche oscura y azulada, estrellas. El agua, la niebla y las nubes siguen la luz.
   - HUD: junto a la fecha, si es de día o de noche y cuánto falta para el cambio.
   - *Criterios:* con año de 10 min, día 5 y noche 10, la prueba da día en la primera mitad del año 1 y noche hasta la mitad del año 2, y se repite; apagado, siempre es de día y el juego se ve como antes; dos instancias en red ven la misma hora; guardar y cargar la conserva; el formulario recuerda los valores; suben las versiones de reglas y de red; español e inglés.
69. **Luces de noche.**
   - Luces puntuales reales en el motor: iluminan terreno, edificios, personas y árboles cercanos; sin sombras propias. Se dibujan en una textura de luz alrededor de la cámara (1 km de lado, 2 m por punto), así que su número casi no cuesta y no hace falta un tope por calidad gráfica.
   - Dan luz: el centro del pueblo, las casas y talleres con gente (ventanas que brillan), las fogatas encendidas, y las decoraciones que por naturaleza alumbran (faroles, braseros, antorchas, linternas, velas…), declarado en los datos con `"light"` (radio en metros) y los puntos de luz del modelo.
   - Antorcha construible barata (1 tronco, 1 × 1, en Decoración) para iluminar caminos y zonas de trabajo, sin mantenimiento.
   - De noche, los aldeanos fuera de zonas iluminadas llevan una antorcha en la mano (solo de la vista).
   - *Criterios:* de noche un pueblo se ve por sus luces y lo demás queda oscuro; un farol recién construido ilumina su alrededor; las luces se apagan de día; el juego pierde como mucho un 15 % de FPS de noche frente al día, medido y anotado.
70. **Oscuridad en la simulación.**
   - Mapa de luz de la simulación (por celda, entero): lo que da luz en la fase 69 ilumina su radio. Se actualiza al construir, demoler, ocupar o apagarse.
   - De noche, fuera de la luz, los aldeanos trabajan y caminan al 75 %. Las razas con visión nocturna (gatunos) no tienen penalización: el rasgo `nightVision` por fin hace algo (reemplaza D-1904).
   - La ventana del aldeano dice cuando está a oscuras.
   - *Criterios:* prueba: de noche un leñador lejos del pueblo tarda un tercio más que de día y uno junto a un farol tarda lo mismo; un gatuno tarda lo mismo; de día no hay diferencia; con el ciclo apagado nada cambia; suben las versiones.
71. **Energía y descanso.**
   - Cada aldeano tiene energía. Se gasta igual de día y de noche: unos 8 minutos (a ×1) de actividad. Al acabarse deja lo que hace, va a su casa y se queda 2 minutos hasta recuperarla. Sin casa descansa junto al centro del pueblo o una fogata, el doble de lento.
   - Comer, abrigarse y huir siguen teniendo prioridad sobre descansar; los soldados con una orden y quienes atienden la campana no se van a descansar hasta terminar.
   - Regla de partida «Cansancio y descanso» (casilla, encendida por omisión), para poder jugar sin ella.
   - La ventana del aldeano muestra su energía y «descansando».
   - *Criterios:* prueba: un aldeano trabaja unos 8 minutos, descansa 2 en su casa y vuelve a su trabajo; uno sin casa tarda el doble; un pueblo de referencia sigue creciendo (no muere de hambre por el descanso); se guarda y carga a medio descanso; suben las versiones.
72. **Amenazas de noche.**
   - Los asaltos llegan con el doble de probabilidad de noche que de día.
   - Lobos y osos notan a los aldeanos desde un 50 % más lejos de noche y se alejan 15 m más de su guarida; no van tras quien está en una zona iluminada (si ya lo perseguían, siguen).
   - Con niebla de guerra, de noche se ve a menos distancia (la mitad), salvo lo que está en zonas iluminadas y las razas con visión nocturna.
   - Torres, soldados y milicia hacen el 75 % del daño a lo que está a oscuras (fuera de la luz); la milicia con visión nocturna y los asaltantes, no.
   - *Criterios:* pruebas de cada regla con el ciclo encendido y sin efecto con el ciclo apagado; suben las versiones.
73. **Fundar el pueblo: la simulación** (pedido del 2026-10-03; con las fases 74 a 78 permite abrir a otros jugadores una partida que empezó de uno solo).
   - La partida ya no nace con pueblos. Cada asiento empieza **sin pueblo**: no tiene edificios, aldeanos ni recursos, y la única orden que se le acepta es fundar.
   - Orden nueva «fundar pueblo» (celda y giro). Vale en cualquier parte del mapa con las reglas normales de construcción (no en agua, no sobre otro edificio, desnivel de hasta 4 m; los árboles y rocas que haya debajo se quitan, como bajo cualquier edificio). No hay zonas reservadas ni distancia mínima a otros pueblos. La regla de «nadie puede llegar» (fase 65) no se aplica al centro: todavía no hay aldeanos. Se funda una sola vez; el sitio no se puede cambiar.
   - Al fundar aparecen, junto al sitio y en celdas caminables: los aldeanos iniciales de hoy, un **carro** y el centro del pueblo **como obra**.
   - El carro es un edificio provisional de 2 × 2 que no se puede construir ni demoler y que se coloca solo, en el sitio libre más cercano a la puerta del centro (si no hay ninguno a 16 m, no se puede fundar ahí). Guarda todo lo que hoy empieza dentro del centro (materiales, comida, herramientas y oro, según la opción de recursos de la partida) más los materiales que cuesta el centro. Sirve de almacén y de lugar de descanso (fase 71) mientras no haya centro. Al terminarse el centro, lo que queda pasa adentro y el carro desaparece.
   - Con el centro en obra ya se pueden colocar los edificios de nivel 1. Lo que el centro desbloquea por nivel espera a que esté terminado.
   - Los sitios de inicio que calcula el generador dejan de ser pueblos y pasan a ser **sitios sugeridos**, guardados en el mapa. El generador usa «sitios para pueblos» (1 a 12) donde hoy usa la cantidad de jugadores (una isla por pueblo, recursos cercanos), así el mapa puede tener lugar para quien llegue después.
   - Asaltos, mercaderes, inmigrantes, enfermedades y condiciones de derrota no cuentan para un asiento sin pueblo. El fondo de los menús (0 jugadores) no cambia.
   - Las pruebas de fases anteriores y el pueblo de referencia arrancan con los pueblos ya en pie en los sitios sugeridos y el centro terminado (opción `start_towns` de la simulación, que el juego no usa), para no cambiar lo que miden.
   - *Criterios:* una partida nueva no tiene ningún edificio ni aldeano; fundar en un sitio válido crea aldeanos, carro y obra, y los aldeanos terminan el centro con los materiales del carro; al terminar, el carro desaparece y sus recursos y oro están en el centro (prueba que cuenta totales antes y después); fundar en agua, fuera del mapa, sobre otro edificio o dos veces se rechaza; una casa se puede colocar antes de terminar el centro; dos pueblos fundados pegados uno al otro son válidos; guardar y cargar con un asiento sin pueblo y con el centro a medias; suben las versiones de reglas, de red y de partidas guardadas.
74. **Fundar el pueblo: elegir el sitio en pantalla.**
   - Al empezar una partida, cada jugador ve el mapa y un aviso «Elige dónde fundar tu pueblo», con la silueta del centro bajo el cursor (verde o roja con el motivo, como al construir), giro con las teclas de siempre y confirmación «Fundar aquí» / «Cancelar» antes de mandar la orden.
   - Lo que se ve al elegir sigue la opción de niebla de la partida: sin niebla, todo el mapa; con niebla, el mapa sin explorar. Los sitios sugeridos se marcan siempre, en el mapa y en el minimapa, también bajo la niebla; se pueden ignorar. Una tecla lleva la cámara al siguiente sitio sugerido. Un sitio sugerido con un centro ajeno a menos de 60 m deja de marcarse.
   - Una partida nueva empieza **en pausa** hasta que todos los asientos fundaron; se muestra quién falta. Luego el tiempo corre desde el tick 0 (amanecer del primer día). Quien llega a una partida ya empezada (fase 77) elige con el tiempo corriendo.
   - En la sala, modo «un pueblo por jugador»: cada jugador funda el suyo. Modo «pueblo común»: funda el anfitrión, y los demás ven «Esperando a que … funde el pueblo» con la cámara libre.
   - El formulario de partida nueva gana «Sitios para pueblos» (1 a 12; por omisión, la cantidad de jugadores), recordado en `newGame`.
   - Mientras no hay pueblo, la barra de construcción y la de recursos no se muestran. El carro tiene su ventana (lo que guarda) y su modelo, hecho con el pipeline de Blender a partir de la carreta del mercader.
   - *Criterios:* en un jugador, la partida arranca en pausa sobre el mapa vacío y empieza a correr al confirmar el sitio; con niebla se elige sobre lo no explorado viendo las marcas sugeridas; un sitio inválido muestra su motivo y no deja confirmar; dos instancias en red: el juego no avanza hasta que las dos fundaron, y cada una ve el aviso de quién falta; en pueblo común solo el anfitrión coloca; el formulario recuerda los sitios para pueblos; español e inglés.
75. **Pueblos y asientos que cambian durante la partida.**
   - La simulación guarda, por asiento, a qué pueblo pertenece (o ninguno), y por pueblo, quién lo fundó. Reemplaza al modo único de partida (`shared_town`): en una misma partida pueden convivir pueblos de varios jugadores y pueblos de uno solo. Los pueblos de distintos jugadores son siempre aliados, como hoy.
   - Orden nueva, que solo el anfitrión puede dar, para **agregar un asiento** sin pueblo a una partida en curso, hasta 12. Nombre y color viajan con el asiento.
   - Orden nueva para **unir un asiento a un pueblo** que ya existe: desde ese tick da órdenes a ese pueblo con los mismos permisos y ve lo que el pueblo ya exploró.
   - Los dos modos de la sala se expresan con esto: «pueblo común» pone todos los asientos en el pueblo que funde el anfitrión; «un pueblo por jugador» deja cada asiento con el suyo.
   - Índices, cachés por pueblo, visión, comercio entre jugadores y el panel final dejan de suponer que pueblo y asiento son lo mismo.
   - *Criterios:* pruebas: una partida de un asiento recibe un segundo que funda su pueblo y los dos pueblos avanzan 10 minutos de juego; un tercer asiento se une al primer pueblo y sus órdenes se aceptan ahí y se rechazan en el otro; el asiento número 13 se rechaza; agregar un asiento por orden de quien no es anfitrión se rechaza; todo se guarda y se carga igual; las pruebas de red de doce jugadores en pueblo común y de cuatro pueblos separados siguen pasando; suben las versiones.
76. **Abrir la partida a otros jugadores.**
   - En el menú de pausa de una partida de un jugador: «Abrir a multijugador». El jugador elige qué se permite a quien llegue: **unirse a un pueblo**, **fundar un pueblo propio**, o las dos cosas. Desde ese momento es el anfitrión: escucha en el puerto de siempre y se anuncia en la red local como partida empezada.
   - Al abrir, si la velocidad pasa de ×5 baja a ×5, y las de ×6 a ×9 dejan de ofrecerse mientras la partida esté abierta o tenga más de un asiento. Pausa y votos de velocidad funcionan como en cualquier partida en red.
   - Las herramientas de desarrollo siguen aceptándose en una partida abierta (cómo ocultarlas en la versión final queda pendiente, sección 14).
   - Quien se conecta pasa el saludo de siempre (versión, compilación, mods), recibe la instantánea y entra como asiento nuevo sin pueblo. Quien vuelve con el mismo nombre recupera su asiento.
   - «Cerrar a jugadores nuevos», en el mismo menú: el anfitrión deja de aceptar asientos nuevos sin terminar la partida. Los que ya tienen asiento pueden seguir reconectándose. Se puede volver a abrir y cambiar lo permitido.
   - Si la partida está abierta y qué permite se guarda con la partida.
   - *Criterios:* dos instancias con `--loopback`: la 1 juega sola 5 minutos a ×8, abre la partida (la velocidad queda en ×5) y la 2 entra, recibe el estado y ve el mismo tick y los mismos hashes; la 2 sale y vuelve con su nombre y recupera el asiento; con la partida cerrada, un nombre nuevo se rechaza con su mensaje y uno conocido entra; versión o mods distintos se rechazan como hoy; pruebas de la suite `net` para abrir, entrar, cerrar y reconectar; español e inglés.
77. **Llegar a una partida: fundar o pedir unirse.**
   - Quien entra sin pueblo ve una ventana con lo que el anfitrión permitió: «Fundar mi pueblo» y la lista de pueblos con el nombre de su fundador y un botón «Pedir unirme».
   - Fundar: la misma elección de sitio de la fase 74, con el tiempo corriendo y los demás jugando.
   - Pedir unirse: la solicitud llega **solo al fundador** del pueblo, como aviso con «Aceptar» y «Rechazar». No caduca: si el fundador no está conectado o no responde, queda esperando y él la ve al volver. Si el fundador no vuelve nunca, nadie más puede aceptar solicitudes para ese pueblo: ni otro miembro ni el anfitrión de la partida. Quien pidió puede cancelarla y, si está permitido, fundar su propio pueblo o pedir otro. Una solicitud a la vez por asiento.
   - Las solicitudes y sus respuestas son órdenes de la simulación (viajan por los turnos y se guardan con la partida); solo el fundador puede responder la de su pueblo.
   - Mientras espera, el jugador tiene la cámara libre y ve lo que la niebla le deja ver a un asiento sin pueblo.
   - Todos reciben aviso de quién llegó, quién fundó un pueblo y quién se unió a cuál.
   - *Criterios:* dos instancias: la 2 pide unirse, la 1 acepta y las dos dan órdenes al mismo pueblo; rechazada, la 2 puede fundar el suyo y elige el sitio mientras la 1 sigue jugando; con solo «unirse» permitido no se ofrece fundar, y al revés; pruebas: una respuesta de quien no es el fundador se rechaza, una solicitud sobrevive a guardar y cargar y a la desconexión del fundador, y cancelar la retira; tres instancias: un tercer jugador en el pueblo no puede aceptar por el fundador; español e inglés.
78. **Cargar una partida guardada como anfitrión** (reemplaza lo pendiente de D-672).
   - En la lista de partidas guardadas: «Cargar» (como hoy) y «Cargar como anfitrión». La segunda abre la sala con los asientos de la partida: nombre, color y pueblo de cada uno.
   - Cada jugador que entra con el nombre de un asiento lo recupera; recibe la partida como instantánea. El anfitrión empieza cuando quiere: los asientos sin jugador dejan su pueblo trabajando solo y pueden ocuparse después por nombre.
   - Una partida guardada que estaba abierta sigue abierta al cargarla así, con lo mismo permitido; el anfitrión puede cambiarlo en la sala. Una guardada de un jugador se puede cargar como anfitrión: equivale a cargarla y abrirla.
   - El asiento del anfitrión es el suyo de la partida guardada (por nombre); si no está, el del fundador del primer pueblo.
   - *Criterios:* dos instancias juegan, guardan, salen; la 1 carga como anfitrión, la 2 entra con su nombre y siguen en el mismo tick con los mismos hashes; sin la 2, la partida empieza igual y su pueblo trabaja solo, y la 2 entra más tarde; una guardada de otra versión o con otros mods se rechaza como hoy; una solicitud de unión pendiente sigue ahí tras cargar; español e inglés.
79. **Modo espectador** (pedido del 2026-10-03).
   - Tercera casilla del anfitrión, «Permitir espectadores», junto a «unirse» y «fundar»: en la sala de una partida nueva, al abrir una partida (fase 76) y al cargar como anfitrión (fase 78). Se guarda con la partida.
   - Un espectador es una conexión, no un asiento: no está en el estado de la simulación ni en sus hashes, no ocupa ninguno de los 12 asientos y no se guarda. Hasta 8 espectadores por partida. No puede dar ninguna orden (tampoco las de las herramientas de desarrollo), no pausa ni vota la velocidad, y el juego no lo espera: si se atrasa se pone al día solo y, si queda muy atrás, el anfitrión le manda la instantánea.
   - Entrar a mirar: en la sala, cada jugador puede marcarse como espectador en lugar de ocupar un asiento; al llegar a una partida empezada, la ventana de la fase 77 ofrece «Mirar» además de fundar y pedir unirse.
   - Vista: por omisión todo el mapa sin niebla, y puede abrir las ventanas de cualquier pueblo, edificio o aldeano (solo lectura). Con una lista de pueblos elige **mirar como** uno de ellos: ve lo que ese pueblo ve (su niebla, sus recursos, sus avisos). Vuelve a «todo» cuando quiere.
   - De espectador a jugador: mientras mira puede fundar su pueblo o pedir unirse a uno, si el anfitrión lo permite y queda asiento; entonces recibe un asiento nuevo (fase 75).
   - De jugador a espectador: «Pasar a espectador» en el menú de pausa. El asiento sigue siendo suyo: su pueblo queda trabajando solo, o con sus compañeros, igual que cuando un jugador se desconecta, y con «Volver a mi pueblo» lo recupera sin pedir permiso. Un fundador que está mirando ve el aviso de las solicitudes de unión, pero para responderlas tiene que volver a su pueblo. El anfitrión también puede pasar a espectador; sigue siendo el anfitrión.
   - Todos ven en la lista de jugadores quién está mirando, y reciben aviso cuando alguien pasa a mirar o vuelve a jugar.
   - *Criterios:* tres instancias: la 3 entra a mirar una partida con niebla, ve los dos pueblos enteros y, al elegir «mirar como» el primero, ve solo lo que ese pueblo exploró; sus intentos de dar órdenes, pausar o votar se rechazan (prueba con mensajes forzados); doce jugadores más ocho espectadores caben, y el noveno espectador se rechaza con su mensaje; un espectador detenido 10 s no frena a los demás y al volver alcanza el tick; los hashes de la partida son los mismos con y sin espectadores; la 3 funda su pueblo desde el modo espectador; la 2 pasa a espectador, su pueblo sigue trabajando y vuelve a él sin pedir permiso; con la casilla apagada no se ofrece «Mirar» y una conexión que lo pide se rechaza; sube la versión de red; español e inglés.
80. **Corrección: los animales brillan de noche** (reportado el 2026-10-03; con las fases 81 a 85 forma la ronda de recursos).
   - De noche los animales se ven con luz propia en lugar de oscurecerse como el terreno, los edificios y los aldeanos. Encontrar la causa (el nombre de sus materiales frente a la regla de brillo de la fase 69, o un camino de dibujo que se salta la oscuridad) y corregirla en su origen, sin excepciones por modelo.
   - Revisar de paso que no les pase lo mismo a los cadáveres, a las piezas de caza y a los animales del fondo de los menús.
   - *Criterios:* una prueba recorre todos los modelos de animales del mod `core` y ninguno de sus materiales cuenta como «brilla de noche»; de noche y lejos de toda luz, un animal se ve tan oscuro como el suelo que pisa, y junto a una antorcha se ilumina como un aldeano (captura de antes y de después); de día no cambia nada.
81. **Avisos de recursos agotados.**
   - Cada edificio de recolección (leñador, recolector, cantero, herbolario, mina de hierro) sabe en la simulación si tiene algo que recoger a su alcance. Tres estados: **con recursos**, **esperando** (solo queda lo que rebrota y hoy está vacío o helado) y **agotado** (no queda nada de lo que no rebrota).
   - Al pasar a **agotado**: una notificación con la posición del edificio («El cantero ya no tiene roca a su alcance»), una sola vez por edificio y por agotamiento; un ícono sobre el edificio mientras dure; y una línea de estado en la ventana del edificio y en la de cada uno de sus trabajadores. **Esperando** solo muestra la línea de estado («esperando que rebrote»), sin notificación ni ícono.
   - El estado se borra solo cuando vuelve a haber recursos a su alcance. Los trabajadores de un edificio agotado quedan sin tarea, como hoy.
   - El cazador y el pescador muestran la línea de estado cuando no tienen presa o el agua está helada, sin notificación (es de temporada).
   - *Criterios:* pruebas: un cantero con dos rocas a su alcance las agota, queda «agotado» y emite el evento una sola vez; un recolector con arbustos vacíos queda «esperando» y no emite nada; con una roca más allá del radio sigue agotado; el estado se guarda y se carga igual; en pantalla se ven la notificación, el ícono y la línea de estado; español e inglés; sube la versión de reglas.
82. **Más roca, bayas y hierbas en los mapas.**
   - El generador pone cerca del doble de rocas sueltas, arbustos de bayas y hierbas en todos los mapas; el mineral de hierro y los árboles no cambian. El porcentaje «Recursos» de la partida nueva sigue escalando todo junto.
   - Los mínimos garantizados alrededor de cada inicio suben en la misma proporción.
   - *Criterios:* prueba: con la misma semilla y «Recursos» al 100 %, el mapa tiene al menos 1,8 veces las rocas, los arbustos y las hierbas de antes, y la misma cantidad de hierro; cada inicio cumple los mínimos nuevos; el mapa colosal al 200 % cabe en el límite de objetos naturales; generar un mapa no tarda más de un 10 % más; suben la versión del generador y la suma de referencia.
83. **Yacimientos de roca.**
   - Objeto natural nuevo, el **yacimiento de roca**: un afloramiento grande, en tres tamaños (800, 2 000 y 5 000 unidades), con un modelo por tamaño hecho con el pipeline de Blender. No se puede caminar ni construir encima. El grande se ve bajo la niebla como punto de referencia.
   - Lo trabaja el **cantero** de siempre cuando queda dentro de su radio, además de las rocas sueltas; no hay edificio nuevo. Varios trabajadores pueden picar el mismo yacimiento a la vez.
   - Al gastarse cambia al modelo del tamaño menor y, agotado, desaparece y deja el suelo libre.
   - Se puede seleccionar: su ventana dice cuánta roca le queda.
   - El generador pone pocos por mapa, de preferencia en laderas, colinas y montañas; su cantidad sigue el porcentaje «Recursos»; y garantiza al menos uno, mediano o grande, a no más de 250 m caminando de cada inicio.
   - *Criterios:* pruebas: un cantero con un yacimiento a su alcance saca roca con sus dos trabajadores a la vez; un yacimiento de 800 entrega 800 unidades y desaparece; al bajar de cada umbral cambia de tamaño; agotado, el cantero avisa (fase 81); cada inicio tiene uno a 250 m o menos por camino; no se puede construir encima; guardar y cargar con uno a medio gastar; en pantalla se distinguen los tres tamaños; suben las versiones del generador y de reglas.
84. **Frutales silvestres.**
   - Las especies de árbol pueden declararse **frutales** en su JSON. Empiezan como frutales el manzano, el cerezo, la palma y el baobab. Todas dan el mismo recurso «fruta» de hoy, aunque lo que den no sea técnicamente fruta; la dieta no cambia.
   - Una cosecha al año: los frutales medianos o mayores cargan fruta al empezar el verano (más cuanto más grande el árbol) y lo que nadie recogió se pierde al terminar el otoño.
   - El **recolector** recoge la fruta de los frutales a su alcance, además de bayas y hierbas; el árbol queda en pie y vuelve a cargar al año siguiente.
   - La ventana del árbol dice cuánta fruta tiene. El modelo no cambia (fruta visible queda como idea para después).
   - Para los avisos de la fase 81, la fruta cuenta como algo que rebrota.
   - *Criterios:* pruebas: un manzano mediano no tiene fruta en primavera, la tiene en verano y la pierde al entrar el invierno; uno pequeño nunca tiene; un recolector la lleva al almacén como «fruta» y el árbol sigue ahí; un roble no da fruta; la cosecha vuelve al año siguiente; guardar y cargar con fruta en los árboles; una especie de un mod marcada como frutal se comporta igual; español e inglés; sube la versión de reglas.
85. **El leñador y los frutales.**
   - La ventana del leñador gana el interruptor **«Talar frutales»**, apagado por omisión: sus trabajadores no tocan los frutales. Cada leñador tiene el suyo; cambiarlo es una orden de la simulación y se guarda con la partida.
   - Un frutal talado, por el leñador o al despejar una obra, entrega su madera y además la fruta que tenía en ese momento.
   - Si a un leñador con el interruptor apagado solo le quedan frutales a su alcance, el aviso de la fase 81 lo dice («solo quedan frutales»).
   - *Criterios:* pruebas: con el interruptor apagado, un leñador rodeado solo de manzanos no tala ninguno y avisa; encendido, los tala; un manzano con fruta talado en verano entrega madera y fruta, y en invierno solo madera; despejar una obra sobre un frutal con fruta entrega las dos cosas; el interruptor se guarda, se carga y viaja en red (dos instancias con los mismos hashes); español e inglés; suben las versiones de reglas y de red.
86. **Los árboles crecen.**
   - Todos los árboles del mapa suben de tamaño con los años hasta el mayor que admite su especie: de pequeño a mediano en un año, a grande en otro, y a enorme dos años después. Los gigantes (fase 55) no cambian.
   - Tamaño nuevo por debajo del pequeño, el **brote**: no da madera, no se tala, no estorba el paso y se puede construir encima. Pasa a pequeño al año. El generador no pone brotes; solo aparecen al replantar (fase 87).
   - Cada árbol cumple años en un día propio, fijado por su posición, para que el bosque no cambie todo el mismo día y el trabajo se reparta entre los días del año.
   - Al crecer, el árbol da la madera de su tamaño nuevo y, si es frutal, empieza a dar fruta al llegar a mediano (fase 84). La vista cambia su tamaño sin rehacer el bosque.
   - *Criterios:* pruebas: un roble pequeño es mediano al año, grande a los dos y enorme a los cuatro, y entrega la madera de cada tamaño; una especie que no admite «enorme» se queda en grande; un gigante no cambia; en un año de juego no crecen todos el mismo día; guardar y cargar a mitad de año da la misma partida; dos instancias en red con los mismos hashes tras dos años; en el mapa colosal el día más cargado de crecimiento no añade más de 2 ms al tick, y los FPS no bajan (medido con `--reporte`); sube la versión de reglas.
87. **El leñador: replantar y talar solo maduros.**
   - Dos interruptores más en la ventana del leñador, junto a «Talar frutales», los dos apagados por omisión (el leñador se comporta como hoy): **«Replantar lo talado»** y **«Solo árboles maduros»**. Cada leñador tiene los suyos; cambiarlos es una orden de la simulación y se guarda con la partida.
   - Replantar: después de talar, el trabajador planta en el mismo sitio un brote de la misma especie (un frutal se replanta como frutal). Le toma un rato de trabajo y no cuesta materiales. Lo que se tala para despejar una obra no se replanta.
   - Solo maduros: tala únicamente árboles grandes y enormes, o del tamaño mayor de su especie si es menor que grande.
   - Avisos (fase 81): si a su alcance solo quedan árboles jóvenes, el leñador queda «esperando que crezcan», con línea de estado y sin notificación; si no queda ningún árbol ni brote, queda agotado.
   - *Criterios:* pruebas: con «Replantar» encendido, cada árbol talado deja un brote de su especie en el mismo sitio, y apagado no deja nada; con «Solo maduros», un leñador rodeado de árboles pequeños y medianos no tala ninguno y muestra «esperando que crezcan», y tala el primero que llega a grande; un leñador con los dos encendidos y 60 árboles grandes a su alcance sigue produciendo madera después de 10 años de juego; despejar una obra no deja brotes; los interruptores se guardan, se cargan y viajan en red; español e inglés; suben las versiones de reglas y de red.
88. **Pulido y entrega.** `/analyze` limpio, README con la lista de verificación completa, guías revisadas, `DECISIONES.md` revisado, ZIP de entrega y compilación en tu Linux.

## 14. Pendientes para después (no implementar ahora)

- Reemplazar los animales y los aldeanos del juego por los modelos low poly nuevos (`art/blender/zoo`, `people`); entonces se borran los viejos y sus scripts, que quedan archivados en `J:\Back\salvaciudad-alfa-1.zip` (pedido del usuario, 2026-10-02).

- Ocultar las herramientas de desarrollo en la versión final, también en partidas en red (el usuario decidirá cómo; 2026-10-03).

- Compilación y pruebas en macOS.
- CI en GitHub para Windows, Linux y macOS.
- Steam: publicación gratuita, Workshop y conexión sin abrir puertos.
- Música.
- Estaciones extremas o de fantasía adicionales.
- Servidor dedicado.

## 15. Preguntas resueltas

Las preguntas abiertas de la versión 1 se respondieron el 2026-09-26 y sus respuestas ya están integradas en el documento. El detalle está en `docs/DECISIONES.md` (D-009 a D-013).
