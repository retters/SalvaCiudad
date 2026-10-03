#include "game/map_report.h"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <ctime>
#include <format>
#include <map>
#include <system_error>

#include <yyjson.h>

#include "core/json.h"
#include "core/log.h"
#include "game/settings.h"

namespace sc::report {

namespace {

namespace names = new_game_names;

template <std::size_t N>
std::string_view pick(const std::string_view (&list)[N], std::size_t i) {
    return i < N ? list[i] : list[0];
}

template <std::size_t N>
std::optional<std::size_t> find_name(const std::string_view (&list)[N], std::string_view name) {
    for (std::size_t i = 0; i < N; ++i) {
        if (list[i] == name) {
            return i;
        }
    }
    return std::nullopt;
}

constexpr std::string_view kCameraModes[] = {"aerial", "thirdPerson", "firstPerson"};
constexpr std::string_view kSeasons[] = {"spring", "summer", "autumn", "winter"};
constexpr std::string_view kTerrains[] = {"grass", "meadow", "forestFloor", "sand", "rock", "clay", "water"};
constexpr std::string_view kWaters[] = {"none", "river", "lake", "sea", "estuary"};
// In the order of sim::LandformKind.
constexpr std::string_view kLandforms[] = {"gulf",  "peninsula", "islet",   "island", "river", "plain",
                                           "hills", "mountains", "plateau", "basin",  "sea",   "crest",
                                           "pass",  "cliff",     "ramp",    "valley", "canyon"};
static_assert(std::size(kLandforms) == static_cast<std::size_t>(sim::LandformKind::Count));
static_assert(std::size(kTerrains) == static_cast<std::size_t>(sim::Terrain::Count));

// Files a report folder may hold: only folders with nothing else are deleted.
bool is_report_file(std::string_view name) {
    if (name == kFileName || name == "captura.png" || name == "captura_limpia.png") {
        return true;
    }
    return name.starts_with("despues_") && (name.ends_with(".png") || name.ends_with(".txt"));
}

std::string hex64(std::uint64_t v) {
    return std::format("{:016x}", v);
}

// A key that is not a string literal must be copied into the document.
void add(yyjson_mut_doc* doc, yyjson_mut_val* obj, std::string_view key, yyjson_mut_val* val) {
    (void)yyjson_mut_obj_add(obj, yyjson_mut_strncpy(doc, key.data(), key.size()), val);
}

void add_str(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, std::string_view value) {
    (void)yyjson_mut_obj_add_strncpy(doc, obj, key, value.data(), value.size());
}

yyjson_mut_val* cell_array(yyjson_mut_doc* doc, const Cell& c) {
    yyjson_mut_val* a = yyjson_mut_arr(doc);
    (void)yyjson_mut_arr_add_int(doc, a, c[0]);
    (void)yyjson_mut_arr_add_int(doc, a, c[1]);
    return a;
}

double round2(double v) {
    return std::round(v * 100.0) / 100.0;
}

// A description as JSON, with names that do not depend on the language.
yyjson_mut_val* describe_json(yyjson_mut_doc* doc, const CellDescription& d, const sim::Content& content) {
    yyjson_mut_val* o = yyjson_mut_obj(doc);
    (void)yyjson_mut_obj_add_val(doc, o, "cell", cell_array(doc, {d.cx, d.cz}));
    if (!d.inside) {
        (void)yyjson_mut_obj_add_bool(doc, o, "inside", false);
        return o;
    }
    (void)yyjson_mut_obj_add_real(doc, o, "heightM", d.height_cm / 100.0);
    (void)yyjson_mut_obj_add_int(doc, o, "slopePct", d.slope_pct);
    add_str(doc, o, "ground", pick(kTerrains, static_cast<std::size_t>(d.terrain)));
    add_str(doc, o, "biome", d.biome < content.flora.biomes.size() ? std::string_view(content.flora.biomes[d.biome].id) : "?");
    (void)yyjson_mut_obj_add_int(doc, o, "fertilityPct", d.fertility_pct);
    add_str(doc, o, "water", pick(kWaters, static_cast<std::size_t>(d.water)));
    if (d.region) {
        add_str(doc, o, "region", landform_name(*d.region));
    }
    if (d.water != WaterKind::None) {
        (void)yyjson_mut_obj_add_real(doc, o, "waterDepthM", d.water_depth_cm / 100.0);
    }
    yyjson_mut_val* lf = yyjson_mut_obj_add_arr(doc, o, "landforms");
    if (d.coast) {
        (void)yyjson_mut_arr_add_str(doc, lf, "coast");
    }
    for (const sim::LandformKind k : d.landforms) {
        const std::string_view n = landform_name(k);
        (void)yyjson_mut_arr_add_strncpy(doc, lf, n.data(), n.size());
    }
    return o;
}

// Reading: a number in an array, finite.
bool array_numbers(yyjson_mut_val* arr, std::size_t count, double limit, double* out) {
    if (!yyjson_mut_is_arr(arr) || yyjson_mut_arr_size(arr) != count) {
        return false;
    }
    for (std::size_t i = 0; i < count; ++i) {
        yyjson_mut_val* v = yyjson_mut_arr_get(arr, i);
        if (!yyjson_mut_is_num(v)) {
            return false;
        }
        out[i] = yyjson_mut_get_num(v);
        if (!std::isfinite(out[i]) || std::abs(out[i]) > limit) {
            return false;
        }
    }
    return true;
}

template <std::size_t N>
bool get_name(yyjson_mut_val* obj, const char* key, const std::string_view (&list)[N], std::size_t& out) {
    std::string s;
    if (json::get_string(obj, key, 64, s) != json::Field::Ok) {
        return false;
    }
    const auto i = find_name(list, s);
    if (!i) {
        return false;
    }
    out = *i;
    return true;
}

bool parse_hex64(const std::string& s, std::uint64_t& out) {
    if (s.empty() || s.size() > 16) {
        return false;
    }
    const auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), out, 16);
    return ec == std::errc{} && p == s.data() + s.size();
}

}  // namespace

std::string_view camera_mode_name(CameraMode mode) {
    return pick(kCameraModes, static_cast<std::size_t>(mode));
}

std::string_view water_name(WaterKind kind) {
    return pick(kWaters, static_cast<std::size_t>(kind));
}

std::string_view landform_name(sim::LandformKind kind) {
    return pick(kLandforms, static_cast<std::size_t>(kind));
}

bool closes(const Stroke& stroke) {
    const auto& p = stroke.screen;
    if (p.size() < 8) {
        return false;
    }
    float x0 = p[0][0], x1 = p[0][0], y0 = p[0][1], y1 = p[0][1];
    for (const auto& q : p) {
        x0 = std::min(x0, q[0]);
        x1 = std::max(x1, q[0]);
        y0 = std::min(y0, q[1]);
        y1 = std::max(y1, q[1]);
    }
    const float size = std::hypot(x1 - x0, y1 - y0);
    const float gap = std::hypot(p.back()[0] - p.front()[0], p.back()[1] - p.front()[1]);
    return size >= 20.0f && gap <= std::max(24.0f, size * 0.2f);
}

std::vector<Cell> cells_under(const Stroke& stroke, const std::function<std::optional<math::Vec3>(float, float)>& hit,
                              float step) {
    std::vector<Cell> cells;
    const auto sample = [&](float x, float y) {
        if (const std::optional<math::Vec3> g = hit(x, y)) {
            cells.push_back({static_cast<std::int32_t>(std::floor(g->x)), static_cast<std::int32_t>(std::floor(g->z))});
        }
    };
    const auto& p = stroke.screen;
    if (p.size() == 1) {
        sample(p[0][0], p[0][1]);
    }
    for (std::size_t k = 0; k + 1 < p.size() && cells.size() < kMaxCells; ++k) {
        const float dx = p[k + 1][0] - p[k][0];
        const float dy = p[k + 1][1] - p[k][1];
        const int n = std::max(1, static_cast<int>(std::ceil(std::hypot(dx, dy) / std::max(0.5f, step))));
        for (int i = (k == 0 ? 0 : 1); i <= n; ++i) {
            const float t = static_cast<float>(i) / static_cast<float>(n);
            sample(p[k][0] + dx * t, p[k][1] + dy * t);
        }
    }
    if (closes(stroke)) {
        // Inside: a grid of points over its box, those within the outline
        // (even-odd rule, with the gap between the ends closed).
        float x0 = p[0][0], x1 = p[0][0], y0 = p[0][1], y1 = p[0][1];
        for (const auto& q : p) {
            x0 = std::min(x0, q[0]);
            x1 = std::max(x1, q[0]);
            y0 = std::min(y0, q[1]);
            y1 = std::max(y1, q[1]);
        }
        const float grid = std::max({std::max(0.5f, step), std::sqrt((x1 - x0) * (y1 - y0) / static_cast<float>(kMaxAreaSamples))});
        const auto inside = [&](float x, float y) {
            bool in = false;
            for (std::size_t i = 0, j = p.size() - 1; i < p.size(); j = i++) {
                if ((p[i][1] > y) != (p[j][1] > y) &&
                    x < (p[j][0] - p[i][0]) * (y - p[i][1]) / (p[j][1] - p[i][1]) + p[i][0]) {
                    in = !in;
                }
            }
            return in;
        };
        for (float y = y0 + grid * 0.5f; y < y1 && cells.size() < kMaxCells; y += grid) {
            for (float x = x0 + grid * 0.5f; x < x1; x += grid) {
                if (inside(x, y)) {
                    sample(x, y);
                }
            }
        }
    }
    std::sort(cells.begin(), cells.end());
    cells.erase(std::unique(cells.begin(), cells.end()), cells.end());
    if (cells.size() > kMaxCells) {
        cells.resize(kMaxCells);
    }
    return cells;
}

std::string to_json(const Report& r, const sim::MapData& map, const sim::Content& content, TerrainNames& names) {
    json::MutDoc doc = json::new_object_doc();
    if (!doc) {
        return {};
    }
    yyjson_mut_doc* d = doc.get();
    yyjson_mut_val* root = yyjson_mut_doc_get_root(d);
    (void)yyjson_mut_obj_add_int(d, root, "schemaVersion", kSchemaVersion);
    add_str(d, root, "createdAt", r.created_at);

    yyjson_mut_val* game = yyjson_mut_obj_add_obj(d, root, "game");
    add_str(d, game, "version", r.game_version);
    add_str(d, game, "build", r.build_id);
    (void)yyjson_mut_obj_add_int(d, game, "generatorVersion", r.generator_version);
    add_str(d, game, "contentHash", hex64(r.content_hash));
    yyjson_mut_val* mods = yyjson_mut_obj_add_arr(d, game, "mods");
    for (const std::string& m : r.mods) {
        (void)yyjson_mut_arr_add_strncpy(d, mods, m.data(), m.size());
    }

    const sim::MapSettings& s = r.map;
    yyjson_mut_val* m = yyjson_mut_obj_add_obj(d, root, "map");
    add_str(d, m, "seed", std::to_string(s.seed));
    add_str(d, m, "size", pick(names::kSizes, static_cast<std::size_t>(s.size)));
    const auto& types = content.flora.map_types;
    add_str(d, m, "mapType", s.map_type < types.size() ? std::string_view(types[s.map_type].id) : "");
    const auto& biomes = content.flora.biomes;
    add_str(d, m, "biome", s.biome < biomes.size() ? std::string_view(biomes[s.biome].id) : "");
    add_str(d, m, "water", pick(names::kAmounts, static_cast<std::size_t>(s.water)));
    add_str(d, m, "forests", pick(names::kAmounts, static_cast<std::size_t>(s.forests)));
    add_str(d, m, "resources", pick(names::kAmounts, static_cast<std::size_t>(s.resources)));
    add_str(d, m, "relief", pick(names::kReliefs, static_cast<std::size_t>(s.relief)));
    add_str(d, m, "sea", pick(names::kSeas, static_cast<std::size_t>(s.sea)));
    add_str(d, m, "landforms", pick(names::kAmounts, static_cast<std::size_t>(s.landforms)));
    (void)yyjson_mut_obj_add_int(d, m, "players", s.players);
    (void)yyjson_mut_obj_add_bool(d, m, "separate", s.separate);
    (void)yyjson_mut_obj_add_int(d, m, "islands", s.islands);
    (void)yyjson_mut_obj_add_int(d, m, "cells", map.size);
    add_str(d, m, "checksum", hex64(r.map_checksum));

    const View& v = r.view;
    yyjson_mut_val* view = yyjson_mut_obj_add_obj(d, root, "view");
    add_str(d, view, "camera", camera_mode_name(v.mode));
    yyjson_mut_val* target = yyjson_mut_obj_add_arr(d, view, "target");
    for (const float c : {v.target.x, v.target.y, v.target.z}) {
        (void)yyjson_mut_arr_add_real(d, target, static_cast<double>(c));
    }
    (void)yyjson_mut_obj_add_real(d, view, "yaw", static_cast<double>(v.yaw));
    (void)yyjson_mut_obj_add_real(d, view, "pitch", static_cast<double>(v.pitch));
    (void)yyjson_mut_obj_add_real(d, view, "distance", static_cast<double>(v.distance));
    (void)yyjson_mut_obj_add_int(d, view, "width", v.width);
    (void)yyjson_mut_obj_add_int(d, view, "height", v.height);
    add_str(d, view, "season", pick(kSeasons, static_cast<std::size_t>(v.season)));
    (void)yyjson_mut_obj_add_real(d, view, "snow", round2(static_cast<double>(v.snow)));
    add_str(d, view, "context", r.in_game ? "game" : "map");
    add_str(d, view, "fog", pick(names::kFogs, static_cast<std::size_t>(r.fog)));

    if (r.cursor) {
        (void)yyjson_mut_obj_add_val(d, root, "cursor", describe_json(d, names.describe(map, (*r.cursor)[0], (*r.cursor)[1]), content));
    }

    // Each stroke, then what they cover together.
    std::vector<Cell> all;
    yyjson_mut_val* strokes = yyjson_mut_obj_add_arr(d, root, "strokes");
    for (const Stroke& st : r.strokes) {
        yyjson_mut_val* o = yyjson_mut_arr_add_obj(d, strokes);
        (void)yyjson_mut_obj_add_bool(d, o, "closed", st.closed);
        yyjson_mut_val* screen = yyjson_mut_obj_add_arr(d, o, "screen");
        for (const auto& p : st.screen) {
            yyjson_mut_val* pt = yyjson_mut_arr_add_arr(d, screen);
            (void)yyjson_mut_arr_add_int(d, pt, std::lround(p[0]));
            (void)yyjson_mut_arr_add_int(d, pt, std::lround(p[1]));
        }
        yyjson_mut_val* cells = yyjson_mut_obj_add_arr(d, o, "cells");
        for (const Cell& c : st.cells) {
            (void)yyjson_mut_arr_append(cells, cell_array(d, c));
        }
        all.insert(all.end(), st.cells.begin(), st.cells.end());
    }
    std::sort(all.begin(), all.end());
    all.erase(std::unique(all.begin(), all.end()), all.end());

    yyjson_mut_val* marked = yyjson_mut_obj_add_obj(d, root, "marked");
    (void)yyjson_mut_obj_add_int(d, marked, "cells", static_cast<std::int64_t>(all.size()));
    if (!all.empty()) {
        Cell lo = all[0];
        Cell hi = all[0];
        std::int32_t h_min = INT32_MAX;
        std::int32_t h_max = INT32_MIN;
        std::int32_t slope = 0;
        std::map<std::string, std::int64_t> water, ground, biome, landform, region;
        // Described every so many cells, so a long stroke stays quick.
        const std::size_t every = std::max<std::size_t>(1, all.size() / 20000);
        std::int64_t described = 0;
        for (std::size_t i = 0; i < all.size(); ++i) {
            const Cell& c = all[i];
            lo = {std::min(lo[0], c[0]), std::min(lo[1], c[1])};
            hi = {std::max(hi[0], c[0]), std::max(hi[1], c[1])};
            if (i % every != 0) {
                continue;
            }
            const CellDescription cd = names.describe(map, c[0], c[1]);
            if (!cd.inside) {
                continue;
            }
            ++described;
            h_min = std::min(h_min, cd.height_cm);
            h_max = std::max(h_max, cd.height_cm);
            slope = std::max(slope, cd.slope_pct);
            ++water[std::string(water_name(cd.water))];
            ++ground[std::string(pick(kTerrains, static_cast<std::size_t>(cd.terrain)))];
            ++biome[cd.biome < content.flora.biomes.size() ? content.flora.biomes[cd.biome].id : "?"];
            if (cd.coast) {
                ++landform["coast"];
            }
            for (const sim::LandformKind k : cd.landforms) {
                ++landform[std::string(landform_name(k))];
            }
            if (cd.region) {
                ++region[std::string(landform_name(*cd.region))];
            }
        }
        (void)yyjson_mut_obj_add_val(d, marked, "min", cell_array(d, lo));
        (void)yyjson_mut_obj_add_val(d, marked, "max", cell_array(d, hi));
        (void)yyjson_mut_obj_add_int(d, marked, "described", described);
        if (described > 0) {
            (void)yyjson_mut_obj_add_real(d, marked, "heightMinM", h_min / 100.0);
            (void)yyjson_mut_obj_add_real(d, marked, "heightMaxM", h_max / 100.0);
            (void)yyjson_mut_obj_add_int(d, marked, "slopeMaxPct", slope);
        }
        // Counts of described cells by kind.
        const auto counts = [&](const char* key, const std::map<std::string, std::int64_t>& list) {
            yyjson_mut_val* o = yyjson_mut_obj_add_obj(d, marked, key);
            for (const auto& [name, n] : list) {
                add(d, o, name, yyjson_mut_int(d, n));
            }
        };
        counts("water", water);
        counts("ground", ground);
        counts("biomes", biome);
        counts("landforms", landform);
        if (!region.empty()) {
            counts("regions", region);
        }
    }
    return json::write_pretty(d);
}

bool parse_replay(std::string_view text, const sim::Content* content, Replay& out, std::string& error) {
    if (text.size() > kMaxFileBytes) {
        error = "the file is too large";
        return false;
    }
    json::ParseResult parsed = json::parse_object(text);
    if (parsed.error != json::ParseError::None) {
        error = "not valid JSON: " + parsed.message;
        return false;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
    std::int64_t schema = 0;
    if (json::get_int(root, "schemaVersion", 1, 1000, schema) != json::Field::Ok || schema != kSchemaVersion) {
        error = "unknown schemaVersion";
        return false;
    }
    Replay r;
    yyjson_mut_val* game = nullptr;
    yyjson_mut_val* map = nullptr;
    yyjson_mut_val* view = nullptr;
    if (json::get_object(root, "game", game) != json::Field::Ok || json::get_object(root, "map", map) != json::Field::Ok ||
        json::get_object(root, "view", view) != json::Field::Ok) {
        error = "missing game, map or view";
        return false;
    }
    std::int64_t gen = 0;
    std::string hash;
    if (json::get_string(game, "version", 64, r.game_version) != json::Field::Ok ||
        json::get_string(game, "build", 64, r.build_id) != json::Field::Ok ||
        json::get_int(game, "generatorVersion", 0, 65535, gen) != json::Field::Ok ||
        json::get_string(game, "contentHash", 16, hash) != json::Field::Ok || !parse_hex64(hash, r.content_hash)) {
        error = "bad game fields";
        return false;
    }
    r.generator_version = static_cast<std::uint16_t>(gen);

    sim::MapSettings& s = r.map;
    std::string seed;
    std::string type_id;
    std::string biome_id;
    std::size_t size = 0, water = 0, forests = 0, resources = 0, relief = 0, sea = 0, landforms = 0;
    std::int64_t players = 0;
    std::int64_t islands = 0;
    bool separate = false;
    if (json::get_string(map, "seed", 20, seed) != json::Field::Ok || !get_name(map, "size", names::kSizes, size) ||
        json::get_string(map, "mapType", 128, type_id) != json::Field::Ok ||
        json::get_string(map, "biome", 128, biome_id) != json::Field::Ok || !get_name(map, "water", names::kAmounts, water) ||
        !get_name(map, "forests", names::kAmounts, forests) || !get_name(map, "resources", names::kAmounts, resources) ||
        !get_name(map, "relief", names::kReliefs, relief) || !get_name(map, "sea", names::kSeas, sea) ||
        !get_name(map, "landforms", names::kAmounts, landforms) ||
        json::get_int(map, "players", 1, 12, players) != json::Field::Ok ||
        json::get_bool(map, "separate", separate) != json::Field::Ok ||
        json::get_int(map, "islands", 1, sim::kMaxIslandsPerTown, islands) != json::Field::Ok) {
        error = "bad map fields";
        return false;
    }
    // The "generator" of reports made before phase 49 is ignored: there is
    // only one now, and their generatorVersion tells them apart (D-4904).
    const auto [p, ec] = std::from_chars(seed.data(), seed.data() + seed.size(), s.seed);
    if (seed.empty() || ec != std::errc{} || p != seed.data() + seed.size()) {
        error = "bad seed";
        return false;
    }
    if (content != nullptr) {
        const auto& types = content->flora.map_types;
        const auto type = std::find_if(types.begin(), types.end(), [&](const sim::MapTypeDef& t) { return t.id == type_id; });
        const auto& biomes = content->flora.biomes;
        const auto biome = std::find_if(biomes.begin(), biomes.end(), [&](const sim::BiomeDef& b) { return b.id == biome_id; });
        if (type == types.end() || biome == biomes.end() || types.size() > 255 || biomes.size() > 255) {
            error = "the map type or biome is not in the loaded mods";
            return false;
        }
        s.map_type = static_cast<std::uint8_t>(type - types.begin());
        s.biome = static_cast<std::uint8_t>(biome - biomes.begin());
    }
    s.size = static_cast<sim::MapSize>(size);
    s.water = static_cast<sim::Amount>(water);
    s.forests = static_cast<sim::Amount>(forests);
    s.resources = static_cast<sim::Amount>(resources);
    s.relief = static_cast<sim::Relief>(relief);
    s.sea = static_cast<sim::Sea>(sea);
    s.landforms = static_cast<sim::Amount>(landforms);
    s.players = static_cast<std::uint8_t>(players);
    s.separate = separate && players > 1;
    s.islands = static_cast<std::uint8_t>(islands);

    View& v = r.view;
    std::size_t mode = 0;
    std::size_t season = 0;
    double target[3] = {};
    double yaw = 0.0, pitch = 0.0, distance = 0.0, snow = 0.0;
    std::int64_t width = 0, height = 0;
    if (!get_name(view, "camera", kCameraModes, mode) ||
        !array_numbers(yyjson_mut_obj_get(view, "target"), 3, 100000.0, target) ||
        json::get_double(view, "yaw", -1000.0, 1000.0, yaw) != json::Field::Ok ||
        json::get_double(view, "pitch", -10.0, 10.0, pitch) != json::Field::Ok ||
        json::get_double(view, "distance", 0.0, 100000.0, distance) != json::Field::Ok ||
        json::get_int(view, "width", 320, 16384, width) != json::Field::Ok ||
        json::get_int(view, "height", 200, 16384, height) != json::Field::Ok ||
        !get_name(view, "season", kSeasons, season) || json::get_double(view, "snow", 0.0, 1.0, snow) != json::Field::Ok) {
        error = "bad view fields";
        return false;
    }
    v.mode = static_cast<CameraMode>(mode);
    v.target = {static_cast<float>(target[0]), static_cast<float>(target[1]), static_cast<float>(target[2])};
    v.yaw = static_cast<float>(yaw);
    v.pitch = static_cast<float>(pitch);
    v.distance = static_cast<float>(distance);
    v.width = static_cast<std::uint32_t>(width);
    v.height = static_cast<std::uint32_t>(height);
    v.season = static_cast<sim::Season>(season);
    v.snow = static_cast<float>(snow);
    out = std::move(r);
    return true;
}

void draw_strokes(std::vector<std::uint8_t>& rgb, std::uint32_t width, std::uint32_t height,
                  const std::vector<Stroke>& strokes, float thickness, std::array<std::uint8_t, 3> color) {
    if (rgb.size() != static_cast<std::size_t>(width) * height * 3u) {
        return;
    }
    const float r = std::max(0.5f, thickness * 0.5f);
    const auto dot = [&](std::int64_t x, std::int64_t y) {
        if (x >= 0 && y >= 0 && x < width && y < height) {
            const std::size_t i = (static_cast<std::size_t>(y) * width + static_cast<std::size_t>(x)) * 3u;
            rgb[i] = color[0];
            rgb[i + 1] = color[1];
            rgb[i + 2] = color[2];
        }
    };
    for (const Stroke& st : strokes) {
        const auto& p = st.screen;
        for (std::size_t k = 0; k < p.size(); ++k) {
            const float ax = p[k][0], ay = p[k][1];
            const float bx = p[std::min(k + 1, p.size() - 1)][0], by = p[std::min(k + 1, p.size() - 1)][1];
            const float dx = bx - ax, dy = by - ay;
            const float len2 = dx * dx + dy * dy;
            const auto x0 = static_cast<std::int64_t>(std::floor(std::min(ax, bx) - r));
            const auto x1 = static_cast<std::int64_t>(std::ceil(std::max(ax, bx) + r));
            const auto y0 = static_cast<std::int64_t>(std::floor(std::min(ay, by) - r));
            const auto y1 = static_cast<std::int64_t>(std::ceil(std::max(ay, by) + r));
            for (std::int64_t y = std::max<std::int64_t>(0, y0); y <= std::min<std::int64_t>(height - 1, y1); ++y) {
                for (std::int64_t x = std::max<std::int64_t>(0, x0); x <= std::min<std::int64_t>(width - 1, x1); ++x) {
                    const float px = static_cast<float>(x) + 0.5f - ax;
                    const float py = static_cast<float>(y) + 0.5f - ay;
                    const float t = len2 > 0.0f ? std::clamp((px * dx + py * dy) / len2, 0.0f, 1.0f) : 0.0f;
                    if (std::hypot(px - dx * t, py - dy * t) <= r) {
                        dot(x, y);
                    }
                }
            }
        }
    }
}

std::filesystem::path base_dir() {
    std::error_code ec;
    std::filesystem::path temp = std::filesystem::temp_directory_path(ec);
    if (ec) {
        return {};
    }
    return temp / "SalvaCiudad" / "reportes";
}

std::string folder_name_now() {
    const std::time_t t = std::time(nullptr);
    std::tm local{};
#if defined(_WIN32)
    if (localtime_s(&local, &t) != 0) {
        return "report";
    }
#else
    if (localtime_r(&t, &local) == nullptr) {
        return "report";
    }
#endif
    return std::format("{:04}-{:02}-{:02}_{:02}{:02}{:02}", local.tm_year + 1900, local.tm_mon + 1, local.tm_mday,
                       local.tm_hour, local.tm_min, local.tm_sec);
}

bool is_report_name(std::string_view name) {
    // "YYYY-MM-DD_HHMMSS", maybe with "-N".
    if (name.size() < 17) {
        return false;
    }
    for (std::size_t i = 0; i < 17; ++i) {
        const char c = name[i];
        const bool ok = (i == 4 || i == 7) ? c == '-' : (i == 10 ? c == '_' : c >= '0' && c <= '9');
        if (!ok) {
            return false;
        }
    }
    if (name.size() == 17) {
        return true;
    }
    if (name[17] != '-' || name.size() == 18 || name.size() > 21) {
        return false;
    }
    return std::all_of(name.begin() + 18, name.end(), [](char c) { return c >= '0' && c <= '9'; });
}

std::filesystem::path create_folder(const std::filesystem::path& base, const std::string& name) {
    std::error_code ec;
    std::filesystem::create_directories(base, ec);
    if (ec) {
        return {};
    }
    for (int n = 1; n < 100; ++n) {
        const std::filesystem::path dir = base / (n == 1 ? name : name + "-" + std::to_string(n));
        if (std::filesystem::create_directory(dir, ec) && !ec) {
            return dir;
        }
        if (ec) {
            return {};
        }
    }
    return {};
}

void prune(const std::filesystem::path& base, std::size_t keep) {
    std::error_code ec;
    std::vector<std::filesystem::path> dirs;
    for (const auto& entry : std::filesystem::directory_iterator(base, ec)) {
        if (entry.is_directory(ec) && !entry.is_symlink(ec) && is_report_name(entry.path().filename().string())) {
            dirs.push_back(entry.path());
        }
    }
    if (ec || dirs.size() <= keep) {
        return;
    }
    // The names sort by time.
    std::sort(dirs.begin(), dirs.end());
    for (std::size_t i = 0; i + keep < dirs.size(); ++i) {
        bool ours = true;
        std::vector<std::filesystem::path> files;
        for (const auto& f : std::filesystem::directory_iterator(dirs[i], ec)) {
            if (!f.is_regular_file(ec) || f.is_symlink(ec) || !is_report_file(f.path().filename().string())) {
                ours = false;
                break;
            }
            files.push_back(f.path());
        }
        if (ec || !ours) {
            log::info("report: kept {} (it holds other files)", dirs[i].filename().string());
            ec.clear();
            continue;
        }
        for (const auto& f : files) {
            std::filesystem::remove(f, ec);
        }
        std::filesystem::remove(dirs[i], ec);
        ec.clear();
    }
}

}  // namespace sc::report
