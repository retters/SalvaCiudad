#include "game/fog_view.h"

#include <algorithm>
#include <bit>
#include <cmath>

namespace sc {

namespace {

// Words of a grid holding rows first..last (inclusive), as [begin, end).
std::pair<std::size_t, std::size_t> row_words(std::int32_t side, std::int32_t first, std::int32_t last) {
    if (first > last || side <= 0) {
        return {0, 0};
    }
    const std::size_t begin = static_cast<std::size_t>(first) * static_cast<std::size_t>(side) / 64;
    const std::size_t end = (static_cast<std::size_t>(last + 1) * static_cast<std::size_t>(side) - 1) / 64 + 1;
    return {begin, end};
}

std::int32_t cell_of(float meters) {
    return static_cast<std::int32_t>(std::floor(meters / static_cast<float>(sim::kFogCell)));
}

}  // namespace

std::vector<std::uint16_t> fog_ceiling(const sim::MapData& map, std::int32_t side) {
    if (side <= 0 || map.size <= 0 || map.heights.empty()) {
        return {};
    }
    const auto n = static_cast<std::size_t>(side);
    constexpr std::int32_t kCell = FogView::kCeilingCell;
    constexpr std::int32_t kStep = 4;  // Samples every 4 m inside a cell.
    // The mean height of each cell.
    std::vector<float> a(n * n, 0.0f);
    for (std::int32_t cz = 0; cz < side; ++cz) {
        for (std::int32_t cx = 0; cx < side; ++cx) {
            float sum = 0.0f;
            int count = 0;
            for (std::int32_t z = cz * kCell + kStep / 2; z < (cz + 1) * kCell; z += kStep) {
                for (std::int32_t x = cx * kCell + kStep / 2; x < (cx + 1) * kCell; x += kStep) {
                    sum += static_cast<float>(map.height_cm(x, z));
                    ++count;
                }
            }
            a[static_cast<std::size_t>(cz) * n + static_cast<std::size_t>(cx)] = sum / static_cast<float>(count);
        }
    }
    // Smoothed twice over 7 cells (112 m, weighted to the middle): wide
    // ground keeps its height, lone peaks and trees stick out.
    constexpr std::int32_t kRadius = 3;
    std::vector<float> b(n * n, 0.0f);
    const auto blur = [&](const std::vector<float>& from, std::vector<float>& to, bool across) {
        for (std::int32_t i = 0; i < side; ++i) {
            for (std::int32_t j = 0; j < side; ++j) {
                float sum = 0.0f;
                for (std::int32_t k = -kRadius; k <= kRadius; ++k) {
                    const std::int32_t m = std::clamp(j + k, 0, side - 1);
                    const std::size_t at = across ? static_cast<std::size_t>(i) * n + static_cast<std::size_t>(m)
                                                   : static_cast<std::size_t>(m) * n + static_cast<std::size_t>(i);
                    sum += from[at];
                }
                const std::size_t out = across ? static_cast<std::size_t>(i) * n + static_cast<std::size_t>(j)
                                               : static_cast<std::size_t>(j) * n + static_cast<std::size_t>(i);
                to[out] = sum / static_cast<float>(2 * kRadius + 1);
            }
        }
    };
    for (int pass = 0; pass < 2; ++pass) {
        blur(a, b, true);
        blur(b, a, false);
    }
    std::vector<std::uint16_t> out(n * n);
    for (std::size_t i = 0; i < out.size(); ++i) {
        out[i] = static_cast<std::uint16_t>(std::clamp(a[i] + static_cast<float>(FogView::kCeilingAbove), 0.0f, 65535.0f));
    }
    return out;
}

void FogView::begin(const sim::Game& game, std::uint8_t group) {
    game_mode_ = game.rules().fog;
    mode_ = game_mode_ == sim::FogMode::Revealed ? sim::FogMode::Dynamic : game_mode_;
    group_ = group;
    // Unique across views, so a new game is never mistaken for the last.
    static std::uint32_t next_generation = 0;
    generation_ = ++next_generation;
    side_ = game.fog() ? game.vision().side() : 0;
    tick_ = ~0ull;
    ceiling_.clear();
    ceiling_side_ = 0;
    explored_count_ = 0;
    rows_[0] = last_rows_[0] = 0;
    rows_[1] = last_rows_[1] = -1;
    pending_.clear();
    visible_.reset(side_);
    previous_.reset(side_);
    explored_.reset(side_);
    texels_.assign(static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_), kHidden);
    tiles_ = (side_ + kTile - 1) / kTile;
    dirty_.assign(static_cast<std::size_t>(tiles_) * static_cast<std::size_t>(tiles_), 0);
    ++revision_;
    if (side_ == 0) {
        return;
    }
    // The ceiling covers the same meters as the texels (map sizes are
    // multiples of 64 m, so of the ceiling's cells too).
    ceiling_side_ = side_ * sim::kFogCell / kCeilingCell;
    ceiling_ = fog_ceiling(game.map(), ceiling_side_);
    // Everything once, then only what changes.
    explored_ = game.vision().explored(group_);
    explored_count_ = game.vision().count(group_);
    if (game.vision().all_explored()) {
        for (std::int32_t cz = 0; cz < side_; ++cz) {
            explored_.set_span(cz, 0, side_ - 1);
        }
    }
    update(game);
    mark_all();
    refresh_tiles();
    pending_.clear();  // The caller sends the whole texture at first.
}

void FogView::set_revealed(bool revealed) {
    if (revealed != revealed_) {
        revealed_ = revealed;
        ++revision_;
    }
}

void FogView::set_watch_all(bool all) {
    if (all != watch_all_) {
        watch_all_ = all;
        ++revision_;
    }
}

void FogView::stamp(std::int32_t x, std::int32_t z, std::int32_t radius) {
    sim::for_each_disc_row(side_, x, z, radius, [&](std::int32_t cz, std::int32_t cx0, std::int32_t cx1) {
        visible_.set_span(cz, cx0, cx1);
        rows_[0] = std::min(rows_[0], cz);
        rows_[1] = std::max(rows_[1], cz);
    });
}

void FogView::mark_word(std::size_t word, std::uint64_t changed) {
    while (changed != 0) {
        const std::size_t cell = (word << 6) | static_cast<std::size_t>(std::countr_zero(changed));
        changed &= changed - 1;
        const auto cx = static_cast<std::int32_t>(cell % static_cast<std::size_t>(side_));
        const auto cz = static_cast<std::int32_t>(cell / static_cast<std::size_t>(side_));
        if (cz >= side_) {
            continue;
        }
        dirty_[static_cast<std::size_t>(cz / kTile) * static_cast<std::size_t>(tiles_) + static_cast<std::size_t>(cx / kTile)] = 1;
        any_dirty_ = true;
    }
}

void FogView::mark_all() {
    std::fill(dirty_.begin(), dirty_.end(), std::uint8_t{1});
    any_dirty_ = !dirty_.empty();
}

void FogView::update(const sim::Game& game) {
    // By turns, not ticks: a town founded while the game still waits for
    // the others (phase 74) must show its surroundings.
    if (side_ == 0 || game.turn() == tick_) {
        return;
    }
    tick_ = game.turn();
    // What was in sight is only in the rows stamped last time.
    std::vector<std::uint64_t>& now = visible_.words();
    std::vector<std::uint64_t>& before = previous_.words();
    {
        const auto [b, e] = row_words(side_, last_rows_[0], last_rows_[1]);
        std::fill(now.begin() + static_cast<std::ptrdiff_t>(b), now.begin() + static_cast<std::ptrdiff_t>(e), 0ull);
    }
    rows_[0] = side_;
    rows_[1] = -1;
    for (const sim::Building& b : game.buildings().data()) {
        if (game.town_group(b.owner) == group_) {
            stamp(b.x + b.width / 2, b.z + b.depth / 2, game.sight(b));
        }
    }
    for (const sim::Villager& v : game.villagers().data()) {
        if (game.town_group(v.owner) == group_) {
            stamp(v.position.x.floor_int(), v.position.z.floor_int(), game.sight(v));
        }
    }
    for (const sim::Creature& a : game.creatures().data()) {
        const std::int32_t r = game.sight(a);
        if (r > 0 && game.town_group(a.town) == group_) {
            stamp(a.position.x.floor_int(), a.position.z.floor_int(), r);
        }
    }
    // Compare over the rows stamped now or last time, then remember.
    const std::int32_t first = std::min(rows_[0], last_rows_[0]);
    const std::int32_t last = std::max(rows_[1], last_rows_[1]);
    {
        const auto [b, e] = row_words(side_, first, last);
        for (std::size_t k = b; k < e; ++k) {
            if (now[k] != before[k]) {
                mark_word(k, now[k] ^ before[k]);
                before[k] = now[k];
            }
        }
    }
    last_rows_[0] = rows_[0];
    last_rows_[1] = rows_[1];
    // Newly explored cells (the game reveals them once a second).
    const sim::FogGrid& game_explored = game.vision().explored(group_);
    if (game.vision().count(group_) != explored_count_ && game_explored.side() == side_) {
        explored_count_ = game.vision().count(group_);
        std::vector<std::uint64_t>& mine = explored_.words();
        const std::vector<std::uint64_t>& theirs = game_explored.words();
        for (std::size_t k = 0; k < mine.size(); ++k) {
            if (mine[k] != theirs[k]) {
                mark_word(k, mine[k] ^ theirs[k]);
                mine[k] = theirs[k];
            }
        }
    }
    refresh_tiles();
}

void FogView::refresh_tiles() {
    if (!any_dirty_) {
        return;
    }
    any_dirty_ = false;
    ++revision_;
    for (std::int32_t tz = 0; tz < tiles_; ++tz) {
        for (std::int32_t tx = 0; tx < tiles_; ++tx) {
            std::uint8_t& flag = dirty_[static_cast<std::size_t>(tz) * static_cast<std::size_t>(tiles_) + static_cast<std::size_t>(tx)];
            if (flag == 0) {
                continue;
            }
            flag = 0;
            const Rect r{tx * kTile, tz * kTile, std::min(kTile, side_ - tx * kTile), std::min(kTile, side_ - tz * kTile)};
            for (std::int32_t cz = r.z; cz < r.z + r.d; ++cz) {
                std::uint8_t* row = texels_.data() + static_cast<std::size_t>(cz) * static_cast<std::size_t>(side_);
                for (std::int32_t cx = r.x; cx < r.x + r.w; ++cx) {
                    std::uint8_t t = kHidden;
                    if (cell_in_sight(cx, cz)) {
                        t = kInSight;
                    } else if (explored_.get(cx, cz)) {
                        t = mode_ == sim::FogMode::Dynamic ? kExplored : kInSight;
                    }
                    row[cx] = t;
                }
            }
            pending_.push_back(r);
        }
    }
}

std::vector<FogView::Rect> FogView::take_dirty() {
    std::vector<Rect> out;
    out.swap(pending_);
    return out;
}

bool FogView::in_sight(float x, float z) const {
    if (mode() == sim::FogMode::None) {
        return true;
    }
    return cell_in_sight(cell_of(x), cell_of(z));
}

bool FogView::explored(float x, float z) const {
    if (mode() == sim::FogMode::None) {
        return true;
    }
    return cell_explored(cell_of(x), cell_of(z));
}

bool FogView::shows(float x, float z) const {
    switch (mode()) {
        case sim::FogMode::Static: return explored(x, z);
        case sim::FogMode::Dynamic: return in_sight(x, z);
        default: return true;
    }
}

bool FogView::rect_in_sight(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const {
    if (mode() == sim::FogMode::None) {
        return true;
    }
    for (std::int32_t cz = z / sim::kFogCell; cz <= (z + std::max(1, d) - 1) / sim::kFogCell; ++cz) {
        for (std::int32_t cx = x / sim::kFogCell; cx <= (x + std::max(1, w) - 1) / sim::kFogCell; ++cx) {
            if (cell_in_sight(cx, cz)) {
                return true;
            }
        }
    }
    return false;
}

bool FogView::rect_unexplored(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const {
    if (mode() == sim::FogMode::None) {
        return false;
    }
    for (std::int32_t cz = z / sim::kFogCell; cz <= (z + std::max(1, d) - 1) / sim::kFogCell; ++cz) {
        for (std::int32_t cx = x / sim::kFogCell; cx <= (x + std::max(1, w) - 1) / sim::kFogCell; ++cx) {
            if (cell_explored(cx, cz)) {
                return false;
            }
        }
    }
    return true;
}

float FogView::ceiling_at(float x, float z) const {
    if (ceiling_side_ <= 0) {
        return 0.0f;
    }
    // Bilinear between cell centers, as the GPU samples it.
    const float fx = std::clamp(x / static_cast<float>(kCeilingCell) - 0.5f, 0.0f, static_cast<float>(ceiling_side_ - 1));
    const float fz = std::clamp(z / static_cast<float>(kCeilingCell) - 0.5f, 0.0f, static_cast<float>(ceiling_side_ - 1));
    const auto x0 = static_cast<std::int32_t>(fx);
    const auto z0 = static_cast<std::int32_t>(fz);
    const std::int32_t x1 = std::min(x0 + 1, ceiling_side_ - 1);
    const std::int32_t z1 = std::min(z0 + 1, ceiling_side_ - 1);
    const float tx = fx - static_cast<float>(x0);
    const float tz = fz - static_cast<float>(z0);
    const auto at = [&](std::int32_t cx, std::int32_t cz) {
        return static_cast<float>(ceiling_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(ceiling_side_) +
                                           static_cast<std::size_t>(cx)]);
    };
    const float top = at(x0, z0) * (1 - tx) * (1 - tz) + at(x1, z0) * tx * (1 - tz) + at(x0, z1) * (1 - tx) * tz +
                      at(x1, z1) * tx * tz;
    return top * 0.01f;
}

bool FogView::rect_shows(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const {
    switch (mode()) {
        case sim::FogMode::Static:
            for (std::int32_t cz = z / sim::kFogCell; cz <= (z + std::max(1, d) - 1) / sim::kFogCell; ++cz) {
                for (std::int32_t cx = x / sim::kFogCell; cx <= (x + std::max(1, w) - 1) / sim::kFogCell; ++cx) {
                    if (cell_explored(cx, cz)) {
                        return true;
                    }
                }
            }
            return false;
        case sim::FogMode::Dynamic: return rect_in_sight(x, z, w, d);
        default: return true;
    }
}

}  // namespace sc
