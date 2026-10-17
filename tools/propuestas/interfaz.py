"""Builds and reads the interface mockups page (docs/propuestas/interfaz).

    python tools/propuestas/interfaz.py datos        # kit/datos.js from the game's defs and texts
    python tools/propuestas/interfaz.py fondos       # backgrounds from the saved captures
    python tools/propuestas/interfaz.py miniaturas   # renders img/ with Blender (a few minutes)
    python tools/propuestas/interfaz.py respuestas   # Salvador's answers, readable

Nothing here touches src/ or data/: the game's files are only read.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "data" / "mods" / "core"
OUT = ROOT / "docs" / "propuestas" / "interfaz"
CAPTURES = ROOT / ".claude" / "capturas"
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

CATEGORIES = ["housing", "food", "resources", "industry", "services", "decoration", "defense", "plaza", "garden",
              "nature", "monuments", "ruins"]

# Clothes for the portraits: the game recolors these slots per villager.
OUTFITS = [
    {"top": "#3a5a7a", "bottom": "#4a3a2a", "shoes": "#2a2018", "belt": "#5a3a1a", "hat": "#6a4a2a", "apron": "#c8b890"},
    {"top": "#8a3a2a", "bottom": "#3a3a3a", "shoes": "#2a2018", "belt": "#3a2a1a", "hat": "#4a5a3a", "apron": "#d8c8a0"},
    {"top": "#4a6a3a", "bottom": "#5a4a3a", "shoes": "#3a2a1a", "belt": "#2a2018", "hat": "#8a6a3a", "apron": "#c8c0a8"},
    {"top": "#6a4a7a", "bottom": "#2a3a4a", "shoes": "#2a2018", "belt": "#6a4a2a", "hat": "#3a3a5a", "apron": "#e0d0b0"},
    {"top": "#b08a3a", "bottom": "#4a3a2a", "shoes": "#2a2018", "belt": "#4a2a1a", "hat": "#7a3a2a", "apron": "#d0c0a0"},
]

# Villagers shown in the mockups: (id, race, body, sex, name index, skin, hair, outfit).
PORTRAITS = [
    ("alonso", "core:human", "adventurer_man", "male", 0, 1, 1, 0),
    ("francisca", "core:human", "adventurer_woman", "female", 5, 0, 3, 1),
    ("nicolas", "core:human", "adventurer_man", "male", 12, 3, 0, 2),
    ("elena", "core:human", "adventurer_woman", "female", 4, 2, 4, 3),
    ("rodrigo", "core:human", "knight_man", "male", 14, 1, 5, 4),
    ("teresa", "core:human", "mage", "female", 15, 0, 2, 3),
    ("pascual", "core:human", "cleric", "male", 13, 4, 0, 0),
    ("nyxar", "core:dark_elf", "dark_elf_man", "male", 0, 0, 0, 0),
    ("thazza", "core:dark_elf", "dark_elf_woman", "female", 0, 1, 2, 3),
    ("borin", "core:dwarf", "dwarf_man", "male", 0, 0, 0, 2),
    ("helga", "core:dwarf", "dwarf_woman", "female", 0, 1, 4, 1),
    ("aelar", "core:elf", "high_elf_man", "male", 0, 0, 0, 2),
    ("lirien", "core:elf", "high_elf_woman", "female", 0, 1, 1, 3),
    ("misu", "core:catfolk", "catfolk", "male", 0, 0, 0, 1),
    ("rojo", "core:foxfolk", "foxfolk", "male", 0, 0, 0, 4),
    ("crok", "core:frogfolk", "frogfolk", "male", 0, 0, 0, 2),
    ("sssar", "core:lizardfolk", "lizardfolk", "male", 0, 1, 0, 1),
    ("grum", "core:orc", "orc", "male", 0, 0, 0, 0),
]

ITEMS = {  # Picture of a resource or a thing on the map: model.
    "core:log": "loads/logs_back", "core:stone": "loads/stone_back", "core:wheat": "loads/sack_back",
    "core:clothes": "loads/crate_back", "core:berries": "props/bush_berries", "core:herbs": "props/herb",
    "core:fish": "props/fish_shoal", "core:gold": "props/gold_deposit",
    "core:clay": "props/clay_deposit", "core:coal": "props/coal_deposit", "core:fruit": "trees/apple_autumn",
    "core:firewood": "buildings/decor_firewood_rack",
}
THINGS = ["props/boulder", "props/berry_bush", "props/loose_stones", "props/ducks", "trees/pine_summer",
          "trees/apple_autumn", "trees/yellow_oak_autumn", "trees/maple_autumn", "props/cover_reeds",
          "animals/wolf", "animals/deer", "animals/bear", "animals/boar", "animals/sheep", "fauna/dog",
          "fauna/cat_tabby", "fauna/hen", "fauna/fox", "fauna/mammoth", "fauna/goat", "fauna/lynx", "fauna/rabbit"]

BACKGROUNDS = [  # (id, capture, crop box or None, name). interfaz_* are the map report's clean captures.
    ("pueblo", "interfaz_pueblo.png", None, "Pueblo"),
    ("lago", "interfaz_lago.png", None, "Lago y bosque de colores"),
    ("pradera", "interfaz_pradera.png", None, "Pradera"),
    ("lluvia", "interfaz_lluvia.png", None, "Tarde de lluvia"),
    ("caminos", "fase95_caminos.png", (0, 0, 1120, 630), "Caminos (de cerca)"),
    ("vallas", "fase94_vallas.png", (0, 85, 1120, 715), "Vallas y setos (de cerca)"),
    ("otono", "fase114_pregunta_tortugas.png", (250, 180, 1023, 615), "Bosque en otoño (de cerca)"),
    ("noche", "fase96_faroles_de_noche.png", (140, 60, 1020, 555), "Noche con faroles"),
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def strings(lang):
    out = {}
    for path in (ROOT / "data" / "lang" / f"{lang}.json", CORE / "lang" / f"{lang}.json"):
        doc = load_json(path)
        out.update(doc.get("strings", {}))
    return out


def category(d):
    if d.get("category") in CATEGORIES:
        return CATEGORIES.index(d["category"])
    kind = d.get("kind")
    if kind == "house":
        return 0
    if kind in ("storage", "market", "townCenter"):
        return 4
    if kind == "decoration":
        return 5
    if kind == "defense":
        return 6
    work = d.get("work")
    if work == "gather":
        return 2
    if work in ("farm", "hunt", "fish"):
        return 1
    if d.get("service"):
        return 4
    return 3


def model_name(d):
    m = d.get("model") or ""
    if not m and d.get("id") == "core:house":
        m = "models/buildings/house.glb"
    return Path(m).stem if m else ""


def cmd_datos():
    buildings = []
    for d in load_json(CORE / "defs" / "buildings.json")["defs"]:
        if d.get("cart"):
            continue
        stem = model_name(d)
        buildings.append({
            "id": d["id"], "nombre": d.get("name", ""), "categoria": category(d), "costo": d.get("cost") or {},
            "nivel": d.get("tier", 1), "trabajadores": d.get("workers", 0), "habitantes": d.get("residents", 0),
            "guarda": d.get("storage", 0), "img": f"img/edificios/{stem}.png" if stem else "",
            "tamano": d.get("size", [0, 0]),
        })
    resources = []
    for d in load_json(CORE / "defs" / "resources.json")["defs"]:
        item = ITEMS.get(d["id"])
        resources.append({"id": d["id"], "nombre": d["name"], "cat": d.get("category", "material"),
                          "valor": d.get("value", 0), "img": f"img/cosas/{Path(item).name}.png" if item else ""})
    races = []
    for d in load_json(CORE / "defs" / "races.json")["defs"]:
        races.append({"id": d["id"], "nombre": d["name"], "nombres": d.get("names", {}), "pieles": d.get("skins", []),
                      "pelos": d.get("hairs") or []})
    race_by_id = {r["id"]: r for r in races}
    portraits = []
    for pid, race, body, sex, name_i, _skin, _hair, _outfit in PORTRAITS:
        names = race_by_id[race]["nombres"].get(sex) or race_by_id[race]["nombres"].get("male") or [pid.title()]
        name = names[name_i % len(names)] if race == "core:human" else pid.title()
        portraits.append({"id": pid, "raza": race, "sexo": sex, "nombre": name, "img": f"img/retratos/{pid}.png"})
    data = {
        "textos": {"es": strings("es"), "en": strings("en")},
        "categorias": CATEGORIES,
        "edificios": buildings,
        "recursos": resources,
        "razas": races,
        "retratos": portraits,
        "cosas": [f"img/cosas/{Path(t).name}.png" for t in THINGS],
        "fondos": [{"id": b[0], "nombre": b[3], "img": f"fondos/{b[0]}.jpg"} for b in BACKGROUNDS],
    }
    out = OUT / "kit" / "datos.js"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text("// Generated by tools/propuestas/interfaz.py datos: do not edit.\nwindow.DATOS = "
                   + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    os.replace(tmp, out)
    print(f"{out.relative_to(ROOT)}: {len(buildings)} edificios, {len(resources)} recursos, {len(portraits)} retratos")


def cmd_fondos():
    from PIL import Image
    folder = OUT / "fondos"
    folder.mkdir(parents=True, exist_ok=True)
    for bid, capture, box, _name in BACKGROUNDS:
        im = Image.open(CAPTURES / capture).convert("RGB")
        if box:
            im = im.crop(box)
        if im.size != (1920, 1080):
            im = im.resize((1920, 1080), Image.LANCZOS)
        im.save(folder / f"{bid}.jpg", quality=86, optimize=True)
        print("fondos/" + bid + ".jpg")
    # The minimap as the game draws it (with its view outline), from a capture.
    im = Image.open(CAPTURES / "interfaz_hud_actual.png").convert("RGB")
    im.crop((1693, 73, 1892, 272)).resize((400, 400), Image.LANCZOS).save(folder / "minimapa.jpg", quality=90)
    print("fondos/minimapa.jpg")


def cmd_miniaturas(only=None):
    races = {d["id"]: d for d in load_json(CORE / "defs" / "races.json")["defs"]}
    models = CORE / "models"
    jobs = []
    seen = set()
    for d in load_json(CORE / "defs" / "buildings.json")["defs"]:
        stem = model_name(d)
        if not stem or stem in seen or d.get("cart"):
            continue
        seen.add(stem)
        jobs.append({"glb": str(models / "buildings" / f"{stem}.glb"),
                     "out": str(OUT / "img" / "edificios" / f"{stem}.png"), "kind": "building", "size": 256})
    for pid, race, body, _sex, _n, skin, hair, outfit in PORTRAITS:
        r = races[race]
        palette = dict(OUTFITS[outfit])
        palette["skin"] = r["skins"][skin % len(r["skins"])]
        if r.get("hairs"):
            palette["hair"] = r["hairs"][hair % len(r["hairs"])]
        jobs.append({"glb": str(models / "characters" / f"{body}.glb"), "out": str(OUT / "img" / "retratos" / f"{pid}.png"),
                     "kind": "portrait", "size": 256, "palette": palette, "yaw": 22})
    for path in sorted(set(ITEMS.values()) | set(THINGS)):
        jobs.append({"glb": str(models / f"{path}.glb"), "out": str(OUT / "img" / "cosas" / f"{Path(path).name}.png"),
                     "kind": "item", "size": 256})
    jobs = [j for j in jobs if Path(j["glb"]).exists() and (not only or only in j["out"])]
    for j in jobs:
        Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        jobs_file = Path(tmp) / "jobs.json"
        jobs_file.write_text(json.dumps(jobs), encoding="utf-8")
        script = Path(__file__).with_name("interfaz_miniaturas.py")
        result = subprocess.run([str(BLENDER), "--background", "--factory-startup", "--python", str(script), "--",
                                 str(jobs_file)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = [l for l in result.stdout.splitlines() if l.startswith("OK ")]
    bad = [l for l in result.stdout.splitlines() if l.startswith("FAILED ")]
    print(f"{len(ok)} renderizadas, {len(bad)} fallaron")
    for line in bad:
        print(line)


def cmd_respuestas():
    path = OUT / "respuestas.json"
    if not path.exists():
        print("Todavía no hay respuestas (docs/propuestas/interfaz/respuestas.json).")
        return
    doc = load_json(path)
    for key, a in sorted(doc.get("temas", {}).items()):
        line = f"{key}: {a.get('voto', '-')}"
        if a.get("partes"):
            line += " · le gusta: " + ", ".join(a["partes"])
        print(line)
        if a.get("nota"):
            print("   nota: " + a["nota"])
    for key, a in sorted(doc.get("iconos", {}).items()):
        print(f"iconos {key}: {a.get('voto', '-')}" + (f" · {a['nota']}" if a.get("nota") else ""))
    if doc.get("general"):
        print("general: " + doc["general"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "datos":
        cmd_datos()
    elif cmd == "fondos":
        cmd_fondos()
    elif cmd == "miniaturas":
        cmd_miniaturas(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "respuestas":
        cmd_respuestas()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
