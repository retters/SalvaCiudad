"""Writes catalogo.json for the piles: four groups, each pile in its three levels.

    python art/blender/proposals/piles/catalog.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS = ("poco", "a medias", "lleno")

NAMES = {
    "bricks": "Ladrillos", "roof_tiles": "Tejas", "clay": "Arcilla", "planks": "Tablas", "iron": "Lingotes de hierro", "tools": "Herramientas",
    "firewood": "Leña", "coal": "Carbón", "iron_ore": "Mineral de hierro", "gold": "Oro",
    "wheat": "Trigo", "barley": "Cebada", "flax": "Lino en rama", "bread": "Pan", "vegetables": "Verduras", "fruit": "Fruta", "berries": "Bayas", "roots": "Raíces",
    "meat": "Carne", "smoked": "Ahumados", "fish": "Pescado", "herbs": "Hierbas", "beer": "Cerveza", "cheese": "Queso y leche", "honey": "Miel", "hay": "Heno",
    "hides": "Pieles", "leather": "Cuero", "linen": "Tela de lino", "clothes": "Ropa", "shoes": "Zapatos", "bows": "Arcos", "weapons": "Armas", "wool": "Lana",
}

GROUPS = [
    ("pile_construction", "Pilas de materiales de obra", True,
     "Pilas de 1,5 × 1,5 m en tres niveles (poco, a medias, lleno), como las que el juego ya tiene para troncos y piedra: ladrillos, tejas, arcilla, tablas, lingotes de hierro y cajones de herramientas.",
     [("Las obras muestran lo que tienen", "Hoy las obras solo enseñan troncos y piedra. Con estas pilas se ve cada material que ya llegó a la obra: se sabe de un vistazo qué falta para terminar un edificio de ladrillo y teja."),
      ("Patio del almacén", "El almacén muestra fuera lo que guarda dentro: sin abrir su ventana se ve que sobran ladrillos y no queda hierro."),
      ("Salida de los talleres", "El horno, el pozo de arcilla, la fundición y el herrero apilan su producción junto a la puerta hasta que alguien la recoge: se ve cuáles están atascados por falta de acarreo."),
      ("Tablas como recurso nuevo", "La pila de tablas es para un material nuevo, entre el tronco y el edificio, que haría un aserradero.")],
     ["bricks", "roof_tiles", "clay", "planks", "iron", "tools"]),
    ("pile_fuel", "Pilas de combustible y minerales", False,
     "Leña en hileras, carbón en su cajón, mineral de hierro y lingotes de oro con un cofre, en tres niveles.",
     [("Leñera y carbonera que se ven", "El partidor de leña, la carbonera y la mina apilan fuera lo que producen; en invierno se ve cómo baja la leña del pueblo."),
      ("El oro de la bóveda", "La bóveda muestra el oro que guarda: mucho oro a la vista atrae incursiones mayores, lo que da sentido a protegerla."),
      ("Reserva de invierno", "El jugador fija una reserva de leña; la pila cambia de color o de señal cuando no se alcanza antes del frío.")],
     ["firewood", "coal", "iron_ore", "gold"]),
    ("pile_food", "Pilas de comida", True,
     "Gavillas de trigo, cebada y lino, bandejas de pan, cajones de verduras y raíces, canastas de fruta y bayas, colgaderos de carne, ahumados, pescado y hierbas, barriles de cerveza, quesos y lecheras, tarros de miel y pacas de heno, en tres niveles.",
     [("El granero y el mercado enseñan su surtido", "Cada alimento distinto que haya aparece como su pila: la dieta variada se ve, y se nota qué falta antes de que baje la salud."),
      ("Puestos del mercado", "Los puestos se llenan con las pilas de lo que de verdad venden y se vacían cuando el mercado se queda sin género."),
      ("Lo que trae el mercader", "El mercader descarga sus pilas junto al puesto de comercio: se ve qué ofrece sin abrir su ventana."),
      ("Comida que se estropea", "La pila pasa a un tono apagado cuando la comida está por echarse a perder: hay que comerla o venderla ya.")],
     ["wheat", "barley", "flax", "bread", "vegetables", "fruit", "berries", "roots", "meat", "smoked", "fish", "herbs", "beer", "cheese", "honey", "hay"]),
    ("pile_goods", "Pilas de bienes", False,
     "Pieles apiladas, rollos de cuero, rollos de tela, ropa doblada de colores, un estante de zapatos, armeros de arcos y de armas con escudos, y fardos de lana, en tres niveles.",
     [("Talleres y almacén", "La curtiduría, el tejedor, el sastre, el zapatero, el arquero y la armería muestran su producción, y el almacén sus existencias."),
      ("Armería a la vista", "Los armeros llenos o vacíos junto al cuartel dicen cuántos soldados más se pueden armar."),
      ("Carga de las caravanas", "Las ofertas a otros pueblos y lo que traen los mercaderes se ven como estas pilas sobre el carro o junto al puesto.")],
     ["hides", "leather", "linen", "clothes", "shoes", "bows", "weapons", "wool"]),
]


def main():
    groups = []
    for gid, name, star, what, proposals, kinds in GROUPS:
        models = []
        for kind in kinds:
            for level in (1, 2, 3):
                models.append({"id": "pile_%s_%d" % (kind, level), "nombre": "%s, %s" % (NAMES[kind], LEVELS[level - 1])})
        group = {"id": gid, "nombre": name, "categoria": "Pilas de recursos", "descripcion": what,
                 "propuestas": [{"titulo": t, "detalle": d} for t, d in proposals], "modelos": models}
        if star:
            group["destacado"] = True
        groups.append(group)
    with open(os.path.join(HERE, "catalogo.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"familia": "piles", "grupos": groups}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("piles: %d groups, %d models" % (len(groups), sum(len(g["modelos"]) for g in groups)))


if __name__ == "__main__":
    main()
