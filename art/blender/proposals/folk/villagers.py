"""Villagers by trade: one human per trade (and a woman where the trade
reads differently), each with its tool in the hand, told apart from the
game's camera by silhouette, tool and color. Every one has `idle` and
`walk`; most have a `work` clip that suits the trade."""

from _folk import person

IDLE = ("idle", "idle")
WALK = ("walk", "walk")
RUN = ("run", "run")


def clips(work=None, *more):
    out = [IDLE, WALK]
    if work:
        out.append(("work", work))
    return tuple(out) + tuple(more)


# Skin and hair tones, to mix along the trades.
PALE, TAN, BROWN, DARK = 0xF6C8A0, 0xD99A6C, 0xB87850, 0x8A5A3C
BLACK, BLOND, RED, GRAY, WHITE, CHESTNUT = 0x2A2220, 0xD0A050, 0xA84A22, 0xB0ACA4, 0xE8E4DC, 0x6A3B2A


def c(**colors):
    return colors


MODELS = {
    # --- Field and forest.
    "folk_farmer": person(
        "folk_farmer", hat_style="straw", sleeves="short", right="hoe", carry_r="shoulder", extras=("pouch",),
        colors=c(top=0x7A9A4A, bottom=0x6A5238, skin=TAN), clips=clips("dig")),
    "folk_farmer_woman": person(
        "folk_farmer_woman", female=True, height=1.7, hair_style="long", hat_style="scarf", sleeves="short",
        skirt=0.3, apron=True, left="basket", carry_l="hang",
        colors=c(top=0xC8A24A, bottom=0x7A5A3A, hat=0xB8382E, hair=BLOND, apron=0xE0D8C0), clips=clips("sow")),
    "folk_farmer_pitchfork": person(
        "folk_farmer_pitchfork", hat_style="straw", beard="short", right="pitchfork", carry_r="staff",
        colors=c(top=0xB07A3A, bottom=0x4E5A3A, skin=BROWN, hair=BLACK), clips=clips("dig")),
    "folk_reaper": person(
        "folk_reaper", hat_style="straw", sleeves="none", right="scythe", carry_r="staff",
        colors=c(top=0xD8C8A0, bottom=0x7A6A4A, hair=RED), clips=clips("dig")),
    "folk_woodcutter": person(
        "folk_woodcutter", build=1.12, hat_style="cap", beard="full", right="axe", carry_r="shoulder",
        colors=c(top=0xA8402E, bottom=0x4A4036, hat=0x4A6A3A, hair=CHESTNUT), clips=clips("chop")),
    "folk_woodcutter_woman": person(
        "folk_woodcutter_woman", female=True, height=1.72, hair_style="ponytail", sleeves="short", right="axe",
        carry_r="shoulder", colors=c(top=0x3E7A4A, bottom=0x5A4632, hair=RED), clips=clips("chop")),
    "folk_hunter": person(
        "folk_hunter", hat_style="hood", cape="short", left="bow", carry_l="staff", back="quiver",
        extras=("pouch",), boot=0.42,
        colors=c(top=0x5A7A3E, bottom=0x5E4A32, hat=0x3E5A30, cape=0x3E5A30, hair=CHESTNUT), clips=clips("shoot")),
    "folk_hunter_woman": person(
        "folk_hunter_woman", female=True, height=1.72, hair_style="ponytail", hat_style="feather", left="bow",
        carry_l="staff", back="quiver", boot=0.42,
        colors=c(top=0x7A5A36, bottom=0x4A5A3A, hat=0x4A6A3A, hair=BLACK, skin=TAN), clips=clips("shoot")),
    "folk_shepherd": person(
        "folk_shepherd", hat_style="straw", cape="short", beard="short", right="crook", carry_r="staff",
        colors=c(top=0xD8D0B8, bottom=0x7A6A52, cape=0x8A7A5A, hair=GRAY), clips=clips("wave")),
    "folk_shepherdess": person(
        "folk_shepherdess", female=True, height=1.68, hair_style="long", hat_style="scarf", skirt=0.32,
        right="crook", carry_r="staff", colors=c(top=0xE0D8C8, bottom=0x4E7AA0, hat=0xE0D8C8, hair=BLOND),
        clips=clips("wave")),
    "folk_fisher": person(
        "folk_fisher", hat_style="straw", sleeves="short", legs="bare", boot=0.0, right="rod", carry_r="low",
        back="basket_back", extras=("fish",),
        colors=c(top=0x4E8AA8, bottom=0x4E8AA8, shoes=TAN, skin=TAN, green=0x8A9AA8), clips=clips(
            "fish_stand", ("cast", "fish_cast"))),
    "folk_fisher_woman": person(
        "folk_fisher_woman", female=True, height=1.7, hair_style="bun", hat_style="scarf", sleeves="short",
        skirt=0.45, right="rod", carry_r="low", extras=("fish",),
        colors=c(top=0xE0D8C8, bottom=0x3E6A8A, hat=0x3E6A8A, hair=BLACK, skin=BROWN), clips=clips(
            "fish_stand", ("cast", "fish_cast"))),
    # --- Mine and workshop.
    "folk_miner": person(
        "folk_miner", build=1.08, hat_style="cap", beard="short", sleeves="short", right="pick",
        carry_r="shoulder", left="lantern", carry_l="hang",
        colors=c(top=0x7A7468, bottom=0x4A4640, hat=0x5A5A62, hair=BLACK, skin=TAN), clips=clips("dig")),
    "folk_blacksmith": person(
        "folk_blacksmith", build=1.22, shoulder=0.2, hair_style="bald", beard="full", sleeves="none", apron=True,
        right="hammer", carry_r="low", gloves="belt",
        colors=c(top=0x6A5A4A, bottom=0x3E3A3A, apron=0x5E3F36, hair=BLACK, skin=BROWN), clips=clips("work")),
    "folk_blacksmith_woman": person(
        "folk_blacksmith_woman", female=True, build=1.1, hair_style="bun", hat_style="bandana", sleeves="short",
        apron=True, right="hammer", carry_r="low", gloves="belt",
        colors=c(top=0x8A8A92, bottom=0x3E3A3A, apron=0x5E3F36, accent=0xC8502E, hair=RED), clips=clips("work")),
    "folk_mason": person(
        "folk_mason", hat_style="cap", apron=True, right="trowel", carry_r="low", left="bucket", carry_l="hang",
        colors=c(top=0xB8A888, bottom=0x6A6258, hat=0xE0D8C8, apron=0x9A9488, glass=0x9A9488), clips=clips("work")),
    "folk_builder": person(
        "folk_builder", build=1.1, hair_style="short", sleeves="short", right="mallet", carry_r="low",
        extras=("pouch",), colors=c(top=0xC8802E, bottom=0x5A4A3A, hair=BLOND, skin=TAN), clips=clips("work")),
    "folk_carpenter": person(
        "folk_carpenter", hat_style="cap", beard="short", apron=True, right="saw", carry_r="low",
        extras=("pouch",), colors=c(top=0x4E6A8A, bottom=0x5A4632, hat=0x8A6038, apron=0xA8824E, hair=CHESTNUT),
        clips=clips("work")),
    # --- Food.
    "folk_baker": person(
        "folk_baker", belly=0.5, hat_style="toque", sleeves="short", apron=True, right="peel", carry_r="staff",
        colors=c(top=0xE8E0D0, bottom=0x8A7A6A, apron=0xF4F0E8, hair=BLOND), clips=clips("wave")),
    "folk_baker_woman": person(
        "folk_baker_woman", female=True, height=1.68, belly=0.3, hair_style="bun", hat_style="coif", skirt=0.3,
        apron=True, right="rolling_pin", carry_r="low", left="basket", carry_l="hang",
        colors=c(top=0xC87A5A, bottom=0x8A5A4A, apron=0xF4F0E8, green=0xC98A46, hair=CHESTNUT),
        clips=clips("work")),
    "folk_miller": person(
        "folk_miller", belly=0.3, hat_style="cap", apron=True, back="sack",
        colors=c(top=0xD8D0C0, bottom=0xB8A888, hat=0xEEE8DC, apron=0xEEE8DC, hair=GRAY, shoes=0x8A7A6A),
        clips=clips("work")),
    "folk_innkeeper": person(
        "folk_innkeeper", belly=1.0, build=1.1, hair_style="balding", beard="short", sleeves="short", apron=True,
        right="mug", carry_r="raised", colors=c(top=0x8A3A3A, bottom=0x4A4036, apron=0xD8CFB8, hair=CHESTNUT),
        clips=clips("wave")),
    "folk_innkeeper_woman": person(
        "folk_innkeeper_woman", female=True, belly=0.6, hair_style="bun", skirt=0.28, apron=True, right="mug",
        carry_r="raised", left="mug", carry_l="raised",
        colors=c(top=0x4E7A5A, bottom=0x6A3A3A, apron=0xE8E0D0, hair=RED), clips=clips("wave")),
    "folk_brewer": person(
        "folk_brewer", belly=0.6, hat_style="cap", beard="full", apron=True, right="ladle", carry_r="low",
        left="bucket", carry_l="hang",
        colors=c(top=0xB88A3A, bottom=0x5A4632, hat=0x6A4A2A, apron=0x7A5A3A, glass=0xD8A83A, hair=BLOND),
        clips=clips("work")),
    # --- Haulage.
    "folk_carrier": person(
        "folk_carrier", build=1.1, hat_style="cap", sleeves="short", back="load", right="staff", carry_r="staff",
        hunch=9.0, boot=0.2, colors=c(top=0x9A7A4A, bottom=0x5A4A3A, hat=0x7A5636, accent=0x4E7AA0, skin=TAN),
        clips=clips()),
    "folk_carrier_woman": person(
        "folk_carrier_woman", female=True, hair_style="ponytail", sleeves="short", back="basket_back",
        left="bucket", carry_l="hang", right="bucket", carry_r="hang", hunch=4.0,
        colors=c(top=0xA85A3A, bottom=0x5A5A4A, hair=BLACK, skin=BROWN), clips=clips()),
    # --- Trade, learning and the town's offices.
    "folk_merchant": person(
        "folk_merchant", belly=0.7, hat_style="feather", beard="short", skirt=0.3, skirt_mat="top", collar="fur",
        left="scales", carry_l="raised", extras=("purse", "medal"),
        colors=c(top=0x7A3A8A, bottom=0x7A3A8A, hat=0x4A2A6A, accent=0xE2B13C, hair=BLACK), clips=clips("sow")),
    "folk_merchant_woman": person(
        "folk_merchant_woman", female=True, hair_style="bun", hat_style="circlet", skirt=0.12, collar="fur",
        left="scales", carry_l="raised", extras=("purse",),
        colors=c(top=0x2E7A7A, bottom=0x1E5A5A, hair=CHESTNUT, skin=TAN), clips=clips("sow")),
    "folk_healer": person(
        "folk_healer", female=True, height=1.7, hair_style="long", hat_style="coif", skirt=0.2, apron=True,
        left="basket", carry_l="hang", extras=("pouch",),
        colors=c(top=0x5A9A6A, bottom=0x3E7A52, apron=0xF0ECE0, hair=CHESTNUT), clips=clips("sow")),
    "folk_healer_man": person(
        "folk_healer_man", hair_style="balding", beard="short", hat_style="hood", skirt=0.2, skirt_mat="top",
        left="hand_out", carry_l="chest", right="ladle", carry_r="low", extras=("pouch", "satchel"),
        colors=c(top=0x5A8A8A, bottom=0x5A8A8A, hat=0x3E6A6A, hair=GRAY), clips=clips("write")),
    "folk_priest": person(
        "folk_priest", hat_style="mitre", hair_style="balding", skirt=0.08, skirt_mat="top", collar="gold",
        right="holy_staff", carry_r="staff", extras=("medal",),
        colors=c(top=0xEEE8DC, bottom=0xEEE8DC, hair=GRAY, shoes=0x8A6038), clips=clips("cast")),
    "folk_priestess": person(
        "folk_priestess", female=True, height=1.72, hair_style="long", hat_style="circlet", skirt=0.08,
        skirt_mat="top", collar="gold", right="holy_staff", carry_r="staff",
        colors=c(top=0xEEE8DC, bottom=0xEEE8DC, hair=BLOND, shoes=0x8A6038), clips=clips("cast")),
    "folk_monk": person(
        "folk_monk", belly=0.5, hair_style="balding", hat_style=None, skirt=0.1, skirt_mat="top", collar="top",
        left="book", carry_l="chest", colors=c(top=0x7A5A3A, bottom=0x7A5A3A, belt=0xD8C8A0, hair=CHESTNUT),
        clips=clips("write")),
    "folk_scholar": person(
        "folk_scholar", hair_style="balding", beard="long", hat_style="cap", skirt=0.12, skirt_mat="top",
        left="book", carry_l="chest", right="quill", carry_r="low",
        colors=c(top=0x2E4A8A, bottom=0x2E4A8A, hat=0x1E2E5A, hair=WHITE, red=0x8A2E2A), clips=clips("write")),
    "folk_teacher": person(
        "folk_teacher", female=True, height=1.7, hair_style="bun", skirt=0.14, collar="white", left="book",
        carry_l="chest", right="pointer", carry_r="low",
        colors=c(top=0x4A4A6A, bottom=0x3A3A52, hair=GRAY, red=0x3E7A4A), clips=clips("wave")),
    "folk_tax_collector": person(
        "folk_tax_collector", belly=0.4, hat_style="feather", hair_style="short", collar="white", left="scroll",
        carry_l="chest", right="quill", carry_r="low", extras=("purse", "keys"),
        colors=c(top=0x2A2630, bottom=0x4A2A3A, hat=0x2A2630, accent=0xE2B13C, hair=BLACK, skin=PALE),
        clips=clips("write")),
    "folk_tax_collector_chest": person(
        "folk_tax_collector_chest", belly=0.5, hat_style="cap", beard="short", collar="white", left="chest",
        carry_l="hang", extras=("purse", "keys", "medal"),
        colors=c(top=0x4A2A3A, bottom=0x2A2630, hat=0x4A2A3A, hair=GRAY), clips=clips("sow")),
    "folk_town_crier": person(
        "folk_town_crier", belly=0.3, hat_style="feather", cape="short", right="bell", carry_r="raised",
        left="scroll", carry_l="chest",
        colors=c(top=0xB8382E, bottom=0x2A2630, hat=0x2A2630, cape=0x2E4A8A, accent=0xE2B13C, hair=CHESTNUT),
        clips=clips("wave")),
    "folk_bard": person(
        "folk_bard", hat_style="feather", hair_style="long", cape="short", extras=("lute",), boot=0.4,
        colors=c(top=0xC8A02E, bottom=0x7A2E5A, hat=0x2E7A5A, cape=0x2E7A5A, accent=0xE8E0D0, hair=BLOND),
        clips=clips("play", ("dance", "dance"))),
    "folk_bard_woman": person(
        "folk_bard_woman", female=True, height=1.7, hat_style="feather", hair_style="long", skirt=0.4,
        extras=("lute",), colors=c(top=0xB8382E, bottom=0x2E5A8A, hat=0x7A2E5A, accent=0xE2B13C, hair=RED),
        clips=clips("play", ("dance", "dance"))),
    "folk_gravedigger": person(
        "folk_gravedigger", hat_style="hood", beard="short", right="shovel", carry_r="shoulder", left="lantern",
        carry_l="hang", hunch=7.0,
        colors=c(top=0x4A4A52, bottom=0x35333A, hat=0x35333A, hair=GRAY, skin=PALE), clips=clips("dig")),
    # --- Ages and stations.
    "folk_child_boy": person(
        "folk_child_boy", height=1.18, head_size=1.3, sleeves="short", legs="bare", boot=0.12, right="dagger",
        carry_r="low", colors=c(top=0x4E8AA8, bottom=0x7A5A3A, hair=BLOND, metal=0x8A6038, gold=0x8A6038,
                                belt=0x70432B),
        clips=clips(None, RUN, ("play", "strike"))),
    "folk_child_girl": person(
        "folk_child_girl", female=True, height=1.14, head_size=1.3, hair_style="ponytail", sleeves="short",
        skirt=0.5, legs="bare", boot=0.12, right="flower", carry_r="raised",
        colors=c(top=0xD86A7A, bottom=0xD86A7A, hair=CHESTNUT), clips=clips(None, RUN, ("play", "dance"))),
    "folk_elder": person(
        "folk_elder", height=1.7, hair_style="balding", beard="long", right="cane", carry_r="cane", hunch=15.0,
        skirt=0.4, skirt_mat="top", colors=c(top=0x7A7A8A, bottom=0x5A5A62, hair=WHITE, skin=PALE), clips=clips()),
    "folk_elder_woman": person(
        "folk_elder_woman", female=True, height=1.6, hair_style="bun", hat_style="scarf", skirt=0.12,
        collar="hat", right="cane", carry_r="cane", hunch=17.0,
        colors=c(top=0x6A4A6A, bottom=0x4A3A4A, hat=0x8A8A92, hair=WHITE, skin=PALE), clips=clips()),
    "folk_noble": person(
        "folk_noble", belly=0.3, hat_style="crown", beard="full", cape="long", collar="fur",
        extras=("medal", "scabbard"), boot=0.42,
        colors=c(top=0x2E4A9A, bottom=0x2A2630, cape=0xA82E2E, fur=0xEEE8DC, hair=CHESTNUT, shoes=0x2A2630),
        clips=clips("wave")),
    "folk_noble_lady": person(
        "folk_noble_lady", female=True, height=1.74, hair_style="long", hat_style="circlet", skirt=0.06,
        skirt_mat="top", cape="long", collar="fur", right="flower", carry_r="low",
        colors=c(top=0x8A2E6A, bottom=0x8A2E6A, cape=0x4A2A6A, fur=0xEEE8DC, hair=BLACK), clips=clips("wave")),
    "folk_beggar": person(
        "folk_beggar", build=0.9, hat_style="hood", beard="full", sleeves="short", legs="bare", boot=0.0,
        right="hand_out", carry_r="raised", left="cane", carry_l="cane", hunch=14.0,
        colors=c(top=0x7A6A52, bottom=0x5A4E3E, hat=0x5A4E3E, shoes=0xD0A078, skin=0xD0A078, hair=GRAY),
        clips=clips("wave")),
    "folk_beggar_woman": person(
        "folk_beggar_woman", female=True, build=0.9, height=1.65, hair_style="long", hat_style="scarf",
        sleeves="short", skirt=0.25, boot=0.0, right="hand_out", carry_r="raised", hunch=12.0,
        colors=c(top=0x6A6258, bottom=0x4E4A44, hat=0x6A5A4A, shoes=0xD0A078, skin=0xD0A078, hair=GRAY),
        clips=clips("wave")),
}
