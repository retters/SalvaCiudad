# SalvaCiudad

Juego 3D de construcción y supervivencia de pueblos medievales con multijugador de 1 a 12 jugadores. Motor propio en C++20 sobre SDL3. El diseño completo está en [ESPECIFICACION_SalvaCiudad.md](ESPECIFICACION_SalvaCiudad.md) y las decisiones en [docs/DECISIONES.md](docs/DECISIONES.md).

**Estado:** fase 6 de 21 (mapa procedural). "Un jugador" abre la pantalla de partida nueva: semilla, tamaño (hasta 4 km de lado), ríos y lagos, bosques, recursos, relieve y posiciones de inicio. El mapa se genera en segundo plano y se puede recorrer con la cámara; todavía no hay pueblo (fase 8). La simulación es determinista ([docs/DETERMINISMO.md](docs/DETERMINISMO.md)) y los modelos salen de scripts de Blender ([docs/ARTE.md](docs/ARTE.md)). La "Escena de prueba 3D" sigue disponible.

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

Los modelos de `data/models` se generan con Blender desde los scripts de `art/blender`. Ver [docs/ARTE.md](docs/ARTE.md). Compilar el juego no requiere Blender.

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
- [ ] En Configuración > Pantalla, activar y desactivar varias veces la sincronización vertical: el juego no se cierra.
- [ ] **Tu opinión:** ¿te gustan los colores del suelo y del agua, el ancho de los ríos y la cantidad de bosque?

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
