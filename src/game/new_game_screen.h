// "New game" screen: the map settings (seed, size, water, forests,
// resources, relief and players) before generating the map.
#pragma once

#include <cstdint>
#include <string>

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

class NewGameScreen {
public:
    enum class Result : std::uint8_t { None, Back, Generate };

    // Resets the form with a fresh random seed; map types and biomes come
    // from `content`, which must outlive the screen's use.
    void open(const sim::Content* content);
    Result frame(ui::Context& ctx, bool modal);

    // Valid once frame() returned Generate.
    [[nodiscard]] const sim::MapSettings& settings() const { return settings_; }

private:
    void seed_field(ui::Context& ctx, const ui::Rect& r, bool modal);

    const sim::Content* content_ = nullptr;
    sim::MapSettings settings_;
    std::string seed_text_;
    bool seed_focused_ = false;
};

}  // namespace sc
