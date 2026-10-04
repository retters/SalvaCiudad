"""Registers the pieces of every wall type."""

from registry import reg
from walltypes import PIECES, WALLS, stairs_length

# Catalog name of each piece.
NAMES = {
    "straight": "Recto (2 m)",
    "half": "Medio módulo (1 m)",
    "corner": "Esquina",
    "tee": "Unión en T",
    "cross": "Cruce",
    "end": "Remate",
    "pillar": "Pilar suelto",
    "slit": "Con aspillera",
    "breach": "Brecha (dañado)",
    "building": "En construcción",
    "step": "Escalón de 1 m (pendiente)",
    "stairs": "Escalera al adarve",
    "torch": "Con brasero",
    "stile": "Paso de escalones",
    "arch": "Arco de paso",
    "buttress": "Con contrafuerte",
    "drain": "Con desagüe enrejado",
    "banner": "Con estandarte",
    "diagonal": "Diagonal (45°, 2,83 m)",
    "roofed": "Adarve cubierto",
}

BASE = ["straight", "half", "corner", "tee", "cross", "end", "pillar"]
SETS = {
    "palisade": BASE + ["slit", "breach", "building", "step", "torch", "banner"],
    "plank": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "banner"],
    "fieldstone": BASE + ["stile", "breach", "building", "step", "torch"],
    "stone": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "buttress", "drain", "banner"],
    "brick": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "buttress", "drain", "banner"],
    "adobe": BASE + ["slit", "breach", "building", "step", "torch"],
    "iron": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "buttress", "drain", "banner"],
    "hedge": BASE + ["arch", "breach", "building", "step", "torch"],
    "whitewash": BASE + ["slit", "breach", "building", "step", "torch"],
    "cobble": BASE + ["slit", "breach", "building", "step", "torch", "buttress"],
    "dwarf": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "buttress", "drain", "banner"],
    "elf": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "banner"],
    "darkelf": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "buttress", "banner"],
    "sandstone": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "buttress", "drain", "banner"],
    "foxfolk": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "banner"],
    "catfolk": BASE + ["slit", "breach", "building", "step", "stairs", "torch", "buttress", "banner"],
    "orc": BASE + ["slit", "breach", "building", "step", "torch", "banner"],
    "reed": BASE + ["breach", "building", "step", "torch"],
}
for _key, _set in SETS.items():   # Every wall has a diagonal; walls with a walkway, a roofed stretch.
    _set.insert(7, "diagonal")
    if "stairs" in _set:
        _set.insert(_set.index("stairs") + 1, "roofed")
SETS["stockade"] = BASE + ["diagonal", "slit", "breach", "building", "step", "stairs", "torch", "banner"]
MATERIAL = {
    "palisade": "troncos", "plank": "troncos", "fieldstone": "piedra", "stone": "piedra",
    "brick": "ladrillo y piedra", "adobe": "arcilla", "iron": "piedra y hierro", "hedge": "seto vivo",
    "whitewash": "piedra encalada y tejas", "cobble": "piedra", "dwarf": "piedra y oro", "elf": "piedra",
    "darkelf": "piedra y hierro", "sandstone": "piedra", "orc": "troncos y hierro", "reed": "cañas y arcilla",
    "stockade": "troncos", "foxfolk": "piedra, troncos y tejas", "catfolk": "arcilla y tejas",
}
RENAME = {
    ("palisade", "slit"): "Con tronera",
    ("orc", "slit"): "Con tronera",
    ("stockade", "slit"): "Con ventana",
    ("adobe", "slit"): "Con ventana",
    ("whitewash", "slit"): "Con ventana",
    ("cobble", "slit"): "Con ventana",
    ("hedge", "building"): "Recién plantado",
    ("hedge", "breach"): "Hueco (dañado)",
}


def register(key):
    W = WALLS[key]
    for kind in SETS[key]:
        fn = PIECES[kind]
        nota = None
        anim = None
        if kind == "torch":
            anim = {"flicker": "La llama del brasero se mueve"}
        if kind == "stairs":
            nota = "Ocupa %d × 3 m: %d módulos de muro y 1 m más hacia dentro." % (
                stairs_length(W), stairs_length(W) // 2)
        if kind == "step":
            nota = "La mitad derecha queda 1 m más alta; se encadenan para subir una ladera."
        if kind == "diagonal":
            nota = ("Va de una esquina de la celda a la opuesta: el algoritmo la usaría en trazados a 45° en "
                    "lugar de una escalera de esquinas. Su unión con las piezas rectas necesita un pilar.")
        reg("wall_" + key, "wall_%s_%s" % (key, kind), RENAME.get((key, kind), NAMES[kind]),
            (lambda p, fn=fn, W=W: fn(p, W)), material=MATERIAL[key], anim=anim, nota=nota)


for _key in SETS:
    register(_key)
