# SALVA'S PROSPERIA

Juego 3D de construcción y supervivencia de pueblos medievales con multijugador de 1 a 12 jugadores. Motor propio en C++20 sobre SDL3. El diseño completo está en [ESPECIFICACION_SalvasProsperia.md](ESPECIFICACION_SalvasProsperia.md) y las decisiones en [docs/DECISIONES.md](docs/DECISIONES.md).

**Estado:** en desarrollo, fase 116 de 117; falta el pulido y la entrega. Se juega de principio a fin: fundar el pueblo, recolectar, cultivar, producir, comerciar y defenderse, con estaciones, clima, día y noche, enfermedades, incendios, fauna, asaltantes, ejército y nueve razas de fantasía. Hay partidas de un jugador y multijugador cooperativo o versus, con espectadores. No hay todavía un ejecutable para descargar: hay que compilarlo.

El contenido (recursos, edificios, árboles, biomas, razas y sucesos) es un mod, `core`, y se pueden agregar mods con datos, modelos, textos y reglas en Lua; ver [docs/CREAR_MODS.md](docs/CREAR_MODS.md).

Requisito para jugar: una tarjeta gráfica compatible con Direct3D 12 (ver D-201).

## Compilar en Windows

Se necesita Visual Studio 2022 con las herramientas de C++ (MSVC x64). CMake y Ninja vienen con Visual Studio. Desde una consola "x64 Native Tools Command Prompt for VS 2022", **siempre la misma** para configurar y compilar:

```
cmake --preset release
cmake --build --preset release
ctest --preset release
```

- El ejecutable queda en `build\release\bin\SalvasProsperia.exe`, con la carpeta `data\` al lado.
- Presets de Windows: `debug`, `release` y `debug-asan` (con AddressSanitizer).
- Los sombreadores se compilan con el `dxc.exe` del Windows SDK, que viene con Visual Studio.
- Presets de Linux y macOS: `unix-debug`, `unix-release` y `unix-debug-asan`. Todavía no compilan, porque falta preparar los sombreadores para esas plataformas (D-201).

## Modelos

Los modelos de `data/mods/core/models` se generan con Blender desde los scripts de `art/blender`. Ver [docs/ARTE.md](docs/ARTE.md). Compilar el juego no requiere Blender.

El visor de modelos, `build\release\bin\SalvasProsperiaModelos.exe`, es una herramienta aparte para revisar los modelos por categoría con todas sus variantes, ver cuánto cuesta dibujarlos y encontrar los que sobran o faltan (ver [docs/ARTE.md](docs/ARTE.md#visor-de-modelos)).

## Dónde guarda sus datos

- Normalmente en `%APPDATA%\Salva\SalvasProsperia\`: `settings.json`, `logs\`, `saves\` y `mods\`.
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
4. Se guarda en `%TEMP%\SalvasProsperia\reportes\<fecha_hora>\`:
   - `captura.png`: la pantalla con los trazos;
   - `captura_limpia.png`: la misma pantalla sin trazos;
   - `reporte.json`: la semilla y las opciones del mapa, la cámara, lo que hay bajo el cursor y las casillas que cubren los trazos, con un resumen.

   Se conservan los últimos 30 reportes.
5. En el chat dile a Claude qué quieres de ese lugar.

`SalvasProsperia.exe --reporte <carpeta>` genera ese mismo mapa con el generador actual, sin niebla y con la estación del reporte, pone la cámara igual y guarda `despues_<fecha_hora>.png`, junto con un `.txt` que dice qué cambió desde el reporte (versión del generador, mods, compilación, tamaño de la ventana). Muestra el mapa generado, no la partida: no aparecen los edificios ni los árboles talados. No guarda la configuración ni partidas.

## Mapas

Qué genera cada generador de mapas, cómo se llama cada cosa y qué opción la controla: [docs/GENERADORES.md](docs/GENERADORES.md).

## Idiomas

Español, español de México (solo cambia el formato de números) e inglés. Para agregar otro idioma sin tocar el código, ver [docs/AGREGAR_IDIOMA.md](docs/AGREGAR_IDIOMA.md).

## Multijugador y seguridad

El multijugador está pensado para jugar **con gente de confianza**, en red local o por una VPN privada. Cómo funciona: [docs/RED.md](docs/RED.md).

- El tráfico no va cifrado y la partida no tiene contraseña: quien alcance el puerto del anfitrión (47800, y el 47799 por UDP para que lo encuentren en la red local) puede pedir entrar.
- El código de red no ha pasado una auditoría de seguridad frente a un participante malintencionado. No abras esos puertos a internet.
- Los mods no viajan por la red: cada jugador instala los suyos. Sus reglas en Lua corren aisladas (sin archivos, sin sistema y con límites de instrucciones y memoria; ver [docs/CREAR_MODS.md](docs/CREAR_MODS.md)), pero ese aislamiento tampoco está auditado: instala solo mods de quien confíes.

Si encuentras un fallo de seguridad, repórtalo en privado desde la pestaña Security del repositorio en GitHub, no en un issue público.

## Documentación

- [ESPECIFICACION_SalvasProsperia.md](ESPECIFICACION_SalvasProsperia.md): el diseño completo y el plan por fases.
- [docs/DECISIONES.md](docs/DECISIONES.md): las decisiones que la especificación no cubre.
- [docs/VERIFICACION_MANUAL.md](docs/VERIFICACION_MANUAL.md): lo que conviene probar a mano, por fase.
- [docs/RED.md](docs/RED.md), [docs/DETERMINISMO.md](docs/DETERMINISMO.md) y [docs/RENDIMIENTO.md](docs/RENDIMIENTO.md): el multijugador, la simulación determinista y los tiempos medidos.
- [docs/ARTE.md](docs/ARTE.md) y [docs/ARBOLES.md](docs/ARBOLES.md): cómo se generan los modelos y los sonidos.
- [docs/revision](docs/revision/LEEME.md) y [docs/propuestas](docs/propuestas/LEEME.md): las páginas con las que el autor revisa el trabajo y elige modelos nuevos.

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
