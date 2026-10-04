"""Fighters: those the town can raise (militia, archers, pikemen, the
guard and its captain, scouts, a battle mage, a war priest) and the humans
who attack it (bandits, raiders, cultists, a necromancer). Clips: idle,
walk, run and attack."""

from _folk import person

BLACK, BLOND, RED, GRAY, CHESTNUT = 0x2A2220, 0xD0A050, 0xA84A22, 0xB0ACA4, 0x6A3B2A
TAN, BROWN, PALE = 0xD99A6C, 0xB87850, 0xF6C8A0
# The town's livery, shared by its troops: blue with a gold trim.
TOWN, TOWN_DARK = 0x2E5AA8, 0x1E3E7A


def clips(attack, *more):
    return (("idle", "idle"), ("walk", "walk"), ("run", "run"), ("attack", attack)) + tuple(more)


def c(**colors):
    return colors


MODELS = {
    # --- The town's troops.
    "folk_militia": person(
        "folk_militia", hat_style="cap", tabard=True, right="spear", carry_r="staff", shield="round",
        colors=c(top=0x9A8A6A, bottom=0x5A4A3A, hat=0x70432B, accent=TOWN, hair=CHESTNUT), clips=clips("thrust")),
    "folk_militia_woman": person(
        "folk_militia_woman", female=True, height=1.72, hair_style="ponytail", hat_style="kettle", tabard=True,
        right="spear", carry_r="staff", shield="round",
        colors=c(top=0x9A8A6A, bottom=0x5A4A3A, accent=TOWN, hair=BLOND), clips=clips("thrust")),
    "folk_militia_pitchfork": person(
        "folk_militia_pitchfork", hat_style="straw", sleeves="short", right="pitchfork", carry_r="staff",
        extras=("pouch",), colors=c(top=0xB07A3A, bottom=0x4E5A3A, skin=TAN, hair=BLACK), clips=clips("thrust")),
    "folk_archer": person(
        "folk_archer", hat_style="hood", tabard=True, left="bow", carry_l="staff", back="quiver", boot=0.4,
        gloves="belt", colors=c(top=0x6A7A4A, bottom=0x4A4036, hat=TOWN_DARK, accent=TOWN, hair=CHESTNUT),
        clips=clips("shoot")),
    "folk_archer_woman": person(
        "folk_archer_woman", female=True, height=1.72, hair_style="ponytail", hat_style="feather", tabard=True,
        left="bow", carry_l="staff", back="quiver", boot=0.4,
        colors=c(top=0x6A7A4A, bottom=0x4A4036, hat=TOWN_DARK, accent=TOWN, hair=RED), clips=clips("shoot")),
    "folk_crossbowman": person(
        "folk_crossbowman", hat_style="kettle", tabard=True, armor="leather", right="crossbow", carry_r="aim",
        back="quiver", colors=c(top=0x6A6A72, bottom=0x4A4036, accent=TOWN, hair=BLACK, skin=TAN),
        clips=clips("aim")),
    "folk_pikeman": person(
        "folk_pikeman", build=1.08, hat_style="kettle", armor="breastplate", right="pike", carry_r="staff",
        extras=("scabbard",), colors=c(top=TOWN, bottom=TOWN_DARK, hair=CHESTNUT), clips=clips("thrust")),
    "folk_town_guard": person(
        "folk_town_guard", build=1.1, hat_style="helm", armor="breastplate", tabard=True, cape="short",
        right="halberd", carry_r="staff", extras=("scabbard",), boot=0.42, gloves="metal_dark",
        colors=c(top=0x6A6A72, bottom=0x3E3A44, accent=TOWN, cape=TOWN, hair=BLACK), clips=clips("thrust")),
    "folk_town_guard_woman": person(
        "folk_town_guard_woman", female=True, hair_style="ponytail", hat_style="helm", armor="breastplate",
        tabard=True, right="halberd", carry_r="staff", boot=0.42, gloves="metal_dark",
        colors=c(top=0x6A6A72, bottom=0x3E3A44, accent=TOWN, hair=BLOND), clips=clips("thrust")),
    "folk_guard_swordsman": person(
        "folk_guard_swordsman", build=1.1, hat_style="helm", armor="breastplate", tabard=True, right="sword",
        carry_r="low", shield="kite", carry_l="guard", boot=0.42, gloves="metal_dark",
        colors=c(top=0x6A6A72, bottom=0x3E3A44, accent=TOWN, hair=CHESTNUT), clips=clips("strike")),
    "folk_captain": person(
        "folk_captain", build=1.14, shoulder=0.195, hat_style="plume", beard="short", armor="pauldrons",
        cape="long", right="sword", carry_r="low", shield="kite", carry_l="guard", boot=0.45, gloves="metal_dark",
        extras=("medal",), colors=c(top=0x4A4A56, bottom=0x2A2630, accent=0xB8382E, cape=0xB8382E, hair=CHESTNUT,
                                    metal=0xB8B4C4),
        clips=clips("strike", ("command", "wave"))),
    "folk_standard_bearer": person(
        "folk_standard_bearer", hat_style="kettle", armor="leather", tabard=True, right="banner", carry_r="staff",
        extras=("scabbard",), colors=c(top=0x6A6A72, bottom=0x3E3A44, accent=TOWN, hair=BLOND),
        clips=clips("wave")),
    "folk_scout": person(
        "folk_scout", build=0.95, hat_style="hood", cape="short", right="dagger", carry_r="low",
        extras=("satchel", "bedroll"), boot=0.42,
        colors=c(top=0x6A5A3E, bottom=0x4E5A3A, hat=0x4E5A3A, cape=0x4E5A3A, accent=0x8A7A5A, hair=BLACK,
                 skin=TAN), clips=clips("strike")),
    "folk_scout_woman": person(
        "folk_scout_woman", female=True, build=0.95, height=1.72, hair_style="ponytail", hat_style="hood",
        cape="short", left="bow", carry_l="staff", back="quiver", extras=("satchel",), boot=0.42,
        colors=c(top=0x6A5A3E, bottom=0x4E5A3A, hat=0x4E5A3A, cape=0x4E5A3A, hair=RED), clips=clips("shoot")),
    "folk_battle_mage": person(
        "folk_battle_mage", hat_style="wizard", beard="long", skirt=0.3, skirt_mat="top", cape="short",
        collar="gold", right="crystal_staff", carry_r="staff", extras=("pouch", "satchel"),
        colors=c(top=0x4A3A9A, bottom=0x4A3A9A, hat=0x35287A, cape=0x35287A, hair=GRAY, glass=0x6AE0FF),
        clips=clips("cast")),
    "folk_battle_mage_woman": person(
        "folk_battle_mage_woman", female=True, height=1.72, hair_style="long", hat_style="wizard", skirt=0.3,
        skirt_mat="top", right="crystal_staff", carry_r="staff", extras=("pouch",),
        colors=c(top=0xA83A4A, bottom=0xA83A4A, hat=0x7A2A3A, hair=BLACK, glass=0xFFA03A), clips=clips("cast")),
    "folk_war_priest": person(
        "folk_war_priest", build=1.12, hair_style="balding", beard="full", armor="breastplate", tabard=True,
        skirt=0.45, skirt_mat="apron", right="mace", carry_r="low", shield="kite", carry_l="guard",
        extras=("medal",), gloves="metal_dark",
        colors=c(top=0x8A8A96, bottom=0x8A8A96, accent=0xEEE8DC, apron=0xEEE8DC, hair=GRAY, gold=0xE2B13C),
        clips=clips("strike", ("bless", "cast"))),
    # --- Those who attack the town.
    "folk_bandit": person(
        "folk_bandit", hat_style="bandana", mask=True, sleeves="short", armor="leather", right="club",
        carry_r="low", extras=("pouch",), colors=c(top=0x5A4A3E, bottom=0x3E3A36, accent=0x7A2A2A, hair=BLACK,
                                                   skin=TAN), clips=clips("strike")),
    "folk_bandit_woman": person(
        "folk_bandit_woman", female=True, hair_style="ponytail", mask=True, sleeves="short", armor="leather",
        right="dagger", carry_r="low", left="dagger", carry_l="low", boot=0.42,
        colors=c(top=0x4A3E4A, bottom=0x35333A, hair=RED), clips=clips("strike")),
    "folk_bandit_archer": person(
        "folk_bandit_archer", build=0.95, hat_style="hood", mask=True, left="bow", carry_l="staff", back="quiver",
        colors=c(top=0x4E4A3A, bottom=0x3E3A36, hat=0x35333A, hair=BLACK), clips=clips("shoot")),
    "folk_bandit_chief": person(
        "folk_bandit_chief", build=1.25, shoulder=0.205, height=1.88, hat_style="bandana", beard="full",
        collar="fur", armor="pauldrons", cape="short", right="sword", carry_r="low", shield="round",
        carry_l="guard", extras=("pouch", "purse"), boot=0.42,
        colors=c(top=0x4A2E2E, bottom=0x2E2A2A, accent=0x7A2A2A, cape=0x5A4636, fur=0x5A4636, metal=0x5A5A62,
                 hair=RED), clips=clips("strike")),
    "folk_raider_torch": person(
        "folk_raider_torch", hair_style="bald", beard="short", sleeves="none", collar="fur", right="torch",
        carry_r="raised", left="club", carry_l="low", boot=0.4,
        colors=c(top=0x6A4A36, bottom=0x4A3E36, fur=0x7A6A52, skin=BROWN, hair=BLACK), clips=clips("strike")),
    "folk_raider_axe": person(
        "folk_raider_axe", build=1.18, hair_style="long", beard="long", sleeves="none", collar="fur", right="axe",
        carry_r="shoulder", shield="round", boot=0.4,
        colors=c(top=0x5A5A4A, bottom=0x4A3E36, fur=0x8A8478, accent=0x3E6A4A, hair=BLOND), clips=clips("chop")),
    "folk_cultist": person(
        "folk_cultist", hat_style="hood", mask=True, skirt=0.1, skirt_mat="top", right="dagger", carry_r="low",
        left="torch", carry_l="raised", extras=("medal",),
        colors=c(top=0x6A1E2A, bottom=0x6A1E2A, hat=0x4A1420, gold=0x2A2630, skin=PALE, belt=0xB89A62),
        clips=clips("strike", ("chant", "cast"))),
    "folk_necromancer": person(
        "folk_necromancer", build=0.9, height=1.84, hair_style="bald", hat_style="hood", beard="long",
        skirt=0.06, skirt_mat="top", cape="long", collar="bone", right="skull_staff", carry_r="staff",
        left="book", carry_l="chest", extras=("pouch",),
        colors=c(top=0x2A2630, bottom=0x2A2630, hat=0x1E1A24, cape=0x3A2A4A, skin=0xC8D0C0, hair=0xE8E4DC,
                 red=0x4A2A6A, eye=0x6AE0A0), clips=clips("cast")),
}
