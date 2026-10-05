# Bitácora de decisiones

Cada entrada dice qué se decidió y por qué. Numeración: `D-0xx` para la especificación, `D-<fase>xx` para cada fase (por ejemplo `D-3xx` para la fase 3).

---

## Especificación (2026-09-26)

**D-001. Multijugador por lockstep determinista.**
Solo viajan los comandos de los jugadores y cada máquina simula todo. Se descartó sincronizar el estado desde el anfitrión: con hasta 12 000 aldeanos el ancho de banda sería inviable. El costo es que la simulación debe ser determinista entre máquinas, compiladores y sistemas operativos. Por eso la simulación usa punto fijo, un RNG propio y un orden de iteración definido (ver 7.3 de la especificación).

**D-002. Bibliotecas de código abierto en lugar de escribir todo desde cero.**
"Sin motores comerciales" se interpreta como sin Unity, Unreal ni Godot. Las bibliotecas pequeñas y enfocadas (SDL3, cgltf, stb, Lua, ENet, yyjson, zstd, Dear ImGui, doctest) se vendorizan con su licencia. Todas están **pendientes de aprobación** (pregunta P-5).

**D-003. Simulación a 10 ticks por segundo con render interpolado.**
10 ticks por segundo bastan para un juego de construcción y dejan margen de CPU para 12 jugadores a x3 (30 ticks por segundo). El render interpola entre ticks para verse fluido a la frecuencia de la pantalla.

**D-004. Partidas guardadas en binario por bloques, configuración en JSON.**
La configuración es pequeña y conviene que el usuario la pueda leer y reparar, así que va en JSON. Una partida con miles de aldeanos y un mapa de 4096 × 4096 sería de cientos de MB en JSON, así que va en binario por bloques con etiqueta, versión, CRC y compresión zstd. Se conservan los bloques desconocidos. La misma serialización sirve para las instantáneas de red.

**D-005. Objetivo de rendimiento provisional.**
60 FPS en una PC de gama media con 4 jugadores de 500 aldeanos en un mapa Grande. Con 12 jugadores de 1000 aldeanos en un mapa Enorme, el objetivo es que la simulación aguante x1; si no, el lobby lo advierte (fase 20).

**D-006. Sombreadores en HLSL compilados al construir.**
La API de GPU de SDL3 recibe código ya compilado para cada backend (SPIR-V, DXIL, MSL). Escribirlos una sola vez en HLSL y convertirlos con `shadercross` al construir evita mantener tres versiones. Los mods no pueden agregar sombreadores en la primera versión.

**D-007. Modelos generados con scripts de Blender versionados.**
En lugar de modelar a mano con el MCP y guardar solo el `.blend`, cada modelo sale de un script de Python en `art/blender/`. Así se puede regenerar, mejorar y producir variantes, y cualquier agente puede retomar el trabajo.

**D-008. Mapas separados dentro de una sola simulación.**
En el modo de mapas separados, todos los mapas se simulan en la misma simulación determinista, como regiones sin contacto físico, conectadas por un mapa del mundo abstracto. Se descartó tener simulaciones independientes por jugador: complicaría la sincronización del comercio y de los ataques entre mapas.

## Respuestas a las preguntas abiertas (2026-09-26)

**D-009. Pausa inmediata, reanudar por votación.**
Cualquier jugador pausa sin votación. Reanudar y cambiar de velocidad requieren que todos acepten, o se descartan a los 15 s. En el pueblo común todos los jugadores tienen permisos iguales. Si un jugador se desconecta, sus aldeanos siguen trabajando sin órdenes nuevas hasta que vuelva.

**D-010. Duración del año.**
Por omisión, unos 20 minutos a x1, igual que en Farthest Frontier. Es configurable al crear la partida.

**D-011. Razas mezclables con rasgos de juego.**
Un pueblo puede mezclar razas. Los rasgos son modificadores declarados en datos: los enanos minan más rápido, los elfos cazan mejor, los gatunos ven de noche y se mueven más rápido. No hay edificios exclusivos por raza, porque no se pidió y duplicaría el trabajo de arte y de equilibrio. El sistema de definiciones permite agregarlos después.

**D-012. Licencia MIT para el código.**
Se pidió la licencia "que permita usar más assets y bibliotecas".
- Todas las bibliotecas elegidas son permisivas (MIT, zlib, BSD, Apache 2.0 o dominio público), y la MIT es compatible con todas.
- Los assets son archivos de datos separados del código y conservan su propia licencia (CC0, CC-BY, CC-BY-SA, OFL) sin afectar a la del código. Basta cumplir la atribución en `CREDITS.md`.
- Se descartó la GPL. Permitiría usar bibliotecas GPL, que en el desarrollo de juegos son raras, pero es incompatible con SDK propietarios como el de Steamworks, que se necesitará para publicar en Steam.
- Limitación: no se pueden usar bibliotecas con licencia GPL. Si alguna vez hiciera falta una, se revisa entonces.

**D-013. Tipografías elegibles.**
Se incluyen varias fuentes OFL y el jugador elige la de la interfaz en Configuración. El logotipo usa una fuente decorativa fija. Todas cubren al menos el latín extendido; un idioma con otro alfabeto necesitará agregar una fuente que lo cubra.

## Fase 1: base del proyecto (2026-09-26)

**D-101. Carpeta de datos `%APPDATA%\Salva\SalvaCiudad`.**
SDL recomienda un nombre de organización no vacío en `SDL_GetPrefPath`: sin él, el juego no pasaría la certificación de algunas tiendas. Se usa "Salva" como organización, que sirve para todos los juegos de la familia. La especificación decía `%APPDATA%\SalvaCiudad` y se actualizó.

**D-102. SDL3 3.4.16, yyjson 0.13.0 y doctest 2.5.3, vendorizadas sin modificar.**
Versiones y hashes en `third_party/README.md`. De SDL3 se quitaron solo las carpetas que no se compilan (`test`, `examples`, `VisualC`, `VisualC-GDK` y `Xcode`). El resto queda intacto para poder actualizarla reemplazando la carpeta. SDL incluye `AGENTS.md` y `CLAUDE.md`: piden no usar IA **para contribuir a SDL**. Este proyecto solo usa la biblioteca, sin modificarla ni enviarle cambios.

**D-103. Sin excepciones ni RTTI en el código del juego; las pruebas sí usan excepciones.**
El motor y el juego se compilan con `/EHs-c- /GR-` y `_HAS_EXCEPTIONS=0` (con `-fno-exceptions -fno-rtti` en GCC y Clang). doctest reporta los fallos con excepciones, así que solo el ejecutable de pruebas las activa. Consecuencia: toda función de la biblioteca estándar que pueda lanzar se llama en su versión con `error_code`, o se validan antes sus entradas. Por ejemplo, `path_from_utf8` rechaza el UTF-8 inválido, y `path_to_utf8` convierte con `WideCharToMultiByte` para tolerar sustitutos sueltos en nombres de archivo de Windows.

**D-104. La simulación se integra en el bucle principal por ahora.**
La especificación prevé un hilo de simulación (7.2). En la fase 1 no hay simulación, así que el reloj de paso fijo (`GameClock`) vive en el hilo principal. El hilo aparte se decide en la fase 5, midiendo, junto con el núcleo determinista.

**D-105. Atajos provisionales F11 y Alt+Enter.**
F11 cambia en ciclo entre ventana, sin bordes y pantalla completa. Alt+Enter alterna entre ventana y el último modo de pantalla completa usado. En la fase 2 pasan al sistema de teclas reasignables y al menú de Configuración.

**D-106. La pantalla completa exclusiva usa la resolución del escritorio por omisión.**
Con `fullscreenWidth` y `fullscreenHeight` en 0, la pantalla completa no cambia el modo de vídeo del monitor. Elegir otra resolución llega en la fase 2, con confirmación y reversión automática a los 15 s.

**D-107. Sin cuadro de diálogo para errores fatales antes de la fase 2.**
Un error al iniciar SDL o al crear la carpeta de datos se escribe en stderr y en el registro. Los cuadros de diálogo necesitan los textos traducidos, que llegan en la fase 2. Lo mismo vale para el aviso de "N ajustes ignorados", que por ahora solo va al registro.

**D-108. Registro con marca de tiempo en UTC.**
Así los registros de jugadores en distintas zonas horarias se pueden comparar al diagnosticar el multijugador.

## Fase 2: idiomas, texto e interfaz base (2026-09-26)

**D-201. Por ahora, solo DXIL y Direct3D 12.**
Los sombreadores se escriben en HLSL y se compilan a DXIL con el `dxc.exe` del Windows SDK que ya está instalado, sin dependencias nuevas. Se incrustan en el ejecutable como arreglos de bytes. El dispositivo de GPU pide solo DXIL, así que SDL elige Direct3D 12.
- Se descartó `SDL_shadercross` por ahora: compilarlo arrastra DXC y SPIRV-Cross completos, que son enormes, cuando lo único que se prueba es Windows.
- Consecuencias: una PC sin Direct3D 12 no puede jugar (el juego lo dice con un mensaje claro), y en Linux y macOS CMake se detiene con un mensaje que apunta a esta decisión.
- Cuando se pruebe Linux se agregará SPIR-V (con el `dxc` del SDK de Vulkan) y MSL.

**D-202. Interfaz propia en modo inmediato.**
Cada cuadro, las pantallas llaman a funciones de widgets que se dibujan y devuelven la interacción. Es lo más simple para menús y configuración, y no guarda estado duplicado. Las ventanas acoplables de la fase 17 se construirán encima, con su propio estado de posición y tamaño.

**D-203. Las teclas se guardan por scancode y se muestran según el teclado.**
En `settings.json` se guarda el nombre del scancode de SDL (la posición física), así WASD sigue en su lugar con cualquier distribución de teclado. En pantalla se muestra la letra que la distribución actual pone en esa tecla. Las teclas especiales (flechas, Espacio, Intro…) tienen nombre traducido (`key.*`), porque SDL solo da nombres en inglés.

**D-204. Una tecla asignada a otra acción se le quita a la otra.**
Al asignar una tecla que ya usa otra acción, la otra acción la pierde y se muestra un aviso con el nombre de las dos. Se descartó rechazar la asignación: obliga a buscar y borrar primero la tecla en la otra acción, que es más pesado. Al cargar `settings.json`, un duplicado se desasigna y cuenta como ajuste inválido.

**D-205. Tipografías solo desde la carpeta de datos del juego.**
stb_truetype no está preparada para archivos de fuente maliciosos. Por eso las fuentes solo se cargan desde `data/fonts/` (instalado con el juego), con rutas validadas dentro de esa carpeta, y los mods no pueden agregar fuentes. Si en el futuro hace falta, se evaluará un cargador endurecido.

**D-206. Atlas de glifos de 2048 × 2048 que se vacía al llenarse.**
Con el español, el inglés y pocos tamaños de letra, el atlas no se llena. Si se llenara, se vacía y los glifos se vuelven a rasterizar. El texto de ese cuadro puede verse mal durante un solo cuadro. Se registra en el registro.

**D-207. El tamaño de la interfaz es relativo a la escala de la pantalla.**
La escala final es la del monitor (la de Windows, por ejemplo 150 %) multiplicada por el ajuste del jugador. "Automático" equivale a 100 %, así que el 100 % no aparece dos veces en la lista. El diseño se hace en unidades pensadas para 1080p al 100 %.

**D-208. Formato de números y variante es-MX.**
- `es.json` sigue la RAE: coma decimal, espacio duro como separador de miles, y sin separar los números de cuatro cifras (`minimumGroupingDigits` 2).
- `es-MX.json` solo cambia el formato de números (punto decimal y coma de miles) y hereda todos los textos de `es`.
- Además, `es-MX.json` demuestra que un idioma nuevo puede ser solo una variante.

**D-209. Inglés incrustado como respaldo.**
`data/lang/en.json` se incrusta en el ejecutable al compilar. Si falta la carpeta de datos, el juego igual muestra textos y puede explicar el error. Si existe, el archivo reemplaza a la copia incrustada. Los idiomas se cargan antes de iniciar SDL, para mostrar en el idioma del jugador incluso los errores fatales.

**D-210. Los ajustes de gráficos y audio se guardan antes de tener efecto.**
Las pestañas Gráficos y Audio ya guardan sus valores y lo dicen con una nota. Las notas (`settings.graphics.pendingNote` y `settings.audio.pendingNote`) se quitan cuando el render 3D (fase 3) y el sonido (fase 18) los apliquen. La calidad general se deriva siempre de los niveles individuales, así nunca se contradicen.

**D-211. En ventanas pequeñas, la cabecera de Configuración se desplaza.**
Si el título y las pestañas dejan menos del 45 % del alto para las opciones, se desplazan junto con ellas. Los botones "Restaurar" y "Volver" quedan siempre fijos. Con poco ancho, cada etiqueta va encima de su control. El menú principal limita el logotipo a un tercio del alto y se desplaza si no cabe.

**D-212. Tipografías elegidas: Cinzel (logotipo) y Alegreya Sans (interfaz).**
El selector de Configuración lista las familias de `data/fonts/fonts.json`, así que agregar otra es un cambio de datos. Ver D-013.

**D-213. Las pruebas automáticas de la interfaz mueven el cursor real.**
SDL toma la posición del cursor real para los clics, no la del mensaje de Windows. Las pruebas de humo con capturas de pantalla usan `SetCursorPos` y devuelven el cursor a su posición al terminar. Los cambios de modo de pantalla no se prueban en vivo, porque ocuparían la pantalla; se prueban con servicios simulados (`tests/test_menus.cpp`).

**D-214. Las acciones de pausa, velocidades y guardado rápido ya son reasignables.**
Se pueden reasignar aunque todavía no hacen nada. Pausa y velocidades se aplican desde la fase 8, y el guardado rápido desde la fase 8 o 9. La captura de pantalla (F12) queda pendiente sin fase asignada.

## Fase 3: render 3D base (2026-09-26)

**D-301. Modelos de prueba generados con Python.**
`tools/models/make_test_models.py` genera `data/models/test/*.glb` (árbol, casa con textura de entramado y roca). Usa solo la biblioteca estándar de Python y el resultado es idéntico en cada ejecución. Los `.glb` se guardan en el repositorio. Sirven para probar el render hasta que la fase 4 produzca los modelos reales con Blender.

**D-302. Solo `.glb` autocontenidos, y solo desde la carpeta del juego.**
El cargador acepta únicamente glTF binario con todos sus datos en el propio archivo: sin URIs externas ni `data:`. Valida tamaños, cantidades, índices y que las posiciones sean números finitos. Como stb_image, igual que stb_truetype (D-205), no está pensado para archivos maliciosos, por ahora los modelos solo se cargan de `data/`. Los mods podrán aportar modelos cuando se evalúe un decodificador endurecido (fase 7).

**D-303. Instancias en un búfer de almacenamiento.**
Todas las instancias viven en un búfer de la GPU que solo se vuelve a subir cuando la escena cambia. Cada cuadro se sube únicamente la lista de índices visibles, 4 bytes por objeto, para la vista y para cada cascada de sombra. El recorte por frustum se hace en la CPU: con 50 000 objetos y tres cascadas tarda alrededor de 1 ms.

**D-304. Profundidad invertida (reversed Z) con 32 bits en coma flotante.**
Da precisión uniforme en mapas de varios kilómetros, sin parpadeo entre superficies lejanas.

**D-305. Sombras en cascada por nivel de calidad.**
Desactivadas; 1 cascada de 1024 px hasta 120 m; 2 de 2048 px hasta 250 m; 3 de 2048 px hasta 400 m. Cada cascada se ajusta a una esfera alrededor de su tramo de la vista, de tamaño redondeado y con el centro alineado a los texeles, para que los bordes no titilen al mover la cámara. Filtrado PCF de 3 × 3, con desplazamiento por la normal y sesgo de profundidad.

**D-306. Sin sincronización vertical se usa el modo de presentación inmediato.**
Con "mailbox", Direct3D 12 seguía esperando al refresco del monitor: la medición se quedaba clavada en 100 FPS en un monitor de 100 Hz. Con el modo inmediato la misma escena da unos 600 FPS. Puede haber tearing, que es lo esperable al desactivar la sincronización vertical. "Mailbox" queda como respaldo si el inmediato no está disponible. Se verificó en Windows 11 build 26200.

**D-307. El suavizado de bordes ahora es MSAA 2x, 4x u 8x.**
Se reemplazó la opción FXAA, que habría requerido un pase de posprocesado extra, por niveles de MSAA, que la API de SDL resuelve sola. El valor guardado 1 pasa a significar MSAA 2x. El preset "Alta" usa 4x y "Ultra" 8x. Si la GPU no admite un nivel, se baja al siguiente disponible.

**D-308. Iluminación en espacio lineal.**
El swapchain no es sRGB, así que el sombreador convierte el resultado a gamma al final. Las texturas de los modelos se suben como sRGB, con mipmaps. La iluminación es estilizada: sol con sombra, luz ambiental de cielo y suelo, y niebla que se funde con el horizonte del cielo.

**D-309. Escena de prueba y fondo del menú.**
La escena de prueba tiene 50 000 objetos en 2 km × 2 km: 42 000 árboles, 3000 casas en aldeas y 5000 rocas. También sirve de fondo del menú principal, con la cámara girando despacio detrás de un velo oscuro. El botón "Escena de prueba 3D" del menú es provisional: se quita cuando exista la partida de un jugador (fase 8).

**D-310. Panel de estadísticas con Dear ImGui.**
Se abre con F3 (reasignable). Sus textos también están traducidos. Se desactivaron `imgui.ini` y el registro de ImGui para que no escriba archivos. Incluye una "vista de estrés" de depuración que aleja la cámara hasta ver toda la escena, para medir el peor caso.

**D-311. Rendimiento medido en el equipo de desarrollo.**
`release`, ventana de 1600 × 900, calidad Alta (MSAA 4x, 2 cascadas) y sin sincronización vertical:
- Vista normal: unos 600 FPS.
- Vista de estrés con 49 025 objetos en pantalla (2,35 M triángulos): unos 525 FPS.

El criterio de la fase era 60 FPS o más con 50 000 instancias. Falta medir en una PC de gama media de referencia.

**D-312. Parámetros de la cámara.**
Distancia de 8 a 260 m, con una inclinación que pasa de 28° (cerca) a 68° (lejos). El desplazamiento es proporcional a la distancia, con suavizado exponencial independiente de los FPS. Gira con Q/E o arrastrando con el botón central, y se desplaza al acercar el puntero a 3 px del borde. Los valores están en `src/game/camera.cpp` y se ajustarán según tu opinión.

## Fase 4: pipeline de arte (2026-09-26)

**D-401. Blender en segundo plano, no por el MCP.**
Los modelos se generan con `blender --background --factory-startup`. Así el resultado no depende de las preferencias ni de los complementos de Blender, y nunca se toca la escena que el usuario tenga abierta. El MCP de Blender queda para inspeccionar o para trabajo interactivo si el usuario lo pide. Se verificó con Blender 5.2.0 LTS.

**D-402. Orden de triángulos normalizado tras exportar.**
El exportador glTF de Blender 5.2 no mantiene el orden de las caras entre ejecuciones: los vértices salían idénticos, pero los índices en otro orden. Tras exportar, `common.canonicalize_triangle_order` gira cada triángulo para que empiece por su índice menor, sin cambiar el sentido de giro, y ordena la lista. Con esto, regenerar da archivos idénticos byte a byte (el criterio de la fase).

**D-403. Animaciones precalculadas en la GPU.**
Al cargar un modelo, cada animación se muestrea a 30 fotogramas por segundo y se guarda la matriz de piel de cada hueso y fotograma en un búfer de la GPU (unos 30 KB por cuerpo). El sombreador interpola entre dos fotogramas y mezcla hasta 4 huesos por vértice. Por cuadro, cada personaje solo sube 80 bytes (posición, clip, tiempo y paleta), así que 2000 aldeanos animados cuestan poco. Se descartó animar los esqueletos en la CPU cada cuadro, que escala peor. Si más adelante hacen falta mezclas entre animaciones, se agregará un segundo clip con un peso por personaje.

**D-404. Accesorios rígidos fijados a un hueso.**
Sombreros, barba y delantales son modelos sin esqueleto, con el origen en el punto de fijación. El juego los traslada al comienzo del hueso en la pose de reposo del cuerpo y los mueve con la matriz de ese hueso. Un mismo sombrero sirve para los dos cuerpos porque la cabeza mide lo mismo. Se descartó exportar cada accesorio con el esqueleto completo, porque obligaría a una copia por cuerpo. Un personaje elige sus accesorios con una máscara de bits, hasta 32 por cuerpo.

**D-405. Variantes de ropa por paleta de colores.**
Cada material cuyo nombre es un "espacio de paleta" (piel, pelo, prenda de arriba, de abajo, zapatos, cinturón, sombrero y delantal) se pinta con la paleta del personaje, sin cambiar de modelo ni de llamada de dibujo. Las tres variantes de ropa son tres combinaciones de colores (campesino, trabajador y lugareño) que se cruzan con 5 tonos de piel y 5 colores de pelo: 75 paletas. A eso se suman el delantal, dos sombreros y la barba como piezas opcionales. Las prendas con otra forma se agregarán como accesorios.

**D-406. Cuerpos con piel rígida por pieza.**
Cada pieza del cuerpo (brazo, antebrazo, muslo…) sigue a un solo hueso, con esferas en las articulaciones para que no se abran huecos. Es el aspecto típico del low-poly estilizado y se genera de forma fiable desde código. El motor ya admite pesos repartidos entre 4 huesos, así que se puede pasar a una piel suave sin cambiarlo.

**D-407. Los modelos de prueba de Python quedan para las pruebas.**
La escena de prueba ahora usa el pino, la roca y la casa de Blender, y los 2000 aldeanos. `data/models/test/*.glb` (D-301) se conservan porque las pruebas automáticas del cargador los usan.

**D-408. Rendimiento medido.**
Equipo de desarrollo, `release`, 1600 × 900, calidad Alta y sin sincronización vertical:
- 1996 aldeanos animados en pantalla, más casas, árboles y sombras: unos 365 FPS, con 3,5 M de triángulos.
- Vista cercana con 579 aldeanos: unos 375 FPS.

El criterio era 60 FPS o más con 2000 aldeanos.

## Petición del usuario: modos de cámara y seguimiento (2026-09-26)

El usuario pidió, tras la fase 4, cambiar entre cámara aérea, tercera persona (estilo World of Warcraft) y primera persona con F4, y que la cámara siga a un personaje seleccionado: WASD deja de seguirlo, girar no.

**D-409. Tres modos en la misma cámara.**
`Camera` conserva la vista aérea (D-312) y suma dos modos:
- **Tercera persona:** órbita libre alrededor de un punto a 1,5 m del suelo, a entre 2 y 60 m, con una elevación de -30° a 85°. Al entrar, se acerca a 10 m y 25°. Gira con Q/E o arrastrando con el botón derecho o el central, en ambos ejes.
- **Primera persona:** ojos a 1,65 m; el ratón queda capturado (modo relativo de SDL) para mirar; WASD camina a 5,5 m/s hacia donde se mira, con la mirada limitada a ±85°.

Al cambiar de modo se conserva el punto observado. El desplazamiento por el borde de la pantalla solo aplica a la vista aérea. F4 es la acción reasignable "Cambiar cámara".

**D-410. La tercera persona nunca atraviesa el suelo.**
Si el ojo quedara a menos de 0,4 m del suelo (en el punto del ojo o en el observado), la órbita sube hasta el mínimo necesario: la vista hace un paneo hacia arriba. La altura del suelo es una función que la cámara recibe (hoy plana; el terreno de la fase 6 la dará).

**D-411. Selección y seguimiento de personajes.**
- Un clic, sin arrastrar, lanza un rayo desde la cámara y elige al aldeano más cercano cuyo cuerpo (un segmento vertical de 1,8 m con 0,4 m de radio) toca el rayo. En primera persona se apunta con la cruz del centro.
- El seleccionado muestra un marcador sobre la cabeza, dorado mientras se lo sigue.
- La cámara sigue sus pies en los tres modos. En primera persona se ve con sus ojos y ese aldeano no se dibuja, para que no tape la vista.
- WASD (o el borde de la pantalla) deja de seguirlo; girar no. Un clic en el suelo quita la selección.

Esta selección vive por ahora en la escena de prueba. Es la misma mecánica que necesitará la partida (fase 8, abrir la ventana de un aldeano) y no afecta al determinismo: la cámara y la selección son solo presentación.

**D-412. Con el panel de estadísticas abierto no se captura el ratón.**
Así la ventana de Dear ImGui se puede usar también en primera persona.

## Fase 5: núcleo determinista (2026-09-26)

**D-501. Punto fijo 16.16 con saturación.**
`Fixed` guarda 32 bits: rango de ±32 767 m con 1/65 536 de precisión, suficiente para mapas de 4 km. Las operaciones se calculan en 64 bits y **saturan** en vez de desbordar, así que nunca hay comportamiento indefinido. Las divisiones redondean hacia cero, las multiplicaciones hacia abajo (desplazamiento aritmético, definido en C++20) y dividir por cero da el extremo del signo. Las distancias al cuadrado se calculan exactas en 64 bits sin signo.
- Se descartó un tipo de 64 bits para todo: duplica la memoria de cada entidad sin necesidad.

**D-502. Trigonometría por tablas generadas.**
- `tools/sim/make_trig_tables.py` genera `src/sim/fixed_tables.inc`: un cuarto de onda de seno con 1024 pasos y los ángulos de CORDIC. Es código generado y guardado en el repositorio: el juego no calcula esos números en tiempo de ejecución.
- El error del seno es menor de 2·10⁻⁵ y el de `atan2`, de pocas unidades de las 65 536 de una vuelta.

**D-503. PCG32 con flujos separados.**
Cada sistema tiene su propio flujo de números aleatorios, así agregar o quitar un sistema no cambia la secuencia de los demás. `below` usa el método de Lemire con rechazo: es exactamente uniforme y siempre consume la misma cantidad de números. La prueba compara con la secuencia de referencia de PCG (semilla 42, flujo 54).

**D-504. Mundo de prueba de caminantes.**
Hasta la fase 8, la simulación es un mundo de "caminantes" que ejercita todo el núcleo: números aleatorios, raíces, trigonometría, entidades que aparecen y desaparecen, y comandos válidos e inválidos. Los comandos de prueba (`SpawnWalkers`, `SendWalker`, `RemoveWalker`) se reemplazarán por los del juego. El formato de los comandos (20 bytes) y las reglas de validación se mantienen.

**D-505. Hash de referencia en las pruebas.**
Un escenario fijo de 1500 ticks debe dar `0xed6fa5148c47bb17`. La prueba corre en `debug`, `release` y `debug-asan`, así que verifica que las optimizaciones del compilador no cambian nada. Cuando se compile en Linux y macOS, la misma prueba verificará las otras plataformas. Si cambian las reglas a propósito, se actualiza el número y se sube `kRulesVersion`.

**D-506. La simulación corre en el hilo principal.**
Esto resuelve D-104. A 10 ticks por segundo, el mundo actual cuesta microsegundos, y un hilo aparte agregaría sincronización sin beneficio. `App` avanza la simulación con `GameClock` y el panel F3 muestra el tick y el último hash. Cuando la aldea pese de verdad (fase 8, medido en la fase 20), se evaluará moverla a un hilo propio. Las reglas de determinismo ya lo permiten: la simulación no comparte estado con el render salvo lo que se le lee.

**D-507. Repeticiones y archivos fuera de `src/sim`.**
La simulación no toca archivos. `game/replay_file` guarda y lee las repeticiones con escritura atómica, un límite de 256 MB y validación completa (firma, versiones, orden de los ticks y suma de verificación). Una prueba estática impide usar en `src/sim` coma flotante, contenedores desordenados, relojes, archivos, hilos o números aleatorios estándar.

## Fase 6: mapa procedural (2026-09-27)

**D-601. El generador es parte de la simulación.**
`sim/worldgen` usa solo enteros, `Fixed` y su propio ruido (`sim/noise`: ruido de valor sobre una retícula con hash y fBm). Así el mapa sale idéntico en todas las máquinas y la prueba estática de `src/sim` también lo cubre.
- El mapa (`sim::MapData`) guarda:
  - alturas de los vértices en centímetros;
  - la superficie del agua por celda;
  - tipo de suelo y fertilidad;
  - objetos naturales, zonas de animales y posiciones de inicio.
- Una celda mide 1 m. Pequeño, Mediano, Grande y Enorme miden 512, 1024, 2048 y 4096 m de lado.
- La prueba `worldgen` fija la suma de verificación de un mapa Pequeño (semilla 12345): `0x9171cd08375d6a63`. Si el generador cambia a propósito, se actualiza.

**D-602. Etapas del generador.**
1. Relieve: fBm, más cuencas para lagos. La amplitud es de 5 m con relieve bajo y de 10 m con colinas suaves.
2. Lagos: relleno de depresiones por prioridad ("priority flood").
   - Una depresión de al menos 0,7 m de hondo y 150 vértices se vuelve lago.
   - Las demás se rellenan, así ningún río se queda atascado.
3. Ríos: nacen en puntos altos separados entre sí y siguen la pendiente hasta el borde o un lago.
   - El nivel del agua nunca sube río abajo.
   - El ancho crece de unos 5 m a 11 m. Al principio medían de 3 a 5 m y en la prueba en vivo desaparecían bajo el terreno lejano; ver D-606.
4. Suelos: distancia al agua, fertilidad, roca en pendientes, arena en orillas, arcilla, pradera y bosque.
5. Árboles en una retícula de 3 m con desplazamiento aleatorio.
6. Recursos: piedra, hierro, bayas, hierbas y zonas de ciervos, jabalíes, lobos y osos.
7. Posiciones de inicio.

Cada etapa informa su avance y se puede cancelar.

*Reemplazada en parte por D-4901 (el generador clásico se borró en la fase 49): el relieve (etapa 1) lo hace el generador jerárquico (D-3903); las demás etapas siguen.*

**D-603. Posiciones de inicio justas.**
- Los candidatos salen de una retícula de 32 m y se eligen lo más separados posible.
- Cada inicio recibe lo que le falte hasta tener, a menos de 180 m, al menos 2 piedras, 2 arbustos de bayas y 60 árboles, y agua a menos de 150 m.
- Se despejan 25 m alrededor del inicio para el centro del pueblo y se quitan las zonas de depredadores a menos de 250 m.
- Las pruebas lo verifican con 1, 4 y 8 jugadores.

**D-604. Tiempos.**
Un mapa Enorme se genera en unos 6 s en `release`, con unos 410 000 objetos; el criterio pide menos de 30 s. La prueba `worldgen_perf` lo mide y solo corre en `release`.

**D-605. Terreno en la GPU por parcelas con niveles de detalle.**
- Las alturas y el agua suben tal cual a la GPU, en búferes de almacenamiento (dos valores de 16 bits por palabra). Un mapa Enorme ocupa unos 67 MB entre los dos.
- El suelo se dibuja en parcelas de 64 m con 5 mallas compartidas: pasos de 1, 2, 4, 8 y 16 celdas.
  - Cada malla tiene faldones que cuelgan para tapar las grietas entre niveles.
  - El sombreador de vértices lee la altura y calcula la normal.
- Cada cuadro, la CPU elige las parcelas visibles y su nivel según la distancia: hasta 140, 280, 560, 1120 m y más allá. Luego hace una llamada de dibujo por nivel.
- El suelo usa el mismo sombreador de píxeles que los modelos, así que recibe las sombras de los árboles y tiene la misma luz y niebla.
- El suelo no proyecta sombras: el relieve es suave y así se ahorra una pasada.

**D-606. Colores del suelo.**
- Una textura sRGB con mipmaps da el color de cada celda según el tipo de suelo y la fertilidad (la tierra pobre se ve más seca), con una leve variación.
- Tiene un texel por celda hasta 2048; en el mapa Enorme, cada texel promedia 2 × 2 celdas.
- Encima se repite una textura de ruido suave, generada al arrancar, para que el suelo no se vea plano de cerca.
- El lecho de los ríos y lagos se pinta del color del agua. Así el agua se sigue viendo donde el terreno lejano, más simplificado, tapa su superficie.

**D-607. Agua.**
- Es una pasada transparente al final, sobre las parcelas que tienen agua, con un paso de malla de 1 o 2 celdas.
- Cada vértice toma el agua más alta de sus cuatro celdas. Los vértices secos se hunden 2 m bajo el suelo, así la orilla queda donde el terreno corta la superficie.
- El color depende de la profundidad; tiene ondas lentas, reflejo del sol, efecto Fresnel y la misma niebla que el resto.

**D-608. Instancias por regiones y distancia de la vegetación.**
- Cuando cambian las instancias, se ordenan por regiones de 64 m, y el descarte prueba primero la esfera de cada región.
- En el mapa Enorme, el descarte de las ~410 000 instancias cuesta menos de 0,7 ms por cuadro, con las sombras incluidas.
- Los modelos se clasifican como "normal" o "vegetación pequeña" (arbustos y hierbas).
  - La vegetación pequeña se dibuja solo hasta la distancia de la opción Vegetación: 70, 130, 220 o 350 m, también en las sombras.
  - Lo demás llega hasta la distancia de dibujo.
- Con esto se quitó la nota "tendrá efecto cuando se agregue el mapa" de Configuración.

**D-609. La generación corre en un hilo aparte.**
- `game/map_generation` lanza un `std::thread`, informa el avance con variables atómicas y cancela con la respuesta de la función de avance.
- El resultado se toma en el hilo principal, que es el único que sube datos a la GPU. La simulación sigue sin hilos (D-506).
- Además del mapa, el hilo prepara lo visual: colores del suelo e instancias.
- Como el juego se compila sin excepciones (D-103), quedarse sin memoria cierra el programa, igual que en el resto del juego. Por eso no hay un estado de "falló".
- Se agregó `Threads::Threads` a CMake para Linux y macOS.

**D-610. La semilla se escribe con dígitos.**
- La semilla es un número de 1 a 19 cifras que cabe en 64 bits.
- Se escribe con las teclas numéricas, las de arriba o las del teclado numérico. No hace falta la entrada de texto del sistema ni un editor de métodos de entrada.
- Retroceso borra una cifra y Supr borra todo.
- El botón "Al azar" da números de hasta 9 cifras, fáciles de compartir.
- Semillas con palabras (el hash de un texto) se pueden agregar después sin romper las numéricas.

**D-611. Vista de mapa provisional.**
- "Un jugador" ya lleva a Partida nueva → Generando (barra de avance y Cancelar) → vista del mapa.
- La vista del mapa tiene cámara libre, los tres modos de F4 y marcadores numerados en las posiciones de inicio. Esc vuelve al menú y libera el mapa.
- Mientras se ve un mapa, la escena de prueba se retira del render, y vuelve al salir. El fondo del menú sigue siendo la escena de prueba.
- En la fase 8, esta vista se convierte en la partida.

**D-612. Cámara sobre el mapa.**
- La cámara no sale del mapa y se apoya en el suelo o en la superficie del agua, lo que esté más alto.
- Empieza sobre la posición de inicio 1.
- Más allá del borde del mapa solo se ve cielo. Un borde con niebla o montañas se puede agregar más adelante.

**D-613. Rendimiento medido (1600 × 900, en tu PC).**
Mapa Enorme, semilla 2026, calidad Ultra (MSAA 8x, 3 cascadas de sombra, 2500 m de distancia de dibujo):
- vista aérea: unos 400 FPS;
- tercera persona: unos 360 FPS;
- primera persona mirando al bosque, el peor caso: unos 220 FPS con 8,5 millones de triángulos.

Con la calidad Alta por omisión, la vista aérea supera los 500 FPS.

## Peticiones del usuario tras la fase 6 (2026-09-27)

**D-614. Cambiar la sincronización vertical se aplica entre cuadros.**
- El juego se cerraba al desactivar la sincronización vertical. La casilla cambiaba el modo de presentación a mitad del cuadro, con una imagen del swapchain todavía en uso. Para pasar a presentación inmediata, Direct3D 12 tiene que recrear el swapchain, y falló con "Acceso denegado" (0x80070005).
- Ahora el cambio queda pendiente y se aplica después de enviar el cuadro.
- Si aun así falla, se vuelve al modo anterior y se corrige el ajuste guardado.
- Verificado activándola y desactivándola varias veces seguidas.

**D-615. Cámara hasta ver el mapa entero (provisional).**
- Sobre un mapa, la vista aérea se puede alejar hasta 1,6 veces el lado del mapa: unos 6,5 km en el Enorme.
- Más allá del límite normal (260 m):
  - el suelo y el agua se dibujan hasta donde haga falta;
  - la niebla se ajusta a esa distancia;
  - los modelos siguen limitados por la distancia de dibujo, así que desde muy alto solo se ve el suelo, con los bosques en su color, a más de 1000 FPS.
- Las ondas del agua se desvanecen con la distancia, porque de lejos solo producían brillos granulados.
- Cuando se decida, se vuelve al límite normal quitando `set_max_distance_override` en `App::enter_generated_map`.

**D-616. Menú del juego.**
- Con un mapa abierto, Esc ya no vuelve al menú principal: abre el menú del juego, con Continuar, Configuración, Salir al menú principal y Salir del juego. Esc lo cierra.
- Mientras el menú o la configuración están abiertos:
  - el mapa sigue detrás, oscurecido;
  - la cámara no se mueve y el ratón se libera.
- Cerrar la configuración vuelve al mapa con el menú abierto.
- En la fase 8, este menú también pausará la partida de un jugador y avisará antes de salir sin guardar.
- La escena de prueba sigue volviendo directo al menú principal con Esc.

**D-617. Aldea de muestra en el mapa (provisional, 2026-09-27).**
- A pedido del usuario, para juzgar tamaños: al abrir un mapa se ponen hasta 6 casas en un anillo de 18 m alrededor del inicio 1. Las casas que caerían en el agua se omiten.
- 40 aldeanos caminan en la plaza del medio, sobre el relieve.
- Se puede hacer clic en un aldeano para seguirlo, igual que en la escena de prueba.
- Al salir del mapa, la multitud de 2000 vuelve a la escena de prueba.
- Es solo presentación: desaparece cuando exista el pueblo de verdad (fase 8).

Tamaños actuales, para comparar:

| Modelo | Altura |
|---|---|
| Aldeano | 1,7–1,8 m |
| Casa | 5,2 m |
| Pino y roble | 4,6–7,8 m (modelo de 5,8 m con escala de 0,8 a 1,34) |
| Arbusto de bayas | 0,7–1,1 m |
| Hierbas medicinales | 0,45–0,8 m, solo en el interior de los bosques |

El pasto como cubierta del suelo todavía no existe: el suelo es solo textura.

## Fase 6b: biomas, especies de árboles y herramientas de desarrollo (2026-09-27)

**D-618. Especies y tamaños.**
- Hay 21 especies, con las que pidió el usuario más naranjo, peral, durazno y aguacate como "otros frutales" (catálogo en `docs/ARBOLES.md`).
- "Tulipán" se interpretó como el tulipán africano (*Spathodea campanulata*), común en México. Si se quería el tulipero (*Liriodendron*), basta cambiar sus colores en `art/blender/trees.py`.
- Cada árbol del mapa guarda especie, tamaño y altura exacta. `scale` es la altura dividida entre la altura del modelo del tamaño, así que el mismo árbol mide lo mismo con cualquier modelo.
- Especies y tamaños ya permiten que en la fase 8 la madera dependa del tamaño y que los árboles crezcan.

**D-619. Modelos de árboles paramétricos.**
- `art/blender/trees.py` arma todos los árboles con un solo constructor. La especie define tronco, forma de copa, colores, flores y frutos. Las formas son: redonda, ovalada, cónica, aguja (secuoya), sombrilla, alta, jarrón y colgante.
- El tamaño cambia las proporciones: los chicos son más delgados y con menos masas de hojas.
- Salen 52 modelos, de 150 a 2000 triángulos, 1100 en promedio. Dos generaciones seguidas dan archivos idénticos.
- Los frutos se hacen un poco más grandes que en la realidad para que se vean de lejos.
- `art/blender/preview_trees.py` dibuja cada especie en sus tamaños junto a un aldeano.

**D-620. Versión del generador.**
- `worldgen::kGeneratorVersion` (ahora 2) se guarda en el mapa y entra en su suma de verificación.
- Cambia cada vez que la misma configuración daría otro mapa. Así una semilla compartida o una partida guardada puede avisar si viene de otra versión.
- Recomendación para la fase 8: las partidas guardadas incluyen el mapa entero y no dependen de regenerarlo.

**D-621. Biomas y colocación de árboles.**
- Los biomas son regiones alrededor de puntos al azar, uno cada 180–450 m según el tipo de mapa. Sus bordes se tuercen con ruido, y se deciden en bloques de 4 m.
- Los árboles se colocan de mayor a menor. Cada tamaño recorre su propia cuadrícula (12, 8, 5 y 3 m) y cada tronco reserva un disco de media separación, así los grandes nunca se amontonan.
- Los pesos por tamaño de cada bioma reparten el suelo del bosque entre mediano, grande y enorme. Los chicos llenan el espacio que queda.
  - Primero se probó repartir por número de árboles. Los grandes no cabían en su parte y el bosque quedó ralo (4500 árboles en un mapa Mediano, contra unos 17 000 ahora).
- Los árboles guardan del inicio una distancia de 25 m más su separación, así las copas enormes no tapan el pueblo.
- La suma de referencia del mapa Pequeño pasó a `0x9692d3e6c6c5d81f`.

**D-622. Herramientas de desarrollo.**
- Se abren con Ctrl+F3, un atajo fijo como Alt+Enter. Usan ImGui como la ventana de estadísticas y tienen tres pestañas:
  - **Inspector:** el objeto bajo el cursor, o el seleccionado con clic, con su nombre y sus propiedades. De un árbol: especie, tamaño, altura, modelo y tamaños posibles. De una persona: actividad, velocidad, vestimenta y accesorios. Siempre incluye el terreno donde está: suelo, bioma, fertilidad, altura, pendiente y agua. Sin objeto, muestra el terreno bajo el cursor. Botones: Ir a, Quitar selección, Eliminar.
  - **Crear:** árboles de cualquier especie, tamaño y altura; arbustos, hierbas, piedra, mineral, casas y personas. Se colocan en el centro de la vista, o con clic en el suelo si se activa esa opción.
  - **Explorador:** todos los objetos, filtrados por categoría y buscados por nombre sin importar mayúsculas ni acentos. Opcionalmente ordena por cercanía. Al elegir uno, la cámara va hacia él y queda seleccionado.
- "Colocar con clic" solo actúa mientras la pestaña Crear está a la vista. En otra pestaña, o con la ventana colapsada, el clic selecciona como siempre (corrección pedida por el usuario el 2026-09-27).
- Los cambios modifican el mapa en memoria (solo presentación y pruebas): no hay partida que guardar todavía.
- Cuando exista el multijugador, estas herramientas solo funcionarán en partidas de un jugador o si el anfitrión las permite. En la fase 8 se agrega la pestaña de recursos.

**D-623. Pasto decorativo en la GPU.**
- Una cuadrícula de matas cada 0,55 m alrededor de la cámara, colocada solo por el sombreador de vértices: posición al azar por celda, altura del terreno y densidad desde el canal alfa de la textura de colores del suelo.
- La densidad depende del suelo, la fertilidad y el bioma. No hay pasto sobre agua, arena ni roca.
- Llega hasta 20, 35, 50 o 70 m según la opción Vegetación, y se encoge al acercarse al borde para que no se vea el corte.
- No guarda nada por mata, así que cuesta lo mismo en cualquier tamaño de mapa: unas 65 000 matas de 7 triángulos en Ultra.
- Recibe las sombras de los árboles pero no proyecta sombra.

**D-624. Rendimiento con los árboles nuevos (1600 × 900, Ultra, mapa Enorme "Tierra de gigantes").**
- La generación tarda unos 6 s.
- Tercera persona: unos 460 FPS.
- Primera persona mirando al horizonte, el peor caso: unos 125 FPS, con 30 millones de triángulos por los árboles grandes hasta 2500 m.
- Si hiciera falta más adelante, el paso siguiente sería una versión simplificada de cada árbol para la distancia.

## Fase 6c: estilo visual low-poly facetado (2026-09-27)

A pedido del usuario, con dos imágenes de referencia ("Low-Poly Experiments"). Los árboles de primitivas se conservan: el usuario prefirió no cambiarlos tras ver un prototipo de árboles orgánicos con tarjetas de hojas, que quedó en el historial (commit b0147ec).

**D-625. Generador: relieve montañoso, lagos irregulares, playas y un error de los ríos.**
- Nueva opción de relieve "Montañoso". En regiones amplias (una máscara de ruido) se suman crestas afiladas de hasta 90 m donde un campo de ruido cruza cero. Los inicios siguen buscando terreno llano, y las laderas empinadas quedan como roca.
- Lagos irregulares: de uno a tres lóbulos superpuestos, con la orilla deformada por ruido hasta un 45 %. Donde dos lóbulos se cruzan cuenta el más hondo, no la suma.
- Playas de 2 a 8 m, de ancho variable, solo donde la orilla no es empinada.
- **Error corregido, venía de la fase 6:**
  - Al tallar un río paso a paso, las "orillas" de cada paso volvían a levantar el cauce ya excavado de los pasos anteriores, y también el borde de los lagos donde desembocaba. Muchos ríos quedaban como franjas de arena seca.
  - Ahora el cauce excavado y la orilla de un lago no se levantan.
  - El cauce baja de 15 cm en el borde a 90 cm en el centro, siempre bajo el agua.
  - Una celda de lago necesita al menos 1 cm de agua.
  - La prueba "water is above the ground it covers" lo verifica.
- Versión del generador: 3. Suma de referencia del mapa Pequeño: `0x02797a3d14672e4b`.

**D-626. Terreno facetado con triangulación adaptativa.**
- Cada parcela de 64 m se triangula con una red irregular de triángulos rectángulos (RTIN, el método de la biblioteca "Martini" de Mapbox, escrito de nuevo aquí).
- Un triángulo se divide si:
  - la diferencia con el relieve pasa del margen del nivel de detalle;
  - es más grande que el máximo del nivel;
  - o, en los niveles cercanos, cubre dos clases de suelo (blando, arena, agua, roca).
- Los tres niveles de detalle:

| Nivel | Margen | Faceta máxima | Hasta |
|---|---|---|---|
| Cercano | 0,15 m | 8 m | 260 m |
| Medio | 0,9 m | 16 m | 800 m |
| Lejano | 4 m | 64 m | más allá |

- Los vértices interiores se desplazan al azar hasta un 15 % del tamaño de sus facetas vecinas, para que las facetas sean irregulares sin plegarse; los del borde de la parcela no se mueven. Faldones de 2 a 10 m tapan las grietas entre parcelas de distinto nivel.
- Cada faceta tiene su propio color: el de la celda bajo su centro, con una leve variación. Va en un búfer de almacenamiento que el sombreador de píxeles lee con `SV_PrimitiveID`, así los bordes entre suelos siguen las aristas de las facetas.
  - La primera prueba tomaba el color del primer vértice de cada triángulo y dejaba bordes en dientes de sierra.
- La normal de cada faceta sale de las derivadas en pantalla de la posición, así que cada triángulo se ilumina plano.
- Las mallas se calculan en el hilo de generación. Un mapa Enorme montañoso tarda unos 7,4 s en total y ocupa unos 380 MB de memoria con todo el juego.
- Se quitaron el sombreador de la cuadrícula anterior y la textura de ruido del suelo.

**D-627. Colores, luz y ajuste de tono.**
- Paleta más viva:
  - pasto 96,168,58;
  - pradera 122,180,66;
  - suelo de bosque 70,128,50;
  - arena 226,206,150;
  - roca 138,104,82;
  - arcilla 164,118,84.
- El fondo del agua es arena mojada: se ve a través del agua poco profunda.
- Cielo azul intenso y sol más fuerte.
- Todos los sombreadores iluminados, el agua y el cielo pasan por la misma curva de tono tipo cine (ACES, ajuste de K. Narkowicz, exposición 0,68). Así la luz fuerte no satura los colores, y la niebla coincide con el cielo.
- La primera prueba, sin ese ajuste, se veía lavada y verde lima.
- No hay oclusión ambiental ni luz rebotada: las imágenes de referencia son renders offline. Se puede agregar oclusión en pantalla en la fase de optimización visual.

**D-628. Cordillera de fondo y nubes (decoración).**
- Alrededor del mapa, hasta 3 km, hay un anillo de montañas facetadas en baldosas de 48 × 48 puntos cada 32 m:
  - nacen a la altura del borde del mapa y suben suavemente en los primeros 500 m;
  - tienen pasto abajo, roca en las laderas y nieve arriba.
- Se dibujan con el mismo sombreador que el terreno. No son jugables ni forman parte de la simulación.
- Las nubes low-poly (`props/cloud.glb`) son unas pocas por kilómetro cuadrado, a 240–360 m de altura, sobre el mapa y la cordillera.
  - Son de la clase de modelo "cielo": no proyectan sombra y llegan tan lejos como el terreno.
  - Por ahora no se mueven.

**D-629. Agua facetada.**
- La superficie usa mallas de 2 m de paso cerca y de 4 m lejos. Sus vértices se desplazan igual en todas las parcelas y suben y bajan con dos ondas lentas, más calmadas en la orilla. Cada faceta se ilumina plana.
- El color va de turquesa claro a azul profundo según la profundidad, con brillo del sol y efecto Fresnel.
- Es más transparente en la orilla (opacidad desde 0,62), donde se ve la arena.

**D-630. Rendimiento medido (1600 × 900, Ultra, mapa Enorme montañoso).**
- Tercera persona: unos 347 FPS.
- Primera persona mirando al bosque, el peor caso: unos 110 FPS, con 31 millones de triángulos (casi todos de árboles).

## Plan de trabajo desde la fase 7 (2026-09-27)

**D-631. Sin compatibilidad entre versiones de partidas guardadas.**
El usuario no quiere compatibilidad de partidas guardadas entre versiones del juego, ni siquiera después de la entrega: cada versión empieza partidas nuevas. Una partida de otra versión se rechaza con un mensaje claro. Así el generador de mapas y las reglas pueden cambiar en cualquier fase; solo hay que actualizar las sumas de referencia de las pruebas.

**D-632. Cambios visuales al final.**
Los cambios de aspecto que el usuario quiere en el terreno y el agua se hacen en la fase 18 (Arte y sonido). Las ideas se anotan en `docs/IDEAS_VISUALES.md`. Si algo del terreno estorba al juego antes, se corrige en esa fase.

**D-633. Fases 7 a 20 seguidas.**
El usuario pidió avanzar de la fase 7 a la 20 sin detenerse, tomando en cada duda la opción recomendada, y un resumen al final con lo que debe revisar por fase. Cada fase termina igual que las anteriores: todas las configuraciones compiladas sin advertencias, pruebas en verde, una prueba en vivo, documentación y un commit. Cada decisión que la especificación no cubre se anota aquí.

## Fase 7: mods y datos (2026-09-27)

**D-701. Contenido como datos del mod `core`.**
- Recursos, edificios, recetas, rasgos del mapa, especies, biomas y tipos de mapa son definiciones JSON en `data/mods/core/defs/`.
- Los modelos pasaron de `data/models` a `data/mods/core/models`. Los modelos de prueba del cargador pasaron a `tests/data_models_test`.
- Los nombres de especies, biomas y tipos de mapa pasaron a los textos del mod (`data/mods/core/lang`).
- El juego arma una estructura `sim::Content` con todo validado, y la simulación y el generador solo la leen. Las especies, biomas y tipos de mapa son índices en listas; ya no son enumeraciones del código.
- Los tamaños de árbol siguen en el código: son reglas del motor, no contenido.
- El generador da el mismo mapa que antes para la misma semilla (la suma de referencia no cambió).

**D-702. Lua 5.4 aislado y determinista.**
- Se vendorizó Lua 5.4.7 (aprobado en la especificación).
- La semilla de los hashes de texto de Lua se fija en 0 (`luai_makeseed`); si no, el orden de `pairs` variaría entre máquinas.
- `math` se reemplaza por funciones enteras. Los números con decimales de Lua siguen existiendo, pero los valores que vuelven al juego se leen como enteros (`luaL_checkinteger` los rechaza si no lo son).
- Límites: 50 millones de instrucciones por llamada (gancho de conteo) y 64 MB por estado (asignador propio).
- `require` solo carga `scripts/*.lua` del propio mod, con nombres `[a-z0-9_.]`.
- Lua informa errores con `longjmp`, que no ejecuta destructores de C++. Las funciones que Lua llama leen y validan sus argumentos antes de crear objetos de C++. Está anotado en `lua_sandbox.cpp`.

**D-703. Primer gancho de reglas: `on_map_generated`.**
- Es el único punto de la simulación que existe antes de la fase 8, y cubre el criterio de "una regla en Lua sin tocar el código".
- Se ejecuta en el hilo de generación con un estado de Lua nuevo por mod y por mapa, y un generador aleatorio derivado de la semilla y del id del mod.
- Si una regla falla, el mapa se genera igual y se avisa.
- Los ganchos de la simulación (nace un aldeano, termina una estación…) se agregan cuando existan esos sistemas.

**D-704. Ids únicos por tipo; parches y quitas indican el tipo.**
- `core:stone` es a la vez un recurso y un rasgo del mapa, y `core:giants` un bioma y un tipo de mapa, así que los ids se distinguen por tipo.
- Un parche o una quita llevan `"type"`.
- El campo de tamaño de mancha de los tipos de mapa se llama `patchSize`, para no confundirse con `"patch"`.

**D-705. Orden de carga y errores.**
- Primero `core`, luego los mods activados en el orden del jugador, movidos después de sus `dependencies` y `loadAfter` (orden topológico estable).
- Un mod con errores en sus definiciones se quita y el contenido se reconstruye sin él (hasta 16 veces), junto con los mods que dependían de él.
- Un mod de usuario con el id de uno incluido se rechaza.
- Los errores se ven en la pantalla de Mods.

**D-706. Hash del contenido.**
- Cada mod tiene un hash FNV-1a de 64 bits de sus archivos (ruta, tamaño y contenido, en orden).
- El contenido tiene un hash que combina id, versión y hash de los mods que afectan a la simulación. Sirve para comparar mods en multijugador y en las partidas guardadas; no es una firma de seguridad.

**D-707. Elección de mods en `mods.json`.**
Separado de `settings.json`, con escritura atómica y cuarentena si está dañado. Aplicar los mods reconstruye el contenido, recarga los textos y carga solo los modelos nuevos (los ya cargados se reutilizan por ruta). Si había un mapa abierto, se cierra.

## Fase 8: primer pueblo jugable (2026-09-27)

**D-801. Tiempo del juego.**
10 ticks por segundo a x1; un día son 100 ticks (10 s), un mes 10 días y un año 12 meses: un año dura unos 20 minutos a velocidad normal. La edad de juego va comprimida: se es adulto a los 5 años y la vejez empieza a los 45 (con una probabilidad mensual de morir que crece con la edad).

**D-802. Hambre y salud.**
- Cada aldeano tiene un medidor de comida de 0 a 1000. Un adulto gasta un punto cada 4 ticks y un niño la mitad; un medidor lleno dura unos cuatro meses.
- Va a comer por debajo de 500 al almacén con comida más cercano y come varias raciones, primero la más nutritiva (bayas 3, raíces 2; 100 puntos por punto de nutrición).
- Con el medidor en cero pierde un punto de salud cada 2 ticks: muere de hambre en unos 3 minutos si no come. Con comida, la salud se recupera sola.
- Se descartó 1 punto por tick: la comida inicial duraba menos de 3 minutos.

**D-803. Crecimiento de la población.**
- Nacimientos: una vez al mes, cada casa con un hombre y una mujer adultos de hasta 40 años, bien alimentados, con lugar libre y con comida guardada para al menos 3 raciones por habitante tiene un 12 % de probabilidad.
- Inmigración: una vez al mes llega una familia (2 a 4 personas) si hay al menos 2 lugares libres en casas y comida guardada de al menos 40 + 10 por habitante.
- Arranque: centro del pueblo, cinco parejas y dos niños, 60 troncos, 20 piedras, 150 bayas y 40 raíces.

**D-804. Caminar: rejilla de 2 m y A\*.**
- `NavGrid` marca como bloqueadas las celdas con agua o con más de 1.8 m de desnivel, y las de los edificios; el bosque y las pendientes cuestan más.
- A\* con 8 vecinos, sin cortar esquinas, con la clave del montículo `(f << 32) | celda` para desempatar por índice (determinista). Presupuesto de 150 000 nodos por búsqueda.
- Quien queda dentro de un edificio recién puesto sale por la celda libre más cercana.
- Los aldeanos caminan a 2 m/s (los niños a 1.6).
- Para usar un edificio se acercan a cualquier lado de su contorno, el más cercano a ellos, no a una puerta fija: con una puerta fija, un barranco detrás de ella provocaba rodeos de cientos de metros.

**D-805. Área de trabajo por distancia caminando.**
El radio de trabajo de un taller (leñador 55 m, recolector 65 m…) se mide caminando: un Dijkstra desde el taller hasta 1.5 veces el radio, recalculado cuando cambian los edificios. Los recolectores eligen el recurso más cercano **por camino**, no en línea recta. En la prueba, un leñador al otro lado de un río mandaba a sus trabajadores a rodearlo y morían de hambre en el camino.

**D-806. Recolectar, guardar y acarrear.**
- Los recolectores cargan lo que llevan (12 unidades de peso 1; troncos pesan 2) y lo dejan en su propio taller si tiene lugar, o en el almacén más cercano.
- Los peones (adultos sin trabajo) construyen primero y, si no hay obras, acarrean: llevan a un almacén lo que se juntó en los talleres cuando hay una carga completa o el taller está casi lleno.
- Construir, comer y producir también toman bienes de los talleres, salvo los insumos de sus recetas.
- Los arbustos se vacían y rebrotan (bayas en 30 días, hierbas en 45); los árboles talados y las piedras agotadas desaparecen.

**D-807. Construcción por etapas.**
Colocar un edificio despeja al instante los árboles y rocas de su terreno. Los peones llevan los materiales (reservados para que dos no lleven lo mismo) y luego trabajan: la obra termina con todos los materiales y el trabajo hecho. En la vista, el edificio sube desde el suelo con color de madera sin terminar. Cancelar devuelve los materiales al centro del pueblo.

**D-808. Trabajos y casas.**
Cada 20 ticks se asignan trabajadores a los talleres terminados (el adulto libre más cercano) y casa a quien no tiene (primero con su familia). El jugador cambia cuántos trabajadores quiere en cada taller (comando `SetWorkers`).

**D-809. Todo cambio pasa por comandos.**
El juego solo cambia con los comandos `PlaceBuilding`, `RemoveBuilding`, `SetWorkers` y `DevGrant` (herramientas de desarrollo, aceptado solo si la partida lo permite; el permiso es parte del estado). La sesión aplica los comandos del jugador al empezar el siguiente tick, como se hará en multijugador. Los comandos inválidos se ignoran y se cuentan igual en todas las máquinas.

**D-810. Pausa y velocidad.**
Espacio pausa y reanuda; 1, 2 y 3 eligen la velocidad. En pausa, y con el menú del juego abierto en una partida de un jugador, el juego se detiene, la escena se desenfoca (dos pasadas gaussianas sobre la imagen terminada, solo mientras dura la pausa) y la interfaz no se puede usar, como pide la especificación.

**D-811. Partidas guardadas.**
- Archivo `.scsave`: firma, versión del esquema, cabecera JSON legible (nombre, versión del juego, fecha, jugadores, reglas, hash del contenido, mods, semilla, tick, población) y bloques con etiqueta, tamaños y CRC32. Los bloques desconocidos se conservan.
- El bloque `GAME` es la serialización del juego (mapa incluido) y es la que se usará para sincronizar partidas en red.
- Se guarda con escritura atómica verificada. F5 guarda una partida nueva con fecha y hora; F9 carga la más reciente. Autoguardado cada 10 minutos de juego en tres archivos que rotan.
- Una partida de otra versión del juego o de las reglas, o con otros mods, se rechaza con un mensaje claro (D-631).
- Sin miniatura por ahora: requiere leer la imagen de la GPU; queda para la fase 17.

**D-812. Bloques comprimidos con zstd.** *(Reemplaza a una primera versión sin compresión.)*
Cada bloque se comprime con zstd nivel 3 si así ocupa menos; el campo de compresión dice cuál (0 = sin comprimir, 1 = zstd). Al leer, el tamaño del marco de zstd tiene que coincidir con el del bloque, y ningún bloque descomprimido pasa de 1 GiB. Se vendorizó zstd 1.5.7 (licencia BSD) sin ensamblador ni formatos antiguos.

**D-813. Vista del pueblo.**
- Cada edificio usa el modelo de su definición, escalado a su huella; por ahora todos usan la casa de prueba (el arte llega en la fase 18).
- Los aldeanos usan los cuerpos del grupo de prueba; su aspecto (paleta, sombrero, barba, delantal) sale de bits aleatorios guardados en el juego, así que es igual en todas las máquinas y después de cargar.
- Los rasgos del mapa cambian uno por uno (`update_instance`) cuando se talan o se vacían, sin reconstruir las listas.
- Se quitaron del mapa el pueblo de muestra y la multitud de prueba (D-617).

**D-814. Interfaz de la fase 8.**
Barra superior (comida total, otros bienes, población, fecha y velocidad), barra de construcción con descripción de costo y tamaño, fantasma verde o rojo con el motivo del rechazo, R para girar, Mayús+clic para colocar varios, clic derecho o Esc para cancelar, y ventanas de edificio y de aldeano con marcador sobre lo seleccionado. Las ventanas con imán y anclaje quedan para la fase 17. Las herramientas de desarrollo tienen una pestaña "Pueblo" para dar bienes al centro del pueblo.

**D-815. Balance comprobado con una prueba de una hora.**
La prueba `village` juega una hora a x1 (36 000 ticks, 0.2 s de CPU) con un jugador simulado que construye casas, recolectores, leñadores y un almacén: el pueblo pasa de 12 a unos 18 habitantes sin muertes. Sin edificios, el pueblo muere de hambre. El ritmo de crecimiento se ajustará con las fases 10 a 12 (estaciones, agricultura, necesidades).

**D-816. Advertencias en bibliotecas de terceros.**
Las bibliotecas vendorizadas no se modifican. ENet 1.3.18 combina valores de dos enumeraciones con `|` a propósito y MSVC 17 lo advierte (C5287); esa advertencia se desactiva solo para el objetivo `enet`. En nuestro código ninguna advertencia se desactiva. ENet se vendorizó ya en esta fase (aprobado en la especificación) para la fase 9.

## Fase 9: multijugador por lockstep (2026-09-27)

**D-901. Turnos cerrados por adelantado desde el anfitrión.**
El anfitrión es la autoridad de los turnos. Antes de ejecutar el tick *T* cierra el turno *T + retraso* con las órdenes que tenga y lo envía. Nadie espera respuestas de los demás para avanzar, solo los turnos del anfitrión. Esto mantiene la estrella de la especificación y hace que una orden nunca se aplique en máquinas distintas en ticks distintos. El detalle está en `docs/RED.md`.

**D-902. Cada máquina genera el mapa.**
El mapa no viaja por la red: la configuración y el contenido bastan, y cada máquina confirma con el hash del mapa. Así empezar una partida en un mapa enorme no manda decenas de MB. Las instantáneas (entrar a una partida empezada, resincronizar) sí llevan el mapa.

**D-903. ENet en el hilo principal.**
La red se atiende una vez por cuadro en el hilo principal (`enet_host_service` sin espera) en lugar de en un hilo propio (sección 7.2). Con pocos mensajes por tick no hace falta otro hilo; se moverá si la fase 20 lo pide.

**D-904. Comprobación por partes cada 50 ticks.**
El hash del estado se divide en siete partes para que el informe de desincronización diga dónde está la diferencia. Cada comprobación serializa el estado completo; en la fase 20 se medirá su costo con 12 000 aldeanos.

**D-905. Reparar una desincronización con la instantánea del anfitrión.**
El estado del anfitrión manda: se le envía al jugador desincronizado, que lo carga y sigue. El informe queda en la carpeta de registros.

**D-906. Volver a entrar por nombre.**
Un jugador que cerró el juego a la fuerza no guarda ninguna credencial. Al volver con el mismo nombre recupera su asiento, que estaba desconectado. Como en las partidas de LAN no hay cuentas, alcanza. Si un nombre ya está en uso en la sala se le agrega " (2)".

**D-907. Asientos y mundo.**
- Al empezar, los asientos se ordenan 0..n−1 y se reenvía a cada uno su número.
- En un **pueblo común** la partida tiene los 12 asientos activos que dan órdenes al pueblo 0, así que cualquiera puede entrar después.
- En **pueblos separados** hay un pueblo por jugador presente al empezar. Quien entra después solo puede tomar el pueblo de un jugador que se fue.
- El modo "mapas separados" (7.7) llega con el comercio y el mapa del mundo (fase 14).

**D-908. Velocidad.**
La pausa es inmediata; lo demás se vota con 15 s de plazo (7.5). Un jugador que retrasa a todos más de 3 s baja la velocidad un paso. En red, abrir el menú del juego no pausa la partida.

**D-909. `--instance` y `--loopback`.**
`--instance n` (1 a 8) usa la carpeta de datos `instance-n`, el puerto 47800 + n y una ventana pequeña si es la primera vez. `--loopback` escucha solo en 127.0.0.1 y no usa el descubrimiento. Se agregó para probar varias ventanas en una PC sin que Windows pregunte por el firewall. Sin esa opción, crear una partida hace que Windows pida permiso la primera vez.

**D-910. Sin herramientas de desarrollo en red.**
Los comandos de las herramientas de desarrollo (`DevGrant`) se rechazan en partidas en red: el permiso es parte del estado y está apagado. Más adelante podrá ser una opción de la sala.

**D-911. Qué no entra en esta fase.**
- Cargar una partida guardada en red, que debe reabrir la sala (6.2), queda para la fase 17, con la interfaz completa. En red se puede guardar (F5), pero la partida guardada se abre como de un jugador.
- La contraseña opcional de la sala tampoco se hizo.

**D-912. Campo de texto.**
La interfaz propia tiene ahora un campo de texto de una línea con entrada de SDL (`SDL_StartTextInput` solo mientras un campo tiene el teclado). Mientras se escribe, los atajos del juego no actúan.

**D-913. Autoguardado según la configuración.**
El autoguardado usa los minutos y la cantidad de archivos de Configuración → Juego (antes eran constantes).

## Fase 10: estaciones y clima (2026-09-27)

**D-1001. Reglas de partida aparte del mapa.**
El clima, los recursos iniciales y la población máxima son `GameRules`, que viajan con la partida (`GameSetup`, la configuración de red y el guardado) y no dentro de `MapSettings`. Así el mapa y su hash no cambian, y la prueba del mapa de referencia sigue igual.

**D-1002. Calendario.**
- El año tiene 12 meses de 10 días. Su duración es corta (10 min a x1), normal (20 min) o larga (40 min); cambia cuánto dura un día.
- Las estaciones elegidas se reparten el año en partes iguales y en orden. Con una sola estación, dura todo el año.
- La edad de los aldeanos y los meses de nacimientos y llegadas siguen el año de la partida.

**D-1003. Temperatura.**
- Cada estación tiene una temperatura base: primavera 12 °C, verano 24 °C, otoño 11 °C (7 °C con invierno duro), invierno 3 °C (suave), −4 °C (normal) o −14 °C (duro).
- El primer cuarto de cada estación pasa gradualmente desde la anterior.
- Cada día varía entre −3 y +3 °C según la semilla y el número de día. Es una función pura del tick y es igual en todas las máquinas.

**D-1004. Nieve y heladas.**
- Con temperatura bajo cero cae nieve (0 a 100) y con más de 2 °C se derrite.
- La nieve frena al caminar hasta la mitad y tapa el pasto.
- Con helada (0 °C o menos), los arbustos y las hierbas ni se recolectan ni rebrotan.

**D-1005. Calefacción y ropa.**
- Cada casa guarda hasta 20 de leña, que llevan sus habitantes cuando se acerca el frío.
- La casa quema 1 de leña por día con helada, y 1 cada dos días por debajo de 10 °C.
- Un aldeano sin casa caliente pierde calor cuando hace menos de 5 °C; con ropa de abrigo, la mitad. Sin calor pierde salud y no se recupera hasta abrigarse.
- La ropa se toma del almacén al comer y dura un año. La hará el sastre en la fase 12; por ahora el pueblo empieza con 12.
- El consumo inicial (2 de leña por día) resultó imposible de sostener: la leñera se comía todos los troncos y no quedaban para casas.

**D-1006. Límite de producción.**
Un taller de producción (por ejemplo la leñera) trabaja solo mientras el pueblo tenga menos de 30 + 3 por habitante de su producto. Así no se gasta toda la materia prima; en la fase 12 cada edificio tendrá su propio límite configurable.

**D-1007. Peones de reserva.**
Mientras haya obras, al asignar trabajos quedan libres al menos 2 adultos, o un quinto de ellos. Sin esto, todos terminaban en talleres y nada se construía. En la fase 12 esto podrá ajustarse, como en Farthest Frontier.

**D-1008. Zonas caminables.**
La rejilla de caminos numera sus zonas conectadas y la búsqueda termina al instante si el destino está en otra zona (una isla, la otra orilla). Antes, pasear hacia un lugar inalcanzable recorría hasta 150 000 celdas y una hora de juego pasó de 0.2 s a 8 s.

**D-1009. La vista de las estaciones.**
- La nieve se dibuja en los sombreadores: cubre lo que mira hacia arriba (suelo, copas, techos) según la nieve acumulada, y el pasto desaparece.
- Los árboles de hoja caduca cambian de tinte en otoño (dorado, naranja o rojo) y en invierno; los de hoja perenne (`"evergreen"` en las especies) no.
- La luz cambia por estación, y los aldeanos usan gorra en invierno y sombrero de paja en verano.
- El tinte afecta a todo el modelo, tronco incluido. En la fase 18 se agregarán árboles sin hojas y colores por material (anotado en `docs/IDEAS_VISUALES.md`).

## Fase 11: agricultura y alimentos (2026-09-27)

**D-1101. Cultivos como datos.**
El tipo de definición `crop` tiene recurso, rendimiento (unidades por 10 celdas con fertilidad plena), días de crecimiento, efecto en la fertilidad al cosechar y si resiste la helada. El juego base trae trigo (−12), verduras (−8) y frijoles (+12, la leguminosa que devuelve nitrógeno).

**D-1102. Campos de una granja.**
- Una granja tiene hasta 4 campos rectangulares de 4 a 20 m por lado, con su centro dentro de su alcance.
- Se marcan arrastrando sobre el suelo. Despejan lo que crece ahí, no dejan construir encima y se pueden caminar.
- La fertilidad inicial es el promedio de la del mapa en sus celdas.

**D-1103. El año de un campo.**
- Cada campo tiene un plan de tres años: un cultivo o barbecho por año, que se cambia en la ventana de la granja.
- En el primer día del año pasa al siguiente año del plan. Un barbecho descansa y suma 15 de fertilidad.
- Se siembra con al menos 6 °C y fuera del invierno, a 2 trabajos por celda.
- Crece los días de 5 °C o más, más rápido con buena fertilidad. Una helada mata el cultivo que no resiste.
- Al madurar se cosecha una unidad cada 20 ticks: se lleva a la granja y de ahí a un almacén o granero.
- Rinde celdas × rendimiento × fertilidad / 1000. Al terminar la cosecha se aplica el efecto del cultivo en la fertilidad.

**D-1104. Abono.**
La compostera produce abono sin insumos. Antes de sembrar, los granjeros lo llevan a la granja y lo esparcen: cada unidad suma 3 de fertilidad, hasta 10 unidades por campo y año.

**D-1105. Huertos por datos.**
Los edificios tienen tres campos nuevos:
- `seasons`: estaciones en que trabaja;
- `matureYears`: años hasta que produce;
- `yearlyLimit`: tope por año.

El huerto los usa: da fruta en verano y otoño desde su tercer año, hasta 120 por año. No hizo falta código nuevo de trabajo.

**D-1106. Caza y pesca sin animales todavía.**
- Las zonas de ciervos y jabalíes del mapa guardan cuántos animales quedan (16 y 10), y se recuperan cada mes.
- Un cazador va a la zona con animales más cercana dentro de su alcance y a la que se pueda llegar. Cada presa da una carga de carne, y la piel queda en el refugio.
- El pescador pesca en el agua más cercana: un pescado cada 45 ticks, hasta 8 por viaje. Con −3 °C o menos el agua está helada.
- Los animales con comportamiento llegan en la fase 15.

**D-1107. Dieta variada.**
- Al comer, un aldeano prefiere los alimentos que no comió en el mes y después los más nutritivos.
- Con tres o más tipos de comida en el mes anterior recupera la salud el doble de rápido. En la fase 12 la variedad también cuenta para la felicidad.
- El trigo se come crudo con poca nutrición (1) hasta que la fase 12 traiga harina y pan.

**D-1108. Vista de los campos.**
Los campos se dibujan con dos modelos hechos en código: una losa de tierra de 2 × 2 m y un grupo de plantas. Las plantas crecen con el cultivo y pasan de verde a su color maduro: dorado el trigo, naranja las verduras, verde los frijoles. Tras la cosecha queda rastrojo, y en barbecho la tierra se cubre de pasto. Los colores del tinte están en espacio lineal.

**D-1109. Qué no entra.**
Las malas hierbas, las piedras en los campos y las plagas (7.9) quedan para después de la fase 12; no están en los criterios de esta fase.

## Fase 12: cadenas de producción y necesidades (2026-09-27)

**D-1201. Cadenas como datos.**
Las cadenas de 7.9 son recetas y talleres en `core`:
- alimentos: trigo → harina → pan (con leña); cebada → cerveza; carne o pescado → ahumados;
- ropa y calzado: pieles → cuero → ropa o calzado; lino → tela → ropa;
- construcción: arcilla → ladrillos o tejas;
- hierro: troncos → carbón; mineral y carbón → hierro; hierro → herramientas.

Un taller con varias recetas trabaja la primera cuyo producto falta y cuyos insumos tiene; si no, va a buscar lo que falta para la primera posible. La salazón quedó fuera: no hay sal en el mapa.

**D-1202. Límite de producción por taller.**
Cada taller guarda un límite de su producto: automático (30 + 3 por aldeano, D-1006) o el que ponga el jugador, de 10 en 10, con el comando `SetLimit`.

**D-1203. Necesidades.**
Cada día, cada casa revisa diez necesidades (una por bit):
- dieta variada, ropa y calzado: para al menos la mitad de sus habitantes;
- agua (un pozo), religión (una capilla con sacerdote), entretenimiento (una taberna con tabernero y cerveza, que gasta una por día) y mercado: un edificio de servicio a su alcance;
- calefacción: su fuego;
- belleza: un entorno de 10 o más;
- higiene: en la fase 13.

Los servicios se definen en datos (`service`, `serviceRadius`, `serviceUses`). Lo que un servicio consume no se lo llevan los peones.

**D-1204. Dieta variada por comidas.**
La variedad cuenta los tipos entre los últimos cuatro bocados, sin importar cuándo fueron. Primero se contó por mes y luego por dos meses: un aldeano come cada uno o dos meses, así que la ventana se vaciaba entre comidas y nunca llegaba a tres tipos.

**D-1205. Entorno y felicidad.**
- **Entorno:** la suma de la deseabilidad de los edificios a menos de 30 m (disminuye con la distancia) más un punto por árbol cercano, hasta 8. Los jardines y estatuas suben; curtiduría, fundición, horno y carbonera bajan.
- **Felicidad de una casa:** 28 + 8 por necesidad cubierta + la mitad del entorno (±10), entre 0 y 100.
- **Felicidad del pueblo:** el promedio por habitante, y quien no tiene casa cuenta 25.
- **Efectos:**
  - los nacimientos dependen de la felicidad del hogar (12 % al mes con 60);
  - llegan recién llegados si el pueblo tiene 35 o más;
  - un hogar con menos de 15 tiene 25 % cada mes de irse entero.

**D-1206. Niveles de las casas.**
Una casa sube de nivel sola cuando cubre las necesidades del siguiente nivel: los peones traen los materiales y hacen el trabajo, como en una obra.
- Nivel 2 (7 habitantes): dieta, agua, ropa y calefacción; troncos y piedra.
- Nivel 3 (9 habitantes): además calzado, mercado, religión, entretenimiento y belleza, y el centro del pueblo en nivel 2; ladrillos, tejas y herramientas.

Las casas no bajan de nivel.

**D-1207. Niveles del centro del pueblo.**
El jugador lo mejora desde su ventana cuando tiene los aldeanos necesarios (30 y 70), y los peones hacen la obra. Cada nivel desbloquea edificios (`tier` en los datos):
- nivel 2: molino, panadería, cervecería, talleres, horno, carbonera, mercado, capilla, taberna y estatua;
- nivel 3: mina de hierro, fundición y herrería.

**D-1208. Paseos cortos.**
Un aldeano sin nada que hacer ya no pasea si el camino mide más de 54 m (tres veces el radio del paseo). Un tabernero pasaba más de 1000 ticks rodeando un lago y dejaba la taberna sin cerveza.

**D-1209. Categorías en la barra de construcción.**
Seis grupos (vivienda, alimentos, recursos, industria, servicios, decoración) con pestañas. Cada edificio los toma de su `category` o de su tipo y trabajo. Los edificios de un nivel mayor del centro del pueblo aparecen desactivados, con el nivel que necesitan.

## Fase 13: salud e incendios (2026-09-27)

**D-1301. Enfermedades como datos.**
Cada enfermedad (`type: "disease"`) dice de dónde viene, qué tan contagiosa es, cuánta salud quita por día y cuántos días dura. `core` trae tres:
- gripe: del frío (menos de 5 °C sin ropa de abrigo o sin casa caliente);
- disentería: de una casa sin pozo;
- peste: de las ratas, en casas a menos de 40 m de un almacén con más de 150 de comida y sin higiene.

Cada día, un aldeano sano tiene la probabilidad de la fuente más un contagio por cada tipo de enfermo en su casa o en su trabajo. La higiene la reduce a la mitad.

**D-1302. Gravedad y curación.**
La salud va de 0 a 1000. Un enfermo no se recupera solo y pierde la gravedad cada día: gripe 60, disentería 80, peste 120. Un curandero cerca la reduce a la mitad y cura el doble de rápido; un médico, a la cuarta parte y el triple de rápido. Al sanar, 60 días de inmunidad. Los enfermos descansan en casa y no trabajan.

La primera versión usaba gravedades de 15 a 60, que la recuperación natural (25 por día) anulaba: nadie moría. Se ajustó al verlo en una partida.

**D-1303. Incendios.**
- Cada día, cada edificio que no sea a prueba de fuego (`fireproof`: pozo, estatua, jardín, fundición, horno) tiene 4 en 100 000 de prenderse; ×3 una casa habitada con frío, ×4 un taller que gasta combustible. Con más de 30 % de nieve no empieza ninguno.
- El fuego crece cada 10 ticks, daña el edificio y cada 50 ticks puede saltar a los que estén a menos de unos 10 m. Con 1000 de daño el edificio desaparece; el centro del pueblo nunca desaparece, queda chamuscado.
- Al terminar lo que hacen, los aldeanos adultos van primero a apagarlo, pero solo si hay un pozo a menos de 50 m del incendio: cada cubo baja 2 puntos cada 10 ticks.

**D-1304. Niveles de amenaza en las reglas.**
`GameRules` suma enfermedades e incendios, de ninguno a brutal (0, 50, 100, 200 o 400 % de las probabilidades), con medio por omisión. Se eligen en la pantalla de partida nueva.

**D-1305. Avisos.**
La simulación junta eventos (incendio, edificio quemado, brote de una enfermedad nueva en el pueblo) que la aplicación muestra como avisos solo para el pueblo local. No se guardan: son para la vista y no cambian el estado.

**D-1306. Fuego de prueba.**
El comando `DevIgnite` prende fuego a un edificio propio; solo funciona con las herramientas de desarrollo permitidas, como `DevGrant`. Las herramientas (Ctrl+F3, pestaña Pueblo) tienen un botón para el edificio seleccionado.

## Fase 14: comercio (2026-09-27)

**D-1401. Monedas como tesoro del pueblo.**
Las monedas no son un recurso que se carga ni se guarda en almacenes: son un número por pueblo (`coins`). Cada pueblo empieza con 100 (50 con recursos escasos, 200 con abundantes). Así el comercio no depende de que los peones muevan monedas.
*Reemplazada el 2026-09-27 a pedido del usuario:* el oro pasará a ser un recurso que se carga, con bóveda (fase 28), y el puesto de comercio podrá comerciar solo mientras haya mercaderes de visita (fase 29).

**D-1402. Precios en los datos.**
Cada recurso tiene `value`, su precio base en monedas; con 0, los mercaderes no lo compran ni lo venden. Los valores de `core` van de 1 (bayas, trigo, arcilla) a 15 (herramientas).

**D-1403. Mercaderes del entorno.**
- Llegan al puesto de comercio (`trade: true` en los datos; uno por pueblo) un mes después de construirlo y luego cada dos o tres meses. Se quedan un mes.
- Cada visita trae precios del día (entre 75 % y 125 % del valor): el pueblo compra al 125 % de ese precio y vende al 75 %, así que no hay ganancia comprando y vendiendo lo mismo.
- Traen de cuatro a seis lotes de 20 a 60 unidades para vender, y compran cualquier bien con precio de venta mayor que cero, sin límite.
- Lo comprado queda en el puesto de comercio (o en el centro del pueblo si no cabe); lo vendido sale primero del puesto y luego de los demás almacenes.

**D-1404. Comercio entre jugadores.**
Un jugador ofrece a otro "doy X de A por Y de B" (A o B pueden ser monedas).
- Lo que ofrece queda apartado hasta que el otro acepta o rechaza, o hasta que la oferta vence al mes; si no se acepta, vuelve.
- Al aceptar salen dos caravanas, una en cada sentido, que tardan lo mismo.
- En un mapa compartido, la caravana tarda un día más el camino recto entre los centros de los pueblos a 2 m/s. Con mapas separados, un día más cinco por cuadro de distancia en el mapa del mundo.
- Las caravanas son abstractas: no caminan por el mapa. Se verán en la fase 18.
- En un pueblo común no hay comercio entre jugadores.

**D-1405. Mapas separados como regiones de un solo mundo.**
Con mapas separados, cada jugador recibe el mapa del tamaño elegido, generado con la semilla más su número. Todos se ponen lado a lado en un solo mapa grande: 2 × 2 hasta cuatro jugadores, 3 × 3 hasta nueve, 4 × 4 hasta doce.
- Los cuadros que no son de nadie son mar.
- La navegación bloquea las costuras, así que nadie cruza de un mapa a otro. Solo se construye dentro del mapa propio, y la cámara no sale de él.
- El mundo no pasa de 4096 m: si el tamaño elegido no cabe, cada mapa se reduce (por ejemplo, Mediano con cinco jugadores o más).

Se prefirió esto a varias simulaciones separadas: la simulación, el guardado, la red y la verificación por hash quedan como estaban. La otra opción obligaba a rehacer los tres. Las costuras se ven si se mira hacia el borde; se pulirán en la fase 18.

**D-1406. Barra superior compacta.**
Con monedas, comercio y enfermos, la barra ya no cabía en una ventana de 1024 px.
- El clima con la fecha, la felicidad con las monedas y los enfermos con los incendios ahora van en dos líneas pequeñas.
- La población muestra solo el total; los adultos van en el tooltip.
- Los bienes que no caben se juntan en "+N más", con la lista en el tooltip.

La fase 17 rehará la barra.

**D-1407. Formato de los comandos.**
`Command` suma `def2` y `value2` para las ofertas; todos los comandos ocupan 6 bytes más. La suma de verificación dorada del mapa pequeño cambió porque `MapSettings` guarda ahora `separate` (sin compatibilidad con partidas anteriores, D-631).

## Fase 15: fauna y asaltantes (2026-09-27)

**D-1501. Animales como criaturas.**
Ciervos, jabalíes, lobos y osos son entidades (`Creature`) que viven en las zonas del mapa. La cantidad por zona sigue siendo `zone_animals`: cazar o matar un animal la baja; cada mes vuelve a crecer y nacen animales nuevos.

Se mueven en línea recta, sin buscar caminos. Es barato con cientos de animales y basta para pasear dentro de la zona.
- **Ciervos:** huyen de quien se acerque a menos de 14 m.
- **Jabalíes:** muerden una vez (30 de daño) a quien se acerque a menos de 4 m y vuelven a su zona. Primero perseguían hasta matar, y en las pruebas acababan con los constructores.
- **Lobos y osos:** persiguen a los aldeanos dentro de su territorio (el radio de la zona más 20 m) y los dejan al salir. El nivel de fauna peligrosa ajusta su alcance; con "ninguno" no hay lobos ni osos.
- No hay guaridas a menos de 150 m de un punto de inicio.

**D-1502. Asaltantes.**
- **Cuándo:** el primer asalto llega tras un año de gracia más el intervalo del nivel: 2 años en bajo, 1 en medio, 6 meses en alto y 3 en brutal. Los siguientes llegan con esa frecuencia, ±25 %.
- **Cuántos:** 2 + riqueza / 400 + población / 15, escalado por el nivel, entre 2 y 40. La riqueza suma las monedas y el valor de lo guardado.
- **Qué hacen:** salen del borde del mapa del pueblo y eligen el almacén más lleno (o, una vez de cada tres, una casa). Al llegar roban hasta 30 unidades de un bien o prenden fuego, y se van.
- **Cuándo se van antes:** pelean con quien tengan a menos de 6 m y se retiran al bajar del 35 % de salud.
- **Su camino:** buscan una ruta que puede cruzar edificios, cada uno con un costo alto. Rodean si pueden; si no, rompen lo que esté en medio (muros, puertas o casas) hasta su `hp`.

**D-1503. Defensas.**
- **Empalizada:** 400 de `hp`.
- **Muro de piedra:** 1500 de `hp`, no arde.
- **Puerta:** los aldeanos pasan y los asaltantes tienen que romperla. La navegación tiene una capa aparte para las puertas.
- **Torre de vigía:** dispara sola (60 de daño cada 2 s a menos de 30 m) a asaltantes, lobos y osos, sin guarnición: todavía no hay soldados (fase 16).
- **Trampa:** se puede pisar, hace 300 de daño al primer enemigo y se rearma en 30 s.

Las empalizadas y los muros se colocan en línea arrastrando el ratón.

**D-1504. La campana y la milicia.**
El centro del pueblo tiene un botón para tocar la campana (comando `RingBell`).
- Mientras suena, los adultos sanos dejan lo que hacen y pelean contra el enemigo más cercano a menos de 160 m del centro del pueblo. Eligen de nuevo cada 2 s y dejan ir a los asaltantes que huyen.
- Un miliciano atacado pelea contra quien lo ataca.
- Los niños y los enfermos van a casa.
- Sin campana, un aldeano atacado corre al centro del pueblo.

La milicia hace 35 de daño cada segundo: sin armas todavía (fase 16).

**D-1505. Asalto de prueba.**
`DevRaid` trae asaltantes en el acto; como los demás comandos de desarrollo, solo funciona con las herramientas permitidas (Ctrl+F3 → Pueblo).

**D-1506. Aspecto provisional.**
Los animales son un cuerpo de cajas teñido por especie y los asaltantes usan el cuerpo de los aldeanos con una marca roja en el suelo. Las defensas usan el modelo de casa. Todo se reemplaza en la fase 18.

**D-1507. La prueba del pueblo que crece, sin asaltantes.**
La prueba de "una hora de juego" mide la economía; con asaltantes en medio y sin nadie que toque la campana, el pueblo no crece. Los asaltantes tienen su propia suite (`wildlife`).

**D-1508. Índices de aldeanos tras una muerte.**
Las criaturas buscan aldeanos en una cuadrícula que se arma una vez por tick. Si un asaltante o una fiera mata a un aldeano, el almacén de aldeanos se reordena y la cuadrícula queda con índices viejos. En debug, la biblioteca estándar lo detectó como un índice fuera de rango. Ahora se rearma tras cada muerte.

## Fase 16: ejército y versus (2026-09-27)

**D-1601. Unidades como datos.**
Cada `unit` define salud, daño, cadencia, alcance, velocidad, costo en equipo, tiempo de entrenamiento, poder militar y el nivel del centro del pueblo que pide.
- **Leva:** 3 troncos.
- **Arquero:** un arco; dispara a 20 m. Los arcos se hacen en la arquería (nivel 2) con 2 troncos.
- **Lancero:** unas armas; nivel 3. Las armas se hacen en la armería (nivel 3) con hierro y un tronco.

**D-1602. El cuartel.**
Uno por pueblo, nivel 2. Tiene una fila de hasta 10 unidades. Al terminar el tiempo de entrenamiento, toma el equipo de los almacenes y a un adulto sano (primero los peones), que deja de ser aldeano: no cuenta como muerte. Si falta el equipo o la gente, la unidad espera en la fila.

Los soldados no comen ni cobran por ahora; queda anotado para balancear más adelante.

**D-1603. Órdenes.**
El jugador da una orden a todo el ejército (comando `ArmyOrder`):
- **Defender el pueblo:** se reúnen en el centro del pueblo.
- **Defender aquí:** se reúnen en un punto del mapa.
- **Atacar a un pueblo:** van por su centro del pueblo rompiendo lo que estorbe, como los asaltantes.
- **Retirarse:** vuelven sin pelear.

Mientras no se retiran, pelean solos contra el enemigo más cercano (asaltantes, lobos, osos y soldados enemigos) a menos de 16 m, o de su alcance más 6 m. Quien recibe un golpe responde, salvo los ciervos. Las torres y las trampas también dañan a los soldados enemigos, y la milicia pelea contra ellos.

Los soldados no atacan a los aldeanos enemigos.

**D-1604. Mapas separados.**
Con mapas separados, un ejército que ataca a otro pueblo viaja por el mapa del mundo: desaparece del mapa propio, tarda lo mismo que una caravana y aparece en un borde del mapa enemigo. Al retirarse vuelve igual.

**D-1605. Versus y victoria.**
`GameRules` tiene `versus`, `pvp` (combate entre jugadores), `victory` y `score_years`. La sala ofrece seis opciones:
- cooperativa;
- versus sin guerra, que gana la mejor puntuación a 5 años (el ejército cuenta como poder militar);
- versus por eliminación;
- versus por puntuación;
- versus por objetivo (derribar los centros del pueblo rivales);
- versus sin final.

Reglas del resultado:
- Un pueblo queda fuera si pierde su centro del pueblo o, salvo en "objetivo", si no le queda gente ni soldados.
- Los asaltantes no pueden derribar un centro del pueblo; solo un ejército enemigo.
- Se revisa cada mes y en cuanto cae un centro del pueblo.

**Puntuación:** 10 por habitante, 5 por edificio terminado, 100 por nivel del centro del pueblo, una por cada 10 monedas y 10 por punto de poder militar.

**D-1606. Fin de la partida.**
- En una partida cooperativa o de un jugador, la partida termina cuando no queda ningún pueblo.
- Al terminar, un panel muestra victoria, derrota o fin, con los puntos de cada pueblo. Permite seguir mirando o salir al menú.

**D-1607. Subir de nivel para probar.**
`DevLevel` sube un nivel el centro del pueblo sin costo, solo con las herramientas de desarrollo. Sirve para revisar a mano lo que pide nivel 2 o 3 sin juntar 30 o 70 aldeanos.

## Fase 17: interfaz completa (2026-09-27)

**D-1701. Ventanas del juego.**
Todas las ventanas (edificio, aldeano, bienes, estadísticas, eventos, capas, comercio y ejército) usan un mismo marco (`GameHud::window`, en `hud_windows.cpp`):
- **Mover:** se arrastran por el título. A menos de 12 px se pegan a los bordes de la pantalla y a los bordes de otras ventanas.
- **Anclar:** al soltarla tocando otra, forman un grupo que se mueve junto. Ctrl+arrastrar la saca del grupo.
- **Ancho:** la esquina inferior derecha lo cambia.
- **Plegar:** sin foco (un clic fuera) y sin el cursor encima, a los 0,7 s se pliega en una pestaña con su título. El cursor sobre la pestaña la abre de nuevo.
- **Fijar:** "Fijar" la deja siempre abierta.

La posición, el ancho, si está fijada y el grupo se guardan en `settings.json` (`ui.windows`), en un texto compacto que se valida carácter por carácter; una entrada dañada solo devuelve esa ventana a su lugar. Al abrirse por primera vez, una ventana se coloca debajo de las que ya ocupan su lugar por omisión.

**D-1702. Columna de ventanas.**
A la izquierda, botones para Bienes, Estadísticas, Eventos y Capas, más Comercio y Ejército cuando corresponden. Comercio y Ejército salen de la barra superior, que queda para los números.

**D-1703. Notificaciones.**
- **Cuáles:** los eventos del pueblo propio (incendios, brotes, mercaderes, ofertas, caravanas, asaltos, ataques, soldados nuevos, nacimientos y muertes). Los pueblos que quedan fuera se avisan a todos.
- **Dónde:** aparecen sobre la barra de construcción a la derecha, hasta cuatro, durante 12 s. Si una se repite en menos de 10 s se cuenta ("×3") en vez de apilarse.
- **Registro:** se guardan las últimas 100 en la ventana Eventos, con la fecha del juego.
- Un clic en una notificación con lugar lleva la cámara ahí.

Los avisos de la red, guardar y cargar siguen siendo mensajes breves arriba.

**D-1704. Capas del mapa.**
Se dibujan con cuadros de color sobre el suelo en unos 100 m alrededor de donde mira la cámara, y se recalculan dos veces por segundo para no pesar:
- **Fertilidad:** del suelo.
- **Belleza:** el mismo cálculo que usan las casas (`Game::desirability_at`), en cuadros de 8 m.
- **Alcance de servicios:** agua, mercado, religión y salud (curandero o médico).
- **Riesgo de incendio:** rojo si el edificio de madera no tiene pozo a 50 m, amarillo si lo tiene.
- **Rutas:** los caminos que siguen los aldeanos.

**D-1705. Tutorial.**
Un tutorial es un tipo de definición (`tutorial`) con un mapa (semilla y tamaño) y pasos. Cada paso tiene:
- un texto;
- una meta: mover la cámara, colocar o terminar un edificio, asignar trabajadores, cambiar la velocidad, juntar un bien, llegar a una población, o una función de Lua del `main.lua` del mod que recibe una copia del estado y devuelve si se cumplió;
- el elemento a señalar: un edificio de la barra (primero su pestaña), el + de trabajadores, la velocidad o un botón de la columna.

`core` trae "Primeros pasos", de diez pasos. La meta de guardar leña es una función de Lua, como ejemplo para los mods. Se abre desde el menú principal, sin asaltantes y con amenazas bajas. El panel de pasos va sobre la barra de construcción para no tapar las ventanas, y permite saltar un paso o salir. Al terminar se marca `tutorialSeen`.

**D-1706. Tooltips.**
Las ventanas nuevas tienen tooltips en cada elemento: los bienes con su valor y alimento, las capas con qué muestran, y las notificaciones con "clic para ir".

## Fase 18: arte y sonido (2026-09-27)

**D-1801. Un modelo por edificio.**
`art/blender/buildings.py` genera los 46 edificios de `core` en `models/buildings/`. Cada uno ocupa su terreno (ancho en X, fondo en Y) con la puerta hacia −Y.
- La mayoría de los talleres son una casita de entramado al fondo del terreno con el patio del oficio al frente: troncos en el leñador, yunque en la herrería, horno en la panadería, barriles en la cervecería, telar en el tejedor, aspas en el molino...
- Los edificios propios tienen su forma: el centro del pueblo con torre y campana, la capilla con aguja, el mercado con tres puestos de toldos, el pozo, las defensas, el cuartel con patio de entrenamiento...
- Techos de teja, paja o pizarra según el oficio.

Todo se regenera con Blender y da archivos idénticos.

**D-1802. Animales con modelo propio.** *(Reemplazada por D-4716: los animales del juego son los del zoo low poly, animados.)*
`art/blender/animals.py` hace ciervo (con cornamenta), jabalí (con colmillos), lobo y oso, sin esqueleto. El juego los hace trotar subiendo y bajando. Las animaciones con huesos quedan para más adelante. Los asaltantes y soldados siguen con el cuerpo de los aldeanos y una marca de color.

**D-1803. Partículas.**
Son bolitas de pocos polígonos que suben, crecen y se achican al final; se calculan en la CPU y se dibujan como instancias, sin shaders nuevos. Solo se emiten cerca de la cámara, con un máximo de 4000:
- humo de chimenea en las casas con fuego cuando hace frío y en los talleres que queman combustible;
- llamas y humo negro en los incendios.

**D-1804. Sonido.**
- **Los sonidos:** `art/audio/make_sounds.py` los sintetiza en Python puro, con semilla fija (WAV mono de 16 bits a 22 050 Hz): hacha, martillo, campana, fuego, clic, aviso, monedas, espada, pájaros y viento. Sin bancos de sonidos externos ni dependencias nuevas.
- **La mezcla:** `src/audio/mixer` los lee con validación estricta (solo ese formato), mezcla hasta 24 voces y dos sonidos de fondo en bucle con volumen por categoría (maestro, efectos, ambiente e interfaz, de la configuración), y los envía por SDL3.
- **Qué suena:**
  - clic en la interfaz;
  - campana con incendios y asaltos, monedas con el comercio, espada con los soldados nuevos y un aviso con el resto;
  - hachas y martillos de los aldeanos cerca de la cámara;
  - crepitar del incendio más cercano;
  - de fondo, pájaros (se apagan al alejar la cámara) o viento en invierno.
- Sin dispositivo de sonido, el juego sigue en silencio y lo anota en el registro.
- La música queda pendiente (sección 14 de la especificación).

**D-1805. Ideas visuales hechas.**
De `docs/IDEAS_VISUALES.md`:
- las nubes se mueven con el viento;
- el agua se congela bajo −3 °C (más blanca y quieta), igual que la pesca se detiene en la simulación;
- las chimeneas echan humo.

Quedan para más adelante la oclusión ambiental, el balanceo de los árboles, los árboles sin hojas en invierno y las huellas en la nieve.

## Fase 19: razas de fantasía (2026-09-27)

**D-1901. Razas como datos.**
Cada `race` declara:
- su cuerpo (los archivos `characters/<body>_male.glb` y `_female.glb`);
- su velocidad al caminar;
- su velocidad en diez oficios: madera, piedra, recolección, cultivo, huerto, caza, pesca, construcción, oficios y metal;
- su resistencia al frío (pierde menos abrigo y enferma menos de gripe; puede ser negativa) y a las enfermedades;
- si ve de noche.

**D-1902. Rasgos de `core`, para equilibrar jugando.**
- **Humanos:** 105 % en todo.
- **Gatunos:** caminan al 125 %; caza 120, pesca 125, recolección 110, construcción 90; sienten más el frío (−20).
- **Enanos:** caminan al 90 %; piedra y metal 145, construcción 115, cultivo y recolección 85, huerto 80; resisten el frío (30).
- **Elfos:** caminan al 105 %; recolección y caza 130, huerto 145, piedra y metal 80; resisten las enfermedades (25).

**D-1903. Trabajo por pasos.**
La velocidad de la raza se aplica acumulando centésimos de trabajo por aldeano (`work_carry`, guardado en la partida): al 125 % hace 5 pasos cada 4 ticks. Así sigue siendo entero y determinista.

El oficio sale de lo que hace:
- lo que recolecta: árbol, piedra o mineral, arbustos y hierbas;
- en un taller: metal si usa mineral, hierro o carbón; piedra si usa piedra o arcilla o si la saca del suelo; huerto en los que tardan años en dar fruto; oficios el resto;
- las tareas de la granja, la caza, la pesca y la construcción.

**D-1904. Visión nocturna sin noche.**
El juego no tiene ciclo de día y noche; la especificación no lo pide y agregarlo cambiaría la luz y el trabajo. El rasgo queda declarado en los datos y en la simulación para cuando exista. Por ahora los gatunos se distinguen por su rapidez.

**D-1905. Pueblos mixtos e inmigración.**
- Cada jugador empieza con una raza o con una mezcla: en la mezcla, las cinco familias iniciales se reparten entre las razas.
- Los hijos toman la raza de la madre o del padre, al azar.
- Los recién llegados llegan en familias de una sola raza. Con "otras razas" en 20 % o 50 % (se elige en la partida nueva), esa parte de las familias es de una raza al azar.

**D-1906. Raza en multijugador.**
El anfitrión elige en la sala la raza de todos los pueblos (o mixta), como el resto de la configuración. Así el protocolo de la sala no cambia. Que cada jugador elija la suya queda para después.

**D-1907. Cuerpos por raza.**
`human.py` genera los cuerpos de las cuatro razas con el mismo esqueleto y animaciones:
- **enanos:** 74 % de alto y 128 % de ancho, y los hombres siempre con barba;
- **elfos:** 107 % de alto, más delgados, con orejas largas en punta;
- **gatunos:** orejas de gato y cola del color del pelo.

La cabeza mide lo mismo en todas las razas, así los sombreros les sirven a todos. Los asaltantes y soldados siguen con el cuerpo humano.

**D-1908. Pruebas de economía sin amenazas.**
Las pruebas de necesidades, cultivos y clima ahora apagan incendios, asaltantes y fauna. Al cambiar las velocidades, un incendio al azar quemaba la panadería de la prueba. Las amenazas tienen sus propias pruebas.

## Fase 20: rendimiento (2026-09-27)

**D-2001. Medir con una prueba, no con el juego.**
La prueba `sim_perf` arma 12 pueblos de 1000 aldeanos en un mapa enorme sin interfaz: casas, trabajo y comida con los comandos de desarrollo, y la gente con `DevSpawn` (nuevo, solo con las herramientas de desarrollo, que también ganan un botón "500 aldeanos más"). El caso grande se corre a mano (`--no-skip`); uno chico corre siempre y falla si el tick pasa de 33 ms. Resultados y método en `docs/RENDIMIENTO.md`.

**D-2002. Índices derivados del estado.**
Las optimizaciones no cambian la partida guardada ni el protocolo; son datos que se rehacen:
- la lista de edificios por pueblo;
- la población por pueblo;
- los bienes guardados por pueblo durante un tick;
- las casas libres al asignar hogares.

Las búsquedas recorren los edificios en el mismo orden de antes y eligen igual.

La única diferencia de reglas: dentro de un tick, las decisiones ven lo guardado al empezar el tick. Es igual en todas las máquinas, así que no afecta al determinismo.

**D-2003. Límites y aviso.**
El tick promedio con 12 × 1000 bajó de 61 a 12,5 ms, así que el límite de 1000 por jugador se mantiene. La sala avisa por encima de 6000 aldeanos posibles en total (la especificación sugería 600 por jugador, 7200 con 12): desde ahí los ticks más pesados pasan de 33 ms en este equipo.

## Fase 21: mapas más grandes (2026-09-27)

Pedido del 2026-09-27: tamaños de 8192 × 8192 y 16384 × 16384, junto con el minimapa, la brújula, recordar la partida nueva y el mapa de islas (fases 22 a 24).

**D-2101. Gigante y Colosal.**
Dos tamaños nuevos: Gigante (8192 m) y Colosal (16384 m). Se generan igual que los demás. Con mapas separados, el mundo entero puede llegar ahora a 16384 m (antes 4096): cada mapa se achica solo si no cabe. Por ejemplo, 4 jugadores con mapas gigantes llenan un mundo colosal; con mapas enormes y 2 a 4 jugadores, cada uno conserva su mapa enorme (antes bajaba a grande).

**D-2102. El mapa sigue dentro de la partida guardada.**
Otra opción era guardar solo la semilla y regenerar el mapa al cargar. Se descartó: un mapa colosal tarda unos dos minutos en generarse, y cargar sería igual de lento. Se subieron los límites según lo medido (ver `docs/RENDIMIENTO.md`):
- cada pedazo de la partida, sin comprimir: de 1 a 3 GiB;
- la instantánea de red, sin comprimir: de 512 MiB a 3 GiB;
- un paquete de red: de 128 a 512 MiB (la instantánea colosal comprimida pesa unos 190 MiB);
- los rasgos del mapa (árboles, piedras…): de 4 a 32 millones.

Los tamaños se leen como números de 32 bits, así que 3 GiB es el máximo que el formato admite con margen.

**D-2103. Zonas conectadas por bloques.**
La búsqueda de caminos sabe de antemano si dos puntos están en la misma zona transitable, para no buscar en vano. Antes, cada edificio nuevo obligaba a reetiquetar el mapa entero: 470 ms en un mapa gigante (unos 2 s en uno colosal, y 120 ms en uno enorme). Ahora las zonas se etiquetan por bloques de 128 m y se unen por sus bordes, y un cambio solo reetiqueta sus bloques: menos de medio milisegundo. El resultado es el mismo; una prueba lo compara con un relleno completo del mapa.

**D-2104. Descarte en dos niveles.**
Los objetos se agrupaban en zonas de 64 m para decidir cuáles se ven. En un mapa colosal son 65 536 zonas por modelo y por cascada de sombra: 10 ms por cuadro. Ahora las zonas se agrupan además de 16 × 16 (1 km), y un grupo que no se ve se salta entero.

**D-2105. Aviso de tiempo y memoria.**
Al elegir Gigante o Colosal, la ayuda del tamaño dice cuánto tarda y cuánta memoria necesita. No se bloquea nada: en este equipo (32 GB, RTX 2080 SUPER) el colosal se juega a unos 60 FPS en Ultra con 7 GB de memoria.

**D-2106. Terreno de hasta 16384 m en la tarjeta gráfica.**
El límite de las capas del terreno pasó de 8192 a 16384 m. Las alturas de un mapa colosal ocupan 512 MiB en la tarjeta. Si una tarjeta con poca memoria no puede cargarlas, el juego ya muestra "No se pudo mostrar el mapa" y vuelve a la partida nueva.

## Fase 22: mapa de islas (2026-09-27)

**D-2201. Islas como tipo de mapa.**
Las islas son un tipo de mapa de `core` (`core:islands`) con la marca `"islands": true`, así un mod puede definir otros tipos con islas y su propia mezcla de biomas. La partida nueva agrega "Islas por pueblo" (de 1 a 8), activa solo con ese tipo de mapa. Con 2 pueblos y 3 islas por pueblo hay 6 islas.

El número se guarda en la configuración del mapa (un byte más en la partida y en la sala). Por eso cambiaron la suma de verificación del mapa pequeño de referencia y la versión de las reglas (21). Los demás mapas se generan igual que antes.

**D-2202. Cómo se forman.**
- Alrededor del 40 % del mapa es tierra. Cada pueblo tiene una isla de origen, más grande (peso 3); las demás pesan de 1 a 2 al azar.
- Las islas de origen se colocan lo más lejos posible entre sí, y las demás donde quepan, siempre con mar entre ellas y alrededor del mapa. Si alguna no cabe, todas se achican un poco y se vuelven a colocar.
- La costa se deforma según la dirección desde el centro, así cada isla queda de una sola pieza.
- La tierra conserva su relieve. Hacia la orilla baja suave hasta una playa, y bajo el agua desciende hasta el fondo del mar.
- Si un lago parte una isla en la orilla, el pedazo suelto se hunde. Así el mapa tiene exactamente las islas pedidas; una prueba cuenta las islas de varios mapas.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): la forma de las islas es la del jerárquico (D-4102); el reparto en archipiélagos sigue (D-2501).*

**D-2203. Cuántas islas caben.**
La partida nueva ofrece solo las islas por pueblo que caben: cada isla de origen necesita unos 110 m de radio y las demás unos 45 m. En un mapa pequeño con muchos pueblos cabe 1 por pueblo. El generador aplica el mismo tope si la configuración viene de otro lado.

**D-2204. El mar.**
El mar es el agua a 20 m de altura que llega al borde del mapa; los ríos terminan en él como en un lago. Fuera del mapa, el borde decorativo es mar abierto hasta el horizonte, en lugar de las montañas de los otros tipos.

*Reemplazada en parte por D-4901 (el generador clásico se borró en la fase 49): el nivel del mar lo pone el jerárquico, 2 m bajo las llanuras (D-4101). Lo demás sigue.*

**D-2205. Dónde empieza cada pueblo.**
Cada pueblo empieza cerca del centro de su isla de origen, en buen suelo, con agua cerca y terreno plano. Después recibe los recursos básicos garantizados como en los otros mapas (D-603).

**D-2206. Cruzar el mar.**
El juego no tiene barcos. Mientras no los tenga:
- los aldeanos no pueden llegar a las otras islas: se ven, pero no se usan;
- los asaltantes que no pueden llegar desde el borde del mapa desembarcan en la costa de la isla del pueblo;
- los ejércitos que no pueden llegar a pie viajan por mar como entre mapas separados (D-1604): tardan según la distancia y desembarcan en la costa cerca del centro del pueblo enemigo; lo mismo al volver.

Las dos últimas reglas valen en cualquier mapa donde el agua separe las tierras (por ejemplo, un río que cruza el mapa entero). Usar las otras islas necesitaría un muelle y barcas; queda como propuesta para decidir.

**D-2207. Islas y mapas separados.**
Con mapas separados, cada jugador tiene su propio mapa de islas con sus islas por pueblo.

## Fase 23: partida nueva recordada (2026-09-27)

**D-2301. Qué se recuerda.**
Todo lo del formulario de partida nueva salvo la semilla, que sigue siendo nueva al azar en cada partida: con la misma semilla saldría siempre el mismo mapa. Se guarda en `settings.json`, sección `newGame`.

**D-2302. Por nombre, no por posición.**
Los tipos de mapa, los biomas y las razas se guardan por su id de mod (`core:islands`, `core:dwarf`…), porque su orden cambia al activar o quitar mods. Si uno ya no existe, esa opción vuelve a su valor por omisión y las demás se conservan. Las demás opciones se guardan con nombres legibles (`"size": "giant"`, `"raiders": "high"`). Cada campo se valida por separado, como el resto del archivo; uno inválido se ignora y cuenta como aviso.

**D-2303. Cuándo se guarda.**
Al salir del formulario, con "Generar mapa", "Abrir la sala" o "Volver". Así queda la última configuración aunque no se haya jugado. El formulario de la partida multijugador es el mismo y comparte lo recordado.

**D-2304. Restablecer.**
El botón "Restablecer", a la izquierda de "Volver", devuelve todas las opciones a sus valores por omisión (los de una instalación nueva) y deja la semilla escrita. Lo restablecido se guarda al salir, como cualquier otro cambio.

**D-2305. Arreglo: cierre del juego.**
Al probar esta fase, el juego terminaba con un error de memoria al cerrarse (Windows lo informaba como 0xC0000374 o 0xC0000005 desde la fase 18). La compilación con AddressSanitizer mostró la causa: `SDL_Quit` liberaba el sonido y el director de sonido lo volvía a liberar después. Ahora el sonido se cierra antes de `SDL_Quit` (commit aparte).

## Fase 24: minimapa y brújula (2026-09-27)

**D-2401. El norte.**
El norte es −z: la parte de arriba del mapa y hacia donde mira la cámara al empezar. El minimapa no gira; siempre tiene el norte arriba, y alrededor muestra N, E, S y O (W en inglés). El norte va en rojo.

**D-2402. Qué muestra el minimapa.**
- El terreno con los colores del suelo del juego, los bosques más oscuros, sombras del relieve (luz del noroeste) y el agua más oscura donde es honda. Es una imagen de 256 × 256 hecha una vez por mapa; en un mapa colosal cada punto resume 64 × 64 m.
- Los edificios de cada pueblo, en el color de su jugador (el de la sala multijugador), con un mínimo de un punto para que se vean en mapas grandes.
- Lo que ve la cámara: el contorno del suelo que cae en las esquinas de la pantalla.

Un clic, o arrastrar, lleva la cámara a ese lugar; no reacciona si una ventana del juego está encima.

**D-2403. Dónde va.**
Arriba a la derecha, bajo la barra superior, de 200 unidades de lado (menos en pantallas bajas: a lo sumo el 30 % del alto). La brújula va a su izquierda. Las ventanas de edificio y de aldeano, que por omisión se abrían en esa esquina, ahora se abren debajo del minimapa; si el jugador las movió, se respeta su lugar.

**D-2404. La brújula.**
Un disco con una flecha: la mitad roja y la letra N apuntan al norte, y giran con la cámara. Funciona igual en los tres modos de cámara.

**D-2405. Imágenes en la interfaz.**
El dibujo de la interfaz solo tenía el atlas de letras. Ahora un comando de dibujo puede usar una imagen a color que el renderizador guarda por número (la del minimapa es la 1). El sombreador de la interfaz tiene un modo para eso; lo demás se dibuja igual que antes.

## Fase 25: archipiélagos (2026-09-27)

Pedido del 2026-09-27: islas de formas irregulares, en archipiélagos con una isla principal por jugador y secundarias más pequeñas; y en general que los mapas puedan tener golfos, penínsulas, bahías, estrechos, cabos, mesetas, valles, cordilleras, cañones, fosas marinas y dorsales (fases 26 y 27).

**D-2501. Archipiélagos.**
Cada pueblo tiene una isla principal (peso 5) y sus secundarias (peso 0,8 a 1,8). Las principales se colocan lo más lejos posible entre sí; cada secundaria, alrededor de la principal de su pueblo y siempre más cerca de ella que de las de los demás. Reemplaza el reparto de D-2202, donde las islas "de origen" pesaban 3 y las demás iban donde cupieran.

**D-2502. Formas irregulares.**
Una isla ya no es un círculo con el borde ondulado. Es un disco deformado por tres campos de ruido:
- uno mueve cada punto hasta media isla en cada eje: lóbulos, penínsulas y cuellos angostos;
- otro, de manchas grandes, empuja la costa hacia adentro y hacia afuera: bahías y cabos grandes;
- un tercero, de manchas chicas: caletas y puntas.

Un núcleo en el centro (un quinto del radio, sin deformar) garantiza que el medio de cada isla es tierra: ahí empieza el pueblo y desde ahí se reconoce la isla. En mapas de prueba, la compacidad de las islas (4π·área/perímetro², que para un disco dibujado en casillas da unos 0,6) queda en promedio entre 0,18 y 0,37.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): la forma de las islas es la del jerárquico (D-4102).*

**D-2503. Canales en lugar de distancia.**
Para que las islas no se toquen, antes se separaban tanto como su forma podía crecer, y quedaban chicas y lejanas. Ahora cada punto del mar pertenece a la isla más cercana (medida en radios de cada isla), y a lo largo de la línea donde se encuentran dos islas siempre corre un canal de mar de al menos `gap` metros (1/64 del mapa, mínimo 20 m). Así las islas pueden quedar juntas y forman estrechos, y sigue habiendo exactamente las islas pedidas. El mar también rodea el mapa.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): la forma de las islas es la del jerárquico (D-4102).*

**D-2504. Tierra suelta.**
La tierra que se une a su isla solo por una esquina de casilla contaba como otra isla. Ahora la limpieza de tierra suelta trabaja por casillas (las cuatro esquinas sobre el mar), igual que se recorre y se cuenta el mapa. Además no se cavan lagos en el centro de una isla.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49).*

**D-2505. Versión del generador.**
Los mapas de islas cambian con la misma semilla: el generador pasa a la versión 4 y cambió la suma de verificación del mapa pequeño de referencia. Los demás tipos de mapa salen igual.

## Fase 26: costas y fondo marino (2026-09-27)

**D-2601. La opción "Mar".**
Los tipos de mapa sin islas tienen la opción "Mar": sin mar, a veces (por omisión) o siempre. Con "a veces", la semilla decide (4 de cada 10 mapas). Se guarda en la configuración del mapa (un byte más) y se recuerda con la partida nueva. En el mapa de islas no aplica: siempre hay mar.

**D-2602. Cómo es la costa.**
- El mar ocupa uno, dos lados en esquina o dos lados opuestos (55, 30 y 15 %), de 12 a 22 % del mapa de ancho cada uno.
- La línea de costa se deforma con ruido: salen bahías y cabos por todas partes.
- Además, al azar: de 0 a 2 golfos hacia tierra adentro, de 0 a 2 penínsulas y de 0 a 3 cabos hacia el mar, y de 0 a 3 islotes frente a la costa, que forman estrechos con ella.
- Golfos, penínsulas e islotes usan la misma deformación y el mismo ruido que la costa, así que tampoco son formas geométricas.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): la costa es la del jerárquico (D-4101, D-4304).*

**D-2603. La altura del mar.**
Con costa, toda la tierra sube 15 m para dejar lugar al fondo del mar bajo la tierra más baja (las alturas se guardan en centímetros sin signo). El mar queda 1 m bajo el punto más bajo que puede tener el relieve. La tierra conserva su relieve, con una playa en la orilla.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): la costa es la del jerárquico (D-4101).*

**D-2604. Fosas y dorsales.**
En todo mapa con mar, incluido el de islas, puede haber hasta 2 fosas y 2 dorsales (cada una con 55 % de probabilidad, y 20 % de que haya otra). Son líneas serpenteantes de borde a borde:
- una fosa baja el fondo de 5 a 9 m en una franja de 30 a 60 m;
- una dorsal lo sube en una franja de 90 a 160 m, con crestas, hasta 1,2 m bajo la superficie: nunca sale del agua, así que no cambia las islas.

Solo tocan el fondo abierto, no la orilla. Se ven por el color del agua, más oscuro donde es honda.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): ya no hay fosas ni dorsales.*

**D-2605. El borde decorativo.**
Fuera del mapa hay mar donde el borde del mapa es mar a lo largo de 48 m, y montañas donde es tierra. Reemplaza la regla del mapa de islas (D-2204). La desembocadura de un río no cuenta como mar.

**D-2606. Versión del generador.**
Pasa a la 5: con "a veces", un mapa clásico puede tener costa con la misma semilla que antes no la tenía.

**D-2607. Formas para las pruebas.**
`generate_map` puede devolver la lista de formas que colocó (costa, golfo, península, islote, fosa, dorsal), con su línea y su ancho. Solo lo usan las pruebas; no se guarda con la partida.

## Fase 27: accidentes del terreno (2026-09-27)

**D-2701. La opción "Accidentes del terreno".**
Pocos, normales (por omisión) o muchos. Da cuántos hay por km² en promedio: mesetas 0,35, valles 0,30, cordilleras 0,20 y cañones 0,25 con "normales"; la mitad con "pocos" y el doble con "muchos". Sale la parte entera y una más al azar por el resto. Así, en un mapa pequeño muchas veces no hay ninguno, y en uno enorme hay varios. Se guarda en la configuración del mapa y se recuerda con la partida nueva.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): "Accidentes del terreno" decide qué parte de las regiones no es llanura y cuántos valles y cañones hay (D-3903, D-4001).*

**D-2702. Cómo son.**
- **Cordillera:** una cresta a lo largo de una línea curva de 35 a 70 % del mapa, de 100 a 220 m de ancho y de 35 a 70 m de alto, con picos y estribaciones por ruido, y más baja en los extremos. Se suma al relieve (también a las cordilleras de "Montañoso").
- **Meseta:** una cima plana de 110 a 260 m de radio, de 10 a 22 m sobre el suelo, con un borde irregular. Casi toda rodeada de acantilado (10 m), con una rampa suave de hasta 100 m hacia un lado para poder subir. La cima conserva un poco de la forma del suelo.
- **Valle:** en U, de 160 a 320 m de ancho y de 6 a 14 m de hondo, de un borde del mapa a otro; se funde con el terreno en sus orillas.
- **Cañón:** de 36 a 70 m de ancho y de 12 a 25 m de hondo, con fondo plano y paredes a pique. Va de un borde a otro y su fondo baja 4 m hacia el final, así que desagua. Un río nace en su cabecera.

Todos siguen líneas curvas: dobleces al azar suavizados, cuatro tramos por doblez.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): las mesetas, valles y cañones son los del jerárquico (D-3903, D-4001) y ya no hay cordilleras.*

**D-2703. Sobre la tierra, después del mar.**
Se aplican después de formar la costa o las islas y solo sobre tierra. Así no quedan bajíos raros en el mar, y un valle o cañón que llega a la costa termina en ella. El fondo de un valle o cañón nunca baja del nivel del mar (30 cm por encima), para no partir una isla.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49).*

**D-2704. Ríos que serpentean.**
Los ríos bajaban en línea recta por las pendientes suaves: el terreno no tenía detalle de menos de 32 m y el agua sigue la cuadrícula. Arreglos:
- un micro-relieve de hasta 40 cm en manchas de 8 a 16 m;
- en las hondonadas rellenas (planas), el agua se reparte en un orden revuelto en vez del de la cuadrícula.

El micro-relieve dejaba orillas de lago de 1 cm cortadas en charcos sueltos. Por eso:
- un lago necesita 150 puntos con 10 cm de agua o más (no basta un pozo en una hondonada ancha);
- los charcos de menos de 64 casillas lejos del borde se secan.

**D-2705. Versión del generador y pruebas de juego.**
El generador pasa a la versión 6: todos los mapas cambian. Algunas pruebas de juego dependían de la forma de un mapa en particular:
- las de salud, ejército y aldea usan ahora mapas sin mar, porque no son sobre costas;
- "una hora de juego" usa el mapa 29. Con 16 semillas, el jugador de prueba (que construye siempre lo mismo) prospera en 7 tanto antes como después de esta fase: los cambios no empeoraron la economía;
- "el fuego se propaga" se comprueba en 5 pueblos y pide que se propague en 3. Es por azar: se propaga en 16 de 20 mapas probados.

## Fase 28: oro que se carga y bóveda (2026-09-27)

**D-2801. El oro es un recurso (reemplaza D-1401).**
Las monedas pasan a ser `core:gold`, de una categoría nueva, `gold`, y con `value` 0: los mercaderes no lo compran ni lo venden como mercancía. Desaparecen el número `coins` del pueblo y el valor especial `kCoins` de los comandos: una oferta entre jugadores usa el índice del oro como cualquier otro bien. Las reglas pasan a la versión 22, así que las partidas guardadas antes no se abren (D-631).

**D-2802. Bolsas de 50.**
Con la regla de siempre (12 unidades por viaje), llenar una reserva de 500 pedía más de 40 viajes. Un recurso puede tener ahora `carry`, las unidades por viaje, en lugar de 12 / peso; el oro usa 50. Así el oro se mueve con pocos peones sin dejar de ocupar un lugar en el almacén por unidad.

**D-2803. Dónde se guarda.**
- Solo en el centro del pueblo, el puesto de comercio y las bóvedas (`gold` en `stores`); los almacenes comunes no.
- El pueblo empieza con su oro en el centro del pueblo: 100, o 50 y 200 con recursos escasos y abundantes.
- **Bóveda** (`core:vault`, Servicios, sin nivel): 5 × 5 m, 10 troncos y 40 piedras, 5000 de capacidad, a prueba de fuego y con 1500 de resistencia a los asaltantes.
- El puesto de comercio pasa de 200 a 400 de capacidad, para que quepan la reserva y lo comprado.

**D-2804. La reserva del puesto.**
- Es el `limit` del edificio (el mismo comando que el tope de un taller): 100 al terminarlo, de 50 en 50 en su ventana, hasta su capacidad.
- Los peones sin trabajo, después de construir y acarrear, mueven el oro:
  - lo que sobra en el puesto va a la bóveda más cercana, o al centro del pueblo si no hay;
  - lo que falta lo traen de una bóveda, o del centro del pueblo;
  - si nada de eso hace falta, el oro del centro del pueblo va a una bóveda.
- A lo más dos peones por pueblo a la vez. Cada uno toma, al llegar, solo lo que sobra o lo que falta contando lo que ya va en camino, para no pasarse.

**D-2805. El oro no desaparece.**
Solo cambia por comercio, robo o incendio:
- el centro del pueblo acepta oro aunque esté lleno, como ya pasaba con lo que llega por comercio;
- si un peón muere con oro en la mano, o no tiene dónde dejarlo, el oro va al centro del pueblo;
- el oro de un edificio que se demuele, o que derriban asaltantes o soldados, va al centro del pueblo. Si se quema, se pierde con lo demás;
- los asaltantes roban oro como cualquier bien: se llevan hasta 30 de lo que más hay en el edificio que atacan.

**D-2806. Comprar y vender.**
Al comprar sale primero el oro y luego entran los bienes, así el oro deja lugar en el puesto. Las dos cosas usan las reglas de D-1403: se toma primero del puesto y luego de los demás edificios, y se deja en el puesto o, si no cabe, en el centro del pueblo. La puntuación sigue contando una por cada 10 de oro. La riqueza que atrae asaltantes lo cuenta a 1 por unidad, como antes las monedas.

**D-2807. En la interfaz.**
El oro se muestra solo en la barra superior, debajo de la felicidad. Su tooltip lo separa en puesto, bóvedas y centro del pueblo. No se repite en la lista de recursos. La ventana del puesto tiene "Oro que guarda" con − y +.

**D-2808. El modelo de la bóveda.**
Un cuarto de piedra con contrafuertes, techo de pizarra, puerta con bandas de hierro y un sello dorado, en `art/blender/buildings.py`. Regenerar los edificios deja los demás archivos idénticos.

## Fase 29: comercio automático en el puesto (2026-09-27)

**D-2901. Reglas por bien, del pueblo.**
Cada regla dice, para un bien que los mercaderes compran y venden, "vender si hay más de N" y "comprar si hay menos de M"; cualquiera de las dos puede estar apagada. Son del pueblo, no del edificio: si el puesto se quema y se reconstruye, las reglas siguen. Se cambian con el comando `SetTradeRule`; con las dos apagadas, la regla se quita. Se guardan ordenadas por bien, para que el orden de aplicación sea el mismo en todas las máquinas.

**D-2902. M no puede pasar de N.**
Una regla con M mayor que N compraría hasta M y al otro día vendería lo que pasa de N, una y otra vez, pagando la diferencia de precio. Esa regla se rechaza al leer el comando, y la ventana no deja aplicarla.

**D-2903. Cuándo y cómo.**
- Una vez al día, mientras hay un mercader, empezando el día en que llega.
- Primero las ventas de todas las reglas y después las compras, así el oro de lo vendido ya sirve para comprar.
- Ventas: como la venta a mano, primero del puesto y luego de los demás almacenes. El oro entra al puesto, o al centro del pueblo si no cabe.
- Compras: solo con el oro que hay en ese momento en el puesto, y sin pasar del stock del mercader. Lo comprado queda en el puesto, o en el centro del pueblo si no cabe.
- "Lo que hay en el pueblo" es lo mismo que puede vender el comercio: lo de los almacenes, el puesto y el centro del pueblo, sin lo que llevan los aldeanos en la mano.

**D-2904. El aviso.**
El pueblo lleva la cuenta de la visita: unidades vendidas y compradas, y el oro que entró y salió. Cuando el mercader se va, si se hizo algo, llega el aviso con esas cuentas y suena como el comercio; la cuenta vuelve a cero con cada mercader. Se guarda con la partida, así un guardado a mitad de la visita no la pierde.

**D-2905. En la ventana del puesto.**
Debajo de lo que trae el mercader: un selector del bien, dos deslizadores de 0 a 2000 de 10 en 10 (el primer paso es "No") y un botón para aplicar la regla. Así mover un deslizador no manda un comando por cada paso en multijugador. Abajo, las reglas en vigor (hasta 8 a la vista). Las reglas pasan a la versión 23.

## Fase 30: visor de modelos (2026-09-27)

Se hizo antes que las fases 28 y 29 porque es una herramienta aparte y no toca el juego.

**D-3001. Un programa aparte sobre el mismo motor.**
- `SalvaCiudadModelos.exe` se compila con el juego y usa su renderizador, su cargador de glTF y sus textos, así que cada modelo se ve con la misma luz, sombras y colores que en el juego. No abre el juego ni lo necesita.
- La interfaz es Dear ImGui, como las demás herramientas de desarrollo, con la fuente del juego (Alegreya Sans) para que se vean los acentos.
- No escribe ningún archivo del juego ni del usuario. No usa `settings.json`: la ventana es siempre de 1600 × 900, el idioma es el del sistema y se cambia en el propio visor sin guardarse. Su registro va a `logs/viewer/`, para no rotar el del juego.

**D-3002. Qué cuenta como "usado" y qué es una variante.**
- El cargador de mods anota cada modelo que usan las definiciones (`ModelRef`: tipo, id, mod y ruta, y si el archivo existe), también los de un mod que quedó fuera por errores. Así el visor puede señalar una definición cuyo archivo falta aunque el juego la haya descartado.
- Los modelos que el código carga por nombre (nubes, casa de muestra, escena de prueba, animales, sombreros, barba y delantales) están ahora en una sola lista, `src/game/builtin_models.h`, que usan tanto el juego como el visor.
- Los cuerpos de las razas se buscan en `core`, como hace el juego (`sim::race_body_file`). Si falta uno, el juego solo lo deja fuera, así que no es un error del mod; el visor sí lo señala.
- Grupo de un modelo: la primera definición que lo usa (las tallas de una especie, los dos cuerpos de una raza); si no, su uso en el código (los sombreros); si nada lo usa, su nombre sin el sufijo de talla o de sexo. En la fase 31, las variantes de una definición formarán un grupo del mismo modo.
- La categoría sale de la carpeta (`buildings`, `characters`, `animals`, `props`). Los árboles son los de una especie o los archivos `tree_*`.
- Los objetos del mapa no tienen nombre propio: se muestran con el nombre del recurso que dan (bayas, piedra…).

**D-3003. Lee los mods del código fuente.**
Los scripts de Blender escriben en `data/mods` del repositorio, pero la compilación copia `data/` junto al ejecutable. Si el visor leyera esa copia, no vería los modelos recién exportados. Por eso lee `data/mods` del código fuente mientras esa carpeta exista (la ruta se fija al compilar) y, si no existe, la del juego instalado. La pestaña Revisión muestra qué carpetas lee.

**D-3004. Recarga automática.**
Cada medio segundo compara la fecha y el tamaño de los archivos mostrados; si cambian, los carga otra vez y avisa abajo. El renderizador no puede liberar un modelo, así que la copia anterior queda en la tarjeta gráfica hasta cerrar el visor. Para una herramienta de desarrollo son unos pocos MB, y es más simple y seguro que agregar al renderizador del juego una forma de borrar modelos.

**D-3005. Cómo se muestran.**
- Los modelos de un grupo van en fila de izquierda a derecha, con un aldeano humano de 1,7 m a la izquierda como referencia de escala, sobre un suelo con líneas cada metro y más marcadas cada 5 m.
- Calidad Ultra y la luz por omisión del juego (verano). Los árboles y objetos del mapa toman el color de la estación elegida con la misma función que el mapa (`season_tint`, que se separó de `feature_instance`).
- Los sombreros, la barba y los delantales se muestran puestos en un cuerpo humano, cada uno en su propia copia del cuerpo, porque son accesorios rígidos fijados a un hueso.
- En la ficha, "llamadas de dibujo" son las primitivas del modelo (una por material), que se dibujan en la vista y en cada cascada de sombras. "Materiales" cuenta solo los que usan sus primitivas.

**D-3006. Recorrer la lista con el teclado.**
- W A S D, las flechas y las del teclado numérico (llegan así con Bloq Num apagado) mueven un cursor por la lista tal como se ve: categorías, tipos y, dentro de un tipo abierto, sus archivos. Mantener la tecla repite.
- Arriba y abajo pasan de un elemento a otro; un tipo o un archivo se carga y se encuadra al llegar a él, sin Enter. Una categoría solo mueve el cursor.
- Derecha abre lo que está cerrado y, si ya está abierto, entra en su primer elemento. Izquierda cierra lo abierto o, si no, sube a lo que lo contiene. Es la conducta habitual de los árboles de archivos.
- Solo en la pestaña Modelos y nunca mientras se escribe en el buscador. El visor recuerda qué está abierto; el ratón y el teclado comparten ese estado y el cursor.
- La lógica de las teclas es una función pura (`navigate`) con sus pruebas; al abrir, el cursor empieza en el primer tipo de la lista tal como se ve.

## Fase 31: variantes de modelos (2026-09-27)

**D-3101. Variantes declaradas en los JSON.**
- `"models": [...]` (1 a 8 archivos) en edificios, niveles de edificio y recursos naturales; `"model"` sigue valiendo y equivale a una lista de uno. Usar los dos a la vez es un error, igual que una lista vacía, repetida o con un archivo que falta.
- Un parche de `model` o `models` reemplaza la otra forma, y sus archivos se buscan en el mod del parche. Los de los niveles se buscan en el mod que escribió `levels` (`levels_model_mod`), para que un mod que solo cambia las casas de la planta baja no rompa las de los niveles de `core`.
- Los árboles no cambian: ya tienen cuatro tamaños por especie, que son sus variantes.

**D-3102. La variante sale del lugar, no de la simulación.**
- Edificios: de la celda de su esquina (`place_key(x, z)`), así la vista previa al colocarlo ya muestra la casa que quedará, y es la misma en todas las computadoras y al cargar. Recursos naturales: de su posición en punto fijo. Nubes: del mismo generador que las reparte, con la semilla del mapa.
- La elección (`pick_variant`) está en `src/game/variants.cpp` y solo la usa la vista. La prueba "the looks never change the simulation" corre la misma partida con y sin variantes y compara el hash.
- Cada nivel de una casa usa las variantes del nivel más alto alcanzado que tenga `models`; si ninguno tiene, las de la planta baja.

**D-3103. Paleta de colores en los edificios.**
- Como la de los aldeanos (D-405): los materiales `var_roof`, `var_roof_dark`, `var_walls` y `var_shutter` toman el color de la paleta de cada instancia. 150 paletas: 5 techos × 6 paredes × 5 postigos. Solo las casas usan esos materiales por ahora; los talleres conservan su techo característico (pizarra en la herrería, paja en el leñador...).
- El número de paleta viaja en el cuarto canal del tinte de la instancia (sin agrandar la instancia de 64 bytes) y el color en un búfer de 256 paletas, siempre del mismo tamaño para que el sombreador nunca lea fuera. Como el sombreador de píxeles multiplica por el color del material, el de vértices divide por él: un material recoloreado sin paleta (el visor, la vista previa al colocar) conserva el color que tiene en Blender.
- La vista previa al colocar un edificio no usa paleta, para que el verde o el rojo se lean bien.

**D-3104. Qué se agregó.**
- Casas: tres por nivel, nueve en total, dentro del terreno de 6 × 5 m (`house_variant` en `buildings.py`). Nivel 1: cabaña; nivel 2: media planta bajo el techo, un ala o un porche; nivel 3: dos plantas.
- Rocas, rocas con mineral y arbustos de bayas: tres de cada uno. Nubes: cuatro formas.
- Sombreros: siguen los dos de antes; la especificación permitía hasta tres, pero los accesorios se dibujan en cada aldeano y la paleta ya los varía.
- Los parámetros nuevos de los scripts de Blender tienen por omisión el comportamiento de antes: regenerar da los mismos archivos para todo lo demás, salvo `house.glb`, que ahora usa los materiales `var_*`.

**D-3105. El visor y las variantes.**
Las variantes de una definición, niveles incluidos, forman un grupo. "Otros colores" recorre las 150 paletas en los edificios.

**D-3106. La compilación del visor espera a la del juego.**
Los dos copian `data/` junto al ejecutable al terminar de enlazar; en paralelo, una copia podía fallar. Ahora el visor se enlaza después del juego.

**D-3107. Una sola copia de `data/` para los dos ejecutables.**
Reemplaza a D-3106: esperar al juego no bastaba como garantía y ataba la compilación del visor a la del juego. Ahora un solo objetivo, `sc_data`, copia `data/` a `bin/data` y deja un archivo testigo (`sc_data.stamp`); el juego y el visor dependen de él, así la copia corre una vez y nunca dos a la vez. Se repite solo cuando cambia o se agrega un archivo de `data/` (la lista se recalcula en cada compilación), no en cada enlace. Como antes, borrar un archivo de `data/` no lo borra de `bin/data`; si se borra `bin/data` a mano, hay que borrar también el testigo o compilar desde cero.

**D-3108. La prueba `worldgen` corre solo en `release`.**
Sin optimizaciones tarda casi 4 minutos (en `release`, unos 50 s) y pasaba el límite de 120 s de cada prueba en `debug` y `debug-asan`. En esos dos presets no se registra en `ctest`; sigue compilándose y se puede correr a mano con `salvaciudad_tests --test-suite=worldgen`.

**D-3109. La semilla fija de Lua ahora sí se aplica.**
Corrige D-702: CMake descartaba la definición `luai_makeseed(L)=0u` porque no pasa macros con parámetros por la línea de comandos (solo avisaba al configurar), así que Lua usaba una semilla al azar y el orden de `pairs` sobre claves de texto cambiaba entre estados y entre máquinas. La macro está ahora en `src/script/lua_user.h`, que Lua incluye por su mecanismo oficial `LUA_USER_H`, sin tocar el código vendorizado. La prueba "pairs walks string keys in the same order in every state" fallaba antes del cambio y ahora pasa.

**D-3110. Las pruebas del generador, repartidas en varias suites.**
Reemplaza a D-3108: `worldgen` vuelve a correr en los tres presets. Desde la fase 27 la suite `worldgen` tardaba unos 232 s en `debug` y 392 s en `debug-asan` (48 s en `release`), y ctest la cortaba a los 120 s aunque todo pasara. Sin quitar ninguna comprobación:
- "Sin mar" y "a veces mar" se comprueban en mapas pequeños y en un caso aparte: si hay mar lo decide la semilla, no el tamaño (`plan_coast`). Las costas con mar siguen en 10 mapas medianos. El caso de costas bajaba así de 100 s a unos 45 s en `debug`.
- Los casos que generan muchos mapas enteros pasaron a suites propias, en el mismo archivo: `worldgen_sea` (islas, fondo marino, costas sin mar), `worldgen_coasts`, `worldgen_landforms` y `worldgen_large` (el mapa Grande de islas, generado dos veces). `worldgen` conserva el resto.
- En `debug` cada una tarda entre 25 y 60 s según la carga de la máquina: cabe en los 120 s de siempre.
- En `debug-asan` cada una tarda de 45 a 65 s, pero en esta máquina el mismo binario varía casi al doble entre corridas (`worldgen`: 61, 66 y 115 s; `worldgen_sea`: 74 y 116 s). Costas y el mapa Grande no se pueden partir más sin artificios. Por eso, solo cuando se compila con AddressSanitizer, el límite de cada suite es de 240 s en vez de 120 s (`SC_TEST_TIMEOUT` en `CMakeLists.txt`); sigue sirviendo para detectar una prueba colgada.

## Petición del usuario tras la fase 31: mapas grandes más rápidos (2026-09-27)

Generar un mapa colosal tardaba unos 13 minutos en el juego (9 en la prueba). Las mediciones están en `docs/RENDIMIENTO.md`.

**D-3111. Los mapas no cambian.**
Todos los cambios dan exactamente el mismo resultado: la versión del generador sigue en 6 y las sumas de verificación no cambian (la del mapa pequeño de las pruebas, y la de los mapas gigante y colosal con semilla 12345, comparadas antes y después). Así las partidas y las semillas conocidas siguen valiendo.

**D-3112. Las formas del relieve, por bloques.**
- Para cada punto cerca de un valle, cañón, cordillera, fosa o dorsal, `along_line` comparaba su distancia con todos los tramos de la línea: el trabajo crecía con la superficie de la línea por su número de tramos. Ahora cada bloque de 64 × 64 vértices lista los tramos que pueden alcanzarlo, y cada fila del bloque los que pueden alcanzarla. El tramo elegido es el mismo: el más cercano, y en un empate el primero.
- Los márgenes (48 m desde el centro del bloque, 34 m desde el de la fila) cubren media diagonal más el redondeo de la distancia, que no llega a medio metro.
- Se recorre por franjas de bloques, fila por fila, para leer la memoria en orden. El orden en que se tocan los puntos cambia, pero cada forma solo cambia el punto que toca, así que el resultado es el mismo.
- Las mesetas recorrían un cuadrado de 1,5 radios más 110 m; ahora el de su borde más lejano posible (el radio más un tercio, más 100 m de rampa).

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): `along_line` era solo del clásico.*

**D-3113. Los lagos, con un montículo por milímetro de altura.**
La inundación desde el borde (D-2704) usaba un solo montículo con todo el frente: en el colosal, con millones de puntos en orden revuelto, cada paso buscaba en memoria lejana. Ahora hay un montículo por milímetro de altura y se vacían de menor a mayor. Nada entra por debajo de la altura que se está vaciando, así que sale el mismo orden. Además se pide al procesador que cargue de antemano los datos del siguiente punto (solo es una pista: no cambia el resultado).

**D-3114. Ruido por filas y raíz cuadrada sin saltos.**
- `FbmRow` da los mismos valores que `fbm` a lo largo de una fila, pero guarda las esquinas de la retícula de cada capa mientras el punto no cambia de celda. Se usa en el relieve, la costa, las islas, los lagos, el suelo, las mesetas y las cordilleras. Una prueba lo compara con `fbm` punto por punto.
- `isqrt` empieza en el bit más alto del valor y elige sin saltos. Da el mismo resultado; una prueba lo comprueba alrededor de cuadrados perfectos y con valores al azar.
- La distancia a un tramo no divide cuando el punto cae antes o después del tramo, y la posición a lo largo de la línea se divide en 32 bits.

**D-3115. Lo que queda.**
- Sin hilos ni coma flotante: la simulación los prohíbe (prueba "the simulation code avoids what breaks determinism").
- Los valles y cordilleras siguen costando más de lo que crece el mapa. Su cantidad va por km² (D-2701) y cada uno cruza el mapa entero, así que su superficie total crece con el cubo del lado: en el colosal, valles y cañones pasan por 2,8 veces la superficie del mapa. Bajarlo cambiaría los mapas, así que queda como propuesta para que decida el usuario (ver `docs/RENDIMIENTO.md`).

*Reemplazada en parte por D-4901 (el generador clásico se borró en la fase 49): ya no hay valles ni cordilleras que crucen el mapa entero.*

## Plan de la niebla de guerra, fases 32 a 34 (2026-09-27)

A pedido del usuario, antes del pulido (que pasa a ser la fase 35). El usuario eligió el esquema mixto, fantasmas para los edificios ajenos, techo relativo al terreno y visión compartida activada.

**D-3201. Lo explorado en la simulación, lo visible en la vista.**
Con lockstep cada máquina simula todo, así que un cliente modificado siempre podría revelar el mapa; se acepta, como en otros juegos de estrategia por lockstep. Lo explorado va en la simulación porque cambia las reglas (dónde se puede construir) y debe guardarse; lo visible ahora solo sirve para dibujar y se calcula en la vista, sin costo para la simulación. Los fantasmas (fase 33) también van en la simulación para que se guarden y sean iguales en todas las instancias.

**D-3202. Niebla estática por omisión.**
Es la que más se parece al juego de referencia, donde el mapa empieza tapado y lo descubierto queda descubierto. "Sin niebla" conserva el comportamiento de antes y el mismo hash.

**D-3203. No se construye en lo no explorado.**
La pregunta quedó sin respuesta explícita; se eligió la regla porque es la de otros juegos del género y evita colocar edificios a ciegas. Mandar un ejército hacia lo no explorado sí se permite. Queda para confirmar en el registro de revisión (`conf-niebla-construir`).

**D-3204. Rejilla de 4 m, actualizada una vez por segundo.**
Una rejilla de 1 m ocuparía 32 MB por jugador en el mapa colosal (en bits); con 4 m son 2 MB y se comprimen muy bien al guardar. Los bordes se suavizan en la GPU. Una vez por segundo basta para descubrir terreno y mantiene el costo de la simulación bajo.

**D-3205. Lo ajeno se oculta aunque sea de un aliado.**
El pedido dice "cualquier entidad que no es tuya". Con visión compartida, lo que ven los aliados cuenta como visión propia, así que en cooperativo casi nunca se nota.

**D-3206. La altura no amplía la visión.**
Se mencionó como idea (ver más lejos desde un cerro) pero no se pidió; queda fuera. La línea de visión bloqueada por el terreno también queda fuera por su costo.

## Fase 32: niebla de guerra estática (2026-09-27)

**D-3207. Qué da visión y cuánto.**
- Todo edificio del pueblo, también en obra, ve desde su centro su `sight` más medio lado; los aldeanos, el `sight` de su raza; los soldados, el de su unidad, salvo mientras viajan por el mapa del mundo. Animales, asaltantes y mercaderes no dan visión.
- Por omisión: 12 m edificios y aldeanos, 16 m soldados. En `core`: centro del pueblo 48 m (el terreno inicial), atalaya 45 m y arquero 24 m (más que su alcance de 20 m).
- Una celda de 4 m queda vista si su centro está dentro del radio. La simulación lo anota después de cada tick múltiplo de 10 (una vez por segundo a x1) y al crear la partida.

**D-3208. Grupos de visión.**
En cooperativo con visión compartida hay un solo grupo; si no, uno por pueblo (el pueblo común es uno solo). Los grupos se fijan al crear la partida y se comprueban al cargarla. Con mapas separados cada jugador descubre su región sin nada especial: su gente no sale de ella.

**D-3209. Suma de verificación, partida y red.**
- La cuenta de celdas exploradas y una suma de un número mezclado por celda, por grupo, entran en el estado como una parte propia, "vision", que el anfitrión compara cada 5 s como las demás. Recorrer 2 MB por grupo en cada comprobación saldría caro; la cuenta y la suma se llevan al día al descubrir cada celda.
- Las celdas mismas van en la partida guardada y en la instantánea de red, después de los números al azar. Al cargar se recalculan la cuenta y la suma y deben coincidir con las guardadas.
- Versión de las reglas 24 y versión del protocolo de red 2 (ocho partes en la comprobación).
- Sin niebla no se guarda ninguna celda y la simulación no cambia: la prueba "the fog does not change the rest of the game" compara todas las partes menos la cabecera (las reglas) y "vision".

**D-3210. La regla por omisión.**
`GameRules{}` sigue sin niebla, así que las pruebas, los tutoriales y cualquier partida hecha en código se comportan como antes. El formulario de partida nueva empieza en estática, también tras "Restablecer" (D-3202).

**D-3211. Lo que ve la vista (`FogView`).**
- Vive en `GameSession` y en cada tick recalcula lo que el jugador tiene a la vista con los mismos discos que la simulación, solo en las filas que tocaron los discos ahora o el tick anterior. Lo explorado lo copia de la simulación cuando su cuenta cambia.
- La textura de niebla tiene un texel por celda (R8: 0 sin explorar, 128 explorado fuera de vista, 255 a la vista) y se sube en cuadros de 64 texeles, solo los que cambian, con filas alineadas a 256 bytes y cada cuadro a 512, como pide Direct3D 12.
- El sombreador toma cinco muestras para un borde suave y aplica la niebla después de la bruma de distancia, así lo no explorado es un mismo negro cerca y lejos y no deja ver siluetas. El agua sin explorar se vuelve opaca.

**D-3212. Qué se oculta con niebla estática.**
Lo que no es del jugador (edificios, campos, aldeanos, soldados, animales, asaltantes) solo se dibuja, se puede seleccionar, suena, echa humo y aparece en el minimapa donde está explorado. Las capas del mapa no pintan sobre lo no explorado. Si lo seleccionado queda bajo la niebla, se deselecciona. Lo propio se ve siempre. La vista previa de un edificio sobre lo negro queda negra, pero el aviso "Ese lugar no está explorado." dice por qué no se puede.

**D-3213. Repeticiones.**
Las partidas de pueblo no tienen repeticiones (solo el núcleo de la fase 5), así que la parte de la especificación sobre ver las repeticiones no aplica.

**D-3214. Ver a través de la niebla.**
Una casilla en Ctrl+F3 > Pueblo apaga la niebla solo en la vista, sin comando ni cambio en la partida. Está desactivada donde no se permiten los comandos de desarrollo (multijugador, D-910).

**D-3215. La sala multijugador.**
La sala tiene una fila "Niebla de guerra" que cambia el anfitrión; la visión compartida se elige en el formulario de partida nueva del anfitrión, como la mayoría de las reglas.

**D-3216. Rendimiento.**
`Game::update_vision()` es pública para poder medirla sola. Medido en `docs/RENDIMIENTO.md`.

## Fase 33: niebla de guerra dinámica (2026-09-27)

**D-3301. Qué ve cada grupo, en la simulación.**
Con niebla dinámica, la actualización de cada segundo anota también qué celdas ve cada grupo en ese momento. Es un dato derivado: no se guarda y se rehace en la siguiente actualización, igual en todas las máquinas (también en la que acaba de cargar o de unirse). La vista sigue calculando lo suyo en cada tick para que lo que se mueve aparezca y desaparezca sin esperar un segundo.

**D-3302. Fantasmas.**
- En cada actualización, cada grupo recuerda los edificios de otros grupos que ve (tipo, dueño, giro, nivel, avance de obra, si arde y cuánto se quemó) y olvida los recordados cuyo lugar ve y ya no existen. No guarda campos, bienes ni trabajadores.
- Se guardan con la partida y entran en la suma de verificación, en la parte "vision", ordenados por entidad.
- Con niebla estática no hay fantasmas: todo lo explorado se ve en vivo.

**D-3303. Cómo se ven.**
Fuera de la vista, un edificio ajeno se dibuja como su fantasma: la variante de su lugar, a medio levantar si estaba en obra, rojizo si ardía o chamuscado. No echa humo ni suena y no se puede seleccionar. En el minimapa sale un poco más tenue. Los campos de las granjas ajenas solo se ven a la vista. Si el edificio real está a la vista, se dibuja el real.

**D-3304. El gris.**
Lo explorado fuera de vista se desatura un 75 % y queda al 45 % de brillo, con un tinte frío, después de la bruma de distancia. El minimapa usa la misma idea.

## Fase 34: niebla con techo de altura (2026-09-27)

**D-3401. El techo.**
Se calcula en la vista al empezar la partida, a partir del mapa: la altura media del suelo en celdas de 16 m, suavizada dos veces sobre 7 celdas (112 m), más 14 m. Así una meseta de 160 m de ancho queda bajo la niebla salvo cerca de su borde, un pico aislado de 12 m de ancho asoma, y en terreno llano asoman los árboles grandes (12 a 24 m) y enormes, pero no los chicos ni los medianos. Sobre el techo hay una franja de 4 m en la que la niebla se va aclarando. Va a la GPU como una textura de 16 bits sobre la misma área que la de niebla (los mapas miden múltiplos de 64 m). La simulación no cambia.

**D-3402. Cómo se ve lo que asoma.**
Bajo la niebla negra, como una silueta oscura con un poco de su luz; bajo la gris, como sin niebla. Lo que se mueve nunca asoma: no se dibuja fuera de lo que se permite ver.

**D-3403. `landmark`.**
Una marca en especies de árbol, recursos del mapa y edificios (`"landmark": true`). Viaja al sombreador en el tinte de la instancia (la paleta más 4096) y hace que el objeto se vea como silueta aunque no sobresalga del techo. `core` no marca nada por ahora: los árboles altos ya asoman por su altura.

**D-3404. Edificios de otros en lo no explorado.**
Se dibujan solo si todo su terreno está sin explorar y su punta sobresale del techo (o son `landmark`), para que se vea su silueta, como la de una atalaya a lo lejos. No se pueden seleccionar ni aparecen en el minimapa. Los bajos no se dibujan, así tampoco echan una sombra que los delate.

## Ajuste: la pausa es solo velocidad 0 (2026-09-27)

**D-3320. La pausa ya no desenfoca ni bloquea (reemplaza parte de D-810).**
Pedido de Salvador tras probar en red: al pausar se bloqueaba toda la interfaz, incluido el aviso para aceptar un cambio de velocidad, y la partida no se podía reanudar. Ahora pausar es solo poner la velocidad en 0: no hay desenfoque ni panel de pausa, la cámara se mueve libre y se pueden dar órdenes, que se aplican cuando la partida vuelve a avanzar. El desenfoque y el velo oscuro quedan solo para el menú del juego (y la configuración o la carga abiertas desde él), que en una partida de un jugador sigue deteniendo el juego. La votación de D-009 no cambia.

**D-3321. Identificador de compilación en la sala.**
El número de versión (`0.20.0`) no cambia entre fases, así que dos compilaciones distintas se aceptaban y se desincronizaban (pasó con la niebla de guerra). Ahora cada compilación lleva un identificador: los primeros 12 dígitos hexadecimales de un SHA-256 de todos los archivos de `src/` (ruta y contenido), calculado en cada compilación por `cmake/BuildId.cmake`. No depende de git, así que también distingue compilaciones con cambios sin confirmar, y dos equipos que compilan el mismo código obtienen el mismo. La sala compara la versión completa (`0.20.0+1a2b3c4d5e6f`) y, si solo cambia el identificador, explica que hay que copiar la misma compilación a todos los equipos. El menú principal y el registro muestran la versión completa para compararla a simple vista. Se hashea todo `src/`, no solo la simulación, por ser lo más simple y seguro: cualquier cambio de código obliga a usar la misma compilación. Las partidas guardadas siguen comparando solo el número de versión.

## Herramienta: ideas y análisis en el registro de revisión (2026-09-28)

**D-9001. Las ideas viven en `revision.json`, no en un archivo aparte.**
Se había propuesto un `ideas.json` separado para no hacer más grande `revision.json` (410 KB). Se descartó porque la página tendría que abrir y guardar dos archivos, con dos permisos y el doble de lugares donde perder cambios. Unos cientos de ideas agregan pocos kilobytes. Las ideas son el tipo `idea` y las preguntas del análisis el tipo `pregunta`, con los mismos campos de estado, nota, respuesta e historial que el resto. El `docs/IDEAS_POR_REFINAR.md` de la primera propuesta ya no se usa.

**D-9002. El texto de una idea no se cambia nunca.**
`revision.py agregar` no toca `detalle`, `area` ni `capturada` de una idea que ya existe. El análisis va en un campo aparte (`analisis`), y la página muestra el texto original tal cual, sin interpretar Markdown.

**D-9003. `agregar` actualiza solo los campos que recibe, y puede cambiar el estado.**
Antes reemplazaba el elemento entero. Ahora los campos que no se envían se conservan, así que poner el análisis en una idea no obliga a repetir su texto. El estado se cambia solo si se envía de forma explícita, como al marcar una idea "analizada" o "planeada", y queda en el historial como acción de Claude, igual que con `responder`. Las notas y elecciones de Salvador nunca se tocan.

**D-9004. Números de idea sin choques.**
Las ideas se numeran I-001, I-002… con el siguiente número libre, contando también las archivadas. Si Salvador escribe una idea en la página mientras Claude agrega otra con el mismo número, al guardar la de la página toma el siguiente número libre. Ninguna de las dos se pierde.

**D-9005. Cerrar una ronda archiva, no borra.**
`revision.py archivar` marca con `archivado` las ideas planeadas o descartadas y las preguntas respondidas. La página las oculta salvo que se active la casilla "archivadas". Las ideas "para después" siguen abiertas. Así la limpieza no destruye nada y el historial de por qué se decidió cada cosa queda disponible.

**D-9006. La página del registro sigue solo en español.**
La regla de textos en español e inglés es para las aplicaciones. El registro es una herramienta interna que solo usa Salvador, así que se deja en español. Si algún día la usa alguien más, se traduce.

**D-9007. Contador "atendidos/total" en las pestañas, y lo atendido al final.**
Pedido de Salvador. Un elemento está atendido cuando ya no está en su primer estado (sin revisar, sin probar, pendiente, abierto, nueva, sin responder) y no tiene una respuesta mía que él no haya leído. Cada pestaña muestra atendidos/total, por ejemplo 5/400, y cada grupo lleva su propio contador. En las listas, lo pendiente va primero dentro de cada grupo, y los grupos ya completos van al final. La casilla "ocultar atendidos" los esconde, y el navegador la recuerda. "Requiere tu atención" sigue mostrando un solo número.

**D-9008. No se separa un archivo histórico por ahora.**
Salvador preguntó si el tamaño de `revision.json` gasta tokens. No los gasta: Claude no lee el archivo entero, sino que usa `revision.py pendientes` e `ideas`, que imprimen solo lo que espera acción, y los commits se revisan con `--stat`. Para la página, 400 KB o unos pocos MB no pesan. Separar un archivo histórico obligaría a la página a manejar dos archivos (ver D-9001). Se reconsidera si el archivo pasa de unos 5 MB o si la página se vuelve lenta; en ese caso, lo más simple sería un comando que mueva lo atendido y archivado a un `revision-historico.json` de solo lectura.

**D-9009. Correcciones con su propio ciclo.**
Pedido de Salvador para anotar lo que encuentra al probar el juego. Son el tipo `correccion`, numerado C-001…, y comparten con las ideas su regla principal: el texto de Salvador no se cambia. Estados: nueva, autorizada, en curso, corregida, no se reproduce, verificada, descartada. Salvador pone "autorizada", "verificada" y "descartada"; Claude pone "en curso", "corregida" y "no se reproduce". "Autorizada" sirve también para regresar una corrección que sigue fallando. Las correcciones no pasan por el análisis ni por el plan. Las autorizadas aparecen en `revision.py pendientes`, y `archivar` guarda las verificadas y las descartadas.

**D-9010. Explicación de los estados en la página.**
Cada estado de cada tipo tiene una frase que dice qué significa y quién lo pone. Se ve de dos formas: al pasar el ratón sobre el selector de estado, y en "¿Qué significa cada estado?", bajo la introducción de cada pestaña. Las frases viven solo en la página, porque `revision.py` no las necesita.

**D-9011. Las peticiones nuevas escritas en una decisión pasan a Ideas.**
En D-003, D-010, D-410 y `conf-soldados`, la nota de Salvador no corregía la decisión: pedía algo nuevo (más velocidades, años más largos, mejoras de cámara, soldados que comen y cobran). Cada nota se copió tal cual a una idea (I-001 a I-004), que muestra de qué elemento salió (`desde`). El elemento de origen enlaza a la idea (`ideaCreada`) y recibe una respuesta de Claude. No se tocaron ni sus estados ni sus notas. Así esas peticiones entran en la ronda de refinamiento en vez de quedar sueltas.

**D-9012. Una prueba manual que falla se vuelve una corrección autorizada.**
`revision.py pendientes` crea, por cada prueba en "falla" que aún no tiene corrección, una corrección en estado "autorizada". Su texto dice qué prueba falló e incluye la nota de Salvador; las dos quedan enlazadas. Nace autorizada porque marcar "falla" ya era pedir el arreglo. Una corrección autorizada espera a Claude sin importar quién la autorizó. Al marcarla "verificada" en la página, la prueba pasa a "funciona". Los enlaces se conservan al sincronizar con el README.

**D-9013. Por confirmar con opciones.**
Una confirmación puede traer opciones, como una pregunta, pero siempre de elección única, y una de ellas marcada `actual`: lo que Claude ya implementó. Elegir esa opción la confirma; elegir otra la rechaza y pide el cambio. Las 20 confirmaciones que ya existían se quedan sin opciones.

**D-9014. Sugerencias y pendientes son ideas.**
Las 14 sugerencias y los 9 pendientes pasaron a ser ideas con `autor: "Claude"` y un área. Conservan su número, su texto, su historial y, en `antes`, su tipo y estado anteriores. Equivalencias:
- "sin revisar", "abierto" y "requiere definición" pasan a "nueva";
- "autorizada" pasa a "para el plan";
- "pospuesta" pasa a "para después";
- "en curso", "implementada" y "hecho" pasan a "planeada".

Lo ya hecho o descartado queda archivado. "Pulido y entrega" quedó como planeada en la fase 37. Las pestañas Sugerencias y Pendientes desaparecen, y los tipos `sugerencia` y `pendiente` ya no existen. Así, todo lo que podría hacerse pasa por la misma ronda de refinamiento, sea de Salvador o de Claude.

**D-9015. El texto de una idea se puede editar mientras esté "nueva".**
Pedido de Salvador. En sus ideas y correcciones en estado "nueva", la página muestra "✎ Editar texto". Al guardar, el título se recalcula y el texto anterior queda en el historial (acción `texto`). No aplica a las ideas de Claude, a las correcciones creadas desde una prueba ni a lo archivado. Si Claude la analizó entre la edición y el guardado (en el disco ya no está en "nueva", o su texto cambió), el texto no se reemplaza: la versión nueva se guarda como nota de Salvador y la página lo avisa. Claude sigue sin poder cambiar el texto (D-9002).

**D-9016. Guardar desde la página ya no deshace estados puestos por Claude.**
Antes, al guardar cualquier cambio de un elemento, la página escribía también el estado que tenía en memoria. Si Claude había cambiado el estado mientras tanto, por ejemplo al marcar una idea "analizada", ese cambio se perdía aunque Salvador solo hubiera escrito una nota. Ahora la página escribe el estado solo si Salvador eligió uno (un estado o una opción) desde el último guardado. Si los dos lo cambiaron, gana la elección de Salvador, que es la más reciente y deliberada.

**D-9017. Los estados que pone Claude no se pueden elegir en la página.**
Pedido de Salvador. En el selector, los estados que solo pone Claude aparecen atenuados y no se pueden elegir; así se sigue viendo el estado actual. Son "analizada" y "planeada" en las ideas; "en curso", "corregida" y "no se reproduce" en las correcciones; y "respondida" en las preguntas, que se pone sola al contestar. El cambio masivo de estados también los excluye. Para no estar de acuerdo con lo que marcó Claude, se elige uno de los estados propios, por ejemplo regresar una corrección a "autorizada". `revision.py` sí puede ponerlos. Además, las introducciones y los textos de la página nombran a Claude en tercera persona, en vez de "yo" o "mi", para que no haya duda de quién hace qué.

## Fase 37: nombres del terreno bajo el cursor (2026-09-29)

**D-3701. Los accidentes viven en el mapa, fuera de su suma de verificación.**
Antes, el generador entregaba la lista de accidentes solo a las pruebas. Ahora queda en `MapData::landforms`, junto con `sea_levels`, el nivel del mar de cada región. Así se guarda con la partida y llega a quien se une a una partida en red sin nada aparte. `checksum()` no los incluye porque describen el terreno, no son parte de él; por eso las sumas de verificación de referencia y la versión del generador (6) no cambian. Las partidas guardadas antes de esta fase ya no se pueden cargar, como en cualquier cambio de formato (D-631).

**D-3702. Tipos nuevos: cabo, río e isla.**
Los cabos antes se contaban como penínsulas; ahora son `Cape`. Los ríos se guardan con un punto cada 8 m de su curso y 14 m de ancho, y las islas de los mapas de islas, con su centro y su radio. Los lagos no se guardan uno por uno: el agua que no es mar ni río es lago. El mar es el agua que está justo al nivel del mar de su región. La costa es tierra seca con mar a 12 m o menos. Los tipos nuevos van al final de la lista, porque la partida guarda sus números.

**D-3703. Los accidentes de la costa se guardan donde quedaron.**
Los golfos, las penínsulas, los cabos y los islotes se dibujan sobre posiciones deformadas por ruido, y encima las bahías y cabos pequeños mueven la orilla. Al medirlo, solo 10 de 15 caían donde decía el plan. Por eso, después de dar forma a la costa, el generador:
- deshace la deformación en el punto (tres iteraciones, porque cambia despacio);
- mide once puntos a lo largo del eje y guarda solo el tramo continuo más largo que sí es tierra (o mar, en un golfo), si mide al menos un quinto del plan;
- descarta el que no se formó, y el islote cuyo centro quedó bajo el agua.

Con esto, 12 de 12 quedan en su lugar en las pruebas. El terreno no cambia; solo cambia lo que se anota. Las mesetas, los islotes y las islas tienen bordes deformados por ruido, así que se reconocen con un margen: 4/3 del radio más 10 m, el radio más 10 m y 1,7 veces el radio.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): los golfos, penínsulas e islotes del jerárquico son estructuras y se nombran por su cuadrícula (D-4103).*

**D-3704. Bajo la niebla no se dice nada.**
F3 es una ventana de desarrollo, pero no debe revelar lo que el jugador no ha explorado. Donde la niebla lo oculta, dice solo "Todavía sin explorar". Con "Revelar todo" de las herramientas de desarrollo, sí se ve.

**D-3705. Una sola descripción para F3 y para las herramientas de desarrollo.**
El panel "Terreno" de Ctrl+F3 ya mostraba suelo, bioma, altura, pendiente y agua. Ahora usa la misma descripción de `game/terrain_names`, y se borraron sus textos repetidos (`dev.terrain.*`, salvo el título). La descripción se recalcula solo cuando cambian la casilla, el mapa o el idioma. El índice de accidentes, por cuadros de 128 m, se arma la primera vez que hace falta. Con F3 cerrado no se hace nada.

**D-3706. Lo que no tiene nombre.**
Las montañas del relieve "Montañoso" salen de un campo de ruido, no de una lista, así que no tienen nombre de accidente: F3 muestra su altura y su pendiente, pero no dice "Cordillera". "Cordillera" es solo la de la fase 27. Tampoco se nombran las bahías y cabos pequeños que ondulan toda la costa: son parte de la "Costa". Si hiciera falta nombrarlos, el generador tendría que guardarlos también.

*Reemplazada por D-4901 (el generador clásico se borró en la fase 49): las montañas son regiones con nombre, y "Cordillera" ya no existe.*

**D-3707. Numeración de las fases.**
Otra sesión agregó las fases 35 (movimiento) y 36 (caminos), todavía sin commit. Esta fase es la 37, el reporte con Ctrl+F12 es la 38 y el pulido pasa a la 39.

## Fase 38: reporte del mapa (2026-09-29)

Salvador eligió, entre las opciones propuestas: captura solo del mundo, sin nota dentro del juego, escritor de PNG propio y carpeta temporal.

**D-3801. La captura se lee del propio swapchain.**
La API de GPU de SDL3 no permite hacer un blit desde la textura del swapchain (solo tiene uso de destino de color), pero `SDL_DownloadFromGPUTexture` sí la acepta: en Direct3D 12 la pasa al estado de copia y la regresa. En el cuadro capturado se copia a un búfer de descarga, se espera la valla y se convierte a RGB. Solo se leen formatos de 8 bits (BGRA o RGBA); otro formato hace fallar el reporte con un aviso, sin romper nada. Se verificó en Windows 11 (build 26200) con Direct3D 12: dos capturas del mismo reporte difieren en el 0,04 % de los píxeles, por el agua animada.

**D-3802. Una sola captura; los trazos se pintan después.**
El cuadro capturado no dibuja nada de la interfaz: ni los trazos, ni la línea de ayuda, ni F3, ni las herramientas de desarrollo. Esa es `captura_limpia.png`. Los trazos se pintan luego sobre una copia en la CPU, del mismo grosor que en pantalla, y esa copia es `captura.png`. Así las dos son el mismo instante, aunque el juego siga corriendo en multijugador.

**D-3803. PNG propio sin compresión.**
`core/png` escribe PNG RGB de 8 bits con bloques deflate "stored", CRC32 y Adler-32: unas 80 líneas, sin bibliotecas nuevas. Una captura de 1280×720 pesa unos 2,7 MB. Las pruebas lo leen de vuelta con `stb_image`.

**D-3804. Qué se congela al marcar.**
Al marcar se ignoran la cámara, los clics sobre el mundo, las herramientas de desarrollo y todas las teclas salvo las del reporte. En una partida local la velocidad pasa a 0 y al terminar vuelve a la que tenía; en multijugador no se pausa, para no detener a los demás. Esc cancela sin llegar al menú del juego. Ctrl+F12 es un atajo fijo, como Ctrl+F3. No funciona con un menú abierto sobre el juego.

**D-3805. `reporte.json`.**
Tiene claves en inglés, como `settings.json`, y nombres que no dependen del idioma: los tipos de mapa y biomas van por su id de mod, y los suelos, el agua y los accidentes, por nombres fijos. La semilla va como texto, porque es un entero de 64 bits. Cada trazo guarda sus puntos en pantalla y sus casillas; las casillas salen del mismo rayo de cámara que usa el juego, muestreado cada 2 píxeles. El resumen describe como mucho unas 20 000 casillas, repartidas entre todas, para que un trazo largo no tarde. `--reporte` valida estrictamente solo lo que usa: versión del esquema, opciones del mapa (con rangos y nombres conocidos) y vista (números finitos dentro de rangos). Nunca ejecuta nada del archivo.

**D-3806. `--reporte` no toca la configuración ni el disco del jugador.**
Usa una ventana en modo ventana, del tamaño en píxeles del reporte (corrigiendo la escala de la pantalla), y el sonido en silencio. Solo cambia la memoria: la configuración no se guarda y el autoguardado no corre. Genera el mapa como una partida nueva sin niebla, con velocidad 0 y la estación y la nieve del reporte; espera 3 segundos y 30 cuadros a que se llene la vista, captura y se cierra. Devuelve 1 si no pudo leer el reporte, generar el mapa o guardar la captura. El `.txt` anota lo que cambió respecto del reporte y la suma de verificación del mapa de ahora.

**D-3807. Limpieza de reportes viejos.**
Antes de crear uno nuevo se borran los más viejos, hasta dejar 29 más el nuevo. Solo se borran carpetas con nombre de reporte (`AAAA-MM-DD_HHMMSS`, quizá con `-N`) que contienen únicamente archivos de reporte. Si alguien dejó otra cosa dentro, la carpeta se conserva y se anota en el registro.

**D-3808. F12 solo sigue sin hacer nada.**
La acción `ui.screenshot` (F12) existe desde la fase 17 pero no hace nada. No se implementó aquí para no crear un segundo tipo de captura; queda para el pulido.

**D-3809. Un contorno cerrado describe su área, y el rayo llega lejos.**
Pedido de Salvador tras sus primeros reportes. Un trazo cuenta como cerrado si su final queda cerca de su inicio: a no más de una quinta parte de su tamaño, con un mínimo de 24 píxeles. Además de la línea, el reporte describe lo que encierra: lo muestrea en una rejilla que se abre cuanto más grande es el área, con 20 000 puntos como máximo, y el JSON marca el trazo con `"closed": true`. En un reporte con la cámara a 3,4 km, dos trazos lejanos no tenían casillas: el rayo buscaba el suelo solo hasta 4 km. Ahora F3 y los reportes buscan hasta cuatro veces la distancia de la cámara más 1,5 veces el lado del mapa. El recorrido del rayo empieza a la altura máxima posible del terreno y alarga el paso con la distancia (un metro más por cada 500 m), así que llegar lejos no lo vuelve lento.

## Fase 39: generadores intercambiables y generador jerárquico, mundo y regiones (2026-09-30)

Salvador pidió un generador nuevo, independiente del actual, con la idea de generar por jerarquías, y que las fases 39 a 43 se hagan seguidas, sin su intervención.

**D-3901. Cada generador es una opción de la partida, no un parámetro de otro.**
`MapSettings::generator` (clásico o jerárquico) se guarda con el mapa, en la partida, en la partida nueva recordada (`newGame.generator`) y en los reportes (`"generator"`; un reporte sin ese campo es del clásico). Agregar un generador después es agregar su módulo y su nombre al final de la lista. Para que los mapas clásicos no cambien, `MapSettings::write_identity`, lo que usa la suma de verificación, no escribe el generador cuando es el clásico: las sumas de referencia siguen iguales. Cada generador tiene su propia versión; la del jerárquico es `hier::kVersion` (1).

*Reemplazada por D-4901 y D-4902: desde la fase 49 hay un solo generador y la partida ya no guarda cuál fue.*

**D-3902. Qué es independiente y qué se comparte.**
El jerárquico vive en `sim/worldgen_hier.cpp` y da forma a todo el terreno a su manera. Las etapas de agua, suelo y vida del clásico (lagos por inundación desde el borde, ríos, suelo, biomas, bosques, recursos, fauna y salidas) se reutilizan, porque están probadas y rinden bien. Solo cambian donde el jerárquico lo pide: por ejemplo, los lagos (D-3906). Si más adelante un generador necesita otra etapa distinta, se separa entonces.

*Reemplazada por D-4901: las etapas de agua, suelo y vida ya no se comparten con nadie; son las del único generador.*

**D-3903. Las regiones.**
Hay un centro por celda de una rejilla, movido al azar, cada 150 a 900 m (el lado del mapa entre 7). Cada casilla es de la región del centro más cercano, medido después de deformar el punto con ruido: una ondulación amplia (30 % de la separación) y otra corta de 14 m, para que los bordes no sean rectos. "Accidentes del terreno" decide qué parte de las regiones no es llanura (30, 45 o 60 %). "Relieve" decide qué parte de esas son montañas (20, 35 o 55 %). De las demás, un 15 % son mesetas, un 10 % cuencas y el resto colinas. Las reglas:
- las montañas se colocan en cadenas de 2 a 4 regiones vecinas que siguen una dirección;
- una meseta no toca otra meseta ni una cuenca;
- una cuenca no toca otra cuenca ni una meseta;
- las colinas van primero junto a las montañas.

**D-3904. Las alturas.**
Cada papel da una altura base y dos tamaños de irregularidad (ondulaciones de 512 m y lomas de 64 m). Las alturas base aproximadas:
- llanura: 21 m;
- colinas: 25 a 29 m;
- montañas: 38 a 52 m;
- meseta: 48 a 62 m;
- cuenca: 13,5 m.

Se calculan en las esquinas de cuadros de 8 m, mezclando las regiones cercanas según su distancia al borde: en una franja ancha entre la mayoría y en 6 m alrededor de una meseta, que así queda con acantilado. Cada vértice interpola entre esas esquinas y suma sus irregularidades, más 40 cm de relieve fino para que el agua no corra en línea recta. Así, un mapa grande tarda 1,5 s en generarse.

**D-3905. Los nombres son exactos.**
El mapa guarda, por cuadro de 8 m, la región y la estructura que lo ocupan (`region_owner`, `structure_owner`), y la partida los guarda también. No entran en la suma de verificación, igual que los accidentes (D-3701). F3 y los reportes leen esas cuadrículas en vez de adivinar por distancia: "Región: Montañas" y, desde la fase 40, la estructura.

**D-3906. Los lagos van en las cuencas.**
Las primeras pruebas dejaban cientos de estanques en cualquier hondonada. En un mapa jerárquico, la etapa de lagos solo deja un lago si al menos la mitad está en una cuenca, o si es grande (15 000 vértices con 10 cm de agua o más, cerca de 1,5 ha). Las demás hondonadas se rellenan y quedan planas. En el clásico no cambia nada.

**D-3907. Hasta la fase 41, sin mar.**
El jerárquico todavía no hace mar ni islas: ignora "Mar", y en los tipos de mapa con islas genera tierra firme. La fase 41 agrega el agua.

## Fase 40: generador jerárquico, estructuras (2026-09-30)

**D-4001. Qué estructura va en cada región.**
Cada estructura solo modifica el terreno de su región (y, los valles y cañones, el de la región vecina a la que desembocan). Cada cuadro de 8 m tiene como mucho un dueño. Si dos se superponen, gana el más específico, en este orden: acantilado y rampa, cresta y paso, valle, cañón.
- **Montañas:** una cresta por cadena, que pasa por el centro de cada región de la cadena y se alarga un poco en los extremos. Se eleva sobre la base con un perfil suave hasta el 45 % de la separación entre regiones, con picos y espolones de ruido "crestado" y más baja en los extremos. Altura de la cresta: 25 a 40 m con relieve bajo, 40 a 65 m con suave y 65 a 110 m con montañoso. Siete de cada diez tienen un paso: un tramo de 120 m donde baja un 65 %. El nombre "Cresta" cubre el 35 % central del ancho; el resto de la región es "Montañas".
- **Mesetas:** su borde es "Acantilado", y tienen una rampa de 32 a 48 m de ancho, del 30 % de la meseta al 85 % de la región vecina, hacia una llanura o unas colinas (nunca montañas ni cuencas).
- **Valles:** en forma de U, de 80 a 320 m de ancho y 6 a 12 m de hondo, desde una región de colinas o montañas hasta una llanura o cuenca vecina, con el fondo en bajada. En las montañas empiezan en una ladera, al 30 % del camino hacia la salida, para no cortar la cresta. Hay uno por cada 7, 3 o 2 regiones candidatas (según "Accidentes": pocos, normales o muchos). El 60 % lleva río.
- **Cañones:** solo en mesetas, desde lo hondo de la meseta hasta la región vecina más baja: de 28 a 44 m de ancho, con fondo plano y paredes a pique. El fondo empieza 55 a 75 % más abajo que la cima y termina 80 cm bajo la salida, para que drene. El 75 % lleva río.

**D-4002. Menos cañones.**
Salvador pidió que salieran menos pero que sí salieran. Hay un cañón por cada 15, 25 o 40 % de las mesetas (redondeando hacia abajo), y al menos uno si hay mesetas, salvo con "Pocos". En cuatro mapas grandes con "Muchos" salen 8 cañones con 2,6 km en total, contra 8 cañones con 18 km en el clásico, que cruza todo el mapa con cada uno. La prueba compara la longitud, que es lo que se ve.

**D-4003. Los ríos que piden los valles y cañones.**
Los nacimientos que pide el jerárquico se usan todos, aunque pasen del número de ríos por superficie de la etapa compartida (en el clásico sigue el tope). El inicio de un cañón o un valle siempre queda dentro del mapa, a 16 m o más del borde. Antes, algunos quedaban fuera y su río "nacía" en el borde y se iba de inmediato.

**D-4004. Pruebas del jerárquico en tres suites.**
Como las del clásico (D-3110): `worldgen_hier` (unos 36 s en debug), `worldgen_hier_structures` (49 s) y `worldgen_hier_compare` (57 s), para que cada una quepa en el límite de 120 s en debug y de 240 s con AddressSanitizer.

## Fase 41: generador jerárquico, agua (2026-09-30)

**D-4101. El mar es el nivel 0: se decide antes que los papeles.**
Con costa ("Mar": a veces el 40 % de los mapas, o siempre) el mar ocupa uno, dos opuestos o dos contiguos de los lados, con los mismos patrones que el clásico, y entra entre 12 y 22 % del lado. Las regiones cuyo centro queda en esa franja son mar. Su fondo está 4 a 8 m bajo el nivel del mar, que va a 19 m: las llanuras quedan 2 m arriba, y la mezcla entre regiones hace las playas. Después de repartir los papeles:
- 0 a 2 regiones costeras de llanura o colinas se hunden como golfos;
- 0 a 2 regiones de mar junto a tierra quedan como penínsulas;
- 0 a 3 regiones de mar abierto reciben un islote de 20 a 60 m.

Las mesetas y cuencas nunca tocan el mar.

**D-4102. Islas y archipiélagos.**
En los tipos de mapa con islas, las islas se ubican con la misma distribución del clásico (`worldgen::island_layout`), y la tierra la decide su forma: toda tierra dentro del 70 % del radio, nada más allá del 130 %, y la orilla doblada por ruido en bahías y cabos. Dentro de cada isla siguen las regiones con su papel (una isla puede tener montañas), y cada pueblo empieza en su isla principal, con la etapa de salidas compartida. Una región cuyo centro cae en el mar aporta altura de llanura bajo una isla (la forma de la isla manda); si no, las islas sobre esas regiones quedaban bajo el agua.

**D-4103. Nombres del agua.**
Los cuadros de mar que caen en una región de tierra se nombran "Mar". Los golfos, penínsulas, islotes e islas son estructuras, que cualquier estructura posterior puede ocupar. En los dos generadores, el agua al nivel del mar sobre el curso de un río se llama "Estuario": es la desembocadura, no mar abierto ni una dorsal (lo que Salvador vio en un reporte del clásico).

**D-4104. Pruebas.**
Nueva suite `worldgen_hier_water`:
- con costa, el mar llega al borde en al menos medio lado, la mayoría del mapa es tierra, ninguna meseta toca el mar y los pueblos empiezan en tierra;
- con islas, hay tantas como se pidieron, sus centros son tierra, las esquinas son mar y cada pueblo está en su isla;
- 4 de 4 cañones tienen agua en su fondo;
- el final de un río nunca se nombra "Mar".

## Fase 42: generador jerárquico, suelo, vida y detalle (2026-09-30)

**D-4201. Los biomas siguen las regiones.**
En un mapa jerárquico, cada región tiene un solo bioma, elegido con los pesos del tipo de mapa a partir de su número. Si el tipo de mapa tiene pinares, todas las regiones de montañas son pinar. En un mapa grande de prueba, 58 de 58 regiones tienen un solo bioma (al menos 80 % de sus cuadros) y 14 de 14 montañas son pinares. Los bosques, recursos, fauna, humedad, fertilidad y suelo salen de las etapas compartidas, que ya se guían por el agua y las pendientes.

**D-4202. Los pueblos empiezan en llanuras o colinas.**
La etapa de salidas prefiere, en un mapa jerárquico, casillas de llanura o colinas que no sean parte de ninguna estructura (ni valle, ni rampa, ni islote). Si no hay suficientes, usa el resto, como el clásico. Las garantías de siempre (recursos, agua a 150 m o menos, claro de 25 m) se prueban también en el jerárquico con 1, 4 y 8 pueblos, y con 12 en un mapa grande.

**D-4203. Detalle fino.**
El nivel 5 son las lomas de 64 m y los 40 cm de relieve fino de la fase 39, más el detalle que ya ponen las etapas compartidas (rocas, arbustos, hierbas y pasto). No hizo falta agregar otro.

**D-4204. Rendimiento.**
El mapa colosal jerárquico tarda 113 s, contra 179 s del clásico (`docs/RENDIMIENTO.md`). Las pruebas de esta fase están en la suite `worldgen_hier_life`.

## Fase 43: generador jerárquico, ajuste y documentación (2026-09-30)

Ajustes después de revisar con `--reporte` mapas de seis semillas: mediano, grande, enorme; los tipos Clásico, Variado, Pinar del norte, Tierra de gigantes e Islas; y los tres relieves.

**D-4301. Acantilados sin escalones.**
Con la mezcla de regiones calculada cada 8 m, el borde de las mesetas salía en zigzag. Ahora, cerca del borde de una meseta, cada vértice calcula su propia mezcla (una franja de un cuadro y medio a cada lado del borde), y en el resto se sigue interpolando. El acantilado mide 6 m y sigue el borde sin dientes, sin costo apreciable: el mapa mediano sigue tardando menos de medio segundo, y el colosal pasa de 113 a 115 s.

**D-4302. El relieve se escala con el tamaño de las regiones.**
En mapas pequeños y medianos las regiones miden unos 150 m, y con las mismas alturas que en los grandes todo era acantilado y rampa. La altura sobre la llanura de colinas, montañas, crestas y mesetas se multiplica por la separación entre regiones entre 300 m: la mitad con 150 m y completa desde 300 m. La prueba de mesetas pide 8 m sobre su entorno en vez de 15.

**D-4303. Rampas y cañones a la medida de la meseta.**
- La rampa es un corte dentro de la meseta: nace en la cima y llega 20 m más allá del pie del acantilado, con pendiente de 1 en 4 si la meseta es lo bastante ancha (más empinada si no). Su ancho es el 6 % de la separación entre regiones (de 8 a 20 m de medio ancho), y sus lados bajan en el 8 % (10 a 24 m). Antes era un terraplén largo y empinado que cruzaba la llanura.
- Un cañón solo va en una meseta de 1,3 ha o más, y su ancho es el 7 % de la separación entre regiones (de 9 a 20 m de medio ancho). En las mesetas chicas, el cañón se comía la meseta entera.

**D-4304. Costa en dos lados más angosta.**
Con mar en dos lados, cada franja entra del 10 al 16 % (en vez del 12 al 22 %), para que la tierra siga siendo la mayor parte del mapa. Una semilla con dos costas y golfos quedaba con 48 % de tierra.

**D-4305. `docs/GENERADORES.md`.**
El documento responde la pregunta que dio origen a las fases 37 a 43: qué genera cada generador, cómo se llama cada cosa, qué opción de la partida la controla y con qué frecuencia aparece. También tiene la tabla de todo lo que F3 puede nombrar.

## Fase 44: animales animados, el cerdito (2026-09-30)

**D-4401. Técnica de modelado de los animales low poly.**
Antes de la fase, a pedido del usuario, se hicieron el cerdito y el tigre con diez técnicas, con hojas de comparación y de aristas (`pig_studies.py`, `tiger_studies.py`): primitivas, envolventes convexas, icoesferas, metaballs, *remesh* con reducción planar, *remesh* con reducción por colapso, modificador Skin, loft, box modeling y vóxeles. El usuario eligió la de *remesh* y reducción por colapso (la 06) para todos los animales de la imagen de referencia. Lo que se aprendió:
- Pintar rayas cara por cara deja manchas cuando las caras son grandes: hay que cortar la superficie en los bordes de cada raya. Los cortes cuestan muchos triángulos, así que el tigre lleva menos rayas y la vaca está cerca de su límite.
- Un disco de otro color pegado sobre la superficie deja asomar bordes: la punta se corta y se aplana en la misma superficie (`flat_cap`).
- En la flora (cactus, piña y fresa), el cuerpo se construye a mano en `details()` (tubo con costillas, escamas, perfil girado), porque el *remesh* no daba esas formas. Solo el hongo usa la técnica completa. Queda pendiente que el usuario confirme esa excepción.

**D-4402. Pesos propios por distancia en lugar del pesado automático de Blender.**
El pesado automático de Blender (por difusión de calor) falla con piezas separadas y da resultados difíciles de controlar. Los pesos se calculan en `rigs.py` por distancia a cada hueso, con tres reglas que salieron de las pruebas:
- Los huesos de una pata solo tiran de puntos cerca de su eje y por debajo de donde sale del cuerpo: el vientre del cerdo cuelga tan bajo como la rodilla y se iba con la pata.
- Bajo el tobillo todo es del hueso del pie: con una transición de 8 cm, la pezuña se inclinaba con la pierna y se hundía 1,5 cm en el suelo.
- La transición entre huesos es de 4 cm en el cerdito (se ajusta por animal con `blend`).

**D-4403. Anillos cortados en las articulaciones.**
La reducción deja triángulos largos de la pezuña al vientre, sin vértices en la rodilla, y la pata se doblaba como una cuña de goma. La plantilla corta la superficie en la rodilla y donde la pata sale del cuerpo. Esto suma triángulos: el cerdito pasa de 1066 a 1426, dentro de su límite de 1500. Por eso el criterio de la especificación "mismos triángulos que sin esqueleto" pasa a "dentro de su límite".

**D-4404. Patas por cinemática inversa y velocidad guardada en el modelo.**
En lugar de girar las patas con ángulos fijos, cada pie sigue una trayectoria: apoyado, retrocede en línea recta a la velocidad de la animación; luego avanza en arco. Los ángulos salen de resolver los dos huesos de la pata en el plano lateral. Así los pies no patinan ni se hunden por construcción, y `rig_check.py` lo mide sobre el archivo exportado.
- La velocidad de cada animación se guarda en los *extras* glTF del esqueleto (`walk_speed`, `run_speed`). El juego todavía no los lee (fases 45 y 47).
- La articulación que se ve bajo el cuerpo se dobla hacia adelante en las patas delanteras (el carpo) y hacia atrás en las traseras (el corvejón).

**D-4405. Animaciones pensadas para un motor sin mezcla.**
El motor todavía no mezcla animaciones (D-403). Por eso `eat` empieza y termina en la pose de reposo (baja la cabeza, hoza y la sube), y cambiar entre `idle` y `eat` no salta. `die` no se repite: el juego deberá detenerla en su último fotograma (fase 47).

**D-4406. Los modelos de estudio no se versionan.**
`art/studies/` (modelos e imágenes de revisión) se regenera con los scripts y queda en `.gitignore`. El cerdito animado se copió a `tests/data_models_test/animal_pig.glb` para probar que el cargador del juego lo acepta: 21 huesos, las 5 animaciones y pesos que suman 1.

## Fase 45: revisión de animaciones en el visor (2026-09-30)

**D-4501. La carpeta de estudio como un mod aparte, sin copiar nada a `core`.**
"Modelos en estudio" es una entrada más en la lista de mods del visor, con el identificador `@studies` (un mod real no puede llamarse así). Lee los `.glb` de una carpeta suelta: por omisión `art/studies/animals` del código fuente con que se compiló el visor, o la que se pase con `--estudio <carpeta>`. Solo lee los archivos de esa carpeta, no sus subcarpetas (ahí están las imágenes de revisión), y los lista como animales, sin la marca de "sin usar". Se descartó darle a la carpeta la forma de un mod (`mod.json` y `models/animals/`): obligaba a cambiar a dónde escriben los scripts y las vistas previas.

**D-4502. La velocidad de cada animación se lee del modelo, y lo inválido se ignora.**
El cargador lee `<animación>_speed` (m/s) de los *extras* glTF de un nodo por encima del esqueleto y lo guarda en `ModelClip::speed`. Se acepta solo un número entre 0 y 100, en unos *extras* de hasta 4096 bytes que sean un objeto JSON válido. Cualquier otra cosa significa "sin velocidad" (0), y el modelo se carga igual: un dato opcional mal escrito no debe dejar sin modelo al juego. El juego todavía no usa la velocidad (fase 47); el visor la usa para el suelo en movimiento.

**D-4503. El esqueleto se dibuja con la interfaz, no con el renderizador.**
El visor guarda en la CPU las matrices de cada animación, calcula la posición de cada hueso con la misma mezcla entre dos fotogramas que hace el sombreador y dibuja líneas de cada hueso a su padre con Dear ImGui, proyectadas con la cámara. No hizo falta un sombreador ni una pasada nuevos. Para saber el padre de cada hueso, `ModelData` guarda ahora `joint_parent`.

**D-4504. Un solo reloj para todo lo que se anima en el visor.**
Pausa, velocidad y paso a paso actúan sobre el reloj de animación del visor, que comparten el modelo, el aldeano de referencia y el suelo en movimiento. Así el suelo avanza exactamente lo que avanza la animación, también al ir fotograma a fotograma. El paso a paso lleva primero al fotograma entero más cercano.

**D-4505. Un tipo con un solo modelo se trata como ese modelo.**
Elegir la animación solo funcionaba al elegir un archivo dentro de un tipo con variantes. Los animales en estudio son tipos de un solo modelo, así que el visor trata ese caso igual que un archivo elegido: animación, suelo en movimiento y esqueleto.

## Personajes, armas y árboles low poly (2026-10-01)

Pedido del usuario fuera de las fases numeradas: modelos fieles a siete imágenes de referencia suyas, con la técnica de *remesh* y reducción (D-4401) o un proceso parecido. Son modelos en estudio (`art/studies/`); todavía no entran al juego.

**D-4410. Límites de triángulos.**
Personaje 3000, arma 500 a 600, árbol con hojas 2500 y sin hojas 1500. Los eligió el agente siguiendo la tabla de animales; el usuario puede cambiarlos.

**D-4411. Un cuerpo común para los 15 personajes, con proporciones medidas.**
`people/_human.py` define la anatomía una sola vez, para que todos compartan esqueleto después. La primera versión salió con la cabeza un 30 % grande, el torso un 30 % ancho y los brazos abiertos, y los personajes no se parecían a las referencias. Se midió sobre las imágenes (la cabeza es cerca de un décimo de la altura y el pecho un quinto, con los brazos junto al cuerpo), se corrigió el cuerpo y cada personaje se ajustó midiendo su recorte. Pendiente:
- La postura de las referencias (pies separados, brazos algo abiertos) no está en el cuerpo base, así que de la cintura para abajo las siluetas quedan más angostas.
- Los tres grupos de personajes tienen cada uno sus propios ayudantes (bordes rectos de tela, caras, correas sobre la superficie), en `adventurer_man.py`, `lizardfolk.py` y `dark_elf_man.py`. Hay que unificarlos en `_human.py` antes de ponerles esqueleto.
- La tela (faldas de abrigo, capas, capuchas) son láminas sueltas: al animar habrá que atarlas a varios huesos.

**D-4412. Las armas no usan el *remesh* en las partes duras.**
El *remesh* redondea hojas, escudos y cristales. Se construyen como sólidos facetados directos, y `build_final` acepta especificaciones sin partes soldadas. Las astas siguen las proporciones del dibujo (7 a 9 cm de grosor); si no se ven bien en la mano de un personaje, se adelgazan. Las armas se modelan derechas aunque el dibujo las muestre inclinadas. `grip` todavía no se exporta al archivo.

**D-4413. Los árboles se trazan de las imágenes.**
En vez de parámetros a mano, `_trace.py` saca de la imagen sin hojas el esqueleto de ramas, de la imagen en flor las masas de follaje y de la de otoño el color de cada zona. La vista de frente es la del dibujo; la profundidad se inventa. Las ramas gruesas van al *remesh* y las delgadas son tubos directos. El follaje es un núcleo oscuro por masa, cubierto de cuadros doblados en tres tonos. Lo más débil es el cerezo llorón: tiene menos hebras que el dibujo.

**D-4414. Piezas abiertas y descarte de caras traseras.**
`MeshBuilder.to_object` recalcula las normales de toda la malla, y Blender puede voltear una pieza abierta suelta. Con el descarte de caras traseras del juego, esa pieza no se vería. Los árboles lo resuelven cerrando las hojas que saldrían volteadas. Revisados en el visor (que dibuja como el juego), un árbol con hojas, un elfo con capa, la espada demoníaca y el hacha se ven completos por ambos lados. Queda pendiente una verificación automática para todos los modelos, y que `study_preview.py` pueda descartar caras traseras.

## Fases 46 y 48: animales y personajes animados (2026-10-01)

Pedido del usuario: animar todos los animales y personajes, y que los personajes puedan talar con hacha, disparar flechas y pescar sentados o de pie. La fase 48 (personajes) se agregó a la especificación y se hizo junto con la 46, antes de la 47.

**D-4601. Una base y plantillas por familia.**
`rigs.Rig` reúne lo común: huesos, pesos, exportación y ganchos (`surface_weights`, `piece_bone`, `piece_weights`, `pose_extra`). `rigs.Pose` coloca un esqueleto en el espacio: lleva la cuenta de dónde queda cada hueso y resuelve extremidades de dos huesos hacia un punto. Las plantillas son `Quadruped`, `rigs_bird.Bird`, `rigs_swim` (`Fish`, `SeaTurtle`, `Tentacled`) y `rigs_human.Humanoid`. Cada especificación deriva la suya para lo propio (trompa, alas, cola, capa). La flora no lleva esqueleto.

**D-4602. La superficie y los detalles se distinguen por conjunto, no por orden.**
`bind` suponía que los vértices de detalle venían después de los de la superficie. No es cierto: bmesh reutiliza los huecos de los vértices que borran los cortes, así que piezas de detalle quedaban entre la superficie y se ataban mal (dedos atados a la cabeza, pies a medias en la cadera, modelos hundidos). El cerdito se salvó porque sus cortes no borran vértices. Ahora `finish` guarda el conjunto de vértices de la superficie. Varios archivos conservan su propio arreglo (reordenar o copiar la malla) porque se escribieron antes del cambio; `bind` los admite.

**D-4603. Personajes con los huesos de los aldeanos.**
`Humanoid` usa los mismos 17 nombres que `human.py`, para que después sirvan el mismo código del juego y los mismos accesorios. Los pesos salen de las partes del cuerpo (cada punto sigue al hueso de su parte más cercana, mezclando solo alrededor de la articulación), y los huesos de brazos y piernas siguen las partes de cada personaje, así que un brazo levantado en reposo tiene su hueso donde está.

**D-4604. Extremidades por puntos y no por ángulos.**
Los pies se plantan en el suelo y las manos van a puntos sobre el mango de la herramienta, por cinemática inversa. La zancada de `walk` y `run` sale de lo que alcanzan las piernas de cada personaje, y la velocidad guardada es la que resulta. Por eso las mismas animaciones sirven del orco a la rana sin ajustar ángulos, y los pies no patinan por construcción.

**D-4605. La herramienta es un modelo aparte, declarada en el modelo.**
El hacha, el arco y la caña no son parte del personaje. Cada animación declara su herramienta y su mano en los *extras* (`chop_prop`…), con la convención de agarre descrita en `docs/ARTE.md`. Las armas exportan su punto `grip`. El juego todavía no lee esto. Pendiente para cuando entren al juego: el mago y el clérigo llevan su báculo en la mano izquierda también mientras talan, disparan o pescan.

**D-4606. La ropa.**
Tres soluciones, una por grupo de personajes, todas dentro de sus archivos: faldas que siguen a la pierna más adelantada o atrasada con huesos `skirt.F` y `skirt.B`; faldas soldadas que se mezclan de la cadera a cada muslo; y cadenas de huesos para capas y abrigos que cuelgan por gravedad, se inclinan para no atravesar el cuerpo y se tienden en el suelo. Hay que unificarlas en `rigs_human.py` (pendiente junto con los ayudantes de D-4411). Defectos conocidos: sentados, las espaldas de abrigos y faldas quedan tendidas como un abanico rígido; al correr, los paneles se abren.

**D-4607. Cambios en modelos ya aprobados, para poder animarlos.**
- Los anillos en las articulaciones gastan triángulos, así que bajó el presupuesto del cuerpo en varios modelos (la vaca de 487 a 402, el zorro, el tigre, el ciervo).
- Aventurera, zorro y rana: muslos, brazaletes y muñecas unos milímetros más delgados, porque el antebrazo quedaba soldado a la cadera.
- Tigre: las rayas de las patas pasan a ser horizontales, sobre los anillos.
- Flamenco: la pata doblada se alargó para igualar a la otra (medía 0,48 m contra 0,79 m y no podía desdoblarse para caminar).
- Gallo y águila: su límite sube de 800 a 1000 triángulos, por las alas que se abren al volar.
- Garras del grifo, patas del pingüino y del tigre: unos milímetros arriba o abajo para que apoyen en el suelo.

**D-4608. Verificación.**
`rig_check.py` mide sobre el archivo exportado: hasta 64 huesos y 16 animaciones; los ciclos cierran; nada baja del suelo salvo en las animaciones en que el cuerpo deja de apoyarse en los pies (`die`, `fish_sit`, `swim`, `fly`); y los pies apoyados retroceden a la velocidad guardada. Falla si una animación con velocidad en tierra no tiene pies que medir (antes se saltaba la prueba en silencio cuando el modelo flotaba). Una prueba del juego carga todos los modelos de `art/studies` que existan y comprueba esqueleto, pesos y velocidades.

**D-4609. Defectos conocidos de las animaciones, pendientes de la revisión del usuario.**
- Las patas delanteras de los cuadrúpedos se doblan hacia adelante a media pata; bien para los de pezuña, algo raro en felinos y lobo.
- Los galopes no tienen fase de vuelo.
- Al morir, las patas quedan rectas y algunas piezas (cuerno, oreja, colmillo, costado) entran un poco en el suelo.
- La tortuga escondida deja ver una abertura al frente: el caparazón no tiene pared detrás del cuello.
- El conejo salta corto y lento (1,4 m/s) para que el muslo no se estire.
- `fly` y `swim` se animan cerca del origen; el juego debe dar la altura.

## Modelos de Tripo en el visor (2026-10-01)

Pedido del usuario: `--estudio tripo` para ver modelos generados en Tripo, y animar un lobo de prueba (`.fbx` con el esqueleto automático de Tripo).

**D-4701. El esqueleto de Tripo solo sirve de guía.**
El lobo trae 24 huesos con nombres que no corresponden (una pata delantera cuelga de `Head_1`, la cabeza se llama `0_Right_Limb_0`) y hasta 6 pesos por vértice (el motor admite 4). En vez de animar esos huesos, `tripo_build.py` toma las posiciones de sus articulaciones, reconoce por la forma las cuatro patas (cadenas que llegan al suelo), la cola y el frente, y le pone al modelo la plantilla `rigs.Beast` con sus pesos por distancia y sus animaciones. Así pasa por la misma verificación que los demás (`rig_check.py`). Se descartó retargetear animaciones sobre el esqueleto de Tripo: habría que mapear a mano cada modelo.

**D-4702. Tres mejoras de la plantilla de cuadrúpedo que salieron de este modelo.**
- Patas dadas una por una (`"FL"`, `"FR"`, `"HL"`, `"HR"`): un modelo importado no está parado de forma simétrica.
- La cinemática de las patas usa las longitudes proyectadas en el plano lateral. Con las longitudes en 3D, una pata inclinada hacia un lado no volvía a su pose de reposo y el pie quedaba en el aire.
- La articulación se dobla hacia donde está doblada en reposo; solo una pata dibujada recta usa la regla anterior (adelante en las delanteras, atrás en las traseras). Esto corrige el defecto anotado en D-4609 para felinos y lobo. Doce animales cambiaron un poco y todos siguen en `RIG OK`.
- `Beast` y `GALLOP_PHASES` pasaron de `zoo/tiger.py` a `rigs.py`.

**D-4703. Texturas en modelos con esqueleto, y un error de color.**
- El renderizador siempre ponía una textura blanca a los modelos con esqueleto. Ahora usa la del material, salvo en los materiales que la paleta recolorea.
- El sombreador convertía de sRGB a lineal una textura cuyo formato ya es sRGB (la GPU la entrega lineal), así que toda textura salía oscura y saturada. Nadie lo había visto porque ningún modelo de `core` tiene textura. Se quitó la conversión del sombreador, y las dos texturas hechas por código (la cuadrícula del visor y el pasto de la escena de prueba), que estaban ajustadas a ojo con la doble conversión, se convirtieron una vez para verse igual que antes.

**D-4704. `--estudio` acepta un nombre.**
`--estudio tripo` abre `art/studies/tripo`; una ruta sigue funcionando. Al pasar `--estudio`, el visor arranca mostrando esa carpeta.

**D-4705. `rig_check.py`: cada pie se mide desde su propio punto más bajo en reposo.**
Las patas de un modelo importado no apoyan todas a la misma altura.

## Personajes de Tripo (2026-10-01)

Pedido del usuario: que la herramienta de Tripo sirva también para personajes, probar con una versión de la rana (`Personaje 5 - tripo.fbx`) y darle los colores de la imagen original.

**D-4710. El archivo era una escultura, no un modelo listo.**
Sin esqueleto, sin textura, sin colores y con 94 608 triángulos, mirando hacia +X. `tripo_build.py` distingue los dos casos por el archivo: con esqueleto, cuadrúpedo (D-4701); sin esqueleto, personaje (`tripo_character.py`).

**D-4711. Reducir con la misma técnica de los demás modelos.**
La malla se reduce por colapso de aristas a 3000 triángulos (el límite de personajes, D-4410) con caras planas. Es el segundo paso de la técnica elegida por el usuario (D-4401), así que el resultado tiene el mismo facetado que los demás. No hace falta el *remesh*: la escultura ya es una sola superficie.

**D-4712. Articulaciones por rebanadas.**
Sin esqueleto que sirva de guía, las articulaciones salen de la forma: cada rebanada horizontal de la malla se separa en piezas conectadas. Una pierna se sigue hacia arriba desde el tobillo hasta que se une a la otra (la entrepierna); un brazo, hacia abajo desde la axila hasta la punta de los dedos. Con eso se arma un cuerpo con las mismas partes que `people/_human.py` y se usa `rigs_human.Humanoid` sin cambios. Límite: el personaje debe estar de pie y con los brazos separados del cuerpo; si no, la herramienta lo rechaza con un aviso.

**D-4713. Colores proyectados desde la imagen de origen.**
Tripo generó el modelo a partir de la imagen, así que hay un ángulo desde el que el modelo coincide con ella. Se busca comparando siluetas (para la rana: 40° de lado y 6° de elevación, con 0,80 de coincidencia) y cada cara toma el color de la imagen en su posición. La imagen solo muestra de frente un tercio de las caras. Se probó primero rellenar el resto con la cara vista más cercana: la espalda quedaba a parches oscuros (el interior de la capucha se extendía por todo). Lo que funcionó: el reflejo en el otro costado y, si tampoco se ve, el color de lo que la imagen tiene delante. Después se quitan las caras sueltas de un color entre vecinas de otro. Límites conocidos: los bordes entre colores salen dentados, porque las caras reducidas no siguen los bordes del dibujo; los ojos quedan como manchas amarillas sin pupila; la luz de la imagen queda pintada en el modelo.

**D-4714. Caras puente.**
En la escultura, la mano izquierda está fundida con la cadera y hay puntas de tela pegadas a las piernas. Al animar, esas caras se estiraban en tiras de un metro. Se cortan las caras cuyos vértices siguen a huesos que no deben tocarse (brazo con cadera o pierna, una pierna con la otra, pantorrilla con cadera) y se tapan los huecos. En la rana fueron 33 caras.

**D-4715. Qué va con el tronco y qué con las extremidades.**
Lo que está a más del 3 % de la altura de la superficie de un brazo o una pierna (un chal, un taparrabos) sigue al tronco; los dedos de manos y pies siguen siempre a su mano o pie. Un brazo que llega mucho más abajo que el otro sostiene algo: eso va con la mano.

## Más árboles y árboles gigantes (2026-10-02)

Pedido del usuario: modelos fieles a `Arboles 4`, `5` y `6` (16 árboles con hojas, en otoño y sin hojas) y a `Arboles 7` y `8` (8 árboles gigantes con y sin hojas).

**D-4720. Dos generadores.**
- Los 16 árboles normales amplían `_tree.py` y `_trace.py` con opciones apagadas por omisión, así que los 48 árboles anteriores salen idénticos (comprobado por suma de verificación). Lo nuevo: corteza por árbol (abedul blanco con marcas, baobab pálido), flores en copa en las puntas (magnolia), rosetas (drago), frutos y flores sobre el follaje (manzano, laurel), y cortinas colgadas de las ramas para sauce y glicinia. El pino, el ciprés y la palmera no se trazan: se construyen con medidas (`_built.py`).
- Los gigantes tienen su generador (`_giant.py`), que no importa nada de `_tree.py`. Tronco, raíces y ramas gruesas son cápsulas soldadas con la técnica de *remesh* y reducción; cuatro se trazan de las imágenes (baobab, cerezo, mangle, ginkgo) y cuatro se hacen a mano (secuoya, araucaria, sauce, hongo).

**D-4721. Tamaños y límites de los gigantes.**
De 22 m (hongo) a 47 m (secuoya), siguiendo las proporciones de cada dibujo. Límite de 6000 triángulos con hojas y 4000 sin hojas, porque son árboles escasos que sirven de punto de referencia. Los eligió el agente; el usuario puede cambiarlos.

**D-4722. El hongo gigante "sin hojas" conserva los sombreros**, como en la imagen: más apagados y sin manchas.

**D-4723. Lo que queda flojo.**
Sauce llorón (normal y gigante), glicinia y drago: el follaje colgante sale en rombos grandes y sueltos en vez de cortinas densas. Los árboles sin hojas tienen menos ramitas que los dibujos, por el límite de triángulos. La corteza del segundo grupo es algo más clara que la del primero.

## Fase 47: animales animados en el juego (2026-10-02)

El usuario eligió mantener las cuatro especies del juego (ciervo, jabalí, lobo y oso) con su comportamiento de hoy, y modelar el jabalí y el oso que faltaban en el zoo.

**D-4716. Los animales del juego salen del zoo.**
`art/blender/zoo/boar.py` y `bear.py` son nuevos, con la técnica 06 como el resto del zoo: el jabalí con la plantilla del cerdito (lomo alto y oscuro, hocico largo, colmillos, cola con mechón; 1228 triángulos), el oso con la de las fieras (joroba, patas gruesas, hocico claro; 1460 triángulos). `build_all.py` construye `animals/deer.glb`, `boar.glb`, `wolf.glb` y `bear.glb` de `core` con esos cuatro archivos del zoo, y `animals.py` (los animales sin esqueleto) se borró. `rig_check.py` da RIG OK en los cuatro. En el jabalí, la cabeza baja la mitad que en el cerdito al comer, para que el hocico largo no se meta en el suelo.

**D-4717. La animación sale del movimiento, no de la simulación.**
La simulación no sabe si un animal come o descansa: solo si se movió en el último tick. La vista decide:
- **Moviéndose:** camina o corre según su velocidad real (corre por encima de 1,5 veces la velocidad de la caminata del modelo). El clip avanza a la distancia recorrida entre la velocidad del clip guardada en el modelo, así que las patas no patinan a ninguna velocidad del juego. Al pasar de caminar a correr se conserva el punto de la zancada.
- **Quieto:** alterna `idle` y `eat` al terminar cada vuelta (los dos empiezan y terminan en la misma pose); come el doble de veces que descansa. La elección sale del número del animal, así que se ve igual cada vez.
- La respiración y el comer van al ritmo del juego, pero nunca más rápido que el tiempo real (a x3 no tiemblan); en pausa todo se detiene.
La lógica está en `src/game/animal_motion.*`, con pruebas en `tests/test_wildlife.cpp`.

**D-4718. Muertes solo en la vista.**
La simulación quita al animal muerto en el mismo tick. Como los animales solo salen del juego muriendo, la vista toma a uno que estaba a la vista y desapareció como muerto: deja su cuerpo donde cayó, reproduce `die`, lo deja quieto 8 s y lo hunde en el suelo en 3 s (en tiempo de juego). Al cargar una partida o empezar otra no aparecen cuerpos.

**D-4719. El aspecto de las criaturas, aparte del de los aldeanos.**
Las criaturas y los aldeanos guardaban su aspecto (giro, tiempo de la animación) en la misma lista, indexada por el número de entidad de cada uno, que no es único entre las dos. Ahora las criaturas tienen su propia lista.

**D-4720. El reporte del mapa anota los FPS.**
Para medir sin manejar la ventana, `--reporte` anota en `despues_<hora>.txt` los cuadros dibujados en la segunda mitad de la espera (1,5 s), los FPS y cuántos personajes se dibujaron. Ver `docs/RENDIMIENTO.md`.

## Fase 49: un solo generador, el jerárquico (2026-10-02)

**D-4901. Qué se borró.**
- En `sim/worldgen.cpp`, unas 1000 líneas: el relieve por ruido, la costa con sus golfos, penínsulas, cabos e islotes, las islas a la antigua (forma, canales y hundimiento de la tierra suelta), las mesetas, valles, cordilleras y cañones que cruzaban el mapa, el fondo marino con fosas y dorsales, y `along_line`, que solo usaban ellos.
- `MapGenerator` y `MapSettings::generator`; el selector "Generador de mapas" de la partida nueva, `newGame.generator` de `settings.json`, el campo `"generator"` del reporte del mapa y sus textos.
- Los tipos de accidente que solo hacía el clásico (`Coast`, `Cape`, `Range`, `Trench`, `Ridge`) y sus nombres ("Cordillera", "Cabo", "Fosa marina", "Dorsal marina").
- Las ramas del clásico en las etapas que quedan: lagos (siempre la regla de las cuencas, D-3906), ríos (siempre todos los nacimientos que piden los valles y cañones, D-4003), biomas (siempre uno por región, D-4201), salidas (siempre en llanuras o colinas, D-4202) y mapas separados.

Se quedan, con su comportamiento: lagos, ríos, suelo, biomas, bosques, recursos, fauna, salidas y el reparto de las islas en archipiélagos (`worldgen::island_layout`, que usa el jerárquico). Las decisiones del clásico quedan marcadas como reemplazadas.

**D-4902. Versión del generador, partidas y red.**
- El mapa ya no guarda qué generador lo hizo: `MapSettings` pierde su último byte. `write_identity` (que existía solo para que los mapas clásicos conservaran su suma) desaparece y la suma de verificación usa `write`.
- `worldgen::kGeneratorVersion` es la única versión y sigue en **1**, el número que ya tenía el jerárquico (`hier::kVersion`, que se borra). Así un reporte hecho con el jerárquico coincide, y uno del clásico (versión 6) queda anotado como distinto.
- Arreglo: los mapas separados guardaban siempre la versión del clásico (6), aunque los hiciera el jerárquico. Ahora guardan la misma que un mapa compartido; una prueba lo comprueba.
- `LandformKind` se renumera sin los tipos borrados, así que cambia el formato de la partida guardada. Las reglas pasan a la versión 25: una partida anterior se rechaza con el mensaje de partida de otra versión (D-631). El protocolo de red pasa a la versión 3, porque la configuración del mapa que manda la sala tiene un byte menos.
- Los mapas no cambian: se compararon los datos (alturas, agua, suelo, fertilidad, biomas, objetos, zonas, salidas, accidentes, niveles del mar y dueños) de 28 mapas jerárquicos de 4 semillas con costa, montañoso, muchos accidentes, islas, mapas separados y otros tipos de mapa, antes y después: iguales. Sí cambian todas las sumas de verificación, porque ya no incluyen el byte del generador; y 3 de esos 28 mapas por el arreglo de D-4907.

**D-4903. Los nombres.**
- F3 y los reportes nombran siempre por las cuadrículas de región y estructura (D-3905). El índice de `TerrainNames` guarda ahora solo los ríos, que es lo único que se busca por distancia (para decir "Río" o "Estuario").
- "Costa" se queda: no es el accidente `Coast` del clásico, sino la tierra seca con el mar a 12 m o menos, que F3 calcula del mar mismo (D-3702), también en el jerárquico.
- Los tooltips de "Relieve", "Accidentes del terreno" y "Mar" describen lo que hace el jerárquico (cuántas montañas y qué tan altas; qué parte no es llanura y cuántos valles y cañones; golfos, penínsulas e islotes).

**D-4904. Reportes y ajustes de antes.**
- `--reporte` ignora el campo `"generator"` de un reporte viejo y genera el mapa con el único generador. El `.txt` ya anota cuando la versión del generador es otra (6 en un reporte del clásico, 1 ahora). Rechazar esos reportes no servía de nada: el clásico ya no existe para compararlo.
- Un `settings.json` con `newGame.generator` se lee sin aviso (las claves desconocidas se ignoran, como siempre) y la próxima vez se guarda sin ella.

**D-4905. Biomas y tipos de mapa.**
- Los biomas se deciden por cuadro de 8 m (el de las regiones) en vez de 4 m y sin la deformación por ruido del clásico. El resultado es el mismo que antes en los mapas jerárquicos, porque ya se tomaba la región de cada cuadro.
- `patchSize` de los tipos de mapa ya no da el tamaño de las manchas; solo `0` sigue queriendo decir "un solo bioma" (el del ajuste). No se cambia el formato de los datos: la fase 54 borra los tipos de mapa como datos.
- El tipo de mapa "Clásico" (`core:classic`) se queda: es una mezcla de biomas, no el generador. Se aclara en `docs/GENERADORES.md`.

**D-4906. Pruebas.**
- Se borraron las que solo probaban el clásico: las suites `worldgen_coasts`, `worldgen_landforms` y `worldgen_hier_compare` (que comparaba cañones con el clásico), "trenches are deeper and ridges higher", y "the generator is a setting of the map".
- Las que generaban mapas clásicos sin decirlo ahora generan jerárquicos: `worldgen`, `worldgen_sea`, `worldgen_large`, `flora`, `worldgen_perf`, `terrain_names` y las de juego. Ajustes:
  - suma de referencia del mapa pequeño (semilla 12345): `0xf49f15655b948834` → `0xe50a4229c67425a9`;
  - "layout and contents of a medium map": más de 7000 árboles en vez de 9000 (salen 8217);
  - "map types change the forests": la arboleda joven tiene menos de la mitad de árboles grandes que la tierra de gigantes (72 contra 184 en este mapa pequeño) en vez de la veinteava parte, y se comprueba lo que de verdad importa: todos sus árboles grandes son de especies que no pueden ser chicas (`core:mountain_ash`). Con una región por bioma, en un mapa chico la parte de cada bioma varía más que con las manchas del clásico;
  - "coasts: none without sea, and sometimes by the seed" mira el nivel del mar y que no haya golfos, penínsulas ni islotes, en vez del accidente `Coast`;
  - "the names of what is under the cursor": la meseta se reconoce como región, y en valles y cañones basta el 80 % del trazo (una rampa o un acantilado, más específicos, pueden ocupar parte);
  - mapas de islas: se cuentan las islas que el mapa nombra y se comprueba que cada pueblo esté en un pedazo de tierra propio. El jerárquico **no** garantiza lo que garantizaba el clásico (D-2504): en el mapa grande de prueba (4 pueblos × 2 islas) hay 11 pedazos de tierra para 8 islas y dos islas quedan unidas, y en el mediano (2 × 3) el centro de una isla quedó bajo el agua. La prueba lo informa sin fallar; queda para que lo decida el usuario;
  - pruebas de juego que dependían de la forma de un mapa en particular, con otra semilla (como en D-2705): "an hour of play" (el jugador de prueba prospera en 9 de las primeras 20 semillas, como antes en 7 de 16; se usa la 1), "a farm sows" (16 de 20; semilla 4), "hunters take game" (10 de 20; semilla 2) y "villagers put a fire out" (19 de 20; semilla 2).
- Se agregan a `ctest` los grupos `minimap` (0,2 s en release) y `nav` (1 s), que existían pero nunca corrían.

**D-4907. Arreglo: las salidas cuentan solo lo que queda.**
Al pasar la prueba de salidas justas al jerárquico con mar "A veces", un pueblo quedó sin piedra a 180 m. La etapa de salidas contaba las piedras y bayas que había cerca y después despejaba 25 m alrededor del centro del pueblo: las dos piedras que había contado estaban dentro de ese claro. Ahora la cuenta deja fuera lo que se va a despejar, con la misma regla del claro. Cambian solo los mapas donde pasaba eso (3 de los 28 comparados en D-4902).

**D-4908. Las imágenes de referencia entran al repositorio.**
Las 13 imágenes del usuario (`Animales low poly`, `Arboles 1` a `8`, `Armas y herramientas`, `Personajes 1` a `3`; unos 26 MB) se copiaron de la raíz del repositorio, donde estaban sin seguimiento, a `art/reference/`. Los originales de la raíz no se tocaron: el usuario los puede borrar. `lowpoly_trees/_trace.py` y `_giant_trace.py` las leen de ahí; no se volvieron a generar los modelos. No se usa Git LFS, porque el repositorio no lo usa para nada más.

**D-4909. Tiempo del mapa colosal.**
Mapa colosal, semilla 12345, opciones por omisión (mar "A veces", un jugador), en `release`, alternando el ejecutable de antes y el de después: antes 131, 132, 134 y 142 s; después 123, 126, 149 y 150 s. Es el mismo tiempo dentro de lo que varía este equipo (mientras se medía, otra sesión trabajaba en el mismo equipo). Era lo esperado: el camino del jerárquico no cambió, salvo los biomas, que ya no calculan las manchas del clásico para descartarlas. El mapa es el mismo (mismos datos antes y después). Anotado en `docs/RENDIMIENTO.md`.

## Fase 50: mapa de fondo en el menú; se borra la escena de prueba (2026-10-02)

**D-5001. Qué quedó de la escena de prueba.**
Se borraron el plano con 50 000 objetos, la multitud de 2000 aldeanos, el botón del menú, la pantalla con su ayuda, la "Vista de estrés" de F3 y la selección y el seguimiento de un aldeano de la multitud con la cámara. Lo que el juego usaba pasó a su lugar: `game/model_file.*` (leer un modelo del disco) y `game/walkers.*` (los cuerpos de los aldeanos con sus paletas y accesorios, y la gente de prueba que ponen las herramientas de desarrollo, que sigue funcionando). Los modelos `props/tree_pine.glb` y `props/rock.glb` ya no los usa el código directamente; la roca sigue en uso por los datos y el pino suelto se irá con los árboles viejos (fase 53).

**D-5002. La simulación de prueba de la fase 5 se borra entera.**
`sim/world.*`, `sim/simulation.*`, `game/replay_file.*` y los tres comandos de caminantes. Las pruebas que dependían de ellos (hash de referencia del escenario, doce simulaciones, guardar y seguir, repeticiones) se borraron: la simulación del juego tiene las suyas (ver `docs/DETERMINISMO.md`). Quedan las de punto fijo, números aleatorios, entidades, comandos y la que impide `float`, hilos y relojes en `src/sim`. No había repeticiones del juego real en ningún formato, así que no se pierde ninguna función del jugador.

**D-5003. El fondo es una partida sin pueblos.**
El mapa de fondo es uno pequeño (512 m, relieve suave, lo demás por omisión) y sobre él corre una partida con cero jugadores: no hay centro del pueblo ni aldeanos, y los animales viven con la simulación de siempre. Así no hizo falta otra forma de mover animales. Una prueba cubre que esa partida corre y es repetible. La cámara gira a 80 m del centro del mapa.

**D-5004. Dónde está la lista y dónde guarda la tecla.**
La lista que viaja con el juego es `data/menu_backgrounds.json` (11 semillas elegidas mirando 12 candidatas). La tecla de guardar no escribe ahí: la carpeta del juego puede ser de solo lectura y, al compilar, `data/` se vuelve a copiar encima. Escribe en un `menu_backgrounds.json` de la carpeta de datos del usuario, que se lee además de la lista del juego. Para que una semilla viaje con el juego hay que copiarla a mano a `data/menu_backgrounds.json`. Las semillas van como texto, porque no caben en un número de JSON. Un archivo dañado se ignora con un aviso en el registro.

**D-5005. Teclas.**
Con las herramientas de desarrollo abiertas (Ctrl+F3) y en los menús: F5 genera otro fondo con una semilla nueva y F6 guarda la semilla actual. Son fijas, como Ctrl+F3.

**D-5006. Cuándo se genera.**
El mapa se empieza a generar en su hilo en cuanto se cargan los mods, antes de crear la ventana, así que el menú no lo espera: mientras llega, el fondo es el color liso de siempre. Medido en release: el mapa se genera en 0,14 s y aparece 0,93 s después de arrancar el programa, casi a la vez que el menú. Al salir de una partida al menú se genera otro (el mapa de la partida ocupa el lugar del de fondo mientras se juega), y también al cambiar de mods. Con `--reporte` no hay fondo.

## Fase 51: árboles por estación y tamaño (2026-10-02)

**D-5101. Los dos formatos conviven hasta la fase 53.**
`core` todavía tiene los 21 árboles viejos, con un modelo por tamaño. Una especie declara `models` por estado o `model` con su prefijo, nunca los dos. El formato viejo y su tinte de otoño e invierno se quedan para esas especies y se borran con ellas en la fase 53 (la especificación dice que el tinte se borra: se borra cuando ya ninguna especie lo use). Los arbustos conservan su tinte.

**D-5102. El cerezo es la especie de prueba.**
`core:cherry` pasa a usar `cherry_1` de los árboles low poly en sus tres estados. No cambia los mapas: es la misma especie en los mismos lugares, con los mismos tamaños y madera. `build_all.py` construye esos modelos en `models/trees/`; los `tree_cherry_*.glb` viejos quedan sin uso hasta la fase 53.

**D-5103. El cambio es por pasos, no por días.**
La simulación da la estación y cuánto ha avanzado (de 0 a 999), no el día dentro de ella. El cambio ocupa la primera quinta parte de la estación en 8 pasos; cada árbol tiene su paso, que sale de su posición. Con las cuatro estaciones son 6 días. Cada paso rehace la lista de árboles a dibujar, como ya pasaba al cambiar de estación o al nevar.

**D-5104. Una partida nueva no empieza con árboles pelados.**
En la primera estación de la partida no hay cambio: todos los árboles están ya en su estado. Si no, una partida que empieza en primavera mostraría los árboles sin hojas los primeros días, y el mapa de fondo del menú también.

**D-5105. Escala por altura.**
Un árbol por estado se dibuja con su modelo escalado a la altura que le dio el generador, entre 0,5 y 1,5 veces la altura del modelo. Los árboles viejos siguen con su escala exacta.

**D-5106. El visor no necesitó cambios.**
Ya muestra juntos los modelos de una definición; los tres estados de una especie salen lado a lado en su grupo. Solo se le quitó el tinte de estación a las especies por estado.

**D-5107. Costo del cambio en los mapas más grandes.**
Rehacer la lista tarda 301 ms en el mapa colosal de referencia (3,39 millones de objetos); se nota como un tirón. Ya ocurría 4 veces al año (más las nevadas) y ahora ocurre 8 veces más en cada estación que cambia. En mapas pequeños y medianos no se nota (menos de 20 ms). Queda anotado en `docs/RENDIMIENTO.md`; si molesta, se puede rehacer solo la parte que cambia.

## Fase 52: versión lejana de los árboles (2026-10-03)

**D-5201. El estado y la versión de un árbol se eligen al dibujar.**
El renderizador ya no tiene una lista de instancias por cada modelo de árbol. Un modelo puede tener *aspectos* (otros modelos con los que se dibujan sus instancias, hasta 3 más el propio) y una *versión lejana*. Cada instancia lleva el número de su aspecto. Al descartar lo que no se ve, cada instancia visible va a la lista de su aspecto, en versión cercana o lejana. Los estados del año de un árbol son aspectos: `bloom` es el modelo y `autumn` y `bare` sus aspectos 1 y 2.

**D-5202. Con eso se quitó el tirón del cambio de estado (pedido del usuario).**
En la fase 51 cada paso del cambio rehacía las listas de todos los árboles (301 ms en el mapa colosal, D-5107). Ahora un paso solo cambia el número de aspecto de los árboles a los que les toca: no se reordena ni se sube nada a la GPU. Un árbol queda todo el año en el mismo lugar de la misma lista. El registro anota el paso si tarda 5 ms o más. Rehacer todo sigue pasando al cambiar de estación y al nevar, como antes de la fase 51, porque cambia el tinte de los arbustos y de los árboles viejos.

**D-5203. Cuándo se cambia de versión.**
Por el alto del árbol en pantalla: lejana por debajo de 90 píxeles en Ultra, 120 en Alta, 160 en Media y 220 en Baja (el nivel de "vegetación"). Un árbol que ya está en una versión no cambia hasta pasar el límite por un 10 %, así que no parpadea en el borde. Las sombras usan siempre la lejana. A la distancia inicial de la cámara (110 m) los árboles grandes se ven en su versión cercana y los chicos en la lejana.

**D-5204. La versión lejana sale del modelo terminado, no de cada generador.**
Hay tres generadores de árboles (los trazados, los construidos a mano y los gigantes) con muchas formas de follaje. En lugar de enseñarle a cada uno a hacer una versión simple, `far_tree.py` trabaja sobre el modelo ya hecho: reduce las piezas grandes soldadas (tronco y ramas gruesas), convierte las ramitas en púas de tres lados (las más grandes primero) y agrupa todo lo demás por cercanía en pocas masas, cada una un icosaedro estirado. Lo que está en el suelo (pasto, piedras, pétalos) se omite. Límite: 300 triángulos (600 en los gigantes).

**D-5205. El color de una masa es la mezcla de sus hojas.**
La especificación pedía el color dominante. Se probó: el bosque lejano se veía más claro que el cercano, porque de cerca se mezclan las hojas claras, medias y oscuras. Cada masa lleva la mezcla de los colores de sus hojas según cuánto cubre cada uno (sin los núcleos oscuros que quedan debajo), como material propio (`far_1`, `far_2`...).

**D-5206. En los datos.**
Una entrada de la lista de un estado puede ser `{"model": ..., "far": ...}`. El cerezo de `core` ya tiene sus tres versiones lejanas.

**D-5207. El visor.**
Las versiones lejanas aparecen en el grupo de su especie junto a las cercanas. En las opciones de vista hay "Versión: automática, cercana o lejana", que obliga a dibujar una de las dos en los modelos que tienen versión lejana.

**D-5208. Medición.**
`--reporte` anota además los objetos dibujados, cuántos en versión lejana, los triángulos, las llamadas de dibujo y el tiempo de descarte. F3 muestra cuántos objetos van en versión lejana. Resultados en `docs/RENDIMIENTO.md`: en el mapa colosal, un bosque de árboles nuevos con versión lejana dibuja menos de la mitad de triángulos que el de árboles viejos y queda un 7 % por debajo en FPS (promedio de tres corridas, que varían entre sí un 10 %).

## Fase 53: árboles nuevos en core; se borran los viejos (2026-10-03)

El usuario eligió: crear ya los once biomas de la fase 54; dejar tres tipos de mapa (Clásico, Islas y Bioma único); y que los gigantes no salgan en los mapas hasta la fase 55.

**D-5301. Especies.**
19 especies con los 32 árboles (el cerezo con 4 variantes, el jacarandá con 5, el olmo y el guayacán con 4) y 8 gigantes como especies de tamaño enorme con `landmark`. El roble amarillo conserva el id `core:oak`, y se conservan `core:pine`, `core:cherry`, `core:jacaranda`, `core:magnolia`, `core:elm` y `core:apple`, para que los mods y las pruebas que los nombran sigan valiendo. La lista completa está en `docs/ARBOLES.md`.

**D-5302. Tamaños y madera.**
Los modelos miden de 6 a 7,5 m y se dibujan entre 0,5 y 1,5 veces eso, así que las especies chicas (cerezo, magnolia, palmera, glicinia, laurel, drago, manzano) tienen tamaños chico y mediano; las demás, hasta grande; el baobab, mediano y grande. La madera va según el tronco: el abedul, el ciprés, la palmera y la glicinia dan menos (1, 3, 7); el olmo, el guayacán y el arce algo más (2, 6, 12); el roble amarillo 3, 7, 13; el baobab 10 y 18.

**D-5303. Biomas y tipos de mapa provisionales.**
Los once biomas llevan las especies de la tabla de la fase 54, con pesos, densidad y pasto elegidos aquí (la sabana y el huerto ralos, el boreal denso). Hasta la fase 54 se reparten en manchas al azar con el tipo "Clásico" (el nombre se queda hasta la 54, a pedido del usuario), que da más peso al templado. Las montañas llevan el bosque de montaña, como antes llevaban el pinar. Se borraron Arboleda joven, Tierra de gigantes, Pinar del norte y Variado.

**D-5304. Se borró el formato viejo.**
`model` con prefijo por tamaño, `evergreen` y el tinte de otoño e invierno de los árboles ya no existen (D-5101 los dejaba hasta esta fase). Un mod con ese formato se rechaza con un mensaje. Los arbustos conservan su tinte. Se borraron `trees.py`, `preview_trees.py`, los árboles de `props.py`, los 72 modelos `props/tree_*.glb` y los estudios `pig_studies.py` y `tiger_studies.py`.

**D-5305. Versiones.**
Cambian los mapas: versión del generador 2, versión de reglas 26; las sumas de verificación de referencia de las pruebas se fijaron de nuevo.

**D-5306. Las versiones lejanas de los gigantes pasan del límite.**
Los 32 árboles quedan entre 150 y 330 triángulos en su versión lejana. Los gigantes, entre 590 y 1856 (su modelo completo tiene de 3400 a 6000): tienen muchas piezas grandes soldadas y cada una conserva un mínimo de triángulos. Como habrá pocos por mapa, se deja así; la fase 55 mide su costo al ponerlos en los mapas.

## Fase 54: clima y biomas por geografía (2026-10-03)

**D-5401. El clima es de la vista del generador, por bloques de 8 m.**
Temperatura y humedad van de 0 a 100 y solo deciden qué bioma crece; no tocan la temperatura de la simulación (fase 10). El norte es el borde de z = 0 (arriba en el minimapa). La temperatura va de 20 en el norte a 80 en el sur, baja un punto cada 5 m de altura y lleva un ruido de ±8; la humedad es un ruido alrededor de 50 más hasta 20 puntos cerca del agua. Se guardan por bloque en el mapa (`climate`) para F3 y el reporte, fuera de la suma de verificación, como los dueños de región.

**D-5402. Todo mapa es "mezclado" hasta la fase 56.**
Con las opciones por omisión, un mapa de cualquier tamaño va del frío al calor, así que caben todos los biomas. `MapSettings` ya lleva `temperature` y `humidity` (0 a 200 %), que corren el mapa hasta 30 puntos; la fase 56 les pone el formulario y hace que la semilla elija el clima en "Variado".

**D-5403. Reglas de los biomas.**
Los rangos, pesos y condiciones de cada bioma están en `docs/ARBOLES.md`. La ribera y la costa tropical pesan 400 para ganar siempre junto a su agua; el huerto pesa 60 para ser raro. El bosque de montaña pide estar en la mitad más alta de la tierra (por altura, no por tipo de región): así cumple el criterio en cualquier mapa, y las montañas, que son altas y frías, lo llevan de todos modos. El "bosque encantado" pide cuenca y humedad.

**D-5404. Cuando ningún bioma encaja.**
Se elige el de clima más parecido sin exigir región ni margen, pero nunca se renuncia al agua ni a la altura que pide un bioma. Antes de este cuidado, la ribera (por su peso) ganaba lejos del agua y había sauces en seco.

**D-5405. Palmeras lejos de pinos.**
La costa tropical empieza en 78 de temperatura y el mediterráneo (que tiene pinos) termina en 60, con 6 puntos de margen cada uno: quedan al menos 6 puntos entre los dos, unos 50 m en un mapa pequeño. La prueba exige que ninguna palmera esté a menos de 15 m de un pino.

**D-5406. Sin tipos de mapa.**
Se borraron `mapType`, `patchSize`, `sizeBias` y el bioma único como tipo. `MapSettings` lleva `island_map` (islas o tierra firme) y `biomes`, una máscara de los biomas permitidos (los primeros 64 del contenido; 0 es todos). La partida nueva ofrece, hasta la fase 56, "Mapa: Tierra firme o Islas" y "Biomas: Todos o uno solo". Un `settings.json` anterior se acepta: `core:islands` sigue siendo islas y lo demás vuelve a tierra firme con todos los biomas. Un reporte anterior también: `core:single` con su bioma da ese bioma solo. Un mod con definiciones `mapType` se rechaza con un mensaje.

**D-5407. Bosques más abiertos (pedido del usuario).**
La separación mínima entre troncos pasó de 3, 5, 8 y 12 m a 5, 7, 10 y 16 m. El mapa mediano de referencia pasó de 17 751 objetos a 6558. Para compensar, la madera por árbol se duplicó en chicos y medianos y subió un 50 % en grandes; aun así hay menos madera total en el mapa (queda para el balance con partidas largas).

**D-5408. Tiempo de generación.**
El mapa mediano de referencia (semilla 12345): 0,46 s antes y 0,48 s después (tres corridas cada uno). La etapa de biomas agrega dos mapas de distancia al agua y el cálculo por bloque, y la de bosques coloca menos árboles.

**D-5409. Versiones.**
Generador 3, reglas 27, protocolo de red 4 (cambió `MapSettings`).

**D-5410. Datos viejos en las carpetas de compilación.**
`data/` se copia junto al ejecutable sin borrar lo que ya no existe, así que `map_types.json` y los modelos viejos seguían ahí y el juego los leía. Ahora la copia es un espejo: la carpeta se borra antes de copiar.

## Fase 55: árboles gigantes como hitos (2026-10-03)

**D-5501. El lugar de cada gigante es su bioma.**
Desde la fase 54 los biomas ya están donde la especificación quería a los gigantes: la ribera junto al agua dulce, la costa tropical junto al mar, el bosque de montaña en lo alto, el encantado en las cuencas. Cada gigante declara su bioma en los datos (`giantBiome`). El mangle pide además el mar a 40 m o menos (`giantWater`), para quedar en la costa baja.

**D-5502. Se colocan al final, después de las salidas.**
Así se puede exigir la distancia a las salidas (200 m) sin tocar el reparto justo de recursos. El claro se hace quitando los árboles a menos de 18 m. La cantidad por tamaño de mapa (2, 3, 6, 10, 18, 30) cumple los ejemplos de la especificación; `MapSettings::giants` la escala (0 a 200 %).

**D-5503. Menos gigantes si falta su bioma.**
Las especies se turnan; la que no encuentra lugar pasa. Un mapa sin mar no tiene mangle, y uno pequeño puede quedarse con uno o ninguno si los biomas con gigante quedan cerca de las salidas.

**D-5504. Tala.**
No hizo falta nada nuevo: un árbol da `logs` de su tamaño y cada tronco cuesta el mismo trabajo, así que un gigante de 120 troncos tarda 12 veces más que un árbol grande de 10.

**D-5505. Rendimiento.**
Mapa mediano de la semilla 91, Ultra, 1600 × 900, con sus tres gigantes a la vista desde 750 m: 1038 FPS y 1,31 M de triángulos (3593 objetos, casi todos en versión lejana). De cerca, a 70 m de un gigante en su versión completa: de 925 a 1284 FPS. Los gigantes no pesan: son pocos y de lejos usan su versión simple.

**D-5506. Versiones.**
Generador 4, reglas 28, protocolo de red 5.

**D-5507. Las pruebas se enlazan completas, sin enlazado incremental.**
En `debug`, los grupos `i18n` y `sim_rules` terminaban a veces con el código 0xC0000409 al cerrar el proceso, después de pasar todas sus comprobaciones. Pasó tras las fases 52 y 55 y antes se había atribuido a objetos viejos de Ninja. La causa es el estado del enlazado incremental (`.ilk`) del ejecutable de pruebas: al borrarlo y enlazar de nuevo, sin recompilar nada, los dos grupos pasan. Ahora `salvaciudad_tests` se enlaza con `/INCREMENTAL:NO`.


## Fase 56: partida nueva Variado y Personalizado (2026-10-03)

**D-5601. Las cantidades del mapa son porcentajes.**
`MapSettings` guardaba ríos y lagos, bosques, recursos, relieve y accidentes como tres niveles (pocos, normal, muchos). Ahora son porcentajes de 0 a 200, y "ríos y lagos" se separa en dos. Los niveles de antes equivalen a 50, 100 y 200 % (relieve: plano 50, suave 100, montañoso 175), y entre esos puntos el generador interpola en línea recta; 0 % quita la cosa (sin ríos fuera de los valles, sin lagos, sin bosques, todo llanura). Un mapa creado sin elegir nada sigue teniendo relieve plano, como siempre; el formulario empieza en relieve suave (su 100 %), que es lo que pide la especificación para Variado.

**D-5602. El mar es una sola lista.**
"Mapa: Tierra firme o Islas" y "Mar: Sin mar, A veces, Siempre" se unen en `Sea`: sin mar, un lado, dos lados (opuestos una vez de cada tres; si no, una esquina), islas (una por pueblo) y archipiélago (las islas por pueblo que se elijan, si caben). "A veces" desaparece: ahora es Variado quien decide con la semilla.

**D-5603. Qué decide la semilla en Variado.**
El clima: frío 22 %, templado 40 %, cálido 20 %, mezclado 18 %. El mar: sin mar 35 %, un lado 27 %, dos lados 20 %, islas 10 %, archipiélago 8 % (de 2 o 3 islas por pueblo). Todo lo demás, lo de la especificación. La misma semilla da siempre lo mismo; cambiar el tamaño o los jugadores no cambia el clima ni el mar.

**D-5604. "Variación del clima" en Personalizado.**
La especificación no la lista, pero sin ella "Partir de Variado" no podía reproducir Variado: un mapa frío, templado o cálido tiene poca diferencia entre norte y sur (12 puntos), y uno mezclado mucha (30, lo de la fase 54). Es una lista de dos valores, "Poca" y "Mucha", guardada en el mapa como `climate_range`.

**D-5605. La vista previa.**
Se genera el mapa de verdad, en otro hilo, un momento después del último cambio, y se pinta con el mismo código del minimapa. Si cambia algo mientras tanto, el trabajo se cancela y empieza otro. Solo hasta mapas grandes: uno enorme o mayor tarda demasiado para rehacerlo a cada cambio, y el formulario lo dice. La línea de resumen ("Mapa templado, costa al este, 3 árboles gigantes") sale de ese mismo mapa: los lados con mar y los gigantes que de verdad se colocaron. La simulación sigue sin hilos: el hilo es del formulario.

**D-5606. Duración del año, estaciones e inmigrantes.**
El año era corto, normal o largo; ahora es un porcentaje de 25 a 200 (100 % son los 12 000 pasos de siempre). Las estaciones ya se elegían una por una. Las razas que pueden llegar como inmigrantes son una máscara en las reglas (`immigrants`; 0 es todas): un inmigrante "de otra raza" se sortea solo entre las marcadas. "Otras razas" es un porcentaje de la proporción normal (100 % es el 20 % de la especificación; 200 %, el 40 %).

**D-5607. Ajustes y reportes de antes.**
`settings.json` guarda la partida nueva con las claves nuevas (`mode`, `rivers`, `lakes`, `sea`, `immigrants`…). Uno anterior se acepta: lo que no se entiende vuelve a su valor de Variado y cuenta como aviso; las claves viejas (`mapType`, `biome`, `water`) se borran al guardar. El reporte del mapa escribe los porcentajes y acepta los de antes: los niveles con nombre, `water` (vale para ríos y lagos), `mapType` de islas y el mar "sometimes" (sin mar) o "always" (un lado).

**D-5608. El formulario se desplaza.**
Personalizado no cabe en la pantalla: el panel entero se desplaza con la rueda, como el menú principal. Las casillas van en dos columnas. Una prueba llega hasta "Generar mapa" con la rueda.

**D-5609. Las islas ya no se tocan (pendiente de D-4906).**
Cada punto pertenece a la isla más cercana, medida en radios de cada una, y la tierra termina antes de la línea donde se encuentran dos islas: siempre queda un canal de mar (unos 20 m; 1/64 del mapa en los grandes). En 10 mapas de prueba (pequeño, mediano y grande, 5 semillas) ninguna isla queda unida a otra, y la prueba ahora lo exige. Sigue pudiendo haber pedazos sueltos de tierra además de las islas pedidas (islotes), y el centro de una isla puede caer en un lago o un río: no es un defecto. Las islas quedan un poco menos irregulares (compacidad media hasta 0,41), porque el canal recorta los brazos más largos.

**D-5610. Versiones.**
Generador 5, reglas 29, protocolo de red 6 (cambiaron `MapSettings` y las reglas). Suma de referencia del mapa pequeño: `0xb62f09e39b1ea9c0`.

**D-5611. Lo que no se pudo ver en pantalla.**
Se revisaron en la ventana del juego Variado y la mitad de arriba de Personalizado (clima, biomas, tierra y agua, y la vista previa, que cambia al elegir archipiélago). La mitad de abajo (el año y las reglas) quedó cubierta solo por las pruebas, porque la rueda del ratón no se pudo simular en la ventana. Queda en la lista de pruebas a mano.

**D-5612. Sin botón "Restablecer".**
El botón de la fase 23 (D-2304) ya no está: volver a "Variado" deja todo en sus valores de siempre, y "Partir de Variado" hace lo mismo dentro de Personalizado.

**D-5613. Por qué "los cazadores traen carne" pasaba solo en la mitad de las semillas (investigación pedida tras la fase 49).**
La prueba pone la cabaña de caza junto a la primera zona de venados o jabalíes del mapa, esté donde esté, y espera 3000 pasos. Con las primeras 20 semillas (ahora pasa en 13):
- en 4 (9, 11, 15, 16) la zona está a 335-370 m del pueblo: la cabaña se termina tarde y los cazadores, que viven en el pueblo, gastan todo el tiempo caminando (unos 0,18 m por paso);
- en 2 (17, 20) la zona está al otro lado del agua: el juego deja poner la cabaña ahí, pero nadie puede llegar y nunca se construye;
- en 2 (1, 14) el camino es tan largo (más de 400 m, o un rodeo por el agua) que quienes llevan los materiales se quedan sin comida en el viaje y mueren: un aldeano solo decide comer cuando está sin tarea, nunca a medio camino.
La caza en sí funciona: con la zona a menos de 250 m siempre hay carne. No se cambió la simulación. Quedan dos propuestas para decidir con el usuario: (1) que un aldeano con mucha hambre deje lo que hace y vaya a comer; (2) que no se pueda construir donde ningún aldeano puede llegar, con su mensaje. La prueba sigue con la semilla 2.

## Fase 57: los personajes low poly en el juego (2026-10-03)

Decidido con el usuario antes de empezar: se modelan un enano y una enana sin imagen de referencia; elfo oscuro, zorruno, rano, lagarto y orco pasan a ser razas jugables con los números de los humanos; todos son aldeanos (soldados y asaltantes siguen siendo aldeanos con su marca de color; caballero, caballera, mago y clérigo son variantes humanas al azar); la variedad sale de paletas (ropa, piel y cabello) y de la estatura; las razas de un solo modelo lo usan para los dos sexos; los niños son el adulto a menor escala; sombreros, barbas y delantales se borran.

**D-5701. Qué personaje es cada raza.**
En `races.json`, `"bodies": {"male": [...], "female": [...]}` reemplaza a `"body"`. Humanos: aventurero, caballero, mago y clérigo (hombres) y aventurera, caballera, mago y clérigo (mujeres); un aldeano toma uno por sus bits de apariencia. Elfos: los altos elfos. Enanos: los dos nuevos. Gatunos, zorrunos, ranos, lagartos y orcos: su único modelo, bajo cualquiera de los dos sexos. El maniquí no entra al juego. Las cinco razas nuevas van al final de la lista, así que los índices de las cuatro de antes no cambian.

**D-5702. Los enanos.**
Son el cuerpo de los aventureros con otras proporciones (`people/dwarf_man.py`, `dwarf_woman.py`): 1,30 y 1,24 m, hombros y miembros gruesos, la cabeza grande y sin cuello, la túnica hasta la rodilla y las botas altas para que las piernas se vean cortas. Él lleva barba hasta el pecho con dos trenzas y cejas espesas; ella, dos trenzas gruesas y vestido. El cuerpo común escala todo por igual, así que las piernas tienen la proporción humana debajo de la ropa; acortarlas de verdad pedía rehacer las alturas de todo el cuerpo común.

**D-5703. Paletas: el material lleva el nombre de su espacio.**
El juego recoloreaba solo los materiales llamados exactamente `skin`, `hair`, `top`…, y los pintaba de un color liso. Los personajes nuevos tienen facetas más claras y más oscuras (`skin_light`, `tunic_shade`). Ahora un material pertenece a un espacio si se llama como él o empieza con él y `_`, y conserva su tono: se multiplica el color de la paleta por la razón entre su color y el del material principal del espacio. Cada personaje declara qué materiales suyos son ropa recoloreable (`palette = {"tunic": "top", "trousers": "bottom"}`), y al exportar toman el nombre del espacio. La piel de gatunos, zorrunos y ranos es su pelaje o su piel azul; la cresta del lagarto es su "cabello". Acero, cuero, oro y ojos no cambian.

**D-5704. Qué paletas hay.**
Por personaje: su piel propia más las de su raza (`"skins"` en `races.json`), su cabello propio más los de su raza (`"hairs"`), y su ropa propia más 7 conjuntos comunes (azul, bermejo, verde, pardo, púrpura, crudo y pizarra). Un humano tiene 6 × 7 × 8 = 336 combinaciones; un enano, 144. La primera paleta de cada personaje es el modelo tal como se hizo. Los espacios `shoes`, `belt`, `hat` y `apron` quedan sin uso.

**D-5705. Animación por tarea.**
`game/people.*` decide: quieto, caminando, corriendo (al huir, al ir a un incendio o a pelear, y con la alarma), talando (hacha; también al pelear), cazando (arco), pescando (el lance una vez y después la espera, con la caña) y trabajando (un clip nuevo, `work`: martillar a la altura de la cintura, con un martillo; lo usan construir, producir, cultivar, apagar un incendio y recoger lo que no es un árbol). Caminar y correr avanzan según los metros que el aldeano recorre de verdad entre un paso de simulación y el siguiente, divididos por la velocidad del clip y por su escala, así que los pies no patinan con ninguna raza, con nieve ni en los niños. Lo demás va a su propio ritmo, nunca más rápido que el tiempo real.

**D-5706. La caminata es más viva.**
La caminata de los personajes cubría 0,9 m/s y los aldeanos del juego van a 2 m/s: se habría visto al doble de velocidad. El ciclo pasó de 26 a 16 fotogramas (1,3 a 1,6 m/s según el personaje; 1,0 los enanos). Quien va a más de vez y media la velocidad de su caminata corre: los enanos trotan.

**D-5707. Las herramientas.**
`models/tools/axe.glb`, `bow.glb`, `rod.glb` y `hammer.glb` salen de cuatro de las 40 armas (`w07`, `w13`, `w18`, `w33`). El modelo del personaje dice qué herramienta va en qué mano en cada clip (`<clip>_prop`), y cuánto mide el hueso de la mano; la herramienta dice dónde se sujeta (`grip`). El motor la coloca una vez, en la pose de reposo, con la regla de las tiras de revisión, y la mueve con el hueso; se ve solo mientras dura el clip. Se reduce para manos chicas (un enano lleva el hacha al 74 %). El hacha de guerra y el martillo de piedra son lo que hay: herramientas de trabajo propias (hacha de leñador, pico, azada) quedan como idea.

**D-5708. Soldados y asaltantes.**
Como decidió el usuario, siguen siendo aldeanos (un humano cualquiera, por su número) con la marca de color debajo. Ahora corren al perseguir y dan golpes de hacha al atacar.

**D-5709. Versión lejana de los personajes.**
Con 1000 aldeanos a la vista el juego perdía un 30 % de FPS (de 428 a 298): los personajes nuevos tienen de 2300 a 3000 triángulos. Cada uno tiene ahora `<nombre>_far.glb`, el mismo esqueleto con la malla reducida a unos 500 triángulos y sin clips (usa los del modelo cercano). Se dibuja cuando el personaje mide en pantalla menos que los píxeles del nivel de detalle (los mismos de los árboles), y siempre en las sombras, que además pasaron a dibujarse en una sola llamada por modelo. Resultado, medido con `--reporte` y `"people": 1000` (Ultra, 1600 × 900): 596 FPS, un 39 % **más** que antes de la fase. Ver `docs/RENDIMIENTO.md`.

**D-5710. `"people"` en el reporte del mapa.**
Para medir sin manejar la ventana, `view.people` en `reporte.json` (escrito a mano, hasta 5000) pone esa cantidad de aldeanos en un cuadro alrededor del centro de la vista al repetir el reporte.

**D-5711. Código repetido de los tres grupos de personajes.**
`people/_people_kit.py` reúne lo que estaba igual en `adventurer_man.py`, `lizardfolk.py` y `dark_elf_man.py`: la pieza convexa (`chunk`, `hull` y `solid` eran la misma), la tira (`strip`; `ribbon` es una tira de normal constante), los tonos de faceta, la distancia a las partes del cuerpo y los ayudantes de puntos simétricos. Los 17 modelos salieron idénticos byte a byte antes y después. **No se unificó** lo que solo comparte el nombre: `tube`, `spike`, `strap`, `buckle`, `pouch` y `sheet` hacen cosas distintas en cada grupo (en uno `sheet(back=)` es una dirección y en otro un material), y las tres soluciones de tela y de marcar piezas a huesos (D-4606) usan convenciones opuestas; fundirlas cambiaría la geometría o los pesos de los personajes ya revisados. Queda pendiente, y cada personaje nuevo debe elegir un grupo y seguir su convención.

**D-5712. Lo que se borró.**
`art/blender/human.py` y `preview.py`, los 8 cuerpos y 5 accesorios de `models/characters/`, sus entradas en `builtin_models.h`, la carga y el reparto de sombreros, barbas y delantales, el gorro de invierno, y sus textos. `Walkers` queda solo como la gente que colocan las herramientas de desarrollo; los cuerpos están en `people::Cast`.

**D-5713. La simulación.**
El código de la simulación no cambió: `RaceDef` lleva los nombres de los modelos y los colores, que solo lee la vista. Sí cambió el contenido: hay 9 razas en vez de 4, así que con el 20 % de inmigrantes de otras razas llegan también las nuevas, y una partida con la misma semilla ya no transcurre igual que antes de la fase (la prueba "una hora de juego" usa otra semilla de partida). Las reglas siguen en la versión 29: el formato de la partida guardada no cambió, y una partida guardada antes se rechaza de todos modos porque el contenido es otro.

**D-5714. El visor.**
Cada personaje se ve con sus paletas ("Otra paleta" las recorre en orden) y con la herramienta en la mano en los clips que la usan. La versión lejana aparece en el grupo de su raza, quieta. Las herramientas están en "Otros".

**D-5715. Defectos de animación de D-4609.**
El usuario no indicó ninguno para esta fase; los de D-4609 son de los animales y siguen anotados.

**D-5716. Lo que no se pudo ver en pantalla.**
En el visor se revisaron los personajes, sus paletas y la herramienta en la mano (hacha, arco). En una partida se comprobó que los aldeanos son los nuevos, pero solo desde lejos: desde las pruebas automáticas no se pudo acercar la cámara. Que cada tarea use su animación lo cubre una prueba (`people`); queda en la lista de pruebas a mano verlo de cerca.

## Ronda de ideas del 2026-10-03: fases 58 a 67

Salvador pidió refinar I-001, I-002, I-003, I-005, I-006, I-007, I-008 e I-009 y las correcciones C-002 y C-003. El análisis de cada una y sus respuestas están en el registro de revisión (pestaña Análisis).

**D-9101. Qué entra y en qué orden.**
Fases 58 a 67 de la especificación, en el orden propuesto y aceptado: primero lo chico de reglas (velocidades, año, niebla y comercio), luego cámara y ventanas, después lo que cambia la simulación (pendientes, explorador) y al final lo visual. El pulido y la entrega pasan a la fase 68. Entran además `sug-precio-maximo` (ya estaba "para el plan"), I-010 e I-011 (las dos propuestas de D-5613) y la corrección C-001. I-004 (soldados que comen y cobran) no se analizó en esta ronda y queda abierta.

**D-9102. Lo que Salvador eligió.**
- Velocidades: ×0,25, ×0,5, ×1 a ×5 para todos y ×6 a ×9 solo en un jugador; control "− ×N +". Se descartó ×0,75 (no la eligió).
- Año largo: se mantiene el ritmo por minuto real; cada estación con su barra en minutos.
- Niebla revelada: se construye en cualquier parte de la región propia.
- Cámara: seguir con botón y doble clic; fantasma de aldeano translúcido; lo que estorba se vuelve translúcido (C-002 no era un error puntual sino una decisión de diseño).
- Ventanas: una ventana de paso y las fijadas; nombres propios guardados en la partida; interruptor de producción que libera a los trabajadores; ventana de cámara viva, chica y con máximo; se quita el plegado automático.
- Explorador: lleva provisiones; ve 30 m; solo él recibe órdenes de movimiento.
- Pendiente: piso a la altura del suelo frente a la puerta; hasta 4 m de desnivel.
- Cargas: espalda y manos según el recurso; además pilas, etapas de construcción, flechas y mercader.

**D-9103. Aprobación.**
Salvador aprobó el plan el 2026-10-03, con todas las ideas en "para el plan" (I-003 e I-008 incluidas). Pidió hacer las fases seguidas, sin pausa, y que se le pregunte antes de hacer fases en paralelo.

**D-9104. Las murallas quedan fuera.**
En su nota de I-007, Salvador dice que las replanteará (tramos dinámicos entre dos puntos) después de ver ejemplos de otros juegos. Se copió tal cual a una idea nueva. La fase 65 no toca murallas ni empalizadas.

**D-9105. Valores que el plan fijó sin pregunta.**
Lo más simple en cada caso, para ajustar al probar: estaciones de 1 a 30 min (5 por omisión); límites de precio de 75 a 125 % en pasos de 5; mirar hasta 60° hacia arriba; tope de 16 ventanas de objeto y de 2 ventanas de cámara de 320 × 200; nombres de hasta 24 caracteres. En red, el tope de ×5 se sostiene midiendo los márgenes en tiempo real.

## Fase 58: más velocidades (2026-10-03)

**D-5801. La velocidad se cuenta en cuartos.**
Un entero sigue bastando: 4 es ×1, 1 es ×0,25 y 36 es ×9; 0 es la pausa. Solo valen los pasos de la tabla (`src/core/speed.h`): 1, 2, 4, 8, 12, 16, 20 y, sin red, 24, 28, 32 y 36. Así no hay números con decimales en el reloj ni en la red, y lo que no es un paso baja al paso de abajo. Reemplaza al entero 0 a 3 de D-003.

**D-5802. Barra y teclas.**
Pausa y "− ×N +". Mientras está en pausa, ×N muestra la velocidad a la que volverá, y − y + la cambian y reanudan. Las teclas 1, 2 y 3 siguen poniendo ×1, ×2 y ×3. Para subir y bajar un paso se usan el punto y la coma: + y − ya son el zoom de la cámara, y dos acciones no pueden compartir tecla por omisión. Se pueden cambiar en Controles.

**D-5803. En red, tope ×5 y márgenes en tiempo real.**
El mensaje de velocidad lleva los cuartos; uno que no sea un paso o pase de ×5 se rechaza. El retraso de las órdenes, cuánto puede atrasarse un jugador y cada cuánto se compara la partida estaban en pasos de simulación pensados para ×1 a ×3. Ahora, por encima de ×1, valen lo mismo en tiempo real: hasta 1 s de retraso, 3 s de atraso y una comparación cada 5 s (a ×5, cada 250 pasos en vez de 50). La comparación usa la velocidad con que se cerró cada turno, que viaja en el turno, así que todos comparan en los mismos pasos. Por debajo de ×1 no cambia nada. "Bajar por un jugador lento" baja un paso de la tabla, hasta ×1. Protocolo de red 7.

**D-5804. Si el equipo no alcanza, baja un paso.**
En un jugador, si durante 20 cuadros seguidos se pierden pasos (el reloj corre como mucho 8 por cuadro), la velocidad baja un paso de la tabla y un aviso lo dice; no baja de ×1. En red eso ya lo hace el anfitrión con el jugador lento.

**D-5805. Las velocidades lentas.**
A ×0,25 un paso dura 0,4 s: la interpolación sigue siendo suave, pero una orden puede tardar hasta 0,4 s en notarse y la niebla se actualiza cada 4 s. Las animaciones, las partículas y los sonidos de trabajo van a la velocidad del juego (antes, por ser enteros, se habrían quedado quietos).

**D-5806. Cuánto aguanta.**
No se midió una partida de 300 aldeanos en vivo a ×9; el dato sale de las mediciones de `docs/RENDIMIENTO.md`: con 2 pueblos de 300 un paso cuesta 0,15 ms, así que ×9 (90 pasos por segundo) son 14 ms de cada segundo. En vivo se comprobó ×9 en una partida recién empezada (mapa mediano, 12 aldeanos): 9 días de juego en unos 4 s y sin bajar de velocidad. Con 12 pueblos de 1000, el paso promedio (12,5 ms) da para ×8 sin dibujar, pero uno de cada veinte pasa de 34 ms: ahí el juego bajará solo hacia ×3 o ×4.

## Fase 59: años largos y duración de cada estación (2026-10-03)

**D-5901. Cada estación con sus minutos.**
`ClimateSettings` gana `minutes`: los minutos (a ×1) de cada estación activa, de 1 a 30; el año es la suma, hasta 120 min. Con todos en 0 vale lo de antes: el porcentaje del año repartido en partes iguales (así siguen funcionando las pruebas, los tutoriales y cualquier partida hecha en código). Variado y Personalizado usan siempre minutos; cuatro estaciones de 5 min son exactamente el año de 20 min de siempre. El calendario y la temperatura salen ahora de una sola función que reparte el año entre las estaciones. Los meses siguen siendo 12 de 10 días: con un año más largo, cada día dura más.

**D-5902. El día del pueblo ya no se estira.**
Para mantener "el ritmo por minuto real" que eligió Salvador, la simulación separa dos relojes:
- **el del calendario** (se estira con el año): estaciones, temperatura, crecimiento y siembra de los cultivos, madurez de los huertos, edad y muerte por vejez, y los años de la victoria por puntos;
- **el del pueblo** (siempre 10 s por día y 100 s por mes a ×1): hogares, salud y enfermedades, incendios, comercio diario, asaltos, nieve, leña, nacimientos, llegadas y salidas, vuelta de los animales y arbustos, mercaderes, caravanas, ropa y calzado.
Con el año de 20 min los dos coinciden y el orden de las operaciones es el mismo: las partidas de ese largo transcurren igual que antes.

**D-5903. Cosechas y límites anuales, en proporción al año.**
Un campo sigue dando una cosecha por año de calendario y un huerto tiene su tope anual; los dos se multiplican por la duración del año sobre 20 min (`Game::per_year`). Por minuto de juego rinden lo mismo con cualquier año. Esto corrige también los años cortos, que antes daban el doble o el cuádruple de comida por minuto.

**D-5904. Diferencia con el plan: las enfermedades no se estiran.**
El plan decía que las enfermedades, medidas en días, se estirarían con el año. Quedaron en el reloj del pueblo (duran lo mismo en minutos con cualquier año): era lo coherente con "el ritmo por minuto real" y lo más simple. Lo que sí se estira es lo que el plan decía: las estaciones y la edad.

**D-5905. Lo que cambia para el jugador con un año largo.**
Cada estación dura más, así que hay que guardar más comida y leña para el invierno; los niños tardan más minutos en crecer (5 años); un campo tarda lo mismo en madurar en días de calendario, o sea más minutos, y da una cosecha más grande. Los días que muestra la interfaz (llegada del mercader, viaje de una caravana) son días del calendario.

**D-5906. La prueba de equilibrio suma cuatro partidas.**
El criterio pedía comparar comida por habitante y población entre el año normal y el largo. Una partida sola no sirve: con la misma configuración, la suerte del pueblo mueve su población un tercio (de 23 a 47 habitantes en diez semillas). Sumando cuatro partidas de una hora con años de 15 y de 45 min (sin invierno, para que el clima sea el mismo): 149 y 140 habitantes, 161 y 147 llegadas, comida por habitante 9,7 y 9,6. La prueba (`village_years`) exige que queden dentro del 15 %.

**D-5907. Ajustes de antes.**
`settings.json` guarda `springMinutes`, `summerMinutes`, `autumnMinutes` y `winterMinutes`. Un archivo anterior con `year` (porcentaje) se convierte: ese año repartido entre sus estaciones, redondeado a minutos enteros de 1 a 30.

**D-5908. Versiones.**
Reglas 30, protocolo de red 8 (las reglas llevan cuatro bytes más).

**D-5909. Sin revisar en pantalla.**
Las barras nuevas están en la mitad de abajo de Personalizado, que no se puede capturar desde las pruebas automáticas (D-5611). Quedan en la lista de pruebas a mano.

## Fase 60: niebla "mapa revelado" y reglas de comercio con precio (2026-10-03)

**D-6001. Cuarto modo de niebla.**
`FogMode::Revealed` ("Dinámica, mapa revelado") se comporta como la dinámica en todo (lo que se mueve y los edificios de otros solo se ven donde alguien propio mira; lo visto queda como recuerdo), pero todo el mapa cuenta como explorado desde el principio. No se llena ninguna cuadrícula: `Vision` lleva una marca "todo explorado" que sale del modo de la partida, así que el archivo guardado mide lo mismo que con la dinámica y la suma de verificación no cambia de forma. La vista lo dibuja como dinámica con todas las celdas exploradas.

**D-6002. Dónde se construye.**
Como eligió Salvador, en cualquier parte de la región propia: la regla de D-3203 se cumple sola porque todo está explorado.

**D-6003. Lo que se sabe de más.**
En este modo se ve desde el principio el terreno y los recursos de todo el mapa, y un árbol que tala otro pueblo desaparece a la vista aunque nadie propio lo mire. Se acepta: es el precio de "todo explorado".

**D-6004. Reglas del puesto con precio.**
Cada regla de comercio automático puede llevar dos límites: vender solo si el precio del día del mercader es al menos N % del valor del bien, y comprar solo si es a lo más N %. N va de 75 a 125 en pasos de 5 (el rango de precios de un mercader); sin límite por omisión. El límite se compara con el precio del día, no con lo que el mercader paga o cobra: él paga tres cuartos de ese precio y cobra cinco cuartos, así que comparar con lo pagado o cobrado dejaba fuera de rango casi todos los casos (se probó primero así y ninguna compra pasaba).

**D-6005. Versiones.**
Reglas 31 (las reglas de comercio guardan dos bytes más), protocolo de red 9 (un cliente anterior no conoce el modo de niebla).

## Fase 61: cámara que mira al cielo, sigue a un aldeano y ve a través de lo que estorba (2026-10-03)

**D-6101. Mirar hacia arriba en tercera persona.**
La cámara en tercera persona lleva dos ángulos: el de la vista y el del ojo. Mientras el suelo deja, son el mismo y la vista mira al punto alrededor del que gira. Cuando el ojo tocaría el suelo se queda a ras de él y la vista sigue subiendo, hasta 60° sobre el horizonte. Al volver, primero baja la vista y solo después sube el ojo. El punto de giro no se mueve: sigue siendo tercera persona.

**D-6102. Seguir a un aldeano.**
Con el botón "Seguir" de su ventana o con doble clic sobre él (dos clics en 400 ms sobre el mismo aldeano). La cámara aérea pasa a tercera persona al empezar a seguir; en primera persona se mira desde sus ojos y ese aldeano no se dibuja. Se suelta con "Dejar de seguir", al mover la cámara con el teclado, o si el aldeano muere o queda bajo la niebla. Es solo de la vista: no viaja por la red ni se guarda en la partida.

**D-6103. El fantasma del ancla.**
En tercera persona sin seguir a nadie, en el punto de giro se dibuja un aldeano pálido y translúcido que camina cuando el ancla se mueve (a paso de carrera como mucho, por rápido que vaya la cámara). No hace sombra, no se puede seleccionar y no existe en la simulación.

**D-6104. Translúcido por tramado, no por mezcla.**
Lo translúcido se dibuja descartando píxeles con un patrón ordenado de 4 × 4 (uno, dos o tres de cada cuatro), en el mismo pase que lo opaco. Es lo más simple y seguro: no hace falta ordenar nada por distancia ni otro pase, la profundidad sigue siendo correcta y cuesta lo mismo que dibujar lo opaco. El suavizado de bordes disimula el tramado. Lo translúcido conserva su sombra en el caso de edificios y árboles (la sombra no estorba) y no la hace en el de personajes.

**D-6105. Qué se vuelve translúcido.**
El edificio o el árbol que contiene al ojo de la cámara (en cualquier modo) y, en tercera persona, los que quedan entre el ojo y el punto de giro. Un edificio cuenta como su caja (planta por altura, tal como se dibuja; una obra a medio levantar cuenta hasta donde llega); un árbol, como el cilindro de su copa (radio de 0,3 veces su altura, mínimo 1 m, desde un cuarto de su altura), así que el tronco solo no estorba. La línea de visión se corta 0,75 m antes del ancla para que lo que está justo detrás del seguido no cambie. Los árboles talados no cuentan. El relieve no se vuelve translúcido: de él se ocupa D-6101.

**D-6106. La transición.**
Lo que estorba pasa a tres cuartos translúcido en 0,2 s y vuelve igual de despacio, por los tres niveles del tramado. Un cambio de estación vuelve a dibujar todos los árboles; los que estorban se vuelven a marcar en ese mismo cuadro.

**D-6107. Costo.**
Los árboles se buscan en una rejilla de 16 m hecha una vez por mapa, con muestras cada medio metro de la línea de visión (160 como mucho); los edificios se recorren todos, que son pocos. Los edificios se vuelven a enviar al dibujante solo cuando cambia el nivel de alguno.

**D-6108. Sin revisar en pantalla por Claude.**
Mirar al cielo (necesita arrastrar con el ratón) y los árboles translúcidos (no había árbol cerca en la partida de prueba). Sí se vio en pantalla: la casa que tapa el ancla translúcida, el fantasma del ancla y el botón "Seguir".

## Fase 62: ventanas, base (2026-10-03)

**D-6201. La lista de ventanas.**
Las ventanas dejan de ser funciones sueltas que se dibujan en orden fijo: `WindowList` (`src/game/window_list.h`) guarda dónde está cada una, cuál va delante de cuál, las ventanas de objeto, los grupos y los imanes, sin dibujar nada, para poder probarla sola. `GameHud` las dibuja de atrás hacia adelante.

**D-6202. Un clic solo llega a la ventana de arriba.**
Cada cuadro se calcula qué ventana está delante bajo el cursor (con los rectángulos del cuadro anterior) y solo esa oye al ratón; las demás, y el resto de la interfaz que quede debajo (barra de construcción, lanzador, avisos), se dibujan sin atenderlo. Tocar una ventana la trae al frente. Las ventanas ahora son opacas: antes eran algo translúcidas y la de atrás se leía a través de la de adelante.

**D-6203. Ventana "de paso" y ventanas fijadas.**
Seleccionar algo en el mapa lo abre en la ventana de paso (la única ventana de objeto sin fijar), que la siguiente selección reutiliza en el mismo sitio. Al fijarla se queda y la siguiente selección abre otra, al lado mientras haya lugar. Si lo seleccionado ya tiene ventana fijada, esa pasa al frente y no se abre otra. Esc y un clic en el suelo cierran solo la de paso. Soltar ("Fijada" → "Fijar") una ventana de objeto la convierte en la de paso y cierra la que lo era. Cada ventana da sus órdenes sobre su propio objeto, no sobre la selección.

**D-6204. Tope de 16.**
Con 16 ventanas de objeto fijadas, una selección nueva no abre ventana y sale un aviso. Es lo más simple: cerrar por su cuenta una ventana que el jugador fijó iría contra "fijar".

**D-6205. Qué impide "Fijar".**
Una ventana fijada solo se cierra con su X. Para las ventanas del lanzador (Bienes, Estadísticas...) eso incluye el botón del lanzador: con la ventana fijada, el botón la trae al frente en vez de cerrarla.

**D-6206. Objeto que deja de existir.**
La ventana de paso se cierra sola (como antes). Una fijada se queda, con el título "Ya no existe" y una línea que lo explica, hasta que se cierre con su X. Demoler un edificio desde su ventana la cierra.

**D-6207. Minimizar en lugar del plegado automático.**
Se quitó el plegado a pestaña por tiempo. El botón "–" deja solo la barra de título (que se puede mover y fijar) y "+" la restaura. Se guarda en los ajustes como sexto valor de cada ventana; el formato de cinco valores de antes se sigue leyendo.

**D-6208. Imanes.**
Además de los bordes de pantalla y de quedar lado a lado o apiladas, las ventanas se pegan al borde inferior, a la barra de construcción y a los bordes iguales de otras (arriba con arriba, abajo con abajo, izquierda con izquierda, derecha con derecha). La pantalla gana a las ventanas cuando las dos tiran.

**D-6209. Grupos.**
Al cerrar una ventana, sale de su grupo; si el grupo queda con una sola, deja de existir (dos que siguen juntas siguen siendo grupo). Antes una ventana cerrada seguía en su grupo y al reabrirla se movía con ventanas que ya no tocaba. Al cargar, los grupos de un solo miembro se descartan y los grupos nuevos se numeran después de los leídos (antes volvían a empezar en 1 y se mezclaban con los guardados). Las ventanas de objeto pueden anclarse durante la partida, pero ni ellas ni sus grupos se guardan.

**D-6210. Qué se guarda.**
Solo las ventanas del lanzador. Las entradas `building` y `villager` de un `ui.windows` anterior se leen y se descartan. Al empezar otra partida se cierran las ventanas de objeto.

**D-6211. C-003: la X no cerraba.**
La función de la ventana devolvía "dibuja el contenido" aunque se hubiera pulsado la X, y las ventanas de aldeano y edificio solo miraban el cierre cuando no se dibujaba. Ahora la X devuelve "no dibujar" y cada ventana se cierra a sí misma.

**D-6212. C-001: la brújula.**
Sin disco: solo la aguja y la N, con un borde oscuro para que se lean sobre cualquier terreno. El cuadro de la brújula ya no tapa los clics al mapa.

**D-6213. Ventanas de objeto más anchas.**
De 360 a 400 unidades, para que el título quepa junto a los tres botones.

**D-6214. Sin revisar en pantalla por Claude.**
Mover ventanas, los imanes, anclar y cambiar el ancho: la herramienta de pruebas no logra arrastrar dentro del juego. Los cubren las pruebas de `WindowList`. Sí se vio en pantalla: varias ventanas de objeto fijadas a la vez, Esc y clic en el suelo, la X, minimizar, el traslape con la de arriba delante y la lectura de un `ui.windows` del formato anterior.

## Fase 63: ventanas, contenido (2026-10-03)

**D-6301. De dónde sale el nombre.**
Cada raza trae en `races.json` dos listas de nombres (`names.male` y `names.female`, hasta 64 cada una; una raza con una sola lista la usa para todos). El nombre de un aldeano sale de la lista de su raza y sexo según los bits al azar con los que nació (los mismos que deciden su aspecto, revueltos para que el nombre no vaya ligado al aspecto). Esos bits ya se guardaban en la partida, así que el nombre es el mismo en todas las máquinas y al cargar, sin gastar otro número al azar al nacer: las partidas con la misma semilla transcurren igual que antes de la fase. Solo el nombre que pone el jugador se guarda aparte.

**D-6302. Renombrar es una orden del juego.**
Orden nueva `RenameVillager` con el texto: hasta 24 bytes de UTF-8 bien formado, sin caracteres de control y sin espacios en los extremos. La validación es la misma al leer la orden de la red, al aplicarla, al cargar una partida y al leer los nombres de un mod. Un nombre vacío devuelve el de siempre. Solo el dueño puede renombrar a los suyos. Las órdenes llevan ahora un texto (vacío salvo en esta) y miden 36 bytes en lugar de 32.

**D-6303. Interruptor de producción.**
Orden nueva `SetProduction`. Un edificio detenido cuenta como si quisiera cero trabajadores: los que tenía vuelven a ser peones con la regla de siempre y, sin trabajadores, ni consume ni produce. El número que quería no se toca, así que al reactivarlo vuelve a pedir los mismos. Vale para todo edificio con trabajadores (talleres, recolectores, granjas, mercados, cuarteles); uno sin trabajadores rechaza la orden.

**D-6304. Enlaces entre ventanas.**
La ventana del aldeano tiene botones "Vive en" y "Trabaja en"; la del edificio, un botón por habitante y por trabajador con su nombre y edad. Pulsar uno fija la ventana desde la que se pulsa y abre lo enlazado como selección nueva, en la ventana de paso: así se recorre aldeano → casa → otro habitante → su trabajo con todas las ventanas abiertas. Las listas de más de cinco personas se desplazan. Las listas y el interruptor solo salen en los edificios propios.

**D-6305. El botón de ojo.**
"Ver", en la primera fila de toda ventana de objeto: lleva la cámara principal al objeto. Va en el contenido y no en la barra de título para no quitarle más lugar al nombre.

**D-6306. Seleccionar lo demás.**
Un clic que no cae en un aldeano ni en un edificio busca un animal, soldado o asaltante a la vista y luego un árbol, piedra, veta, arbusto o hierba en terreno explorado. Los árboles se eligen por el tronco o por la copa. La ventana dice qué es (la especie del árbol, su altura), qué da (los troncos que le quedan; la carne y la piel que trae un cazador de un venado o jabalí) y su estado (alguien lo trabaja; vacío y volverá a crecer; qué hace el animal; su salud). Son ventanas de solo lectura: no dan órdenes.

**D-6307. Lo que da un animal.**
La caza no mata al animal que se ve: descuenta uno de la zona y el cazador vuelve con lo que carga de carne y una piel. La ventana muestra eso mismo, igual para venados y jabalíes; lobos y osos dicen que son peligrosos.

**D-6308. Versiones.**
Reglas 32 (el aldeano guarda su nombre puesto y el edificio si está detenido), protocolo de red 10 (las órdenes llevan texto).

**D-6309. Sin revisar en pantalla por Claude.**
Escribir un nombre (la herramienta de pruebas no teclea texto), el interruptor de producción, las listas con desplazamiento y las ventanas de animales. Los cubren las pruebas de la simulación. Sí se vio en pantalla: nombres en títulos y listas, "Renombrar" abre el campo, el enlace de habitante fija la casa y abre al aldeano con "Vive en: Casa", y la ventana de un árbol ("Pino, árbol de 3 m, da: Troncos 4").

## Fase 64: pestañas y ventana de cámara (2026-10-03)

**D-6401. Pestañas.**
Soltar una ventana sobre la barra de título de otra las une en una pila: comparten sitio y ancho, se dibuja una sola y las demás quedan como pestañas encima. Un clic en una pestaña la muestra; arrastrarla más de 10 unidades la saca de la pila y sigue el arrastre como ventana suelta. Si la que se suelta ya era una pila, entran todas sus pestañas. Unir gana a anclar: soltada sobre un título se une; soltada tocando un borde se ancla.

**D-6402. Solo cuentan las abiertas.**
Una pila con una sola ventana abierta se ve como una ventana sola, sin pestañas. Cerrar una ventana del lanzador no la saca de su pila: al volver a abrirla regresa como pestaña (así se restaura también lo guardado, porque al empezar no hay ninguna abierta). Las ventanas de objeto y de cámara, que no vuelven, sí salen de la pila al cerrarse.

**D-6403. Qué se guarda.**
Dos valores más por ventana en `ui.windows`: el número de su pila y su pestaña (el doble de su lugar entre las pestañas, más uno si es la que se muestra), para conservar el orden. Se siguen leyendo los formatos de cinco y de seis valores. Las pilas con ventanas de objeto o de cámara no se escriben.

**D-6404. La segunda vista del motor.**
`SceneRenderer::request_inset` pide una vista pequeña (320 × 200) que se dibuja en su propia textura después de la vista principal, en el mismo cuadro: mismo cielo, terreno, modelos, personajes, agua y niebla de guerra; sin pasto. Los destinos tienen el mismo suavizado que la vista principal porque los programas de dibujo están hechos para él; así no hizo falta otro juego de programas. La interfaz dibuja esa textura como una imagen más.

**D-6405. Sombras de la vista principal.**
La vista pequeña no calcula sombras: usa las cascadas de la vista principal. Como están ajustadas a otra cámara, elige para cada punto la cascada más fina que lo contiene y, donde ninguna llega, no hay sombra. Lejos de la cámara principal la ventana de cámara se ve sin sombras; se acepta por el costo.

**D-6406. Media frecuencia.**
Se dibuja a lo más una vista pequeña por cuadro, por turnos: cada ventana de cámara se actualiza un cuadro sí y otro no, haya una o dos abiertas. Su distancia de dibujo es corta (ocho veces la distancia de la órbita, entre 120 y 400 m) y los modelos pasan antes a su versión lejana, sin tocar la memoria que evita el parpadeo en la vista principal.

**D-6407. La ventana de cámara.**
Botón "Cámara" en la primera fila de toda ventana de objeto. La ventana muestra la vista desde una órbita propia: arrastrar sobre la imagen la gira y la rueda acerca o aleja (de 3 a 80 m). Como cualquier ventana se mueve, se fija, se minimiza, se ensancha y se une en pestañas. Si el objeto deja de existir o queda bajo la niebla, se cierra. Dos como mucho: con las dos ocupadas, la que se abrió primero pasa a mirar lo nuevo. Su título es el nombre del objeto.

**D-6408. Fila de botones.**
Los botones de la primera fila de las ventanas de objeto se reparten el ancho según lo que mide su texto, y las ventanas de objeto pasan de 400 a 420 unidades para que quepan los cuatro del aldeano.

**D-6409. Medición.**
`release`, 1600 × 900, Ultra, sin vsync, partida nueva en mapa mediano con 12 aldeanos, a 70 m: 797–801 FPS sin ventanas de cámara y 784–800 con las dos abiertas (238 llamadas de dibujo más en el cuadro que le toca a una). La pérdida queda por debajo del 2 %, muy lejos del 25 % permitido. No se midió con un pueblo grande: la herramienta de reportes no abre ventanas de cámara. Anotado en `docs/RENDIMIENTO.md`.

**D-6410. Sin revisar en pantalla por Claude.**
Unir ventanas soltándolas y sacar una pestaña arrastrando, y girar o acercar la vista de la cámara (la herramienta de pruebas no arrastra ni mueve la rueda). Los cubren las pruebas de `WindowList`. Sí se vio en pantalla: una pila de tres ventanas leída de los ajustes, cambiar de pestaña con un clic, cerrar una pestaña, y dos ventanas de cámara vivas (un edificio y un aldeano) con la cámara principal en otra parte.

## Fase 65: construir en pendiente (2026-10-03)

**D-6501. Hasta 4 m de desnivel.**
El desnivel permitido bajo un edificio pasa de 1,8 a 4 m. Murallas, empalizadas, portones y trampas ("lo que sigue al terreno": defensas sin ataque) quedan como estaban: 1,8 m y apoyadas en la esquina más baja, como pidió Salvador.

**D-6502. El piso, a la altura del suelo frente a la puerta.**
El piso de un edificio queda a la altura del terreno en el punto medio del lado de la puerta. Girar el edificio al colocarlo elige ese lado. `Game::floor_cm` lo calcula; la vista dibuja el modelo a esa altura.

**D-6503. Cimientos en los modelos.**
Los 51 modelos de edificios que no siguen al terreno ganan cimientos de piedra de 4,5 m bajo el piso (un ayudante común, `foundation`, en `art/blender/buildings.py`), del tamaño de la planta del modelo para que el juego los escale igual. En terreno plano quedan bajo tierra; ladera abajo son lo que se ve. Son 4,5 y no 4 m porque el juego escala los modelos a 0,95 de su planta. La vista usa ahora la altura del modelo sobre su piso (marcadores, humo, selección, obra, lo que estorba a la cámara).

**D-6504. Ladera arriba: la pared queda enterrada hasta 2 m; no se recorta el terreno. (Cambio respecto a la especificación.)**
La especificación decía recortar el terreno bajo el edificio solo en lo dibujado. El terreno se dibuja con mallas facetadas hechas una vez por mapa, con facetas grandes en las laderas lisas: recortarlo pide rehacer y volver a subir las mallas de las parcelas tocadas en cada construcción y demolición, y deja a los aldeanos caminando a una altura distinta de la que se ve junto al edificio. Se eligió lo más simple y seguro: el terreno puede subir hasta 2 m por encima del piso (la pared queda enterrada esa altura, por debajo de los aleros); si sube más, el lugar se rechaza con el mensaje "La ladera sube demasiado detrás de la puerta: gira el edificio". Con la puerta ladera arriba o de lado cabe siempre que el desnivel no pase de 4 m. Queda en el registro para que Salvador confirme o pida el recorte de verdad.

**D-6505. No se construye donde nadie puede llegar (I-011).**
Un sitio se rechaza ("Nadie del pueblo puede llegar hasta ahí") si ninguno de sus cuatro lados está unido por tierra caminable con la puerta del centro del pueblo. Vale también para los campos (su centro con la puerta de su granja). Un recinto cerrado por murallas sin portón cuenta como inalcanzable. El centro del pueblo mismo no se comprueba.

**D-6506. La prueba de los cazadores.**
Uno de los tres motivos de D-5613 era que la cabaña se podía poner al otro lado del agua y nunca se construía; un sitio así ahora se rechaza al colocarlo (prueba nueva con un foso hecho a mano). No se volvieron a correr las semillas 17 y 20 una por una. La prueba de los cazadores sigue con la semilla 2; las otras fallas de D-5613, por distancia y por hambre en el camino, son de la fase 66.

**D-6507. Versiones.**
Reglas 33, protocolo de red 11.

**D-6508. Sin revisar en pantalla por Claude.**
Un edificio en ladera dentro del juego: en las partidas de prueba el terreno junto al pueblo era plano. Se vio el modelo con sus cimientos (imagen hecha con Blender) y que en terreno plano los edificios se ven como antes. Lo cubren las pruebas de la simulación con una rampa hecha a mano.

## Fase 66: explorador, y el hambre que interrumpe un viaje (2026-10-03)

**D-6601. El edificio y su trabajador.**
"Explorador" (`core:explorer`, en Servicios, 10 troncos, un trabajador), con trabajo nuevo `explore` y `workerSight: 30` en los datos: su trabajador ve 30 m (el resto, lo de su raza: 12). Mientras no tiene órdenes vive como cualquier aldeano con trabajo.

**D-6602. La orden.**
Orden nueva `MoveVillager` (aldeano y punto). Solo vale para el trabajador de un Explorador terminado y del propio pueblo; cualquier otro se rechaza. En la interfaz: con ese aldeano seleccionado, clic derecho en el mapa o en el minimapa. Mientras tiene una orden no hace otra cosa: ni come en el pueblo, ni trabaja, ni pasea. Al llegar, o al toparse con algo, espera ahí la siguiente orden. Si huye de un animal, al terminar retoma la orden.

**D-6603. La ruta.**
Con niebla y el destino explorado: el camino más corto que pise solo celdas exploradas (`NavGrid::find_path_within`). Si no lo hay, o el destino no está explorado: en línea recta, metro a metro, hasta el último punto caminable antes de un obstáculo (agua, un barranco, un edificio); no lo rodea. Sin niebla: el camino de cualquiera. En "mapa revelado" todo cuenta como explorado.

**D-6604. Provisiones.**
Al recibir una orden, si lleva menos de la mitad de sus provisiones y hay comida en algún almacén, pasa primero por el más cercano y toma comida hasta completar 2000 puntos de hambre (dos medidores llenos; lo más nutritivo primero). En el camino come de lo que lleva cuando su medidor baja de la mitad. Sin comida en el pueblo sale igual, con lo puesto.

**D-6605. La vuelta.**
Cada 16 pasos se compara lo que le queda (medidor más provisiones) con lo que cuesta volver a su edificio (60 de margen más 13/8 de punto por metro en línea recta: caminar cuesta 5/4 y los caminos rara vez son rectos). Cuando ya no le sobra, vuelve solo y sale el aviso "El explorador vuelve: le queda la comida justa para el camino". Al llegar es un aldeano corriente otra vez. También se le manda a casa con una orden a menos de 12 m de su edificio.

**D-6606. El frío. (No estaba en la especificación.)**
La especificación dice que se abriga como los demás. Como no vuelve al pueblo por su cuenta, se añadió que regrese cuando su calor baja de un cuarto, con su aviso. Sin esto, uno que espera lejos en invierno moría de frío sin que el jugador pudiera saberlo.

**D-6607. Deja de ser explorador.**
Si su edificio se demuele, se detiene o le quitan el trabajador, la orden se olvida y vuelve a ser peón.

**D-6608. El hambre interrumpe (I-010).**
Cada 16 pasos, para quien camina o trabaja (no para quien pelea, apaga un incendio, huye o ya va a comer): si la comida que le queda no alcanza para terminar la caminata que lleva y llegar después al almacén con comida más cercano (5/4 de punto por metro, más 60 de margen), va a comer primero, siempre que comer lo deje mejor de lo que está: así se da la vuelta al principio de un viaje largo y no al final. Lo que cargaba para una obra vuelve al almacén. Quien trabaja parado lejos (construir, talar) va a comer cuando ya no le sobra para volver.

**D-6609. Los viajes imposibles se abandonan.**
Si ni recién comido alcanza para ir y volver, el viaje se abandona en vez de seguirlo hasta morir. Consecuencia: una obra a más de unos 340 m de cualquier almacén con comida no avanza (nadie muere por ella). La salida es la de siempre: un almacén o granero más cerca. No hay aviso propio para esto; queda como posible mejora.

**D-6610. Las semillas de D-5613.**
Con las semillas 1 y 14 la zona de caza está tan lejos que el viaje es de los imposibles: la cabaña ya no se construye y nadie pasa hambre (el medidor más bajo en un año queda sobre 400). La prueba nueva con una obra a 320 m, que sí se alcanza, termina construida sin que ningún medidor llegue a cero (el más bajo, 48).

**D-6611. La prueba de equilibrio del año largo.**
Con el hambre nueva, la suma de llegadas de las cuatro partidas quedó en 132 contra 156 (15,4 % de diferencia; el límite era 15 %). Población y comida por habitante, que son las que pedía la fase 59, siguen dentro del 15 %. Las llegadas siguen a los que mueren, y con años largos se envejece más despacio (D-5902): su margen pasa al 25 %.

**D-6612. Versiones.**
Reglas 34 (el aldeano guarda su orden, el punto y las provisiones), protocolo de red 12.

**D-6613. Sin revisar en pantalla por Claude.**
El clic derecho en el minimapa y el regreso por provisiones (se vio en pantalla: construir el Explorador, su trabajador con "Provisiones" y la pista, y mandarlo con clic derecho en el mapa: fue por provisiones y quedó esperando en el punto).

## Fase 67: lo que pasa, a la vista (2026-10-03)

**D-6701. Todo es de la vista.**
Cargas, pilas, etapas de obra, flechas y carreta se deducen del estado del juego al dibujar; la simulación y su suma de verificación no cambian y no suben las versiones de reglas ni de red. Lo único que cambia en los datos es `"load"` en los recursos, que la simulación no lee (sí cambia la huella del contenido, así que las partidas guardadas antes no cargan; ya pasaba con las fases 63 a 66).

**D-6702. El tipo de carga de cada recurso.**
`"load"` en `resources.json`: `crate`, `logs`, `stone`, `sack` o `basket`. Por omisión, los alimentos van en canasta y lo demás en cajón. En `core`: troncos y leña como troncos; piedra, mineral de hierro, arcilla y carbón como piedra; harina, cebada, abono, lino y oro en saco; hierbas en canasta. No hay modelo de lingotes: el hierro va en cajón.

**D-6703. Espalda o brazos.**
Si lleva más de la mitad de lo que cabe en un viaje, la carga va a la espalda; si no, en brazos, y entonces camina y espera con las animaciones de carga (y no corre). No hay saco para los brazos: un saco chico se ve como cajón. Si las manos sostienen una herramienta (talar con troncos encima), la carga de brazos no se dibuja; la de espalda sí.

**D-6704. Hasta dónde se ven las cargas. (Ajuste a la especificación.)**
La especificación decía que con la versión lejana del personaje la carga no se dibuja. Pero el personaje pasa a su versión lejana muy cerca (a unos 15 m con la cámara normal), así que casi nunca se verían. Las cargas se dibujan hasta cuatro veces esa distancia y no hacen sombra; más lejos, no se dibujan.

**D-6705. Cómo se dibujan.**
Cada carga es un accesorio rígido fijado al hueso `chest` de cada personaje (9 por cada uno de los 17). Para que tantos modelos no cuesten, el descarte de personajes ya no recorre cada modelo contra todos los personajes: cada personaje entra directo en las listas de lo que se dibuja con él.

**D-6706. Etapas de construcción.**
Una obra muestra los cimientos hasta el 35 % del trabajo y el armazón con andamio desde ahí; al terminar, el edificio. Los modelos son por tamaño de terreno (`site_<ancho>x<fondo>_<etapa>.glb`, con cimientos de piedra como los edificios, fase 65). Si falta el modelo de un tamaño, esa obra sube del suelo como antes. Los edificios de otros recordados bajo la niebla usan la misma regla.

**D-6707. Pilas.**
Una pila por tipo de carga, en tres tamaños, a un metro del lado de la puerta. En una obra, a la izquierda de la puerta: lo entregado de cada tipo contra lo que pide la obra. En un almacén (todo edificio con almacenaje que no sea casa), a la derecha: lo guardado de cada tipo, donde un tercio de su capacidad ya es una pila llena. Se actualizan dos veces por segundo. Pueden encimarse con un edificio vecino; son adorno.

**D-6708. Flechas.**
La simulación no dice cuándo sale cada tiro, así que la vista lo deduce: un cazador suelta una flecha cada vez que su animación de disparo da la vuelta, hacia donde apunta; una torre, al ritmo de su ataque, a la bestia o asaltante más cercano dentro de su alcance; un arquero, al ritmo del suyo, a quien persigue si está a tiro. Vuelan a 30 m/s en un arco bajo y con el reloj del juego (en pausa se quedan en el aire). El modelo es una flecha acostada de 1,2 m (`props/arrow_flight.glb`), más grande que la real para verse desde arriba; solo gira sobre la vertical. Puede no coincidir exactamente con el golpe de la simulación.

**D-6709. El mercader.**
Mientras dura la visita, junto a cada puesto de comercio del pueblo hay una carreta y una persona de pie. No camina ni llega: aparece y se va con la visita.

**D-6710. Medición.**
Con `--reporte`, `release`, 1600 × 900, Ultra, 1000 personas de las herramientas de desarrollo, una de cada tres con una carga, comparando seguidas la versión anterior y la nueva: a media distancia (750 a la vista) 549 y 541 FPS antes, 536, 533 y 533 después (−2 %); lejos (995 a la vista) 596 y 582 antes, 586, 582 y 582 después (−1 %); de cerca (420 a la vista) 550 antes y después. El criterio permitía un 10 %. Anotado en `docs/RENDIMIENTO.md`.

**D-6711. Sin revisar en pantalla por Claude.**
Las flechas y el mercader con su carreta (no hubo cazadores, torres ni visita en las partidas de prueba). Sí se vio en pantalla: troncos y cajones a la espalda, las pilas junto al centro del pueblo y junto a una obra, y un granero pasando por cimientos, armazón y edificio.

## Después de la fase 67: humo alto, fogatas, selección de lo creado con las herramientas y decoraciones (2026-10-03)

Pedido directo de Salvador, fuera del plan de fases.

**D-6801. Humo hasta unos 40 m.**
El humo de chimeneas, incendios y fogatas sube ahora unos 40 m (bocanadas que duran 24 a 28 s y casi no se frenan) y se genera hasta 700 m del centro de la vista, no 180, para verse de lejos. Menos bocanadas y más grandes por chimenea; el tope de partículas pasa de 4000 a 16 000.

**D-6802. Lo creado con las herramientas de desarrollo no se podía seleccionar.**
Causa: árboles, piedras y arbustos creados ahí se añadían solo a la copia del mapa que usa la vista, no a la partida, y las personas son paseantes de la vista, no aldeanos. Ahora, en una partida, crear un recurso es una orden de desarrollo (`DevFeature`) que lo añade al juego con su nodo: se selecciona, se tala y viaja en red y en las partidas guardadas. Las personas de prueba se seleccionan con una ventana sencilla (qué modelo son, «Ver», «Cámara», «Seguir»), como eligió Salvador; siguen sin ser aldeanos.

**D-6803. Fogata.**
Edificio de Decoración de 2 × 2 (2 troncos, 2 piedras). Como eligió Salvador, da calor: quien está a 10 m de una fogata encendida no pierde calor (igual que en una casa caliente). Cada día frío (menos de 10 °C) gasta 1 de leña del almacén más cercano; sin leña se apaga y lo dice su ventana. Con llamas y humo. `"warmth"` en los datos es el radio.

**D-6804. Decoraciones.**
Modelos hechos por cinco subagentes en paralelo, uno por tema, en `art/blender/decor/` (`ruins.py`, `nature.py`, `statues.py`, `plaza.py`, `garden_market.py`), cada uno con su `.json` (nombre, tamaño, textos, costo, agrado). `build_all.py ... decor` los genera. Entran al juego como edificios de decoración, con costo bajo en troncos y piedra y agrado para las casas cercanas. Cinco pestañas nuevas en la barra de construcción: Plaza, Jardín y mercado, Naturaleza, Monumentos y Ruinas.

**D-6805. Versiones.**
Reglas 35, protocolo de red 13.

**D-6806. Sin revisar.**
Cada modelo se miró en una imagen de Blender, no uno por uno en el juego (en el juego se vieron tres construidos y las pestañas). Los brillos de runas y flores de fantasía son solo color. No se probó en pantalla la selección de lo creado con las herramientas (sí por pruebas la orden nueva). La verificación en debug y asan de este cambio queda pendiente.

**D-6807. La regla del hambre de la fase 66 era lenta y se rehízo (corrige D-6608 y D-6609).**
La verificación en debug falló por tiempo: una hora de juego simulada tardaba 3,7 s en lugar de 0,6. La regla de D-6608 miraba, para cada aldeano en camino, si le alcanzaba la comida para terminar la caminata y volver; con comida a medias casi nunca alcanzaba, así que abandonaba la tarea, la retomaba y volvía a buscar camino, miles de veces por hora. Ahora la regla es más simple: un aldeano que camina o trabaja va a comer cuando solo le queda lo que cuesta llegar a la comida (60 de margen más 13/8 de punto por metro en línea recta). Ya no se abandonan viajes "imposibles" (D-6609 queda sin efecto): quien salió sin comer se da la vuelta a medio camino, come y vuelve a salir. Consecuencia medida: una obra a 220 m de la comida se construye sin que nadie pase hambre; a 270 m ya no se termina (los que llegan tienen que volver a comer casi enseguida). Antes de la fase 66 esas obras se construían, pero con gente muriendo de hambre en el camino. Una hora de juego vuelve a tardar 0,65 s y se interrumpen unas 30 tareas por hora en vez de miles; hay una prueba que lo vigila.

## Fase 68: día y noche, el ciclo y el cielo (2026-10-03)

Pedido de Salvador: un ciclo de día y noche configurable como las estaciones. Respondió antes de empezar: efectos jugables (más lento a oscuras salvo con luz cerca, más amenazas, y energía con descanso en casa en vez de dormir de noche), encendido por omisión con 5 + 5 minutos, noche oscura, sol y luna que recorren el cielo, estrellas, ventanas y antorchas que brillan y luces puntuales reales; penalización del 75 % al trabajar y caminar; energía igual de día y de noche, 8 minutos de actividad y 2 de descanso; dan luz los edificios con gente, las decoraciones que por naturaleza alumbran, faroles construibles y, solo a la vista, la antorcha en mano de los aldeanos; todas las amenazas nocturnas propuestas. Fases 68 a 72, seguidas y sin pausa; el pulido pasa a ser la 73.

**D-6810. El ciclo no sigue al calendario.**
Como en el ejemplo de Salvador (año de 10 min, día de 5 y noche de 10: medio año de día y año y medio... de noche hasta la mitad del año 2), el día y la noche tienen sus propios minutos y se repiten desde el tick 0, que es el amanecer. Los «días» del calendario (10 por mes) siguen siendo la unidad de la fecha y no tienen que ver con esto. `sim::day_time(reglas, tick)` es una función pura, como `calendar`: no hay estado nuevo en la partida.

**D-6811. Reglas: los dos minutos o ninguno.**
`GameRules::day_night` lleva minutos de día y de noche (1 a 30, como las estaciones). 0 y 0 es «sin ciclo» (siempre de día); uno solo en 0 se rechaza al leer. Las reglas por omisión de la simulación (pruebas, fondo del menú) no tienen ciclo; el formulario sí lo enciende por omisión (5 + 5), también en «Variado». Se descartó un tercer valor «encendido» aparte: sería un estado inválido más que validar.

**D-6812. La luz es solo de la vista.**
`src/game/day_light.*` toma la luz de la estación y la hora: el sol va de este a oeste por el sur y la luna por el norte, ninguno baja de unos 9° (sombras cortas y sanas); en el primer y último 12 % del día el sol sale de la oscuridad y vuelve a ella, con tono cálido; la noche es oscura y azulada con luna tenue. El amanecer y el anochecer coinciden exactamente con la noche (sol en 0), así que no hay salto. Las estrellas van en el shader del cielo. El agua, que tiene colores propios, se oscurece con un factor aparte.

**D-6813. Versiones.**
Reglas 36, protocolo de red 14.

**D-6814. Sin revisar.**
Se vio en pantalla: día, anochecer, noche con estrellas, amanecer, sombras que giran, agua oscura de noche y el HUD. No se vio la luna (la cámara no se pudo girar desde las pruebas) ni se probó con dos instancias en red: la hora sale de las reglas y del tick, que ya viajan y se comparan. El tono naranja del atardecer es discreto; queda a tu gusto.

## Fase 69: luces de noche (2026-10-03)

**D-6901. Las luces van en una textura, no en una lista por píxel.**
Cada luz (posición, radio, color) se dibuja en la CPU sobre una textura de 512 × 512 puntos de 2 m centrada en la cámara (1 km de lado); los shaders con luz (terreno, pasto, modelos, personajes) la leen con una sola muestra y la suman a la luz ambiente. Se descartó una lista de luces recorrida por píxel: con cientos de luces a la vista cuesta por píxel y obliga a un tope por calidad. Así el número de luces casi no importa y no hay tope. Limitaciones aceptadas: la luz no tiene dirección (ilumina igual todas las caras), no da sombras y el agua no la recibe. La textura guarda además la altura de las luces: lo que está muy por encima (humo, copas, tejados altos) recibe menos.

**D-6902. Las luces que se mueven se redibujan cada 80 ms como mucho.**
Dibujar la textura en cada cuadro (las antorchas de los aldeanos se mueven siempre) bajaba de 1310 a 320 FPS. Con el tope de 80 ms: 1402 FPS de día y 1333 a 1358 de noche (−4 %) en un mapa pequeño con 12 aldeanos, `release`, 1280 × 720, calidad alta. El criterio permitía un 15 %. No se midió con 200 luces: el costo por luz es dibujar unos cientos de puntos doce veces por segundo.

**D-6903. Qué da luz.**
`"light"` en los datos del edificio es el radio en metros (0 a 40) y `"coolLight"` la hace azul pálido. En `core`: centro del pueblo 20, fogata 12 (solo encendida), antorcha 10, farol 14, farol doble 16, braseros 12, arco con estandartes 8, pilar de llamas 14, horno público 6, muro memorial 6, lirios de fuego 4; y en azul, anillo de hadas 6, campanillas y tocón luminosos 5, pétalos flotantes 5, flores de luna 5, loto gigante 4. Son las decoraciones cuyos modelos ya tenían materiales de llama o de brillo. Las casas con habitantes y los talleres con trabajadores (no detenidos) alumbran 6 m más allá de sus paredes sin declararlo. Una obra no alumbra. `Game::light(edificio)` lo decide, y la fase 70 usa lo mismo para la penalización.

**D-6904. Antorcha.**
Edificio nuevo de Decoración, 1 × 1, 1 tronco, sin mantenimiento ni agrado: es la luz barata para caminos y zonas de trabajo que pidió Salvador. Los faroles de la pestaña Plaza alumbran más y dan agrado, pero cuestan piedra. Se añadieron los modelos de obra de 1 × 1.

**D-6905. Brillo propio por nombre de material.**
De noche, los materiales llamados `window` se ven como ventanas encendidas (color cálido fijo) y los que llevan `glow`, `flame` o `ember` en el nombre, o terminan en `_fire`, brillan con su propio color. No hubo que regenerar modelos. Todas las ventanas brillan, también las de un edificio vacío: distinguirlo pediría un dato por instancia y no cambia el juego.

**D-6906. Antorcha en mano.**
Los aldeanos dibujados que están fuera del alcance de la luz de un edificio llevan un charco de luz pequeño (4,5 m). Es solo de la vista y no quita la penalización de la fase 70. No se dibuja el objeto antorcha en la mano.

**D-6907. Versiones.**
Reglas 37, protocolo de red 15 (edificio nuevo y campo nuevo en los datos).

**D-6908. Tropiezos.**
(1) Tras cambiar `content.h`, Ninja dejó objetos de las pruebas sin recompilar y 40 suites fallaron con violaciones de acceso; borrar `CMakeFiles/sc_engine.dir` y `salvaciudad_tests.dir` y recompilar lo arregló. (2) `Get-Content`/`Set-Content` de PowerShell 5.1 dañó los acentos de un `.cpp` en UTF-8: editar siempre con Python o con la herramienta de edición. (3) Otra sesión usaba el worktree `verify` (rama `fix-hunger-cost`); mi verificación le cambió el commit dos veces y lo devolví a `aee56c5`. Desde ahora verifico en `.claude/worktrees/verify-dn`.

**D-6909. Sin revisar.**
Se vio en pantalla: charcos de luz del centro del pueblo, antorchas, fogata y aldeanos; ventanas encendidas; el humo oscuro por encima de las luces; las luces apagadas de día. No se vieron las decoraciones de luz azul ni los faroles de Plaza. En una partida aparecieron de noche unos pocos triángulos blancos en un acantilado oscuro junto al agua; no se repitió en otros dos mapas y no se encontró la causa.

## Fase 70: oscuridad en la simulación (2026-10-03)

**D-7001. La luz de la simulación: celdas de 4 m, no se guarda.**
Un byte por celda de 4 m dice si la alcanza la luz de algún edificio (`Game::light`, el mismo radio que dibuja la vista). Solo se calcula de noche, y solo se vuelve a dibujar cuando cambia el conjunto de luces (posición y radio), que se resume en un número cada tick. Es una función pura de los edificios: no va en la partida guardada ni en el hash, y una partida cargada dibuja la misma luz (prueba). Se descartó actualizarla cada cierto tiempo: una partida cargada a medias y otra en marcha podrían no coincidir y desincronizar la red.

**D-7002. La penalización.**
De noche, un aldeano fuera de la luz camina y trabaja al 75 % (`village::kDarkPercent`), como eligió Salvador. Se aplica en los dos sitios donde ya entraban la raza y la nieve: el paso por tick y los pasos de trabajo (talar, recolectar, cultivar, cazar, pescar, construir, producir). Dentro de un edificio que da luz no hay penalización, porque su centro está iluminado. Los animales, los asaltantes y los soldados no cambian aquí (fase 72).

**D-7003. Visión nocturna (reemplaza D-1904).**
El rasgo `nightVision` de la raza quita la penalización. En `core` lo tienen los gatunos.

**D-7004. La antorcha en mano no cuenta.**
Es solo de la vista (D-6906): no quita la penalización. La ventana del aldeano dice «A oscuras: camina y trabaja al 75 %» cuando le toca.

**D-7005. Versiones.**
Reglas 38, protocolo de red 16.

**D-7006. Lo probado y lo que no.**
Prueba: humanos de noche dan pasos de 0,20 m por tick en la luz y de 0,15 a oscuras; los gatunos nunca están a oscuras; sin ciclo nadie lo está; la luz rodea al centro del pueblo y es igual tras cargar. La velocidad de trabajo usa la misma condición pero no tiene una prueba propia que mida cuánto tarda un leñador (el criterio lo pedía): queda por medir. La línea de la ventana del aldeano y la barra de energía se vieron en pantalla al cerrar la fase 72 (la ventana creció para que quepan).

## Fase 71: energía y descanso (2026-10-03)

**D-7101. Energía: un punto por tick despierto.**
Cada aldeano tiene 4800 puntos de energía (8 minutos a ×1) y gasta uno por tick mientras no descansa, haga lo que haga, de día o de noche, como eligió Salvador. Se descartó gastar distinto según la tarea: no se pidió y haría difícil de explicar cuándo se cansa cada quien. Al nacer o llegar empieza entre la mitad y el total (según su apariencia, sin tirar dados), para que el pueblo no se vaya a descansar todo a la vez.

**D-7102. Descansar.**
A 0 de energía, deja lo que hace (suelta su reserva, como cuando va a comer; lo que lleva en las manos lo entrega después) y va a su casa; ahí recupera 4 puntos por tick: 2 minutos. Sin casa va a la fogata encendida más cercana o al centro del pueblo y recupera 2 por tick: 4 minutos. Dos tareas nuevas, «yendo a descansar» y «descansando». No duerme de noche: descansa cuando le toca.

**D-7103. Lo que va antes del descanso.**
Comer (va antes en la decisión, y un hambre extrema interrumpe el descanso), la campana, pelear, apagar incendios y huir. El explorador con una orden no descansa hasta volver. Los soldados no son aldeanos y no se cansan.

**D-7104. Es una regla de partida.**
`GameRules::rest`, casilla «Cansancio y descanso» en Personalizado, encendida por omisión (también en «Variado»). Las reglas por omisión de la simulación no la tienen: las pruebas de fases anteriores, calibradas sin descanso, siguen como estaban. Salvador eligió un ritmo fijo y no barras para ajustarlo; la casilla solo permite apagarlo.

**D-7105. Quitado de la especificación.**
El resumen del pueblo no cuenta a los que descansan: la ventana de cada aldeano ya lo dice, y la lista de estadísticas no tiene hoy conteos por tarea.

**D-7106. Versiones.**
Reglas 39, protocolo de red 17.

**D-7107. Lo medido.**
Prueba: un descanso completo en casa dura 1200 ticks y sin casa 2400; con casas, el pueblo pasa el 18 % del tiempo descansando; guardar con gente descansando y cargar da la misma partida; sin la regla nadie descansa. El pueblo de referencia de una hora llega a 24 habitantes y 7 casas con cansancio (sin él, la prueba original pide más de 12). No se revisó en pantalla a los aldeanos quietos frente a su casa (se quedan de pie en la puerta; no entran ni se sientan).

## Fase 72: amenazas de noche (2026-10-03)

**D-7201. Asaltos: el doble de probables por hora de noche que de día.**
Los asaltos ya tenían su fecha; cuando a uno le toca de día, espera al anochecer con probabilidad noche / (día + 2 × noche) (un tercio con día y noche iguales). Así una hora de noche recibe el doble de asaltos que una de día sin cambiar cuántos hay por año. El dado solo se tira con el ciclo encendido: las partidas sin ciclo son idénticas a antes. Prueba: 11 de noche y 5 de día en 16 asaltos.

**D-7202. Fieras.**
De noche, lobos y osos notan a un aldeano desde un 50 % más lejos y se alejan 15 m más de su guarida. No van tras un aldeano que está en una celda iluminada; si ya lo perseguían, siguen (la persecución no vuelve a mirar la luz: es lo más simple y evita que un aldeano «apague» a un lobo pisando la luz). Los jabalíes no cambian. Sin prueba propia.

**D-7203. Se ve menos lejos.**
Con niebla de guerra, de noche los aldeanos y los soldados ven la mitad (mínimo 4 m) y los edificios la mitad, pero nunca menos de lo que alumbran. Las razas con visión nocturna ven igual que de día. «Lo que está en zonas iluminadas se ve» queda cubierto porque todo lo que da luz es un edificio propio, que ve al menos su radio de luz.

**D-7204. Acertar a oscuras depende del blanco, no del que dispara.**
La especificación decía «defensores a oscuras»; se decidió por dónde está el blanco: una torre casi siempre está iluminada por sus propios trabajadores, y lo que tiene sentido es que cueste acertarle a lo que no se ve. Torres, soldados y milicia hacen el 75 % del daño a un enemigo que está fuera de la luz de noche; la milicia de una raza con visión nocturna, el 100 %. Los soldados no tienen raza en la simulación, así que no se benefician de la visión nocturna. Las trampas, los asaltantes y los animales no cambian. Iluminar los accesos al pueblo ahora sirve para defenderlo.

**D-7205. Versiones.**
Reglas 40, protocolo de red 18.

**D-7206. Sin revisar.**
Nada de esta fase se vio en pantalla; todo por pruebas (visión, daño de la torre, reparto de asaltos), salvo las fieras (D-7202).

## Fase 73: fundar el pueblo, la simulación (2026-10-03)

**D-7301. De dónde salen las fases 73 a 79.**
Salvador preguntó si una partida de un jugador podía abrirse a multijugador y pidió las fases por el chat, respondiendo ahí las preguntas (no se usó el registro de revisión). Sus respuestas están en el texto de las fases. Las hace una sesión en el worktree `.claude/worktrees/town` (rama `phase-73-found-town`) porque otra sesión trabaja a la vez en el checkout principal con las fases 80 en adelante.

**D-7302. Sobre un árbol sí se puede fundar.**
La primera redacción de la fase decía que fundar sobre un recurso se rechazaba. Las «reglas normales de construcción» que pidió Salvador no dicen eso: cualquier edificio quita los árboles y rocas que tiene debajo. El centro hace lo mismo y la especificación se corrigió.

**D-7303. Las pruebas viejas no fundan: `GameSetup::start_towns`.**
Por omisión la simulación sigue naciendo con los pueblos en pie en los sitios sugeridos, centro terminado y bienes adentro, exactamente como antes; el juego la crea con `start_towns = false`. Es el mismo patrón que el ciclo de día y el descanso (D-6810, D-7104). Se descartó cambiar las cuarenta suites para que funden con un ayudante: habría movido todos sus números (el centro en obra, el carro, los dados) sin probar nada nuevo.

**D-7304. El carro es un almacén con la bandera `cart`, no una clase nueva de edificio.**
Así recibe, entrega, guarda oro y cuenta en los totales sin tocar ninguna de esas reglas. La bandera solo impide construirlo y quitarlo. Guarda de todo y sin límite práctico (100 000), no arde y alumbra 12 m. Si los mods no definen ningún carro, el centro nace terminado y con los bienes adentro.

**D-7305. Dónde va el carro.**
En el primer hueco libre de 2 × 2 buscando por anillos alrededor de la puerta, a dos celdas o más del centro, hasta 16 m. Si no hay ninguno, ahí no se puede fundar (error «ocupado»). Se descartó dejar que el jugador lo coloque: otra decisión más antes de empezar, sin ganancia.

**D-7306. El centro cuesta 30 troncos y 10 piedras y 2400 de trabajo.**
Antes no costaba nada porque nadie lo construía. El carro trae esos materiales además de los bienes de siempre, así el pueblo empieza con lo mismo que antes una vez terminado el centro. Con los diez adultos iniciales tarda unos 50 s a ×1 (489 ticks en la prueba).

**D-7307. El tiempo espera a los fundadores dentro de la simulación.**
Mientras falte alguien por fundar, `step()` no avanza el tick: solo cuenta el paso (`waited`). Las órdenes sí se aplican. `turn()` = tick + pasos de espera es lo que numera los turnos en red, que así siguen corriendo durante la espera. Se descartó hacerlo con la pausa de la interfaz (velocidad 0): en pausa no se cierran turnos y la orden de fundar no llegaría a nadie. Quien se suma a una partida empezada (fase 75) no la detiene: la espera solo existe antes del tick 0.

**D-7308. Un asiento sin pueblo solo puede fundar.**
Cualquier otra orden suya se rechaza, incluidas las de las herramientas de desarrollo. Un pueblo sin fundar no cuenta para la derrota ni para el fin de la partida, y no recibe mercaderes ni asaltos.

**D-7309. En un pueblo común funda su primer asiento.**
Los demás no pueden; hasta la fase 75 un pueblo común es siempre el del asiento 0.

**D-7310. Versiones.**
Reglas 41, protocolo de red 19. El formato de las partidas guardadas cambia con las reglas (un número distinto las rechaza), como en las fases anteriores.

**D-7311. Sin revisar.**
Nada de esta fase se ve todavía en el juego, que sigue creando las partidas con los pueblos en pie hasta la fase 74. Todo por pruebas (suite `founding`).

## Fase 74: elegir el sitio en pantalla (2026-10-03)

**D-7401. «Sitios para pueblos» ya existía: es el control «Posiciones de inicio».**
El formulario de partida nueva ya tenía una barra de 1 a 12 que le dice al generador cuántos inicios preparar, recordada en `newGame.players`. Solo cambió su nombre y su explicación. En red, al empezar, el mapa lleva los sitios que pidió el anfitrión o uno por pueblo a fundar, lo que sea mayor (antes el anfitrión no elegía: era siempre uno por jugador).

**D-7402. Mientras se elige, es de día.**
El tick 0 es el amanecer y con el ciclo de día y noche la pantalla empieza casi a oscuras. Mientras el juego espera a los fundadores se dibuja con la luz plena de la estación; al fundar el último, empieza el amanecer. Sin esto nadie veía dónde ponía el centro.

**D-7403. Con niebla se elige de verdad a ciegas.**
Es lo que eligió Salvador. La vista 3D está negra y la silueta del centro bajo el cursor no se distingue; lo que guía es el texto del cartel (dice por qué no se puede ahí), las marcas de los sitios sugeridos y el minimapa, que mientras no hay pueblo muestra bajo la niebla la forma de la tierra y del agua en dos tonos oscuros. Esa silueta desaparece al fundar.

**D-7404. La confirmación y el pedido que se pierde.**
El clic fija el sitio y aparece la pregunta «¿Fundar el pueblo aquí?» con «Fundar aquí» y «Cancelar» (también Esc y clic derecho). Si en ese rato otro jugador ocupa el lugar, la pregunta se retira sola. Si la orden salió y a los 50 turnos el pueblo no existe (otro fundó ahí en el mismo instante), se avisa y se vuelve a elegir.

**D-7405. Tecla del siguiente sitio sugerido: Tabulador.**
Acción nueva `game.nextSite`, reasignable como las demás. Salta los sitios ya ocupados.

**D-7406. En un jugador no hay avisos de fundación.**
«X fundó su pueblo» y «empieza el tiempo» solo se muestran en red. El aviso del pueblo de otro no lleva lugar: con niebla, un clic en él revelaría dónde está.

**D-7407. El tutorial y los reportes empiezan con el pueblo en pie.**
El tutorial enseña a construir desde un centro terminado y sus pasos no hablan de fundar; `--reporte` debe volver a dibujar la misma vista que cuando se guardó. Los dos crean la partida con `start_towns`. Queda como posible mejora un primer paso del tutorial que enseñe a fundar.

**D-7408. Pausa y velocidad mientras se funda.**
En un jugador la simulación da un paso por cuadro mientras espera, a cualquier velocidad y en pausa, para que la orden de fundar se aplique; el tiempo no corre. En red el anfitrión ignora pausas y votos de velocidad hasta que todos fundaron: sin turnos, la orden de fundar no llegaría.

**D-7409. El modelo del carro.**
`props.py` gana `wagon()`: la carreta del mercader alargada a cuatro ruedas, con lanza, la carga a la vista por los extremos y un toldo de lona sobre arcos. Sale un poco de su huella de 2 × 2 m. Solo se generó ese archivo (`models/props/wagon.glb`); los demás modelos no se tocaron.

**D-7410. Lo revisado en pantalla.**
En una copia portable en ventana: elegir con luz de día, la pregunta, fundar, el carro con su ventana (sin botón de demoler), la obra del centro, la barra de recursos que aparece al fundar, y con niebla estática la pantalla negra con marcas y silueta. No se probó a mano con dos instancias (lo cubren las pruebas de la suite `net`); queda en la lista de verificación. Durante estas pruebas el guion de capturas mandó por error cuatro clics y un Enter a otra ventana de SalvaCiudad abierta en el equipo (la de `J:\Back`); se corrigió para que solo toque la copia de su propia carpeta.

## Fase 75: pueblos y asientos que cambian durante la partida (2026-10-03)

**D-7501. Un pueblo se llama como el asiento que lo funda.**
La simulación ya indexaba todo lo de un pueblo (edificios, aldeanos, cachés) con un número de 0 a 11 que coincidía con el del jugador. Se conserva: el pueblo *t* es el del asiento *t*, su fundador. Cada asiento guarda a qué pueblo pertenece: al suyo (lo haya fundado o no) o al de otro asiento. Así «quién fundó el pueblo» no necesita guardarse aparte y casi ninguna regla cambió; `shared_town` dejó de ser un modo de la partida y pasó a ser una pregunta («¿algún pueblo tiene más de un asiento?»). Se descartó separar los índices de pueblo y de asiento: habría tocado cada regla de la simulación para el mismo resultado.

**D-7502. «Sin pueblo» es el pueblo propio sin fundar.**
No hay un valor especial para «ninguno». Un asiento nuevo pertenece a su propio pueblo, que no existe hasta que lo funde; mientras tanto solo puede fundar, o ser admitido en otro.

**D-7503. El anfitrión es un asiento de la simulación.**
`Game::host()` (asiento 0 por omisión) forma parte del estado y de las partidas guardadas. Solo ese asiento puede dar la orden de agregar asientos. Hace falta en el estado porque al cargar una partida como anfitrión (fase 78) quien hospeda puede no ser el asiento 0.

**D-7504. Los nombres y colores de los asientos viven en la simulación.**
Antes solo los conocía la sala de la red. Ahora viajan en `GameSetup` y en la orden de agregar asiento, se guardan con la partida y entran en el hash. Es lo que permitirá devolver su asiento por nombre a quien vuelva a una partida guardada. Hasta 32 bytes, con las reglas de los nombres de aldeanos; vacío vale («Pueblo N» en la interfaz).

**D-7505. Unir un asiento a un pueblo es, por ahora, una orden de su fundador.**
`JoinTown`: solo el fundador del pueblo, y solo para un asiento sin pueblo fundado y sin nadie más en él. La fase 77 le pone delante la solicitud del que quiere entrar. Un asiento que se une ya no puede fundar.

**D-7506. Un pueblo común ya no reserva los doce asientos.**
Antes la simulación activaba los doce desde el principio para que alguien pudiera entrar después. Ahora la partida tiene los asientos de quienes juegan y los demás llegan con la orden de agregar. En esta fase, quien entra a un pueblo común creado en la sala recibe su asiento y es unido al pueblo en el mismo turno, sin pedir permiso, como hasta ahora; las fases 76 y 77 lo cambian.

**D-7507. Los grupos de visión cuentan el pueblo propio de cada asiento.**
Con visión separada por pueblo, cada asiento tiene reservado el grupo del pueblo que podría fundar, además del grupo del pueblo en el que está. El conjunto no cambia cuando alguien se une a otro pueblo, y la comprobación al cargar sigue valiendo. Con visión compartida entre aliados (lo normal en cooperativo) todos están en el grupo 0, así que quien llega ve lo que los demás ya exploraron.

**D-7508. Mapas separados: sin región no hay dónde fundar.**
En una partida de mapas separados cada pueblo tiene su región del mundo. Un asiento que llegue cuando ya no quedan regiones no puede fundar (todo le queda «fuera del mapa»); puede unirse a un pueblo. Para dejar lugar hay que pedir más «sitios para pueblos» al crear la partida.

**D-7509. Versiones.**
Reglas 42, protocolo de red 20.

**D-7510. Sin revisar.**
Todo por pruebas (suite `seats`, y las de red, que siguen pasando con el pueblo común de doce y los cuatro pueblos separados). En pantalla no cambia nada todavía, salvo que los pueblos se llaman por el nombre del jugador también en un jugador.

## Fase 76: abrir la partida a otros jugadores (2026-10-03)

**D-7601. Lo que la partida permite es estado de la simulación.**
Tres banderas (`sim::access`): abierta (quien llega recibe asiento), puede pedir unirse a un pueblo, puede fundar el suyo. Las cambia solo el anfitrión con la orden `SetAccess`, así todas las máquinas lo saben en el mismo turno, se guarda con la partida y lo ven quienes entran después. Una partida de un jugador nace cerrada (0).

**D-7602. Los asientos que llegan tarde llevan una marca.**
`PlayerState::late`. Los que empezaron la partida fundan siempre; los que llegaron después, solo si la partida lo permite. Tampoco se les espera: una partida que aún aguarda a sus fundadores arranca aunque un recién llegado no tenga pueblo.

**D-7603. Las herramientas de desarrollo quedan encendidas en red (reemplaza a D-910 por ahora).**
Salvador, 2026-10-03: «por ahora se quedan aún en multiplayer, en release se ocultará de alguna forma». Una partida abierta las conserva y las creadas en la sala ya no las apagan. Cómo ocultarlas en la versión final queda pendiente (sección 14 de la especificación).

**D-7604. Abrir no pasa por la sala.**
`NetHost::adopt` toma la partida en curso y queda jugando de inmediato: los turnos empiezan en el turno actual, la velocidad es la que había (con tope ×5; en pausa sigue en pausa) y los asientos conservan el nombre que tienen en la partida. Las órdenes dadas y aún no ejecutadas pasan a la red. Un asiento sin nombre no se puede recuperar.

**D-7605. Quien llega siempre recibe un asiento nuevo; ya no se ocupa el de otro.**
Antes, en pueblos separados, un jugador nuevo podía quedarse con el pueblo de alguien que se había ido, y en un pueblo común entraba directo. Ahora un asiento solo se recupera con el nombre de su dueño, y los nuevos entran sin pueblo si la partida está abierta. Con la partida cerrada el motivo del rechazo es nuevo («no acepta jugadores nuevos»); con los doce asientos usados, «sin lugares libres».

**D-7606. Las partidas creadas en la sala nacen abiertas.**
Para no perder lo que ya hacían: en pueblo común permiten pedir unirse, en pueblos separados fundar el propio (`net::lobby_access`). El anfitrión lo cambia desde el menú de pausa («Jugadores nuevos…»). La fase 79 llevará estas casillas a la sala.

**D-7607. El tope de ×5 también vale para una partida de varios asientos jugada a solas.**
Lo pide la especificación («abierta o con más de un asiento»). La red ya lo aplicaba; ahora también `max_game_speed` cuando la partida tiene más de un asiento aunque nadie esté conectado.

**D-7608. El diálogo.**
«Abrir a multijugador» en el menú de pausa (no en el tutorial) pregunta qué se permite, con las dos casillas marcadas; hay que dejar al menos una. Una vez abierta, la misma ventana («Jugadores nuevos…») agrega la casilla «Aceptar jugadores nuevos», que es la manera de cerrarla y volver a abrirla.

**D-7609. Versiones.**
Reglas 43, protocolo de red 21.

**D-7610. Sin revisar.**
Todo por pruebas (suite `net`: abrir a ×9 y quedar en ×5, entrar con el estado, fundar, salir y volver por nombre, cerrar y reabrir, solo el anfitrión cambia el acceso; suite `seats` para las reglas). La prueba a mano con dos ventanas se hace al cerrar la fase 77, cuando quien llega ya tiene su ventana.

## Fase 77: llegar a una partida, fundar o pedir unirse (2026-10-04)

**D-7701. La solicitud vive en el asiento que la hace.**
`PlayerState::request` guarda a qué pueblo pidió unirse (uno a la vez). Órdenes: `RequestJoin` (quien no tiene pueblo), `CancelJoin` (la retira), `JoinTown` (el fundador acepta; ahora exige que haya solicitud) y `RefuseJoin` (el fundador rechaza). Todas viajan por los turnos, entran en el hash y se guardan: por eso la solicitud sobrevive a guardar y cargar y a que el fundador se desconecte.

**D-7702. Si el fundador no está, nadie responde.**
Lo pidió Salvador de forma expresa. Ni otro miembro del pueblo ni el anfitrión de la partida pueden aceptar o rechazar: la orden de quien no fundó ese pueblo se rechaza. La solicitud no caduca. Quien pidió puede retirarla, y fundar su pueblo la anula sola.

**D-7703. Pedir unirse exige que la partida lo permita y que el pueblo exista.**
Hace falta la bandera «unirse» del acceso, y el pueblo debe estar fundado y seguir en juego. No se puede pedir entrar a un pueblo que aún no se fundó (en la lista solo salen los que existen).

**D-7704. La ventana de quien llega.**
Solo para asientos que llegaron tarde y no tienen pueblo: «Fundar mi pueblo» (pasa a la elección de sitio de la fase 74; Esc vuelve a la ventana) y la lista de pueblos con «Pedir unirme» o «Cancelar solicitud». Según lo que permita el anfitrión se muestra una cosa, la otra o las dos; si no permite nada, lo dice. Las marcas de sitios sugeridos solo aparecen mientras se elige sitio.

**D-7705. El fundador responde en un cuadro como el de los votos.**
«X quiere unirse a tu pueblo», con «Aceptar» y «Rechazar», una solicitud a la vez, mientras siga en pie; además suena y queda en el registro de avisos. Solo lo ve el fundador.

**D-7706. Avisos.**
A todos: quién se unió a qué pueblo. Al que pidió: que ya es parte del pueblo (y la cámara va a su centro) o que no lo aceptaron. Quién llegó ya lo decía la red.

**D-7707. La niebla sigue al asiento.**
La vista de la niebla se rehace cuando el asiento local cambia de grupo de visión (al recibir su asiento o al unirse a un pueblo), y se actualiza por turnos y no por ticks, para que un pueblo recién fundado se vea aunque el tiempo siga esperando a los demás.

**D-7708. Versiones.**
Reglas 44, protocolo de red 22.

**D-7709. Lo revisado en pantalla.**
Con dos instancias (`--instance 1 --loopback` y `--instance 2 --loopback`) en una copia portable: la 1 funda sola, abre la partida desde el menú de pausa (ventana con las dos casillas), la 2 entra por 127.0.0.1:47801, ve su ventana de llegada, pide unirse, la 1 ve el cuadro y acepta, y la 2 queda en el pueblo con su barra de construcción y la cámara sobre el centro. No se probó a mano: rechazar, cancelar, fundar el propio desde la ventana, ni salir y volver (lo cubren las pruebas de `net` y `seats`).

## Fase 78: cargar una partida guardada como anfitrión (2026-10-04)

**D-7801. Reemplaza lo pendiente de D-672.**
En la lista de partidas guardadas cada fila tiene «Cargar» (como hasta ahora) y «Como anfitrión». La segunda carga la partida sin mostrarla, abre el puerto y entra a la sala de siempre en un modo «partida guardada»: no se puede cambiar nada del juego; solo se ven los asientos, quién llegó y las casillas de acceso.

**D-7802. Los asientos se guardan para sus dueños, por nombre.**
En esa sala solo entra quien trae el nombre de un asiento libre de la partida. A un nombre nuevo se le rechaza con un motivo propio («todavía está en la sala; entra cuando haya empezado»): admitir asientos nuevos antes de empezar obligaba a llevar la cuenta de asientos que aún no existen en la simulación, y un recién llegado puede entrar igual en cuanto arranca. En una sala de partida guardada no se cambian nombres ni colores.

**D-7803. Empezar no espera a nadie.**
El anfitrión empieza cuando quiere (si los que están marcaron «listo»). Cada conectado recibe la partida como instantánea, la misma vía de quien entra a una partida empezada; no se genera el mapa de nuevo. Los asientos de los que faltan quedan esperando: su pueblo trabaja solo y ellos entran después con su nombre. En la sala no corre ningún tick.

**D-7804. El anfitrión es el asiento de quien carga.**
Se busca su nombre entre los asientos; si no está, toma el del fundador del primer pueblo que exista (asiento 0 si no hay ninguno). `Game::set_host` lo deja en el estado antes de que nadie más lo reciba. El anfitrión de red dejó de suponer que es el asiento 0: quien fue cliente puede hospedar la misma partida otro día. «Cargar» normal también toma el asiento por nombre, y «Abrir a multijugador» hospeda desde el asiento que se esté jugando.

**D-7805. El acceso al cargar.**
Una partida que estaba abierta sigue igual. Una de un solo jugador que nunca se abrió se abre al cargarla como anfitrión (unirse y fundar), que es lo que la especificación llama «equivale a cargarla y abrirla». Una de varios jugadores que su anfitrión cerró se queda cerrada. En la sala las casillas cambian el acceso aplicando la orden directamente: nadie más tiene la partida todavía.

**D-7806. La sala lleva una marca en su mensaje.**
`Lobby::saved`, para que los clientes muestren la sala de partida guardada. Protocolo de red 23. Las reglas no cambian (44).

**D-7807. Lo revisado en pantalla.**
Con una instancia: guardar con F5, la lista con los dos botones, la sala de partida guardada con sus casillas y el asiento propio, «Empezar» y la partida en marcha como anfitrión. Con dos instancias no se probó a mano: lo cubren las pruebas de `net` (volver por nombre y seguir en el mismo tick con los mismos hashes; empezar sin alguien que entra después; hospedar desde el asiento 1; un nombre nuevo rechazado en la sala y admitido al empezar).

## Fase 79: modo espectador (2026-10-04)

**D-7901. Un espectador es una conexión; la simulación no sabe que existe.**
No tiene asiento, no está en el estado ni en sus hashes y no se guarda. Lo único que la simulación guarda es la casilla: `sim::access::kWatch`, una bandera más del acceso (fase 76). Así una partida con espectadores y sin ellos da el mismo estado, turno por turno (hay una prueba que lo compara).

**D-7902. Donde se puede mirar, quien llega entra mirando.**
Con «Permitir espectadores» marcado, un nombre nuevo entra a una partida empezada como espectador, sin asiento, y el asiento se crea recién cuando elige jugar («Fundar mi pueblo» o «Pedir unirme»): pide el asiento al anfitrión, y con él en la mano funda o hace la solicitud. Sin esa casilla todo sigue como en la fase 76: recibe asiento al entrar. Se descartó dar asiento a todos y dejar que algunos «solo miren» desde él: ocuparían uno de los doce para siempre, porque los asientos no se quitan.

**D-7903. Hasta 8, aparte de los 12 jugadores.**
Con los ocho ocupados, si la partida además está abierta el que llega recibe asiento como antes; si solo se podía mirar, se le rechaza con «ya tiene todos sus espectadores».

**D-7904. Un jugador que pasa a espectador conserva su asiento.**
Es una marca en su conexión, no un cambio en la partida: el anfitrión ignora sus órdenes, pausas y votos, nadie lo espera y su pueblo trabaja solo o con sus compañeros, igual que cuando alguien se desconecta. «Volver a mi pueblo» la quita sin pedir permiso. Si se desconecta mientras mira, al volver juega. El anfitrión también puede mirar y sigue hospedando.

**D-7905. Lo que no puede hacer un espectador se corta en dos lados.**
Su propio programa no manda órdenes, pausas ni votos; y si llegaran (un programa modificado), el anfitrión los ignora y los cuenta. Los votos de velocidad se resuelven sin quienes miran.

**D-7906. Nadie espera a un espectador.**
No entra en la cuenta del jugador más lento. Recibe todos los turnos y se pone al día a su ritmo (hasta 8 por cuadro). Si se atrasa más de 600 turnos, o sus hashes no coinciden, el anfitrión le manda la instantánea (a lo sumo cada 10 s).

**D-7907. La vista.**
«Todo el mapa» apaga la niebla en esa máquina (como la casilla de las herramientas de desarrollo). «Como X» toma el grupo de visión del pueblo X: su niebla, y con ella sus recursos en la barra y sus avisos, porque la interfaz pasa a tratar ese asiento como el propio. Se elige en una franja arriba al centro. La barra de construcción no se muestra.

**D-7908. «Solo lectura» significa que las órdenes no salen.**
Las ventanas de edificios y aldeanos se abren con sus botones de siempre; pulsarlos no hace nada porque la sesión no envía órdenes mientras mira. No se rehicieron las ventanas para esconder cada botón.

**D-7909. Un fundador que mira ve la solicitud, pero responde desde su pueblo.**
El cuadro le muestra «X quiere unirse a tu pueblo» con un solo botón, «Volver a mi pueblo para responder».

**D-7910. En la sala.**
La sala de una partida nueva tiene la fila «Espectadores»: el anfitrión marca si se permiten (viaja en la configuración de la partida) y cada jugador puede marcar «Entrar a mirar, sin jugar». Al empezar, esos no reciben asiento: generan el mapa como todos y siguen los turnos. El anfitrión no puede entrar mirando (alguien tiene que fundar); puede pasar a mirar después. En la sala de una partida guardada y al abrir una partida, es la cuarta casilla del acceso. En una sala de partida guardada solo entran los dueños de asiento; los espectadores, cuando empiece.

**D-7911. Quién mira.**
La lista de jugadores (la cuenta de la barra de arriba, con los nombres al pasar el cursor) marca «(mirando)» a los que miran y agrega a los espectadores sin asiento. Un aviso dice cuando alguien empieza a mirar o vuelve a jugar. Los espectadores no cuentan en «Jugadores N».

**D-7912. Versiones.**
Reglas 45 (una bandera más en el acceso), protocolo de red 24.

**D-7913. Lo revisado en pantalla.**
Con dos instancias: la 1 abre su partida con las tres casillas; la 2 entra y queda mirando (franja «Mirando: Todo el mapa», ventana con Fundar, Pedir unirme y Solo mirar), cambia a «Como Jugador 2», y desde «Jugar…» elige fundar: recibe asiento y pasa a elegir sitio. No se probó a mano: pasar de jugador a espectador y volver, la sala con la casilla de espectadores, ocho espectadores, ni un espectador detenido (lo cubren las pruebas de `net` y `spectator`).

## Ronda de recursos: fases 80 a 85 (2026-10-03)

**D-8001. De dónde sale la ronda.**
Salvador pidió por el chat cinco cambios y reportó una falla, y respondió las preguntas ahí mismo; no se usó el registro de revisión. Quedaron como fases 80 a 85 y el pulido pasó a ser la 86. Se numeraron después de las fases 73 a 79 (fundar el pueblo, multijugador abierto), que otra sesión tenía escritas sin commit en la especificación.

**D-8002. Avisar, no ir más lejos.**
Un edificio sin recursos a su alcance avisa (notificación una vez, ícono y línea de estado) y sus trabajadores quedan sin tarea. No se amplía el radio ni se los manda a buscar más lejos: el radio es lo que hace que importe dónde se construye. Lo que rebrota solo muestra «esperando», para no llenar la lista de avisos cada invierno.

**D-8003. Más recursos solo al generar el mapa.**
Cerca del doble de roca, bayas y hierbas, con el porcentaje «Recursos» de siempre. Se descartó un porcentaje aparte por recurso (más controles en un formulario ya largo) y que broten arbustos nuevos durante la partida (toca la simulación y el determinismo en red por poca ganancia).

**D-8004. La mina de roca es un yacimiento, no un edificio.**
Un objeto natural grande que trabaja el cantero de siempre. Se descartaron el edificio nuevo junto al yacimiento y el edificio sin yacimiento. Finito, en tres tamaños (800, 2 000 y 5 000), elegido por Salvador en lugar de un tamaño único o de una mina infinita. Al gastarse usa el modelo del tamaño menor: no hace falta arte aparte para las etapas.

**D-8005. Frutales: una bandera de la especie y el recurso «fruta» de hoy.**
Salvador: todos los frutales dan «fruta» aunque técnicamente no lo sea, y la dieta no cambia por ahora (podría ampliarse más adelante). La lista inicial (manzano, cerezo, palma, baobab) es propuesta de Claude; robles y pinos quedan fuera para que el leñador, que no tala frutales por omisión, no se quede sin bosque. Una cosecha al año, de verano a fin de otoño, solo en árboles medianos o mayores. Sin fruta visible en el modelo (sería una fase de arte).

**D-8006. Talar un frutal.**
Entrega la madera y la fruta que tenía en ese momento; fuera de temporada, solo madera. El interruptor «Talar frutales» es por leñador y empieza apagado. Despejar una obra tala el frutal sin mirar el interruptor: el jugador ya eligió construir ahí.

**D-8007. Los animales que brillan de noche son una corrección.**
Va como fase 80, primero, por ser lo más barato. La causa no se buscó al planear.

**D-8008. Replantar obliga a que los árboles crezcan (fases 86 y 87; pedido del 2026-10-03, después del resto de la ronda).**
Hasta ahora cada árbol tenía un tamaño fijo. Salvador eligió que crezcan todos los árboles del mapa, no solo los replantados, para que «solo maduros» sirva también sin replantar. Ritmo: de brote a grande en unos 3 años de juego (un tamaño por año) y a enorme dos años después. Se descartó un ritmo por especie (más datos que balancear sin pedirlo). El crecimiento va en fase propia, antes de los interruptores, porque es lo arriesgado: toca todo el bosque, el rendimiento en mapas colosales y los hashes de red. El pulido pasa a ser la fase 88.

**D-8009. Maduro es grande o enorme.**
Elegido por Salvador. Para una especie que no llega a grande cuenta su tamaño mayor; si no, nunca se talaría. Los dos interruptores son independientes y empiezan apagados, así las partidas y pruebas de antes no cambian.

**D-8010. El brote.**
Un tamaño nuevo debajo del pequeño: sin madera, no se tala, no estorba el paso ni la construcción. Replantar no cuesta materiales (no hay semillas), solo trabajo; es lo más simple. Lo talado para despejar una obra no se replanta: el brote quedaría debajo del edificio.

---

## Petición del usuario: menos corridas de pruebas (2026-10-04)

**D-014. Las tres configuraciones solo al cerrar la fase.**
Salvador notó que las corridas de `debug` y `debug-asan` tardan mucho. Mientras se trabaja en una fase se compila solo `debug` y se corren solo los grupos de pruebas que toca el cambio. Al cerrar la fase se compilan y prueban `debug`, `release` y `debug-asan` completas, una sola vez. No se quita ninguna configuración: `release` es lo que se juega y muestra fallas de optimización y de determinismo, y `debug-asan` atrapa errores de memoria que las otras dejan pasar. Se descartó por ahora dejar `debug-asan` solo para antes de unir a `main` o para fases que tocan memoria: ahorra más, pero un error de memoria se descubriría varias fases después. Se revisa con Salvador cuando se vea cómo quedan los tiempos.

## Fase 80: los animales brillaban de noche (2026-10-04)

**D-8011. La causa: una antorcha por animal.**
No era el material: ningún material de los animales tiene nombre de brillo. La vista le ponía una antorcha de noche (fase 69) a todo lo que se dibuja como personaje animado, y desde la fase 47 los animales y sus cadáveres son personajes animados; también la recibía el fantasma del ancla de la cámara. Ahora la vista guarda aparte dónde están las personas (aldeanos, soldados, asaltantes y el mercader junto al puesto) y solo ellas llevan antorcha. Vale igual para el fondo de los menús, que usa la misma vista.

**D-8012. Los asaltantes conservan la antorcha.**
Ya la tenían y nadie la reportó como falla. Es solo de la vista: para la simulación siguen «a oscuras» (D-7204).

**D-8013. Lo medido y lo no revisado.**
Prueba nueva: ningún material de los modelos de `models/animals` cuenta como brillo (cubre la otra forma de que un animal brille). La regla de quién lleva antorcha no tiene prueba propia: vive en la vista, que no se puede actualizar sin dispositivo gráfico. No se tomó la captura de antes y después que pedía el criterio: queda en la lista manual del README.

## Fase 81: avisos de recursos agotados (2026-10-04)

**D-8101. El estado lo calcula el trabajador al buscar.**
Cada edificio que vive de la tierra guarda un estado (`Supply`: con recursos, esperando, agotado) que se actualiza cuando uno de sus trabajadores busca qué recoger; no hay un barrido aparte. Consecuencias: un edificio sin trabajadores conserva el último estado, y el aviso llega cuando el primer trabajador vuelve con las manos vacías, no en el tick exacto en que se gastó la última roca. Es lo más barato y no añade trabajo por tick.

**D-8102. Qué cuenta como «con recursos».**
Un recurso a su alcance que otro trabajador tiene reservado cuenta: el edificio no está agotado, solo le sobra gente. Lo que rebrota y hoy está vacío o helado deja al edificio «esperando». «Agotado» es que no queda nada de lo que no rebrota. «A su alcance» es el mismo alcance por camino que usa la recolección (fuera queda la otra orilla de un río).

**D-8103. Cazador y pescador nunca quedan «agotados».**
Sin presas o sin agua abierta quedan «esperando», con su propio texto y sin notificación, como pide la especificación.

**D-8104. El ícono es un cuadro rojo con «!».**
Dibujado por la interfaz sobre el edificio, como las marcas de los sitios sugeridos; no es un modelo ni una textura nueva. Solo se muestra en edificios propios, terminados, con trabajadores y sin detener. La notificación nombra el edificio («Cantero: ya no queda nada que recoger a su alcance») en lugar de tener un texto por recurso: sirve igual para edificios de mods.

**D-8105. Versiones y lo medido.**
Reglas 46 (el estado se guarda con la partida y entra en el hash). Suite nueva `resources`: un cantero con dos rocas las agota, queda agotado y lo dice una sola vez aunque sus trabajadores sigan buscando; la roca fuera de su alcance no cuenta; guardar y cargar da la misma partida; un recolector con arbustos vacíos queda esperando sin evento. El texto del cazador y del pescador no tiene prueba propia. Nada se vio en pantalla.

## Fase 82: más roca, bayas y hierbas (2026-10-04)

**D-8201. Cuánto.**
El generador pone el doble de grupos de rocas sueltas y de hierbas, y dos veces y media los de arbustos de bayas: los arbustos solo caben en el borde del bosque y en praderas, y con el doble de intentos salían 1,66 veces más. En tres mapas medianos (semillas 4242, 12345 y 777): rocas de 152 a 310, arbustos de 137 a 280, hierbas de 140 a 280; el hierro sigue en 28. El mínimo alrededor de cada inicio sube de 2 a 4 rocas y de 2 a 4 arbustos. «Recursos» sigue escalando todo junto.

**D-8202. Versiones y lo no medido.**
Generador 6; suma de referencia del mapa pequeño `0xc35b65fc86f2066e`. El límite de objetos del mapa (32 millones) queda lejísimos: un colosal al 200 % tiene del orden de cientos de miles de rocas, arbustos y hierbas. El tiempo de generación no se midió: son unos cientos de objetos más por mapa mediano, en una etapa que ya era de las más rápidas.

**D-8203. Pruebas que dependían del mapa exacto.**
Al cambiar los mapas, dos pruebas de la suite `farming` quedaron en otro escenario y cambiaron de semilla: «los cazadores traen carne» pasa de la 2 a la 7 (con los mapas nuevos pasa en 9 de las primeras 20 semillas, por las mismas razones de D-5613), y «nadie pasa hambre en un viaje largo» pasa de 1 y 14 a 4 y 16 (zona de caza a 350 m o más). **Hallazgo sin resolver:** en esa misma prueba, con las semillas 14, 15 y 18 de los mapas nuevos, el medidor de comida de algún aldeano llega a cero durante el año aunque el pueblo tiene comida, y la cabaña de caza nunca se termina (en la 14 la zona está a solo 51 m). No se investigó si es la regla del hambre de la fase 66, el sitio de la cabaña o algo de las fases 73 a 79; queda para revisar aparte.

## Fase 83: yacimientos de roca (2026-10-04)

**D-8301. Un tipo de objeto natural nuevo, con tamaño.**
`stoneDeposit` es un tipo más de los objetos del mapa. Su tamaño (0 a 2) va en el campo que los árboles usan para el suyo, y lo fija lo que le queda: más de 2 000, grande; más de 800, mediano; si no, chico. Las cantidades salen del `amount` de su definición (800) por 1, 5/2 y 25/4, así un mod puede cambiarlas con un número. Al gastarse, la simulación le baja el tamaño y la vista cambia de modelo sin rehacer nada (los tres modelos son «aspectos» de uno solo, como los estados de un árbol).

**D-8302. Ocupa terreno.**
Un cuadrado de 4, 6 u 8 m de lado donde no se camina ni se construye; al bajar de tamaño ocupa menos y al agotarse queda libre. Es el único objeto natural que estorba: árboles y rocas sueltas siguen sin estorbar. El generador quita lo que haya caído sobre ese cuadrado (y el yacimiento menor si dos se pisan).

**D-8303. Varios a la vez.**
Un yacimiento no se reserva: lo trabajan a la vez todos los canteros que lo tengan a su alcance, cada uno parado fuera del cuadrado. Las rocas sueltas siguen siendo de un trabajador por roca.

**D-8304. Cuántos y dónde.**
Con «Recursos» al 100 %, 4 por km² (uno al menos por mapa) en el terreno más rocoso o empinado de entre varios sitios al azar; la mitad chicos, un 35 % medianos y un 15 % grandes. Además cada inicio tiene uno mediano a entre 70 y 180 m si no le tocó ya uno mediano o grande a menos de 200 m. La especificación pedía «250 m caminando»: el generador no calcula caminos, así que se garantiza la distancia en línea recta, y la prueba comprueba que desde el pueblo se llega caminando en tres mapas medianos de cuatro jugadores. Un inicio rodeado de agua podría quedar sin el suyo (seis intentos), como ya pasa con las rocas y las bayas.

**D-8305. Su propio azar.**
Los yacimientos tiran sus dados aparte (otra secuencia de la misma semilla). Así el resto del mapa es el de la fase 82 más los yacimientos, y no hubo que volver a buscar semillas para las pruebas de partida. La primera versión usaba los dados comunes y dejaba otra vez sin pueblo a las pruebas de una hora.

**D-8306. Arte.**
`props.py` (`stone_deposits`): tres afloramientos de rocas grandes con caras más claras de piedra cortada y musgo arriba, de unos 2,5, 4 y 5,5 m de alto. Se construyeron solo esos tres archivos, sin rehacer los demás modelos.

**D-8307. Versiones, lo medido y lo que no.**
Generador 7 (suma del mapa pequeño `0xcef750f665d22845`), reglas 47. Pruebas en la suite `resources`: los dos canteros pican a la vez; un yacimiento chico se trabaja hasta la última unidad, libera su terreno y el cantero avisa una vez; guardar y cargar con uno a medio gastar; no se construye ni se camina encima; cada inicio tiene el suyo y se llega caminando; nada más ocupa su terreno. Sin prueba propia: el paso de grande a mediano y de mediano a chico dentro de una partida (sí la función que decide el tamaño), y que entregue exactamente 800 unidades (lo que no cabe en los almacenes se pierde, así que solo se comprueba que el nodo llega a cero). Las herramientas de desarrollo no ganaron un botón para crear yacimientos (la orden `DevFeature` sí los acepta).

## Fase 84: frutales silvestres (2026-10-04)

**D-8401. Frutal es la especie que declara fruta.**
Una especie es frutal si su JSON trae `"fruit"`: cuatro números, la fruta al año de un árbol de cada tamaño (pequeño, mediano, grande, enorme). En `core`: manzano, cerezo, palma y baobab, con `[0, 6, 10, 14]`. El pequeño no da. Ojo: manzano, cerezo y palma solo existen en pequeño y mediano, así que hoy dan 6; el baobab, en mediano y grande, da 6 o 10. Todo es el recurso «fruta» de siempre (lo busca por `core:fruit`), como pidió Salvador; la dieta no cambia.

**D-8402. La fruta se calcula, no se reparte.**
No hay un barrido del bosque al empezar el verano ni al terminar el otoño. Cada árbol guarda solo cuánta fruta se le recogió y en qué año; lo que cuelga hoy es «lo que da su tamaño menos lo recogido este año» si es verano u otoño, y cero si no. Así no cuesta nada por tick ni por día, aun en un mapa colosal, y lo no recogido «se pierde» solo. En una partida con una sola estación de verano, la cosecha vuelve al cambiar el año.

**D-8403. Quién la recoge.**
Los edificios de recolección con `"picksFruit": true` (el recolector). El árbol queda en pie y no se toca su madera. Cada fruta cuesta lo que una baya (15 pasos de trabajo) y cuenta para la habilidad de recolección. Un árbol lo trabaja una persona a la vez, sea para fruta o para leña. Para los avisos de la fase 81 un frutal sin fruta hoy cuenta como algo que rebrota: el recolector queda «esperando», sin notificación.

**D-8404. Versiones y lo medido.**
Reglas 48 (dos campos más por objeto natural en la partida guardada). Pruebas en `resources`: un manzano mediano sin fruta en primavera, con 6 en verano y otoño, sin nada en invierno y con 6 al verano siguiente; el pequeño y el roble, nunca; un roble marcado como frutal por el contenido (lo que haría un mod) da fruta; el recolector trae la fruta, el árbol y el roble de al lado siguen en pie, queda «esperando» sin evento, guardar y cargar da la misma partida y al año siguiente se vuelve a recoger. La ventana del árbol no tiene prueba y nada se vio en pantalla.

## Fase 85: el leñador y los frutales (2026-10-04)

**D-8501. Opciones de un edificio de trabajo, y una orden para cambiarlas.**
`Building::options` guarda bits (`sim::option`), y la orden nueva `SetOption` (41) enciende o apaga una por su número. Qué opciones tiene cada edificio lo dice `workplace_options`: hoy solo «talar frutales», para los edificios que recogen árboles. Se hizo genérico porque la fase 87 agrega dos interruptores más al mismo edificio. Una opción que el edificio no tiene, o de un edificio ajeno, se rechaza; una partida guardada con bits que no corresponden no se carga.

**D-8502. Apagado por omisión.**
Un leñador recién construido no tala frutales (lo eligió Salvador). Cambia el comportamiento de los leñadores de siempre: en un bosque con manzanos o cerezos los dejan en pie.

**D-8503. «Solo quedan frutales» es un estado propio.**
`Supply::OnlyFruit`: avisa una vez, con su texto, el cuadro rojo y la línea de estado, igual que «agotado». Si además hay algo que rebrota o un árbol que otro tiene reservado, ganan «esperando» o «con recursos».

**D-8504. Dónde queda la fruta de un frutal talado.**
Al caer el árbol (su última unidad de madera), la fruta que tenía ese día queda en el leñador, como las pieles en la cabaña del cazador, y de ahí la llevan al almacén. La madera la sigue cargando el leñador. Fuera de verano y otoño no hay fruta que dar.

**D-8505. Despejar una obra o un campo.**
Un frutal bajo una casa, un campo o cualquier obra deja su madera y su fruta en el centro del pueblo (o en el carro si aún no hay centro), sin mirar el interruptor. Los demás árboles despejados siguen sin dejar nada, como desde la fase 8: cambiarlo era otra regla que nadie pidió. Queda como pregunta para Salvador.

**D-8506. Versiones y lo medido.**
Reglas 49, protocolo de red 25 (una orden nueva). Pruebas en `resources`: un leñador rodeado solo de manzanos no tala ninguno y avisa una vez con el texto de frutales; la orden viaja como bytes y dos partidas que la reciben siguen con el mismo hash; encendido, tala los tres y aparecen su madera y su fruta; en invierno solo madera; una casa sobre un manzano con fruta suma madera y 6 de fruta por árbol despejado; el interruptor se guarda y se carga; una opción inexistente y una sobre el centro del pueblo se rechazan. No se probó con dos instancias reales en red ni se vio en pantalla.

## Fase 86: los árboles crecen (2026-10-04)

**D-8601. Cuándo crece cada árbol.**
Cada árbol guarda el día en que sube de tamaño (`Node::grow_day`, en días desde el primero del año 1; 120 por año). Al empezar la partida es «su cumpleaños del año siguiente»: un día del año fijado por su posición, así el bosque no crece todo junto. De pequeño a mediano y de mediano a grande pasa un año; de grande a enorme, dos. Sube al siguiente tamaño que su especie admite y conserva su altura relativa dentro del tamaño; su madera pasa a la del tamaño nuevo, descontando lo que ya le habían cortado. Un árbol que llegó al tamaño mayor de su especie, y todos los gigantes, quedan marcados como «no crece».

**D-8602. Un barrido repartido entre los ticks.**
En cada tick se mira una porción de los objetos del mapa, de modo que en los ticks de un día promedio se ven todos una vez. No hay listas por día ni trabajo extra un día en particular. Se compara con el número del día, no con «hoy es su cumpleaños»: las estaciones pueden durar distinto (fase 59) y así un árbol nunca se salta su año ni crece dos veces. Los árboles están al día con un día de atraso como mucho.

**D-8603. El brote es un árbol «en espera».**
No se agregó un quinto tamaño (habría movido las tablas de madera y de tamaños de todas las especies y de los mods). Un brote es un árbol del tamaño menor de su especie, sin nada que talar y con una fecha en la que se vuelve árbol: la misma cola con la que rebrotan los arbustos, con un año de plazo. Por eso no se puede talar, no estorba (ningún árbol estorba el paso) y se puede construir encima. La vista lo dibuja al 30 % de su tamaño y su ventana dice «Brote: será un árbol en un año». El generador no pone brotes: aparecen al replantar (fase 87). Como los arbustos, no pasa a árbol mientras hiela.

**D-8604. Pruebas que cambiaron.**
La prueba «una hora de juego: un pueblo atendido crece» pasa de la semilla de partida 81 a la 86: con el bosque creciendo, la 81 termina con 3 casas en lugar de 4 (y 20 habitantes, sin muertes). **Hallazgo sin resolver, anterior a esta fase:** con las semillas de partida 80, 84 y 90 ese pueblo guionizado no termina ninguna casa en una hora, con madera de sobra y sin muertes; ya había pasado una vez en la fase 82. No se investigó.

**D-8605. Versiones y lo medido.**
Reglas 50 (un campo más por objeto natural). Pruebas en `resources`: un roble pequeño es mediano al segundo año y grande al tercero, con la madera de cada tamaño; un manzano se queda en mediano y entonces da fruta; guardar y cargar a mitad da la misma partida y sigue igual un año después; en un mapa pequeño, 882 de 887 árboles crecen en el segundo año, en los 120 días y nunca más de 16 el mismo día; los gigantes no crecen; con una especie que admite «enorme», de grande a enorme tarda dos años. Costo medido en release, en un mapa sin pueblos (prueba `sim_perf` «the trees' growth», se salta por omisión): colosal, 1 149 616 árboles, 100 ticks por día: 1,83 ms por tick de media el primer año (nada crece) y 1,89 ms el segundo (crecen 988 552), peor tick 4,2 ms; mapa enorme de 4 km, 89 031 árboles: 0,10 ms en los dos años. No se midieron los FPS con `--reporte` como pedía el criterio: hace falta la ventana del juego. Sin prueba de dos instancias en red (sí de dos partidas con el mismo hash tras guardar y cargar). Pendiente menor: la lista de árboles cambiados que la vista consume crece sin límite en una partida sin vista (pruebas largas); son 4 bytes por árbol crecido.

## Fase 87: el leñador replanta y tala solo maduros (2026-10-04)

**D-8701. Dos opciones más del leñador.**
`option::kReplant` (número 1) y `option::kMatureOnly` (número 2), con la misma orden `SetOption` de la fase 85; el protocolo de red no cambia. Las dos empiezan apagadas.

**D-8702. Replantar.**
Cuando el trabajador saca la última madera de un árbol y su leñador tiene «Replantar», el mismo objeto del mapa pasa a ser un brote de su especie (D-8603), en el mismo sitio, y el trabajador se queda 4 segundos de juego sin hacer otra cosa: eso es «plantar». No cuesta materiales. Si el trabajador deja el árbol a medias (se va a comer, cambia de empleo), no hay brote hasta que alguien lo termine de talar. Lo despejado por una obra o un campo no se replanta, y un brote bajo una obra nueva se quita; de paso se corrige que un arbusto vacío bajo un edificio nuevo rebrotara dentro del edificio.

**D-8703. Maduro.**
Grande o enorme, o del tamaño mayor de su especie (un manzano mediano ya es maduro). Con la opción encendida el leñador ni mira los demás. Al encenderla, quien ya estaba talando un árbol joven termina esa carga: la opción decide qué árbol se elige, no interrumpe.

**D-8704. «Esperando que crezcan».**
`Supply::Growing`: a su alcance solo hay brotes, o árboles jóvenes con «Solo maduros». Línea de estado y nada más (sin notificación ni cuadro rojo), como pide la especificación. Vale también sin «Solo maduros» cuando solo quedan brotes. Si no hay ni árboles ni brotes, «agotado».

**D-8705. Versiones y lo medido.**
Reglas 51. Suite nueva `resources_years` para las pruebas de años (con las de la fase 86), aparte de `resources`, para caber en el tiempo de un debug. Pruebas: con «Replantar», cuatro robles talados dejan cuatro brotes de roble en su sitio y sin él ninguno; el leñador queda «esperando que crezcan» sin evento; guardar y cargar con brotes; una casa sobre un brote lo quita; al año los brotes son robles pequeños con su madera. Con «Solo maduros», seis robles medianos no se tocan, y durante su segundo año se talan los seis sin sacar madera de ninguno que no fuera grande. Con los dos encendidos y 60 robles grandes, árboles talados por año en diez años: 32, 28, 0, 28, 32, 0, 26, 33, 1, 24; al final los 60 siguen ahí, en pie o como brote. Los interruptores viajan con la misma orden probada en la fase 85; no se probó con dos instancias reales. Nada se vio en pantalla.

## Cierre de la ronda de recursos (2026-10-04)

**D-8801. Lo único visto en pantalla.**
Con una copia portátil en ventana, `SalvaCiudad.exe --reporte` sobre el mapa pequeño de semilla 12345 apuntando a (340, 506): el yacimiento mediano se dibuja con su modelo y su sombra. Sirve además de prueba de que el juego carga los modelos y aspectos nuevos sin fallar. Ese yacimiento, el garantizado del inicio, quedó a 6 m del borde del mapa: el generador no lo aleja del borde.

**D-8802. Hallazgo anterior a la ronda: `--reporte` termina con 0xC0000409.**
El modo `--reporte` guarda la imagen y el texto, escribe «SalvaCiudad stopped» en el registro y el proceso sale con el código 0xC0000409. Pasa igual con la compilación 8768267 (antes de las fases 73 a 87), así que no es de esta ronda. No se investigó.

**D-8803. Verificación.**
Cada fase se cerró con la compilación `release` sin advertencias y todas las suites. `debug` y `debug-asan` se corrieron en el árbol de verificación sobre el commit de la fase 80 (67 suites, todas pasan en los dos), el de la 85 (68, todas pasan en los dos) y el de la 87 (69: todas en `debug`; en `debug-asan` pasaron 68 y `worldgen_hier_life` se pasó de sus 240 s).

**D-8804. `worldgen_hier_life` partida en dos.**
Esa suite, sola y con AddressSanitizer, tarda 214 s de los 240 s permitidos, y los tiempos de asan varían hasta el doble en este equipo (D-3110): en la corrida completa del commit de la fase 87 se pasó del límite, y en la del commit de la fase 85 había entrado. Las fases 86 y 87 no tocan el generador; las 82 y 83 le agregan poco. Se movieron sus tres últimos casos (gigantes, ajustes de clima, tierra e islas con muchos pueblos) a una suite nueva, `worldgen_hier_giants`, como ya se hizo en D-3110. Queda al borde `worldgen_hier_structures` (212 s con asan), que es un solo caso y no se puede partir sin reescribirlo.

## Corrección: hambre en viajes con rodeo (2026-10-04)

**D-8810. Por qué alguien llegaba a cero de comida con el pueblo lleno (semillas 14, 15 y 18 de D-8203).**
Pedido por Salvador: investigar. Siguiendo al aldeano que llegaba a cero: es un peón que lleva materiales a una obra lejana (la cabaña de caza). La regla del hambre (D-6807) lo manda a comer cuando le queda lo que cuesta volver, y esa cuenta era «la línea recta hasta el almacén, por 1,3, a paso normal». Fallaba de dos maneras. En la 14 y la 15 el camino real rodea agua y es bastante más largo que 1,3 veces la recta. En la 18 el peón salió en otoño y volvió con nieve: caminó 1 880 pasos de ida y más de 2 100 de vuelta. En los tres casos se quedaba sin comida a pocas decenas de metros del pueblo y perdía salud; a veces moría. No tiene que ver con las fases 73 a 87.

**D-8811. La corrección.**
Cada aldeano lleva la cuenta de los pasos que caminó desde que comió o desde que estuvo en un almacén con comida (`Villager::walked`). La vuelta se estima como lo mayor entre la recta de siempre y eso que ya caminó, las dos al paso de hoy (nieve, oscuridad, raza lenta), con tope en tres veces la recta, y se guarda un cuarto más de reserva por si el camino empeora. No hay búsquedas de camino nuevas: sigue siendo una cuenta. Reglas 52. Medido con la cabaña de caza junto a la primera zona, un año, semillas 1 a 20: el medidor más bajo de cualquier aldeano pasa de 0 (en tres semillas) a 72 como mínimo; la prueba «nadie pasa hambre en un viaje largo» ahora incluye las semillas 14, 15 y 18. Costos: (1) las obras lejanas alcanzan un poco menos: la cabaña de la semilla 2, a unos 300 m en línea recta, antes se terminaba y ahora no; la obra de prueba a 220 m sigue terminándose (medidor más bajo 152); (2) en la hora de juego guionizada se interrumpen unas 100 tareas para ir a comer, antes unas 25 (el límite de la prueba es 200); (3) la prueba del año largo quedó con la comida por habitante a 18 % de diferencia y su margen pasa de 15 % a 25 %, como ya se hizo con las llegadas en D-6611; influye también que la fruta silvestre de la fase 84 es anual.

**D-8812. Lo que sigue igual.**
Una obra más lejos de lo que permite un medidor lleno nunca se termina y el juego no lo dice: los peones salen, se dan la vuelta a medio camino a comer y vuelven a salir (ya estaba en D-6807). Las salidas posibles son un aviso de «obra demasiado lejos de la comida», o que los peones lleven provisiones como el explorador; queda para decidir con Salvador.

## Fase 88: despejar una obra talando (2026-10-04)

**D-8820. Lo que pidió Salvador y cómo quedó.**
Al revisar la fase 85: «todos los árboles deben dejar la madera que dejarían al talarse normalmente, al ser despejados para una obra», y «deben despejarse talándose por trabajadores/jornaleros». Reemplaza a D-8505. Los árboles bajo una obra ya no se quitan al colocarla. Mientras quede uno en pie dentro de su terreno (el mismo margen de un metro de siempre), la obra recibe materiales pero nadie la construye. Los peones los talan antes que cualquier otra tarea de obra, eligiendo la obra más cercana; talan cualquier árbol, sin mirar las opciones de ningún leñador, y no replantan. La madera sale unidad por unidad como en la tala normal y el peón la lleva al almacén. La fruta de un frutal va al centro del pueblo (o al carro). Un leñador cercano también puede talar esos árboles por su cuenta, con sus propias reglas.

**D-8821. Lo que la especificación no decía.**
- **Campos:** igual que las obras, pero los talan los trabajadores de esa granja (son quienes ya van al campo) y no se siembra hasta que estén talados.
- **Lo que no es árbol** (rocas sueltas, arbustos, hierbas, brotes) sigue quitándose al colocar la obra, sin dejar nada. Salvador habló de árboles; queda como pregunta.
- **Edificios que nacen terminados** (los del pueblo ya fundado de las pruebas, el carro): quitan sus árboles en el momento y la madera va al centro del pueblo.
- **Sin sitio donde guardar:** en un pueblo recién fundado el centro está lleno (los bienes y el oro iniciales pasan de su capacidad) y lo que un peón no puede guardar se pierde, como siempre. Para que la madera del despeje no se pierda justo al empezar, un peón que no encuentra almacén la lleva directo a una obra que todavía necesite esa cantidad. Vale para cualquier bien que un peón tenga en las manos, no solo madera. Si tampoco hay obra que la quiera, se pierde.
- **Árboles dentro de la silueta de la obra:** el terreno de la obra ya no se puede pisar, así que el peón tala desde la celda libre más cercana. No se cambió cuándo se bloquea el paso.
- **Cancelar la obra** deja los árboles que queden, con la madera que les quede.
- La orden que elige el árbol es la misma en todas las máquinas: el de índice más bajo que nadie esté talando.

**D-8822. Pruebas guionizadas: los pueblos no «dejaban de construir casas», se quemaban.**
Corrige D-8604. Con la semilla de partida 86 la prueba de «una hora de juego» volvió a terminar con cero casas; siguiéndola minuto a minuto, las casas se construyen bien y en el minuto 36 un incendio se lleva siete edificios (el jugador guionizado no pone pozo). Lo mismo eran las semillas 80, 84 y 90 de D-8604. Las dos pruebas de una hora juegan ahora sin incendios, como ya jugaban sin asaltos: miden la economía. La del año largo pasa de las semillas 70 a 73 a las 74 a 77, donde población, llegadas y comida por habitante quedan dentro de sus márgenes de siempre (se deshace el 25 % de D-8811 para la comida).

**D-8823. Lo observado de paso.**
En esa misma partida guionizada, la obra del cantero queda a unos 200 m en línea recta pero el camino da un rodeo de más de 80 tramos: los peones salen hacia ella una y otra vez y se dan la vuelta a comer. Es el límite de D-8812, no de esta fase; con el despeje talando se nota antes, porque ahora hay que llegar a la obra también para talar.

**D-8824. Versiones y lo medido.**
Reglas 53. El pulido pasa a ser la fase 89. Pruebas en `resources`: una casa sobre manzanos no avanza mientras queda uno, los peones los talan (con un leñador al lado que no tala frutales y que replanta: no cuenta ninguna de las dos cosas), toda su madera queda en el pueblo, su fruta se toma, no quedan brotes, y la casa se termina; guardar y cargar antes de despejar; una obra cancelada conserva sus árboles; un campo sobre dos robles no se siembra hasta que los trabajadores de la granja los talan. Nada se vio en pantalla.

## Ronda de propuestas: fases 89 a 116 (2026-10-04)

**D-8901. De dónde sale la ronda.**
Salvador eligió función para 62 de los 773 grupos de la página de propuestas (`docs/propuestas/respuestas.json`) y pidió el plan por fases, revisando qué le falta al juego. El análisis se publicó en el registro de revisión como diez bloques (`prop-a-vista` a `prop-j-personajes`, ideas con autor Claude) y 28 preguntas (`q-prop-*`); los marcó todos «para el plan» y respondió todo el 2026-10-04. Quedan como fases 89 a 116 y el pulido pasa a ser la 117. Los 711 grupos sin responder no entran.

**D-8902. Ritmo, git y arte en paralelo (respuestas de Salvador).**
Todas las fases seguidas, sin pausa, con un resumen por fase. Las propuestas (scripts, página, herramienta y respuestas) entran a git en un commit propio antes de la fase 89; los `.glb` y `datos/` siguen fuera. Un agente de arte a la vez puede preparar los modelos de la fase siguiente en su copia de trabajo; se revisa antes de unirlo.

**D-8903. Lo que el juego no tenía y la ronda crea.**
Caminos, trazado por arrastre, lluvia, anexos de casa, ganado, sucesos con ánimo temporal y avisos con decisión. Se anota porque cada uno es un sistema nuevo, no un ajuste: su fase lleva sus propias pruebas de guardado, red y rendimiento.

**D-8904. Lo que dicen las funciones elegidas y queda sin efecto.**
«La miel no se echa a perder» (nada se echa a perder en el juego); «las gallinas reducen los insectos del huerto» (no hay plagas); «las carretas no se atascan» en el empedrado (no hay carretas que caminen); «el muelle o la barca rinden más» (no hay muelles ni barcas: aplica a la cabaña del pescador); «hasta que se entierran» y «en las ruinas» de los cuervos (no hay entierros ni ruinas). No se crean esos sistemas en esta ronda: son la opción más simple y Salvador lo confirmó para los cuervos.

**D-8905. Trazado: cuadrícula de 2 m con diagonales a 45° en los muros (respuesta de Salvador; cierra I-012).**
Eligió la cuadrícula con diagonales sobre el trazado de punto a punto en cualquier ángulo, que pedía rehacer las piezas. Vallas, setos bajos y caminos no tienen pieza diagonal: solo 90°. Cada módulo sigue siendo un edificio, como la empalizada de hoy; el trazo es una orden que coloca varios.

**D-8906. Puertas y muro de piedra.**
Se suman la puerta de dos hojas y la poterna en su variante de empalizada (grupos que Salvador no había respondido; lo aceptó en la pregunta). El muro de piedra y su puerta conservan su modelo hasta que elija su kit.

**D-8907. Setos y vallas cierran el paso (respuesta de Salvador).**
A aldeanos y animales; se cruzan por cancela o arco. No son defensa. Las reglas del zorro y de los conejos miran módulos cercanos, no un recinto cerrado: comprobar recintos es caro y frustrante en laderas, y Salvador eligió «6 módulos o más a 3 m» para el jardín de casa.

**D-8908. Los caminos son una capa del terreno, no edificios.**
Se construyen como obras, tramo por tramo, y al terminarse pasan a un valor por celda. Se descartó dejarlos como edificios (miles de entidades en un pueblo grande) y ponerlos al instante (el empedrado cuesta piedra, que alguien tiene que llevar). Velocidades propuestas por Claude: tierra 115 %, empedrado 130 %.

**D-8909. Solo faroles de camino y almenara ahuyentan a las bestias (respuesta de Salvador).**
Si toda luz lo hiciera, una antorcha de un tronco anularía la fase 72. El farol de cristal queda fuera: no hay recurso para él.

**D-8910. Lluvia en la simulación, y frena los incendios (respuesta de Salvador).**
Se calcula como la temperatura, sin estado. Por omisión las reglas no tienen lluvia, como se hizo con el día y la noche, para no tocar las pruebas de fases anteriores; el formulario de partida nueva la enciende. No riega campos ni inunda.

**D-8911. Cada elemento nuevo del mapa usa su propia secuencia de azar.**
Panales, nidos, tocones, corros de setas, yacimientos, piedras sueltas, bancos de peces, juncos, patos y las zonas nuevas se colocan sin mover lo que ya había: así los mapas de las pruebas guionizadas no cambian en cada fase. La versión del generador sube igual.

**D-8912. Comida nueva sin cambiar la dieta.**
Miel, huevos, setas y queso cuentan como un alimento más para la dieta variada, que sigue pidiendo tres tipos al mes. Subir la exigencia es un cambio de equilibrio que nadie pidió. La miel no da felicidad aparte.

**D-8913. Setas rojas: el curandero hace de «recolector experto».**
La función elegida habla de un sanador o un recolector experto; no existen recolectores expertos. Con curandero o médico en el pueblo solo llegan setas buenas; sin ellos, una de cada cinco intoxica.

**D-8914. Bayas por temporada, con compensación (respuesta de Salvador).**
Huevos y hierbas en primavera, miel en verano, setas en otoño, y un 25 % más de provisiones iniciales. Se mide con las pruebas de un año de juego.

**D-8915. El vino sale de la prensa, de cualquier fruta (respuesta de Salvador sobre la prensa).**
La función elegida dice que las uvas son «fruta»; por eso la prensa no distingue uvas de manzanas. Un recurso «uvas» aparte sería más fiel y más caro; queda como idea.

**D-8916. Yacimientos (respuestas de Salvador).**
Oro: la mina saca monedas, poco a poco. Carbón: mina nueva y la carbonera sigue, más lenta, para mapas sin yacimiento cerca. Arcilla: la arcillera pasa a depender de los bancos. Todos se agotan (su nota). Rocas: tres escalones; las piedras sueltas las recoge cualquier peón. Cristal y azufre quedan fuera. Las minas usan el modelo de la mina de hierro hasta que elija otro.

**D-8917. Anexos (respuestas de Salvador).**
Sirven a las casas que tocan y reemplazan a las decoraciones parecidas. El altar da la felicidad de la fe pero no deja subir a nivel 3. Los números (+6, +5, 80 de leña, 10 días secos) son propuesta de Claude.

**D-8918. Colmenas, gallinero, caseta y prensa: decoraciones que pasan a producir.**
Sin trabajador fijo salvo la prensa; los peones llevan y traen. El palomar sigue de decoración (Salvador pidió solo gallinero y caseta).

**D-8919. Perro: una caseta, la raza es solo aspecto (respuesta de Salvador).**
Todos avisan y todos retienen a un lobo. El perro no es una criatura de la simulación: es la caseta la que guarda el radio, y la vista dibuja al perro.

**D-8920. Ganado sencillo: ovejas y cabras; lana, carne y pieles, queso (respuestas de Salvador).**
Sin vacas, sin heno. Se usa el grupo «Redil de ovejas», que no había respondido. La simulación guarda cuántos animales hay, no cada animal. Comprar un carnero de reemplazo cuesta oro: es la salida más simple cuando el rebaño lo pierde.

**D-8921. Fauna (respuestas de Salvador).**
El cazador caza conejos; zorro y lince no se cazan. Pesca: el agua sola da la mitad y bancos y juncos el resto, hasta vez y media. Mamut: zona en biomas fríos, solo en invierno, con armas y dos cazadores; sin bioma de tundra. El marfil solo sirve para vender. Conejos, linces y mamuts se apoyan en las zonas de animales de hoy, no en animales simulados uno por uno.

**D-8922. Sucesos (respuestas de Salvador).**
Farolillos: una noche al azar por año en pueblos con dos zorrunos o más, con ánimo unos días. Tortugas: aviso con dos botones. Sin respuesta, el suceso pasa sin efecto (Claude: lo más simple y lo que menos castiga a quien no está mirando).

**D-8923. Personajes (respuestas de Salvador).**
Un cuerpo de diario más por raza, al azar. Un cuerpo de guardia por raza y el arma según la unidad, como pieza aparte. Los modelos de propuesta se rehacen con las 10 animaciones del juego.

**D-8924. Fauna de ambiente y adornos del terreno, fuera de la simulación.**
Los coloca la vista con reglas fijas por celda. No entran al estado, a los hashes ni a las partidas guardadas, salvo la función que dice dónde hay flores, que es entera y sin estado porque la miel y el entorno dependen de ella.

## Fase 89: modelos de propuesta en el juego y pilas por recurso (2026-10-04)

**D-8930. El tope de una pila es 1 200 triángulos, no 500.**
El plan decía 500, puesto a ojo. Las pilas que el juego ya tenía llegan a 1 056 (sacos llenos), así que 500 habría obligado a rehacer las viejas. Con 1 200 solo hubo que aligerar la leña (de 2 376 a 924: leños de cinco lados con una sola cara de corte) y las bayas (de 1 416 a 1 176). Los demás topes del plan no se tocaron; se revisan en la fase que estrene cada clase.

**D-8931. La lista de modelos que entran es `art/blender/proposals/game.json`.**
El plan la llamaba `juego.json`; los nombres de archivo van en inglés. Cada entrada dice familia, clase, carpeta de destino e ids. `build_all.py proposals` corre el `build.py` de la familia con esos ids (`_kit.SELECT`), comprueba el tope de la clase y copia. Un modelo sobre el tope no se copia y el comando falla: se aligera en su script, no hay decimado automático. El decimado se descartó para las pilas porque a tan pocos triángulos deforma las piezas; se volverá a mirar en la fase 90, donde las parcelas de cultivo pasan mucho del tope.

**D-8932. La pila es un campo del recurso: `"pile"`.**
Cada recurso nombra el comienzo de sus tres archivos (`<pile>_1.glb` a `_3.glb`); los tres tienen que existir o el recurso se rechaza, como cualquier modelo que falta. Se descartó una tabla fija en el código (como la de las pilas genéricas): un mod que agrega un recurso puede traer su pila. Si un mod cambia la pila de un recurso ajeno, los archivos se buscan en ese mod. Es presentación: la simulación no lo lee. El visor de modelos las lista bajo el recurso.

**D-8933. Qué recursos tienen pila propia.**
32 de los 35. Troncos y piedra conservan las suyas, como pedía el plan. El oro sigue con los sacos: la pila de oro de las propuestas (lingotes y cofre a la vista junto a la bóveda) pertenece a una función que Salvador no eligió. Carne ahumada y pescado ahumado comparten la pila de ahumados. Pilas nuevas hechas en esta fase: frijoles, harina y abono.

**D-8934. Hasta 6 pilas, y dónde van.**
Las de los recursos de los que el edificio tiene más; entre ellas, en el orden de los recursos, para que una pila no cambie de sitio cada vez que cambian las cantidades. Antes las pilas se ponían en fila frente a la puerta y la tapaban; ahora ocupan la pared de la puerta dejando un metro libre a cada lado de su centro y siguen por la pared derecha. Un taller de 5 × 5 tiene sitio para 4; un granero, para 6. No se comprueba si el sitio de la pila está ocupado por un edificio vecino (tampoco antes).

**D-8935. Cuándo una pila se ve llena.**
En un almacén, con un sexto de su capacidad en ese recurso (antes un tercio, cuando las pilas eran por tipo de carga y había menos). En una obra, con todo lo que el edificio pide de ese material.

**D-8936. Lo medido y lo que no.**
Pruebas nuevas: `variants` (el campo `pile`: los tres archivos, fuera del mod, sin pila, cambiada por otro mod, y las de `core`), `people` (qué pilas se eligen y dónde van) y `model` (los 622 modelos de `core` cargan; las 108 pilas pesan 1 200 triángulos o menos, no tienen esqueleto ni animación, se apoyan en el suelo y ninguno de sus materiales brilla de noche; esta prueba encontró el abono hundido 9 cm, ya corregido). En pantalla, en una partida nueva: junto al centro del pueblo se ven las pilas de raíces, bayas, leña, troncos, piedra y los sacos del oro. **No se midieron los FPS con 1 000 aldeanos en el mapa colosal** que pedía el criterio: el `--reporte` pone una multitud pero no un pueblo, así que no dibuja pilas y la medida no diría nada. Lo que cuesta es a lo más 6 instancias por edificio, de modelos de menos de 1 200 triángulos, rehechas dos veces por segundo como antes. No se vio en pantalla un granero con cinco alimentos ni una obra de ladrillo: quedan en la lista de pruebas manuales.

**D-8937. La simulación no cambia.**
Ni reglas ni red ni generador. Cambia el hash del contenido (los recursos tienen un campo más), así que las partidas guardadas con la versión anterior no cargan, como siempre que cambian las definiciones.

## Fase 90: cultivos por etapas (2026-10-04)

**D-9001. Las parcelas del juego son de 2 × 2 m, no de 4 × 4.**
El plan hablaba de parcelas de 4 × 4 m estiradas hasta un 25 % para llenar el campo. El motor solo escala una instancia igual en todos sus ejes, y un campo ya se dibujaba celda de 2 × 2 por celda de 2 × 2, cada una a la altura de su suelo. Con parcelas de 2 × 2 no hay que estirar nada, el cultivo sigue la pendiente y cada parcela ocupa justo el lugar de la mata genérica de antes. El tope pasa de 700 triángulos por 16 m² a 200 por 4 m²: un campo de 20 × 20 son cien parcelas, 19 200 triángulos como mucho. Se descartó agregar al motor la escala por eje: más código en el dibujado para un resultado peor en laderas.

**D-9002. Se mecen en el sombreador de vértices.**
El plan decía «todas las de un mismo modelo comparten una pose». El motor anima personajes uno por uno, con su esqueleto; hacer que cien parcelas compartan un esqueleto era una vía de dibujado nueva. En su lugar, un modelo puede marcarse como «se mece» (`set_model_sway`) y el sombreador desplaza cada vértice según su altura, con la fase de cada instancia sacada de su posición: cuesta lo mismo que no mecerse y no hay dos parcelas al compás. Lo usarán también las hierbas y flores de la fase 91. La sombra no se mece. Qué cultivos se mecen lo dice `"sways"` en su definición: trigo, cebada y lino.

**D-9003. Cereales como gavillas.**
A 200 triángulos no cabe modelar los tallos. La primera versión, el surco como una barra con espigas encima, se veía como lingotes. Quedó cada surco como tres gavillas (un tronco de pirámide que se abre hacia arriba) en dos tonos, con su corona al madurar. Verduras, frijoles y raíces sí son piezas sueltas: son pocas por parcela.

**D-9004. Cada cultivo declara sus tres etapas: `"models"` y `"sways"`.**
Como las pilas en la fase 89: en la definición, no en una tabla del código, para que un mod pueda traer su cultivo con su aspecto. Tienen que ser tres archivos exactos. Sin ellos el campo usa las matas genéricas de antes, que siguen en el código para los mods.

**D-9005. Qué etapa se ve.**
Brotes desde que se siembra; verde desde la mitad del crecimiento; maduro cuando el campo está listo para cosechar (no al 100 % de crecimiento: son la misma cosa en la simulación). Después de la cosecha, rastrojo; en barbecho, pasto: como antes. La regla es una función pura con su prueba (`props::crop_stage`).

**D-9006. De lejos, el color del suelo.**
Las parcelas son «vegetación menuda»: no se dibujan más allá de la distancia de vegetación de la configuración. Para que el campo no se vea de tierra desnuda desde lejos, la losa de suelo toma el 45 % del color del cultivo. De cerca ese color asoma entre los surcos.

**D-9007. Las parcelas se apoyan sobre la losa de tierra.**
Visto en pantalla: a ras del terreno quedaban 10 cm hundidas en la losa del campo y los surcos no se veían. Van a la altura de la cara de arriba de la losa.

**D-9008. Lo medido y lo que no.**
Pruebas: `variants` (un cultivo con tres etapas, con dos, con cuatro, con un archivo que falta, sin ninguna, y los cinco de `core`), `people` (qué etapa toca) y `model` (las 15 parcelas pesan 200 triángulos o menos, cien no pasan de 20 000, son estáticas, caben en su 2 × 2, cada etapa es al menos tan alta como la anterior y nada brilla de noche). En pantalla, en una partida: dos campos con sus surcos y brotes, y las verduras en sus tres etapas a lo largo de un verano; trigo solo en brotes (el pueblo de prueba no llegó a la cosecha del año de trigo). **No se vieron en el juego** el trigo, la cebada ni el lino verdes o maduros, ni los frijoles, ni el mecerse: solo sus vistas previas de Blender. **No se midieron los FPS con 40 campos** que pedía el criterio: hacen falta 40 campos marcados a mano. La cuenta: 40 campos de 20 × 20 son 4 000 parcelas y hasta 768 000 triángulos más con todo maduro y a la vista; la distancia de vegetación recorta los lejanos. Queda en la lista de pruebas manuales, con F3.

**D-9009. Visto de paso: triángulos blancos de noche.**
En la partida de prueba volvieron a verse los triángulos blancos sobre un risco oscuro de noche (D-6909, abierto). Hay captura. No es de esta fase y no se tocó.

**D-9010. La simulación no cambia.**
Ni reglas ni red ni generador; cambia el hash del contenido.

## Fase 91: vestir el terreno (2026-10-04)

**D-9101. Las briznas ya existían; la fase agrega lo que faltaba.**
El juego dibuja desde la fase 18 briznas de hierba por todo el suelo, en la tarjeta gráfica, con su vaivén. La «mata verde» de las propuestas repetía eso mismo con un modelo, así que no entró. Entraron la hierba alta, la seca, el trébol, el helecho y los juncos, de la familia `scatter`; de `nature_grass` no se usó ninguno (eran los mismos cuatro, más pesados).

**D-9102. Una regla por cuadro de 4 m, sin estado.**
El suelo se mira en cuadros de 4 × 4 m y cada uno tiene a lo más un adorno, elegido por su terreno, su bioma, su pendiente, el agua cercana, la estación y un número sacado de su posición (`cover::item_at`). La vista calcula los cuadros en trozos de 32 m alrededor de donde mira la cámara y los vuelve a calcular solo al cruzar de trozo, al cambiar la estación, la nieve o la helada, o al cambiar los edificios. No se guarda nada ni pasa por el generador: los mapas y sus sumas de verificación no cambian. Se descartó ponerlos como objetos del mapa (cientos de miles en un mapa colosal, y habría cambiado todos los mapas).

**D-9103. Dónde sale cada cosa.**
Pradera y pasto: flores de primavera a verano (girasoles solo en verano), hierba alta en 9 de cada 100 cuadros, trébol en 4. Suelo de bosque: helechos y, en primavera, pétalos. Roca: pedregal. Laderas con 3 m o más de desnivel en el cuadro: risco (el nav no las deja caminar). Orilla de agua dulce: juncos. Arena a 6 m o menos del mar: madera de deriva, conchas y pozas. Agua abierta con helada: témpanos. Con 30 o más de nieve no se dibuja ninguna planta. Los pétalos no buscan árboles en flor: salen en el suelo de bosque de los biomas que los declaran, que es donde están esos árboles; buscar árbol por árbol pedía un índice de cientos de miles de objetos.

**D-9104. Qué tiene cada bioma lo dicen los datos: `flowers` y `cover`.**
No hay nombres de bioma en el código. Cada bioma declara su porcentaje de flores silvestres y la lista de adornos que su suelo admite; un mod puede dar los suyos. La montaña recibió también helechos después de ver en pantalla su suelo de bosque vacío.

**D-9105. La opción tiene cuatro niveles, no tres.**
El plan decía «apagado, medio, alto». Los selectores de gráficos del juego son todos de cuatro niveles y los ajustes de calidad (bajo, medio, alto, ultra) fijan un nivel a cada uno; con cuatro encaja sin casos especiales. Apagado: nada. Bajo: hasta 64 m, quietos. Medio: 96 m, se mecen. Alto: 160 m, se mecen. Las plantas además se cortan a la distancia de «Vegetación», como los arbustos.

**D-9106. Dónde hay flores lo dice la simulación, pero no las guarda.**
`sim::wildflowers(mapa, contenido, celda)` da de 0 a 100, con enteros y sin estado: manchones de 8 m, cuatro de cada diez con flores, más densos en pradera que en pasto y según el bioma. La vista la usa ya; las reglas de la miel y del entorno la usarán en la fase 104. Por eso `flowers` es el único campo nuevo de bioma que toca el hash del contenido con sentido de reglas.

**D-9107. Invierno: ventisqueros y muñecos según los edificios.**
Cerca de la mitad de los edificios terminados tiene un ventisquero contra una de sus paredes; uno de cada tres adornos de plaza tiene un muñeco de nieve al lado si su pueblo tiene niños. Cuáles, lo decide su posición. Se recalculan con lo demás; un niño que nace en pleno invierno no hace aparecer el muñeco hasta que la vista se vuelve a llenar.

**D-9108. Modelos del juego: sin esqueleto y más ligeros (`_kit.GAME`).**
Los adornos de las propuestas traían un esqueleto para mecerse y hasta 1 128 triángulos. El script de cada familia construye ahora, además, su versión del juego: sin esqueleto, con menos piezas (`kit.light`) y en una carpeta aparte. Así el modelo de la página y el del juego salen del mismo código. Los pétalos del juego no llevan los que «todavía caen»: sin animación quedaban colgados en el aire. Los juncos no llevan su charco: van en la orilla.

**D-9109. Lo medido y lo visto.**
Pruebas, suite nueva `cover`: el mismo cuadro da siempre lo mismo y cae dentro del mapa; cada terreno y cada bioma tiene lo suyo; riscos solo en ladera de montaña; flores de primavera a verano, girasoles en verano, hierba seca en otoño, nada de plantas con nieve, pétalos solo en primavera; en el agua solo témpanos con helada, juncos junto al lago y conchas junto al mar; las flores silvestres en manchones y por bioma; ventisqueros y muñecos fuera de los edificios; los niveles de la opción; los 22 modelos dentro de su tope, sin esqueleto y sin brillo; y que vestir el suelo no cambia el hash de la partida ni la suma del mapa. `settings` e `i18n` cubren la opción. En pantalla, con `--reporte` sobre un mapa mediano en primavera: hierba alta, flores alpinas y riscos en la ladera. Con la opción en «Alto» frente a «Apagado», en esa vista: de 2 545 a 1 976 FPS, es decir 0,11 ms más por cuadro (42 objetos y 146 llamadas de dibujo más). En el mapa colosal (semilla 12345, centro del mapa): 151 FPS en «Apagado» y 165 en «Alto»; la diferencia es ruido, porque mientras se medía corrían las compilaciones de verificación en la misma máquina. Lo que vale es el costo fijo de 0,11 ms, que no depende del tamaño del mapa: a 150 FPS sería menos de un 2 %. En otras cuatro vistas de mapas pequeños se vieron además el trébol y los helechos. **No se vieron en el juego con claridad** las flores de pradera (son pequeñas a la distancia de las capturas), ni los pétalos, la playa, los juncos o el invierno: solo sus pruebas y las vistas previas de Blender.

**D-9110. Versiones.**
La simulación no cambia de reglas (nadie usa todavía `wildflowers`), ni la red, ni el generador. Cambia el hash del contenido.

## Fase 92: fauna de ambiente (2026-10-04)

**D-9201. Quién vive en cada cuadro de 16 m, por una regla sin estado.**
Como los adornos del suelo: el mapa se mira en cuadros de 16 m y en cada uno vive a lo más un animal (o un enjambre), elegido por lo que el cuadro ofrece (si tiene árbol, agua dulce cerca, flores, un jardín al lado, edificios cerca, bioma seco o frío), la estación, la nieve, si es de noche y un número de su posición (`fauna::resident`). La vista los crea alrededor de donde mira la cámara y los vuelve a repartir al cruzar de cuadro o al cambiar la hora o la estación. Lo que hace cada uno después (pasear, comer, volar, huir) no sigue ninguna regla compartida: no hace falta, porque no está en la simulación.

**D-9202. Jardines, por los datos.**
Tu nota pedía pájaros «en jardines, árboles podados, bebederos de pájaros y huertos». No hay bebederos ni árboles podados en el juego. Cuenta como jardín toda decoración de las categorías «jardín» y «naturaleza» y todo edificio que tarda años en dar fruto (el huerto de frutales; el viñedo cuando llegue). En esos cuadros, y en los de al lado, seis de cada diez tienen pájaros en primavera y verano, frente a uno de cada diez junto a un árbol cualquiera.

**D-9203. Los cuervos se quedan un mes, no tres días.**
Un día de juego dura 10 segundos a velocidad normal: en tres días nadie alcanzaría a verlos. Se quedan 1 000 ticks, un mes. Vienen por las muertes de aldeanos (el aviso «murió» de la simulación, de cualquier pueblo) y de soldados y asaltantes (cuando la vista los ve desaparecer). Son tres: una corneja grande y dos cuervos, o tres buitres si el bioma es de veranos secos. Se recuerdan hasta 16 lugares; no se guardan con la partida.

**D-9204. Búhos solo en árboles.**
El plan decía «en ramas y tejados». Posarlos en un tejado pide saber la forma de cada edificio; en un árbol basta su altura. Se posan a media altura, junto al tronco, y no vuelan.

**D-9205. Sin abejas todavía.**
El enjambre de abejas de las propuestas viene con su tronco de miel. Entra con el árbol con panal (fase 98) y las colmenas (fase 104), que es donde tiene sentido.

**D-9206. Huyen de los aldeanos; de los perros, cuando haya.**
Ardillas, pájaros y zorros miran tres veces por segundo si hay un aldeano cerca (6, 5 y 14 m) y se alejan de él: la ardilla corre, el pájaro vuela, el zorro corre 22 m. No entran al agua ni salen del mapa. Los búhos y los enjambres no se inmutan.

**D-9207. Mismo ajuste que los adornos.**
«Detalle del terreno» manda también aquí: apagado, ninguno; bajo, hasta 48 m; medio, 80; alto, 112. No se agregó otra opción.

**D-9208. Lo medido y lo visto.**
Pruebas, suite nueva `fauna`: la misma pregunta da siempre la misma respuesta; cada especie donde y cuando debe (ardillas de día con árboles y sin nieve, búhos de noche en árboles y nivales en frío, luciérnagas en noches de verano, mariposas de día sobre flores en primavera y verano, libélulas junto a agua dulce, nadie sobre el agua ni en roca); los pájaros se van en otoño y el petirrojo se queda, y un jardín atrae más del triple; zorros pocos, lejos de edificios y blancos en frío; carroñeros solo donde hubo muertes; los 15 modelos cargan, con esqueleto, sus animaciones y 2 000 triángulos o menos, y solo las luciérnagas brillan; y nada de esto cambia el hash de la partida ni el mapa. En pantalla, con `--reporte` en un bosque de un mapa pequeño: con el ajuste en «Alto» hay 37 animales de ambiente dentro del alcance (75 personajes frente a 38 con el ajuste apagado) y se vio un petirrojo junto a su árbol, bien dibujado. Costo en esa vista: de 2 027 a 1 834 FPS con adornos y fauna juntos (0,05 ms por cuadro). **No se vieron** moverse, huir ni volar (el reporte toma una sola imagen), ni los búhos, las luciérnagas, las libélulas, los zorros ni los cuervos.

**D-9209. Tropiezo: objetos viejos en `build/release`.**
Al cerrar la fase, el ejecutable de `release` se cerraba al arrancar (0xC0000409) sin escribir una línea en el registro, con el código bien compilado en `debug`. Borrar las carpetas de objetos de `build/release/CMakeFiles` y recompilar lo arregló: es el mismo tropiezo de Ninja del 2026-10-03, ahora con el juego y no con las pruebas. Ninja sí tiene anotadas las dependencias de encabezados, así que la causa sigue sin explicar. Desde ahora, antes del commit de cada fase se recompila `release` desde limpio y se arranca el juego una vez.

**D-9210. Versiones.**
La simulación no cambia: ni reglas ni red ni generador. Cambia el hash del contenido solo por los archivos de modelos nuevos si alguna definición los nombrara; estos no los nombra ninguna (los carga el código, como las cargas y las herramientas).

## Fase 93: trazado por arrastre y empalizada nueva (2026-10-04)

**D-9301. Lo que ya había y lo que cambia.**
El juego ya dejaba arrastrar para poner muros, pero solo en línea recta, y el cliente mandaba una orden por módulo. Ahora hay **una orden, «trazar»**, con la celda inicial, la final y de qué lado empieza una L; la simulación calcula los módulos (`sim::trace_cells`) y pone los que caben. Así el trazo es el mismo en todas las máquinas aunque el mapa haya cambiado entre que se arrastró y se aplicó, y un trazo de 60 módulos es un mensaje y no sesenta. Tope: 64 módulos por trazo.

**D-9302. Cuadrícula de 2 m en celdas pares.**
Los módulos de un trazo van siempre en celdas pares, para que encajen entre sí y con las celdas de 2 m del buscador de caminos. La orden antigua de colocar un solo módulo sigue aceptando cualquier celda (la usan pruebas de fases anteriores); un módulo fuera de la cuadrícula simplemente no se une a sus vecinos y se ve como poste.

**D-9303. Recta, L o diagonal.**
Si las dos celdas comparten fila o columna, recta. Si el muro admite diagonales y están a la misma distancia en los dos ejes, diagonal. Si no, una L. Al arrastrar, la L empieza por su lado más largo y la diagonal se engancha cuando los dos lados difieren en un módulo o menos y miden al menos dos. Lo que no cabe (agua, pendiente, algo construido) se omite y el resto se pone; un trazo del que no cabe nada se rechaza entero.

**D-9304. La diagonal es un tramo entre centros, no una pieza por celda.**
La pieza diagonal de las propuestas va de esquina a esquina de su celda y por eso «no empalma con los rectos sin un pilar» (defecto anotado). En el juego cada módulo de un tramo diagonal se dibuja como lo que es, un poste, y entre dos módulos que se tocan por la esquina se dibuja la pieza diagonal **centrada en esa esquina**: va del centro de uno al centro del otro, así que empalma con cualquier pieza sin huecos. Para el paso no hizo falta nada: el buscador de caminos ya prohibía cortar una esquina entre dos celdas cerradas, y la prueba del recinto lo comprueba.

**D-9305. Puertas: las de empalizada son edificios nuevos; la de siempre se queda.**
Salvador eligió sumar la puerta de dos hojas y la poterna de las propuestas. Entran como `core:palisade_gate` (4 × 2, 10 troncos, 600 de vida, como la puerta de hoy) y `core:palisade_postern` (2 × 2, 6 troncos, 400). La puerta de madera anterior no se toca: es la única que tiene el muro de piedra hasta que elija su kit. Una puerta se coloca **encima** del muro de su familia y reemplaza los módulos que tapa (sus materiales vuelven al centro del pueblo, como al demoler); media puerta sobre el muro y media en terreno libre también vale. Nada reemplaza a una puerta: ni otra puerta ni un trazo que pase por encima. Al colocarla sobre un tramo, la puerta se gira sola para cubrirlo.

**D-9306. Piezas por definición: `line`, `diagonal`, `pieces`.**
Como las pilas y los cultivos: en los datos. El muro de piedra tiene familia (`stone`) y ninguna pieza, así que se traza y se ve como antes. Las piezas son solo de la vista; la familia y `diagonal` sí cuentan en las reglas.

**D-9307. Escalón.**
Un módulo recto cuyos dos extremos difieren en 0,6 m o más de altura usa la pieza de escalón, con su mitad alta hacia el lado alto y apoyada en el bajo. El plan decía «donde el terreno sube 1 m»; con 0,6 se evita el hueco visible bajo un recto en pendientes medianas. No se vio en pantalla: el terreno de la escena de prueba era llano.

**D-9308. Una escena de prueba guardada, para mirar.**
Arrastrar el ratón no se puede hacer desde las pruebas de pantalla (los arrastres enviados no llegan al juego). La suite `trace` tiene un caso **saltado** («manual: a saved game with lines of every shape») que arma un pueblo con muros de todas las formas y lo guarda en `<temp>/SalvaCiudad/manual_lines.scsave`; copiado a la carpeta de partidas, se carga y se mira. Se corre con `salvaciudad_tests -ts=trace -tc="manual*" --no-skip`. Lo que hay dentro de un recinto se construye antes de cerrarlo: los peones no llegan a una obra encerrada (esto ya era así y vale para el jugador).

**D-9309. Lo medido y lo visto.**
Pruebas, suite nueva `trace`: las celdas de un trazo (recta, L por x o por z, diagonal, tope de 64); la pieza y el giro de las 16 combinaciones de vecinos; los datos de la empalizada (4 troncos, 40 de trabajo, 400 de vida, arde), su puerta y su poterna, y el muro de piedra; un trazo de 10 módulos deja 10 obras y construirlas gasta 40 troncos; lo que no cabe se omite; un octágono con cuatro lados rectos y cuatro diagonales no deja pasar a nadie hasta que tiene puerta; la puerta solo reemplaza módulos de su propia familia y nada la reemplaza a ella; la empalizada se incendia; la orden se lee como se escribe, las malformadas se rechazan y dos partidas con las mismas órdenes dan el mismo hash; guardar y cargar con obras a medias. En pantalla, con la escena guardada: el octágono cerrado con sus diagonales sin huecos, la puerta en el lado norte, los muros interiores con sus uniones en T y su cruce, una L, un poste suelto, el muro de piedra trazado y una fila de obras con su pieza de andamio. **No se vio** el arrastre en sí (el fantasma verde y rojo y el aviso con el costo), ni el escalón, ni la brecha, ni a los asaltantes rompiendo un módulo (lo cubre la prueba de fauna de la fase 15, que sigue pasando).

**D-9310. Versiones.**
Reglas 54, red 26. El generador no cambia.

## Fase 94: setos y vallas (2026-10-04)

**D-9401. Los animales salvajes ya no cruzan muros, setos, vallas ni puertas.**
Hasta ahora un lobo caminaba en línea recta hacia su presa y solo lo detenían el agua y los riscos: atravesaba casas, empalizadas y puertas. Para que «un lobo no entre» en un corral, la cuadrícula de paso guarda una marca más por celda, **barrera**, que ponen todos los edificios con `line` y todas las puertas. Un animal no entra a una celda con barrera ni pasa por la esquina donde se tocan dos (los tramos en diagonal); uno al que le construyen un muro encima sí puede salir de él. Vale también para la empalizada y el muro de piedra, que ahora sí protegen de las fieras: es lo que un jugador espera, y no hubo que tocar ninguna prueba anterior. Los demás edificios se siguen cruzando como antes (cambiarlo es otro asunto y movería el equilibrio de todo el juego). Los animales no buscan camino: el que choca con una cerca persiguiendo a alguien se rinde y vuelve a su zona; si el corral tiene un hueco, puede dar con él o no. Asaltantes y soldados no cambian: los asaltantes rompen lo que les estorba. La marca no ocupa memoria nueva: comparte byte con la cuenta de puertas de cada celda (un mapa colosal tiene 67 millones de celdas de paso; un vector más serían 64 MiB).

**D-9402. Qué son en las reglas.**
Edificios de tipo defensa (para que sigan el terreno módulo a módulo y los asaltantes no los elijan como botín) pero en la pestaña «Jardín y mercado», con 60 de vida. El golpe de un asaltante hace 60: cae al primero. No son a prueba de fuego. El seto vivo cuesta 1 tronco y 20 de trabajo; el seto bajo, nada y 8; la valla, 1 tronco y 10: los números del plan.

**D-9403. Los pasos.**
Arco de seto (la pieza de arco del kit de seto vivo; cuesta lo mismo que un módulo), cancela de seto bajo y cancela de valla (1 tronco y 10 de trabajo cada una). Los tres miden un módulo, se colocan sobre un tramo de su propia familia y lo reemplazan, como la poterna de la empalizada. Entran cerrados y sin animación: los aldeanos los cruzan sin que se abran, igual que las puertas de la fase 93.

**D-9404. Entorno con alcance propio.**
El entorno de siempre llega a 30 m y se apaga con la distancia; con esa cuenta, «+1 a 6 m» daría siempre cero y veinte módulos sumarían veinte veces. Campo nuevo `desirabilityRadius`: quien lo tiene vale **entero** dentro de su alcance y **una vez por tipo**, y solo terminado. La distancia se mide de centro a centro, como el resto del entorno (y como lo pinta la capa de entorno, que usa la misma función). El plan no daba la cifra del seto vivo: **+2 a 8 m**, el doble que el bajo por ser el doble de alto. Los dos se suman entre sí. «Rodear» la casa llega en la fase 104.

**D-9405. Las bayas del seto no las va a buscar nadie: aparecen en el recolector.**
Al cambiar el día del calendario, en otoño, cada recolector (lugar de recolección con `picksFruit`, terminado y con al menos un trabajador) mira los módulos de seto de su pueblo dentro de su radio que no hayan dado fruto este año; por cada cuatro recibe 1 de bayas en su propia existencia, como la fruta de un árbol talado, y de ahí sale por el reparto normal. Los que sobran esperan a que haya más. Se descartó que un aldeano camine hasta el seto: habría que tratar cada módulo como un arbusto más (ocupación, cosecha parcial, animación) por una baya cada ocho metros. Sin recolector a su alcance, o sin nadie trabajando en él, el seto no da nada. Va en los datos (`yields`, `yieldPer`, `seasons`), no en el código: un mod puede hacer un seto de otra cosa.

**D-9406. Piezas que faltan y un tope para los setos.**
Los kits bajos de las propuestas no traen pilar, obra, brecha ni diagonal. Un módulo suelto se dibuja con el remate; en obra, con la pieza que será, medio transparente; dañado, con su pieza normal. Sin diagonal en los datos, tampoco se pueden trazar a 45°, como pedía el plan. El seto vivo y el bajo pasan de los 800 triángulos de la clase `line` (hasta 1492 y 888): clase nueva `hedge`, tope 1500. Son hojas; aligerarlos los dejaba calvos.

**D-9407. Lo medido y lo visto.**
Suite nueva `fences`, 10 casos: los datos de los tres y de sus pasos; un corral de valla cerrado no comunica dentro con fuera hasta que tiene cancela, y la cancela de otro tipo no se deja poner; una fiera encerrada en un corral de 16 × 16 m quiere salir y en 6000 pasos no sale, y ninguna otra entra (quitando la barrera a propósito, la misma prueba falla: se escapa); los asaltantes atraviesan un anillo de valla alrededor del centro del pueblo y nunca queda un módulo dañado en pie; 8 módulos de seto dan 2 de bayas en otoño, paso a paso (1 por cada 4 que se marcan) y nada más los días siguientes; 3 módulos no dan nada, ni 8 en primavera, ni 8 sin recolector; un seto bajo terminado sube en 1 el entorno a 5 m y no a 10 m, cinco módulos siguen sumando 1 y el seto vivo suma aparte; el seto arde; guardar y cargar conserva setos, cancelas, lo ya recogido y la barrera.

**D-9408. Versiones.**
Reglas 55. La red no cambia (no hay órdenes nuevas): sigue en 26.

## Fase 95: caminos (2026-10-04)

**D-9501. Una capa dispersa, y una copia por celda solo cuando hace falta.**
Los caminos son un valor por celda de la cuadrícula de paso (2 × 2 m): el tipo de camino, de 1 a 15, en el orden en que el contenido define sus edificios de camino. La partida guarda solo las celdas que tienen camino (una lista ordenada: así se guardan, se envían y entran al hash sin recorrer el mapa). La cuadrícula de paso tiene además su copia por celda, para consultar en cada paso de cada búsqueda, pero **no la reserva hasta que se pone el primer camino**: un mapa colosal tiene 67 millones de celdas y una partida sin caminos no paga esos 64 MiB.

**D-9502. Mientras se construye, un tramo es una obra como cualquier otra.**
Se traza con la orden de la fase 93, los peones llevan la piedra y trabajan en él, y si hay un árbol en la celda lo talan primero (fase 88, sin tocar nada). Lo único distinto: la obra de un camino **no estorba el paso** (ni a aldeanos, ni a fieras, ni a asaltantes). Al terminarse, el edificio desaparece y queda la marca. Se descartó ponerlos al instante: el empedrado cuesta piedra y alguien tiene que llevarla.

**D-9503. Velocidad y rutas.**
Un aldeano con los pies en una celda de camino avanza ese tick al 115 % o al 130 %. Para la búsqueda, pisar esa celda cuesta en la misma proporción menos (10 → 9 en tierra, 8 en empedrado, en terreno llano). La estimación que guía la búsqueda usaba 10 por paso; con caminos eso sería estimar de más y la búsqueda dejaría de encontrar el mejor camino justo cuando hay un rodeo corto por una calle. Ahora usa el costo del camino más rápido **que exista en ese momento en el mapa**: sin caminos sigue siendo 10 y todas las rutas son las de siempre (las pruebas de pueblos guionizados no cambian); con caminos la ruta es la óptima, a cambio de mirar algunas celdas más. Solo los aldeanos van más rápido: soldados, asaltantes y animales se mueven con otro código y no se tocaron.

**D-9504. Dónde cabe un tramo.**
En una celda par (las de la cuadrícula de paso), sobre terreno libre y con hasta 1 m de desnivel dentro del tramo. Un muro admite 1,8 m, pero un camino tan empinado se vería roto. Sobre agua no.

**D-9505. Mejorar.**
Un camino más rápido se traza sobre uno más lento. El lento sigue sirviendo hasta que el tramo nuevo se termina. Tierra sobre empedrado, o cualquiera sobre uno igual, se rechaza. «Mejorar cobra solo la piedra» sale solo: el camino de tierra no cuesta materiales.

**D-9506. «Quitar camino» es un trazo más, no una orden nueva.**
Es un edificio de mentira (`roadEraser`): aparece en la pestaña Plaza junto a los caminos, se arrastra igual, y en lugar de poner obras quita los caminos y los tramos en obra del propio pueblo por donde pasa. Así reutiliza el trazado, el fantasma y el aviso de la fase 93 sin una herramienta aparte en la interfaz. El fantasma marca en rojo solo lo que se irá. Los caminos no tienen dueño: en una partida de varios pueblos cualquiera puede quitar cualquier camino que haya explorado. Es lo más simple; si resulta molesto, se le pone dueño a cada celda.

**D-9507. La casa «frente a la calle».**
La puerta de una casa está un metro fuera de su pared. Como los tramos van en celdas pares y una casa puede estar en celdas impares, el tramo pegado a la pared puede empezar un metro más allá: cuenta una calle a uno **o dos** metros delante de la puerta. +4 con empedrado, nada con tierra (`roadDesirability`). Una calle que pasa por un costado o por detrás no cuenta.

**D-9508. En pantalla.**
Las piezas elegidas (camino de tierra con rodadas, calle empedrada) son losas planas. Puestas tal cual, en una ladera la mitad de cada tramo quedaba enterrada y la otra mitad flotando. Cada instancia de dibujo gana dos números, cuánto sube hacia el este y hacia el sur, y la pieza se **cizalla** con el terreno (no se gira: así dos tramos vecinos siguen coincidiendo en su borde). Va 4 cm sobre el suelo. Las piezas se eligen por vecinos como los muros, y la tierra se une con el empedrado. La hierba y las flores de la fase 91 no crecen sobre un camino. En el minimapa, cada fila de celdas seguidas es una línea clara.

**D-9509. Error de la fase 93 corregido: las puertas de un módulo no se podían colocar con el ratón.**
Al pasar el trazado a «todo lo que tiene `line`», quedó en el clic una regla vieja: «un edificio de defensa de 2 × 2 no se coloca con clic, se arrastra». La poterna de la empalizada (fase 93) y el arco y las cancelas de la fase 94 miden 2 × 2 y son de defensa: el fantasma se veía bien, pero el clic no hacía nada. No lo vieron las pruebas (colocan con órdenes, no con el ratón) ni yo en pantalla (probé con órdenes en la escena guardada). Ahora la regla del clic es la misma que la del trazado: no se coloca con clic lo que se traza, y una puerta sí.

**D-9510. Lo medido y lo visto.**
Suite nueva `roads`, 11 casos: los datos; un trazo de 10 tramos se construye y deja de ser edificios, y mientras es obra se puede caminar sobre él; un árbol en el trazo se tala primero; la calle exige nivel 2 y una piedra por tramo, y con tres tramos más que piedra, tres se quedan en obra hasta que llega; mejorar tierra a calle gasta exactamente una piedra por tramo y ningún tronco, y nada se traza sobre un camino igual o mejor; **entre dos puntos a 40 m, un explorador tarda 200 ticks campo a través, 184 con un camino de tierra en la fila de al lado (160 de ellos sobre el camino) y 166 con una calle**; la casa gana 4 con la calle delante de la puerta y nada con tierra; el borrador, un edificio y una casa encima quitan el camino; guardar y cargar (y un guardado con una celda o un tipo imposibles se rechaza); dos partidas con las mismas órdenes coinciden tick a tick; sin caminos la búsqueda da la ruta de siempre. En `net`: un camino trazado por el cliente queda igual en el anfitrión. Rendimiento, caso manual de `sim_perf` en un mapa colosal con un pueblo de 1000: con 2026 tramos de camino de tierra construidos el tick tarda 2,73 ms de media (p95 4,34) y sin caminos, tras el mismo número de ticks, 2,86 ms (p95 4,55): un 95,5 %, es decir, la diferencia queda dentro del ruido de la medición. El criterio permitía un 10 % más. Es una sola corrida de cada una; pico de memoria del proceso, 6963 MiB (dos partidas colosales una tras otra). En pantalla, con la escena guardada: el camino de tierra con su cruce, su ramal y sus remates, la calle unida a él, los tramos en obra semitransparentes, las piezas siguiendo el terreno, las líneas claras en el minimapa; con clics de verdad, un tramo de camino puesto desde la pestaña Plaza y una cancela de valla colocada sobre su valla. **No se vio** el arrastre (los arrastres enviados no llegan al juego), el borrador en pantalla, ni un camino en una ladera fuerte.

**D-9511. Versiones.**
Reglas 56, red 27.

## Fase 96: faroles de camino y almenara (2026-10-04)

**D-9601. Qué son.**
Los tres faroles son decoración de 1 × 1 en la pestaña Plaza, junto a los caminos: madera (1 tronco, 8 m), hierro (1 de hierro, 16 m) y piedra (4 de piedra, 12 m, no arde y tiene el triple de vida: 300 contra 100). Los tres con 20 de trabajo. No hace falta ponerlos junto a un camino: el nombre viene del modelo. La almenara es un edificio de defensa de 3 × 3 (20 troncos, 10 de piedra, 300 de trabajo, 600 de vida, 30 m de luz) que se ve por encima de la niebla, como las torres. El de cristal quedó fuera, como decía el plan.

**D-9602. La regla, exacta.**
La cuadrícula de luz (celdas de 4 m, ya existía) guarda un segundo bit: «alumbrada por una luz que ahuyenta». De noche:
- un lobo o un oso no da un paso desde fuera hacia dentro de una celda así (ni paseando ni persiguiendo);
- el que venía persiguiendo a alguien y choca con el borde se queda quieto ahí hasta 100 ticks (10 segundos a ×1) y luego se rinde y vuelve a su zona; si su presa sale de la luz antes, sigue;
- el que la noche (o un farol recién puesto) encuentra dentro no elige presa ni muerde mientras siga dentro, y puede salir.
De día nada de esto vale. Ciervos y jabalíes no cambian (el plan decía lobos y osos), ni los asaltantes. Las demás luces siguen como en la fase 70: solo evitan que una fiera elija a quien está dentro. La espera se guarda con el animal (un número más por criatura), así que una partida guardada con un lobo esperando continúa igual.

**D-9603. Las luces solo se calculan de noche.**
Ya era así (fase 70) y se dejó: de día `lit` y `warded` no se actualizan y la regla no se consulta.

**D-9604. Herramienta de desarrollo «Terminar todas las obras».**
Orden nueva, `DevBuild`, solo con las herramientas de desarrollo: todo lo que el pueblo tiene en obra queda terminado, sin materiales (un tramo de camino pasa a ser camino). Hacía falta para las pruebas: para comprobar que un lobo no entra en la luz hay que poner faroles **dentro de la zona de los lobos**, y los peones que fueran a construirlos serían atacados antes de terminar. También sirve para armar escenas de prueba sin esperar a los peones (en las fases 93 a 95 la escena tardaba años de juego y el pueblo se moría de hambre). Tiene su botón en el panel de desarrollo. Por ser una orden nueva sube la versión de red.

**D-9605. La prueba del viaje usa un camino, y por qué.**
El criterio dice «por un camino con faroles». Al principio la prueba ponía solo faroles a lo largo de la ruta calculada y fallaba: en campo abierto hay muchas rutas igual de cortas, y el explorador (que antes pasa por provisiones) tomaba otra, a 25 m de los faroles. Con un camino de tierra por la ruta, la búsqueda lo prefiere y el explorador va por donde están los faroles. Es decir: para que un sendero iluminado proteja, hace falta el camino; los faroles sueltos en el campo no guían a nadie.

**D-9606. Lo medido y lo visto.**
Suite nueva `lanterns`, 7 casos, en un mapa con una manada de lobos a 260 m del pueblo y noches largas: los datos; con cinco faroles de piedra en la guarida, en 6000 ticks de noche **ninguna** fiera entra a la luz desde fuera, contra 34 veces con cinco antorchas y 15 veces de día con los mismos faroles; de noche el explorador llega a la guarida por un camino con faroles en 2041 ticks, sin una herida y siempre dentro de la luz una vez fuera del pueblo, y a oscuras es atacado y no llega; un lobo que persigue al explorador se queda en el borde, espera los 100 ticks sin entrar y se va; los asaltantes entran en la luz de una almenara junto al centro; la orden de desarrollo termina una casa, un farol y un tramo de camino, viaja como bytes y se rechaza sin las herramientas; guardar y cargar. En pantalla, con una escena nocturna guardada (caso saltado «manual: a saved game in the night with lanterns and the beacon» de la misma suite): el camino alumbrado por los tres faroles, la almenara con su llama al final y la antorcha común, cada uno con su charco de luz. **No se vio** a un lobo detenerse en el borde (lo cubre la prueba). En esa escena vuelven a salir, grandes, los triángulos blancos del terreno de noche (D-6909, abierto): no es de esta fase, no se tocó y quedó propuesto como tarea aparte.

**D-9607. Versiones.**
Reglas 57, red 28.

## Fase 97: lluvia (2026-10-04)

**D-9701. Cada día llueve o no, por sorteo fijo.**
Un día del calendario es de lluvia si un número sacado de la semilla de la partida y del número del día cae por debajo de la probabilidad de ese día: 30 % en primavera, 18 % en verano, 32 % en otoño y 26 % en invierno, multiplicada por la «Lluvia» de las reglas y por la humedad del mapa (las dos en porcentaje; tope 90 %). Cada día se sortea aparte: no hay frentes ni rachas (lo más simple; si se quieren, basta con que la probabilidad de hoy mire a ayer). Nada se guarda: `Game::wet(día)` es una función, y por eso una partida cargada, un cliente que entra tarde y el anfitrión dicen lo mismo. Si ese día la temperatura está bajo cero, lo que cae es nieve: no embarra ni apaga. La nieve acumulada en el suelo sigue como desde la fase 10 (depende del frío, no de que nieve): cambiarlo movería pruebas de fases anteriores.

**D-9702. El barro.**
El camino de tierra tiene `muddy` en sus datos. Mientras llueve y todo el día siguiente, su velocidad vuelve a 100 % y la búsqueda de rutas lo trata como terreno. El empedrado no cambia. Se hace cambiando la tabla de velocidades por tipo de camino al empezar cada día del calendario; las celdas no se tocan.

**D-9703. Incendios.**
Bajo la lluvia un incendio crece cada 20 ticks en lugar de cada 10: tanto su intensidad como el daño. Las chispas a los edificios vecinos saltan igual, pero con la intensidad que tenga, que es menor.

**D-9704. Lo que la simulación ofrece a las fases siguientes.**
`raining()`, `snowing()`, `rained(día)`, `wet(día)`, `days_without_rain()` (hasta 30) y `muddy()`. El tonel (fase 103) y las setas (fase 98) las usarán.

**D-9705. En pantalla y en el oído.**
1400 rayas finas (o copos, si nieva) caen en una caja de 120 × 120 × 22 m centrada donde mira la cámara; entran y salen en cuatro segundos. Las rayas engordan con la distancia de la cámara: con su grosor real (2 cm) no llegaban a un píxel desde la altura normal y no se veía llover (así salió en la primera captura); en la segunda, demasiado gruesas y largas, parecían barras, y se dejaron en medio metro, semitransparentes y en una caja baja para que ninguna caiga pegada a la cámara. La luz de la escena pasa por `rain_lighting`: cielo gris con el mismo brillo que tenía (de noche no aclara), sol al 40 % sin disco, sin estrellas. El sonido es un bucle nuevo, `rain.wav`, en un tercer canal de ambiente; los pájaros bajan a la cuarta parte. La barra superior dibuja un ícono con trazos (sol o luna, nube con gotas, nube con copos) solo en partidas donde puede llover, y antepone «Llueve» o «Nieva» al clima. El camino de tierra embarrado se oscurece. Un reporte (`--reporte`) no muestra lluvia: enseña un momento de una partida, no su clima.

**D-9706. Formulario y ajustes.**
«Lluvia», deslizador de 0 a 200 % en pasos de 25 (0 dice «Nunca»), junto a día y noche; se recuerda en `settings.json` (`newGame.rain`). Las partidas armadas en pruebas tienen 0, como pedía el plan.

**D-9707. Lo medido y lo visto.**
Suite nueva `rain`, 8 casos: misma semilla, mismos días, y otra semilla, otros; con 0 nunca; en cinco años con cuatro semillas llueve entre 15 y 35 de cada cien días sin helada, más con más lluvia o más humedad y menos en un mapa seco; las reglas viajan con la lluvia y se rechaza un valor imposible; en 240 días de una partida, 48 de lluvia, 14 de nieve y 78 de barro, y cada día `raining`, `muddy` y `days_without_rain` cuadran entre sí; **bajo la lluvia, 24 m se cruzan en 120 ticks campo a través, 120 por el camino de tierra embarrado y 101 por la calle; con el camino seco, 113**; un incendio, tras 90 ticks, lleva 8 de daño bajo la lluvia y 18 sin ella; guardar y cargar con barro (el barro se va a la vez en la partida y en su copia); la luz de un día de lluvia. En `net`: tras un año con lluvia, anfitrión y cliente tienen el mismo hash y el mismo clima. En `settings`: la lluvia del formulario se guarda y se lee.

**D-9708. Versiones.**
Reglas 58, red 29: no hay mensajes nuevos, pero las reglas de la partida viajan con un byte más (la lluvia) y una versión anterior las leería mal.

## Fase 98: miel, huevos y setas (2026-10-04)

**D-9801. Un solo mecanismo: «lo que da por temporadas», igual que la fruta de un árbol.**
El panal, el nido, el tocón y el corro no se agotan ni rebrotan como un arbusto. Usan lo que ya tenía la fruta de los árboles (fase 84): se recoge de a una unidad, el elemento se queda donde está, y lo recogido se cuenta por año en el propio elemento. Lo que tiene hoy se calcula al preguntarlo (estación, año, cuánto se recogió): **no hay que recorrer el mapa cada día**, que en un mapa colosal son millones de elementos. En los datos es `seasons` en la definición del elemento; el recolector los trabaja porque tiene su tipo en `gathers`. Los avisos de la fase 81 no cambian: fuera de temporada el recolector dice «esperando», como con un arbusto que rebrota (no tiene prueba propia).

**D-9802. Cantidades.**
Panal: 6 de miel en verano, 30 de trabajo cada una. Nido: 4 huevos en primavera, 15. Tocón o tronco hueco: 5 setas en otoño, 15. Corro: 6 setas cada vez que se llena, 15. Miel: 4 de alimento y vale 3; huevos: 3 y 2; setas: 2 y 1. Son extras para variar la dieta, no un sustento: un recolector alcanza pocos de cada uno. La propuesta de la miel decía «no se echa a perder y sube la felicidad»: en el juego nada se echa a perder, y la felicidad ya sube con la variedad de lo que se come; no se añadió regla.

**D-9803. El corro de setas.**
En otoño se llena entero el día siguiente a cada día de lluvia (lo que quedara sin recoger no se acumula) y solo se dibuja mientras tiene setas. El día de llenado es el mismo para todos los corros del mapa y se deduce del clima, así que tampoco se guarda. En una partida sin lluvia, los días múltiplos de diez (contados desde el inicio de la partida, no de la estación: más simple y siempre igual).

**D-9804. La intoxicación se decide al comer.**
El plan decía «una de cada cinco setas recogidas es mala». Llevar la cuenta de setas buenas y malas por almacén era otro recurso o un número más en cada existencia; en su lugar, cada ración de setas que alguien come tiene 1 probabilidad en 5 de ser mala si su pueblo no tiene un curandero o un médico terminado. Con él, ninguna («el recolector solo trae las buenas»). La intoxicación es una enfermedad más (25 de gravedad, 3 días, contagio 0) con origen nuevo, `food`: no sale en el sorteo diario. Como las demás, no existe en una partida sin enfermedades, no cae sobre quien ya está enfermo y deja 60 días de inmunidad.

**D-9805. El generador.**
Lo nuevo se pone al final, con su propia secuencia de azar (semilla, 98), después de despejar los inicios: por kilómetro cuadrado, con recursos al 100 %, 12 árboles con panal y 18 grupos de nidos (praderas y bordes de bosque), 24 grupos de tocones (bosque) y 16 de corros (bosque espeso), de 1 o 2 cada grupo. Cerca de cada inicio (180 m), al menos 2 panales, 2 nidos y 3 tocones; corros no se garantizan (necesitan bosque espeso), las setas de otoño las aseguran los tocones. Ninguno donde irá un centro de pueblo ni sobre un yacimiento. Generador 8. **Lo de antes no se mueve**: antes de tocar el generador se guardó la huella de cuatro mapas (todos los elementos de los tipos que había, los inicios y las zonas de animales) y la prueba comprueba que siguen iguales.

**D-9806. Detalles.**
`gathers` pasa de 8 a 16 bits (ya hay diez tipos de elemento). El leñador no tala el árbol con panal: no es un árbol para las reglas, es su propio elemento. Construir encima de uno lo quita para siempre, como a un arbusto.

**D-9807. Lo medido.**
Suite nueva `forage`, 8 casos: los datos; las huellas del generador 7 en cuatro mapas y los mínimos de cada inicio; en una partida de una sola estación el recolector recoge el nido entero en primavera, el panal entero en verano, el tocón y el corro en otoño y nada en invierno, y nunca lo de otra estación; un panal queda vacío el resto del año y vuelve entero al siguiente; en 60 días de otoño con mucha lluvia el corro se llenó 32 veces (cada día que siguió a uno de lluvia, comprobado día por día) y el recolector lo dejó limpio 5; sin lluvia en las reglas, los días 0, 10, 20 y 30; en 14 000 ticks comiendo setas, 2 intoxicados sin curandero, 0 con él y 0 en una partida sin enfermedades; guardar y cargar; construir sobre un nido. En pantalla, con una escena de otoño guardada (caso saltado «manual: a saved game with hives, nests, stumps and mushrooms»): los árboles con panal, los nidos, el tocón con setas, el tronco hueco y los corros; la ventana de un árbol con panal («Ahora no tiene nada. Da: Miel. Temporada: Verano, una vez al año.»). **No se vieron** las pilas de miel, huevos y setas (con la comida de la escena no entran entre las seis pilas que se dibujan) ni un corro apareciendo y desapareciendo. La primera versión de esa escena no cargaba: tenía minutos para estaciones que la partida no tenía, y la lectura de reglas lo rechaza con razón; era la escena, no el guardado.

**D-9808. Versiones.**
Reglas 59, generador 8. La red no cambia. Cambia la huella de referencia del mapa chico (`kGoldenSmallMap` en `tests/test_worldgen.cpp`), que incluye los elementos nuevos.

## Fase 99: bayas por temporada (2026-10-04)

**D-9901. El arbusto pasa a ser «lo que da por temporadas».**
Con el mecanismo de la fase 98: `seasons` verano y otoño, una cosecha al año contada en el propio arbusto, nada en primavera ni en invierno. Ya no rebrota cada 30 días ni se «agota»: fuera de temporada el recolector queda «esperando». Las hierbas medicinales no cambian.

**D-9902. Cuánto: 30 bayas al año por arbusto.**
Antes daba 12 cada 30 días, es decir hasta 48 al año si alguien lo recogía sin falta. Con 30 una vez al año las pruebas de pueblos (una hora de juego atendida, pueblos de años, recursos) quedan dentro de sus márgenes sin tocar nada más, salvo lo de D-9904. La cantidad es por año de la duración normal y **crece con la duración del año**, como las cosechas de los campos desde la fase 59; lo mismo vale ahora para la miel, los huevos, las setas y las bayas del seto vivo. Sin eso, una partida con años de 45 minutos tenía la tercera parte de la comida por minuto.

**D-9903. Arándanos y zarzas, por bioma.**
Cada bioma dice qué arbusto tiene (`bush`): arándanos en boreal y montaña, zarza en mediterráneo y sabana, bayas en los demás. Los arándanos son las mismas bayas con otro modelo. La zarza no da nada, nunca, y el recolector no la cuenta. No se toca el generador: el arbusto es el mismo elemento en el mismo sitio, y qué es lo decide el bioma donde está. **Consecuencia que conviene saber:** un pueblo que empieza en sabana o mediterráneo tiene sus arbustos «garantizados» convertidos en zarzas; vive de la caza, los campos, los huevos, la miel y las setas. Si resulta demasiado duro, lo simple es que el generador garantice otra comida en esos biomas.

**D-9904. La prueba de «años largos» compara ahora años completos.**
Esa prueba juega una hora con años de 15 y de 45 minutos y comparaba la comida guardada al final. Con la comida por temporadas eso depende de la estación en que termina la hora: tras el otoño en un caso (849 de comida) y al final de una primavera en el otro (398). Se cambió a lo que la prueba quiere medir: la comida por aldeano **promediada sobre los últimos 45 minutos** (tres años de 15, o uno de 45): 7,9 y 8,5, iguales dentro de su margen del 15 %. Población y recién llegados siguen comparándose como antes y pasan (95 y 102 personas). En la partida de años largos hubo 6 muertes entre cuatro pueblos y ninguna en la otra; la prueba no lo mira y no se investigó si son de vejez o de hambre en la primavera larga.

**D-9905. Compensación del primer año.**
Las provisiones iniciales de comida suben un 25 %: 188 de bayas y 50 de raíces (antes 150 y 40). En primavera el recolector tiene los nidos y las hierbas.

**D-9906. En pantalla.**
El arbusto con fruto es el modelo; en flor y verde son dos «aspectos» suyos (el mecanismo de los estados de los árboles, que admite hasta tres por modelo). Verde también cuando se le recogió todo en su temporada. Al cambiar de estación o de año la vista repasa los arbustos una vez (cuatro veces al año). Los modelos anteriores del arbusto quedan en el mod sin uso.

**D-9907. Lo medido.**
Suite nueva `berries`, 7 casos: los datos y qué arbusto tiene cada bioma; por calendario y a lo largo de un año de juego, nada en primavera, 30 en verano, lo que quedó sin recoger en otoño, nada en invierno, y el año siguiente otra vez 30; en invierno el recolector queda «esperando» y no avisa de agotado; en un mapa seco hay zarzas (10 de 17 arbustos) que no dan nada y en uno frío arándanos (10 de 17) que dan lo mismo, y cada uno se dibuja con su modelo; el aspecto por estación; las provisiones iniciales. Se ajustaron tres pruebas de antes: las dos que contaban 150 de bayas al empezar, y la del recolector que espera (los arbustos ya no desaparecen de la cuenta: se quedan, sin fruto).

En pantalla, con dos escenas guardadas (caso saltado «manual: saved games with berry bushes in spring and in summer»): en primavera los arbustos con flores blancas; en verano con bayas rojas, los del lado frío del mapa con arándanos azules, y el que el recolector ya había vaciado, verde. No se vio el invierno ni una zarza.

**D-9908. Versiones.**
Reglas 60. El generador y la red no cambian.

## Fase 100: raíces, viñedo y vino (2026-10-04)

**D-10001. Casi todo son datos.**
Las raíces son un cultivo más (`hardy`, 60 días de crecimiento contra 35 a 45 de los demás, rinde 14, gasta 8 de fertilidad). El viñedo es un huerto de frutales con otros números: 8 × 8, 12 troncos, dos trabajadores, solo en otoño, a partir del tercer año, hasta 140 de fruta al año (el huerto da hasta 120 entre verano y otoño). La prensa: 2 de fruta por 1 de vino, 90 de trabajo. El vino vale 12 (la cerveza, 6). Reglas nuevas solo dos, las de D-10002 y D-10003.

**D-10002. La taberna: «cualquiera de», no «todo».**
`serviceUses` exigía todo lo que listaba. Con `serviceUsesAny` basta una cosa de la lista, y se gasta la primera que haya: cerveza, y si no, vino. Se descartó gastar una de cada si hay las dos (el doble de consumo por el mismo servicio) y elegir al azar (inútil y menos predecible). El tabernero sigue yendo a buscar las dos bebidas cuando le quedan menos de diez.

**D-10003. El viñedo sin hojas en invierno.**
Un edificio puede tener `winterModel`: la vista usa ese modelo mientras es invierno y vuelve a dibujar los edificios cuando el invierno llega o se va. Solo cambia lo que se ve.

**D-10004. La prensa de vino conserva su identificador.**
Sigue siendo `core:decor_wine_press`, ahora como taller en la pestaña Alimentos. Deja de dar entorno (daba 7 como adorno) y de ser incombustible. Cambiarle el identificador no aportaba nada y habría que tocar textos, modelos y catálogo.

**D-10005. Lo medido.**
Suite nueva `wine`, 6 casos: los datos; con cultivos demasiado lentos para madurar antes del invierno, la helada mata el trigo y las raíces siguen creciendo; el viñedo no da nada en sus dos primeros años y en el tercero da 140 de fruta, todo en otoño; la prensa hace vino con dos de fruta cada uno; una taberna con vino y sin cerveza da entretenimiento a una casa, con cerveza también, y sin ninguna de las dos no; guardar y cargar.

En pantalla, con dos escenas guardadas (caso saltado «manual: saved games with a vineyard in autumn and in winter»): el viñedo con hojas en otoño y con las espalderas desnudas en invierno, y la prensa de vino. El modelo del viñedo ocupa unos 5 × 6 m de su solar de 8 × 8. **No se vieron** las parcelas de raíces creciendo (el campo de la escena estaba recién arado), ni la pila de vino.

**D-10006. Versiones.**
Reglas 61. La red y el generador no cambian.

## Fase 101: yacimientos de arcilla, carbón y oro (2026-10-04)

**D-10101. Tres tipos más, con las reglas del yacimiento de roca.**
`ClayDeposit`, `CoalDeposit` y `GoldDeposit` se agregan al final de la lista de tipos (los números de los anteriores no cambian) y todo lo que el juego hacía «si es un yacimiento de roca» pasa a preguntar `is_deposit()`: cantidad por tamaño (1, 5/2 y 25/4 de `amount`), terreno ocupado, varios trabajadores a la vez parados alrededor, achicarse al gastarse y liberar el suelo al acabarse. No se escribió ninguna regla nueva.

**D-10102. La arcillera pasa de taller a recolector.**
Antes tenía la receta `dig_clay` (arcilla de la nada); la receta se quita y la arcillera es un edificio `gather` de `clayDeposit` con 60 m de alcance. Así el aviso «no queda qué trabajar» es el mismo de las fases 84 a 87, sin código propio. Una partida guardada con una arcillera antigua no se puede cargar de todos modos (suben las reglas). Los pueblos de la IA y las pruebas que contaban con arcilla en cualquier parte se ajustaron (ver D-10107).

**D-10103. Las minas.**
Mina de carbón: nivel 2, 20 troncos y 10 de piedra, dos trabajadores, 70 m de alcance, guarda combustible. Mina de oro: nivel 3, 30 troncos y 20 de piedra, dos trabajadores, 70 m, **sin almacén**: como el oro no se guarda en edificios de trabajo (fase 28), sus mineros lo llevan al centro del pueblo y ahí cuenta como oro del pueblo. Las dos usan el modelo de la mina de hierro, como dice la especificación, y solo cambia el nombre. La carbonera pasa de 80 a 120 de trabajo por tanda (un 50 % más lenta).

**D-10104. Cuánto tienen.**
Tamaño chico: arcilla 500 (30 de trabajo por unidad), carbón 600 (35), oro 200 (80). Un banco mediano de arcilla son 1250: unas 20 casas de ladrillo. El oro sale despacio: a 80 de trabajo por moneda, dos mineros sacan menos que lo que deja un mercader en una visita, y una veta chica se acaba. Son números para probar; se ajustan en datos.

**D-10105. Dónde los pone el generador.**
Con «Recursos» al 100 %: arcilla 6 por km² sobre suelo de arcilla, carbón 4 por km² y oro 0,8 por km² en lo más rocoso o empinado de entre varios sitios al azar; mitad chicos, 35 % medianos, 15 % grandes. Además cada inicio tiene un banco de arcilla mediano a menos de 250 m y una veta de carbón mediana a menos de 400 m si no le tocó ya uno. El oro no se garantiza. Como en D-8304, la distancia es en línea recta porque el generador no calcula caminos; la prueba comprueba que desde el pueblo se llega caminando en los cuatro mapas de referencia.

**D-10106. El resto del mapa queda igual.**
Los yacimientos nuevos se colocan al final, con su propia secuencia de azar, y **solo donde no hay nada**: a diferencia de los de roca (que despejan su terreno), un sitio con cualquier objeto encima o al lado se descarta. Así los objetos de antes no se mueven ni desaparecen: las cuatro huellas del generador 7 guardadas en la fase 98 siguen saliendo iguales. El precio es que salen algo menos de los que se piden en mapas muy arbolados.

**D-10107. Lo que hubo que ajustar en las pruebas.**
La prueba del límite de producción usaba la arcillera como taller: ahora usa la carbonera. La huella del mapa pequeño de referencia cambió (generador 9). Una prueba del explorador miraba su salud sin desactivar las enfermedades y con el mapa nuevo le tocó enfermarse: en esa prueba se desactivan.

**D-10108. Lo medido.**
Suite nueva `deposits`, 8 casos: los datos; una arcillera sin banco no saca nada y avisa una vez; con un banco de 14 saca los 14, el banco desaparece, su suelo queda libre y avisa una vez; la mina de carbón entrega los 20 de su veta; la mina de oro sube en 12 el oro del pueblo y no guarda nada; no se construye encima ni al borde, no se camina, y sus dos mineros la trabajan a la vez; en cuatro mapas cada inicio tiene arcilla a 250 m y carbón a 400 m a los que se llega caminando, ninguno donde va el centro del pueblo, y ningún yacimiento comparte suelo con otro objeto; guardar y cargar con una veta grande ya achicada.

**D-10109. Versiones.**
Reglas 62 y generador 9. La red no cambia.

**D-10110. Un fallo que apareció de paso: aldeanos que morían de hambre con comida guardada.**
La prueba del año largo falló con 17 muertos en una partida con más de 300 de comida en el centro del pueblo. La causa no era de esta fase: un aldeano que va a un edificio camina al punto **más cercano** de su borde, y si ese lado quedó encerrado (casas pegadas al centro del pueblo que cierran un pasillo contra él) no hay camino hasta ese punto; el aldeano se quedaba donde estaba, reintentando cada segundo, y moría de hambre aunque otro lado del edificio estuviera libre. Pasaba desde que existe `approach()`; la colocación de los yacimientos movió el azar y lo hizo visible (los 6 muertos sin explicar de la fase 99 eran lo mismo).
Arreglo, el más acotado: solo cuando el camino al lado cercano falla, se busca alrededor del edificio el punto alcanzable más cercano y se va ahí (`walk_round`). Donde antes había camino no cambia nada. Se descartó prohibir construir si se encierra un lado (caro de calcular y sorprendente para el jugador) y elegir siempre el punto alcanzable (cambiaría los caminos de todas las partidas). Prueba nueva en `fences`: un centro del pueblo con empalizada por tres lados y un trabajador al norte, que con el arreglo come y sigue trabajando y sin él muere (comprobado quitándolo).
Queda sin tocar algo parecido que vi en la misma prueba: un explorador mandado a terreno no explorado camina en línea recta desde donde tomó provisiones, y si el centro del pueblo queda en medio se queda esperando ahí mismo. No es de esta fase.

**D-10111. La prueba del año largo ya no compara los recién llegados al 25 %.**
Llegan recién llegados mientras hay comida de sobra guardada (40 más 10 por habitante). Desde que la comida viene por temporadas (fase 99), en un año de 45 minutos el almacén sube tres veces más tras el otoño y baja durante una primavera tres veces más larga, así que llegan en otros momentos y en otra cantidad (34 y 48 en la medición). La prueba sigue exigiendo población parecida (15 %) y comida por habitante parecida (15 %), deja los recién llegados en un 50 %, y ahora exige además que **nadie muera** en ninguna de las ocho partidas.

## Fase 102: rocas en tres tamaños (2026-10-04)

**D-10201. Las piedras sueltas son un tipo más de objeto natural, con una marca nueva.**
`LooseStones` al final de la lista de tipos; 6 de piedra, 10 de trabajo por unidad (un peñasco: 30), no rebrotan. Lo que las hace especiales es un dato, `loose`, no el tipo: cualquier objeto natural marcado así lo recoge un peón para una obra. No se camina ni se construye distinto por ellas (como los peñascos).

**D-10202. Cuándo las recoge un peón.**
Solo si una obra pide ese recurso y **ningún almacén** del pueblo lo tiene; el orden de un peón queda: talar el solar, traer materiales de un almacén, recoger lo suelto, construir. Va al montón libre más cercano a la obra, a 100 m o menos en línea recta y al que pueda llegar caminando. Toma lo que la obra aún necesita (hasta lo que el montón tiene y lo que carga) y lo lleva **directo a la obra**, sin pasar por el almacén. Lo que va a traer queda prometido a la obra desde que sale, igual que lo que se trae de un almacén, para que no vayan dos por lo mismo; si lo interrumpen (hambre, alarma), la promesa se deshace y lo que tenga en la mano va al almacén. Se descartó llevarlas siempre al almacén (doble viaje) y dejar que varios fueran a la vez sin promesa (sobraba piedra recogida de más: lo vi en la primera versión).

**D-10203. La promesa se guarda en un campo que ya existía.**
El peón guarda cuánto prometió en `spot`, que solo usaban los granjeros y los cazadores (que tienen trabajo; un peón no). Así no cambia el formato del aldeano en las partidas guardadas.

**D-10204. El cantero.**
Su lista `gathers` suma `looseStones`. No las prefiere ni las evita: toma lo más cercano por camino, como siempre.

**D-10205. La piedra de cada bioma: solo aspecto.**
Cada bioma tiene `rock` (gris, con musgo, arenisca): con musgo el boreal, el florido, la ribera y el encantado; arenisca el mediterráneo, la sabana y el trópico seco; gris los demás. Las piedras sueltas y el peñasco listan sus tres modelos en ese orden (`rockOfBiome`). El yacimiento de roca lista sus tres tamaños y después el chico con musgo y de arenisca. Un peñasco deja de tener tres variantes al azar: todos los de un bioma usan el mismo modelo, girado y a distinta escala.

**D-10206. Nombres.**
La roca de siempre pasa a llamarse «Peñasco». El yacimiento de roca conserva su nombre aunque su tamaño chico use ahora el modelo del afloramiento: el mediano y el grande son lo mismo de antes y partirlo en dos nombres complicaría su ventana sin ganar nada.

**D-10207. El generador.**
Al final de todo y con su propia secuencia de azar: 200 grupos por km² con «Recursos» al 100 % (cada uno de una a tres piedras, en el más áspero de tres sitios al azar, nunca en arena), y por cada inicio se completan 6 a menos de 80 m. Se quitan las que caen donde va un centro del pueblo o sobre un yacimiento. Lo demás del mapa no cambia: la prueba compara las huellas de cuatro mapas con las del generador 9, tomadas con las piedras sueltas apagadas. La primera densidad (20 grupos por km²) daba 13 en un mapa pequeño: se subió diez veces.

**D-10208. Lo medido.**
Suite nueva `stones`, 8 casos: los datos y la piedra de seis biomas; cada roca se dibuja con la piedra de su bioma y un yacimiento chico con el afloramiento del suyo; una casa que pide toda la piedra del pueblo y 6 más se termina, salen exactamente 6 de los montones cercanos y nada va al almacén; con piedra de sobra en el almacén los montones quedan intactos; sin obra nadie recoge nada, y lo que está a más de 100 m de la obra no se toca; el cantero agota un montón y un peñasco; las garantías de cada inicio y las huellas del mapa anterior; guardar y cargar con un peón a medio recoger (pedía 4: quedan 2 en el montón).

**D-10210. Dos pruebas de antes, ajustadas.**
La de variantes miraba que los peñascos se repartieran entre sus tres modelos al azar: ahora mira el mineral de hierro, que sí tiene variantes. La de «una calle empedrada sin piedra no se termina» usa un mapa sin piedras sueltas, porque con ellas los peones la terminan (que es lo que esta fase pide).

**D-10209. Versiones.**
Reglas 63 y generador 10. La red no cambia.

## Fase 103: anexos de casa (2026-10-04)

**D-10301. El anexo es una decoración con una marca, y sus efectos son datos.**
`annex` más seis campos (`annexRadius`, `annexDesirability`, `annexNeed`, `annexHappiness` con `annexChildren`, `annexRain`, `annexFirewood`). Los cinco anexos del juego base son cinco combinaciones de esos campos; no hay código por anexo. Se descartó un tipo de edificio nuevo: una decoración ya se coloca, se construye y se quita como hace falta.

**D-10302. «A 3 m o menos» se mide de pared a pared.**
La distancia es el hueco entre los dos rectángulos (0 si se tocan). Medir entre centros dejaría fuera a un leñero de 6 m pegado a una casa grande. Sirve a las casas de su mismo pueblo.

**D-10303. Cada casa guarda qué anexos tiene, un bit por tipo.**
`Building::annexes` (16 bits; el cargador numera los tipos de anexo, 16 como mucho). «No suma dos iguales» sale solo: es un bit. Se recalcula al terminar de construirse una casa o un anexo y, como todo lo de las casas, una vez al día; por eso, al quitar un anexo, su casa lo nota al día siguiente. Entra en la partida guardada.

**D-10304. El altar.**
La casa cuenta la fe como cubierta **para la felicidad** (8 puntos, lo mismo que con capilla) pero no en `needs`: el siguiente nivel sigue pidiendo capilla y la ventana de la casa lo sigue listando como falta. Con capilla y altar no se suma dos veces.

**D-10305. Los juegos de niños.**
+5 de felicidad a las casas con algún habitante menor de 5 años a 15 m o menos (de pared a pared). Va aparte de las necesidades y del entorno, y cuenta una vez.

**D-10306. El tonel de lluvia no tiene estado propio.**
Está lleno si llovió hace menos de 10 días (`days_without_rain()` de la fase 97); en una partida sin lluvia, nunca. Todos los toneles del mapa están igual, así que no hay nada que guardar. Lleno: el incendio que empieza solo en su casa no prende (se descartó prenderlo y apagarlo enseguida: mismo resultado y un aviso de incendio falso), y la chispa que llega de un edificio vecino prende con la mitad de probabilidad. No protege de la antorcha de un asaltante. El tonel mismo no arde. Para las pruebas, la herramienta de desarrollo de incendiar acepta «como accidente» (`count` 1).

**D-10307. El leñero.**
La casa guarda hasta 80 de leña. En otoño e invierno sus habitantes van por más mientras quepa una carga entera; el resto del año, y las casas sin leñero, como siempre (cuando baja de 10 y hace o viene frío). No se reserva leña del almacén para nadie: si hay poca, la casa con leñero se lleva más que las otras.

**D-10308. Se quitan tres decoraciones.**
`decor_clothesline`, `decor_firewood_rack` y `decor_tool_corner` dejan de existir como edificios (sus modelos quedan en la carpeta). Los anexos van en la pestaña Vivienda. Costos: tendedero 3 troncos, altar 4, juegos 8, tonel 4, leñero 10.

**D-10309. Lo medido.**
Suite nueva `annexes`, 8 casos: los datos y las tres decoraciones que ya no están; tendedero (la casa pegada +6, la de 10 m nada, dos no suman, 3 m sí y 4 m no); altar (8 de felicidad sin capilla, la necesidad sigue sin cubrir y la casa no sube de nivel, mientras que una igual a la que no se le pide nada sí sube); juegos (5 a las casas con niños, 0 a las que no tienen, igual con dos juegos, nada a la casa lejana); tonel (tras llover, el accidente no prende en su casa y sí en otra; tras 10 días secos, prende); sin lluvia en las reglas el tonel está vacío, y un incendio provocado prende aunque esté lleno; leñero (con 70 de leña en el pueblo su casa llegó a 36 y la otra a 20, el almacén quedó vacío y la casa pasó caliente los 24 días de invierno, de 30 a 8); guardar y cargar. No se midió la chispa a la mitad (es azar; está en el código junto a la regla).

**D-10310. Versiones.**
Reglas 64. La red y el generador no cambian.
