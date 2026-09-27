#include "sim/map.h"

#include <algorithm>
#include <span>

namespace sc::sim {

void MapSettings::write(BinaryWriter& w) const {
    w.u64(seed);
    w.u8(static_cast<std::uint8_t>(size));
    w.u8(static_cast<std::uint8_t>(water));
    w.u8(static_cast<std::uint8_t>(forests));
    w.u8(static_cast<std::uint8_t>(resources));
    w.u8(static_cast<std::uint8_t>(relief));
    w.u8(players);
    w.u8(map_type);
    w.u8(biome);
    w.u8(separate ? 1 : 0);
}

std::int32_t world_grid(const MapSettings& s) {
    if (!s.separate || s.players <= 1) {
        return 1;
    }
    return s.players <= 4 ? 2 : s.players <= 9 ? 3 : 4;
}

MapSize region_map_size(const MapSettings& s) {
    const std::int32_t k = world_grid(s);
    MapSize size = s.size;
    while (k * map_cells(size) > map_cells(kMaxWorldSize) && size != MapSize::Small) {
        size = static_cast<MapSize>(static_cast<std::uint8_t>(size) - 1);
    }
    return size;
}

std::int32_t world_cells(const MapSettings& s) {
    return world_grid(s) * map_cells(region_map_size(s));
}

std::int32_t MapData::region_size() const {
    const std::int32_t k = world_grid(settings);
    return k > 1 ? size / k : 0;
}

std::int32_t MapData::region_at(std::int32_t cx, std::int32_t cz) const {
    const std::int32_t k = world_grid(settings);
    if (k <= 1) {
        return 0;
    }
    const std::int32_t t = size / k;
    return std::clamp(cz / t, 0, k - 1) * k + std::clamp(cx / t, 0, k - 1);
}

bool MapSettings::read(BinaryReader& r, MapSettings& out) {
    MapSettings s;
    std::uint8_t size = 0, water = 0, forests = 0, resources = 0, relief = 0, map_type = 0, biome = 0, separate = 0;
    if (!r.u64(s.seed) || !r.u8(size) || !r.u8(water) || !r.u8(forests) || !r.u8(resources) || !r.u8(relief) ||
        !r.u8(s.players) || !r.u8(map_type) || !r.u8(biome) || !r.u8(separate)) {
        return false;
    }
    if (separate > 1) {
        r.fail();
        return false;
    }
    s.separate = separate != 0;
    if (size >= static_cast<std::uint8_t>(MapSize::Count) || water >= static_cast<std::uint8_t>(Amount::Count) ||
        forests >= static_cast<std::uint8_t>(Amount::Count) || resources >= static_cast<std::uint8_t>(Amount::Count) ||
        relief >= static_cast<std::uint8_t>(Relief::Count) || s.players < 1 || s.players > 12 ||
        map_type >= kMaxMapTypes || biome >= kMaxBiomes) {
        r.fail();
        return false;
    }
    s.size = static_cast<MapSize>(size);
    s.water = static_cast<Amount>(water);
    s.forests = static_cast<Amount>(forests);
    s.resources = static_cast<Amount>(resources);
    s.relief = static_cast<Relief>(relief);
    s.map_type = map_type;
    s.biome = biome;
    out = s;
    return true;
}

std::uint16_t MapData::height_cm(std::int32_t vx, std::int32_t vz) const {
    const std::int32_t v = vertices_per_side();
    vx = vx < 0 ? 0 : (vx >= v ? v - 1 : vx);
    vz = vz < 0 ? 0 : (vz >= v ? v - 1 : vz);
    return heights[static_cast<std::size_t>(vz) * static_cast<std::size_t>(v) + static_cast<std::size_t>(vx)];
}

Fixed MapData::height_at(Fixed x, Fixed z) const {
    const std::int32_t vx = x.floor_int();
    const std::int32_t vz = z.floor_int();
    const std::int64_t fx = x.raw() & 0xFFFF;
    const std::int64_t fz = z.raw() & 0xFFFF;
    const std::int64_t h00 = height_cm(vx, vz);
    const std::int64_t h10 = height_cm(vx + 1, vz);
    const std::int64_t h01 = height_cm(vx, vz + 1);
    const std::int64_t h11 = height_cm(vx + 1, vz + 1);
    // Heights in cm with 16 fractional bits, then to meters.
    const std::int64_t a = (h00 << 16) + (h10 - h00) * fx;
    const std::int64_t b = (h01 << 16) + (h11 - h01) * fx;
    const std::int64_t cm = a + (((b - a) * fz) >> 16);
    return Fixed::from_raw(static_cast<std::int32_t>(cm / 100));
}

Terrain MapData::terrain_at(std::int32_t cx, std::int32_t cz) const {
    if (cx < 0 || cz < 0 || cx >= size || cz >= size) {
        return Terrain::Grass;
    }
    return static_cast<Terrain>(terrain[static_cast<std::size_t>(cz) * static_cast<std::size_t>(size) + static_cast<std::size_t>(cx)]);
}

bool MapData::water_at(std::int32_t cx, std::int32_t cz) const {
    if (cx < 0 || cz < 0 || cx >= size || cz >= size) {
        return false;
    }
    return water[static_cast<std::size_t>(cz) * static_cast<std::size_t>(size) + static_cast<std::size_t>(cx)] != 0;
}

std::uint8_t MapData::biome_at(std::int32_t cx, std::int32_t cz) const {
    if (cx < 0 || cz < 0 || cx >= size || cz >= size || biome.empty()) {
        return 0;
    }
    return biome[static_cast<std::size_t>(cz) * static_cast<std::size_t>(size) + static_cast<std::size_t>(cx)];
}

std::int32_t MapData::tree_height_cm(const MapFeature& f) {
    if (f.type != FeatureType::Tree) {
        return 0;
    }
    const std::int64_t model = size_info(static_cast<TreeSize>(f.size)).model_cm;
    return static_cast<std::int32_t>((model * f.scale.raw()) >> 16);
}

std::uint64_t MapData::checksum() const {
    BinaryWriter w;
    settings.write(w);
    w.u16(generator_version);
    w.i32(size);
    std::uint64_t h = fnv1a64(w.bytes());
    const auto bytes = [](const auto& v) {
        return std::span<const std::uint8_t>(reinterpret_cast<const std::uint8_t*>(v.data()), v.size() * sizeof(v[0]));
    };
    // The vectors hold plain integers; hash their bytes in a fixed (little
    // endian) layout. Big-endian targets would need a conversion here.
    h = fnv1a64(bytes(heights), h);
    h = fnv1a64(bytes(water), h);
    h = fnv1a64(terrain, h);
    h = fnv1a64(fertility, h);
    h = fnv1a64(biome, h);
    BinaryWriter tail;
    for (const MapFeature& f : features) {
        tail.u8(static_cast<std::uint8_t>(f.type));
        tail.u8(f.species);
        tail.u8(f.size);
        tail.u16(f.rotation);
        tail.fixed(f.x);
        tail.fixed(f.z);
        tail.fixed(f.scale);
    }
    for (const Zone& z : zones) {
        tail.u8(static_cast<std::uint8_t>(z.type));
        tail.fixed(z.x);
        tail.fixed(z.z);
        tail.fixed(z.radius);
    }
    for (const StartPosition& s : starts) {
        tail.fixed(s.x);
        tail.fixed(s.z);
    }
    return fnv1a64(tail.bytes(), h);
}

}  // namespace sc::sim
