# Generador de mapas

SalvaCiudad tiene un solo generador de mapas, el **jerárquico**: decide de lo general a lo particular. Primero reparte el mapa en regiones, cada una con un solo papel; después coloca dentro de cada región solo las estructuras de ese papel. Nada se encima. Es determinista: la misma semilla y las mismas opciones dan siempre el mismo mapa, en cualquier computadora.

Hasta la fase 48 había además un generador **clásico** (relieve de ruido con mesetas, valles, cordilleras y cañones que cruzaban el mapa, costas con cabos y un fondo marino con fosas y dorsales). Se borró en la fase 49 (D-4901); quedó archivado en `J:\Back\salvaciudad-alfa-1.zip`.

## Cómo saber qué hay en cada lugar

- **F3** (ventana de estadísticas), sección "Bajo el cursor": casilla, suelo, bioma, altura, pendiente, fertilidad, agua, la región ("Región: Montañas") y la estructura exacta ("Accidentes: Cresta"). Lo no explorado dice solo "Todavía sin explorar".
- **Ctrl+F12** (reporte del mapa): pintas lo que te interesa y se guarda una captura con los datos del lugar en `%TEMP%\SalvaCiudad\reportes\`. Ver el README.
- **`SalvaCiudad.exe --reporte <carpeta>`**: vuelve a generar el mapa de un reporte con el generador actual y guarda una captura del mismo lugar, para comparar el antes y el después de un cambio.

## Opciones de la partida que cambian el mapa

| Opción | Valores | Qué cambia |
|---|---|---|
| Tamaño | Pequeño (512 m) a Colosal (16 km) | El lado del mapa y el tamaño de las regiones |
| Tipo de mapa | Variado, Personalizado | En Variado la semilla decide el clima y el mar y lo demás va en 100 %; lo que sigue se elige en Personalizado (fase 56) |
| Biomas | Una casilla por bioma | Solo crecen los marcados, cada uno donde le toca (fase 54, ver `docs/ARBOLES.md`) |
| Temperatura, Humedad | 0 a 200 % | Corren todo el mapa hacia el frío o el calor, lo seco o lo húmedo |
| Variación del clima | Poca, Mucha | "Mucha": frío en el norte y cálido en el sur; "Poca": casi el mismo clima en todo el mapa |
| Mar | Sin mar, Un lado, Dos lados, Islas, Archipiélago | Costa en uno o dos lados; "Islas" da una isla por pueblo y "Archipiélago" varias |
| Islas por pueblo | Las que quepan, hasta 8 | Solo en "Archipiélago": la isla principal de cada pueblo y las demás. Entre dos islas siempre hay un canal de mar |
| Ríos | 0 a 200 % | Cuántos ríos nacen además de los de los valles y cañones |
| Lagos | 0 a 200 % | Cuántas cuencas hay y qué tan fácil se llenan |
| Bosques, Recursos | 0 a 200 % | Cuántos árboles, piedras, vetas, bayas y hierbas |
| Relieve | 0 a 200 % | Qué parte de las regiones accidentadas son montañas (5, 20, 35 y 60 % a 0, 50, 100 y 200 %) y qué tan altas son sus crestas |
| Accidentes del terreno | 0 a 200 % | Qué parte del mapa no es llanura (0, 30, 45 y 60 %), y cuántos valles y cañones hay |
| Árboles gigantes | Sí o no, y 0 a 200 % | Cuántos gigantes (fase 55) |

## Los niveles

Cada nivel solo refina lo que permitió el anterior.

### Nivel 0: el mundo

Tamaño, semilla y mar. Con costa, el mar ocupa uno o dos lados (entre 12 y 22 % si es un lado, entre 10 y 16 % por lado si son dos). En "Islas", las islas se reparten en archipiélagos (una isla principal por pueblo, lo más lejos posible entre sí, y las demás alrededor de la suya), y su forma decide dónde hay tierra. El nivel del mar está 2 m por debajo de las llanuras.

### Nivel 1: las regiones

El mapa se divide en regiones irregulares de 150 a 900 m (el lado del mapa entre 7). Cada región tiene **un solo papel**, que F3 muestra como "Región: …":

| Región | Cómo es | Cuántas |
|---|---|---|
| **Llanura** | Casi plana, con ondulaciones amplias | El resto: la mayoría del mapa |
| **Colinas** | Unos 6 m más alta, con lomas; primero junto a las montañas | Lo que sobra de las que no son llanura |
| **Montañas** | Base de 17 a 31 m sobre la llanura; van en cadenas de 2 a 4 regiones | 20, 35 o 60 % de las que no son llanura con "Relieve" en 50, 100 o 200 % |
| **Meseta** | Cima plana 27 a 41 m sobre la llanura, rodeada de acantilado; nunca toca el mar, una cuenca ni otra meseta | 15 % de las que no son llanura |
| **Cuenca** | Hundida; ahí van los lagos; no toca el mar ni una meseta | 10 % de las que no son llanura |
| **Mar** | Fondo 4 a 8 m bajo el nivel del mar | Las del nivel 0 |

Las regiones que no son llanura son el 30, 45 o 60 % del mapa con "Accidentes del terreno" en 50, 100 o 200 % (ninguna en 0 %). En mapas pequeños y medianos, donde las regiones son chicas, las alturas se reducen hasta la mitad para que no todo sea acantilado.

### Nivel 2: las estructuras

Solo dentro de su región, y cada lugar tiene una sola. F3 las muestra en "Accidentes: …".

| Estructura | Dónde | Cómo es | Cuántas |
|---|---|---|---|
| **Cresta** | Montañas | El filo de la cadena, con picos y espolones: 25 a 40 m sobre la base con relieve hasta 60 %, 40 a 65 m hasta 150 % y 65 a 110 m de ahí en adelante | Una por cadena |
| **Paso de montaña** | En una cresta | Un tramo de 120 m donde la cresta baja un 65 % | 7 de cada 10 crestas |
| **Acantilado** | Borde de una meseta | La caída de la cima al terreno de alrededor | Todo el borde |
| **Rampa** | Una meseta | Un corte que baja de la cima hasta el pie del acantilado, hacia una llanura o colinas | Una por meseta |
| **Valle** | De colinas o montañas hacia una llanura o cuenca vecina | En forma de U, de 80 a 320 m de ancho y 6 a 12 m de hondo, bajando hacia la salida; el 60 % tiene río | Uno por cada 7, 3 o 2 regiones que pueden tenerlo, según "Accidentes" |
| **Cañón** | Solo mesetas de 1,3 ha o más | Angosto, de paredes a pique, desde lo hondo de la meseta hasta la región vecina más baja; el 75 % tiene río | Pocos: 15, 25 o 40 % de las mesetas, al menos uno si hay mesetas (salvo "Pocos") |
| **Golfo** | Costa | Una región de tierra que el mar tomó | 0 a 2 |
| **Península** | Costa | Una región de mar que quedó tierra | 0 a 2 |
| **Islote** | Mar abierto | Una isla de 20 a 60 m | 0 a 3 |
| **Isla** | Mapas de islas | Cada isla, con sus regiones adentro | Las que pide "Islas por pueblo" |

### Nivel 3: el agua

Los lagos van en las cuencas. Fuera de ellas solo queda un lago si es grande (1,5 ha o más); las demás hondonadas se rellenan. Los ríos nacen en los valles y cañones que tienen río, y además en lo alto: 1 por km² con "Normal" (la mitad con "Pocos", el doble con "Muchos"). Siguen la pendiente hasta un lago, el mar o el borde, serpenteando.

### Nivel 4: suelo y vida

Humedad, fertilidad y suelos (pasto, pradera, suelo de bosque, arena, roca, arcilla) según el agua y las pendientes. Cada bloque de 8 m toma el bioma que mejor encaja con su temperatura (baja hacia el norte y con la altura), su humedad, el agua cercana, su región y su altura (fase 54; las reglas, en `docs/ARBOLES.md`). Después, bosques, recursos y fauna. Los pueblos empiezan en llanuras o colinas, fuera de cualquier estructura, con agua a 150 m o menos, piedra, bayas y árboles cerca.

### Nivel 5: detalle fino

Lomas de 64 m, ondulaciones de 512 m y 40 cm de relieve fino, más las rocas, arbustos, hierbas y el pasto.

## Todo lo que F3 puede nombrar

| Nombre | Qué es |
|---|---|
| Llanura, Colinas, Montañas, Meseta, Cuenca, Mar (como región) | El papel de la región |
| Cresta, Paso de montaña | El filo de una cadena y su parte baja |
| Acantilado, Rampa | Borde y subida de una meseta |
| Valle | Hondonada en U |
| Cañón | Corte angosto de paredes a pique |
| Golfo, Península, Islote, Isla | Formas de la costa y del mar |
| Costa | Tierra con el mar a 12 m o menos (no es una estructura: sale del mar mismo) |
| Río, Lago, Mar, Estuario (como agua) | El agua bajo el cursor; "Estuario" es la desembocadura de un río |

Las decisiones de detalle están en `docs/DECISIONES.md` (D-3701 a D-3707 para los nombres, D-3901 a D-4305 para el generador y D-4901 en adelante para la fase 49).
