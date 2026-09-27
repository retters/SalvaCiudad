#include "sim/map.h"

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
}

bool MapSettings::read(BinaryReader& r, MapSettings& out) {
    MapSettings s;
    std::uint8_t size = 0, water = 0, forests = 0, resources = 0, relief = 0;
    if (!r.u64(s.seed) || !r.u8(size) || !r.u8(water) || !r.u8(forests) || !r.u8(resources) || !r.u8(relief) ||
        !r.u8(s.players)) {
        return false;
    }
    if (size >= static_cast<std::uint8_t>(MapSize::Count) || water >= static_cast<std::uint8_t>(Amount::Count) ||
        forests >= static_cast<std::uint8_t>(Amount::Count) || resources >= static_cast<std::uint8_t>(Amount::Count) ||
        relief >= static_cast<std::uint8_t>(Relief::Count) || s.players < 1 || s.players > 12) {
        r.fail();
        return false;
    }
    s.size = static_cast<MapSize>(size);
    s.water = static_cast<Amount>(water);
    s.forests = static_cast<Amount>(forests);
    s.resources = static_cast<Amount>(resources);
    s.relief = static_cast<Relief>(relief);
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

std::uint64_t MapData::checksum() const {
    BinaryWriter w;
    settings.write(w);
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
    BinaryWriter tail;
    for (const MapFeature& f : features) {
        tail.u8(static_cast<std::uint8_t>(f.type));
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
