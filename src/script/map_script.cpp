#include "script/map_script.h"

#include <cstring>

extern "C" {
#include <lauxlib.h>
#include <lua.h>
}

#include "core/log.h"
#include "script/lua_sandbox.h"
#include "sim/rng.h"
#include "sim/worldgen.h"

namespace sc::script {

namespace {

// Most features one mod may add to a map.
constexpr int kMaxAdded = 20000;

struct MapContext {
    sim::MapData* map = nullptr;
    const sim::Content* content = nullptr;
    sim::Rng rng;
    int added = 0;
};

constexpr const char* kTerrainNames[] = {"grass", "meadow", "forest", "sand", "rock", "clay", "water"};
constexpr const char* kFeatureNames[] = {"tree", "stone", "ironOre", "berryBush", "herbs"};

MapContext* ctx(lua_State* L) {
    return static_cast<MapContext*>(lua_touserdata(L, lua_upvalueindex(1)));
}

// Coordinates are whole centimeters.
std::int32_t cell_of(lua_Integer cm) {
    return static_cast<std::int32_t>(cm >= 0 ? cm / 100 : (cm - 99) / 100);
}

sim::Fixed fixed_cm(lua_Integer cm) {
    return sim::Fixed::from_ratio(static_cast<std::int64_t>(cm), 100);
}

int f_height(lua_State* L) {
    const lua_Integer x = luaL_checkinteger(L, 1);
    const lua_Integer z = luaL_checkinteger(L, 2);
    const MapContext* c = ctx(L);
    const sim::Fixed h = c->map->height_at(fixed_cm(x), fixed_cm(z));
    lua_pushinteger(L, static_cast<lua_Integer>((static_cast<std::int64_t>(h.raw()) * 100) >> 16));
    return 1;
}

int f_terrain(lua_State* L) {
    const lua_Integer x = luaL_checkinteger(L, 1);
    const lua_Integer z = luaL_checkinteger(L, 2);
    const auto t = static_cast<std::size_t>(ctx(L)->map->terrain_at(cell_of(x), cell_of(z)));
    lua_pushstring(L, t < std::size(kTerrainNames) ? kTerrainNames[t] : "grass");
    return 1;
}

int f_is_water(lua_State* L) {
    const lua_Integer x = luaL_checkinteger(L, 1);
    const lua_Integer z = luaL_checkinteger(L, 2);
    lua_pushboolean(L, ctx(L)->map->water_at(cell_of(x), cell_of(z)) ? 1 : 0);
    return 1;
}

int f_biome(lua_State* L) {
    const lua_Integer x = luaL_checkinteger(L, 1);
    const lua_Integer z = luaL_checkinteger(L, 2);
    const MapContext* c = ctx(L);
    const std::uint8_t b = c->map->biome_at(cell_of(x), cell_of(z));
    const auto& biomes = c->content->flora.biomes;
    lua_pushstring(L, b < biomes.size() ? biomes[b].id.c_str() : "");
    return 1;
}

// random(n): a whole number from 1 to n.
int f_random(lua_State* L) {
    const lua_Integer n = luaL_checkinteger(L, 1);
    luaL_argcheck(L, n >= 1 && n <= 0x7FFFFFFF, 1, "must be from 1 to 2147483647");
    lua_pushinteger(L, 1 + static_cast<lua_Integer>(ctx(L)->rng.below(static_cast<std::uint32_t>(n))));
    return 1;
}

// Checks a place for a new feature: on the map, on land and away from the
// start positions. Returns false (and the reason on the stack) otherwise.
bool place_ok(const MapContext* c, lua_Integer x, lua_Integer z) {
    const std::int32_t cx = cell_of(x);
    const std::int32_t cz = cell_of(z);
    if (cx < 1 || cz < 1 || cx >= c->map->size - 1 || cz >= c->map->size - 1 || c->map->water_at(cx, cz)) {
        return false;
    }
    const std::int64_t clear = static_cast<std::int64_t>(sim::worldgen::kStartClearRadius) * 100;
    for (const sim::StartPosition& s : c->map->starts) {
        const std::int64_t dx = x - (static_cast<std::int64_t>(s.x.raw()) * 100 >> 16);
        const std::int64_t dz = z - (static_cast<std::int64_t>(s.z.raw()) * 100 >> 16);
        if (dx * dx + dz * dz <= clear * clear) {
            return false;
        }
    }
    return true;
}

// add_feature(kind, x, z [, scale_percent]) -> true if placed.
int f_add_feature(lua_State* L) {
    const char* kind = luaL_checkstring(L, 1);
    const lua_Integer x = luaL_checkinteger(L, 2);
    const lua_Integer z = luaL_checkinteger(L, 3);
    const lua_Integer scale = luaL_optinteger(L, 4, 100);
    luaL_argcheck(L, scale >= 20 && scale <= 500, 4, "scale must be from 20 to 500 (percent)");
    MapContext* c = ctx(L);
    int k = -1;
    for (int i = 1; i < static_cast<int>(std::size(kFeatureNames)); ++i) {  // Trees use add_tree.
        if (std::strcmp(kind, kFeatureNames[i]) == 0) {
            k = i;
        }
    }
    luaL_argcheck(L, k >= 0, 1, "unknown feature kind (use stone, ironOre, berryBush or herbs)");
    if (c->added >= kMaxAdded || !place_ok(c, x, z)) {
        lua_pushboolean(L, 0);
        return 1;
    }
    sim::MapFeature f;
    f.type = static_cast<sim::FeatureType>(k);
    f.x = fixed_cm(x);
    f.z = fixed_cm(z);
    f.scale = sim::Fixed::from_ratio(scale, 100);
    f.rotation = static_cast<std::uint16_t>(c->rng.next_u32());
    c->map->features.push_back(f);
    ++c->added;
    lua_pushboolean(L, 1);
    return 1;
}

// add_tree(species_id, size, x, z [, height_cm]) -> true if placed.
int f_add_tree(lua_State* L) {
    const char* species = luaL_checkstring(L, 1);
    const char* size = luaL_checkstring(L, 2);
    const lua_Integer x = luaL_checkinteger(L, 3);
    const lua_Integer z = luaL_checkinteger(L, 4);
    const lua_Integer height = luaL_optinteger(L, 5, 0);
    MapContext* c = ctx(L);
    const int s = c->content->flora.find_species(species);
    luaL_argcheck(L, s >= 0, 1, "unknown species");
    int z_index = -1;
    for (int i = 0; i < static_cast<int>(sim::kTreeSizes); ++i) {
        if (std::strcmp(size, sim::size_info(static_cast<sim::TreeSize>(i)).id) == 0) {
            z_index = i;
        }
    }
    luaL_argcheck(L, z_index >= 0, 2, "size must be small, medium, large or huge");
    const sim::TreeSize fitted = c->content->flora.fit_size(static_cast<std::size_t>(s), static_cast<sim::TreeSize>(z_index));
    const sim::SizeInfo& si = sim::size_info(fitted);
    if (c->added >= kMaxAdded || !place_ok(c, x, z)) {
        lua_pushboolean(L, 0);
        return 1;
    }
    const std::int64_t cm = height > 0 ? std::clamp<std::int64_t>(height, si.min_cm, si.max_cm)
                                       : (si.min_cm + si.max_cm) / 2;
    sim::MapFeature f;
    f.type = sim::FeatureType::Tree;
    f.species = static_cast<std::uint8_t>(s);
    f.size = static_cast<std::uint8_t>(fitted);
    f.x = fixed_cm(x);
    f.z = fixed_cm(z);
    f.scale = sim::Fixed::from_ratio(cm, si.model_cm);
    f.rotation = static_cast<std::uint16_t>(c->rng.next_u32());
    c->map->features.push_back(f);
    ++c->added;
    lua_pushboolean(L, 1);
    return 1;
}

int f_count(lua_State* L) {
    const char* kind = luaL_checkstring(L, 1);
    int k = -1;
    for (int i = 0; i < static_cast<int>(std::size(kFeatureNames)); ++i) {
        if (std::strcmp(kind, kFeatureNames[i]) == 0) {
            k = i;
        }
    }
    luaL_argcheck(L, k >= 0, 1, "unknown feature kind");
    lua_Integer n = 0;
    for (const sim::MapFeature& f : ctx(L)->map->features) {
        n += static_cast<int>(f.type) == k ? 1 : 0;
    }
    lua_pushinteger(L, n);
    return 1;
}

// Pushes the `map` table given to on_map_generated.
void push_map(lua_State* L, MapContext* c) {
    lua_newtable(L);
    lua_pushinteger(L, static_cast<lua_Integer>(c->map->size) * 100);
    lua_setfield(L, -2, "size");
    lua_newtable(L);
    for (std::size_t i = 0; i < c->map->starts.size(); ++i) {
        lua_newtable(L);
        lua_pushinteger(L, static_cast<lua_Integer>(static_cast<std::int64_t>(c->map->starts[i].x.raw()) * 100 >> 16));
        lua_setfield(L, -2, "x");
        lua_pushinteger(L, static_cast<lua_Integer>(static_cast<std::int64_t>(c->map->starts[i].z.raw()) * 100 >> 16));
        lua_setfield(L, -2, "z");
        lua_rawseti(L, -2, static_cast<lua_Integer>(i + 1));
    }
    lua_setfield(L, -2, "starts");
    const luaL_Reg functions[] = {{"height", f_height},       {"terrain", f_terrain},   {"is_water", f_is_water},
                                  {"biome", f_biome},         {"random", f_random},     {"add_feature", f_add_feature},
                                  {"add_tree", f_add_tree},   {"count", f_count},       {nullptr, nullptr}};
    for (const luaL_Reg* r = functions; r->name != nullptr; ++r) {
        lua_pushlightuserdata(L, c);
        lua_pushcclosure(L, r->func, 1);
        lua_setfield(L, -2, r->name);
    }
}

std::uint64_t mod_salt(const std::string& id) {
    std::uint64_t h = 0xcbf29ce484222325ull;
    for (const char ch : id) {
        h = (h ^ static_cast<std::uint8_t>(ch)) * 0x100000001b3ull;
    }
    return h;
}

}  // namespace

MapScripts::MapScripts(const std::vector<mods::ModScript>& scripts, const sim::Content& content)
    : scripts_(scripts), content_(content) {}

bool MapScripts::map_generated(sim::MapData& map) {
    for (const mods::ModScript& script : scripts_) {
        LuaSandbox sandbox;
        std::string error;
        if (!sandbox.open(script.mod, script.dir, script.source, error)) {
            errors_.push_back(script.mod + ": " + error);
            log::warn("mod {}: script failed to load: {}", script.mod, error);
            continue;
        }
        if (!sandbox.has_function("on_map_generated")) {
            continue;
        }
        MapContext c;
        c.map = &map;
        c.content = &content_;
        c.rng = sim::Rng(map.settings.seed ^ mod_salt(script.mod), 11);
        push_map(sandbox.state(), &c);
        if (!sandbox.call("on_map_generated", 1, 0, error)) {
            errors_.push_back(script.mod + ": " + error);
            log::warn("mod {}: on_map_generated failed: {}", script.mod, error);
            continue;
        }
        log::info("mod {}: on_map_generated added {} feature(s)", script.mod, c.added);
    }
    return true;
}

}  // namespace sc::script
