"""Writes catalogo.json for the heraldry family: python art/blender/proposals/heraldry/catalog.py"""

import io
import json
import os

RACES = [
    ("human", "Humanos: azul con torre dorada"),
    ("catfolk", "Gatos: naranja con sol"),
    ("dwarf", "Enanos: rojo oscuro con martillo"),
    ("elf", "Elfos: verde con hoja blanca"),
    ("dark_elf", "Elfos oscuros: violeta con luna"),
    ("foxfolk", "Zorros: rojo con llama blanca"),
    ("frogfolk", "Ranas: verde azulado con nenúfar"),
    ("lizardfolk", "Lagartos: jade con pirámide dorada"),
    ("orc", "Orcos: negro con colmillos"),
]

GROUPS = [
    {
        "id": "banner_flag", "suffix": "flag", "nombre": "Bandera de pueblo", "categoria": "Vida del pueblo", "destacado": True,
        "descripcion": "Mástil de 6,6 m con una bandera de 2,7 × 1,7 m que ondea, con el emblema de la raza por las dos caras, dos franjas del segundo color y un remate propio (punta dorada, sol, cubo de bronce, hoja, púa, borla, gota, plumas, calavera). Una por cada raza del juego.",
        "clip": {"wave": "La bandera ondea."},
        "propuestas": [
            {"titulo": "De quién es cada pueblo", "detalle": "En multijugador, la bandera del centro dice de un vistazo qué raza (o qué jugador, si la tela toma su color) gobierna el pueblo. Se iza sola al fundar."},
            {"titulo": "Reclamar territorio", "detalle": "Plantar una bandera en un puesto avanzado extiende el territorio del pueblo unos metros a su alrededor; el enemigo la puede arriar para quitarlo."},
            {"titulo": "Moral", "detalle": "Los defensores a la vista de su bandera luchan mejor; si la bandera cae en una incursión, baja la felicidad hasta que se vuelve a izar."},
            {"titulo": "Barrios de un pueblo mixto", "detalle": "En un pueblo con varias razas, cada barrio iza la suya: los inmigrantes de esa raza prefieren instalarse cerca."}
        ],
    },
    {
        "id": "banner_standard", "suffix": "standard", "nombre": "Estandarte de guerra", "categoria": "Armas y herramientas",
        "descripcion": "Asta de 4,3 m con travesaño y un paño colgante de 1,1 × 2,3 m acabado en dos puntas, con el emblema por las dos caras, borlas y el remate de la raza. Se lleva o se clava.",
        "clip": {"sway": "El paño se mece."},
        "propuestas": [
            {"titulo": "Punto de reunión", "detalle": "Se clava donde el jugador quiere reunir a la milicia: los que toman las armas acuden al estandarte en vez de a la campana."},
            {"titulo": "Portaestandarte", "detalle": "Una unidad lo lleva: los combatientes a su alrededor no huyen. Si cae el portaestandarte, el grupo se desbanda."},
            {"titulo": "Trofeo", "detalle": "Capturar el estandarte de una incursión o de otro jugador da prestigio; se exhibe en el ayuntamiento o en la taberna."}
        ],
    },
    {
        "id": "banner_wall", "suffix": "wall", "nombre": "Pendón de muro", "categoria": "Muros y defensas",
        "descripcion": "Pendón largo de 1,2 × 3,4 m que cuelga de una barra con ménsulas de hierro a 4,5 m; se arrima a un muro, una torre o una puerta (el muro queda detrás).",
        "clip": {"sway": "El pendón se mece."},
        "propuestas": [
            {"titulo": "Adorno de murallas y puertas", "detalle": "Se cuelga en puertas, torres y edificios públicos: sube el prestigio del pueblo y el atractivo de la calle. Cuesta lino y tinte."},
            {"titulo": "Días de fiesta", "detalle": "Aparecen solos en las fachadas durante fiestas, bodas y visitas de mercaderes, y se retiran después."},
            {"titulo": "Marca de edificio mejorado", "detalle": "Señal visual de que un edificio ha subido de nivel o tiene un maestro del oficio."}
        ],
    },
    {
        "id": "banner_border", "suffix": "border", "nombre": "Mojón de frontera", "categoria": "Caminos",
        "descripcion": "Mojón de 1,5 m con el emblema de la raza en la cara y un banderín en un palo de 2,6 m: piedra para humanos, gatos, enanos, elfos oscuros, ranas y lagartos; poste tallado para elfos, zorros y orcos.",
        "clip": {"flutter": "El banderín ondea."},
        "propuestas": [
            {"titulo": "Frontera visible", "detalle": "El límite del territorio de cada pueblo se marca con mojones cada tantos metros en los caminos: se ve dónde empieza la tierra de otro jugador."},
            {"titulo": "Puesto de peaje o de paso", "detalle": "Donde un camino cruza la frontera, el mojón cobra a los mercaderes ajenos o los deja pasar según el trato entre pueblos."},
            {"titulo": "Reclamar a mano", "detalle": "El jugador coloca mojones para ampliar su territorio poco a poco; cada uno cuesta piedra y solo vale si queda unido a los anteriores."}
        ],
    },
]


def main():
    groups = []
    for g in GROUPS:
        group = {k: g[k] for k in ("id", "nombre", "categoria", "descripcion", "propuestas")}
        if g.get("destacado"):
            group["destacado"] = True
        group["modelos"] = [{"id": "banner_%s_%s" % (race, g["suffix"]), "nombre": name, "animaciones": g["clip"]} for race, name in RACES]
        groups.append(group)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalogo.json")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"familia": "heraldry", "grupos": groups}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
