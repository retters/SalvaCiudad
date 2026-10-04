"""The models of the family: id -> builder, and what the catalog says of
each one. A builder is a function fn(pen) that draws into the pen and
returns a kit.Mech or None."""

import _kit as kit
from wallkit import COLORS, FAMILY, Pen

MODELS = {}    # id -> function without arguments that builds and saves.
ENTRIES = []   # (group id, model dict for the catalog), in order.


def make(mid, fn):
    mb = kit.begin()
    mech = fn(Pen(mb))
    kit.save(mb, FAMILY, mid, COLORS, mech=mech)


def reg(group, mid, nombre, fn, material=None, anim=None, nota=None):
    assert mid not in MODELS, "duplicate id " + mid
    MODELS[mid] = lambda: make(mid, fn)
    entry = {"id": mid, "nombre": nombre}
    if material:
        entry["material"] = material
    if anim:
        entry["animaciones"] = anim
    if nota:
        entry["nota"] = nota
    ENTRIES.append((group, entry))
