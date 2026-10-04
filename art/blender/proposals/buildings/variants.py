"""Material variants of buildings that had a single model: the same
generators with another palette (stone, sandstone, brick, slate, thatch)."""

import parts as P
import culture
import extra
import fantasy
import last
import more
import small

SANDSTONE = dict(wall=0xD4BC8C, wall_dark=0xB69C6E, wall_light=0xE6D4AA, trim=0xF0E4C4)
BRICK = dict(wall=0xA65A3E, wall_dark=0x844432, wall_light=0xBE7252, trim=0xCFC8B8)
BLUE_TILES = dict(tile_red=0x3F5F9E, tile_red_dark=0x324B80)
SLATE_TILES = dict(tile_red=0x5A6470, tile_red_dark=0x46505A)
THATCH_SHINGLES = dict(shingle=0xC9A55A, shingle_dark=0xA8863F)
TILE_THATCH = dict(thatch=0xB0503A, thatch_dark=0x8E3E2A)
GRANITE = dict(wall=0x5E5A62, wall_dark=0x46434A, wall_light=0x76727C, rock=0x56525A, rock_dark=0x403D44, banner=0x2F4FA6)


def make(name, fn, **roles):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig)
        P.finish(mb, name, P.palette(**roles), rig)
    return build


MODELS = {
    "bld_dovecote_brick": make("bld_dovecote_brick", extra.dovecote, **dict(BRICK, **SLATE_TILES)),
    "bld_dovecote_sandstone": make("bld_dovecote_sandstone", extra.dovecote, **SANDSTONE),
    "bld_observatory_sandstone": make("bld_observatory_sandstone", culture.observatory, **SANDSTONE),
    "bld_beacon_tower_sandstone": make("bld_beacon_tower_sandstone", small.beacon_tower, **SANDSTONE),
    "bld_beacon_tower_brick": make("bld_beacon_tower_brick", small.beacon_tower, **BRICK),
    "bld_wayside_shrine_blue": make("bld_wayside_shrine_blue", small.wayside_shrine, **BLUE_TILES),
    "bld_wayside_shrine_sandstone": make("bld_wayside_shrine_sandstone", small.wayside_shrine, **SANDSTONE),
    "bld_theater_tiles": make("bld_theater_tiles", culture.theater, **TILE_THATCH),
    "bld_hunting_lodge_thatch": make("bld_hunting_lodge_thatch", extra.hunting_lodge, **THATCH_SHINGLES),
    "bld_lumber_camp_thatch": make("bld_lumber_camp_thatch", more.lumber_camp, **THATCH_SHINGLES),
    "bld_well_house_blue": make("bld_well_house_blue", small.well_house, **BLUE_TILES),
    "bld_wash_house_slate": make("bld_wash_house_slate", small.wash_house, **SLATE_TILES),
    "bld_winery_slate": make("bld_winery_slate", more.winery, **SLATE_TILES),
    "bld_cemetery_sandstone": make("bld_cemetery_sandstone", last.cemetery, **SANDSTONE),
    "bld_dwarf_hall_granite": make("bld_dwarf_hall_granite", fantasy.dwarf_hall, **GRANITE),
}
