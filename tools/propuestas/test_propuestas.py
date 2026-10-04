"""Tests of the proposals packer. They use a temporary folder and never touch
the real catalog or answers.

    python tools/propuestas/test_propuestas.py
"""

import io
import json
import os
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import propuestas  # noqa: E402


def tiny_glb(clips=()):
    """A one-triangle .glb with the given (name, seconds) animations."""
    positions = struct.pack("<9f", 0, 0, 0, 2, 0, 0, 0, 3, 1)
    indices = struct.pack("<3H", 0, 1, 2) + b"\0\0"
    times = struct.pack("<2f", 0.0, 1.0)
    doc = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(positions) + len(indices) + len(times)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36},
                        {"buffer": 0, "byteOffset": 36, "byteLength": 6},
                        {"buffer": 0, "byteOffset": 44, "byteLength": 8}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3",
                       "min": [0, 0, 0], "max": [2, 3, 1]},
                      {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "materials": [{"name": "wood"}],
        "nodes": [{"mesh": 0, "extras": {"die_loops": 0}}],
        "animations": [],
    }
    for name, seconds in clips:
        doc["accessors"].append({"bufferView": 2, "componentType": 5126, "count": 2, "type": "SCALAR",
                                 "min": [0.0], "max": [seconds]})
        doc["animations"].append({"name": name, "channels": [],
                                  "samplers": [{"input": len(doc["accessors"]) - 1, "output": 0}]})
    body = json.dumps(doc).encode()
    body += b" " * (-len(body) % 4)
    binary = positions + indices + times
    return (b"glTF" + struct.pack("<II", 2, 12 + 8 + len(body) + 8 + len(binary))
            + struct.pack("<I", len(body)) + b"JSON" + body + struct.pack("<I", len(binary)) + b"BIN\0" + binary)


class PackTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = self.temp.name
        propuestas.SPECS = os.path.join(root, "specs")
        propuestas.MODELS = os.path.join(root, "models")
        propuestas.PAGE = os.path.join(root, "page")
        propuestas.DATA = os.path.join(root, "page", "datos")
        propuestas.ANSWERS = os.path.join(root, "page", "respuestas.json")

    def tearDown(self):
        self.temp.cleanup()

    def family(self, name, catalog, models):
        os.makedirs(os.path.join(propuestas.SPECS, name))
        os.makedirs(os.path.join(propuestas.MODELS, name))
        with open(os.path.join(propuestas.SPECS, name, "catalogo.json"), "w", encoding="utf-8") as f:
            f.write(catalog if isinstance(catalog, str) else json.dumps(catalog))
        for model, data in models.items():
            with open(os.path.join(propuestas.MODELS, name, model + ".glb"), "wb") as f:
                f.write(data)

    def pack(self):
        with redirect_stdout(io.StringIO()):
            return propuestas.pack()

    def group(self, gid="bridge_a", models=("bridge_a",), proposals=1, category="Puentes"):
        return {"id": gid, "nombre": "Puente", "categoria": category, "descripcion": "Un puente.",
                "propuestas": [{"titulo": "T%d" % i, "detalle": "D"} for i in range(proposals)],
                "modelos": [{"id": m, "nombre": m} for m in models]}

    def test_reads_a_model(self):
        info = propuestas.glb_info(self.write_glb(tiny_glb([("walk", 1.5), ("die", 2.0)])))
        self.assertEqual(info["tris"], 1)
        self.assertEqual(info["medida"], [2, 1, 3])   # Width, depth, height: glTF is Y up.
        self.assertEqual([c["nombre"] for c in info["clips"]], ["walk", "die"])
        self.assertEqual([c["repite"] for c in info["clips"]], [True, False])
        self.assertEqual(info["clips"][0]["segundos"], 1.5)

    def write_glb(self, data):
        path = os.path.join(self.temp.name, "one.glb")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def test_rejects_what_is_not_a_glb(self):
        with self.assertRaises(ValueError):
            propuestas.glb_info(self.write_glb(b"not a model at all, just some text"))

    def test_packs_groups_and_models(self):
        self.family("bridges", {"grupos": [self.group(models=("bridge_a", "bridge_b"))]},
                    {"bridge_a": tiny_glb(), "bridge_b": tiny_glb([("open", 1.0)])})
        catalog = self.pack()
        self.assertEqual(catalog["problemas"], [])
        self.assertEqual(catalog["categorias"], ["Puentes"])
        group = catalog["grupos"][0]
        self.assertEqual(group["clave"], "bridges/bridge_a")
        self.assertEqual([m["id"] for m in group["modelos"]], ["bridge_a", "bridge_b"])
        script = os.path.join(propuestas.DATA, "modelos", "bridges__bridge_b.js")
        with open(script, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith('window.PROPUESTAS_MODELO("bridges/bridge_b","'))
        with open(propuestas.ANSWERS, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"version": 1, "grupos": {}})

    def test_a_broken_catalog_skips_only_its_family(self):
        self.family("bridges", {"grupos": [self.group()]}, {"bridge_a": tiny_glb()})
        self.family("walls", "{ this is not json", {})
        catalog = self.pack()
        self.assertEqual(len(catalog["grupos"]), 1)
        self.assertTrue(any(p.startswith("walls: catalogo.json") for p in catalog["problemas"]))

    def test_missing_and_loose_models_are_reported(self):
        self.family("bridges", {"grupos": [self.group(models=("bridge_a", "bridge_gone"))]},
                    {"bridge_a": tiny_glb(), "bridge_loose": tiny_glb(), "bridge_a_far": tiny_glb()})
        catalog = self.pack()
        self.assertEqual([m["id"] for m in catalog["grupos"][0]["modelos"]], ["bridge_a"])
        loose = [g for g in catalog["grupos"] if g["categoria"] == propuestas.UNCATALOGED]
        self.assertEqual([g["id"] for g in loose], ["bridge_loose"])   # The far model is not shown.
        self.assertEqual(len(catalog["problemas"]), 2)

    def test_keeps_at_most_four_proposals(self):
        self.family("bridges", {"grupos": [self.group(proposals=6)]}, {"bridge_a": tiny_glb()})
        self.assertEqual(len(self.pack()["grupos"][0]["propuestas"]), propuestas.MAX_PROPOSALS)

    def test_stars_groups_listed_apart_from_their_catalog(self):
        self.family("bridges", {"grupos": [self.group(), self.group("bridge_b", ("bridge_b",))]},
                    {"bridge_a": tiny_glb(), "bridge_b": tiny_glb()})
        with open(os.path.join(propuestas.SPECS, "destacados.json"), "w", encoding="utf-8") as f:
            json.dump({"bridges": ["bridge_b", "bridge_gone"]}, f)
        catalog = self.pack()
        self.assertEqual([g["destacado"] for g in catalog["grupos"]], [False, True])
        self.assertEqual(catalog["problemas"], ["destacados.json: bridges/bridge_gone no existe"])

    def test_repacking_removes_stale_models_and_keeps_answers(self):
        self.family("bridges", {"grupos": [self.group(models=("bridge_a", "bridge_b"))]},
                    {"bridge_a": tiny_glb(), "bridge_b": tiny_glb()})
        self.pack()
        with open(propuestas.ANSWERS, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "grupos": {"bridges/bridge_a": {"eleccion": "descartar"}}}, f)
        os.remove(os.path.join(propuestas.MODELS, "bridges", "bridge_b.glb"))
        self.pack()
        self.assertEqual(os.listdir(os.path.join(propuestas.DATA, "modelos")), ["bridges__bridge_a.js"])
        self.assertEqual(propuestas.load_answers(), {"bridges/bridge_a": {"eleccion": "descartar"}})

    def test_finds_a_loop_that_does_not_close(self):
        def with_track(values):
            data = bytearray(tiny_glb([("walk", 1.0)]))
            json_len = struct.unpack_from("<I", data, 12)[0]
            doc = json.loads(bytes(data[20:20 + json_len]))
            out = struct.pack("<6f", *values)
            start = 20 + json_len + 8
            offset = len(data) - start
            doc["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": 24})
            doc["accessors"].append({"bufferView": 3, "componentType": 5126, "count": 2, "type": "VEC3"})
            doc["animations"][0]["samplers"][0]["output"] = len(doc["accessors"]) - 1
            doc["animations"][0]["channels"] = [{"sampler": 0, "target": {"node": 0, "path": "translation"}}]
            body = json.dumps(doc).encode()
            body += b" " * (-len(body) % 4)
            binary = bytes(data[start:]) + out
            return (b"glTF" + struct.pack("<II", 2, 12 + 8 + len(body) + 8 + len(binary)) + struct.pack("<I", len(body)) + b"JSON" + body
                    + struct.pack("<I", len(binary)) + b"BIN\0" + binary)

        closed = propuestas.loop_gaps(self.write_glb(with_track((0, 0, 0, 0, 0, 0))))
        self.assertEqual(closed, {"walk": 0.0})
        jump = propuestas.loop_gaps(self.write_glb(with_track((0, 0, 0, 0, 0.5, 0))))
        self.assertAlmostEqual(jump["walk"], 0.5)

    def test_describes_an_answer(self):
        group = {"propuestas": [{"titulo": "Cruzar", "detalle": "Sin rodear."}]}
        lines = propuestas.describe({"eleccion": "propuesta", "indice": 0, "titulo": "Cruzar", "nota": "más ancho",
                                     "modelos": {"a": "favorito", "b": "descartado"}}, group)
        self.assertEqual(lines[0], "Función elegida: Cruzar")
        self.assertIn("Nota: más ancho", lines)
        self.assertIn("Variantes favoritas: a", lines)
        self.assertIn("Variantes descartadas: b", lines)
        self.assertEqual(propuestas.describe({}, group), [])


if __name__ == "__main__":
    unittest.main()
