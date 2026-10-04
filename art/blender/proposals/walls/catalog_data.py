"""The catalog texts (Spanish) of the family's groups. build.py joins them
with the models that exist and writes catalogo.json."""

CAT = "Muros y defensas"

RULE = (" Regla de conexión: cada celda de muro mira a sus 4 vecinas; sin vecinos usa «pilar», con 1 «remate», "
        "con 2 opuestas «recto», con 2 en ángulo «esquina», con 3 «unión en T» y con 4 «cruce», girando la pieza "
        "en pasos de 90°. Todas las piezas muestran la misma sección en el centro de cada borde de celda, así que "
        "encajan sin costuras; el «medio módulo» de 1 m cierra tramos de longitud impar en la rejilla de 1 m y el "
        "«escalón» sube 1 m en laderas. La «diagonal» cubre los trazados a 45°. Las torres (4 × 4 m) y las "
        "puertas (4 × 2 m) se centran sobre la línea del muro y lo interrumpen; donde se juntan dos tipos de "
        "muro distintos se pone el «pilar» del más alto.")

GROUPS = [
    {
        "id": "wall_palisade",
        "nombre": "Empalizada de troncos",
        "categoria": CAT,
        "descripcion": "Troncos apuntados atados con cuerda, con postes más gruesos en las uniones. Módulo de 2 m, "
                       "3 m de alto (3,6 m los postes) y 0,4 m de grueso; sin adarve." + RULE,
        "propuestas": [
            {"titulo": "Primer muro, barato y rápido",
             "detalle": "Sustituye a la empalizada actual: 4 troncos y 40 de trabajo por módulo, 400 puntos de "
                        "vida, arde con el fuego. El jugador la traza arrastrando y el juego elige esquinas, "
                        "uniones y remates."},
            {"titulo": "Mejora a piedra sin derribar",
             "detalle": "Cada módulo se puede mejorar a muralla de piedra pagando solo la diferencia (4 de piedra); "
                        "mientras dura la obra se ve la pieza «en construcción» y sigue cerrando el paso."},
            {"titulo": "Brechas visibles",
             "detalle": "Por debajo del 35 % de vida el módulo cambia a la pieza «brecha»: los asaltantes pasan "
                        "despacio por ella y un constructor la repara con 2 troncos."},
            {"titulo": "Troneras para la milicia",
             "detalle": "La pieza con tronera deja disparar a un arquero de la milicia desde el suelo, con medio "
                        "alcance, sin exponerse."},
        ],
    },
    {
        "id": "wall_plank",
        "nombre": "Muro de tablas con adarve",
        "categoria": CAT,
        "descripcion": "Cajón de tablas aserradas sobre postes, con pasarela y parapeto almenado de madera a los "
                       "dos lados. Módulo de 2 m, adarve a 2,6 m, 3,7 m de alto total y 1,2 m de grueso." + RULE +
                       " La «escalera» es la única subida al adarve.",
        "propuestas": [
            {"titulo": "Adarve de madera para arqueros",
             "detalle": "Cuesta 6 troncos por módulo y tiene 700 puntos de vida. Los arqueros y la "
                        "milicia suben por la escalera y disparan desde arriba con +25 % de alcance; arde."},
            {"titulo": "Paso intermedio entre empalizada y piedra",
             "detalle": "Mejora de la empalizada (nivel 1,5): se desbloquea con las herramientas y permite defender "
                        "desde arriba antes de tener cantera."},
            {"titulo": "Camino elevado",
             "detalle": "Los aldeanos pueden usar el adarve como atajo entre torres cuando suena la campana, sin "
                        "abrir las puertas."},
        ],
    },
    {
        "id": "wall_stockade",
        "nombre": "Empalizada doble con adarve",
        "categoria": CAT,
        "descripcion": "Dos filas de troncos con tierra apisonada entre ellas y una pasarela de tablas encima; "
                       "los troncos sobresalen del adarve, altos y bajos por turnos, y hacen de parapeto a los "
                       "dos lados. Módulo de 2 m, adarve a 2,2 m, 4 m de alto total y 1,4 m de grueso." + RULE +
                       " La «escalera» es la subida al adarve.",
        "propuestas": [
            {"titulo": "Mejora de la empalizada sin cambiar de material",
             "detalle": "Añade una segunda fila y el relleno a una empalizada ya construida: +4 troncos y 40 de "
                        "trabajo por módulo. Pasa de 400 a 900 puntos de vida y gana adarve para arqueros."},
            {"titulo": "Aguanta el fuego",
             "detalle": "El relleno de tierra hace que arda a la mitad de velocidad que la empalizada simple "
                        "y que no se derrumbe hasta perder toda la vida."},
            {"titulo": "Muro de frontera",
             "detalle": "Pensada para pueblos de bosque sin cantera: da la función de la muralla (defender "
                        "desde arriba) solo con troncos, a costa de ocupar más y de arder."},
        ],
    },
    {
        "id": "wall_fieldstone",
        "nombre": "Muro bajo de piedra de campo",
        "categoria": CAT,
        "descripcion": "Piedra suelta sin labrar, con albardilla de lajas y pilares en las uniones. Módulo de 2 m, "
                       "1,2 m de alto y 0,7 m de grueso; sin adarve." + RULE,
        "propuestas": [
            {"titulo": "Cercado barato con la piedra suelta del mapa",
             "detalle": "2 de piedra por módulo y 20 de trabajo. No detiene a los asaltantes (lo saltan con una "
                        "pausa de 2 s), pero sí a jabalíes, lobos y ciervos: protege campos y huertos."},
            {"titulo": "Linde de pastos",
             "detalle": "Cierra un pasto: los animales del establo pastan dentro sin pastor. El «paso de "
                        "escalones» deja cruzar a los aldeanos y no al ganado."},
            {"titulo": "Mejora del entorno",
             "detalle": "Cuenta como adorno para las casas a 6 m (+1 de entorno por cada 4 módulos, con tope)."},
        ],
    },
    {
        "id": "wall_stone",
        "nombre": "Muralla de sillería con almenas",
        "categoria": CAT,
        "descripcion": "Cortina de piedra labrada con zócalo, hiladas, cornisa de matacanes ciegos, adarve "
                       "enlosado y parapeto almenado a los dos lados (no hace falta saber qué lado es el de "
                       "fuera). Módulo de 2 m, adarve a 4 m, 5,1 m de alto total y 1,4 m de grueso." + RULE +
                       " La «escalera» ocupa 4 × 3 m y abre el parapeto interior.",
        "propuestas": [
            {"titulo": "Muralla de nivel 2",
             "detalle": "Sustituye al muro de piedra actual: 4 de piedra por módulo, 80 de trabajo, 1500 puntos "
                        "de vida, no arde. Se traza arrastrando y el juego coloca solo esquinas, uniones y "
                        "escalones de ladera."},
            {"titulo": "Arqueros en el adarve",
             "detalle": "Las unidades suben por la pieza de escalera o por una torre; arriba ganan +30 % de "
                        "alcance y reciben la mitad del daño a distancia tras las almenas."},
            {"titulo": "Daño por tramos",
             "detalle": "Cada módulo tiene su vida; al 30 % cambia a la pieza «brecha» y deja pasar. Repararla "
                        "cuesta 2 de piedra. El contrafuerte da +25 % de vida a sus dos vecinos."},
            {"titulo": "Luz en la noche",
             "detalle": "La pieza con brasero ilumina 10 m: las torres y la milicia no sufren el 75 % de daño "
                        "nocturno dentro de su luz. Gasta 1 de carbón o leña por noche."},
        ],
    },
    {
        "id": "wall_brick",
        "nombre": "Muralla de ladrillo con sillares",
        "categoria": CAT,
        "descripcion": "Paño de ladrillo en hiladas finas con zócalo, cornisa y albardillas de piedra clara. "
                       "Módulo de 2 m, adarve a 3 m, 4,1 m de alto total y 1,2 m de grueso." + RULE,
        "propuestas": [
            {"titulo": "Muralla para pueblos sin cantera",
             "detalle": "3 ladrillos y 1 de piedra por módulo, 1100 puntos de vida, no arde. Da salida al "
                        "ladrillo del horno cuando la piedra escasea en el mapa."},
            {"titulo": "Muralla urbana que embellece",
             "detalle": "Además de defender, suma entorno a las casas vecinas (+1 a 8 m), al contrario que la "
                        "empalizada, que lo resta."},
            {"titulo": "Recinto interior",
             "detalle": "Más baja que la sillería: pensada para un segundo anillo alrededor del centro del "
                        "pueblo, la bóveda y los almacenes."},
        ],
    },
    {
        "id": "wall_adobe",
        "nombre": "Tapia de adobe",
        "categoria": CAT,
        "descripcion": "Tapia de arcilla con zócalo de piedra, cabezas de viga, desconchones que dejan ver los "
                       "adobes y albardilla de tejas a dos aguas. Módulo de 2 m, 2,4 m de alto (2,7 m con la "
                       "albardilla) y 0,8 m de grueso en la base; sin adarve." + RULE,
        "propuestas": [
            {"titulo": "Muro de arcilla",
             "detalle": "3 de arcilla por módulo y 50 de trabajo, 600 puntos de vida, no arde. Aprovecha el "
                        "pozo de arcilla antes de tener horno de ladrillos."},
            {"titulo": "Se deshace con la lluvia",
             "detalle": "Pierde un poco de vida cada otoño y primavera si no tiene su albardilla de tejas "
                        "(1 de tejas por módulo la protege para siempre)."},
            {"titulo": "Muro propio de una raza",
             "detalle": "Variante de muralla para la raza de clima seco: más barata para ella y con mejor "
                        "aislamiento del calor para las casas pegadas al muro."},
        ],
    },
    {
        "id": "wall_iron",
        "nombre": "Muralla reforzada con hierro",
        "categoria": CAT,
        "descripcion": "Muralla alta de piedra oscura con tres zunchos de hierro remachados, albardillas de "
                       "hierro y púas sobre las almenas. Módulo de 2 m, adarve a 5 m, 6,1 m de alto total "
                       "(6,5 m con las púas) y 1,6 m de grueso." + RULE + " La «escalera» ocupa 6 × 3 m.",
        "propuestas": [
            {"titulo": "Muralla de nivel 3",
             "detalle": "Mejora de la muralla de piedra: +2 de piedra y 2 de hierro por módulo, 3000 puntos de "
                        "vida. Los arietes y las criaturas grandes le hacen la mitad de daño."},
            {"titulo": "No se puede escalar",
             "detalle": "Las púas impiden a los asaltantes con escalas subir al adarve: tienen que romper una "
                        "puerta o abrir brecha."},
            {"titulo": "Sumidero de hierro del final de la partida",
             "detalle": "Da un uso al hierro sobrante y suma «poder militar» a la puntuación por cada módulo."},
        ],
    },
    {
        "id": "wall_hedge",
        "nombre": "Seto vivo",
        "categoria": CAT,
        "descripcion": "Seto tupido con troncos en la base, flores y bayas. Módulo de 2 m, 1,8 m de alto y 0,9 m "
                       "de grueso; sin adarve." + RULE + " El «arco de paso» deja cruzar a los aldeanos.",
        "propuestas": [
            {"titulo": "Muro que crece solo",
             "detalle": "Se planta sin materiales (10 de trabajo por módulo) como «recién plantado» y tarda un "
                        "año en cerrarse. No cuesta nada, pero arde y solo tiene 200 puntos de vida."},
            {"titulo": "Adorno que da entorno y bayas",
             "detalle": "Suma entorno a las casas a 8 m y cada otoño el recolector saca 1 de bayas por cada "
                        "4 módulos."},
            {"titulo": "Barrera para la fauna",
             "detalle": "Detiene a los animales (conejos, ciervos, jabalíes) y frena a los asaltantes al 50 % "
                        "de velocidad en vez de bloquearlos."},
            {"titulo": "Muro propio de los elfos",
             "detalle": "La raza del bosque lo planta ya crecido y con espinas: daña a quien lo cruza."},
        ],
    },
    {
        "id": "wall_whitewash",
        "nombre": "Tapia encalada con tejas",
        "categoria": CAT,
        "descripcion": "Tapia de mampostería encalada con zócalo de piedra, albardilla de teja y pilastras con "
                       "remate en las uniones. Módulo de 2 m, 2,6 m de alto y 0,8 m de grueso; sin adarve." + RULE,
        "propuestas": [
            {"titulo": "Cerca de casas ricas y templos",
             "detalle": "2 de piedra y 1 de tejas por módulo. No es militar (500 puntos de vida): cierra patios "
                        "de casas de nivel 3, la capilla o el huerto del sanador y les suma entorno."},
            {"titulo": "Muro de barrio",
             "detalle": "Los incendios no saltan de un lado a otro de la tapia: sirve de cortafuegos entre "
                        "manzanas."},
        ],
    },
    {
        "id": "wall_cobble",
        "nombre": "Muro de mampostería",
        "categoria": CAT,
        "descripcion": "Muro macizo de piedra oscura en hiladas bajas, con albardilla clara y pilastras. Módulo "
                       "de 2 m, 2,4 m de alto y 0,9 m de grueso; sin adarve." + RULE,
        "propuestas": [
            {"titulo": "Muro de piedra sin adarve",
             "detalle": "3 de piedra por módulo, 1000 puntos de vida, no arde: el escalón intermedio entre la "
                        "empalizada y la muralla de sillería, sin subida para arqueros."},
            {"titulo": "Cerca de la mina y la cantera",
             "detalle": "El cantero lo levanta gratis alrededor de su cantera con el escombro: evita que los "
                        "aldeanos caigan y marca la zona de trabajo."},
        ],
    },
    # --- Walls of the fantasy races ----------------------------------------------------------
    {
        "id": "wall_dwarf",
        "nombre": "Muralla enana de granito",
        "categoria": CAT,
        "descripcion": "Muralla gruesa de granito oscuro en hiladas altas, con un zuncho de bronce remachado y "
                       "albardillas de bronce sobre las almenas. Módulo de 2 m, adarve a 4 m, 5,1 m de alto total "
                       "y 1,6 m de grueso." + RULE,
        "propuestas": [
            {"titulo": "Muralla propia de los enanos",
             "detalle": "Solo la construyen pueblos con enanos: 5 de piedra por módulo, 2200 puntos de vida "
                        "(+45 % sobre la sillería) y los enanos la levantan el doble de rápido."},
            {"titulo": "Lujo que puntúa",
             "detalle": "Las albardillas doradas cuestan 1 de oro por cada 10 módulos y suman prestigio a la "
                        "puntuación del pueblo; sin oro se construye igual, con albardilla de piedra."},
            {"titulo": "A prueba de zapa",
             "detalle": "Los enemigos que excavan (topos gigantes, zapadores) no pueden abrir brecha por debajo."},
        ],
    },
    {
        "id": "wall_elf",
        "nombre": "Muralla élfica de piedra blanca",
        "categoria": CAT,
        "descripcion": "Muralla esbelta de piedra blanca con una cinta dorada bajo el adarve y albardillas "
                       "verdes. Módulo de 2 m, adarve a 3,6 m, 4,7 m de alto total y 1 m de grueso." + RULE,
        "propuestas": [
            {"titulo": "Muralla propia de los elfos",
             "detalle": "3 de piedra por módulo y 1200 de vida: menos aguante que la sillería, pero los "
                        "arqueros elfos sobre ella ganan +50 % de alcance en vez de +30 %."},
            {"titulo": "Embellece en vez de afear",
             "detalle": "Da +2 de entorno a las casas a 10 m; es la única muralla que sube la felicidad."},
            {"titulo": "Se cubre de enredaderas",
             "detalle": "Con los años le crecen plantas: cada primavera recupera sola el 10 % de su vida."},
        ],
    },
    {
        "id": "wall_darkelf",
        "nombre": "Muralla de los elfos oscuros",
        "categoria": CAT,
        "descripcion": "Muralla alta de piedra violácea casi negra, con albardillas de plata y púas sobre las "
                       "almenas. Módulo de 2 m, adarve a 4,4 m, 5,5 m de alto total y 1,2 m de grueso." + RULE,
        "propuestas": [
            {"titulo": "Muralla propia de los elfos oscuros",
             "detalle": "4 de piedra y 1 de hierro por módulo, 1800 de vida. De noche sus defensores no "
                        "sufren la penalización de oscuridad (la raza ve en la noche)."},
            {"titulo": "Intimida",
             "detalle": "Los grupos pequeños de asaltantes (menos de 6) dan media vuelta al verla si el "
                        "pueblo tiene más poder militar que ellos."},
        ],
    },
    {
        "id": "wall_sandstone",
        "nombre": "Muralla de arenisca",
        "categoria": CAT,
        "descripcion": "Muralla de arenisca dorada con hiladas marcadas y almenas. Módulo de 2 m, adarve a 3,6 m, "
                       "4,7 m de alto total y 1,4 m de grueso." + RULE,
        "propuestas": [
            {"titulo": "La muralla del bioma seco",
             "detalle": "Misma función que la sillería (4 de piedra, 1500 de vida) con el aspecto de la piedra "
                        "del desierto: el juego elige el aspecto según el bioma de la cantera."},
            {"titulo": "Muralla propia de los hombres lagarto",
             "detalle": "Para la raza de clima cálido: las casas pegadas a ella no pasan calor en verano."},
        ],
    },
    {
        "id": "wall_foxfolk",
        "nombre": "Muralla blanca de la gente zorro",
        "categoria": CAT,
        "descripcion": "Muralla enlucida de blanco sobre un zócalo de madera oscura, con albardillas de laca "
                       "roja sobre las almenas y adarve de tablas; sus torres llevan tejado de pizarra. Módulo de "
                       "2 m, adarve a 3,2 m, 4,3 m de alto total y 1 m de grueso." + RULE,
        "propuestas": [
            {"titulo": "Muralla propia de la gente zorro",
             "detalle": "2 de piedra, 2 troncos y 1 de tejas por módulo, 1000 puntos de vida. El enlucido "
                        "no arde, pero el zócalo y el adarve de madera sí pueden quemarse."},
            {"titulo": "Elegante",
             "detalle": "Da +1 de entorno a las casas a 8 m y los mercaderes pagan un 5 % más en un pueblo "
                        "rodeado por ella (prestigio)."},
        ],
    },
    {
        "id": "wall_catfolk",
        "nombre": "Muralla de adobe y azulejo de la gente gato",
        "categoria": CAT,
        "descripcion": "Muralla de adobe claro con una cenefa de azulejo azul bajo el adarve y albardillas "
                       "azules; sus torres llevan tejado de teja vidriada azul. Módulo de 2 m, adarve a 3,4 m, "
                       "4,5 m de alto total y 1,2 m de grueso." + RULE,
        "propuestas": [
            {"titulo": "Muralla propia de la gente gato",
             "detalle": "4 de arcilla y 1 de tejas por módulo, 1200 puntos de vida, no arde: una muralla con "
                        "adarve para pueblos que tienen arcilla y no piedra."},
            {"titulo": "Fresca",
             "detalle": "Las casas pegadas a la muralla gastan la mitad de leña en invierno y no sufren el "
                        "calor del verano."},
        ],
    },
    {
        "id": "wall_orc",
        "nombre": "Empalizada orca",
        "categoria": CAT,
        "descripcion": "Troncos oscuros y desiguales con puntas descortezadas, planchas de chatarra clavadas, púas "
                       "de hierro hacia los dos lados, una franja de pintura de guerra y postes con calavera "
                       "cornuda. Módulo de 2 m, de 2,6 a 3,4 m de alto y 0,4 m de grueso; sin adarve." + RULE,
        "propuestas": [
            {"titulo": "Empalizada propia de los orcos",
             "detalle": "4 troncos y 1 de mineral de hierro por módulo, 550 de vida. Las púas devuelven 10 de "
                        "daño a quien la golpea cuerpo a cuerpo."},
            {"titulo": "Campamento de asaltantes",
             "detalle": "Es el muro de los campamentos enemigos que el explorador encuentra en el mapa: "
                        "destruirlo con soldados da botín."},
            {"titulo": "Asusta a los vecinos",
             "detalle": "Resta 1 de entorno a las casas de otras razas a 8 m y suma 1 a las de los orcos."},
        ],
    },
    {
        "id": "wall_reed",
        "nombre": "Cerca de cañas sobre barro",
        "categoria": CAT,
        "descripcion": "Dos filas de cañas gruesas atadas con cuerda sobre un caballón de barro, con haces de "
                       "tres cañas en las uniones. Módulo de 2 m, 2,4 m de alto y 0,5 m de grueso; sin adarve." +
                       RULE,
        "propuestas": [
            {"titulo": "Muro propio de la gente rana",
             "detalle": "Se construye solo junto al agua o en pantano, con 2 de arcilla por módulo y las cañas "
                        "de la orilla: 300 de vida, no se pudre con la humedad."},
            {"titulo": "Recurso nuevo: cañas",
             "detalle": "Introduce las cañas, que el recolector corta en las orillas y también sirven para "
                        "techos de paja y cestas."},
            {"titulo": "Dique",
             "detalle": "Una línea continua protege de las crecidas de primavera a los campos que tiene detrás."},
        ],
    },
    {
        "id": "wall_ruin",
        "nombre": "Ruinas de una muralla antigua",
        "categoria": "Campamento y exploración",
        "descripcion": "Restos de una fortificación vieja, cubiertos de musgo y hiedra: un tramo de muro "
                       "desmochado, una esquina, el arco de una puerta de 4 m sin hojas y el muñón de una torre "
                       "redonda con un árbol dentro. Usan el módulo de 2 m para poder alinearse en el mapa.",
        "propuestas": [
            {"titulo": "Hallazgo del explorador",
             "detalle": "El generador de mapas siembra ruinas; al descubrirlas el explorador encuentra un "
                        "botín único (oro, herramientas o un plano que desbloquea la muralla de sillería)."},
            {"titulo": "Cantera de sillares",
             "detalle": "Se pueden desmontar: cada pieza da de 6 a 20 de piedra ya labrada sin cantero, pero "
                        "el lugar pierde su valor de entorno."},
            {"titulo": "Reconstruir en vez de construir",
             "detalle": "Una ruina se puede restaurar a muralla o torre por la mitad del coste: premia fundar "
                        "el pueblo junto a ellas."},
            {"titulo": "Guarida",
             "detalle": "Las ruinas sin explorar son refugio de lobos o de un campamento de asaltantes."},
        ],
    },
    # --- Gates -------------------------------------------------------------------------------
    {
        "id": "gate_double",
        "nombre": "Puerta de dos hojas (4 m)",
        "categoria": CAT,
        "descripcion": "Puerta de 4 × 2 m con dos hojas sobre goznes en los postes, una por cada tipo de muro. Sus "
                       "extremos repiten la sección del muro, así que se coloca en medio de un tramo recto. En los "
                       "muros con adarve, la pasarela cruza por encima de las hojas (sube tres escalones si el "
                       "muro es bajo) y dos braseros flanquean la entrada; las de cercado bajo son cancelas.",
        "propuestas": [
            {"titulo": "Se cierra al sonar la campana",
             "detalle": "Abierta deja pasar a aldeanos, carretas y mercaderes; al tocar la campana se cierra sola "
                        "(clip «close») cuando el último aldeano ha entrado y solo vuelve a abrirse al acabar la "
                        "alarma."},
            {"titulo": "El punto débil del muro",
             "detalle": "Tiene la mitad de vida que dos módulos de su muro (600 la de troncos, 2000 la de "
                        "sillería, 4000 la de hierro): los asaltantes la buscan primero, y por eso conviene "
                        "flanquearla con torres."},
            {"titulo": "Peaje y aduana",
             "detalle": "Los mercaderes que entran por una puerta pagan 1 moneda de portazgo; el jugador puede "
                        "marcar una puerta como «solo aldeanos» para desviar las carretas."},
            {"titulo": "Mejora con el muro",
             "detalle": "Al mejorar el muro vecino de troncos a piedra, la puerta se mejora por el mismo coste "
                        "que 2 módulos, sin dejar el hueco abierto durante la obra."},
        ],
    },
    {
        "id": "gate_postern",
        "nombre": "Poterna (puerta pequeña de 2 m)",
        "categoria": CAT,
        "descripcion": "Módulo de muro de 2 m con una puerta de 0,95 × 1,75 m que atraviesa el muro; en los "
                       "cercados bajos es un portillo. Ocupa una sola celda y sigue la regla de conexión del recto.",
        "propuestas": [
            {"titulo": "Paso solo para aldeanos",
             "detalle": "Deja pasar a los aldeanos y a los animales pequeños pero no a carretas ni mercaderes: "
                        "acorta los caminos al campo sin abrir un hueco de 4 m. Cuesta lo que un módulo más "
                        "2 troncos."},
            {"titulo": "Salida de la milicia",
             "detalle": "Durante un asalto los soldados pueden salir por ella aunque las puertas grandes estén "
                        "cerradas; los asaltantes no la usan mientras tenga vida."},
            {"titulo": "Mismo aguante que el muro",
             "detalle": "Tiene el 80 % de la vida de un módulo recto: no crea el punto débil de una puerta grande."},
        ],
    },
    {
        "id": "gate_gatehouse",
        "nombre": "Torre-puerta con rastrillo",
        "categoria": CAT,
        "descripcion": "Casa de puerta de 6 × 4 m y unos 7,5 m de alto con pasadizo de 2,8 m, rastrillo de hierro "
                       "que sube por una ranura, torno en la azotea, puertas laterales a la altura del adarve y "
                       "dos braseros. El muro llega al centro de sus lados cortos.",
        "propuestas": [
            {"titulo": "Puerta de nivel 2",
             "detalle": "Mejora de la puerta de piedra: 20 de piedra y 6 de hierro, 3500 puntos de vida. El "
                        "rastrillo baja en 3 s al sonar la campana, mucho antes que unas hojas."},
            {"titulo": "Puerta que dispara",
             "detalle": "Admite 2 arqueros en la azotea: ataca como media torre de vigía a quien golpee el "
                        "rastrillo."},
            {"titulo": "Pasadizo trampa",
             "detalle": "Los asaltantes que rompen el rastrillo quedan 4 s en el pasadizo recibiendo daño de "
                        "las buhederas antes de entrar al pueblo."},
        ],
    },
    {
        "id": "gate_drawbridge",
        "nombre": "Torre-puerta con puente levadizo",
        "categoria": CAT,
        "descripcion": "La torre-puerta de 6 × 4 m con un puente levadizo de 4 m colgado de cadenas, pensado para "
                       "cruzar el foso. Abrir baja el puente y sube el rastrillo; cerrar hace lo contrario.",
        "propuestas": [
            {"titulo": "Pareja del foso",
             "detalle": "Es la única forma de cruzar un foso: con el puente levantado no hay camino y los "
                        "asaltantes sin escalas tienen que rodear. Cuesta lo que la torre-puerta más 8 troncos "
                        "y 2 de hierro."},
            {"titulo": "Cierre total",
             "detalle": "Con el puente arriba la puerta no puede recibir golpes de ariete: solo daño a "
                        "distancia."},
        ],
    },
    {
        "id": "gate_arch",
        "nombre": "Arco de paso sin puertas (4 m)",
        "categoria": CAT,
        "descripcion": "El hueco de 4 × 2 m de cada muro sin hojas: un arco empedrado por el que pasa un camino, "
                       "con el adarve cruzando por encima en los muros que lo tienen.",
        "propuestas": [
            {"titulo": "Paso para caminos en muros interiores",
             "detalle": "Cuesta lo que 2 módulos de su muro, sin madera ni hierro. No se cierra: sirve para "
                        "dividir barrios o cruzar un camino bajo una muralla vieja sin crear un cuello de "
                        "botella en la puerta."},
            {"titulo": "Mejorable a puerta",
             "detalle": "Se le pueden añadir las hojas después (10 troncos): el jugador decide más tarde qué "
                        "pasos se cierran al sonar la campana."},
            {"titulo": "Arco triunfal",
             "detalle": "Suelto en una plaza, sin muro a los lados, cuenta como monumento: +2 de entorno a "
                        "10 m."},
        ],
    },
    {
        "id": "gate_broken",
        "nombre": "Puerta rota (estado de daño)",
        "categoria": CAT,
        "descripcion": "La puerta de dos hojas de cada muro después de un asalto: una hoja cuelga de un gozne, "
                       "la otra está caída dentro, hay astillas y escombro y queda la cabeza del ariete.",
        "propuestas": [
            {"titulo": "Estado visible de la puerta",
             "detalle": "Cuando la vida de la puerta llega a cero no desaparece: cambia a este modelo, deja "
                        "pasar a todos y se repara por la mitad de su coste en vez de construirla de nuevo."},
            {"titulo": "Aviso para el jugador",
             "detalle": "Una puerta rota salta como notificación y se marca en el minimapa hasta que un "
                        "constructor la repara."},
        ],
    },
    {
        "id": "gate_twin",
        "nombre": "Puerta entre dos torres",
        "categoria": CAT,
        "descripcion": "Puerta de 8 × 4 m: dos torres redondas esbeltas de 2,6 m de diámetro con tejado cónico, "
                       "y entre ellas un rastrillo, dos hojas y el adarve por encima. Las torres tienen puertas "
                       "al adarve del muro a los dos lados.",
        "propuestas": [
            {"titulo": "La gran puerta del pueblo",
             "detalle": "Puerta de nivel 3: 30 de piedra, 8 troncos y 6 de hierro, 5000 puntos de vida. Tiene "
                        "dos cierres (rastrillo y hojas): los asaltantes deben romper los dos."},
            {"titulo": "Cuatro arqueros",
             "detalle": "Cada torre aloja 2 arqueros que cubren la entrada: equivale a dos torres de vigía y "
                        "una puerta en la mitad de sitio."},
            {"titulo": "Entrada de mercaderes",
             "detalle": "Las caravanas prefieren esta puerta: un pueblo con ella recibe un mercader más al "
                        "año y sube su prestigio."},
        ],
    },
    {
        "id": "gate_water",
        "nombre": "Puerta de agua",
        "categoria": CAT,
        "descripcion": "Tramo de muralla de 4 × 2 m sobre un canal de 3 m: un arco con tajamares cerrado por una "
                       "reja de hierro que sube, con el adarve pasando por encima y dos braseros.",
        "propuestas": [
            {"titulo": "La muralla cruza ríos",
             "detalle": "Permite cerrar el recinto donde lo corta un río o un canal: el agua y las barcas de "
                        "pesca pasan, los asaltantes no. 8 de piedra y 4 de hierro."},
            {"titulo": "Entrada del foso",
             "detalle": "Conecta el foso con el río para llenarlo; con la reja bajada el nivel se mantiene."},
            {"titulo": "Muelle protegido",
             "detalle": "Un muelle o una pesquería dentro de la muralla siguen funcionando durante un asedio."},
        ],
    },
    {
        "id": "gate_wood_gatehouse",
        "nombre": "Puerta de madera con cuerpo de guardia",
        "categoria": CAT,
        "descripcion": "Puerta de 4 × 4 m para empalizadas y muros de tablas: cuatro postes de tronco, pasadizo "
                       "forrado de tablas, dos hojas, un cuarto de guardia con parapeto a 3,7 m y tejado a cuatro "
                       "aguas (paja, tejas o, en la orca, cuero y calaveras). Se sube por una escalera de mano.",
        "propuestas": [
            {"titulo": "Puerta de empalizada de nivel 2",
             "detalle": "14 troncos y 2 de hierro, 900 puntos de vida. Dos arqueros arriba disparan a quien "
                        "golpea las hojas; al sonar la campana se cierra sola."},
            {"titulo": "Puesto de guardia",
             "detalle": "Con un soldado asignado inspecciona a los mercaderes: reduce a la mitad el riesgo de "
                        "que entre una enfermedad con una caravana."},
            {"titulo": "Puerta de los campamentos orcos",
             "detalle": "La variante orca es la entrada de los campamentos de asaltantes del mapa: romperla "
                        "abre el campamento al saqueo."},
        ],
    },
    # --- Towers ------------------------------------------------------------------------------
    {
        "id": "tower_building",
        "nombre": "Torre en construcción y torre dañada",
        "categoria": CAT,
        "descripcion": "Dos estados de la torre cuadrada, en sus mismos 4 × 4 m. En construcción: a media "
                       "altura, con andamios en dos caras, una cabria que sube un sillar, la hilada a medio poner "
                       "y piedra y artesa de mortero al pie. Dañada: sin almenas en dos lados, con un boquete en "
                       "el frente, vigas quemadas y escombro.",
        "propuestas": [
            {"titulo": "Obra visible de las torres",
             "detalle": "Sustituye al solar genérico mientras se construye una torre de piedra: el jugador ve "
                        "cuánto falta y la obra ya bloquea el paso y da la mitad de la vida final."},
            {"titulo": "Etapas de mejora",
             "detalle": "También se muestra al mejorar una torre de madera a piedra, sin dejar el hueco "
                        "abierto en el muro."},
            {"titulo": "Daño visible",
             "detalle": "Por debajo del 30 % de vida la torre cambia al modelo dañado: deja de disparar, "
                        "sigue cerrando el muro y se repara por un tercio de su coste."},
        ],
    },
    {
        "id": "tower_mural",
        "nombre": "Torre semicircular adosada",
        "categoria": CAT,
        "descripcion": "Torre de media luna de 4 m de ancho que sobresale 1,9 m de un tramo recto de muralla, "
                       "2,2 m más alta que su adarve, con almenas, aspilleras, puerta al patio, brasero y "
                       "banderín. Sustituye a dos módulos rectos (4 × 3 m) sin cortar el adarve.",
        "propuestas": [
            {"titulo": "Torre barata a mitad de lienzo",
             "detalle": "10 de piedra: la mitad que una torre completa. Da alcance y visión de torre (30 m) y "
                        "flanquea el pie del muro a los dos lados; el juego la ofrece cada 8 módulos al trazar "
                        "murallas largas."},
            {"titulo": "Refuerzo de un tramo",
             "detalle": "Los 3 módulos de muro a cada lado ganan +20 % de vida: sirve para reforzar el punto "
                        "por donde suelen llegar los asaltos."},
        ],
    },
    {
        "id": "tower_bell",
        "nombre": "Torre de la campana",
        "categoria": CAT,
        "descripcion": "Torre esbelta de 3 × 3 m: fuste de 8 m con zócalo y aspilleras, campanario abierto de "
                       "cuatro pilares con una gran campana que voltea, y tejado a cuatro aguas (13,5 m en total).",
        "propuestas": [
            {"titulo": "La campana del pueblo, como edificio",
             "detalle": "Hoy la campana es un botón: con esta torre es un edificio (12 de piedra, 4 troncos y "
                        "2 de hierro). Al tocarla, los aldeanos a 60 m dejan el trabajo, la milicia toma las "
                        "armas y las puertas se cierran."},
            {"titulo": "Varias campanas, varios barrios",
             "detalle": "Cada torre avisa a su barrio: se puede dar la alarma solo en la zona atacada y "
                        "dejar que el resto del pueblo siga trabajando."},
            {"titulo": "Marca las horas",
             "detalle": "Con un campanero asignado, los aldeanos de su radio empiezan y terminan la jornada "
                        "a la vez: +5 % de trabajo y +1 de felicidad."},
        ],
    },
    {
        "id": "tower_beacon",
        "nombre": "Torre de señales",
        "categoria": CAT,
        "descripcion": "Torre esbelta de 3 × 3 m y 10 m de alto con una gran hoguera en una jaula de hierro, o un "
                       "trípode de troncos de 6 m con su hoguera y escalera de mano.",
        "propuestas": [
            {"titulo": "Cadena de avisos",
             "detalle": "Al ver asaltantes se enciende y enciende las torres de señales que la ven: el aviso "
                        "llega al pueblo desde puestos lejanos (minas, pesquerías) y da hasta 60 s más para "
                        "cerrar puertas. 10 de piedra; gasta 2 de leña por alarma."},
            {"titulo": "Faro",
             "detalle": "Junto al mar o a un río guía a las barcas de noche y con niebla: los pescadores "
                        "faenan también en esas horas."},
            {"titulo": "Luz de barrio",
             "detalle": "Encendida de noche ilumina 25 m: nadie tropieza ni sufre la penalización de "
                        "oscuridad en esa zona."},
        ],
    },
    {
        "id": "tower_square",
        "nombre": "Torre cuadrada de mampostería",
        "categoria": CAT,
        "descripcion": "Torre de 4 × 4 m que se centra sobre un nudo del muro (una esquina, una T o en medio de "
                       "un tramo): el muro entra 1 m en ella y se remata con el medio módulo. Zócalo ataluzado, "
                       "sillares en las esquinas, matacanes, almenas, aspilleras, puerta al patio y puertas al "
                       "adarve a la altura del muro de su material (4 m en sillería, 3 m en ladrillo, 5 m en "
                       "hierro). Abierta con brasero y banderín, o con tejado a cuatro aguas.",
        "propuestas": [
            {"titulo": "Torre de vigía de nivel 2",
             "detalle": "Mejora de la torre actual: 16 de piedra y 6 troncos, 2000 puntos de vida, alcance 34 m, "
                        "visión 50 m, no arde. Da paso entre los adarves de los muros que llegan a ella."},
            {"titulo": "Guarnición",
             "detalle": "Admite hasta 3 arqueros de la milicia o del cuartel; cada uno añade un disparo por "
                        "ciclo. Vacía solo vigila."},
            {"titulo": "Con tejado: protegida de la noche y la lluvia",
             "detalle": "La variante con tejado cuesta 4 de tejas más y sus arqueros no sufren la penalización "
                        "de oscuridad ni la del invierno; la abierta lleva brasero e ilumina 12 m."},
        ],
    },
    {
        "id": "tower_round",
        "nombre": "Torre redonda de mampostería",
        "categoria": CAT,
        "descripcion": "Torre cilíndrica de 3,7 m de diámetro (planta de 4 × 4 m) con zócalo, hiladas, corona de "
                       "almenas, aspilleras y puertas al adarve. Se coloca como la cuadrada. Abierta o con tejado "
                       "cónico de tejas.",
        "propuestas": [
            {"titulo": "Torre de esquina resistente",
             "detalle": "Los proyectiles de asedio le hacen un 30 % menos de daño que a la cuadrada y no tiene "
                        "ángulos muertos: dispara en los 360°. Cuesta 20 de piedra."},
            {"titulo": "Elección estética",
             "detalle": "Mismas cifras que la cuadrada; el jugador elige la forma al construir, como con los "
                        "estilos de casa."},
        ],
    },
    {
        "id": "tower_wood",
        "nombre": "Torres de madera",
        "categoria": CAT,
        "descripcion": "Dos torres de 4 × 4 m para empalizadas y muros de tablas: la cuadrada (postes de tronco, "
                       "cuarto de tablas abajo, cruces de San Andrés y plataforma con parapeto a 5 m) y la redonda "
                       "(tambor de troncos apuntados atados con cuerda, plataforma a 4,6 m). Abiertas con brasero "
                       "o con techo de paja; la redonda tiene una variante orca con púas, zunchos de hierro y "
                       "pintura de guerra, y hay una atalaya de cañas sobre ocho pilotes para la gente rana.",
        "propuestas": [
            {"titulo": "Torre de vigía mejorada",
             "detalle": "Sustituye a la torre actual (16 troncos y 4 de piedra, 800 de vida, alcance 30 m) y "
                        "encaja en la empalizada: el muro termina en ella sin dejar hueco."},
            {"titulo": "El techo de paja arde",
             "detalle": "La variante con techo protege a los arqueros de la lluvia y la nieve, pero las flechas "
                        "incendiarias la prenden; la abierta no."},
            {"titulo": "Almacén de flechas",
             "detalle": "El cuarto de abajo guarda 20 flechas del arquero: la torre no dispara sin munición y "
                        "un aldeano la repone desde el almacén."},
        ],
    },
    {
        "id": "tower_bastion",
        "nombre": "Bastión de esquina",
        "categoria": CAT,
        "descripcion": "Plataforma octogonal ataluzada de 6 m de ancho, a la altura del adarve de su muro, con "
                       "troneras anchas, brasero, banderín y piedras apiladas. Se centra en una esquina del muro.",
        "propuestas": [
            {"titulo": "Plataforma para máquinas",
             "detalle": "Admite una balista o una catapulta encima (la torre normal no): 24 de piedra, 3000 de "
                        "vida."},
            {"titulo": "Flanqueo",
             "detalle": "Las unidades sobre el bastión hacen +25 % de daño a los enemigos pegados a los dos "
                        "muros que salen de él."},
        ],
    },
    {
        "id": "tower_keep",
        "nombre": "Torre del homenaje",
        "categoria": "Castillos y fortalezas",
        "descripcion": "Torre de 6 × 6 m y 11 m hasta la azotea (16 m con el tejado), con zócalo ataluzado, "
                       "garitas colgadas en las cuatro esquinas, sala alta bajo tejado a cuatro aguas, escalinata "
                       "y estandarte que ondea.",
        "propuestas": [
            {"titulo": "Último refugio",
             "detalle": "Al sonar la campana, los aldeanos que no son milicia se refugian dentro (hasta 30) en "
                        "vez de en sus casas; mientras resista, no hay bajas civiles. 60 de piedra, 20 troncos "
                        "y 10 de hierro, 6000 de vida."},
            {"titulo": "Mejora del centro del pueblo",
             "detalle": "Tercer nivel del centro del pueblo: amplía la visión a 70 m, permite tener un capitán "
                        "y suma «poder militar» a la puntuación."},
            {"titulo": "Bóveda segura",
             "detalle": "Guarda el oro como la bóveda: los asaltantes no pueden llevárselo mientras la torre "
                        "siga en pie."},
        ],
    },
    {
        "id": "tower_ballista",
        "nombre": "Torre de balista",
        "categoria": CAT,
        "descripcion": "Torre cuadrada de 4 × 4 m, algo más baja, con una balista sobre plataforma giratoria y "
                       "virotes de repuesto; también en madera. La balista gira (clip «aim») y dispara («fire»).",
        "propuestas": [
            {"titulo": "Daño fuerte y lento",
             "detalle": "Dispara un virote cada 6 s con 250 de daño y 45 m de alcance, que atraviesa a dos "
                        "enemigos en línea; ideal contra criaturas grandes. Cuesta 12 de piedra, 8 troncos y "
                        "4 de hierro, y gasta 1 de hierro cada 20 disparos."},
            {"titulo": "Necesita un operario",
             "detalle": "Solo dispara con un soldado asignado (oficio «artillero»); sin él es una torre de "
                        "vigía sin ataque."},
            {"titulo": "Alcance mínimo",
             "detalle": "No puede apuntar a menos de 8 m: conviene cubrir su pie con una torre de arqueros."},
        ],
    },
    # --- Fences ------------------------------------------------------------------------------
    {
        "id": "fence_rail",
        "nombre": "Cerca de palos",
        "categoria": CAT,
        "descripcion": "Postes de madera con tres travesaños redondos. Módulo de 2 m con un poste en el centro de "
                       "cada celda, 1,2 m de alto; se conecta con la misma regla que los muros (recto, esquina, "
                       "T, cruce, remate, escalón y cancela de una hoja).",
        "propuestas": [
            {"titulo": "Cercado de pasto",
             "detalle": "Un recinto cerrado de cerca con una cancela se convierte en pasto: los animales del "
                        "establo pastan dentro sin pastor y rinden un 20 % más. 1 tronco por cada 2 módulos."},
            {"titulo": "Proteger los campos",
             "detalle": "Los ciervos y jabalíes no entran a comerse la cosecha de un campo rodeado; los "
                        "aldeanos cruzan por la cancela."},
            {"titulo": "Guía de caminos",
             "detalle": "Los aldeanos no cruzan una cerca: sirve para obligarlos a usar el camino en vez de "
                        "pisar los huertos."},
        ],
    },
    {
        "id": "fence_picket",
        "nombre": "Valla de estacas pintadas",
        "categoria": "Anexos de casas",
        "descripcion": "Valla de estacas blancas con punta sobre dos largueros, de 1 m de alto, con postes "
                       "rematados. Módulo de 2 m y la misma regla de conexión; cancela de una hoja.",
        "propuestas": [
            {"titulo": "Jardín de casa",
             "detalle": "Rodear una casa con valla (mínimo 6 módulos) le da +2 de entorno y un huerto propio "
                        "que produce 1 de verdura por estación."},
            {"titulo": "Adorno de nivel 2",
             "detalle": "Se desbloquea con las casas de nivel 2; cuesta 1 tronco cada 2 módulos y cuenta como "
                        "decoración para la felicidad del barrio."},
            {"titulo": "Gallinero",
             "detalle": "Un recinto de valla junto a una casa admite gallinas: huevos sin oficio asignado."},
        ],
    },
    {
        "id": "fence_wattle",
        "nombre": "Cerca de zarzo",
        "categoria": CAT,
        "descripcion": "Varas trenzadas entre estacas, de 1,05 m de alto. Módulo de 2 m y la misma regla de "
                       "conexión; cancela de travesaños.",
        "propuestas": [
            {"titulo": "La cerca del primer año",
             "detalle": "No gasta troncos: se hace con 1 de leña cada 2 módulos o gratis con 15 de "
                        "trabajo por módulo. Dura 3 años y se pudre si no se repara."},
            {"titulo": "Corral de animales pequeños",
             "detalle": "Encierra ovejas, cabras y cerdos (las vacas la rompen): permite ganadería antes de "
                        "tener establo."},
            {"titulo": "Paraviento del huerto",
             "detalle": "Un campo rodeado de zarzo pierde la mitad de cosecha con las heladas y los vendavales."},
        ],
    },
    {
        "id": "fence_stone",
        "nombre": "Murete de piedra seca",
        "categoria": CAT,
        "descripcion": "Murete de 0,75 m de alto y 0,5 m de grueso con mojones cuadrados en las uniones. Módulo "
                       "de 2 m y la misma regla de conexión; cancela de travesaños.",
        "propuestas": [
            {"titulo": "Despedregar los campos",
             "detalle": "Se construye con la piedra suelta que el labrador saca al preparar un campo: gratis "
                        "si hay un campo a menos de 10 m. No arde ni se pudre."},
            {"titulo": "Bancal en laderas",
             "detalle": "En pendiente funciona como bancal: el campo de detrás cuenta como terreno llano."},
            {"titulo": "Cercado permanente",
             "detalle": "Pasto para cualquier animal, incluidas las vacas; 1 de piedra por módulo."},
        ],
    },
    {
        "id": "fence_iron",
        "nombre": "Verja de hierro",
        "categoria": CAT,
        "descripcion": "Barrotes con punta de lanza sobre un zócalo de piedra, entre pilares con bola. 1,6 m de "
                       "alto, módulo de 2 m y la misma regla de conexión; cancela de barrotes.",
        "propuestas": [
            {"titulo": "Cerca noble",
             "detalle": "1 de hierro y 1 de piedra por cada 2 módulos. Da +3 de entorno a las casas de nivel 3, "
                        "la capilla, la bóveda y el cementerio."},
            {"titulo": "Barrera que deja ver",
             "detalle": "Bloquea el paso como un muro bajo (800 de vida) pero no tapa la visión ni los disparos "
                        "de las torres."},
            {"titulo": "Recinto de la bóveda",
             "detalle": "Una bóveda rodeada de verja tarda el doble en ser saqueada."},
        ],
    },
    {
        "id": "fence_brick",
        "nombre": "Murete de ladrillo",
        "categoria": "Anexos de casas",
        "descripcion": "Murete de ladrillo de 0,9 m con albardilla de piedra y pilastras con remate. Módulo de "
                       "2 m y la misma regla de conexión; cancela de barrotes de hierro.",
        "propuestas": [
            {"titulo": "Patio de casa de nivel 3",
             "detalle": "1 ladrillo por módulo. Un patio cerrado delante de la casa le da +2 de entorno y "
                        "sitio para un anexo (pozo, banco, tendedero)."},
            {"titulo": "Cortafuegos bajo",
             "detalle": "El fuego no salta entre dos edificios separados por el murete."},
        ],
    },
    {
        "id": "fence_rope",
        "nombre": "Cerca de postes y cuerda",
        "categoria": CAT,
        "descripcion": "Postes bajos unidos por dos cuerdas que cuelgan. Módulo de 2 m, 1 m de alto y la misma "
                       "regla de conexión; cancela de travesaños.",
        "propuestas": [
            {"titulo": "Marcar zonas sin bloquear",
             "detalle": "No bloquea a nadie: delimita el mercado, la plaza de la feria o un campo de "
                        "entrenamiento. 1 tronco y 1 de lino cada 4 módulos."},
            {"titulo": "Cercado de caballos",
             "detalle": "Suficiente para caballos y bueyes mansos junto al puesto de comercio o el establo."},
        ],
    },
    {
        "id": "fence_boxhedge",
        "nombre": "Seto bajo recortado",
        "categoria": "Anexos de casas",
        "descripcion": "Seto recortado de 0,9 m con bolas de topiaria en las uniones. Módulo de 2 m y la misma "
                       "regla de conexión; cancela de estacas blancas.",
        "propuestas": [
            {"titulo": "Jardín formal",
             "detalle": "Sin materiales, 8 de trabajo por módulo. Da +1 de entorno a 6 m y, alrededor del "
                        "jardín o de la estatua, duplica su efecto."},
            {"titulo": "Mantenimiento",
             "detalle": "Si nadie lo recorta una vez al año (tarea del jardinero o de un aldeano ocioso) "
                        "crece hasta ser el seto vivo alto."},
        ],
    },
    # --- Defenses ----------------------------------------------------------------------------
    {
        "id": "defense_ballista",
        "nombre": "Balista de campaña",
        "categoria": CAT,
        "descripcion": "Balista sobre un carro de cuatro ruedas; gira («aim») y dispara («fire»). Ocupa 2 × 3 m.",
        "propuestas": [
            {"titulo": "Máquina móvil",
             "detalle": "La construye el herrero (6 troncos y 3 de hierro) y dos soldados la empujan a donde "
                        "haga falta: 250 de daño cada 6 s a 45 m."},
            {"titulo": "Sobre el bastión",
             "detalle": "Subida a un bastión gana +10 m de alcance y queda protegida del cuerpo a cuerpo."},
        ],
    },
    {
        "id": "defense_catapult",
        "nombre": "Catapulta",
        "categoria": CAT,
        "descripcion": "Catapulta de torsión sobre cuatro ruedas, de 2 × 3,5 m, con torno, viga de tope "
                       "acolchada y piedras de repuesto. «fire» lanza la piedra; «reload» baja el brazo.",
        "propuestas": [
            {"titulo": "Daño en área contra grupos",
             "detalle": "10 troncos, 4 de hierro y 2 de cuero. Lanza 1 de piedra cada 12 s a 60 m con 200 de "
                        "daño en 3 m de radio; no acierta a blancos que se mueven rápido."},
            {"titulo": "Contra campamentos",
             "detalle": "Es la única forma de derribar las empalizadas de un campamento de asaltantes sin "
                        "perder soldados."},
            {"titulo": "Arma de los asaltantes de final de partida",
             "detalle": "En dificultad brutal los asaltos traen una: obliga a tener murallas de piedra y a "
                        "salir a destruirla."},
        ],
    },
    {
        "id": "defense_abatis",
        "nombre": "Tala (abatis)",
        "categoria": CAT,
        "descripcion": "Tres árboles talados y sujetos con estacas, con las ramas afiladas hacia el enemigo. "
                       "Tramo de 2 m de ancho y 3 m de fondo.",
        "propuestas": [
            {"titulo": "Obstáculo del leñador",
             "detalle": "El leñador lo deja al talar si se le marca una línea: no cuesta troncos (usa los "
                        "árboles enteros del sitio) y frena a los asaltantes al 40 %. Arde con facilidad."},
            {"titulo": "Defensa de emergencia",
             "detalle": "Se levanta en 10 de trabajo cuando ya suena la campana, para cerrar un camino del "
                        "bosque; pasado el asalto se recoge como 2 troncos."},
        ],
    },
    {
        "id": "defense_siege_ram",
        "nombre": "Ariete cubierto",
        "categoria": CAT,
        "descripcion": "Ariete de 2 × 4,5 m sobre cuatro ruedas: un tronco con cabeza de hierro colgado de cuerdas "
                       "bajo un tejadillo de tablas y pieles. El tronco toma impulso y golpea (clip «ram»).",
        "propuestas": [
            {"titulo": "Máquina de los asaltos grandes",
             "detalle": "Desde dificultad alta, los asaltos de más de 15 enemigos traen uno: hace 200 de daño "
                        "por golpe a puertas y empalizadas y su techo protege a quienes lo empujan de las "
                        "flechas. Lo paran el aceite hirviendo, el foso y el puente levadizo."},
            {"titulo": "Para asaltar campamentos",
             "detalle": "El jugador también puede construirlo (8 troncos, 2 de hierro, 2 de cuero) para abrir "
                        "las puertas de los campamentos de asaltantes."},
        ],
    },
    {
        "id": "defense_siege_tower",
        "nombre": "Torre de asedio",
        "categoria": CAT,
        "descripcion": "Torre rodante de 3 × 3 m y 7,4 m de alto, con tres pisos unidos por escaleras de mano, "
                       "frente forrado de pieles y una pasarela que cae sobre el adarve (clip «drop»).",
        "propuestas": [
            {"titulo": "La respuesta enemiga a las murallas",
             "detalle": "En dificultad brutal los asaltantes la empujan hasta una muralla de hasta 5 m y "
                        "entran por el adarve sin abrir brecha. Avanza a 0,5 m/s: da tiempo a quemarla con "
                        "flechas incendiarias o a destruirla con balistas."},
            {"titulo": "No cruza fosos ni estacas",
             "detalle": "Se detiene ante un foso, una hilera de estacas o un caballo de frisa: da sentido a "
                        "las defensas exteriores."},
        ],
    },
    {
        "id": "defense_siege_ladder",
        "nombre": "Escala de asalto",
        "categoria": CAT,
        "descripcion": "Escala con garfios de hierro en tres largos, para muros de 3, 4 y 5 m. Se levanta desde "
                       "el suelo hasta apoyarse en el muro (clip «raise»).",
        "propuestas": [
            {"titulo": "Asalto por encima del muro",
             "detalle": "Los asaltantes de dificultad media en adelante llevan escalas: tardan 6 s en subir y "
                        "llegan al adarve de uno en uno. Un defensor en ese tramo la tira (el enemigo cae y "
                        "pierde 50 de vida); las púas de la muralla de hierro la impiden."},
            {"titulo": "Altura que importa",
             "detalle": "Cada escala sirve para una altura: da valor a mejorar el muro, porque las bandas "
                        "pequeñas solo traen escalas cortas."},
        ],
    },
    {
        "id": "defense_pit",
        "nombre": "Foso trampa",
        "categoria": CAT,
        "descripcion": "Hoyo de 2 × 2 m y 1,2 m de hondo con estacas, tapado con ramas, paja y hojas; la tapa "
                       "cede al pisarla.",
        "propuestas": [
            {"titulo": "Trampa de nivel 2",
             "detalle": "Mejora de la trampa actual (6 troncos, 300 de daño): 8 troncos, 500 de daño y "
                        "retiene 5 s a la víctima. Hay que rearmarla tras cada uso."},
            {"titulo": "También caza",
             "detalle": "Fuera de un asalto atrapa jabalíes y ciervos que pasan: el cazador recoge la pieza."},
        ],
    },
    {
        "id": "defense_cheval",
        "nombre": "Caballo de frisa",
        "categoria": CAT,
        "descripcion": "Tronco de 2 m (o 4 m) erizado de estacas cruzadas y afiladas, atadas con cuerda; variante "
                       "con puntas de hierro. Ocupa 2 × 1 m y se puede mover.",
        "propuestas": [
            {"titulo": "Barrera rápida y móvil",
             "detalle": "3 troncos y 15 de trabajo. No bloquea a los aldeanos (lo rodean) pero frena a los "
                        "asaltantes al 30 % y daña 20 a quien lo cruza. Se recoge y se recoloca sin perder "
                        "material."},
            {"titulo": "Anticaballería",
             "detalle": "Los enemigos montados y las criaturas grandes no pueden cruzarlo: tienen que "
                        "destruirlo (300 de vida; 500 con hierro)."},
            {"titulo": "Tapar una brecha",
             "detalle": "Colocado sobre un módulo en «brecha» lo cierra provisionalmente hasta que llegue el "
                        "constructor."},
        ],
    },
    {
        "id": "defense_stakes",
        "nombre": "Hilera de estacas",
        "categoria": CAT,
        "descripcion": "Dos filas de estacas afiladas inclinadas hacia fuera sobre un caballón de tierra; módulo "
                       "de 2 m, variante con puntas de hierro.",
        "propuestas": [
            {"titulo": "Antemuro",
             "detalle": "Se traza arrastrando delante del muro: 2 troncos por módulo. Los enemigos que la "
                        "cruzan reciben 40 de daño y quedan 2 s al alcance de las torres."},
            {"titulo": "Contra la fauna",
             "detalle": "Los lobos, osos y jabalíes no la cruzan: protege corrales y campos lejanos sin "
                        "levantar un muro."},
        ],
    },
    {
        "id": "defense_caltrops",
        "nombre": "Campo de abrojos",
        "categoria": CAT,
        "descripcion": "Parche de 2 × 2 m sembrado de abrojos de hierro sobre barro pisado.",
        "propuestas": [
            {"titulo": "Trampa que frena",
             "detalle": "1 de hierro por parche. No mata: reduce la velocidad de quien lo pisa al 40 % durante "
                        "10 s. Se gasta tras 12 pisadas."},
            {"titulo": "Invisible para el enemigo",
             "detalle": "Como la trampa actual, los asaltantes no lo esquivan; los aldeanos propios sí, salvo "
                        "de noche."},
        ],
    },
    {
        "id": "defense_moat",
        "nombre": "Foso",
        "categoria": CAT,
        "descripcion": "Tramo de foso de 2 m de largo y 4 m de ancho, con 1,5 m de hondo y un caballón con "
                       "estacas en el lado interior. Seco con estacas en el fondo, con agua y juncos, o con una "
                       "pasarela de tablas.",
        "propuestas": [
            {"titulo": "Obra de tierra sin materiales",
             "detalle": "Solo cuesta trabajo (60 por tramo): da empleo a los aldeanos ociosos en invierno. "
                        "Impide llegar al muro salvo por el puente o la pasarela."},
            {"titulo": "Se llena de agua",
             "detalle": "Si toca un río, un lago o el mar se llena solo: entonces tampoco se puede cruzar a pie "
                        "y apaga los incendios de la empalizada vecina."},
            {"titulo": "Con estacas",
             "detalle": "El foso seco con estacas (2 troncos) hace 60 de daño a quien cae o baja a cruzarlo."},
        ],
    },
    {
        "id": "defense_hoarding",
        "nombre": "Cadalso de madera sobre la muralla",
        "categoria": CAT,
        "descripcion": "Galería de tablas colgada por fuera de las almenas de un módulo de muralla, con suelo "
                       "abierto junto al muro, saeteras y tejadillo a un agua. Se añade encima de un recto ya "
                       "construido.",
        "propuestas": [
            {"titulo": "Mejora de guerra para un tramo",
             "detalle": "4 troncos por módulo. Los defensores del tramo no reciben daño a distancia y pueden "
                        "atacar a los enemigos pegados al pie del muro (que normalmente quedan en ángulo "
                        "muerto)."},
            {"titulo": "Arde",
             "detalle": "Es de madera sobre un muro que no arde: las flechas incendiarias lo queman y hay que "
                        "rehacerlo."},
        ],
    },
    {
        "id": "defense_machicolation",
        "nombre": "Matacán de piedra",
        "categoria": CAT,
        "descripcion": "Módulo de muralla cuyo parapeto exterior vuela 0,6 m sobre ménsulas de piedra, con "
                       "buhederas en el suelo entre ellas. Sustituye a un recto.",
        "propuestas": [
            {"titulo": "Cadalso permanente",
             "detalle": "Como el cadalso de madera pero de piedra: +2 de piedra por módulo, no arde. Los "
                        "aldeanos de la milicia arrojan piedras (30 de daño en área) sin necesitar arco."},
            {"titulo": "Sobre las puertas",
             "detalle": "Colocado a los lados de una puerta, duplica el daño que recibe quien la golpea."},
        ],
    },
    {
        "id": "defense_cauldron",
        "nombre": "Caldero de aceite hirviendo",
        "categoria": CAT,
        "descripcion": "Módulo de muralla con un caldero de hierro sobre un eje junto a una tronera, con fuego "
                       "debajo y un barril de aceite. El caldero se vuelca hacia fuera (clip «pour»).",
        "propuestas": [
            {"titulo": "Daño en área al pie del muro",
             "detalle": "2 de hierro para construirlo. Cada vertido gasta 1 de carbón y hace 150 de "
                        "daño a todo lo que esté a 2 m del pie; tarda 30 s en recalentarse."},
            {"titulo": "Contra arietes y escalas",
             "detalle": "Destruye las escalas apoyadas en su tramo y prende los arietes."},
        ],
    },
    {
        "id": "defense_watch",
        "nombre": "Atalaya con campana",
        "categoria": CAT,
        "descripcion": "Plataforma de vigía de 2 × 2 m a 3,2 m de alto sobre cuatro postes, con barandilla, "
                       "escalera de mano y campana de alarma; con techo de paja o abierta.",
        "propuestas": [
            {"titulo": "Vigía barato sin ataque",
             "detalle": "6 troncos. No dispara, pero da 40 m de visión y hace sonar la alarma en cuanto ve "
                        "asaltantes: 20 s más de aviso que el centro del pueblo."},
            {"titulo": "Segunda campana",
             "detalle": "Extiende el alcance de la campana del pueblo a los barrios lejanos: los aldeanos a "
                        "40 m la oyen y corren a refugiarse."},
            {"titulo": "Puesto de explorador",
             "detalle": "Fuera de las murallas sirve de punto de descanso y de visión para el explorador."},
        ],
    },
    {
        "id": "defense_rampart",
        "nombre": "Terraplén",
        "categoria": CAT,
        "descripcion": "Talud de tierra de 2 m de largo, 4 m de ancho y 1,4 m de alto, con césped, zarzo en la "
                       "cara exterior y, en la variante completa, una empalizada y un paso de tablas encima.",
        "propuestas": [
            {"titulo": "La tierra del foso",
             "detalle": "Excavar un tramo de foso da la tierra para un tramo de terraplén gratis; juntos "
                        "cuentan como un muro de 3 m de desnivel."},
            {"titulo": "Empalizada reforzada",
             "detalle": "Una empalizada sobre terraplén tiene +50 % de vida y no arde por la base; cuesta "
                        "40 de trabajo extra por módulo."},
        ],
    },
    {
        "id": "defense_mantlet",
        "nombre": "Mantelete",
        "categoria": CAT,
        "descripcion": "Escudo de tablas de 1,8 × 1,85 m con mirilla, zunchos de hierro y dos ruedas, apoyado en "
                       "dos puntales.",
        "propuestas": [
            {"titulo": "Cobertura para arqueros fuera del muro",
             "detalle": "2 troncos y 1 de hierro. Un arquero detrás recibe un 70 % menos de daño a distancia; "
                        "se empuja a 1 m/s."},
            {"titulo": "Equipo de los asaltantes",
             "detalle": "También lo pueden traer los asaltantes de dificultad alta para acercarse a las "
                        "torres: obliga a salir con la milicia."},
        ],
    },
]
