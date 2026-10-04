"""People of the town's great days: a wedding couple, festival dancers and
the royal party of a procession. All dance or greet in a clip of their own."""

from _folk import person

IDLE, WALK = ("idle", "idle"), ("walk", "walk")
BLACK, BLOND, RED, GRAY, CHESTNUT = 0x2A2220, 0xD0A050, 0xA84A22, 0xB0ACA4, 0x6A3B2A


def c(**colors):
    return colors


MODELS = {
    "folk_bride": person(
        "folk_bride", female=True, height=1.7, hair_style="long", hat_style="veil", skirt=0.05, skirt_mat="top",
        right="flower", carry_r="raised",
        colors=c(top=0xF4F0E8, bottom=0xF4F0E8, hair=CHESTNUT, shoes=0xE8E0D0, belt=0xE2B13C, glass=0xD86A7A),
        clips=(IDLE, WALK, ("dance", "dance"), ("greet", "wave"))),
    "folk_groom": person(
        "folk_groom", hat_style="feather", collar="white", cape="short", extras=("medal",), boot=0.4,
        right="flower", carry_r="low",
        colors=c(top=0x2E4A7A, bottom=0x2A2630, hat=0x2E4A7A, cape=0x8A2E2A, accent=0xF4F0E8, hair=BLACK,
                 shoes=0x2A2630), clips=(IDLE, WALK, ("dance", "dance"), ("greet", "wave"))),
    "folk_dancer": person(
        "folk_dancer", hair_style="short", hat_style="bandana", sleeves="short", collar="accent", boot=0.4,
        colors=c(top=0xF0E8D8, bottom=0x8A2E2A, accent=0xE2B13C, hair=BLACK, skin=0xD99A6C),
        clips=(IDLE, WALK, ("dance", "dance"))),
    "folk_dancer_woman": person(
        "folk_dancer_woman", female=True, height=1.7, hair_style="ponytail", hat_style="circlet", sleeves="short",
        skirt=0.42, apron=True, right="flower", carry_r="raised",
        colors=c(top=0xF0E8D8, bottom=0xC8382E, apron=0x3E8A5A, hair=RED, glass=0xE2B13C),
        clips=(IDLE, WALK, ("dance", "dance"))),
    "folk_dancer_woman_blue": person(
        "folk_dancer_woman_blue", female=True, height=1.66, hair_style="long", hat_style="scarf", sleeves="short",
        skirt=0.42, apron=True,
        colors=c(top=0xF0E8D8, bottom=0x2E5AA8, apron=0xE2B13C, hat=0xC8382E, hair=BLOND),
        clips=(IDLE, WALK, ("dance", "dance"))),
    "folk_jester": person(
        "folk_jester", build=0.92, hat_style="wizard", hair_style="bald", collar="accent", right="bell",
        carry_r="raised", left="bell", carry_l="raised", boot=0.2,
        colors=c(top=0xC8382E, bottom=0x3E8A5A, hat=0x3E8A5A, accent=0xE2B13C, shoes=0xC8382E),
        clips=(IDLE, WALK, ("dance", "dance"), ("work", "wave"))),
    "folk_king": person(
        "folk_king", belly=0.5, build=1.08, hat_style="crown", hair_style="long", beard="full", skirt=0.3,
        skirt_mat="top", cape="long", collar="fur", right="mace", carry_r="low", extras=("medal",),
        colors=c(top=0x7A2E8A, bottom=0x7A2E8A, cape=0xB8282E, fur=0xF4F0E8, hair=GRAY, metal=0xE2B13C,
                 metal_dark=0xC8962E, wood_dark=0xE2B13C, shoes=0x4A2A2A), clips=(IDLE, WALK, ("greet", "wave"))),
    "folk_queen": person(
        "folk_queen", female=True, height=1.74, hat_style="crown", hair_style="long", skirt=0.05,
        skirt_mat="top", cape="long", collar="fur", right="flower", carry_r="low",
        colors=c(top=0x2E7A8A, bottom=0x2E7A8A, cape=0xB8282E, fur=0xF4F0E8, hair=BLOND),
        clips=(IDLE, WALK, ("greet", "wave"))),
}
