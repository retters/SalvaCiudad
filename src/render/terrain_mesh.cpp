#include "render/terrain_mesh.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace sc::render {

namespace {

constexpr int kTile = 64;          // Cells per chunk side.
constexpr int kGrid = kTile + 1;   // Grid points per chunk side.
constexpr int kTriangles = kTile * kTile * 2 - 2;
constexpr int kParents = kTriangles - kTile * kTile;

constexpr FacetSettings kLods[kFacetLods] = {
    {0.15f, 8, true},
    {0.9f, 16, true},
    {4.0f, 64, false},
};

// Skirt depth per level of detail, meters: hides cracks where neighbors
// were cut differently.
constexpr float kSkirt[kFacetLods] = {2.0f, 4.0f, 10.0f};

// The implicit binary tree of right triangles over the chunk grid: corners
// (ax, ay, bx, by, cx, cy) per triangle, where a-b is the hypotenuse.
struct TriangleCoords {
    std::array<std::int16_t, kTriangles * 6> c{};

    TriangleCoords() {
        for (int i = 0; i < kTriangles; ++i) {
            int id = i + 2;
            int ax = 0, ay = 0, bx = 0, by = 0, cx = 0, cy = 0;
            if ((id & 1) != 0) {
                bx = by = cx = kTile;  // Bottom-right triangle.
            } else {
                ax = ay = cy = kTile;  // Top-left triangle.
            }
            while ((id >>= 1) > 1) {
                const int mx = (ax + bx) >> 1;
                const int my = (ay + by) >> 1;
                if ((id & 1) != 0) {
                    bx = ax;
                    by = ay;
                    ax = cx;
                    ay = cy;
                } else {
                    ax = bx;
                    ay = by;
                    bx = cx;
                    by = cy;
                }
                cx = mx;
                cy = my;
            }
            const int k = i * 6;
            c[k] = static_cast<std::int16_t>(ax);
            c[k + 1] = static_cast<std::int16_t>(ay);
            c[k + 2] = static_cast<std::int16_t>(bx);
            c[k + 3] = static_cast<std::int16_t>(by);
            c[k + 4] = static_cast<std::int16_t>(cx);
            c[k + 5] = static_cast<std::int16_t>(cy);
        }
    }
};

const TriangleCoords& coords() {
    static const TriangleCoords table;
    return table;
}

std::uint32_t hash3(std::uint32_t x, std::uint32_t z, std::uint32_t seed) {
    std::uint32_t h = (x * 0x8DA6B343u) ^ (z * 0xD8163841u) ^ (seed * 0xCB1AB31Fu);
    h ^= h >> 13;
    h *= 0x5BD1E995u;
    h ^= h >> 15;
    return h;
}

struct Chunk {
    int ox = 0;
    int oz = 0;
    float h[kGrid * kGrid] = {};
    std::uint8_t cls[kGrid * kGrid] = {};
    float error[kGrid * kGrid] = {};
    std::uint8_t mixed[kGrid * kGrid] = {};  // A class change under this point.
};

class Builder {
public:
    Builder(std::int32_t cells, const std::vector<std::uint16_t>& heights, const std::vector<std::uint8_t>& classes,
            const std::vector<std::uint32_t>& colors, std::uint32_t seed)
        : cells_(cells), heights_(heights), classes_(classes), colors_(colors), seed_(seed) {}

    FacetMeshes build() {
        FacetMeshes out;
        out.cells = cells_;
        const int per_side = cells_ / kTile;
        out.chunks.resize(static_cast<std::size_t>(per_side) * static_cast<std::size_t>(per_side));
        Chunk chunk;
        for (int cz = 0; cz < per_side; ++cz) {
            for (int cx = 0; cx < per_side; ++cx) {
                load(chunk, cx * kTile, cz * kTile);
                compute_errors(chunk);
                auto& lods = out.chunks[static_cast<std::size_t>(cz * per_side + cx)];
                for (int lod = 0; lod < kFacetLods; ++lod) {
                    lods[static_cast<std::size_t>(lod)] = emit(chunk, lod, out);
                }
            }
        }
        return out;
    }

private:
    [[nodiscard]] float height_m(float x, float z) const {
        const float max = static_cast<float>(cells_);
        x = std::clamp(x, 0.0f, max);
        z = std::clamp(z, 0.0f, max);
        const int ix = std::min(static_cast<int>(x), cells_ - 1);
        const int iz = std::min(static_cast<int>(z), cells_ - 1);
        const float tx = x - static_cast<float>(ix);
        const float tz = z - static_cast<float>(iz);
        const auto v = static_cast<std::size_t>(cells_ + 1);
        const auto at = [&](int px, int pz) {
            return static_cast<float>(heights_[static_cast<std::size_t>(pz) * v + static_cast<std::size_t>(px)]) * 0.01f;
        };
        return (at(ix, iz) * (1 - tx) + at(ix + 1, iz) * tx) * (1 - tz) +
               (at(ix, iz + 1) * (1 - tx) + at(ix + 1, iz + 1) * tx) * tz;
    }

    void load(Chunk& c, int ox, int oz) const {
        c.ox = ox;
        c.oz = oz;
        const auto v = static_cast<std::size_t>(cells_ + 1);
        for (int z = 0; z < kGrid; ++z) {
            for (int x = 0; x < kGrid; ++x) {
                const std::size_t i = static_cast<std::size_t>(oz + z) * v + static_cast<std::size_t>(ox + x);
                c.h[z * kGrid + x] = static_cast<float>(heights_[i]) * 0.01f;
                const int cellx = std::min(ox + x, cells_ - 1);
                const int cellz = std::min(oz + z, cells_ - 1);
                c.cls[z * kGrid + x] =
                    classes_[static_cast<std::size_t>(cellz) * static_cast<std::size_t>(cells_) + static_cast<std::size_t>(cellx)];
            }
        }
    }

    static void compute_errors(Chunk& c) {
        std::fill(std::begin(c.error), std::end(c.error), 0.0f);
        std::fill(std::begin(c.mixed), std::end(c.mixed), std::uint8_t{0});
        const auto& t = coords().c;
        for (int i = kTriangles - 1; i >= 0; --i) {
            const int k = i * 6;
            const int ax = t[k], ay = t[k + 1], bx = t[k + 2], by = t[k + 3], cx = t[k + 4], cy = t[k + 5];
            const int mx = (ax + bx) >> 1;
            const int my = (ay + by) >> 1;
            const int m = my * kGrid + mx;
            const int a = ay * kGrid + ax;
            const int b = by * kGrid + bx;
            const int cc = cy * kGrid + cx;
            const float interpolated = (c.h[a] + c.h[b]) * 0.5f;
            float err = std::abs(interpolated - c.h[m]);
            std::uint8_t mixed = (c.cls[m] != c.cls[a] || c.cls[m] != c.cls[b] || c.cls[m] != c.cls[cc]) ? 1 : 0;
            if (i < kParents) {
                const int left = ((ay + cy) >> 1) * kGrid + ((ax + cx) >> 1);
                const int right = ((by + cy) >> 1) * kGrid + ((bx + cx) >> 1);
                err = std::max({err, c.error[left], c.error[right]});
                mixed = static_cast<std::uint8_t>(mixed | c.mixed[left] | c.mixed[right]);
            }
            c.error[m] = std::max(c.error[m], err);
            c.mixed[m] = static_cast<std::uint8_t>(c.mixed[m] | mixed);
        }
    }

    struct Emitted {
        std::vector<std::uint16_t> tris;  // Grid point indices, three per facet.
        std::vector<std::uint8_t> leg;    // Smallest facet leg touching each grid point.
    };

    void split(const Chunk& c, const FacetSettings& s, int ax, int ay, int bx, int by, int cx, int cy, Emitted& e) const {
        const int leg = std::abs(ax - cx) + std::abs(ay - cy);
        const int mx = (ax + bx) >> 1;
        const int my = (ay + by) >> 1;
        const int m = my * kGrid + mx;
        const bool refine = leg > 1 && (c.error[m] > s.max_error_m || (s.split_classes && c.mixed[m] != 0) ||
                                        leg > s.max_leg);
        if (refine) {
            split(c, s, cx, cy, ax, ay, mx, my, e);
            split(c, s, bx, by, cx, cy, mx, my, e);
            return;
        }
        const int corners[3] = {ay * kGrid + ax, by * kGrid + bx, cy * kGrid + cx};
        for (const int p : corners) {
            e.tris.push_back(static_cast<std::uint16_t>(p));
            e.leg[static_cast<std::size_t>(p)] = static_cast<std::uint8_t>(std::min<int>(e.leg[static_cast<std::size_t>(p)], leg));
        }
    }

    ChunkLod emit(const Chunk& c, int lod, FacetMeshes& out) const {
        const FacetSettings& s = kLods[lod];
        Emitted e;
        e.leg.assign(kGrid * kGrid, 255);
        split(c, s, 0, 0, kTile, kTile, kTile, 0, e);
        split(c, s, kTile, kTile, 0, 0, 0, kTile, e);

        ChunkLod result;
        result.first_vertex = static_cast<std::uint32_t>(out.positions.size() / 3);
        result.first_index = static_cast<std::uint32_t>(out.indices.size());
        result.first_face = static_cast<std::uint32_t>(out.face_colors.size());
        std::vector<std::int32_t> remap(kGrid * kGrid, -1);
        std::uint16_t next = 0;
        const auto vertex = [&](int p) {
            if (remap[static_cast<std::size_t>(p)] < 0) {
                remap[static_cast<std::size_t>(p)] = next++;
                const int x = p % kGrid;
                const int z = p / kGrid;
                float wx = static_cast<float>(c.ox + x);
                float wz = static_cast<float>(c.oz + z);
                // Nudge inner points so facets are irregular; never so far
                // that a neighboring facet folds over. Border points stay
                // put so chunks meet.
                const float limit = 0.3f * static_cast<float>(e.leg[static_cast<std::size_t>(p)]) * 0.5f;
                const std::uint32_t h = hash3(static_cast<std::uint32_t>(c.ox + x), static_cast<std::uint32_t>(c.oz + z), seed_);
                if (x != 0 && x != kTile) {
                    wx += (static_cast<float>(h & 0xFFFu) / 4095.0f * 2.0f - 1.0f) * limit;
                }
                if (z != 0 && z != kTile) {
                    wz += (static_cast<float>((h >> 12) & 0xFFFu) / 4095.0f * 2.0f - 1.0f) * limit;
                }
                out.positions.insert(out.positions.end(), {wx, height_m(wx, wz), wz});
            }
            return static_cast<std::uint16_t>(remap[static_cast<std::size_t>(p)]);
        };
        for (std::size_t t = 0; t + 2 < e.tris.size(); t += 3) {
            float gx = 0.0f;
            float gz = 0.0f;
            for (int k = 0; k < 3; ++k) {
                const int p = e.tris[t + static_cast<std::size_t>(k)];
                out.indices.push_back(vertex(p));
                gx += static_cast<float>(p % kGrid);
                gz += static_cast<float>(p / kGrid);
            }
            out.face_colors.push_back(facet_color(c, gx / 3.0f, gz / 3.0f, 1.0f));
        }
        // Skirts: a strip hanging from every facet edge on the chunk border.
        std::vector<std::int32_t> low(kGrid * kGrid, -1);
        const auto lowered = [&](int p) {
            if (low[static_cast<std::size_t>(p)] < 0) {
                const std::uint16_t top = vertex(p);
                const std::size_t k = (static_cast<std::size_t>(result.first_vertex) + top) * 3;
                const float x = out.positions[k];
                const float y = out.positions[k + 1];
                const float z = out.positions[k + 2];
                low[static_cast<std::size_t>(p)] = next++;
                out.positions.insert(out.positions.end(), {x, y - kSkirt[lod], z});
            }
            return static_cast<std::uint16_t>(low[static_cast<std::size_t>(p)]);
        };
        const auto on_border = [](int p, int q) {
            const int px = p % kGrid, pz = p / kGrid, qx = q % kGrid, qz = q / kGrid;
            return (px == 0 && qx == 0) || (px == kTile && qx == kTile) || (pz == 0 && qz == 0) ||
                   (pz == kTile && qz == kTile);
        };
        for (std::size_t t = 0; t + 2 < e.tris.size(); t += 3) {
            for (int k = 0; k < 3; ++k) {
                const int p = e.tris[t + static_cast<std::size_t>(k)];
                const int q = e.tris[t + static_cast<std::size_t>((k + 1) % 3)];
                if (!on_border(p, q)) {
                    continue;
                }
                const std::uint16_t a = vertex(p);
                const std::uint16_t b = vertex(q);
                const std::uint16_t la = lowered(p);
                const std::uint16_t lb = lowered(q);
                out.indices.insert(out.indices.end(), {a, la, b, b, la, lb});
                // Skirts take the ground color, darker (they are earth).
                const float mx = static_cast<float>(p % kGrid + q % kGrid) * 0.5f;
                const float mz = static_cast<float>(p / kGrid + q / kGrid) * 0.5f;
                const std::uint32_t color = facet_color(c, std::min(mx, 63.5f), std::min(mz, 63.5f), 0.7f);
                out.face_colors.insert(out.face_colors.end(), {color, color});
            }
        }
        result.index_count = static_cast<std::uint32_t>(out.indices.size()) - result.first_index;
        return result;
    }

    // The color of the cell under a point of the chunk grid (in cells), with
    // a small shade change per facet.
    [[nodiscard]] std::uint32_t facet_color(const Chunk& c, float gx, float gz, float darken) const {
        const int cx = std::clamp(c.ox + static_cast<int>(gx), 0, cells_ - 1);
        const int cz = std::clamp(c.oz + static_cast<int>(gz), 0, cells_ - 1);
        const std::uint32_t rgba = colors_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(cells_) +
                                           static_cast<std::size_t>(cx)];
        const std::uint32_t h = hash3(static_cast<std::uint32_t>(gx * 8.0f) + static_cast<std::uint32_t>(c.ox) * 8u,
                                      static_cast<std::uint32_t>(gz * 8.0f) + static_cast<std::uint32_t>(c.oz) * 8u,
                                      seed_ ^ 0x5bd1e995u);
        const float shade = (0.94f + 0.12f * static_cast<float>(h & 0xFFu) / 255.0f) * darken;
        std::uint32_t out = rgba & 0xFF000000u;
        for (int k = 0; k < 3; ++k) {
            const float v = static_cast<float>((rgba >> (8 * k)) & 0xFFu) * shade;
            out |= static_cast<std::uint32_t>(std::clamp(v, 0.0f, 255.0f)) << (8 * k);
        }
        return out;
    }

    std::int32_t cells_;
    const std::vector<std::uint16_t>& heights_;
    const std::vector<std::uint8_t>& classes_;
    const std::vector<std::uint32_t>& colors_;
    std::uint32_t seed_;
};

}  // namespace

const FacetSettings& facet_settings(int lod) {
    return kLods[std::clamp(lod, 0, kFacetLods - 1)];
}

namespace {

// Smooth value noise for the backdrop (presentation only, floats are fine).
float value_noise(float x, float z, std::uint32_t seed) {
    const float fx = std::floor(x);
    const float fz = std::floor(z);
    const auto ix = static_cast<std::int32_t>(fx);
    const auto iz = static_cast<std::int32_t>(fz);
    float tx = x - fx;
    float tz = z - fz;
    tx = tx * tx * (3.0f - 2.0f * tx);
    tz = tz * tz * (3.0f - 2.0f * tz);
    const auto at = [&](std::int32_t px, std::int32_t pz) {
        return static_cast<float>(hash3(static_cast<std::uint32_t>(px), static_cast<std::uint32_t>(pz), seed) & 0xFFFFu) /
                   65535.0f * 2.0f - 1.0f;
    };
    const float a = at(ix, iz) + (at(ix + 1, iz) - at(ix, iz)) * tx;
    const float b = at(ix, iz + 1) + (at(ix + 1, iz + 1) - at(ix, iz + 1)) * tx;
    return a + (b - a) * tz;
}

float fbm(float x, float z, std::uint32_t seed, int octaves) {
    float sum = 0.0f;
    float amp = 0.5f;
    for (int o = 0; o < octaves; ++o) {
        sum += value_noise(x, z, seed + static_cast<std::uint32_t>(o) * 101u) * amp;
        x *= 2.03f;
        z *= 2.03f;
        amp *= 0.5f;
    }
    return sum;
}

std::uint32_t pack(float r, float g, float b) {
    const auto c = [](float v) { return static_cast<std::uint32_t>(std::clamp(v, 0.0f, 255.0f)); };
    return 0xFF000000u | (c(b) << 16) | (c(g) << 8) | c(r);
}

}  // namespace

void add_backdrop(FacetMeshes& meshes, std::int32_t cells, const std::vector<std::uint16_t>& heights_cm,
                  std::uint32_t seed, float sea_m) {
    const bool sea = sea_m >= 0.0f;
    constexpr float kStep = 32.0f;       // Meters between backdrop points.
    constexpr int kTileCells = 48;       // Grid cells per tile side.
    constexpr float kReach = 3072.0f;    // How far the mountains go past the edge.
    const auto side = static_cast<float>(cells);
    const auto v = static_cast<std::size_t>(cells + 1);
    const auto edge_height = [&](float x, float z) {
        const int px = std::clamp(static_cast<int>(x), 0, cells);
        const int pz = std::clamp(static_cast<int>(z), 0, cells);
        return static_cast<float>(heights_cm[static_cast<std::size_t>(pz) * v + static_cast<std::size_t>(px)]) * 0.01f;
    };
    // Distance outside the map (0 inside or on the edge).
    const auto outside = [&](float x, float z) {
        const float dx = std::max({0.0f, -x, x - side});
        const float dz = std::max({0.0f, -z, z - side});
        return std::sqrt(dx * dx + dz * dz);
    };
    const auto height = [&](float x, float z) {
        if (sea) {
            return sea_m - 0.05f;  // Open sea to the horizon.
        }
        const float d = outside(x, z);
        const float base = edge_height(x, z) - 1.5f;
        const float t = std::clamp(d / 500.0f, 0.0f, 1.0f);
        const float rise = t * t * (3.0f - 2.0f * t);
        const float ridge = 1.0f - std::abs(fbm(x / 1100.0f, z / 1100.0f, seed ^ 0x51u, 5)) * 2.0f;
        const float hills = fbm(x / 400.0f, z / 400.0f, seed ^ 0x77u, 3);
        return base + rise * (60.0f + std::max(0.0f, ridge) * ridge * 320.0f + hills * 40.0f);
    };
    const float start = -kReach;
    const float end = side + kReach;
    const float tile_size = kStep * kTileCells;
    for (float tz = start; tz < end; tz += tile_size) {
        for (float tx = start; tx < end; tx += tile_size) {
            ChunkLod tile;
            tile.first_vertex = static_cast<std::uint32_t>(meshes.positions.size() / 3);
            tile.first_index = static_cast<std::uint32_t>(meshes.indices.size());
            tile.first_face = static_cast<std::uint32_t>(meshes.face_colors.size());
            std::array<float, 6> box = {1e30f, 1e30f, 1e30f, -1e30f, -1e30f, -1e30f};
            // The tile's grid points, nudged so facets are irregular.
            std::vector<float> grid;
            for (int j = 0; j <= kTileCells; ++j) {
                for (int i = 0; i <= kTileCells; ++i) {
                    float x = tx + static_cast<float>(i) * kStep;
                    float z = tz + static_cast<float>(j) * kStep;
                    const std::uint32_t h = hash3(static_cast<std::uint32_t>(x + 100000.0f),
                                                  static_cast<std::uint32_t>(z + 100000.0f), seed ^ 0xB4u);
                    if (outside(x, z) > kStep) {
                        x += (static_cast<float>(h & 0xFFu) / 255.0f - 0.5f) * kStep * 0.6f;
                        z += (static_cast<float>((h >> 8) & 0xFFu) / 255.0f - 0.5f) * kStep * 0.6f;
                    }
                    grid.insert(grid.end(), {x, height(x, z), z});
                }
            }
            meshes.positions.insert(meshes.positions.end(), grid.begin(), grid.end());
            for (std::size_t k = 0; k < grid.size(); k += 3) {
                box[0] = std::min(box[0], grid[k]);
                box[1] = std::min(box[1], grid[k + 1]);
                box[2] = std::min(box[2], grid[k + 2]);
                box[3] = std::max(box[3], grid[k]);
                box[4] = std::max(box[4], grid[k + 1]);
                box[5] = std::max(box[5], grid[k + 2]);
            }
            const auto point = [&](int i, int j) { return static_cast<std::uint16_t>(j * (kTileCells + 1) + i); };
            const auto face = [&](std::uint16_t a, std::uint16_t b, std::uint16_t c) {
                const float* pa = &grid[a * 3u];
                const float* pb = &grid[b * 3u];
                const float* pc = &grid[c * 3u];
                const float cx = (pa[0] + pb[0] + pc[0]) / 3.0f;
                const float cz = (pa[2] + pb[2] + pc[2]) / 3.0f;
                const float cy = (pa[1] + pb[1] + pc[1]) / 3.0f;
                const float above = cy - edge_height(cx, cz);
                const float lo = std::min({pa[1], pb[1], pc[1]});
                const float hi = std::max({pa[1], pb[1], pc[1]});
                const float steep = (hi - lo) / kStep;
                const std::uint32_t h = hash3(static_cast<std::uint32_t>(cx * 3.0f + 90000.0f),
                                              static_cast<std::uint32_t>(cz * 3.0f + 90000.0f), seed ^ 0xC5u);
                const float shade = 0.9f + 0.2f * static_cast<float>(h & 0xFFu) / 255.0f;
                std::uint32_t color = 0;
                if (sea) {
                    const float calm = 0.97f + 0.06f * static_cast<float>(h & 0xFFu) / 255.0f;
                    color = pack(108 * calm, 158 * calm, 184 * calm);  // Sea, like the water seen from afar.
                } else if (above > 230.0f) {
                    color = pack(236 * shade, 240 * shade, 244 * shade);  // Snow.
                } else if (above > 40.0f || steep > 0.9f) {
                    color = pack(140 * shade, 96 * shade, 68 * shade);    // Rock.
                } else {
                    color = pack(86 * shade, 150 * shade, 56 * shade);    // Grass.
                }
                meshes.indices.insert(meshes.indices.end(), {a, b, c});
                meshes.face_colors.push_back(color);
            };
            for (int j = 0; j < kTileCells; ++j) {
                for (int i = 0; i < kTileCells; ++i) {
                    const float x0 = tx + static_cast<float>(i) * kStep;
                    const float z0 = tz + static_cast<float>(j) * kStep;
                    // Skip cells over the map itself.
                    if (x0 + kStep > 0.0f && x0 < side && z0 + kStep > 0.0f && z0 < side) {
                        continue;
                    }
                    const std::uint16_t a = point(i, j);
                    const std::uint16_t b = point(i + 1, j);
                    const std::uint16_t c = point(i, j + 1);
                    const std::uint16_t d = point(i + 1, j + 1);
                    if (((i + j) & 1) == 0) {
                        face(a, c, b);
                        face(b, c, d);
                    } else {
                        face(a, c, d);
                        face(a, d, b);
                    }
                }
            }
            tile.index_count = static_cast<std::uint32_t>(meshes.indices.size()) - tile.first_index;
            if (tile.index_count == 0) {
                meshes.positions.resize(tile.first_vertex * 3u);
                continue;
            }
            meshes.backdrop.push_back(tile);
            meshes.backdrop_bounds.push_back(box);
        }
    }
}

std::size_t FacetMeshes::triangle_count(int lod) const {
    std::size_t n = 0;
    for (const auto& c : chunks) {
        n += c[static_cast<std::size_t>(lod)].index_count / 3;
    }
    return n;
}

FacetMeshes build_facet_meshes(std::int32_t cells, const std::vector<std::uint16_t>& heights_cm,
                               const std::vector<std::uint8_t>& classes, const std::vector<std::uint32_t>& cell_colors,
                               std::uint32_t seed) {
    const auto area = static_cast<std::size_t>(cells) * static_cast<std::size_t>(cells);
    if (cells < kTile || cells % kTile != 0 ||
        heights_cm.size() != static_cast<std::size_t>(cells + 1) * static_cast<std::size_t>(cells + 1) ||
        classes.size() != area || cell_colors.size() != area) {
        return {};
    }
    return Builder(cells, heights_cm, classes, cell_colors, seed).build();
}

}  // namespace sc::render
