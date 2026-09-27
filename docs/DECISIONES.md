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
