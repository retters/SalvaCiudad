"""Writes catalogo.json for the trade signs and the burnt ruins.

    python art/blender/proposals/states/catalog.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SIGNS = [
    ("bakery", "Panadería: hogaza"), ("tavern", "Taberna: jarra"), ("brewery", "Cervecería: barril"), ("blacksmith", "Herrería: yunque"),
    ("tailor", "Sastre: tijeras"), ("cobbler", "Zapatero: bota"), ("weaver", "Tejedor: carrete"), ("herbalist", "Herbolario: hoja"),
    ("physician", "Médico: frasco"), ("market", "Mercado: balanza"), ("trading_post", "Puesto de comercio: monedas"), ("vault", "Bóveda: llave"),
    ("woodcutter", "Leñador: hacha"), ("stonecutter", "Cantero: pico"), ("fisher", "Pescador: pez"), ("hunter", "Cazador: arco y flecha"),
    ("farm", "Granja: gavilla"), ("mill", "Molino: aspas"), ("smokehouse", "Ahumadero: jamón"), ("tannery", "Curtiduría: piel"),
    ("armory", "Armería: escudo y espada"), ("bowyer", "Arquero: arco"), ("bathhouse", "Casa de baños: tina"), ("chapel", "Capilla: campana"),
    ("kiln", "Horno: ladrillos"), ("smelter", "Fundición: lingote y llama"), ("inn", "Posada: cama"), ("stable", "Establo: herradura"),
    ("explorer", "Explorador: rosa de los vientos"),
]
FOOTPRINTS = ((2, 2), (3, 3), (4, 2), (4, 4), (5, 4), (5, 5), (6, 5), (6, 6), (6, 8), (7, 6), (7, 7), (8, 6), (8, 7), (8, 8))

GROUPS = [
    {
        "id": "sign_trade", "nombre": "Letreros de oficio", "categoria": "Edificios", "destacado": True,
        "descripcion": "Letrero colgante de 0,7 m en un brazo de hierro que sale 1 m de la fachada, a 2,9 m de alto, con el emblema del oficio por las dos caras: uno para cada tipo de edificio. El origen del modelo va pegado a la pared, al nivel del suelo.",
        "propuestas": [
            {"titulo": "Saber qué es cada edificio de un vistazo", "detalle": "Muchos edificios son la misma casita con algo distinto en el patio. El juego cuelga el letrero de su oficio en la fachada de cada uno: se reconoce desde lejos sin pasar el cursor."},
            {"titulo": "Abierto o cerrado", "detalle": "El letrero se mece mientras el edificio trabaja y queda quieto cuando está parado (sin trabajador, sin materia prima, almacén lleno): avisa sin iconos flotantes."},
            {"titulo": "Mejora del entorno", "detalle": "Una calle con letreros se ve cuidada: cada uno suma un poco al atractivo, y los mercaderes encuentran antes la taberna y el mercado."},
            {"titulo": "Opción del jugador", "detalle": "Se activan o no en las opciones de la vista, como los nombres de los edificios."},
        ],
        "modelos": [{"id": "sign_" + key, "nombre": name, "animaciones": {"swing": "El letrero se mece."}} for key, name in SIGNS],
    },
    {
        "id": "ruin_burnt", "nombre": "Ruinas quemadas por tamaño de terreno", "categoria": "Edificios", "destacado": True,
        "descripcion": "Lo que queda de un edificio tras un incendio, genérico por tamaño de terreno como las obras del juego: cimientos ennegrecidos con el hueco de la puerta, postes carbonizados, vigas caídas, montones de ceniza con brasas, la chimenea en pie y humo. Uno por cada uno de los 14 tamaños que usan los edificios.",
        "propuestas": [
            {"titulo": "El incendio deja huella", "detalle": "Un edificio que se quema del todo no desaparece: queda su ruina, que humea unos días. Baja el atractivo de las casas vecinas hasta que se limpia."},
            {"titulo": "Reconstruir más barato", "detalle": "Sobre la ruina se puede reconstruir el mismo edificio por parte del costo (los cimientos de piedra se aprovechan), o despejarla para recuperar algo de piedra."},
            {"titulo": "Tras una incursión", "detalle": "Los edificios destruidos por asaltantes quedan igual: el pueblo muestra sus heridas hasta que se repara."},
            {"titulo": "Ruinas del mapa", "detalle": "El generador puede sembrar aldeas quemadas con estas ruinas: restos de un pueblo anterior con algo que rescatar."},
        ],
        "modelos": [{"id": "ruin_%dx%d" % (w, d), "nombre": "Terreno de %d × %d m" % (w, d), "animaciones": {"smolder": "Sube el humo."}} for w, d in FOOTPRINTS],
    },
]


def main():
    with open(os.path.join(HERE, "catalogo.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"familia": "states", "grupos": GROUPS}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("states: %d groups, %d models" % (len(GROUPS), sum(len(g["modelos"]) for g in GROUPS)))


if __name__ == "__main__":
    main()
