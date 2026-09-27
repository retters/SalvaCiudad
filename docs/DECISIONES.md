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

**D-1802. Animales con modelo propio.**
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
