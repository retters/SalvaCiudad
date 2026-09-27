// "New game" screen: the map settings (seed, size, water, forests,
// resources, relief and players) before generating the map.
#pragma once

#include <cstdint>
#include <string>

#include "sim/climate.h"
#include "sim/content.h"
#include "sim/map.h"
#include "ui/context.h"

namespace sc {

// Seeds are typed as decimal digits; at most this many.
inline constexpr std::size_t kMaxSeedDigits = 19;

// The seed from its text, or 0 if the text is empty or not only digits.
[[nodiscard]] std::uint64_t parse_seed(std::string_view text);
// A new random seed (from the clock), 1 .. 999 999 999.
[[nodiscard]] std::uint64_t random_seed();
// Text key of a map size's name ("{0} m" takes its side).
[[nodiscard]] const char* map_size_text_key(sim::MapSize size);

class NewGameScreen {
public:
    enum class Result : std::uint8_t { None, Back, Generate };

    // Resets the form with a fresh random seed; map types and biomes come
    // from `content`, which must outlive the screen's use.
    // `multiplayer`: the map of a network game; the button opens the lobby.
    void open(const sim::Content* content, bool multiplayer = false);
    Result frame(ui::Context& ctx, bool modal);

    // Valid once frame() returned Generate.
    [[nodiscard]] const sim::MapSettings& settings() const { return settings_; }
    // The rules chosen with the map: climate, starting goods, population.
    [[nodiscard]] const sim::GameRules& rules() const { return rules_; }

private:
    void seed_field(ui::Context& ctx, const ui::Rect& r, bool modal);

    const sim::Content* content_ = nullptr;
    sim::MapSettings settings_;
    sim::GameRules rules_;
    void rules_rows(ui::Context& ctx, float x, float& y, float cw);
    std::string seed_text_;
    bool multiplayer_ = false;
    bool seed_focused_ = false;
};

}  // namespace sc
