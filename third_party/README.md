# Bibliotecas de terceros

Todas se vendorizan sin modificar, con su licencia, y se compilan con sus propias opciones.

| Biblioteca | Versión | Licencia | Origen | SHA-256 del archivo descargado |
|---|---|---|---|---|
| SDL3 | 3.4.16 | zlib (`SDL3/LICENSE.txt`) | https://github.com/libsdl-org/SDL/releases/download/release-3.4.16/SDL3-3.4.16.tar.gz | `7322236cd12090c3eb40b9728be4d49c76f66ad17d04369584d4ecad5cf77c68` |
| yyjson | 0.13.0 | MIT (`yyjson/LICENSE`) | https://github.com/ibireme/yyjson/archive/refs/tags/0.13.0.tar.gz | `34e0f62a2bc11ab20d601e8ca1cc2b2079503aa45119a19133d89d19b94a0fae` |
| stb_truetype | 1.26 (commit `2c980bb`) | Dominio público o MIT, a elección (`stb/LICENSE`) | https://github.com/nothings/stb | `ecd30b05e0dd4fea3a13c26810dd9e1992dc379049482c393d5a19e6b5090aab` (`stb_truetype.h`) |
| stb_image | 2.30 (commit `2c980bb`) | Dominio público o MIT, a elección (`stb/LICENSE`) | https://github.com/nothings/stb | `594c2fe35d49488b4382dbfaec8f98366defca819d916ac95becf3e75f4200b3` (`stb_image.h`) |
| cgltf | 1.15 | MIT (`cgltf/LICENSE`) | https://github.com/jkuhlmann/cgltf/archive/refs/tags/v1.15.tar.gz | `84e352092e5cd6aab7f66de62ddb66beb5e6f18d412ca9d12950d7a55bfef25a` |
| Dear ImGui | 1.92.9b | MIT (`imgui/LICENSE.txt`) | https://github.com/ocornut/imgui/archive/refs/tags/v1.92.9b.tar.gz | `21d8a0a565e85dce943e375db00812c2f3f0ab21f3f0f7964e364a63422d7f99` |
| doctest | 2.5.3 | MIT (`doctest/LICENSE.txt`) | https://github.com/doctest/doctest/archive/refs/tags/v2.5.3.tar.gz | `174ebc4e769928959614789c5b4e9c3d0a0f81a62bb608756b127bfebfb21331` |
| Lua | 5.4.7 | MIT (`lua/LICENSE`) | https://www.lua.org/ftp/lua-5.4.7.tar.gz | `9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30` |

Notas:

- **SDL3:** se quitaron las carpetas `test`, `examples`, `VisualC`, `VisualC-GDK` y `Xcode`, que no se compilan. Para actualizarla, reemplazar la carpeta completa y volver a quitarlas.
- **yyjson:** solo `yyjson.c`, `yyjson.h` y la licencia.
- **stb_truetype:** solo `stb_truetype.h` y la licencia; `stb_truetype.c` es nuestra unidad de compilación de la implementación.
- **stb_image:** solo `stb_image.h`; `stb_image.c` la compila limitada a PNG y JPEG, sin acceso a archivos.
- **cgltf:** solo `cgltf.h` y la licencia; `cgltf.c` es nuestra unidad de compilación.
- **Dear ImGui:** el núcleo (`imgui*.cpp/h`, `imconfig.h`, `imstb_*.h`) y los backends `imgui_impl_sdl3` e `imgui_impl_sdlgpu3`. Solo para el panel de estadísticas de desarrollo.
- **doctest:** solo `doctest.h` y la licencia. Solo se usa en las pruebas.
- **Lua:** los archivos de `src/` sin `lua.c` ni `luac.c`, y la licencia (copiada del final de `lua.h`). Se compilan solo el núcleo y las bibliotecas que abre el sandbox; `luai_makeseed` se fija en 0 para que las tablas se comporten igual en todas las máquinas.

## Tipografías (en `data/fonts/`)

Licencia SIL Open Font License 1.1; cada una va con su `*-OFL.txt`. Se descargaron de https://github.com/google/fonts (commit `23e54b5`).

| Fuente | Archivo | SHA-256 |
|---|---|---|
| Cinzel | `logo/Cinzel.ttf` (fuente variable; se usa su instancia por omisión) | `f4d83d34d1f6c741193e4acf4b3dff9531e5a67b6aa65228d00a7db72a4e0f34` |
| Alegreya Sans | `ui/AlegreyaSans-Regular.ttf` | `8fab634196007afca839f1e5a6fb300976daff55d8528b590ef032f01b14ea10` |
| Alegreya Sans | `ui/AlegreyaSans-Bold.ttf` | `a3055a1893759bdbd7504bb22abc583769e7974c49353176eac0b03792c9fb8e` |
