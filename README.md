# SalvaCiudad

Juego 3D de construcción y supervivencia de pueblos medievales con multijugador de 1 a 12 jugadores. Motor propio en C++20 sobre SDL3. El diseño completo está en [ESPECIFICACION_SalvaCiudad.md](ESPECIFICACION_SalvaCiudad.md) y las decisiones en [docs/DECISIONES.md](docs/DECISIONES.md).

**Estado:** fase 2 de 21 (idiomas, texto e interfaz base). El juego abre el menú principal y la pantalla de Configuración completa, en español o inglés. Las opciones de partida todavía muestran "Próximamente".

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
| Esc | Cierra un diálogo o vuelve desde Configuración |

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

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
