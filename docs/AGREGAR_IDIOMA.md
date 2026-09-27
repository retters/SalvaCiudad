# Cómo agregar un idioma

No hace falta programar ni recompilar.

1. Copia `data/lang/en.json` junto a él, con el código del idioma como nombre: por ejemplo `fr.json` para francés o `pt-BR.json` para portugués de Brasil.
2. Cambia la sección `language`:
   - `code`: el mismo código del nombre del archivo.
   - `name`: el nombre del idioma en ese idioma ("Français").
   - `pluralRule`: una de `none`, `one`, `oneUpToOne`, `eastSlavic`, `polish`, `czech` o `arabic`. Ver la tabla de abajo.
   - `decimalSeparator`, `groupSeparator` y `minimumGroupingDigits` (1 o 2): formato de los números.
3. Traduce los textos de `strings`. **No cambies las claves** (lo que está a la izquierda de los dos puntos).
4. Abre el juego: el idioma aparece en Configuración → Idioma.

## Reglas para traducir

- `{0}`, `{1}`… se reemplazan por valores. Puedes cambiarlos de orden según tu idioma. Lo que va después de los dos puntos (`{0:action}`) solo explica qué es.
- Para un `{` o `}` literal, escribe `{{` o `}}`.
- `\n` es un salto de línea.
- Los textos con plural son objetos con una forma por categoría (`one`, `few`, `many`, `other`…). La forma `other` es obligatoria.
- Si falta un texto, el juego usa el del idioma base (el padre, por ejemplo `es` para `es-MX`, y después el inglés) y lo anota en el registro. Nunca queda un hueco.

## Reglas de plural disponibles

| Regla | Idiomas | Categorías |
|---|---|---|
| `none` | japonés, chino, coreano, vietnamita, tailandés, indonesio | other |
| `one` | inglés, español, alemán, italiano, neerlandés, sueco, portugués de Portugal | one, other |
| `oneUpToOne` | francés, portugués de Brasil, hindi | one (0 y 1), other |
| `eastSlavic` | ruso, ucraniano, bielorruso | one, few, many |
| `polish` | polaco | one, few, many |
| `czech` | checo, eslovaco | one, few, other |
| `arabic` | árabe | zero, one, two, few, many, other |

Si un idioma necesita otra regla, hay que agregarla a `src/i18n/plural.cpp`. Es el único caso que requiere código.

## Variantes regionales

Un archivo como `es-MX.json` puede tener `strings` vacío o solo los textos que cambian: el resto se toma de `es.json`.

## Alfabetos no latinos

Las tipografías incluidas cubren el alfabeto latino. Para un idioma con otro alfabeto hay que agregar a `data/fonts/` una fuente que lo cubra y listarla en `fonts.json`.

## Comprobar

Las pruebas automáticas (`ctest`) comprueban que `en.json` y `es.json` tengan exactamente las mismas claves. Si agregas el idioma al repositorio, agrégalo también a esa prueba.
