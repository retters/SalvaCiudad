"""Generates the low-poly test models used by the phase 3 renderer test scene.

Writes binary glTF (.glb) files with flat-shaded geometry, materials and one
embedded PNG texture. Uses only the Python standard library, and the output
is byte-for-byte reproducible.

Usage: python tools/models/make_test_models.py <output folder>
"""

import json
import math
import os
import struct
import sys
import zlib


# --- Geometry helpers ------------------------------------------------------

class Mesh:
    """Flat-shaded triangles for one material."""

    def __init__(self):
        self.positions = []
        self.normals = []
        self.uvs = []

    def tri(self, a, b, c, uva=(0, 0), uvb=(1, 0), uvc=(0, 1)):
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
        n = (n[0] / length, n[1] / length, n[2] / length)
        for p, uv in ((a, uva), (b, uvb), (c, uvc)):
            self.positions.append(p)
            self.normals.append(n)
            self.uvs.append(uv)

    def quad(self, a, b, c, d, uv=((0, 1), (1, 1), (1, 0), (0, 0))):
        """Counter-clockwise quad a-b-c-d seen from outside."""
        self.tri(a, b, c, uv[0], uv[1], uv[2])
        self.tri(a, c, d, uv[0], uv[2], uv[3])


def cone(mesh, cx, cz, y0, y1, radius, sides, phase=0.0):
    top = (cx, y1, cz)
    ring = [(cx + radius * math.cos(phase + 2 * math.pi * i / sides), y0,
             cz + radius * math.sin(phase + 2 * math.pi * i / sides)) for i in range(sides)]
    for i in range(sides):
        a, b = ring[i], ring[(i + 1) % sides]
        mesh.tri(a, top, b)       # Side, outward.
        mesh.tri(a, b, (cx, y0, cz))  # Base, downward.


def prism(mesh, cx, cz, y0, y1, radius, sides):
    bottom = [(cx + radius * math.cos(2 * math.pi * i / sides), y0,
               cz + radius * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
    top = [(x, y1, z) for x, _, z in bottom]
    for i in range(sides):
        j = (i + 1) % sides
        mesh.quad(bottom[i], top[i], top[j], bottom[j])


def box(mesh, x0, y0, z0, x1, y1, z1, tile=1.0):
    u = (x1 - x0) / tile
    w = (z1 - z0) / tile
    h = (y1 - y0) / tile
    faces = [
        # Front (+z), back (-z), right (+x), left (-x).
        ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), u),
        ((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), u),
        ((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), w),
        ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0), w),
    ]
    for a, b, c, d, span in faces:
        mesh.quad(a, b, c, d, ((0, h), (span, h), (span, 0), (0, 0)))


# --- Texture ---------------------------------------------------------------

def png_rgb(width, height, pixel):
    rows = b"".join(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(width)) for y in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def timber_wall(x, y):
    """Plaster with a timber frame, 32x32, for a one-meter tile."""
    beam = x < 3 or x > 28 or y < 3 or y > 28 or abs(x - y) < 2
    if beam:
        return (92, 62, 38)
    shade = 228 - ((x * 7 + y * 13) % 11)
    return (shade, shade - 8, shade - 26)


# --- glTF writer -----------------------------------------------------------

def write_glb(path, parts, texture_png=None):
    """parts: list of (Mesh, material dict)."""
    binary = bytearray()
    buffer_views = []
    accessors = []

    def add_view(data, target=None):
        while len(binary) % 4:
            binary.append(0)
        view = {"buffer": 0, "byteOffset": len(binary), "byteLength": len(data)}
        if target:
            view["target"] = target
        binary.extend(data)
        buffer_views.append(view)
        return len(buffer_views) - 1

    def add_accessor(values, kind, components):
        flat = [c for v in values for c in v]
        data = struct.pack("<%df" % len(flat), *flat)
        accessor = {"bufferView": add_view(data, 34962), "componentType": 5126,
                    "count": len(values), "type": kind}
        if kind == "VEC3":
            accessor["min"] = [min(v[i] for v in values) for i in range(components)]
            accessor["max"] = [max(v[i] for v in values) for i in range(components)]
        accessors.append(accessor)
        return len(accessors) - 1

    primitives = []
    materials = []
    for mesh, material in parts:
        count = len(mesh.positions)
        indices = struct.pack("<%dH" % count, *range(count))
        index_view = add_view(indices, 34963)
        accessors.append({"bufferView": index_view, "componentType": 5123, "count": count, "type": "SCALAR"})
        index_accessor = len(accessors) - 1
        attributes = {
            "POSITION": add_accessor(mesh.positions, "VEC3", 3),
            "NORMAL": add_accessor(mesh.normals, "VEC3", 3),
            "TEXCOORD_0": add_accessor(mesh.uvs, "VEC2", 2),
        }
        materials.append(material)
        primitives.append({"attributes": attributes, "indices": index_accessor, "material": len(materials) - 1})

    doc = {
        "asset": {"version": "2.0", "generator": "SalvaCiudad make_test_models.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": os.path.splitext(os.path.basename(path))[0]}],
        "meshes": [{"primitives": primitives}],
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
    }
    if texture_png is not None:
        image_view = add_view(texture_png)
        doc["images"] = [{"bufferView": image_view, "mimeType": "image/png"}]
        doc["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
        doc["textures"] = [{"sampler": 0, "source": 0}]
    while len(binary) % 4:
        binary.append(0)
    doc["buffers"] = [{"byteLength": len(binary)}]

    json_bytes = json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes)
        f.write(struct.pack("<II", len(binary), 0x004E4942) + bytes(binary))


def material(name, rgb, texture=None, roughness=0.9):
    pbr = {"baseColorFactor": [rgb[0], rgb[1], rgb[2], 1.0], "metallicFactor": 0.0, "roughnessFactor": roughness}
    if texture is not None:
        pbr["baseColorTexture"] = {"index": texture}
    return {"name": name, "pbrMetallicRoughness": pbr}


# --- Models ------------------------------------------------------------------

def make_tree(folder):
    trunk = Mesh()
    prism(trunk, 0, 0, 0.0, 1.6, 0.18, 6)
    leaves = Mesh()
    cone(leaves, 0, 0, 1.2, 3.6, 1.3, 7, 0.0)
    cone(leaves, 0, 0, 2.4, 4.5, 1.0, 7, 0.4)
    cone(leaves, 0, 0, 3.4, 5.4, 0.7, 7, 0.8)
    write_glb(os.path.join(folder, "test_tree.glb"),
              [(trunk, material("bark", (0.36, 0.24, 0.15))), (leaves, material("leaves", (0.27, 0.48, 0.22)))])


def make_house(folder):
    walls = Mesh()
    box(walls, -2.0, 0.0, -1.5, 2.0, 2.4, 1.5)
    roof = Mesh()
    ridge_y = 3.9
    eave = 0.35
    x0, x1, z0, z1, y = -2.0 - eave, 2.0 + eave, -1.5 - eave, 1.5 + eave, 2.3
    roof.quad((x0, y, z1), (x1, y, z1), (x1, ridge_y, 0), (x0, ridge_y, 0))
    roof.quad((x1, y, z0), (x0, y, z0), (x0, ridge_y, 0), (x1, ridge_y, 0))
    # Gables, part of the walls.
    walls.tri((-2.0, 2.4, 1.5), (-2.0, 3.8, 0.0), (-2.0, 2.4, -1.5), (0, 0), (0.5, 1), (1, 0))
    walls.tri((2.0, 2.4, -1.5), (2.0, 3.8, 0.0), (2.0, 2.4, 1.5), (0, 0), (0.5, 1), (1, 0))
    chimney = Mesh()
    box(chimney, 1.0, 2.8, -0.9, 1.5, 4.5, -0.4)
    texture = png_rgb(32, 32, timber_wall)
    write_glb(os.path.join(folder, "test_house.glb"),
              [(walls, material("wall", (1.0, 1.0, 1.0), texture=0)),
               (roof, material("roof", (0.55, 0.22, 0.14))),
               (chimney, material("stone", (0.52, 0.5, 0.47)))],
              texture_png=texture)


def make_rock(folder):
    rock = Mesh()
    # A squashed, irregular octahedron-like boulder.
    top = (0.1, 1.0, -0.05)
    bottom = (0.0, 0.0, 0.0)
    ring = [(1.0, 0.35, 0.1), (0.3, 0.45, 0.9), (-0.8, 0.3, 0.6), (-0.9, 0.4, -0.4), (-0.1, 0.35, -1.0), (0.8, 0.3, -0.6)]
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        rock.tri(a, top, b)
        rock.tri(a, b, bottom)
    write_glb(os.path.join(folder, "test_rock.glb"), [(rock, material("rock", (0.55, 0.53, 0.5)))])


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(folder, exist_ok=True)
    make_tree(folder)
    make_house(folder)
    make_rock(folder)


if __name__ == "__main__":
    main()
