# SalvaCiudad

Juego 3D de construcción y supervivencia de pueblos medievales con multijugador de 1 a 12 jugadores. Motor propio en C++20 sobre SDL3. El diseño completo está en [ESPECIFICACION_SalvaCiudad.md](ESPECIFICACION_SalvaCiudad.md) y las decisiones en [docs/DECISIONES.md](docs/DECISIONES.md).

**Estado:** fase 1 de 21 (base del proyecto). Por ahora el juego abre una ventana que se pinta de un color, cambia de modo de pantalla y guarda su configuración.

## Compilar en Windows

Se necesita Visual Studio 2022 con las herramientas de C++ (MSVC x64). CMake y Ninja vienen con Visual Studio. Desde una consola "x64 Native Tools Command Prompt for VS 2022", **siempre la misma** para configurar y compilar:

```
cmake --preset release
cmake --build --preset release
ctest --preset release
```

- El ejecutable queda en `build\release\bin\SalvaCiudad.exe`, con la carpeta `data\` al lado.
- Presets de Windows: `debug`, `release` y `debug-asan` (con AddressSanitizer).
- Presets de Linux y macOS (sin probar todavía): `unix-debug`, `unix-release` y `unix-debug-asan`. Hacen falta GCC 13 o Clang 17, CMake 3.25, Ninja y las bibliotecas de desarrollo que SDL3 pide para X11 o Wayland.

## Dónde guarda sus datos

- Normalmente en `%APPDATA%\Salva\SalvaCiudad\`: `settings.json`, `logs\`, `saves\` y `mods\`.
- **Modo portable:** si existe un archivo `portable.txt` junto al ejecutable, todo se guarda en `userdata\`, al lado del ejecutable.
- Un `settings.json` dañado se renombra a `settings.json.bad-<fecha>` (nunca se borra) y el juego arranca con los valores por omisión.

## Controles provisionales (fase 1)

| Tecla | Acción |
|---|---|
| F11 | Cambia en ciclo: ventana, ventana sin bordes, pantalla completa |
| Alt+Enter | Alterna entre ventana y el último modo de pantalla completa |

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

## Licencia

Código bajo licencia MIT (ver [LICENSE](LICENSE)). Las bibliotecas de terceros conservan las suyas; ver [third_party/README.md](third_party/README.md).
