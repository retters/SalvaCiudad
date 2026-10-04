"""Packs the proposal models for the review page and reads the answers.

    python tools/propuestas/propuestas.py empaquetar [--demo]
    python tools/propuestas/propuestas.py respuestas [--todo]
    python tools/propuestas/propuestas.py resumen
    python tools/propuestas/propuestas.py revisar [familia]

`empaquetar` reads every art/blender/proposals/<family>/catalogo.json and
the models of art/studies/propuestas/<family>, and writes what the page
docs/propuestas/index.html shows: datos/catalogo.js and one script per model
in datos/modelos (the .glb as base64, so the page works when opened from
disk, with no server). Problems are listed and never stop the packing: a
family with a broken catalog is skipped, a model without its .glb is left
out, and a .glb nobody cataloged is shown under "Sin catalogar".

`respuestas` prints what the user answered on the page (respuestas.json).

`revisar` looks for defects a machine can see in the packed models: a
looping clip that does not end as it starts, and geometry under the ground
outside the categories where that is expected (bridges, boats).

Pure Python, no dependencies. See docs/propuestas/LEEME.md.
"""

import base64
import datetime
import hashlib
import json
import os
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPECS = os.path.join(REPO, "art", "blender", "proposals")
MODELS = os.path.join(REPO, "art", "studies", "propuestas")
PAGE = os.path.join(REPO, "docs", "propuestas")
DATA = os.path.join(PAGE, "datos")
ANSWERS = os.path.join(PAGE, "respuestas.json")

CATEGORIES = [
    "Muros y defensas", "Puentes", "Castillos y fortalezas", "Maravillas y monumentos", "Edificios", "Personajes", "Mascotas y animales",
    "Enemigos y criaturas", "Naturaleza y terreno", "Caminos", "Anexos de casas", "Transporte",
    "Armas y herramientas", "Campamento y exploración", "Granja y riego", "Vida del pueblo", "Magia y alquimia", "Sucesos y desastres", "Pilas de recursos",
    "Decoraciones del juego",
]
UNCATALOGED = "Sin catalogar"
MAX_PROPOSALS = 4


def glb_info(path):
    """What the page lists about a model, read from the .glb itself."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("no es un .glb")
    json_len = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20:20 + json_len])
    accessors = doc.get("accessors", [])
    tris = 0
    low, high = [None] * 3, [None] * 3
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            position = prim.get("attributes", {}).get("POSITION")
            if "indices" in prim:
                tris += accessors[prim["indices"]]["count"] // 3
            elif position is not None:
                tris += accessors[position]["count"] // 3
            if position is not None and "min" in accessors[position]:
                for k in range(3):
                    a, b = accessors[position]["min"][k], accessors[position]["max"][k]
                    low[k] = a if low[k] is None else min(low[k], a)
                    high[k] = b if high[k] is None else max(high[k], b)
    extras = {}
    for node in doc.get("nodes", []):
        if isinstance(node.get("extras"), dict):
            extras.update(node["extras"])
    clips = []
    for anim in doc.get("animations", []):
        seconds = 0.0
        for sampler in anim.get("samplers", []):
            top = accessors[sampler["input"]].get("max")
            if top:
                seconds = max(seconds, top[0])
        name = anim.get("name", "")
        clip = {"nombre": name, "segundos": round(seconds, 2), "repite": extras.get(name + "_loops", 1) != 0}
        if isinstance(extras.get(name + "_speed"), (int, float)):
            clip["velocidad"] = round(extras[name + "_speed"], 2)
        clips.append(clip)
    # glTF is Y up: width along X, height along Y, depth along Z.
    size = [0.0, 0.0, 0.0] if low[0] is None else [round(high[k] - low[k], 2) for k in (0, 2, 1)]
    skins = doc.get("skins", [])
    return {
        "tris": tris,
        "medida": size,   # Width, depth, height in meters.
        "bajoSuelo": 0.0 if low[1] is None else round(min(0.0, low[1]), 2),
        "clips": clips,
        "huesos": len(skins[0].get("joints", [])) if skins else 0,
        "materiales": [m.get("name", "") for m in doc.get("materials", [])],
        "bytes": len(data),
        "hash": hashlib.sha1(data).hexdigest()[:12],
        "_data": data,
    }


COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def loop_gaps(path):
    """{clip: how far its last keys are from its first} for the looping
    clips of a .glb: meters for moves, quaternion units for turns."""
    with open(path, "rb") as f:
        data = f.read()
    json_len = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20:20 + json_len])
    start = 20 + json_len + 8
    extras = {}
    for node in doc.get("nodes", []):
        if isinstance(node.get("extras"), dict):
            extras.update(node["extras"])
    gaps = {}
    for anim in doc.get("animations", []):
        name = anim.get("name", "")
        if extras.get(name + "_loops", 1) == 0:
            continue
        worst = 0.0
        for channel in anim.get("channels", []):
            acc = doc["accessors"][anim["samplers"][channel["sampler"]]["output"]]
            width = COMPONENTS.get(acc.get("type"), 0)
            if acc.get("componentType") != 5126 or not width or acc["count"] < 2:
                continue
            view = doc["bufferViews"][acc["bufferView"]]
            stride = view.get("byteStride", width * 4)
            base = start + view.get("byteOffset", 0) + acc.get("byteOffset", 0)
            first = struct.unpack_from("<%df" % width, data, base)
            last = struct.unpack_from("<%df" % width, data, base + stride * (acc["count"] - 1))
            gap = max(abs(a - b) for a, b in zip(first, last))
            if channel.get("target", {}).get("path") == "rotation":   # q and -q are the same turn.
                gap = min(gap, max(abs(a + b) for a, b in zip(first, last)))
            worst = max(worst, gap)
        gaps[name] = worst
    return gaps


def text(value):
    return value.strip() if isinstance(value, str) else ""


def highlights(family, problems):
    """Groups starred from outside their catalog (destacados.json): some
    catalogs are rewritten by their build script and cannot carry the mark."""
    path = os.path.join(SPECS, "destacados.json")
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as error:
        problems.append("destacados.json no se puede leer (%s)" % error)
        return set()
    listed = doc.get(family) if isinstance(doc, dict) else None
    return {text(g) for g in listed} if isinstance(listed, list) else set()


def read_family(family, problems):
    """The groups of one family, checked; None if its catalog cannot be read."""
    starred = highlights(family, problems)
    path = os.path.join(SPECS, family, "catalogo.json")
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as error:
        problems.append("%s: catalogo.json no se puede leer (%s)" % (family, error))
        return None
    raw = doc.get("grupos") if isinstance(doc, dict) else None
    if not isinstance(raw, list):
        problems.append("%s: catalogo.json no tiene la lista \"grupos\"" % family)
        return None
    groups, seen_groups, seen_models = [], set(), set()
    for g in raw:
        if not isinstance(g, dict) or not text(g.get("id")):
            problems.append("%s: un grupo sin id" % family)
            continue
        gid = text(g["id"])
        if gid in seen_groups:
            problems.append("%s/%s: grupo repetido" % (family, gid))
            continue
        seen_groups.add(gid)
        category = text(g.get("categoria"))
        if category not in CATEGORIES:
            problems.append("%s/%s: categoría desconocida \"%s\"" % (family, gid, category))
            category = category or UNCATALOGED
        proposals = []
        for p in g.get("propuestas") if isinstance(g.get("propuestas"), list) else []:
            if isinstance(p, dict) and text(p.get("titulo")):
                proposals.append({"titulo": text(p["titulo"]), "detalle": text(p.get("detalle"))})
        if not proposals:
            problems.append("%s/%s: sin propuestas" % (family, gid))
        if len(proposals) > MAX_PROPOSALS:
            problems.append("%s/%s: más de %d propuestas (se muestran las primeras)" % (family, gid, MAX_PROPOSALS))
            proposals = proposals[:MAX_PROPOSALS]
        models = []
        for m in g.get("modelos") if isinstance(g.get("modelos"), list) else []:
            if not isinstance(m, dict) or not text(m.get("id")):
                problems.append("%s/%s: un modelo sin id" % (family, gid))
                continue
            mid = text(m["id"])
            if mid in seen_models:
                problems.append("%s/%s: modelo repetido %s" % (family, gid, mid))
                continue
            seen_models.add(mid)
            notes = m.get("animaciones") if isinstance(m.get("animaciones"), dict) else {}
            models.append({
                "id": mid, "nombre": text(m.get("nombre")) or mid, "material": text(m.get("material")),
                "nota": text(m.get("nota")),
                "animaciones": {str(k): text(v) for k, v in notes.items()},
            })
        groups.append({
            "clave": family + "/" + gid, "familia": family, "id": gid,
            "nombre": text(g.get("nombre")) or gid, "categoria": category,
            "descripcion": text(g.get("descripcion")), "propuestas": proposals, "modelos": models,
            "destacado": g.get("destacado") is True or gid in starred,
        })
    for gid in sorted(starred - seen_groups):
        problems.append("destacados.json: %s/%s no existe" % (family, gid))
    return groups


def families(with_demo):
    if not os.path.isdir(SPECS):
        return []
    found = []
    for name in sorted(os.listdir(SPECS)):
        if name.startswith("__") or not os.path.isdir(os.path.join(SPECS, name)):
            continue
        if name.startswith("_") and not with_demo:
            continue
        if os.path.isfile(os.path.join(SPECS, name, "catalogo.json")) or os.path.isdir(os.path.join(MODELS, name)):
            found.append(name)
    return found


def write_if_changed(path, content):
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == content:
                return False
    except OSError:
        pass
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(temp, path)
    return True


def pack(with_demo=False):
    problems, groups, wanted = [], [], set()
    os.makedirs(os.path.join(DATA, "modelos"), exist_ok=True)
    written = 0
    for family in families(with_demo):
        folder = os.path.join(MODELS, family)
        on_disk = set()
        if os.path.isdir(folder):
            on_disk = {f[:-4] for f in os.listdir(folder) if f.endswith(".glb")}
        family_groups = read_family(family, problems) if os.path.isfile(
            os.path.join(SPECS, family, "catalogo.json")) else []
        if family_groups is None:
            family_groups = []
        cataloged = {m["id"] for g in family_groups for m in g["modelos"]}
        loose = sorted(n for n in on_disk - cataloged if not n.endswith("_far"))
        if loose:
            problems.append("%s: %d modelos sin catalogar (%s)" % (family, len(loose), ", ".join(loose[:8])
                                                               + ("…" if len(loose) > 8 else "")))
            for name in loose:
                family_groups.append({
                    "clave": family + "/" + name, "familia": family, "id": name, "nombre": name,
                    "categoria": UNCATALOGED, "descripcion": "Modelo generado que su familia no describió.",
                    "propuestas": [], "modelos": [{"id": name, "nombre": name, "material": "", "nota": "",
                                                   "animaciones": {}}],
                })
        for g in family_groups:
            kept = []
            for m in g["modelos"]:
                path = os.path.join(folder, m["id"] + ".glb")
                try:
                    info = glb_info(path)
                except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
                    problems.append("%s: falta o no se lee %s.glb (%s)" % (g["clave"], m["id"], error))
                    continue
                data = info.pop("_data")
                key = family + "/" + m["id"]
                file = "%s__%s.js" % (family, m["id"])
                wanted.add(file)
                script = "window.PROPUESTAS_MODELO(%s,\"%s\");\n" % (json.dumps(key),
                                                                    base64.b64encode(data).decode("ascii"))
                if write_if_changed(os.path.join(DATA, "modelos", file), script):
                    written += 1
                m.update(info)
                m["archivo"] = "datos/modelos/" + file
                kept.append(m)
            if kept:
                g["modelos"] = kept
                groups.append(g)
    removed = 0
    for file in os.listdir(os.path.join(DATA, "modelos")):
        if file.endswith(".js") and file not in wanted:
            os.remove(os.path.join(DATA, "modelos", file))
            removed += 1
    categories = [c for c in CATEGORIES + [UNCATALOGED] if any(g["categoria"] == c for g in groups)]
    categories += sorted({g["categoria"] for g in groups} - set(categories))
    catalog = {
        "generado": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "categorias": categories,
        "grupos": groups,
        "problemas": problems,
    }
    write_if_changed(os.path.join(DATA, "catalogo.js"),
                     "window.PROPUESTAS_CATALOGO = " + json.dumps(catalog, ensure_ascii=False, indent=1) + ";\n")
    if not os.path.isfile(ANSWERS):
        write_if_changed(ANSWERS, json.dumps({"version": 1, "grupos": {}}, ensure_ascii=False, indent=1) + "\n")
    models = sum(len(g["modelos"]) for g in groups)
    clips = sum(len(m["clips"]) for g in groups for m in g["modelos"])
    print("Empaquetado: %d grupos, %d modelos, %d animaciones; %d archivos escritos, %d borrados."
          % (len(groups), models, clips, written, removed))
    for c in categories:
        gs = [g for g in groups if g["categoria"] == c]
        print("  %-26s %3d grupos, %3d modelos" % (c, len(gs), sum(len(g["modelos"]) for g in gs)))
    for p in problems:
        print("  PROBLEMA", p)
    return catalog


def load_catalog():
    try:
        with open(os.path.join(DATA, "catalogo.js"), encoding="utf-8") as f:
            body = f.read()
        return json.loads(body[body.index("{"):body.rindex("}") + 1])
    except (OSError, ValueError):
        return {"grupos": []}


def load_answers():
    try:
        with open(ANSWERS, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as error:
        print("No se puede leer respuestas.json:", error)
        return {}
    groups = doc.get("grupos") if isinstance(doc, dict) else None
    return groups if isinstance(groups, dict) else {}


def describe(answer, group):
    """One answer in words: the chosen function, the user's own text, marks."""
    lines = []
    choice = answer.get("eleccion")
    if choice == "propuesta":
        index = answer.get("indice")
        title = text(answer.get("titulo"))
        proposals = group.get("propuestas", []) if group else []
        detail = ""
        for p in proposals:
            if p["titulo"] == title:
                detail = p["detalle"]
        if not detail and isinstance(index, int) and 0 <= index < len(proposals) and not title:
            title, detail = proposals[index]["titulo"], proposals[index]["detalle"]
        lines.append("Función elegida: %s" % title)
        if detail:
            lines.append("  %s" % detail)
    elif choice == "propia":
        lines.append("Función redactada por Salvador: %s" % text(answer.get("texto")))
    elif choice == "descartar":
        lines.append("DESCARTADO: no lo quiere en el juego.")
    elif choice == "decoracion":
        lines.append("Solo decoración, sin función.")
    if text(answer.get("texto")) and choice != "propia":
        lines.append("Texto propio (sin elegirlo): %s" % text(answer["texto"]))
    if text(answer.get("nota")):
        lines.append("Nota: %s" % text(answer["nota"]))
    marks = answer.get("modelos") if isinstance(answer.get("modelos"), dict) else {}
    liked = sorted(k for k, v in marks.items() if v == "favorito")
    dropped = sorted(k for k, v in marks.items() if v == "descartado")
    if liked:
        lines.append("Variantes favoritas: " + ", ".join(liked))
    if dropped:
        lines.append("Variantes descartadas: " + ", ".join(dropped))
    return lines


def answers(show_all=False):
    catalog = {g["clave"]: g for g in load_catalog()["grupos"]}
    given = load_answers()
    shown = 0
    for key in sorted(set(catalog) | set(given), key=lambda k: (catalog.get(k, {}).get("categoria", "~"), k)):
        answer = given.get(key) if isinstance(given.get(key), dict) else {}
        lines = describe(answer, catalog.get(key))
        if not lines and not show_all:
            continue
        group = catalog.get(key)
        name = group["nombre"] if group else "(ya no está en el catálogo)"
        category = group["categoria"] if group else "?"
        print("[%s] %s — %s" % (category, key, name))
        for line in lines or ["Sin responder."]:
            print("    " + line)
        if text(answer.get("fecha")):
            print("    (%s)" % answer["fecha"])
        shown += 1
    answered = sum(1 for k in catalog if describe(given.get(k) if isinstance(given.get(k), dict) else {}, catalog[k]))
    print("%d de %d grupos con respuesta." % (answered, len(catalog)))


def summary():
    catalog = load_catalog()
    groups = catalog["grupos"]
    print("Catálogo generado: %s" % catalog.get("generado", "?"))
    print("%d grupos, %d modelos, %d con animaciones." % (
        len(groups), sum(len(g["modelos"]) for g in groups),
        sum(1 for g in groups for m in g["modelos"] if m["clips"])))
    for p in catalog.get("problemas", []):
        print("  PROBLEMA", p)


WATER = ("Puentes", "Transporte")   # Piers and hulls go under the water line.


def review(family=None):
    """Prints the models with a looping clip that jumps at the end, and
    the ones with geometry under the ground."""
    jumps, sunk = [], []
    for g in load_catalog()["grupos"]:
        if family and g["familia"] != family:
            continue
        for m in g["modelos"]:
            path = os.path.join(MODELS, g["familia"], m["id"] + ".glb")
            try:
                gaps = loop_gaps(path)
            except (OSError, ValueError, KeyError, IndexError, struct.error):
                continue
            bad = {c: v for c, v in gaps.items() if v > 0.05}
            if bad:
                jumps.append("%s/%s: %s" % (g["familia"], m["id"], ", ".join("%s (%.2f)" % (c, v) for c, v in sorted(bad.items()))))
            wet = g["categoria"] in WATER or g["familia"] == "bridges"
            if m.get("bajoSuelo", 0) < -0.5 and not wet and abs(m["bajoSuelo"] + 4.55) > 0.03:
                sunk.append("%s/%s: %.2f m" % (g["familia"], m["id"], m["bajoSuelo"]))
    print("Clips que se repiten y no terminan como empiezan: %d" % len(jumps))
    for line in jumps:
        print("  " + line)
    print("Modelos con piezas bajo el suelo (fuera de puentes y barcos): %d" % len(sunk))
    for line in sunk:
        print("  " + line)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if command == "empaquetar":
        pack("--demo" in sys.argv)
    elif command == "respuestas":
        answers("--todo" in sys.argv)
    elif command == "resumen":
        summary()
    elif command == "revisar":
        review(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
