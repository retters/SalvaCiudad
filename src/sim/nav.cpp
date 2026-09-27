#include "sim/nav.h"

#include <algorithm>
#include <queue>

namespace sc::sim {

namespace {

constexpr std::uint32_t kNoParent = 0xFFFFFFFFu;

}  // namespace

void NavGrid::build(const MapData& map) {
    side_ = map.size / kCell;
    const auto cells = static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_);
    terrain_cost_.assign(cells, 10);
    building_.assign(cells, 0);
    gate_.assign(cells, 0);
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
    if (region_version_ == version_ && region_.size() == terrain_cost_.size()) {
        return;
    }
    region_version_ = version_;
    region_.assign(terrain_cost_.size(), 0);
    std::uint32_t next = 1;
    std::vector<std::uint32_t> stack;
    for (std::size_t start = 0; start < region_.size(); ++start) {
        const auto sx = static_cast<std::int32_t>(start % static_cast<std::size_t>(side_));
        const auto sz = static_cast<std::int32_t>(start / static_cast<std::size_t>(side_));
        if (region_[start] != 0 || !walkable(sx, sz)) {
            continue;
        }
        // Same moves as the search: straight, and diagonal without cutting corners.
        region_[start] = next;
        stack.push_back(static_cast<std::uint32_t>(start));
        while (!stack.empty()) {
            const std::uint32_t c = stack.back();
            stack.pop_back();
            const auto cx = static_cast<std::int32_t>(c % static_cast<std::uint32_t>(side_));
            const auto cz = static_cast<std::int32_t>(c / static_cast<std::uint32_t>(side_));
            constexpr std::int32_t kDx[4] = {1, -1, 0, 0};
            constexpr std::int32_t kDz[4] = {0, 0, 1, -1};
            for (int k = 0; k < 4; ++k) {
                const std::int32_t nx = cx + kDx[k];
                const std::int32_t nz = cz + kDz[k];
                if (walkable(nx, nz)) {
                    std::uint32_t& r = region_[index(nx, nz)];
                    if (r == 0) {
                        r = next;
                        stack.push_back(static_cast<std::uint32_t>(index(nx, nz)));
                    }
                }
            }
        }
        ++next;
    }
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
    return region_[index(ax, az)] == region_[index(bx, bz)];
}

void NavGrid::set_gate(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool on) {
    for (std::int32_t cz = std::max(0, z0 / kCell); cz <= std::min(side_ - 1, (z1 - 1) / kCell); ++cz) {
        for (std::int32_t cx = std::max(0, x0 / kCell); cx <= std::min(side_ - 1, (x1 - 1) / kCell); ++cx) {
            std::uint8_t& g = gate_[index(cx, cz)];
            g = static_cast<std::uint8_t>(on ? std::min(255, g + 1) : std::max(0, g - 1));
        }
    }
}

bool NavGrid::obstacle(std::int32_t cx, std::int32_t cz) const {
    if (cx < 0 || cz < 0 || cx >= side_ || cz >= side_) {
        return false;
    }
    const std::size_t i = index(cx, cz);
    return building_[i] != 0 || gate_[i] != 0;
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

bool NavGrid::search(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out, std::int32_t max_nodes, bool through) {
    out.clear();
    ++searches_;
    if (side_ == 0) {
        return false;
    }
    std::int32_t sx = cell_of(from.x);
    std::int32_t sz = cell_of(from.z);
    std::int32_t tx = cell_of(to.x);
    std::int32_t tz = cell_of(to.z);
    const auto pass = [&](std::int32_t x, std::int32_t z) { return through ? ground(x, z) : walkable(x, z); };
    const bool exact_target = pass(tx, tz);
    // Someone standing on a blocked cell (a building just placed on them)
    // walks out from the nearest free one.
    if (!through && (!nearest_walkable(sx, sz) || !nearest_walkable(tx, tz))) {
        return false;
    }
    if (through && (!ground(sx, sz) || !ground(tx, tz))) {
        return false;
    }
    // Another island, or the other side of a wall: no need to search.
    update_regions();
    if (!through && region_[index(sx, sz)] != region_[index(tx, tz)]) {
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
    const auto heuristic = [&](std::int32_t x, std::int32_t z) {
        const std::int32_t dx = std::abs(x - tx);
        const std::int32_t dz = std::abs(z - tz);
        return static_cast<std::uint32_t>(10 * std::max(dx, dz) + 4 * std::min(dx, dz));
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
            const std::uint32_t step = terrain_cost_[ni] + (through && obstacle(nx, nz) ? 250u : 0u);
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
            const std::uint32_t step = terrain_cost_[index(nx, nz)];
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
