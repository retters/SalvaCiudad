# Bibliotecas de terceros

Todas se vendorizan sin modificar, con su licencia, y se compilan con sus propias opciones.

| Biblioteca | Versión | Licencia | Origen | SHA-256 del archivo descargado |
|---|---|---|---|---|
| SDL3 | 3.4.16 | zlib (`SDL3/LICENSE.txt`) | https://github.com/libsdl-org/SDL/releases/download/release-3.4.16/SDL3-3.4.16.tar.gz | `7322236cd12090c3eb40b9728be4d49c76f66ad17d04369584d4ecad5cf77c68` |
| yyjson | 0.13.0 | MIT (`yyjson/LICENSE`) | https://github.com/ibireme/yyjson/archive/refs/tags/0.13.0.tar.gz | `34e0f62a2bc11ab20d601e8ca1cc2b2079503aa45119a19133d89d19b94a0fae` |
| doctest | 2.5.3 | MIT (`doctest/LICENSE.txt`) | https://github.com/doctest/doctest/archive/refs/tags/v2.5.3.tar.gz | `174ebc4e769928959614789c5b4e9c3d0a0f81a62bb608756b127bfebfb21331` |

Notas:

- **SDL3:** se quitaron las carpetas `test`, `examples`, `VisualC`, `VisualC-GDK` y `Xcode`, que no se compilan. Para actualizarla, reemplazar la carpeta completa y volver a quitarlas.
- **yyjson:** solo `yyjson.c`, `yyjson.h` y la licencia.
- **doctest:** solo `doctest.h` y la licencia. Solo se usa en las pruebas.
