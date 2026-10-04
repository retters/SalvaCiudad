// "New game" screen (phase 56): the size, the players and the seed, and a
// kind of map. "Varied" has nothing else to choose: the seed decides the
// climate and the sea, and the rest is the usual. "Custom" has every
// choice: check boxes, sliders and lists. A small picture of the map is
// made again whenever a choice changes.
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include "game/settings.h"
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

// The climates a varied map may get; the last one goes from cold to warm.
enum class VariedClimate : std::uint8_t { Cold, Temperate, Warm, Mixed, Count };
// What "Varied" gives for a seed: the climate and the sea come from the
// seed, everything else is the usual. The same seed, the same choices.
[[nodiscard]] VariedClimate varied_climate(std::uint64_t seed);
[[nodiscard]] sim::MapSettings varied_map(std::uint64_t seed, sim::MapSize size, int players);
// The rules of a varied game: the usual ones, with static fog.
[[nodiscard]] sim::GameRules varied_rules();

// The preview's image in the interface renderer (the minimap is 1), and
// the largest map it is made for: bigger ones take too long to make again
// at every change.
inline constexpr std::uint32_t kPreviewImageId = 2;
inline constexpr sim::MapSize kLargestPreview = sim::MapSize::Large;

class NewGameScreen {
public:
    enum class Result : std::uint8_t { None, Back, Generate };

    NewGameScreen() = default;
    ~NewGameScreen();
    NewGameScreen(const NewGameScreen&) = delete;
    NewGameScreen& operator=(const NewGameScreen&) = delete;

    // Fills the form with the last choices (`remembered`) and a fresh
    // random seed; biomes and races come from `content`, which must outlive
    // the screen's use. `multiplayer`: the map of a network game; the
    // button opens the lobby.
    void open(const sim::Content* content, bool multiplayer = false, const NewGameSettings& remembered = {});
    Result frame(ui::Context& ctx, bool modal);
    // The choices on the form, to remember them (phase 23).
    [[nodiscard]] NewGameSettings remembered() const;
    // Back to "Varied", with every custom choice at its usual value; the
    // seed stays.
    void reset();
    // Custom, with every choice as "Varied" has it for this seed.
    void start_from_varied();

    // The map and the rules as chosen (what Generate will make).
    [[nodiscard]] const sim::MapSettings& settings() const { return settings_; }
    [[nodiscard]] const sim::GameRules& rules() const { return rules_; }
    [[nodiscard]] bool custom() const { return custom_; }

    // The preview's picture when a new one is ready (RGBA, the minimap's
    // size), once; the caller hands it to the renderer as kPreviewImageId.
    [[nodiscard]] std::optional<std::vector<std::uint8_t>> take_preview();
    // Stops the preview's work (leaving the screen).
    void close();

private:
    void seed_field(ui::Context& ctx, const ui::Rect& r, bool modal);
    void apply(const NewGameSettings& n);
    // Fills settings_ and rules_ from the form.
    void resolve();
    void custom_rows(ui::Context& ctx, float x, float& y, float cw);
    void rules_rows(ui::Context& ctx, float x, float& y, float cw);
    void preview_panel(ui::Context& ctx, float x, float& y, float cw);
    void update_preview(std::uint64_t now_ns);
    [[nodiscard]] std::string summary() const;

    const sim::Content* content_ = nullptr;
    bool custom_ = false;
    // The custom choices (the seed, size and players are the form's own).
    sim::MapSettings map_;
    sim::GameRules game_;
    bool giants_on_ = true;
    int other_races_ = 100;  // Percent of the usual share.
    // Minutes of each season; those of the enabled ones make the year.
    std::array<int, 4> season_minutes_{5, 5, 5, 5};
    // Day and night: whether the game has them, and their minutes.
    bool day_night_on_ = true;
    int day_minutes_ = 5;
    int night_minutes_ = 5;
    // As resolved from the form.
    sim::MapSettings settings_;
    sim::GameRules rules_;
    std::string seed_text_;
    bool multiplayer_ = false;
    bool seed_focused_ = false;
    float last_height_ = 0.0f;

    // The preview: made in its own thread a moment after the last change.
    struct PreviewResult {
        std::vector<std::uint8_t> rgba;
        int giants = 0;
        std::uint8_t sea_sides = 0;  // Bit per side: north, south, west, east.
    };
    void stop_preview();
    std::thread worker_;
    std::atomic<bool> cancel_{false};
    std::atomic<bool> working_{false};
    std::mutex result_mutex_;
    std::optional<PreviewResult> result_;       // From the worker.
    std::optional<std::vector<std::uint8_t>> image_;  // For take_preview().
    std::optional<sim::MapSettings> wanted_;    // What the form shows now.
    std::optional<sim::MapSettings> shown_;     // What the picture is of.
    std::uint64_t changed_ns_ = 0;
    int shown_giants_ = 0;
    std::uint8_t shown_sea_sides_ = 0;
};

}  // namespace sc
