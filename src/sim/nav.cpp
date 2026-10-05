#include "sim/nav.h"

#include <algorithm>
#include <queue>

namespace sc::sim {

namespace {

constexpr std::uint32_t kNoParent = 0xFFFFFFFFu;

std::uint32_t find_root(std::vector<std::uint32_t>& parent, std::uint32_t i) {
    while (parent[i] != i) {
        parent[i] = parent[parent[i]];
        i = parent[i];
    }
    return i;
}

}  // namespace

void NavGrid::Areas::reset(std::int32_t cells_per_side) {
    side = cells_per_side;
    blocks = (side + kBlock - 1) / kBlock;
    const auto b = static_cast<std::size_t>(blocks) * static_cast<std::size_t>(blocks);
    local.assign(static_cast<std::size_t>(side) * static_cast<std::size_t>(side), 0);
    count.assign(b, 0);
    base.assign(b, 0);
    dirty.assign(b, 1);
    any_dirty = true;
    root.clear();
    right.assign(b, {});
    down.assign(b, {});
}

void NavGrid::Areas::mark(std::int32_t cx0, std::int32_t cz0, std::int32_t cx1, std::int32_t cz1) {
    if (blocks == 0) {
        return;
    }
    for (std::int32_t bz = std::max(0, cz0 / kBlock); bz <= std::min(blocks - 1, cz1 / kBlock); ++bz) {
        for (std::int32_t bx = std::max(0, cx0 / kBlock); bx <= std::min(blocks - 1, cx1 / kBlock); ++bx) {
            dirty[static_cast<std::size_t>(bz * blocks + bx)] = 1;
            any_dirty = true;
        }
    }
}

template <class Open>
void NavGrid::Areas::update(const Open& open) {
    if (!any_dirty) {
        return;
    }
    any_dirty = false;
    const auto cell = [&](std::int32_t x, std::int32_t z) {
        return static_cast<std::size_t>(z) * static_cast<std::size_t>(side) + static_cast<std::size_t>(x);
    };
    // Relabel the changed blocks on their own.
    for (std::int32_t bz = 0; bz < blocks; ++bz) {
        for (std::int32_t bx = 0; bx < blocks; ++bx) {
            const auto b = static_cast<std::size_t>(bz * blocks + bx);
            if (dirty[b] == 0) {
                continue;
            }
            const std::int32_t x0 = bx * kBlock;
            const std::int32_t z0 = bz * kBlock;
            const std::int32_t w = std::min(kBlock, side - x0);
            const std::int32_t h = std::min(kBlock, side - z0);
            for (std::int32_t z = z0; z < z0 + h; ++z) {
                std::fill_n(local.begin() + static_cast<std::ptrdiff_t>(cell(x0, z)), w, std::uint16_t{0});
            }
            std::uint16_t next = 0;
            for (std::int32_t sz = 0; sz < h; ++sz) {
                for (std::int32_t sx = 0; sx < w; ++sx) {
                    if (local[cell(x0 + sx, z0 + sz)] != 0 || !open(x0 + sx, z0 + sz)) {
                        continue;
                    }
                    ++next;
                    local[cell(x0 + sx, z0 + sz)] = next;
                    stack.assign(1, static_cast<std::uint16_t>(sz * kBlock + sx));
                    while (!stack.empty()) {
                        const std::int32_t lx = stack.back() % kBlock;
                        const std::int32_t lz = stack.back() / kBlock;
                        stack.pop_back();
                        constexpr std::int32_t kDx[4] = {1, -1, 0, 0};
                        constexpr std::int32_t kDz[4] = {0, 0, 1, -1};
                        for (int k = 0; k < 4; ++k) {
                            const std::int32_t nx = lx + kDx[k];
                            const std::int32_t nz = lz + kDz[k];
                            if (nx < 0 || nz < 0 || nx >= w || nz >= h) {
                                continue;
                            }
                            std::uint16_t& l = local[cell(x0 + nx, z0 + nz)];
                            if (l == 0 && open(x0 + nx, z0 + nz)) {
                                l = next;
                                stack.push_back(static_cast<std::uint16_t>(nz * kBlock + nx));
                            }
                        }
                    }
                }
            }
            count[b] = next;
        }
    }
    // The pairs along the edges of changed blocks.
    const auto edge = [&](Pairs& out, std::int32_t ax, std::int32_t az, std::int32_t dx, std::int32_t dz, std::int32_t n,
                          std::int32_t step_x, std::int32_t step_z) {
        out.clear();
        for (std::int32_t k = 0; k < n; ++k) {
            const std::int32_t x = ax + k * step_x;
            const std::int32_t z = az + k * step_z;
            const std::uint16_t a = local[cell(x, z)];
            const std::uint16_t b = local[cell(x + dx, z + dz)];
            if (a != 0 && b != 0 && (out.empty() || out.back() != std::pair{a, b})) {
                out.emplace_back(a, b);
            }
        }
    };
    for (std::int32_t bz = 0; bz < blocks; ++bz) {
        for (std::int32_t bx = 0; bx < blocks; ++bx) {
            const auto b = static_cast<std::size_t>(bz * blocks + bx);
            const std::int32_t x0 = bx * kBlock;
            const std::int32_t z0 = bz * kBlock;
            if (bx + 1 < blocks && (dirty[b] != 0 || dirty[b + 1] != 0)) {
                edge(right[b], x0 + kBlock - 1, z0, 1, 0, std::min(kBlock, side - z0), 0, 1);
            }
            if (bz + 1 < blocks && (dirty[b] != 0 || dirty[b + static_cast<std::size_t>(blocks)] != 0)) {
                edge(down[b], x0, z0 + kBlock - 1, 0, 1, std::min(kBlock, side - x0), 1, 0);
            }
        }
    }
    std::fill(dirty.begin(), dirty.end(), std::uint8_t{0});
    // Join the areas that touch across block edges.
    std::uint32_t total = 0;
    for (std::size_t b = 0; b < count.size(); ++b) {
        base[b] = total;
        total += count[b];
    }
    root.resize(total);
    for (std::uint32_t i = 0; i < total; ++i) {
        root[i] = i;
    }
    const auto join = [&](std::uint32_t a, std::uint32_t b) {
        const std::uint32_t ra = find_root(root, a);
        const std::uint32_t rb = find_root(root, b);
        // The smaller label wins, so the result is the same whatever the order.
        root[std::max(ra, rb)] = std::min(ra, rb);
    };
    for (std::size_t b = 0; b < count.size(); ++b) {
        for (const auto& [a, n] : right[b]) {
            join(base[b] + a - 1, base[b + 1] + n - 1);
        }
        for (const auto& [a, n] : down[b]) {
            join(base[b] + a - 1, base[b + static_cast<std::size_t>(blocks)] + n - 1);
        }
    }
    for (std::uint32_t i = 0; i < total; ++i) {
        root[i] = find_root(root, i);
    }
}

std::uint32_t NavGrid::Areas::at(std::int32_t cx, std::int32_t cz) const {
    const std::uint16_t l = local[static_cast<std::size_t>(cz) * static_cast<std::size_t>(side) + static_cast<std::size_t>(cx)];
    if (l == 0) {
        return 0;
    }
    return root[base[static_cast<std::size_t>((cz / kBlock) * blocks + cx / kBlock)] + l - 1] + 1;
}

void NavGrid::build(const MapData& map) {
    side_ = map.size / kCell;
    const auto cells = static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_);
    terrain_cost_.assign(cells, 10);
    building_.assign(cells, 0);
    gate_.assign(cells, 0);
    road_.clear();
    road_.shrink_to_fit();
    road_cells_.fill(0);
    least_step_ = 10;
    walk_areas_.reset(side_);
    land_areas_ = Areas{};
    for (std::int32_t cz = 0; cz < side_; ++cz) {
        for (std::int32_t cx = 0; cx < side_; ++cx) {
            const std::int32_t mx = cx * kCell;
            const std::int32_t mz = cz * kCell;
            int wet = 0;
            int forest = 0;
            for (std::int32_t dz = 0; dz < kCell; ++dz) {
                for (std::int32_t dx = 0; dx < kCell; ++dx) {
                    wet += map.water_at(mx + dx, mz + dz) ? 1 : 0;
                    forest += map.terrain_at(mx + dx, mz + dz) == Terrain::ForestFloor ? 1 : 0;
                }
            }
            // Steepness: height range over the cell, in centimeters.
            std::int32_t lo = 65535;
            std::int32_t hi = 0;
            for (const std::int32_t vz : {mz, mz + kCell}) {
                for (const std::int32_t vx : {mx, mx + kCell}) {
                    const std::int32_t h = map.height_cm(vx, vz);
                    lo = std::min(lo, h);
                    hi = std::max(hi, h);
                }
            }
            const std::int32_t slope = hi - lo;  // cm over 2 m.
            // The seams between separate maps.
            const std::int32_t region = map.region_size();
            const bool seam = region > 0 && (mx % region == 0 || mz % region == 0 || (mx + kCell) % region == 0 ||
                                             (mz + kCell) % region == 0);
            std::uint8_t cost = 10;
            if (wet >= 2 || slope > 180 || seam) {
                cost = 0;  // Water or cliffs.
            } else {
                cost = static_cast<std::uint8_t>(10 + std::min(20, slope / 12) + (forest > 0 ? 2 : 0) + (wet > 0 ? 6 : 0));
            }
            terrain_cost_[index(cx, cz)] = cost;
        }
    }
}

bool NavGrid::walkable(std::int32_t cx, std::int32_t cz) const {
    if (cx < 0 || cz < 0 || cx >= side_ || cz >= side_) {
        return false;
    }
    const std::size_t i = index(cx, cz);
    return terrain_cost_[i] != 0 && building_[i] == 0;
}

void NavGrid::set_building(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool blocked) {
    ++version_;
    const std::int32_t c0x = std::max(0, x0 / kCell);
    const std::int32_t c0z = std::max(0, z0 / kCell);
    const std::int32_t c1x = std::min(side_ - 1, (x1 - 1) / kCell);
    const std::int32_t c1z = std::min(side_ - 1, (z1 - 1) / kCell);
    walk_areas_.mark(c0x, c0z, c1x, c1z);
    for (std::int32_t cz = c0z; cz <= c1z; ++cz) {
        for (std::int32_t cx = c0x; cx <= c1x; ++cx) {
            std::uint8_t& b = building_[index(cx, cz)];
            b = static_cast<std::uint8_t>(blocked ? std::min(255, b + 1) : std::max(0, b - 1));
        }
    }
}

std::int32_t NavGrid::cell_of(Fixed meters) const {
    return std::clamp(meters.floor_int() / kCell, 0, std::max(0, side_ - 1));
}

FixedVec2 NavGrid::center(std::int32_t cx, std::int32_t cz) const {
    return {Fixed::from_int(cx * kCell + kCell / 2), Fixed::from_int(cz * kCell + kCell / 2)};
}

std::int32_t NavGrid::distance_estimate(FixedVec2 a, FixedVec2 b) {
    return (a - b).length().floor_int();
}

bool NavGrid::nearest_walkable(std::int32_t& cx, std::int32_t& cz) const {
    if (walkable(cx, cz)) {
        return true;
    }
    for (std::int32_t r = 1; r <= 6; ++r) {
        for (std::int32_t dz = -r; dz <= r; ++dz) {
            for (std::int32_t dx = -r; dx <= r; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) != r) {
                    continue;
                }
                if (walkable(cx + dx, cz + dz)) {
                    cx += dx;
                    cz += dz;
                    return true;
                }
            }
        }
    }
    return false;
}

void NavGrid::update_regions() const {
    if (walk_areas_.side != side_) {
        walk_areas_.reset(side_);
    }
    walk_areas_.update([this](std::int32_t cx, std::int32_t cz) { return walkable(cx, cz); });
}

bool NavGrid::nearest_ground(std::int32_t& cx, std::int32_t& cz) const {
    for (std::int32_t r = 0; r <= 6; ++r) {
        for (std::int32_t dz = -r; dz <= r; ++dz) {
            for (std::int32_t dx = -r; dx <= r; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) == r && ground(cx + dx, cz + dz)) {
                    cx += dx;
                    cz += dz;
                    return true;
                }
            }
        }
    }
    return false;
}

bool NavGrid::same_land(FixedVec2 a, FixedVec2 b) const {
    if (side_ == 0) {
        return false;
    }
    std::int32_t ax = cell_of(a.x), az = cell_of(a.z), bx = cell_of(b.x), bz = cell_of(b.z);
    if (!nearest_ground(ax, az) || !nearest_ground(bx, bz)) {
        return false;
    }
    // The ground never changes: labeled once.
    if (land_areas_.side != side_) {
        land_areas_.reset(side_);
    }
    land_areas_.update([this](std::int32_t cx, std::int32_t cz) { return ground(cx, cz); });
    return land_areas_.at(ax, az) == land_areas_.at(bx, bz);
}

bool NavGrid::connected(FixedVec2 a, FixedVec2 b) const {
    if (side_ == 0) {
        return false;
    }
    std::int32_t ax = cell_of(a.x), az = cell_of(a.z), bx = cell_of(b.x), bz = cell_of(b.z);
    if (!nearest_walkable(ax, az) || !nearest_walkable(bx, bz)) {
        return false;
    }
    update_regions();
    return walk_areas_.at(ax, az) == walk_areas_.at(bx, bz);
}

void NavGrid::set_gate(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool on) {
    for (std::int32_t cz = std::max(0, z0 / kCell); cz <= std::min(side_ - 1, (z1 - 1) / kCell); ++cz) {
        for (std::int32_t cx = std::max(0, x0 / kCell); cx <= std::min(side_ - 1, (x1 - 1) / kCell); ++cx) {
            std::uint8_t& g = gate_[index(cx, cz)];
            const int gates = g & 0x0F;
            g = static_cast<std::uint8_t>((g & 0xF0) | (on ? std::min(15, gates + 1) : std::max(0, gates - 1)));
        }
    }
}

void NavGrid::set_road_kinds(const std::vector<std::int32_t>& percents) {
    road_percent_.fill(100);
    for (std::size_t k = 0; k < percents.size() && k + 1 < road_percent_.size(); ++k) {
        road_percent_[k + 1] = std::clamp(percents[k], 100, 1000);
    }
}

void NavGrid::set_road(std::int32_t cx, std::int32_t cz, std::uint8_t kind) {
    if (cx < 0 || cz < 0 || cx >= side_ || cz >= side_ || kind >= road_cells_.size()) {
        return;
    }
    if (road_.empty()) {
        if (kind == 0) {
            return;
        }
        road_.assign(static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_), 0);
    }
    std::uint8_t& cell = road_[index(cx, cz)];
    if (cell == kind) {
        return;
    }
    --road_cells_[cell];
    ++road_cells_[kind];
    cell = kind;
    ++version_;  // What is within reach of where changed.
    // A search must never guess a way cheaper than it can be: its guess per
    // step is the cost of flat ground on the fastest road there is.
    std::int32_t fastest = 100;
    for (std::size_t k = 1; k < road_cells_.size(); ++k) {
        if (road_cells_[k] != 0) {
            fastest = std::max(fastest, road_percent_[k]);
        }
    }
    least_step_ = std::max<std::uint32_t>(1, (10u * 100u + static_cast<std::uint32_t>(fastest) / 2) / static_cast<std::uint32_t>(fastest));
}

void NavGrid::set_barrier(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool on) {
    for (std::int32_t cz = std::max(0, z0 / kCell); cz <= std::min(side_ - 1, (z1 - 1) / kCell); ++cz) {
        for (std::int32_t cx = std::max(0, x0 / kCell); cx <= std::min(side_ - 1, (x1 - 1) / kCell); ++cx) {
            std::uint8_t& g = gate_[index(cx, cz)];
            const int barriers = g >> 4;
            g = static_cast<std::uint8_t>((g & 0x0F) | ((on ? std::min(15, barriers + 1) : std::max(0, barriers - 1)) << 4));
        }
    }
}

bool NavGrid::barrier(std::int32_t cx, std::int32_t cz) const {
    return cx >= 0 && cz >= 0 && cx < side_ && cz < side_ && (gate_[index(cx, cz)] >> 4) != 0;
}

bool NavGrid::obstacle(std::int32_t cx, std::int32_t cz) const {
    if (cx < 0 || cz < 0 || cx >= side_ || cz >= side_) {
        return false;
    }
    const std::size_t i = index(cx, cz);
    return building_[i] != 0 || (gate_[i] & 0x0F) != 0;
}

bool NavGrid::ground(std::int32_t cx, std::int32_t cz) const {
    return cx >= 0 && cz >= 0 && cx < side_ && cz < side_ && terrain_cost_[index(cx, cz)] != 0;
}

bool NavGrid::find_path_through(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out, std::int32_t max_nodes) {
    return search(from, to, out, max_nodes, true);
}

bool NavGrid::find_path(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out, std::int32_t max_nodes) {
    return search(from, to, out, max_nodes, false);
}

bool NavGrid::find_path_within(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out,
                               const std::function<bool(std::int32_t, std::int32_t)>& allow, std::int32_t max_nodes) {
    return search(from, to, out, max_nodes, false, &allow);
}

bool NavGrid::search(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out, std::int32_t max_nodes, bool through,
                     const std::function<bool(std::int32_t, std::int32_t)>* allow) {
    out.clear();
    ++searches_;
    if (side_ == 0) {
        return false;
    }
    std::int32_t sx = cell_of(from.x);
    std::int32_t sz = cell_of(from.z);
    std::int32_t tx = cell_of(to.x);
    std::int32_t tz = cell_of(to.z);
    const auto pass = [&](std::int32_t x, std::int32_t z) {
        return (through ? ground(x, z) : walkable(x, z)) && (allow == nullptr || (*allow)(x, z));
    };
    const bool exact_target = pass(tx, tz);
    // Someone standing on a blocked cell (a building just placed on them)
    // walks out from the nearest free one.
    if (!through && (!nearest_walkable(sx, sz) || !nearest_walkable(tx, tz))) {
        return false;
    }
    if (allow != nullptr && !(*allow)(tx, tz)) {
        return false;  // The place to go is not one of the cells allowed.
    }
    if (through && (!ground(sx, sz) || !ground(tx, tz))) {
        return false;
    }
    // Another island, or the other side of a wall: no need to search.
    update_regions();
    if (!through && walk_areas_.at(sx, sz) != walk_areas_.at(tx, tz)) {
        return false;
    }
    if (sx == tx && sz == tz) {
        out.push_back(exact_target ? to : center(tx, tz));
        return true;
    }
    const auto cells = static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_);
    if (stamp_.size() != cells) {
        stamp_.assign(cells, 0);
        g_.assign(cells, 0);
        parent_.assign(cells, kNoParent);
        closed_.assign(cells, 0);
    }
    if (++current_stamp_ == 0) {
        std::fill(stamp_.begin(), stamp_.end(), 0u);
        current_stamp_ = 1;
    }
    const auto touch = [&](std::size_t i) {
        if (stamp_[i] != current_stamp_) {
            stamp_[i] = current_stamp_;
            g_[i] = 0xFFFFFFFFu;
            parent_[i] = kNoParent;
            closed_[i] = 0;
        }
    };
    // Without roads: 10 a straight step and 14 a diagonal one, as ever.
    const std::uint32_t straight = least_step_;
    const std::uint32_t diagonal = least_step_ * 14 / 10 - least_step_;
    const auto heuristic = [&](std::int32_t x, std::int32_t z) {
        const auto dx = static_cast<std::uint32_t>(std::abs(x - tx));
        const auto dz = static_cast<std::uint32_t>(std::abs(z - tz));
        return straight * std::max(dx, dz) + diagonal * std::min(dx, dz);
    };
    // Min-heap on (f, cell index): the index breaks ties deterministically.
    std::priority_queue<std::uint64_t, std::vector<std::uint64_t>, std::greater<>> open;
    const std::size_t start = index(sx, sz);
    const std::size_t goal = index(tx, tz);
    touch(start);
    g_[start] = 0;
    open.push((static_cast<std::uint64_t>(heuristic(sx, sz)) << 32) | start);
    std::int32_t expanded = 0;
    bool found = false;
    constexpr std::int32_t kDx[8] = {1, -1, 0, 0, 1, 1, -1, -1};
    constexpr std::int32_t kDz[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    while (!open.empty()) {
        const auto cur = static_cast<std::size_t>(open.top() & 0xFFFFFFFFu);
        open.pop();
        if (closed_[cur] != 0) {
            continue;
        }
        closed_[cur] = 1;
        if (cur == goal) {
            found = true;
            break;
        }
        if (++expanded > max_nodes) {
            break;
        }
        const auto cx = static_cast<std::int32_t>(cur % static_cast<std::size_t>(side_));
        const auto cz = static_cast<std::int32_t>(cur / static_cast<std::size_t>(side_));
        for (int k = 0; k < 8; ++k) {
            const std::int32_t nx = cx + kDx[k];
            const std::int32_t nz = cz + kDz[k];
            if (!pass(nx, nz)) {
                continue;
            }
            // No corner cutting past blocked cells.
            if (k >= 4 && (!pass(cx + kDx[k], cz) || !pass(cx, cz + kDz[k]))) {
                continue;
            }
            const std::size_t ni = index(nx, nz);
            touch(ni);
            if (closed_[ni] != 0) {
                continue;
            }
            // Breaking through costs what walking 25 cells around would.
            const std::uint32_t step = step_cost(ni) + (through && obstacle(nx, nz) ? 250u : 0u);
            const std::uint32_t g = g_[cur] + (k >= 4 ? step * 14 / 10 : step);
            if (g < g_[ni]) {
                g_[ni] = g;
                parent_[ni] = static_cast<std::uint32_t>(cur);
                open.push((static_cast<std::uint64_t>(g + heuristic(nx, nz)) << 32) | ni);
            }
        }
    }
    if (!found) {
        return false;
    }
    std::vector<std::size_t> cells_back;
    for (std::size_t i = goal; i != start && i != kNoParent; i = parent_[i]) {
        cells_back.push_back(i);
    }
    // Every cell is a waypoint except runs in a straight line.
    FixedVec2 last_dir{};
    for (auto it = cells_back.rbegin(); it != cells_back.rend(); ++it) {
        const auto x = static_cast<std::int32_t>(*it % static_cast<std::size_t>(side_));
        const auto z = static_cast<std::int32_t>(*it / static_cast<std::size_t>(side_));
        const FixedVec2 p = center(x, z);
        if (out.size() >= 2) {
            const FixedVec2 dir = p - out.back();
            if (dir == last_dir) {
                out.back() = p;
                continue;
            }
            last_dir = dir;
        } else if (!out.empty()) {
            last_dir = p - out.back();
        }
        out.push_back(p);
    }
    if (exact_target) {
        if (out.empty()) {
            out.push_back(to);
        } else {
            out.back() = to;
        }
    }
    return true;
}

NavGrid::Area NavGrid::flood(FixedVec2 from, std::uint16_t max_cost) const {
    Area area;
    area.version = version_;
    std::int32_t sx = cell_of(from.x);
    std::int32_t sz = cell_of(from.z);
    if (side_ == 0 || !nearest_walkable(sx, sz)) {
        return area;
    }
    const std::int32_t reach = max_cost / 10 + 1;
    area.x0 = sx - reach;
    area.z0 = sz - reach;
    area.side = 2 * reach + 1;
    area.cost.assign(static_cast<std::size_t>(area.side) * static_cast<std::size_t>(area.side), 0xFFFF);
    const auto local = [&](std::int32_t x, std::int32_t z) {
        return static_cast<std::size_t>((z - area.z0) * area.side + (x - area.x0));
    };
    // Dijkstra; the key packs (cost, local index) so ties break by index.
    std::priority_queue<std::uint64_t, std::vector<std::uint64_t>, std::greater<>> open;
    area.cost[local(sx, sz)] = 0;
    open.push(local(sx, sz));
    constexpr std::int32_t kDx[8] = {1, -1, 0, 0, 1, 1, -1, -1};
    constexpr std::int32_t kDz[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    while (!open.empty()) {
        const std::uint64_t top = open.top();
        open.pop();
        const auto li = static_cast<std::size_t>(top & 0xFFFFFFFFu);
        const auto c = static_cast<std::uint32_t>(top >> 32);
        if (c != area.cost[li]) {
            continue;  // A stale entry.
        }
        const std::int32_t cx = area.x0 + static_cast<std::int32_t>(li % static_cast<std::size_t>(area.side));
        const std::int32_t cz = area.z0 + static_cast<std::int32_t>(li / static_cast<std::size_t>(area.side));
        for (int k = 0; k < 8; ++k) {
            const std::int32_t nx = cx + kDx[k];
            const std::int32_t nz = cz + kDz[k];
            if (nx < area.x0 || nz < area.z0 || nx >= area.x0 + area.side || nz >= area.z0 + area.side ||
                !walkable(nx, nz)) {
                continue;
            }
            if (k >= 4 && (!walkable(cx + kDx[k], cz) || !walkable(cx, cz + kDz[k]))) {
                continue;
            }
            const std::uint32_t step = step_cost(index(nx, nz));
            const std::uint32_t n = c + (k >= 4 ? step * 14 / 10 : step);
            const std::size_t ni = local(nx, nz);
            if (n <= max_cost && n < area.cost[ni]) {
                area.cost[ni] = static_cast<std::uint16_t>(n);
                open.push((static_cast<std::uint64_t>(n) << 32) | ni);
            }
        }
    }
    return area;
}

}  // namespace sc::sim
