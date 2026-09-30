# Generadores de mapas

SalvaCiudad tiene dos generadores de mapas, que se eligen en la partida nueva con **Generador de mapas**. No son dos ajustes del mismo generador: cada uno arma el mapa a su manera. Los dos son deterministas: la misma semilla y las mismas opciones dan siempre el mismo mapa, en cualquier computadora.

- **Clásico:** el de siempre. Parte de un relieve de ruido y le pone encima mesetas, valles, cordilleras y cañones que cruzan el mapa.
- **Jerárquico:** decide de lo general a lo particular. Primero reparte el mapa en regiones, cada una con un solo papel; después coloca dentro de cada región solo las estructuras de ese papel. Nada se encima.

## Cómo saber qué hay en cada lugar

- **F3** (ventana de estadísticas), sección "Bajo el cursor": casilla, suelo, bioma, altura, pendiente, fertilidad, agua y accidentes. En el jerárquico dice además la región ("Región: Montañas") y la estructura exacta. Lo no explorado dice solo "Todavía sin explorar".
- **Ctrl+F12** (reporte del mapa): pintas lo que te interesa y se guarda una captura con los datos del lugar en `%TEMP%\SalvaCiudad\reportes\`. Ver el README.
- **`SalvaCiudad.exe --reporte <carpeta>`**: vuelve a generar el mapa de un reporte con el generador actual y guarda una captura del mismo lugar, para comparar el antes y el después de un cambio.

## Opciones de la partida que cambian el mapa

| Opción | Valores | Qué cambia |
|---|---|---|
| Generador de mapas | Clásico, Jerárquico | Todo el método (ver abajo) |
| Tamaño | Pequeño (512 m) a Colosal (16 km) | El lado del mapa; en el jerárquico, también el tamaño de las regiones |
| Tipo de mapa | Clásico, Arboleda joven, Tierra de gigantes, Pinar del norte, Variado, Islas, Bioma único | Qué biomas hay y en qué proporción; "Islas" hace un mapa de islas |
| Islas por pueblo | 1 a 8 | Solo en "Islas": cuántas islas tiene cada pueblo (la principal y las demás) |
| Mar | Sin mar, A veces, Siempre | Si hay costa en uno o dos lados ("A veces": 40 % de las semillas) |
| Ríos y lagos | Pocos, Normal, Muchos | Cuántos ríos y lagos |
| Bosques, Recursos | Pocos, Normal, Muchos | Cuántos árboles, piedras, vetas, bayas y hierbas |
| Relieve | Plano, Colinas suaves, Montañoso | Qué tan alto y accidentado es el terreno |
| Accidentes del terreno | Pocos, Normal, Muchos | Cuántas mesetas, valles, cordilleras y cañones |

## Generador clásico

Etapas, en orden:

1. **Relieve:** un campo de ruido suave de 20 m ± 5 a 12 m, según "Relieve". Con "Montañoso" se suman **crestas de ruido de hasta 90 m** en zonas amplias. Estas crestas no tienen nombre de accidente: F3 muestra su altura y su pendiente, pero no dice "Cordillera" (D-3706).
2. **Costa** (si hay mar): el mar entra de 12 a 22 % desde uno o dos lados, con orilla doblada por ruido. Además:
   - 0 a 2 **golfos** (el mar entra en la tierra);
   - 0 a 2 **penínsulas** y 0 a 3 **cabos** (la tierra sale al mar);
   - 0 a 3 **islotes**;
   - bajo el mar, a veces una **fosa marina** y una **dorsal marina**, líneas de borde a borde que solo cambian el fondo.
3. **Accidentes del terreno.** Cada uno cruza el mapa de un borde a otro, salvo las mesetas. Por km², con "Normal" (la mitad con "Pocos", el doble con "Muchos"):
   - **Mesetas** (0,35): cima plana con acantilado de 10 m y una rampa de hasta 100 m.
   - **Valles** (0,30): en forma de U, de 160 a 320 m de ancho y 6 a 14 m de hondo.
   - **Cordilleras** (0,20): una cresta con picos, de 35 a 70 m de alto, a lo largo del 35 al 70 % del mapa.
   - **Cañones** (0,25): de 36 a 70 m de ancho, 12 a 25 m de hondo, con paredes a pique; su cabecera suele dar origen a un río.
4. **Lagos:** 0,8 cuencas por km² con "Normal". Se llenan de agua las hondonadas hondas y amplias.
5. **Ríos:** 1 por km² con "Normal". Nacen en lo alto (y en las cabeceras de los cañones) y siguen la pendiente hasta el borde, un lago o el mar, serpenteando.
6. **Suelo, biomas y vida:** humedad, fertilidad, suelos (pasto, pradera, suelo de bosque, arena, roca, arcilla), manchas de bioma del tipo de mapa, bosques, recursos, fauna y salidas justas para cada pueblo.

En los tipos de mapa con islas, el relieve se levanta solo sobre las islas, y cada pueblo empieza en la suya.

## Generador jerárquico

Cada nivel solo refina lo que permitió el anterior.

### Nivel 0: el mundo

Tamaño, semilla y mar. Con costa, el mar ocupa uno o dos lados (entre 12 y 22 % si es un lado, entre 10 y 16 % por lado si son dos). En "Islas", las islas se reparten como en el clásico, y su forma decide dónde hay tierra. El nivel del mar está 2 m por debajo de las llanuras.

### Nivel 1: las regiones

El mapa se divide en regiones irregulares de 150 a 900 m (el lado del mapa entre 7). Cada región tiene **un solo papel**, que F3 muestra como "Región: …":

| Región | Cómo es | Cuántas |
|---|---|---|
| **Llanura** | Casi plana, con ondulaciones amplias | El resto: la mayoría del mapa |
| **Colinas** | Unos 6 m más alta, con lomas; primero junto a las montañas | Lo que sobra de las que no son llanura |
| **Montañas** | Base de 17 a 31 m sobre la llanura; van en cadenas de 2 a 4 regiones | 20, 35 o 55 % de las que no son llanura, según "Relieve" |
| **Meseta** | Cima plana 27 a 41 m sobre la llanura, rodeada de acantilado; nunca toca el mar, una cuenca ni otra meseta | 15 % de las que no son llanura |
| **Cuenca** | Hundida; ahí van los lagos; no toca el mar ni una meseta | 10 % de las que no son llanura |
| **Mar** | Fondo 4 a 8 m bajo el nivel del mar | Las del nivel 0 |

Las regiones que no son llanura son el 30, 45 o 60 % del mapa, según "Accidentes del terreno". En mapas pequeños y medianos, donde las regiones son chicas, las alturas se reducen hasta la mitad para que no todo sea acantilado.

### Nivel 2: las estructuras

Solo dentro de su región, y cada lugar tiene una sola. F3 las muestra en "Accidentes: …".

| Estructura | Dónde | Cómo es | Cuántas |
|---|---|---|---|
| **Cresta** | Montañas | El filo de la cadena, con picos y espolones: 25 a 40 m sobre la base con relieve plano, 40 a 65 m con colinas suaves y 65 a 110 m con montañoso | Una por cadena |
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

Los lagos van en las cuencas. Fuera de ellas solo queda un lago si es grande (1,5 ha o más); las demás hondonadas se rellenan. Los ríos nacen en los valles y cañones que tienen río, y además en lo alto, como en el clásico. Siguen la pendiente hasta un lago, el mar o el borde.

### Nivel 4: suelo y vida

Cada región tiene un solo bioma del tipo de mapa, y las montañas son pinares si el tipo de mapa los tiene. Los suelos, bosques, recursos y fauna salen de las mismas etapas que el clásico. Los pueblos empiezan en llanuras o colinas, fuera de cualquier estructura, con agua a 150 m o menos, piedra, bayas y árboles cerca.

### Nivel 5: detalle fino

Lomas de 64 m, ondulaciones de 512 m y 40 cm de relieve fino, más las rocas, arbustos, hierbas y el pasto de las etapas compartidas.

## Todo lo que F3 puede nombrar

| Nombre | Clásico | Jerárquico | Qué es |
|---|---|---|---|
| Llanura, Colinas, Montañas, Meseta, Cuenca, Mar (como región) | – | Sí | El papel de la región |
| Meseta | Sí | Sí | Clásico: accidente; jerárquico: región |
| Valle | Sí | Sí | Hondonada en U |
| Cordillera | Sí | – | Clásico: cresta que cruza parte del mapa |
| Cresta, Paso de montaña | – | Sí | El filo de una cadena y su parte baja |
| Cañón | Sí | Sí | Corte angosto de paredes a pique |
| Acantilado, Rampa | – | Sí | Borde y subida de una meseta |
| Costa | Sí | Sí | Tierra con el mar a 12 m o menos |
| Golfo, Península, Islote, Isla | Sí | Sí | Formas de la costa y del mar |
| Cabo | Sí | – | Una península corta |
| Fosa marina, Dorsal marina | Sí | – | Fondo marino más hondo o más alto |
| Río, Lago, Mar, Estuario (como agua) | Sí | Sí | El agua bajo el cursor; "Estuario" es la desembocadura de un río |

Las decisiones de detalle están en `docs/DECISIONES.md` (D-3701 a D-3707 para los nombres, D-3901 en adelante para el jerárquico).
