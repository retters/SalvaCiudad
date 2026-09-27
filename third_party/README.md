# Bibliotecas de terceros

Todas se vendorizan sin modificar, con su licencia, y se compilan con sus propias opciones.

| Biblioteca | Versión | Licencia | Origen | SHA-256 del archivo descargado |
|---|---|---|---|---|
| SDL3 | 3.4.16 | zlib (`SDL3/LICENSE.txt`) | https://github.com/libsdl-org/SDL/releases/download/release-3.4.16/SDL3-3.4.16.tar.gz | `7322236cd12090c3eb40b9728be4d49c76f66ad17d04369584d4ecad5cf77c68` |
| yyjson | 0.13.0 | MIT (`yyjson/LICENSE`) | https://github.com/ibireme/yyjson/archive/refs/tags/0.13.0.tar.gz | `34e0f62a2bc11ab20d601e8ca1cc2b2079503aa45119a19133d89d19b94a0fae` |
| stb_truetype | 1.26 (commit `2c980bb`) | Dominio público o MIT, a elección (`stb/LICENSE`) | https://github.com/nothings/stb | `ecd30b05e0dd4fea3a13c26810dd9e1992dc379049482c393d5a19e6b5090aab` (`stb_truetype.h`) |
| doctest | 2.5.3 | MIT (`doctest/LICENSE.txt`) | https://github.com/doctest/doctest/archive/refs/tags/v2.5.3.tar.gz | `174ebc4e769928959614789c5b4e9c3d0a0f81a62bb608756b127bfebfb21331` |

Notas:

- **SDL3:** se quitaron las carpetas `test`, `examples`, `VisualC`, `VisualC-GDK` y `Xcode`, que no se compilan. Para actualizarla, reemplazar la carpeta completa y volver a quitarlas.
- **yyjson:** solo `yyjson.c`, `yyjson.h` y la licencia.
- **stb_truetype:** solo `stb_truetype.h` y la licencia; `stb_truetype.c` es nuestra unidad de compilación de la implementación.
- **doctest:** solo `doctest.h` y la licencia. Solo se usa en las pruebas.

## Tipografías (en `data/fonts/`)

Licencia SIL Open Font License 1.1; cada una va con su `*-OFL.txt`. Se descargaron de https://github.com/google/fonts (commit `23e54b5`).

| Fuente | Archivo | SHA-256 |
|---|---|---|
| Cinzel | `logo/Cinzel.ttf` (fuente variable; se usa su instancia por omisión) | `f4d83d34d1f6c741193e4acf4b3dff9531e5a67b6aa65228d00a7db72a4e0f34` |
| Alegreya Sans | `ui/AlegreyaSans-Regular.ttf` | `8fab634196007afca839f1e5a6fb300976daff55d8528b590ef032f01b14ea10` |
| Alegreya Sans | `ui/AlegreyaSans-Bold.ttf` | `a3055a1893759bdbd7504bb22abc583769e7974c49353176eac0b03792c9fb8e` |
