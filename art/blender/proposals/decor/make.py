"""The game's 149 decorations as a proposal family: they are already in
the game as plain decoration, and each group proposes what else they could
do. Nothing is modeled here: the models are copied from the core mod so the
review page can show them, and catalogo.json is written from GROUPS.

    python art/blender/proposals/decor/make.py
"""

import glob
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
SOURCE = os.path.join(REPO, "data", "mods", "core", "models", "buildings")
OUT = os.path.join(REPO, "art", "studies", "propuestas", "decor")
CATEGORY = "Decoraciones del juego"
STARS = {"decor_clothesline", "decor_home_animals", "decor_beehives", "decor_market_stalls", "decor_petrified", "decor_ruins"}

# (id, name, what it is, [(title, detail)...], [decoration names without "decor_"])
GROUPS = [
    ("decor_clothesline", "Tendedero", "El tendedero que hoy solo sube el entorno (3 × 3 m).", [
        ("Anexo que mejora la casa vecina", "Deja de contar para todo su radio y pasa a ser un anexo: la casa que lo tiene a 3 m o menos gana higiene (menos enfermedad) y su ropa dura más. Una casa solo aprovecha un tendedero."),
        ("Requisito para subir de nivel", "La casa de nivel 2 pide un anexo de servicio cerca (tendedero, leñera o barril de lluvia): el barrio se ve vivido antes de mejorar."),
        ("Indicador de ropa", "La ropa tendida aparece solo cuando la casa vecina tiene ropa suficiente; vacío avisa de que falta.")],
     ["clothesline"]),
    ("decor_service_annexes", "Leñera y rincón del barril de lluvia", "Dos adornos de patio de 2 × 2 m.", [
        ("Reserva de leña de la casa", "La leñera junto a una casa le guarda leña para el invierno: sus habitantes hacen un acarreo grande en otoño y no pasan frío si el almacén se vacía."),
        ("Agua contra incendios", "El barril de lluvia apaga o frena un incendio que empieza en la casa de al lado; se llena cuando llueve."),
        ("Anexos de servicio", "Los dos cuentan como el anexo que pide la casa para subir de nivel.")],
     ["firewood_rack", "tool_corner"]),
    ("decor_home_animals", "Gallinero, caseta del perro y palomar", "Tres adornos de patio con animales.", [
        ("Gallinero: huevos", "Da huevos a las casas vecinas, un alimento más para la dieta variada, a cambio de un poco de grano; las gallinas también reducen los insectos del huerto."),
        ("Caseta del perro: guardián", "La casa con caseta tiene perro: ladra ante lobos, zorros y ladrones de noche y defiende el gallinero y el huerto."),
        ("Palomar: mensajes", "Las palomas llevan avisos: con palomar, las órdenes al ejército y las noticias de otros pueblos (ofertas, incursiones) llegan al instante y no a paso de mensajero."),
        ("Palomar: abono y carne", "Además da pichones (carne) y palomina, el mejor abono para los huertos.")],
     ["chicken_coop", "kennel", "dovecote"]),
    ("decor_beehives", "Colmenas", "Colmenas de paja en su banco y una colmena entre flores.", [
        ("Miel", "Producen miel sin trabajador: un alimento que no se estropea y sube la felicidad. Rinden según las flores que tengan cerca (arriates, huertos, pradera)."),
        ("Polinización", "Los huertos, frutales y campos dentro de su radio rinden más."),
        ("Cera e hidromiel", "La cera da velas (luz dentro de los talleres para trabajar de noche) y la miel, hidromiel para la taberna.")],
     ["beehives", "beehive"]),
    ("decor_kitchen_gardens", "Huertos y parras", "Huerto con carretilla, huerto de calabazas, espiral de hierbas, parral de uvas y espaldera con enredadera.", [
        ("Huerto de la casa", "Junto a una casa, le da verdura propia en temporada: sus habitantes van menos al mercado. Lo cuida la familia en sus ratos libres."),
        ("Hierbas para el herbolario", "La espiral de hierbas produce hierbas medicinales cerca del pueblo, sin salir a recolectar."),
        ("Uvas y vino", "El parral da uvas (fruta) y, con la prensa de vino, vino: otra bebida para la taberna y un bien caro para vender."),
        ("Calabazas de otoño", "El huerto de calabazas da una cosecha tardía que aguanta todo el invierno sin estropearse.")],
     ["vegetable_patch", "pumpkin_patch", "herb_spiral", "grape_trellis", "vine_trellis"]),
    ("decor_market_stalls", "Puestos y mercancía", "Puesto de mercado, de alfarería, tienda de alfombras, balanza, carrito de flores, muestrario del herrero, carreta de mano y barriles y cajas.", [
        ("Extienden el mercado", "Cada puesto colocado lejos del mercado reparte bienes a las casas de su alrededor: el mercado deja de ser un solo edificio y se vuelve una red de puestos."),
        ("Puesto especializado", "Cada uno vende una cosa: alfarería (vasijas, un bien nuevo), alfombras y ropa, herramientas (muestrario del herrero), flores (felicidad). Atiende un vendedor."),
        ("Puestos de los mercaderes", "Cuando llega un mercader monta uno de estos puestos junto al puesto de comercio; se ve qué trae."),
        ("Balanza: precios justos", "Con un puesto de balanza en el mercado, los mercaderes pagan un poco mejor y se evitan disputas.")],
     ["market_stall", "pottery_stall", "rug_tent", "scale_stand", "flower_cart", "smith_rack", "cart_stand", "barrel_stack"]),
    ("decor_farm_helpers", "Cosas de granja", "Carreta de heno, almiares, espantapájaros, secadero de pescado y prensa de vino.", [
        ("Espantapájaros: protege la cosecha", "Los campos dentro de su radio pierden menos grano por los pájaros."),
        ("Almiares y carreta: heno", "Guardan heno para el invierno: alimento del ganado y de los animales de tiro, y cama para establos."),
        ("Secadero de pescado: conserva", "Junto a la cabaña del pescador, seca el pescado para que dure más sin ahumadero."),
        ("Prensa de vino: oficio", "Convierte uvas o fruta en vino o sidra con un trabajador.")],
     ["hay_cart", "haystacks", "scarecrow", "fish_rack", "wine_press"]),
    ("decor_garden_structures", "Jardines y parques", "Glorieta, pérgolas, arcos de rosas, setos, arbustos y árboles ornamentales, bonsái, bambú, jardín formal y molinillo.", [
        ("Parque", "Varias piezas juntas forman un parque: los aldeanos pasean en su tiempo libre y recuperan ánimo y energía. Un pueblo grande sin parques pierde felicidad."),
        ("Necesitan jardinero", "Para no marchitarse piden un jardinero cada cierto tiempo; descuidadas dejan de mejorar el entorno."),
        ("Sombra en verano", "Las pérgolas y la glorieta refrescan: quien descansa bajo ellas en verano se recupera antes del calor."),
        ("Bodas y fiestas", "La glorieta es el lugar de las bodas: con una, las parejas se forman antes y nacen más niños.")],
     ["gazebo", "pergola", "wisteria_pergola", "garden_arch", "rose_arch", "hedge_square", "topiary", "topiary_pot", "potted_tree", "parterre",
      "bonsai_rock", "bamboo", "windmill_small"]),
    ("decor_flower_beds", "Flores", "Rosales, tulipanes, girasoles, lavanda, margaritas, lirios, amapolas, hortensias, orquídeas, flores silvestres, arbusto en flor y cactus.", [
        ("Alimento de las abejas", "Las colmenas rinden según las flores que tienen cerca: las flores pasan a ser parte de la producción de miel."),
        ("Ingredientes", "Lavanda y amapolas para el herbolario (remedios), girasoles para aceite (lámparas), rosas y otras para tintes de ropa."),
        ("Floración por estación", "Cada flor mejora el entorno solo cuando florece: tulipanes en primavera, girasoles en verano, hortensias en otoño. Hay que combinarlas para tener color todo el año."),
        ("Regalos y funerales", "Las flores se usan en bodas, fiestas y entierros: suben la felicidad de esos días.")],
     ["rose_bed", "tulip_bed", "sunflowers", "lavender", "daisies", "lilies", "poppies", "hydrangeas", "orchids", "wildflowers", "flowering_shrub", "cacti"]),
    ("decor_magic_flora", "Flora mágica", "Campanillas, tocón y flores luminosas, hongos flor, flores y árbol de cristal, loto gigante, corro de hadas, pétalos flotantes, dientes de león gigantes, lirios de fuego, flores de luna y geoda.", [
        ("Luz sin combustible", "Las que brillan iluminan de noche como un farol pequeño, sin gastar nada: son la luz de las razas del bosque."),
        ("Recurso mágico", "Dan esencia o cristal en pequeñas cantidades: ingrediente de remedios fuertes, faroles de cristal y edificios mágicos."),
        ("Necesidad de algunas razas", "Elfos, elfos oscuros y gente rana piden flora mágica cerca de casa como otros piden capilla."),
        ("Efectos propios", "Cada una hace algo: los lirios de fuego calientan, las flores de luna calman (menos peleas), el corro de hadas trae suerte a las cosechas y la geoda sube el valor de la zona.")],
     ["glow_bells", "mushroom_flowers", "crystal_flowers", "giant_lotus", "glow_stump", "fairy_ring", "floating_petals", "crystal_tree", "giant_dandelions",
      "fire_lilies", "moon_flowers", "geode"]),
    ("decor_dangerous_flora", "Planta carnívora y zarza de ojos", "Dos plantas de fantasía con mala cara.", [
        ("Defensa viva", "La planta carnívora ataca a lo pequeño que pasa a su lado: ratas, conejos que comen el huerto y, con suerte, a un asaltante. Hay que darle carne de vez en cuando."),
        ("Vigía", "La zarza de ojos ve en la oscuridad: descubre a enemigos y bestias en un radio corto, de día y de noche, como una torre diminuta."),
        ("Miedo", "Bajan la felicidad de las casas vecinas (salvo orcos y elfos oscuros, a quienes les gustan).")],
     ["carnivorous_plant", "eye_vine"]),
    ("decor_water", "Fuentes, estanque y cascada", "Fuente de piedra, pozo de la plaza, bebedero de pájaros, estanque con nenúfares y cascada de rocas.", [
        ("Puntos de agua", "La fuente y el pozo de la plaza dan agua como un pozo (con menos alcance) y sirven para apagar incendios."),
        ("Estanque de peces", "El estanque cría peces: un poco de pescado sin río, o un criadero para el pescador."),
        ("Frescor", "En verano refrescan a las casas vecinas: menos golpes de calor y más ánimo."),
        ("Pájaros contra plagas", "El bebedero atrae pájaros que se comen los insectos de huertos y campos cercanos.")],
     ["fountain", "plaza_well", "bird_bath", "pond", "waterfall"]),
    ("decor_rocks", "Rocas y rincones naturales", "Piedra erguida, rocas musgosas, jardín de rocas, rincón de helechos, arco de roca y sendero de piedras.", [
        ("Sendero de piedras como camino", "Es un tramo de camino: quien lo pisa va más rápido y no se embarra. Un camino barato para jardines y barrios."),
        ("Mojones del territorio", "Las piedras erguidas marcan el límite del pueblo: dentro de la línea que forman, los guardias patrullan."),
        ("Refugio de fauna útil", "Rocas musgosas y helechos alojan sapos y erizos que comen babosas: los huertos vecinos rinden un poco más."),
        ("Piedra de reserva", "Se pueden desmontar para recuperar su piedra en una emergencia.")],
     ["standing_stone", "mossy_boulders", "rock_garden", "fern_log", "natural_arch", "stepping_stones"]),
    ("decor_lights", "Faroles y braseros", "Farol, farol doble, par de braseros y pilar de la llama eterna.", [
        ("Alumbrado con farolero", "Ya dan luz; la propuesta es que gasten un poco de combustible (sebo, aceite o carbón) y que un farolero los encienda: sin él se quedan apagados."),
        ("Calles seguras", "Las calles alumbradas no tienen robos ni bestias de noche, y quien camina bajo la luz no pierde velocidad."),
        ("Braseros: calor", "Los braseros calientan en invierno a quien trabaja o hace guardia cerca."),
        ("Llama eterna: memoria", "El pilar de la llama eterna reduce el duelo del pueblo tras una batalla o una epidemia.")],
     ["lamp_post", "lamp_double", "brazier_pair", "flame_pillar"]),
    ("decor_seating", "Bancas y jardineras", "Par de bancas, árbol con banca circular, plazoleta y pretil con jardineras y pedestal florido.", [
        ("Descanso en la calle", "Los aldeanos cansados se sientan en la banca más cercana en vez de ir hasta su casa: recuperan menos, pero vuelven antes al trabajo."),
        ("Lugar de los mayores y de encuentro", "Los ancianos pasan el día en las bancas; donde hay bancas, las parejas se conocen y la gente conversa: sube la felicidad del barrio."),
        ("Sombra", "El árbol con banca da sombra en verano.")],
     ["bench_pair", "tree_bench", "plaza_planter", "planter_wall", "flower_pedestal"]),
    ("decor_information", "Avisos y señales", "Poste de señales, tablón de anuncios, mojón, estrado del pregonero, asta con estandarte, arco de banderines y cruz del mercado.", [
        ("Tablón de anuncios: empleo", "Los aldeanos sin trabajo y los inmigrantes miran el tablón: los puestos vacantes se cubren antes y los recién llegados encuentran casa más rápido."),
        ("Pregonero: órdenes y noticias", "Un pregonero en su estrado difunde los avisos (incursión, incendio, fiesta) por un barrio; sin él, los de lejos tardan en enterarse."),
        ("Señales, mojones y estandartes: caminos e identidad", "Las señales y los mojones dan un poco de velocidad en los caminos que marcan y guían a los visitantes; el estandarte y los banderines muestran el color y el emblema del pueblo y se engalanan solos en las fiestas."),
        ("Cruz del mercado: día de mercado", "Marca el lugar donde, una vez por estación, se celebra un mercado grande que atrae a varios mercaderes a la vez.")],
     ["signpost", "notice_board", "milestone", "crier_stand", "flagpole", "banner_arch", "market_cross"]),
    ("decor_time", "Relojes de sol y campana", "Dos relojes de sol y la campana de la plaza.", [
        ("Horario de trabajo", "Con reloj de sol o campana, los trabajadores cercanos salen y vuelven a la vez y regresan antes de que anochezca: se pierde menos jornada."),
        ("Campana de barrio", "Repite la alarma de la campana del centro: los barrios lejanos se refugian o se arman sin demora."),
        ("Calendario", "El reloj de sol muestra la estación y cuánto falta para el invierno al pasar el cursor.")],
     ["sundial_pillar", "sundial", "bell_frame"]),
    ("decor_pillory", "Picota", "El poste de castigo de la plaza.", [
        ("Orden público", "Si se añaden robos y peleas (pueblos grandes, poca felicidad, mucha cerveza), la picota los reduce; a cambio baja un poco el ánimo de las casas que la ven."),
        ("Castigo a asaltantes capturados", "Los asaltantes vencidos pueden acabar ahí: disuade a la siguiente incursión.")],
     ["pillory"]),
    ("decor_stage", "Tablado", "El tablado de la plaza.", [
        ("Fiestas y teatro", "Una vez por estación se puede dar una función (cuesta cerveza y comida): sube la felicidad de todo el pueblo unos días."),
        ("Músicos y cómicos ambulantes", "De vez en cuando llegan artistas que actúan en el tablado y dejan propina al pueblo; sin tablado pasan de largo."),
        ("Asamblea", "En partidas de varios jugadores, ahí se anuncian pactos y se votan decisiones del pueblo.")],
     ["stage"]),
    ("decor_hitching_post", "Amarradero con abrevadero", "El amarradero de la plaza.", [
        ("Parada de animales de tiro", "Los caballos y bueyes de carros y carretas descansan y beben ahí: necesario junto al puesto de comercio y los almacenes si llegan carros."),
        ("Estancia de mercaderes", "Los mercaderes que llegan en carro se quedan más tiempo si hay amarradero.")],
     ["hitching_post"]),
    ("decor_public_oven", "Horno público", "El horno de la plaza.", [
        ("Pan sin panadería", "Las casas vecinas hornean su propia harina: rinde menos que la panadería pero no pide trabajador; ideal en barrios lejanos."),
        ("Comida caliente", "Las casas con horno cerca gastan menos comida para la misma hambre."),
        ("Riesgo de incendio", "Como toda lumbre, puede iniciar un fuego: mejor con un pozo o un barril cerca.")],
     ["public_oven"]),
    ("decor_petrified", "Figuras petrificadas", "Quince estatuas de aldeanos, un ciervo y un perro convertidos en piedra.", [
        ("Una maldición que deshacer", "Son gente de verdad: con un remedio caro (herbolario, mago o clérigo) se despetrifica a uno y se suma al pueblo como aldeano agradecido, con su oficio (el herrero, el arquero, el mercader)."),
        ("Rastro de un monstruo", "Aparecen en el mapa alrededor de la guarida de un basilisco o una gorgona: avisan del peligro y, al vencerlo, todas despiertan."),
        ("Memoria", "Colocadas por el jugador, recuerdan a los caídos: reducen el duelo tras una batalla."),
        ("Solo decoración", "Se quedan como adorno con historia.")],
     ["petrified_runner", "petrified_kneeling", "petrified_warrior", "petrified_mother", "petrified_pair", "petrified_sunken", "petrified_child",
      "petrified_archer", "petrified_smith", "petrified_dancer", "petrified_merchant", "petrified_elder", "petrified_deer", "petrified_huddle",
      "petrified_dog"]),
    ("decor_monuments", "Monumentos", "Obelisco, arco de piedra, estatua del héroe, muro conmemorativo, ángel, rey en su trono, leones guardianes, estatua de dragón y tótem.", [
        ("Prestigio", "Cada monumento sube el prestigio del pueblo: llegan más inmigrantes y mejores mercaderes. Solo cuenta uno de cada tipo."),
        ("Moral de la tropa", "El héroe, los leones y el dragón dan valor: la milicia y los soldados que pelean cerca aguantan más."),
        ("Duelo", "El muro conmemorativo y el ángel reducen la tristeza tras muertes en batalla o epidemia."),
        ("Monumento por hazaña", "No se compran: se desbloquean al lograr algo (vencer una incursión grande, llegar a 100 habitantes, matar a un dragón).")],
     ["obelisk", "stone_arch", "hero_statue", "memorial_wall", "angel", "king_throne", "guardian_lions", "dragon_statue", "totem_pole"]),
    ("decor_shrines", "Capilla y cruz de camino", "Dos altares pequeños para los caminos.", [
        ("Fe lejos de la capilla", "Cubren la necesidad de fe de las casas cercanas, con menos efecto que la capilla: para barrios lejanos y aldeas."),
        ("Protección del camino", "Quien pasa junto a una va con mejor ánimo, y de noche su luz ahuyenta a los espectros."),
        ("Descanso del viajero", "Los mercaderes y caravanas que encuentran capillas en el camino llegan con mejor disposición y pagan un poco más.")],
     ["roadside_shrine", "wayside_cross"]),
    ("decor_ruins", "Ruinas", "Columnas rotas, arco caído, torre y muro en ruinas, portal del templo, escalera hundida, casa abandonada, cabaña quemada, cobertizo derrumbado, fuente seca, puente roto, mina abandonada y pozo viejo.", [
        ("Parte del mapa, para explorar", "El generador las reparte por el mapa. El explorador las registra: unas dan materiales (piedra labrada, ladrillo), otras un tesoro y otras despiertan algo que vivía dentro."),
        ("Restaurar", "Cada ruina se puede reconstruir por menos que un edificio nuevo: la torre vuelve a ser torre de vigía, el puente se repara, la mina se reabre, el pozo se limpia."),
        ("Cantera de piedra labrada", "Desmontarlas da piedra y ladrillo ya trabajados, sin cantera ni horno."),
        ("Entradas a lo profundo", "El portal, la escalera hundida y la mina son entradas a un subterráneo: de noche pueden salir esqueletos o arañas hasta que se sellan o se limpian.")],
     ["broken_columns", "fallen_arch", "tower_stump", "ruined_wall", "portal_gate", "sunken_stairs", "overgrown_house", "burnt_cottage", "collapsed_shed",
      "dry_fountain", "broken_bridge", "mine_entrance", "old_well"]),
    ("decor_mysteries", "Misterios", "Círculo de runas, cabeza de piedra, monolito, espada gigante, mano del coloso y esqueleto de bestia.", [
        ("Lugares de poder", "Cada uno da un efecto a quien construye cerca: el círculo de runas protege de los no-muertos, el monolito mejora la magia, la espada da valor a la tropa, el esqueleto asusta a las bestias."),
        ("Hallazgos del explorador", "Descubrir uno revela un trozo grande de mapa o enseña algo (una receta, un edificio de otra raza)."),
        ("Sucesos", "De vez en cuando se activan: el círculo brilla una noche y cura, o la cabeza de piedra habla y pide una ofrenda a cambio de una buena cosecha."),
        ("Piezas de una historia", "Son restos del mismo coloso y de la misma guerra: encontrarlos todos desbloquea un monumento único.")],
     ["rune_circle", "stone_head", "monolith", "giant_sword", "colossus_hand", "beast_skeleton"]),
    ("decor_wrecks", "Restos y abandono", "Carreta destrozada, barca abandonada, barriles rotos, campamento abandonado y arado oxidado.", [
        ("Botín para recoger", "Repartidos por el mapa, dan al primero que llega unos pocos materiales, comida o herramientas: un empujón al principio de la partida."),
        ("Rastro de peligro", "Marcan dónde atacaron asaltantes o bestias: cerca hay una guarida o un campamento enemigo."),
        ("Reparar", "La carreta y la barca se pueden reparar por pocos troncos y quedan para el pueblo; el arado, con hierro, mejora una granja.")],
     ["wrecked_cart", "wrecked_boat", "broken_barrels", "abandoned_camp", "rusted_plough"]),
]


def main():
    names = {}
    for path in glob.glob(os.path.join(REPO, "art", "blender", "decor", "*.json")):
        with open(path, encoding="utf-8") as f:
            for item in json.load(f):
                names[item["name"]] = item["es"]
    os.makedirs(OUT, exist_ok=True)
    groups, seen = [], set()
    for gid, name, what, proposals, members in GROUPS:
        models = []
        for member in members:
            model = "decor_" + member
            assert model in names, model
            assert model not in seen, model
            seen.add(model)
            shutil.copyfile(os.path.join(SOURCE, model + ".glb"), os.path.join(OUT, model + ".glb"))
            models.append({"id": model, "nombre": names[model]})
        groups.append({
            "id": gid, "nombre": name, "categoria": CATEGORY,
            "descripcion": what + " Ya están en el juego como decoración: hoy solo suben el atractivo de las casas cercanas.",
            "propuestas": [{"titulo": t, "detalle": d} for t, d in proposals],
            "modelos": models,
            "destacado": gid in STARS,
        })
    missing = sorted(set(names) - seen)
    assert not missing, missing
    with open(os.path.join(HERE, "catalogo.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"familia": "decor", "grupos": groups}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("decor: %d groups, %d models" % (len(groups), len(seen)))


if __name__ == "__main__":
    main()
