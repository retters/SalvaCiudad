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
