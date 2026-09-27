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
