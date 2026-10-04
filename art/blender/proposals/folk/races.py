"""The eight non-human races as townspeople: for each one a villager with
a trade's tool and plain clothes, and a guard or warrior with a weapon and
a shield. They are the game's own race characters (art/blender/people),
recolored and equipped; nothing of their bodies or skeletons changes."""

from _folk import race_variant

from catfolk import Catfolk
from dark_elf_man import DarkElfMan
from dark_elf_woman import DarkElfWoman
from dwarf_man import DwarfMan
from dwarf_woman import DwarfWoman
from foxfolk import Foxfolk
from frogfolk import Frogfolk
from high_elf_man import HighElfMan
from high_elf_woman import HighElfWoman
from lizardfolk import Lizardfolk
from orc import Orc

IDLE, WALK, RUN = ("idle", "idle"), ("walk", "walk"), ("run", "run")


def work(pose):
    return (IDLE, WALK, ("work", pose))


def fight(pose):
    return (IDLE, WALK, RUN, ("attack", pose))


MODELS = {
    "folk_catfolk_villager": race_variant(
        Catfolk, "folk_catfolk_villager", recolor={"blue": 0xC8A24A}, right="hoe", carry_r="shoulder",
        clip_names=work("dig")),
    "folk_catfolk_guard": race_variant(
        Catfolk, "folk_catfolk_guard", accent=0x3F68D6, right="spear", carry_r="staff", shield="round",
        clip_names=fight("thrust")),
    "folk_foxfolk_villager": race_variant(
        Foxfolk, "folk_foxfolk_villager", recolor={"teal": 0x8A7A4A, "teal_dark": 0x6A5A36}, left="bow",
        carry_l="staff", clip_names=work("shoot")),
    "folk_foxfolk_guard": race_variant(
        Foxfolk, "folk_foxfolk_guard", recolor={"teal": 0xA8322E, "teal_dark": 0x7A2420}, accent=0xA8322E,
        right="sword", carry_r="low", shield="kite", carry_l="guard", clip_names=fight("strike")),
    "folk_frogfolk_villager": race_variant(
        Frogfolk, "folk_frogfolk_villager", recolor={"top": 0x7A9A4A}, right="rod", carry_r="low",
        clip_names=(IDLE, WALK, ("work", "fish_stand"), ("cast", "fish_cast"))),
    "folk_frogfolk_guard": race_variant(
        Frogfolk, "folk_frogfolk_guard", recolor={"top": 0x8A2E2A}, accent=0xF2C820, right="spear",
        carry_r="staff", shield="round", clip_names=fight("thrust")),
    "folk_lizardfolk_villager": race_variant(
        Lizardfolk, "folk_lizardfolk_villager", recolor={"scarf": 0xC8A24A, "steel": 0x8A6A4A}, right="pick",
        carry_r="shoulder", clip_names=work("dig")),
    "folk_lizardfolk_guard": race_variant(
        Lizardfolk, "folk_lizardfolk_guard", accent=0xB3383C, right="halberd", carry_r="staff", shield="round",
        clip_names=fight("thrust")),
    "folk_orc_villager": race_variant(
        Orc, "folk_orc_villager", right="axe", carry_r="shoulder", clip_names=work("chop")),
    "folk_orc_warrior": race_variant(
        Orc, "folk_orc_warrior", recolor={"leather": 0x5A5A66, "leather_dark": 0x3E3E4A}, accent=0x8A2E2A,
        right="club", carry_r="low", shield="round", carry_l="guard", clip_names=fight("strike")),
    "folk_dwarf_villager": race_variant(
        DwarfMan, "folk_dwarf_villager", recolor={"tunic": 0x6A7A8A}, right="pick", carry_r="shoulder",
        left="lantern", carry_l="hang", clip_names=work("dig")),
    "folk_dwarf_villager_woman": race_variant(
        DwarfWoman, "folk_dwarf_villager_woman", recolor={"dress": 0xB8823A}, right="mug", carry_r="raised",
        clip_names=work("wave")),
    "folk_dwarf_guard": race_variant(
        DwarfMan, "folk_dwarf_guard", recolor={"tunic": 0x2E5AA8}, accent=0x2E5AA8, right="axe",
        carry_r="shoulder", shield="round", clip_names=fight("chop")),
    "folk_high_elf_villager": race_variant(
        HighElfWoman, "folk_high_elf_villager", left="basket", carry_l="hang", clip_names=work("sow")),
    "folk_high_elf_guard": race_variant(
        HighElfMan, "folk_high_elf_guard", accent=0xC22B33, right="spear", carry_r="staff", shield="kite",
        clip_names=fight("thrust")),
    "folk_high_elf_archer": race_variant(
        HighElfMan, "folk_high_elf_archer", recolor={"red": 0x3E7A4A, "inner": 0x244A2C}, left="bow",
        carry_l="staff", clip_names=fight("shoot")),
    "folk_dark_elf_villager": race_variant(
        DarkElfWoman, "folk_dark_elf_villager", left="lantern", carry_l="hang", right="staff", carry_r="staff",
        clip_names=work("wave")),
    "folk_dark_elf_guard": race_variant(
        DarkElfMan, "folk_dark_elf_guard", accent=0x4E3672, right="sword", carry_r="low", shield="kite",
        carry_l="guard", clip_names=fight("strike")),
}
