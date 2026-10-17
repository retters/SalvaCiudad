# Propuestas de interfaz

Maquetas en HTML del HUD del juego en varios estilos, para decidir la apariencia antes de tocar el motor. No cambian nada del juego.

## Cómo verlas

Abre `index.html` (la galería) con el servidor de propuestas, o directo desde el disco:

```
python -m http.server 8765 --bind 127.0.0.1 --directory docs/propuestas
```

y luego `http://localhost:8765/interfaz/`.

- **Galería** (`index.html`): una miniatura en vivo de cada tema, su costo en rendimiento y tu voto. La escena de las miniaturas se elige arriba.
- **Visor** (`ver.html`): el tema a tamaño real (1920 × 1080 escalado a la ventana). Flechas ← → cambian de tema, 1 a 5 de escena, F de fondo, L de idioma, W cambia entre ventanas flotantes y en columna lateral (inspector), H oculta los controles y mantener C compara con el HUD actual. Las ventanas se arrastran por el título, cambian de tamaño por la esquina y tienen sus botones activos (fijar, minimizar, cerrar, pestañas). Pasa el ratón para ver los textos de ayuda del juego.
- **Comparar** (`comparar.html`): un mismo elemento (barra superior, ventana de edificio, de aldeano o de casa, botones de ventana, Bienes, barra de construcción, dock, minimapa, avisos, pregunta del pueblo o menú) recortado en todos los temas a la vez. El ♥ marca esa parte como «me gusta» del tema, así puedes armar una mezcla.
- **Íconos** (`iconos.html`): nuestro set propio contra Lucide, Phosphor y Tabler. Las bibliotecas se descargan solo al pulsar el botón (jsDelivr y unpkg, versiones fijas).

## Temas (46)

- **Actual** (`actual`): El HUD del juego hoy.
- **Taberna** (`taberna`): Evolución del tema actual: madera, latón y pergamino.
- **Pizarra** (`pizarra`): Tu imagen, panel oscuro de arriba a la izquierda.
- **Crema** (`crema`): Tu imagen, variante clara de arriba a la derecha.
- **Windows 98** (`win98`): Windows 98 / Classic.
- **Windows 11** (`win11`): Fluent 2: Mica y Acrílico.
- **macOS** (`macos`): macOS Sonoma / Sequoia.
- **Liquid Glass** (`liquid`): iOS 26 / macOS Tahoe.
- **Material 3** (`material`): Android 15 / Material You.
- **Frosted** (`frosted`): Frosted UI / glassmorphism claro.
- **Pergamino** (`pergamino`): Juegos de estrategia de fantasía (marcos dorados).
- **Mínimo** (`minimo`): HUD contextual de los juegos modernos.
- **Windows 7 Aero** (`aero`): Windows 7 / Vista: Aero Glass.
- **Windows XP** (`luna`): Windows XP: Luna azul.
- **Aqua** (`aqua`): Mac OS X 10.0 a 10.4.
- **Mac OS 9** (`platinum`): Mac OS 8 y 9: Platinum.
- **Metro** (`metro`): Windows 8 / Windows Phone.
- **GNOME** (`adwaita`): GNOME 46 / libadwaita (oscuro).
- **Consola** (`consola`): Steam Deck / Big Picture.
- **Acogedor** (`acogedor`): Juegos acogedores (Animal Crossing, Stardew).
- **Neumorfismo** (`neumorfismo`): Soft UI (2020).
- **Pixel** (`pixel`): RPG de 16 bits (SNES).
- **Vidrio oscuro** (`vidrio`): Glassmorphism oscuro con neón.
- **iOS 6** (`ios6`): iOS 6 / esqueuomorfismo.
- **ChromeOS** (`chromeos`): ChromeOS / Material You claro.
- **Windows 11 claro** (`fluentclaro`): Fluent 2 claro: Mica.
- **KDE Plasma** (`breeze`): KDE Plasma 6: Breeze oscuro.
- **Terminal** (`terminal`): Monitor de fósforo verde.
- **Imperial** (`imperial`): Constructores de ciudades históricos: azul marino y oro.
- **Acuarela** (`acuarela`): Mapas y diarios ilustrados.
- **Nórdico** (`nordico`): Juegos de construir minimalistas (Islanders, Townscaper).
- **Alto contraste** (`contraste`): Modo de accesibilidad.
- **Heráldico** (`heraldico`): Estandartes y blasones medievales.
- **Tallado** (`tallado`): Juegos de granja: tablones de madera.
- **Piedra** (`piedra`): Tablillas de piedra y runas.
- **Windows 3.1** (`win31`): Windows 3.1 (1992).
- **BeOS** (`beos`): BeOS / Haiku.
- **Material 2014** (`material2`): Google Material Design original.
- **Washi** (`washi`): Papel japonés y tinta sumi.
- **Bazar** (`bazar`): Mercados del desierto: terracota y azulejo.
- **Escarcha** (`escarcha`): Invierno: hielo y escarcha.
- **Noche estrellada** (`estrellas`): Un modo nocturno para el HUD.
- **Cartógrafo** (`cartografo`): Mapas antiguos en sepia.
- **Vitral** (`vitral`): Vidrieras de catedral.
- **Papel recortado** (`recortado`): Manualidades de cartulina en capas.
- **Marfil y oro** (`marfil`): Interfaces de lujo: marfil, oro y negro.

Además del aspecto, cada tema elige unas pocas cosas de acomodo (`layout` en `temas/catalogo.js`): barra superior a lo ancho, en píldoras o en isla central; dock con texto, solo íconos o riel; construcción en pestañas, en dock con aumento, en menú Inicio o con riel de categorías; minimapa cuadrado, redondeado o redondo; botones de ventana a la derecha, semáforos a la izquierda u hoja con asa; avisos en pila, arriba o abajo al centro; y ventanas flotantes o en columna lateral. En el visor, «Ventanas» fuerza flotantes o columna en cualquier tema.

## Escenas

Las cinco escenas cubren todos los elementos del HUD actual:

1. **Ventanas de selección**: edificio (Cantero, con trabajadores), aldeano (Nyxar), casa (habitantes, felicidad, entorno, necesidades, anexos) y la ventana de cámara.
2. **Panel del pueblo**: Bienes, Estadísticas, Eventos (con pestañas apiladas) y un recurso del mapa (arbusto de bayas).
3. **Construir y avisos**: obra en construcción, animal peligroso (lobo), pregunta del pueblo (tortugas), indicación de colocación y avisos.
4. **Comercio y ejército**: Ejército, Comercio y Capas.
5. **Menú y diálogo**: menú del juego y un diálogo, con una ventana minimizada.

En todas están la barra superior (recursos, población, enfermos, felicidad, oro, clima, fecha y velocidad), el dock, el minimapa, la barra de construcción con sus 12 categorías y los avisos que van llegando.

## Qué es real y qué no

- Los **textos** salen de `data/lang` y `data/mods/core/lang` (español e inglés). Lo poco que el juego aún no muestra lleva una estrella ✦ (por ejemplo «+4 al día» o el historial de 12 meses).
- Los **edificios, recursos y razas** salen de `data/mods/core/defs`.
- Las **miniaturas** de edificios, cosas y retratos están renderizadas con Blender desde los modelos del juego (`img/`). Los retratos usan la paleta de cada raza.
- Los **fondos** son capturas limpias del juego (sin HUD) hechas con el reporte del mapa (Ctrl+F12, Enter) sobre las escenas de prueba manuales, más algunas capturas de fases anteriores recortadas.
- El **minimapa** es el del juego, recortado de una captura.

## Rendimiento

Cada tema lista sus efectos y el costo estimado por cuadro a 1920 × 1080, con una tarjeta media y con gráficos integrados (`temas/catalogo.js`, `EFECTOS`). Son estimaciones, no mediciones. Lo que se sabe del motor:

- El sombreador del HUD (`shaders/ui.frag.hlsl`) hoy solo pinta rectángulos de color, letras y la imagen del minimapa. Esquinas redondeadas, bordes y sombras suaves piden una distancia con signo (SDF) en ese sombreador: se programa una vez y cuesta casi nada.
- El motor **ya desenfoca la escena** detrás del menú de pausa (`shaders/blur.frag.hlsl`, gaussiano de 9 muestras en dos pasadas). El vidrio esmerilado del HUD reutilizaría esa pasada, pero corriendo en cada cuadro mientras se juega: es el efecto que más cuesta después de la refracción tipo Liquid Glass.
- El resplandor (`src/ui/glow.cpp`) ya existe para el logotipo.

## Respuestas

En el visor (panel derecho) y en la página de íconos marcas Sí, Tal vez o No, qué partes te gustan y notas; en la galería hay un cuadro de comentarios generales. Se guardan en este navegador y, si lo abres con «Abrir respuestas.json», en `docs/propuestas/interfaz/respuestas.json`. Para leerlas:

```
python tools/propuestas/interfaz.py respuestas
```

## Cómo se regeneran

```
python tools/propuestas/interfaz.py datos        # kit/datos.js desde las definiciones y textos del juego
python tools/propuestas/interfaz.py fondos       # fondos/ desde las capturas de .claude/capturas (locales)
python tools/propuestas/interfaz.py miniaturas   # img/ con Blender 5.2 (unos 5 minutos)
```

## Archivos

- `kit/kit.js`: arma todo el HUD (una sola estructura para todos los temas) y su interacción.
- `kit/kit.css`: estructura y variables de diseño que cada tema redefine.
- `kit/iconos.js`: el set de íconos propio (cuadrícula de 24, trazo con capa opcional de relleno).
- `kit/respuestas.js`: guardado de respuestas (navegador y archivo).
- `temas/catalogo.js`: la lista de temas, sus decisiones de acomodo y los efectos con su costo.
- `temas/<id>.css`: la apariencia de cada tema.

## Decisiones tomadas al hacerlas

- Una sola estructura de HUD para todos los temas, para comparar solo la apariencia y unas pocas opciones de acomodo (barra o píldoras arriba, dock con texto o íconos, construcción en pestañas, dock o menú Inicio, botones de ventana a la derecha o semáforos a la izquierda, avisos en pila, arriba o abajo).
- Las fuentes que no tiene el proyecto (Segoe UI Variable, Tahoma, Bahnschrift) son del sistema Windows y solo sirven para la maqueta; usarlas en el juego obligaría a vendorizar una equivalente con licencia libre. Las del proyecto (Alegreya Sans, EB Garamond, Barlow Semi Condensed) están copiadas en `docs/propuestas/fuentes` con su OFL.
- El set de íconos propio se dibujó a mano con reglas fijas para que los íconos del juego (recursos, razas, categorías) salgan de la misma familia.
