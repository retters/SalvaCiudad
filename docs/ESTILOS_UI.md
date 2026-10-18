# Cómo hacer un estilo de la interfaz

La interfaz del juego (fases 117 a 127) está hecha con RmlUi: cada ventana, panel y menú es un documento RML con hojas RCSS, y su aspecto sale de un **estilo**. El juego trae dos, **Frosted** (por omisión) y **Vidrio oscuro**, y un mod puede traer más. Un estilo es **solo datos**: valores, hojas e imágenes. No ejecuta nada.

Esta guía es para quien hace un estilo, sea para el juego o para un mod.

## Dónde va

```
data/ui/styles/<id>/          estilos del juego
<mod>/ui/styles/<id>/         estilos de un mod
    style.json                obligatorio
    *.rcss                    hojas propias (opcional)
    *.png                     imágenes que usan los tokens o las hojas (opcional)
```

El `<id>` es el nombre de la carpeta (minúsculas, dígitos y `-`). Un estilo con el mismo id que otro ya cargado se rechaza. El elegido se guarda en `settings.json` como `ui.style`. Si deja de existir (se quitó el mod), se vuelve a Frosted.

## `style.json`

```json
{
  "schemaVersion": 1,
  "name": {"es": "Pizarra", "en": "Slate"},
  "glass": false,
  "tokens": {"text": "#e8ecef", "accent": "#f2b544", "panel-radius": "6px", "icon-mode": "solid"},
  "sheets": ["style.rcss"]
}
```

- `name`: el nombre en cada idioma; se muestra en Configuración › Interfaz › «Estilo de la interfaz», con una muestra de sus colores.
- `glass`: si las ventanas desenfocan el mapa que hay detrás. Sin vidrio, o con el ajuste «Vidrio: Simple», el fondo de las ventanas es el token `panel-simple` en lugar de `panel`.
- `tokens`: los valores que cambian. Los que no se nombran quedan como en Frosted.
- `sheets`: hojas `.rcss` propias, en la carpeta del estilo, que se cargan después de las comunes.

Cualquier error invalida el estilo entero y el motivo queda en el registro del juego: un token desconocido, un valor del tipo equivocado, una hoja o imagen que falta, o una ruta que sale de la carpeta. El juego sigue con el estilo anterior.

## Los tokens

Cada token tiene un tipo. Los valores se escriben como en CSS y el juego los pasa a RCSS (por ejemplo, el alfa de 0 a 1 pasa a 0 a 255 y `px` a `dp`, que crece con la escala de la interfaz). La lista completa, con su valor por omisión, está en `src/ui/rml/rml_style.cpp`.

| Tipo | Ejemplos | Tokens |
|---|---|---|
| Color | `#5b5bd6`, `rgba(20, 30, 70, .1)` | `text`, `dim`, `accent`, `accent-text`, `ok`, `warn`, `bad`, `info`, sus versiones `-soft`, `title-text`, `panel-solid`, `panel-border`, `sep`, `btn`, `btn-hover`, `btn-on`, `btn-on-text`, `btn-border`, `chip`, `row`, `row-hover`, `row-border`, `meter`, `switch-off`, `knob`, `icon`, `icon-hover`, `icon-on`, `tip`, `tip-text` |
| Pintura | un color, `linear-gradient(...)`, `radial-gradient(...)`, `image(grano.png repeat)` y varias separadas por comas | `panel`, `panel-simple`, `switch-on`, `thumb` |
| Medida | `16dp`, `6px` | `font-size`, `font-small`, `title-size`, `panel-border-width`, `panel-radius`, `panel-pad`, `btn-radius`, `btn-size`, `row-radius`, `tip-radius` |
| Número | `700` | `title-weight` |
| Sombra | `0 10px 32px rgba(20, 30, 70, .2)`, con `inset` | `panel-shadow`, `btn-shadow` |
| Filtro | `blur(18px) saturate(160%)` | `panel-blur` |
| Tipografía | `ui` (la elegida en Configuración) | `font` |
| Íconos | `stroke`, `duotone` o `solid` | `icon-mode` |

Qué toca cada uno, a grandes rasgos:

- **Texto**: `text` el normal, `dim` el secundario, `title-text` los títulos; `accent` lo destacado (pestaña elegida, títulos de sección, el foco del teclado).
- **Ventanas y paneles**: `panel` (o `panel-simple`), `panel-border`, `panel-radius`, `panel-shadow`, `panel-blur` (solo con vidrio) y `panel-pad`.
- **Botones**: `btn`, `btn-hover`, `btn-border`, `btn-radius`, `btn-shadow`; el botón activo (una pestaña, un interruptor encendido, «Fundar aquí») usa `btn-on` y `btn-on-text`.
- **Filas** (personas, aldeas de la sala, partidas guardadas): `row`, `row-hover`, `row-border`, `row-radius`.
- **Estados**: `ok`, `warn`, `bad` y `info`, con sus fondos suaves `-soft` (los chips «Trabajando» y «Detenido», los avisos, «Demoler»).
- **Barras y deslizadores**: `meter` es el fondo; `switch-on` el relleno y el tirador.
- **Imagen de una cosa**: `thumb` es el fondo detrás de la miniatura de un edificio o el retrato de un aldeano.
- **Ayudas emergentes**: `tip`, `tip-text`, `tip-radius`.

## Las hojas

Las hojas comunes están en `data/ui`: `base.rcss` (texto, imágenes y el foco del teclado), `window.rcss` (ventanas: `.window`, `.bar`, `.wbtn`, `.row`, `.chip`...), `hud/hwin.rcss` (el marco de las ventanas del juego) y `hud/thing.rcss` (las filas: `.btn`, `.btns`, `.kv`, `.line`, `.section`, `.meter`, `.hero`, `.people`, `.slider`...). La hoja de un estilo se carga después y puede cambiar cualquier regla. Puede usar `var(--token)` en cualquier valor.

Por ejemplo, Vidrio oscuro (`data/ui/styles/vidrio/style.rcss`) pinta el borde de las ventanas con dos colores y da un brillo a lo activo:

```css
.window
{
	border-color: rgba(155, 123, 255, 200) rgba(76, 201, 240, 200) rgba(76, 201, 240, 200) rgba(155, 123, 255, 200);
}

.wbtn.on
{
	box-shadow: rgba(155, 123, 255, 140) 0 0 16dp 0;
}
```

Hay que tener en cuenta lo que RCSS no tiene: no hay bordes con degradado, `opacity` no se hereda en `image-color` (se pone en la regla del `img`), y el texto suelto dentro de un contenedor `flex` no se ve si no va en su `<span>`.

## Los íconos

Los íconos son un set propio (`data/ui/icons/icons.json`), dibujado por `tools/ui/iconos.py` en tres modos (`stroke`, `duotone` y `solid`) y dos tamaños (el doble desde una escala de 1,5). El estilo elige el modo con `icon-mode`; el color sale de `icon`, `icon-hover` e `icon-on`. Para agregar un ícono: se suma su trazo a `icons.json` y se corre `python -I tools/ui/iconos.py`. `python -I tools/ui/iconos.py comprobar` verifica que los atlas estén al día.

## El vidrio

Con `glass: true` y «Vidrio: Completo», el juego desenfoca la imagen del mapa una sola vez por cuadro (a la mitad, un cuarto o un octavo de tamaño, según el radio de `panel-blur`) y cada ventana muestra su parte detrás de `panel`. Por eso `panel` debe ser translúcido; `panel-simple` debe ser casi opaco, porque es lo que se ve sin el desenfoque. El costo está en `docs/RENDIMIENTO.md`.

## El foco del teclado

Tab, las flechas, Enter y Espacio recorren los botones de los menús, y Tab entra en las ventanas durante la partida (fase 127). El elemento enfocado lleva la pseudoclase `:focus-visible`; por omisión se marca con el borde y un anillo en el color `accent` (`base.rcss`). Un estilo puede dibujarlo a su manera en su hoja.

## Probarlo

1. Copiar la carpeta del estilo a `data/ui/styles/` (o a `ui/styles/` de un mod activo).
2. Abrir Configuración › Interfaz y elegirlo: el cambio es en vivo, con la ventana abierta.
3. Si no aparece, el motivo está en el registro (`userdata/logs/salvasprosperia.log`).
4. Repasar con él las ventanas, los menús y los paneles de la lista de `docs/VERIFICACION_MANUAL.md`, con vidrio completo y simple, y en las escalas de 75 % a 200 %.

El mod de ejemplo trae un estilo completo y pequeño: `tools/example_mod/ui/styles/pizarra`.
