#include "game/ui_host.h"

#include "core/speed.h"

#include "game/minimap.h"

#include <algorithm>
#include <array>
#include <iterator>
#include <random>
#include <cmath>

#include "core/log.h"
#include "core/text.h"
#include "game/build_info.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr std::uint64_t kDisplayConfirmNs = 15'000'000'000ull;

constexpr std::uint32_t kLogoGlowImageId = 3;  // Next to minimap::kImageId and kPreviewImageId.
constexpr int kMaxGlowSize = 2048;             // UiRenderer::kMaxImageSize.

// One look of the logo (decisions D-RENAME-03 and D-RENAME-04). Sigmas are in name em; from
// the CSS proposals, a blur radius of r px at a 62 px name is a sigma of r / 2 / 62.
struct Glow {
    ui::Color color;
    float opacity = 0.0f;  // 0: none.
    float sigma = 0.0f;
};
struct LogoStyle {
    const char* name_key;  // Its name in the developer tools' toast.
    std::array<ui::TextRenderer::GradientStop, 5> metal;  // The name's vertical gradient.
    ui::Color shadow;      // The hard shadow just below the name.
    Glow inner;            // Close around the name.
    Glow outer;            // Wide, around the name and its inner glow, as chained CSS shadows.
    Glow backdrop;         // A dark cloud behind the whole logo.
    Glow small_glow;       // Around the small line, which is always ivory.
    ui::Color rule;        // In the name's metal.
};

constexpr float kEm = 1.0f / 124.0f;  // A CSS pixel of blur radius at a 62 px name, as a sigma in em.
constexpr ui::Color kIvory = ui::Color::rgb(0xF2E8D5);  // SALVA'S, in every style.

const LogoStyle kLogoStyles[] = {
    // G2: burnished gold with a lantern glow.
    {"logo.style.gold",
     {{{0.00f, ui::Color::rgb(0xFFF2C4)},
       {0.38f, ui::Color::rgb(0xF0C660)},
       {0.52f, ui::Color::rgb(0xB27D22)},
       {0.70f, ui::Color::rgb(0xE9B94F)},
       {1.00f, ui::Color::rgb(0x8A5B14)}}},
     ui::Color::rgb(0x3B2608),
     {ui::Color::rgb(0xFFBE46), 0.75f, 8 * kEm},
     {ui::Color::rgb(0xF08C14), 0.7f, 22 * kEm},
     {},
     {ui::Color::rgb(0xFFBE46), 0.8f, 8 * kEm},
     ui::Color::rgb(0xE9B94F)},
    // B (7 + 3): cold steel with a cold glow.
    {"logo.style.steel",
     {{{0.00f, ui::Color::rgb(0xD8E6EF)},
       {0.45f, ui::Color::rgb(0x8FB0C8)},
       {0.55f, ui::Color::rgb(0xE9F3F9)},
       {0.80f, ui::Color::rgb(0x9DB8CC)},
       {1.00f, ui::Color::rgb(0x6D8FA8)}}},
     ui::Color::rgb(0x14212B),
     {ui::Color::rgb(0xA0D2FF), 0.8f, 8 * kEm},
     {ui::Color::rgb(0x5AA0E6), 0.75f, 24 * kEm},
     {},
     {ui::Color::rgb(0xA0D2FF), 0.8f, 8 * kEm},
     ui::Color::rgb(0x9DB8CC)},
    // New: moonlit silver. Neutral, without the blue of the steel, under a pale white light.
    {"logo.style.silver",
     {{{0.00f, ui::Color::rgb(0xFFFFFF)},
       {0.42f, ui::Color::rgb(0xC9CDD1)},
       {0.54f, ui::Color::rgb(0x8C9296)},
       {0.72f, ui::Color::rgb(0xD5D8DB)},
       {1.00f, ui::Color::rgb(0x6E7377)}}},
     ui::Color::rgb(0x1A1C1E),
     {ui::Color::rgb(0xF4F6F8), 0.6f, 7 * kEm},
     {ui::Color::rgb(0xB8C0C8), 0.55f, 24 * kEm},
     {},
     {ui::Color::rgb(0xF4F6F8), 0.7f, 8 * kEm},
     ui::Color::rgb(0xC9CDD1)},
    // New: embers. Copper going red at the foot, with a deep orange-red glow.
    {"logo.style.ember",
     {{{0.00f, ui::Color::rgb(0xFFE6B8)},
       {0.35f, ui::Color::rgb(0xF2A65A)},
       {0.55f, ui::Color::rgb(0xB4532A)},
       {0.72f, ui::Color::rgb(0xE08A4A)},
       {1.00f, ui::Color::rgb(0x6E2A12)}}},
     ui::Color::rgb(0x2A0E05),
     {ui::Color::rgb(0xFF8A3C), 0.8f, 8 * kEm},
     {ui::Color::rgb(0xD2401E), 0.65f, 28 * kEm},
     {},
     {ui::Color::rgb(0xFFB070), 0.8f, 8 * kEm},
     ui::Color::rgb(0xE08A4A)},
    // New: pale champagne gold on a soft night cloud, which keeps it readable on any map.
    {"logo.style.night",
     {{{0.00f, ui::Color::rgb(0xFFF8E6)},
       {0.40f, ui::Color::rgb(0xEADBB0)},
       {0.55f, ui::Color::rgb(0xB89F6A)},
       {0.72f, ui::Color::rgb(0xDCC898)},
       {1.00f, ui::Color::rgb(0x7D6840)}}},
     ui::Color::rgb(0x1E1A10),
     {ui::Color::rgb(0xFFF4D6), 0.45f, 6 * kEm},
     {},
     {ui::Color::rgb(0x0B1218), 2.6f, 40 * kEm},
     {},
     ui::Color::rgb(0xDCC898)},
    // New: the same pale gold, with a pale gold glow in place of the night cloud.
    {"logo.style.paleGold",
     {{{0.00f, ui::Color::rgb(0xFFF8E6)},
       {0.40f, ui::Color::rgb(0xEADBB0)},
       {0.55f, ui::Color::rgb(0xB89F6A)},
       {0.72f, ui::Color::rgb(0xDCC898)},
       {1.00f, ui::Color::rgb(0x7D6840)}}},
     ui::Color::rgb(0x1E1A10),
     {ui::Color::rgb(0xF6E7BC), 0.75f, 8 * kEm},
     {ui::Color::rgb(0xD8C08A), 0.7f, 24 * kEm},
     {},
     {ui::Color::rgb(0xF6E7BC), 0.8f, 8 * kEm},
     ui::Color::rgb(0xDCC898)},
};
constexpr int kLogoStyleCount = static_cast<int>(std::size(kLogoStyles));

// A centered dialog panel; returns the content rectangle.
ui::Rect dialog_frame(ui::Context& ctx, float content_height, std::string_view title, float& y) {
    const float pad = ctx.s(24.0f);
    const float w = std::min(ctx.s(560.0f), ctx.width() - ctx.s(32.0f));
    const float title_h = ctx.text().line_height(ctx.style(ctx.theme().heading, ui::FontRole::Bold));
    const float h = std::min(ctx.height() - ctx.s(16.0f), content_height + title_h + 3 * pad);
    const ui::Rect box{std::round((ctx.width() - w) * 0.5f), std::round((ctx.height() - h) * 0.5f), std::round(w),
                       std::round(h)};
    ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().overlay);
    ctx.panel(box);
    ctx.label({box.x + pad, box.y + pad, box.w - 2 * pad, title_h}, title,
              ctx.style(ctx.theme().heading, ui::FontRole::Bold), ctx.theme().accent, ui::Align::Left);
    y = box.y + pad + title_h + pad * 0.5f;
    return {box.x + pad, y, box.w - 2 * pad, box.bottom() - pad - y};
}

}  // namespace

UiHost::UiHost(Services& services)
    : services_(services),
      settings_screen_(services),
      mods_screen_(services),
      hud_(services),
      join_(services),
      lobby_screen_(services),
      logo_random_(static_cast<std::uint64_t>(std::random_device{}()) << 32 ^ std::random_device{}()) {}

int pick_logo_style(int current, int count, std::uint64_t random) {
    if (count <= 1) {
        return 0;
    }
    if (current < 0 || current >= count) {
        return static_cast<int>(random % static_cast<std::uint64_t>(count));
    }
    // One of the others: skip over the current one.
    const int pick = static_cast<int>(random % static_cast<std::uint64_t>(count - 1));
    return pick >= current ? pick + 1 : pick;
}

void UiHost::show_message(std::string title, std::string body) {
    messages_.push_back({std::move(title), std::move(body)});
}

void UiHost::add_notice(std::string text) {
    notices_.push_back(std::move(text));
}

void UiHost::toast(std::string text) {
    toast_ = std::move(text);
    toast_since_ns_ = 0;
}

void UiHost::cycle_logo_style() {
    logo_style_ = (std::max(logo_style_, 0) + 1) % kLogoStyleCount;
    toast(tr("dev.logoStyle", std::to_string(logo_style_ + 1), std::to_string(kLogoStyleCount),
             tr(kLogoStyles[logo_style_].name_key)));
}

void UiHost::draw_toast(ui::Context& ctx) {
    constexpr std::uint64_t kToastNs = 3'000'000'000ull;
    if (toast_.empty()) {
        return;
    }
    if (toast_since_ns_ == 0) {
        toast_since_ns_ = ctx.now_ns();
    }
    if (ctx.now_ns() - toast_since_ns_ > kToastNs) {
        toast_.clear();
        return;
    }
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.width() - ctx.s(32.0f), ctx.text().measure(st, toast_) + ctx.s(40.0f));
    const float h = ctx.text().line_height(st) + ctx.s(16.0f);
    const ui::Rect r{std::round((ctx.width() - w) * 0.5f), std::round(ctx.s(60.0f)), std::round(w), std::round(h)};
    ctx.draw().rect(r, ctx.theme().tooltip.with_alpha(0.9f));
    ctx.draw().rect_outline(r, ctx.theme().accent, std::max(1.0f, std::round(ctx.s(1.0f))));
    ctx.label(r, toast_, st, ctx.theme().text, ui::Align::Center);
}

bool UiHost::wants_keyboard() const {
    return screen_ == Screen::Settings && settings_screen_.capturing_key();
}

UiHost::SceneMode UiHost::scene_mode() const {
    if (!services_.scene_available()) {
        return SceneMode::None;
    }
    // Settings and the load list opened from the game keep the map behind them.
    const bool over_map = screen_ == Screen::MapView ||
                          (screen_ == Screen::Settings && settings_return_ == Screen::MapView) ||
                          (screen_ == Screen::Load && load_return_ == Screen::MapView);
    if (over_map && services_.current_map() != nullptr) {
        return SceneMode::Map;
    }
    return SceneMode::MenuBackground;
}

bool UiHost::scene_paused() const {
    if (scene_mode() != SceneMode::Map) {
        return false;
    }
    // Only a menu over the game; a pause is just speed 0 (decision D-3320).
    return game_menu_open_ || screen_ == Screen::Settings || screen_ == Screen::Load;
}

bool UiHost::game_paused() const {
    const GameSession* s = services_.session();
    if (s == nullptr) {
        return true;
    }
    // A network game only stops when the players pause it.
    if (s->networked()) {
        return services_.game_speed() == 0;
    }
    return screen_ != Screen::MapView || game_menu_open_ || services_.game_speed() == 0;
}

void UiHost::follow_network() {
    net::NetSession* net = services_.net();
    if (net == nullptr) {
        if (screen_ == Screen::Lobby) {
            screen_ = Screen::MainMenu;
        }
        return;
    }
    // The host started: everybody builds the map; a game already running
    // is shown as soon as its state arrives.
    if (screen_ == Screen::Lobby && net->state() == net::NetSession::State::Loading) {
        screen_ = Screen::Generating;
    } else if ((screen_ == Screen::Lobby || screen_ == Screen::Generating) && services_.session() != nullptr &&
               net->state() == net::NetSession::State::Playing) {
        screen_ = Screen::MapView;
        game_menu_open_ = false;
    }
}

bool UiHost::modal_open() const {
    return !messages_.empty() || pending_display_.has_value();
}

void UiHost::change_display(const DisplaySettings& wanted) {
    DisplaySettings& current = services_.settings().display;
    const DisplaySettings previous = pending_display_ ? pending_display_->previous : current;
    if (!services_.apply_display(wanted)) {
        show_message(tr("dialog.displayFailed.title"), tr("dialog.displayFailed.body"));
        return;
    }
    current = wanted;
    services_.settings_changed();
    // Nothing risky changed if the result equals where we started.
    if (wanted.mode == previous.mode && wanted.monitor == previous.monitor &&
        wanted.fullscreen_width == previous.fullscreen_width &&
        wanted.fullscreen_height == previous.fullscreen_height) {
        pending_display_.reset();
        return;
    }
    // The countdown starts on the first frame drawn in the new mode.
    pending_display_ = PendingDisplay{previous, 0, false};
}

void UiHost::frame(ui::Context& ctx) {
    const bool modal = modal_open();
    if (services_.session() == nullptr) {
        hud_.hide_rml();  // The HUD's RmlUi parts are for a game.
    }
    // Behind the menus, the 3D scene shows through a dark veil.
    const SceneMode mode = scene_mode();
    if (mode == SceneMode::None) {
        ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().background);
    } else if (mode == SceneMode::MenuBackground) {
        ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().background.with_alpha(0.55f));
    } else if (scene_paused()) {
        ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().background.with_alpha(0.45f));
    }

    follow_network();
    if (screen_ == Screen::MainMenu && (!last_screen_ || *last_screen_ == Screen::MapView || logo_style_ < 0)) {
        // splitmix64: one step per pick.
        logo_random_ += 0x9E3779B97F4A7C15ull;
        std::uint64_t z = logo_random_;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
        logo_style_ = pick_logo_style(logo_style_, kLogoStyleCount, z ^ (z >> 31));
        log::info("menu: logo style {}", logo_style_ + 1);
    }
    last_screen_ = screen_;
    if (screen_ == Screen::NewGame) {
        ctx.set_input_blocked(modal);
        const NewGameScreen::Result r = new_game_.frame(ctx, modal);
        // The preview's picture, when a new one is ready (phase 56).
        if (std::optional<std::vector<std::uint8_t>> image = new_game_.take_preview()) {
            services_.set_ui_image(kPreviewImageId, minimap::kImageSize, minimap::kImageSize, std::move(*image));
        }
        // The form is remembered however it is left (phase 23).
        if (r != NewGameScreen::Result::None && services_.settings().new_game != new_game_.remembered()) {
            services_.settings().new_game = new_game_.remembered();
            services_.settings_changed();
        }
        if (r == NewGameScreen::Result::Back) {
            screen_ = Screen::MainMenu;
            host_new_game_ = false;
        } else if (r == NewGameScreen::Result::Generate && host_new_game_) {
            host_new_game_ = false;
            if (services_.host_game(new_game_.settings(), new_game_.rules())) {
                lobby_screen_.open();
                screen_ = Screen::Lobby;
            } else {
                show_message(tr("lobby.hostFailed.title"), tr("lobby.hostFailed.body"));
            }
        } else if (r == NewGameScreen::Result::Generate) {
            services_.start_map_generation(new_game_.settings(), new_game_.rules());
            screen_ = Screen::Generating;
        }
    } else if (screen_ == Screen::Join) {
        ctx.set_input_blocked(modal);
        const JoinScreen::Result r = join_.frame(ctx, modal);
        if (r == JoinScreen::Result::Back) {
            screen_ = Screen::MainMenu;
        } else if (r == JoinScreen::Result::Joining) {
            lobby_screen_.open();
            screen_ = Screen::Lobby;
        }
    } else if (screen_ == Screen::Lobby) {
        ctx.set_input_blocked(modal);
        if (lobby_screen_.frame(ctx, modal) == LobbyScreen::Result::Leave) {
            services_.leave_network();
            screen_ = Screen::MainMenu;
        }
    } else if (screen_ == Screen::Generating) {
        ctx.set_input_blocked(modal);
        generating_screen(ctx, modal);
    } else if (screen_ == Screen::MapView) {
        ctx.set_input_blocked(modal);
        map_hud(ctx);
        if (screen_ != Screen::MapView) {
            tutorial_.reset();
        }
    } else if (screen_ == Screen::Load) {
        ctx.set_input_blocked(modal);
        load_screen(ctx, modal);
    } else if (screen_ == Screen::Mods) {
        if (!mods_screen_.frame(ctx, modal)) {
            screen_ = Screen::MainMenu;
        }
    } else if (screen_ == Screen::Settings) {
        if (!settings_screen_.frame(ctx, *this, modal)) {
            screen_ = settings_return_ == Screen::MapView && services_.current_map() != nullptr ? Screen::MapView
                                                                                                : Screen::MainMenu;
        }
    } else {
        ctx.set_input_blocked(modal);
        main_menu(ctx);
    }

    ctx.set_input_blocked(false);
    draw_toast(ctx);
    if (pending_display_) {
        display_confirm_dialog(ctx);
    } else if (!messages_.empty()) {
        message_dialog(ctx);
    }
}

void UiHost::draw_logo(ui::Context& ctx, float center_x, float y, float max_width, float max_height, float& height_out,
                       bool draw) {
    // The identity of SALVA'S PROSPERIA (decision D-RENAME-02): a small tracked line over the name,
    // the name in burnished gold with a warm glow, and a thin silver rule below. Every measure is a
    // fraction of the name's size, as on the identity slide.
    constexpr float kCapHeight = 0.65f;    // EB Garamond capitals, in em.
    constexpr float kSmallSize = 0.1515f;  // The small line, 10/66 of the name.
    constexpr float kTracking = 0.3f;      // Between its letters, in its own em.
    constexpr float kGap = 0.12f;          // From its baseline to the capitals, in name em.
    constexpr float kRuleDrop = 0.2f;      // From the name's baseline to the rule.
    constexpr float kRuleThick = 0.014f;

    const std::string small = tr("app.logo.top");
    const std::string name = tr("app.logo.bottom");

    // Shrink until the logo fits both the width and its share of the height.
    float size = 112.0f;
    ui::TextStyle small_style;
    ui::TextStyle name_style;
    float small_w = 0.0f;
    float name_w = 0.0f;
    float tracking = 0.0f;
    float block_h = 0.0f;
    std::vector<std::string_view> letters;
    for (int attempt = 0; attempt < 16; ++attempt) {
        const float px = ctx.s(size);
        name_style = ctx.style(static_cast<int>(px), ui::FontRole::Logo);
        small_style = ctx.style(std::max(9, static_cast<int>(px * kSmallSize)), ui::FontRole::LogoSmall);
        tracking = static_cast<float>(small_style.px) * kTracking;
        letters.clear();
        small_w = 0.0f;
        for (std::size_t i = 0; i < small.size();) {
            std::size_t next = i;
            (void)text::next_codepoint(small, next);
            letters.push_back(std::string_view(small).substr(i, next - i));
            small_w += ctx.text().measure(small_style, letters.back());
            i = next;
        }
        small_w += tracking * static_cast<float>(letters.size() > 1 ? letters.size() - 1 : 0);
        name_w = ctx.text().measure(name_style, name);
        block_h = ctx.text().ascent(small_style) + px * (kGap + kCapHeight + kRuleDrop + kRuleThick);
        if (std::max(small_w, name_w) <= max_width && block_h <= max_height) {
            break;
        }
        size *= 0.88f;
    }
    height_out = block_h;
    if (!draw) {
        return;
    }
    const float px = static_cast<float>(name_style.px);
    const float small_baseline = y + ctx.text().ascent(small_style);
    const float cap_top = small_baseline + px * kGap;
    const float baseline = cap_top + px * kCapHeight;
    const float name_x = std::round(center_x - name_w * 0.5f);
    const float name_y = baseline - ctx.text().ascent(name_style);
    const float rule_y = std::round(baseline + px * kRuleDrop);
    const float rule_h = std::max(1.0f, std::round(px * kRuleThick));
    ui::DrawList& list = ctx.draw();
    ui::TextRenderer& text = ctx.text();

    // The glows and the rule are one blurred image (see ui/glow.h), placed on whole pixels so
    // it lines up with the letters. It is built again only when the layout or the style
    // changes, with room for the widest glow to fade out completely before the image's edge.
    const int style_index = std::max(logo_style_, 0);
    const LogoStyle& style = kLogoStyles[style_index];
    const float widest = std::max({style.inner.sigma + style.outer.sigma, style.backdrop.sigma, style.small_glow.sigma});
    const int pad = static_cast<int>(std::ceil(px * widest * 3.5f)) + 2;
    const int origin_x = static_cast<int>(std::floor(center_x - std::max(small_w, name_w) * 0.5f)) - pad;
    const int origin_y = static_cast<int>(std::floor(y)) - pad;
    const auto frac = [](float v) { return static_cast<int>(std::lround((v - std::floor(v)) * 64.0f)); };
    LogoGlowKey key{style_index, name_style.px, small_style.px, frac(center_x), frac(y), small, name};
    if (logo_glow_key_ != key) {
        logo_glow_key_ = key;
        const LogoGlowLayout layout{name_style, small_style, &letters, name, tracking, small_w, name_w, block_h, pad,
                                    center_x - static_cast<float>(origin_x), y - static_cast<float>(origin_y),
                                    name_x - static_cast<float>(origin_x), name_y - static_cast<float>(origin_y),
                                    rule_y - static_cast<float>(origin_y), rule_h};
        logo_glow_ = build_logo_glow(text, layout, style_index);
        if (logo_glow_.w > 0) {
            services_.set_ui_image(kLogoGlowImageId, logo_glow_.w, logo_glow_.h, std::move(logo_glow_.rgba));
        }
        logo_glow_.rgba = {};
    }
    if (logo_glow_.w > 0) {
        list.picture({static_cast<float>(origin_x), static_cast<float>(origin_y), static_cast<float>(logo_glow_.w),
                      static_cast<float>(logo_glow_.h)},
                     kLogoGlowImageId, 0.0f, 0.0f, 1.0f, 1.0f, ui::Color::rgb(0xFFFFFF));
    }

    // The small line, letter by letter with its tracking.
    float pen = center_x - small_w * 0.5f;
    for (const std::string_view letter : letters) {
        pen += text.draw(list, small_style, std::round(pen), y, letter, kIvory) + tracking;
    }

    // The name: a hard dark shadow just below, then the metal.
    text.draw(list, name_style, name_x, name_y + px * 0.032f, name, style.shadow);
    const std::vector<ui::TextRenderer::GradientStop> metal(style.metal.begin(), style.metal.end());
    text.draw_gradient(list, name_style, name_x, name_y, name, metal, cap_top, px * kCapHeight);
}

UiHost::LogoGlow UiHost::build_logo_glow(const ui::TextRenderer& text, const LogoGlowLayout& l, int style_index) {
    const LogoStyle& style = kLogoStyles[style_index];
    const float px = static_cast<float>(l.name_style.px);
    LogoGlow glow;
    glow.w = static_cast<int>(std::ceil(std::max(l.small_w, l.name_w))) + 2 * l.pad + 2;
    glow.h = static_cast<int>(std::ceil(l.block_h + px * 0.1f)) + 2 * l.pad + 2;
    if (glow.w > kMaxGlowSize || glow.h > kMaxGlowSize) {
        glow.w = glow.h = 0;  // Larger than the renderer takes: letters without glow.
        return glow;
    }

    ui::AlphaMask small_mask;
    small_mask.resize(glow.w, glow.h);
    float pen = l.center_x - l.small_w * 0.5f;
    for (const std::string_view letter : *l.letters) {
        pen += text.rasterize(l.small_style, std::round(pen), l.small_y, letter, small_mask) + l.tracking;
    }
    ui::AlphaMask name_mask;
    name_mask.resize(glow.w, glow.h);
    text.rasterize(l.name_style, l.name_x, l.name_y, l.name, name_mask);

    const auto blurred = [px](ui::AlphaMask mask, float sigma_em) {
        ui::gaussian_blur(mask, px * sigma_em);
        return mask;
    };
    ui::GlowCanvas canvas(glow.w, glow.h);
    if (style.backdrop.opacity > 0.0f) {
        ui::AlphaMask both = name_mask;
        for (std::size_t i = 0; i < both.a.size(); ++i) {
            both.a[i] = std::max(both.a[i], small_mask.a[i]);
        }
        canvas.over(blurred(std::move(both), style.backdrop.sigma), style.backdrop.color, style.backdrop.opacity);
    }
    // The wide glow comes from the letters together with the close one, as chained CSS shadows do.
    const ui::AlphaMask inner = blurred(name_mask, style.inner.sigma);
    if (style.outer.opacity > 0.0f) {
        ui::AlphaMask base = name_mask;
        for (std::size_t i = 0; i < base.a.size(); ++i) {
            base.a[i] = std::max(base.a[i], inner.a[i] * style.inner.opacity);
        }
        canvas.over(blurred(std::move(base), style.outer.sigma), style.outer.color, style.outer.opacity);
    }
    if (style.inner.opacity > 0.0f) {
        canvas.over(inner, style.inner.color, style.inner.opacity);
    }
    // A soft dark bed under the thin small letters keeps them readable over the menu scene.
    ui::AlphaMask bed = small_mask;
    ui::gaussian_blur(bed, std::max(0.8f, static_cast<float>(l.small_style.px) * 0.12f));
    canvas.over(bed, ui::Color::rgb(0x0E1A24), 1.6f);
    if (style.small_glow.opacity > 0.0f) {
        canvas.over(blurred(small_mask, style.small_glow.sigma), style.small_glow.color, style.small_glow.opacity);
    }
    canvas.faded_line(static_cast<int>(l.name_x), static_cast<int>(l.rule_y), static_cast<int>(std::round(l.name_w)),
                      static_cast<int>(l.rule_h), style.rule);
    glow.rgba = canvas.to_rgba8();
    return glow;
}

void UiHost::main_menu(ui::Context& ctx) {
    const float margin = ctx.s(16.0f);
    const float col_w = std::min(ctx.s(380.0f), ctx.width() - 2 * margin);
    const float cx = ctx.width() * 0.5f;
    const float button_h = ctx.s(48.0f);
    const float gap = ctx.s(10.0f);

    struct Entry {
        const char* id;
        std::string label;
        std::string tooltip;
        bool available;
    };
    const Entry entries[] = {
        {"single", tr("menu.main.singlePlayer"), tr("menu.main.singlePlayer.tooltip"), true},
        {"tutorial", tr("menu.main.tutorial"), tr("menu.main.tutorial.tooltip"),
         services_.content() != nullptr && !services_.content()->tutorials.empty()},
        {"host", tr("menu.main.hostGame"), tr("menu.main.hostGame.tooltip"), true},
        {"join", tr("menu.main.joinGame"), tr("menu.main.joinGame.tooltip"), true},
        {"load", tr("menu.main.loadGame"), tr("menu.main.loadGame.tooltip"), true},
        {"mods", tr("menu.main.mods"), tr("menu.main.mods.tooltip"), true},
        {"settings", tr("menu.main.settings"), tr("menu.main.settings.tooltip"), true},
        {"quit", tr("menu.main.quit"), tr("menu.main.quit.tooltip"), true},
    };

    // Measure first so the whole column can be centered or scrolled.
    // The logo takes at most a third of the window height.
    const float logo_max_h = std::max(ctx.s(40.0f), ctx.height() * 0.33f);
    float logo_h = 0.0f;
    draw_logo(ctx, cx, 0.0f, ctx.width() - 2 * margin, logo_max_h, logo_h, false);
    const ui::TextStyle notice_style = ctx.style(ctx.theme().body);
    float notices_h = 0.0f;
    for (const std::string& n : notices_) {
        notices_h += ctx.paragraph_height(col_w - ctx.s(64.0f), n, notice_style) + ctx.s(20.0f) + gap;
    }
    const float buttons_h = static_cast<float>(std::size(entries)) * (button_h + gap);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float version_h = ctx.text().line_height(small);
    const float content_h = notices_h + logo_h + ctx.s(36.0f) + buttons_h + margin * 2;
    // The version sits in the corner if there is room, otherwise below the
    // buttons, so it never covers them.
    const bool version_in_corner = content_h + 2 * version_h <= ctx.height();

    const ui::Rect viewport{0, 0, ctx.width(), ctx.height()};
    const float top = ctx.begin_scroll(ctx.id("main_menu"), viewport);
    float y = top + std::max(margin, (ctx.height() - content_h) * 0.5f + margin);

    // Notices, each with a close button.
    for (std::size_t i = 0; i < notices_.size();) {
        const float text_h = ctx.paragraph_height(col_w - ctx.s(64.0f), notices_[i], notice_style);
        const ui::Rect box{std::round(cx - col_w * 0.5f), std::round(y), std::round(col_w), std::round(text_h + ctx.s(20.0f))};
        ctx.draw().rect(box, ctx.theme().danger.with_alpha(0.35f));
        ctx.draw().rect_outline(box, ctx.theme().danger, std::max(1.0f, std::round(ctx.s(1.0f))));
        ctx.paragraph({box.x + ctx.s(10.0f), box.y + ctx.s(10.0f), box.w - ctx.s(64.0f), text_h}, notices_[i],
                      notice_style, ctx.theme().text);
        const float close = ctx.s(32.0f);
        ctx.push_id("notice");
        const bool closed = ctx.button(ctx.id(std::to_string(i)), {box.right() - close - ctx.s(8.0f), box.y + ctx.s(8.0f), close, close},
                                       "x", tr("menu.main.dismissNotice.tooltip"));
        ctx.pop_id();
        y += box.h + gap;
        if (closed) {
            notices_.erase(notices_.begin() + static_cast<std::ptrdiff_t>(i));
        } else {
            ++i;
        }
    }

    draw_logo(ctx, cx, y, ctx.width() - 2 * margin, logo_max_h, logo_h, true);
    y += logo_h + ctx.s(36.0f);

    for (const Entry& e : entries) {
        const ui::Rect r{std::round(cx - col_w * 0.5f), std::round(y), std::round(col_w), std::round(button_h)};
        if (ctx.button(ctx.id(e.id), r, e.label, e.tooltip)) {
            if (!e.available) {
                show_message(tr("dialog.comingSoon.title"), tr("dialog.comingSoon.body", e.label));
            } else if (std::string_view(e.id) == "load") {
                saves_ = services_.list_saves();
                load_return_ = Screen::MainMenu;
                screen_ = Screen::Load;
            } else if (std::string_view(e.id) == "mods") {
                mods_screen_.open();
                screen_ = Screen::Mods;
            } else if (std::string_view(e.id) == "tutorial") {
                start_tutorial(0);
            } else if (std::string_view(e.id) == "single") {
                new_game_.open(services_.content(), false, services_.settings().new_game);
                host_new_game_ = false;
                screen_ = Screen::NewGame;
            } else if (std::string_view(e.id) == "host") {
                new_game_.open(services_.content(), true, services_.settings().new_game);
                host_new_game_ = true;
                screen_ = Screen::NewGame;
            } else if (std::string_view(e.id) == "join") {
                join_.open();
                screen_ = Screen::Join;
            } else if (std::string_view(e.id) == "settings") {
                open_settings();
            } else if (std::string_view(e.id) == "quit") {
                services_.request_quit();
            }
        }
        y += button_h + gap;
    }
    const std::string version = tr("menu.main.version", std::string(full_version()));
    if (!version_in_corner) {
        ctx.label({margin, y, ctx.width() - 2 * margin, version_h}, version, small, ctx.theme().text_dim,
                  ui::Align::Center);
    }
    ctx.end_scroll(content_h + (version_in_corner ? 0.0f : version_h + margin));

    if (version_in_corner) {
        ctx.label({margin, ctx.height() - margin - version_h, ctx.width() - 2 * margin, version_h}, version, small,
                  ctx.theme().text_dim, ui::Align::Right);
    }
}

// The camera line names the current mode and the key that changes it.
std::string UiHost::camera_line() const {
    const char* mode_key = "camera.mode.aerial";
    if (services_.camera_mode() == CameraMode::ThirdPerson) {
        mode_key = "camera.mode.thirdPerson";
    } else if (services_.camera_mode() == CameraMode::FirstPerson) {
        mode_key = "camera.mode.firstPerson";
    }
    const std::string key = key_display_name(services_.settings().input.bindings.key(Action::CameraCycleMode, 0));
    return tr("camera.line", tr(mode_key), key);
}

void UiHost::generating_screen(ui::Context& ctx, bool modal) {
    const MapGenStatus status = services_.map_generation_status();
    if (status.state == MapGenStatus::State::Done) {
        if (services_.enter_generated_map()) {
            screen_ = Screen::MapView;
            game_menu_open_ = false;
            last_speed_ = speed::kNormal;
        } else {
            show_message(tr("generating.showFailed.title"), tr("generating.showFailed.body"));
            screen_ = Screen::NewGame;
        }
        return;
    }
    if (status.state != MapGenStatus::State::Running) {
        if (services_.net() != nullptr) {
            return;  // The network game shows once its state is ready.
        }
        screen_ = Screen::NewGame;
        return;
    }

    static constexpr const char* kStepKeys[kMapGenSteps] = {
        "generating.step.relief",  "generating.step.lakes",     "generating.step.rivers",
        "generating.step.soil",    "generating.step.biomes",    "generating.step.forests",
        "generating.step.resources", "generating.step.starts",  "generating.step.view"};
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float bar_h = ctx.s(18.0f);
    const float button_h = ctx.s(44.0f);
    const float line_h = ctx.text().line_height(body);
    float y = 0.0f;
    const ui::Rect content =
        dialog_frame(ctx, line_h + ctx.s(12.0f) + bar_h + ctx.s(24.0f) + button_h, tr("generating.title"), y);
    const int step = std::clamp(status.step, 0, kMapGenSteps - 1);
    const float overall = status.overall();
    const std::string percent = tr("generating.percent", static_cast<int>(std::lround(overall * 100.0f)));
    ctx.label({content.x, y, content.w, line_h}, tr(kStepKeys[step]), body, ctx.theme().text);
    ctx.label({content.x, y, content.w, line_h}, percent, body, ctx.theme().text_dim, ui::Align::Right);
    y += line_h + ctx.s(12.0f);
    const ui::Rect bar{content.x, std::round(y), content.w, std::round(bar_h)};
    ctx.draw().rect(bar, ctx.theme().button_active);
    ctx.draw().rect({bar.x, bar.y, std::round(bar.w * overall), bar.h}, ctx.theme().accent);
    ctx.draw().rect_outline(bar, ctx.theme().panel_border, std::max(1.0f, std::round(ctx.s(1.0f))));
    const float bw = std::min(ctx.s(180.0f), content.w);
    const ui::Rect cancel{content.right() - bw, content.bottom() - button_h, bw, button_h};
    if (ctx.button(ctx.id("generating_cancel"), cancel, tr("generating.cancel"), tr("generating.cancel.tooltip")) ||
        (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE))) {
        services_.cancel_map_generation();
        if (services_.net() != nullptr) {
            services_.leave_network();
            screen_ = Screen::MainMenu;
        } else {
            screen_ = Screen::NewGame;
        }
    }
}

void UiHost::game_keys(ui::Context& ctx) {
    const KeyBindings& b = services_.settings().input.bindings;
    for (const SDL_Scancode k : ctx.input().keys) {
        if (b.matches(Action::GamePause, k)) {
            if (services_.game_speed() == 0) {
                services_.set_game_speed(last_speed_);
            } else {
                last_speed_ = services_.game_speed();
                services_.set_game_speed(0);
            }
        } else if (b.matches(Action::GameSpeed1, k)) {
            services_.set_game_speed(speed::kNormal);
        } else if (b.matches(Action::GameSpeed2, k)) {
            services_.set_game_speed(2 * speed::kNormal);
        } else if (b.matches(Action::GameSpeed3, k)) {
            services_.set_game_speed(3 * speed::kNormal);
        } else if (b.matches(Action::GameSpeedDown, k)) {
            // From a pause, the step under the speed it will go back to.
            const int now = services_.game_speed() > 0 ? services_.game_speed() : last_speed_;
            services_.set_game_speed(speed::slower(now));
        } else if (b.matches(Action::GameSpeedUp, k)) {
            const int now = services_.game_speed() > 0 ? services_.game_speed() : last_speed_;
            services_.set_game_speed(speed::faster(now, services_.max_game_speed()));
        } else if (b.matches(Action::GameQuickSave, k)) {
            services_.save_game();
        } else if (b.matches(Action::GameQuickLoad, k)) {
            const std::vector<save::Entry> saves = services_.list_saves();
            const auto it = std::find_if(saves.begin(), saves.end(), [](const save::Entry& e) { return e.readable; });
            if (it != saves.end()) {
                (void)services_.load_game(it->file);
            } else {
                show_message(tr("load.title"), tr("load.empty"));
            }
        }
    }
    if (services_.game_speed() > 0) {
        last_speed_ = services_.game_speed();
    }
}

void UiHost::map_hud(ui::Context& ctx) {
    if (leave_pending_) {
        leave_pending_ = false;
        services_.leave_map();
        services_.leave_network();
        screen_ = Screen::MainMenu;
        return;
    }
    const sim::MapData* map = services_.current_map();
    if (map == nullptr) {
        screen_ = Screen::MainMenu;
        return;
    }
    if (services_.session() != nullptr) {
        // Paused (speed 0) the interface still works: orders wait for the
        // game to move on and the camera goes anywhere (decision D-3320).
        if (!game_menu_open_ && !modal_open()) {
            game_keys(ctx);
        }
        ctx.set_input_blocked(modal_open() || game_menu_open_);
        if (tutorial_ && services_.content() != nullptr && tutorial_->def < services_.content()->tutorials.size()) {
            const sim::TutorialDef& t = services_.content()->tutorials[tutorial_->def];
            hud_.set_highlight(tutorial_->step < t.steps.size() ? t.steps[tutorial_->step].highlight : std::string());
        } else {
            hud_.set_highlight({});
        }
        const bool wants_menu = hud_.frame(ctx, modal_open() || game_menu_open_);
        if (tutorial_ && !game_menu_open_) {
            tutorial_panel(ctx);
        }
        ctx.set_input_blocked(modal_open());
        if (!services_.session()->game().game_over()) {
            end_seen_ = false;
        } else if (!end_seen_ && !game_menu_open_) {
            end_panel(ctx);
            return;
        }
        if (game_menu_open_) {
            game_menu(ctx);
        } else if (wants_menu && !modal_open()) {
            game_menu_open_ = true;
        }
        return;
    }
    const float pad = ctx.s(12.0f);
    const ui::TextStyle st = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.s(600.0f), ctx.width() - 2 * pad);
    static constexpr const char* kSizeKeys[] = {"newGame.size.small", "newGame.size.medium", "newGame.size.large",
                                                "newGame.size.huge"};
    const auto size_index = static_cast<std::size_t>(map->settings.size);
    const std::string size = tr(kSizeKeys[std::min<std::size_t>(size_index, 3)], map->size);
    const std::string text = tr("map.info", std::to_string(map->settings.seed), size) + "\n" + tr("map.hint") + "\n" +
                             camera_line();
    const float h = ctx.paragraph_height(w - 2 * pad, text, st);
    const ui::Rect box{pad, pad, w, h + 2 * pad};
    ctx.draw().rect(box, ctx.theme().tooltip.with_alpha(0.8f));
    ctx.paragraph(box.inset(pad), text, st, ctx.theme().text);
    if (game_menu_open_) {
        game_menu(ctx);
    } else if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
        game_menu_open_ = true;
    }
}

// Esc during a game: continue, settings, or leave. In phase 8 it will also
// pause a single-player game (decision D-616).
void UiHost::start_tutorial(std::size_t index) {
    const sim::Content* content = services_.content();
    if (content == nullptr || index >= content->tutorials.size()) {
        return;
    }
    const sim::TutorialDef& t = content->tutorials[index];
    sim::MapSettings map;
    map.seed = static_cast<std::uint64_t>(t.seed);
    map.size = static_cast<sim::MapSize>(t.size);
    map.players = 1;
    // A gentle start: no raiders, little danger.
    sim::GameRules rules;
    rules.raiders = sim::Threat::None;
    rules.wildlife = sim::Threat::Low;
    rules.diseases = sim::Threat::Low;
    rules.fires = sim::Threat::Low;
    tutorial_ = TutorialRun{};
    tutorial_->def = index;
    tutorial_lua_.reset();
    for (const sim::TutorialStep& step : t.steps) {
        if (step.goal == sim::TutorialGoal::Lua && !tutorial_lua_ && services_.mod_scripts() != nullptr) {
            tutorial_lua_ = std::make_unique<script::TutorialScript>();
            std::string error;
            if (!tutorial_lua_->open(*services_.mod_scripts(), t.mod, error)) {
                tutorial_->error = error;
                tutorial_lua_.reset();
            }
        }
    }
    services_.start_map_generation(map, rules, true);  // The tutorial's town stands from the start.
    screen_ = Screen::Generating;
}

bool UiHost::tutorial_step_done(const sim::TutorialStep& step, std::uint64_t now_ns) {
    GameSession* s = services_.session();
    if (s == nullptr) {
        return false;
    }
    const sim::Game& game = s->game();
    const sim::Content& content = game.content();
    const std::uint8_t town = s->town();
    const auto count = [&](bool complete_only) {
        const sim::DefIndex d = content.find_building(step.target);
        std::int32_t n = 0;
        for (const sim::Building& b : game.buildings().data()) {
            n += b.owner == town && b.def == d && (!complete_only || b.state == sim::BuildingState::Complete) ? 1 : 0;
        }
        return n;
    };
    switch (step.goal) {
        case sim::TutorialGoal::None: return false;
        case sim::TutorialGoal::Camera: {
            const std::array<float, 3> now = services_.camera_view();
            const std::array<float, 3>& was = tutorial_->camera;
            return std::abs(now[0] - was[0]) + std::abs(now[1] - was[1]) > 15.0f || std::abs(now[2] - was[2]) > 10.0f;
        }
        case sim::TutorialGoal::Place: return count(false) >= step.amount;
        case sim::TutorialGoal::Build: return count(true) >= step.amount;
        case sim::TutorialGoal::Workers:
            for (const sim::Building& b : game.buildings().data()) {
                if (b.owner == town && !b.workers.empty()) {
                    return true;
                }
            }
            return false;
        case sim::TutorialGoal::Speed: return services_.game_speed() != tutorial_->speed;
        case sim::TutorialGoal::Stock: {
            const sim::DefIndex r = content.find_resource(step.target);
            return r != sim::kNoDef && game.stored(town)[r] >= step.amount;
        }
        case sim::TutorialGoal::Population: return game.population(town) >= step.amount;
        case sim::TutorialGoal::Lua: {
            if (!tutorial_lua_ || now_ns < tutorial_->next_lua_ns) {
                return false;
            }
            tutorial_->next_lua_ns = now_ns + 500'000'000ull;  // Twice a second.
            script::TutorialState st;
            st.population = game.population(town);
            const sim::Calendar cal = game.calendar();
            st.year = static_cast<std::int32_t>(cal.year);
            st.month = static_cast<std::int32_t>(cal.month);
            st.day = static_cast<std::int32_t>(cal.day);
            const std::vector<std::int32_t> stored = game.stored(town);
            for (std::size_t r = 0; r < stored.size(); ++r) {
                st.stored[content.resources[r].id] = stored[r];
            }
            for (const sim::Building& b : game.buildings().data()) {
                if (b.owner == town && b.state == sim::BuildingState::Complete) {
                    ++st.built[content.buildings[b.def].id];
                }
            }
            bool done = false;
            std::string error;
            if (!tutorial_lua_->check(step.target, st, done, error)) {
                tutorial_->error = error;
                return false;
            }
            return done;
        }
        case sim::TutorialGoal::Count: break;
    }
    return false;
}

void UiHost::tutorial_panel(ui::Context& ctx) {
    const sim::Content* content = services_.content();
    if (content == nullptr || tutorial_->def >= content->tutorials.size()) {
        tutorial_.reset();
        return;
    }
    const sim::TutorialDef& t = content->tutorials[tutorial_->def];
    if (tutorial_->step >= t.steps.size()) {
        tutorial_.reset();
        return;
    }
    const sim::TutorialStep& step = t.steps[tutorial_->step];
    if (!tutorial_->step_started) {
        tutorial_->step_started = true;
        tutorial_->camera = services_.camera_view();
        tutorial_->speed = services_.game_speed();
    }
    const bool last = tutorial_->step + 1 == t.steps.size();
    if (!last && tutorial_step_done(step, ctx.now_ns())) {
        ++tutorial_->step;
        tutorial_->step_started = false;
        return;
    }
    // Phase 125: an RmlUi panel above the build bar, in the middle.
    ThingRows out;
    out.line(tr("tutorial.step", tr(t.name_key), static_cast<int>(tutorial_->step) + 1, static_cast<int>(t.steps.size())),
             WinRow::Kind::Accent);
    out.line(tr(step.text_key), WinRow::Kind::Paragraph);
    if (!tutorial_->error.empty()) {
        out.line(tr("tutorial.scriptError")).cls = "bad";
    }
    if (last) {
        RowButton finish = out.button(tr("tutorial.finish"), tr("tutorial.finish.tooltip"),
                                      [this](GameSession&, const RowInput&, RowEffects&) {
                                          services_.settings().gameplay.tutorial_seen = true;
                                          services_.settings_changed();
                                          tutorial_.reset();
                                      });
        finish.on = true;
        out.buttons({std::move(finish)});
    } else {
        out.buttons({out.button(tr("tutorial.skip"), tr("tutorial.skip.tooltip"),
                                [this](GameSession&, const RowInput&, RowEffects&) {
                                    if (tutorial_) {
                                        ++tutorial_->step;
                                        tutorial_->step_started = false;
                                    }
                                }),
                     out.button(tr("tutorial.quit"), tr("tutorial.quit.tooltip"),
                                [this](GameSession&, const RowInput&, RowEffects&) { tutorial_.reset(); })});
    }
    hud_.panel("tutorial", std::move(out), GameHud::PanelPlace::Bottom, 560.0f);
}

void UiHost::end_panel(ui::Context& ctx) {
    GameSession* s = services_.session();
    const sim::Game& game = s->game();
    std::vector<std::uint8_t> towns;
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        if (game.town_exists(p)) {
            towns.push_back(p);
        }
    }
    const sim::Outcome mine = game.player(s->town()).outcome;
    const char* title = mine == sim::Outcome::Won ? "end.won" : mine == sim::Outcome::Lost ? "end.lost" : "end.over";
    // Phase 125: an RmlUi panel in the middle.
    ThingRows out;
    out.line(tr(title), WinRow::Kind::Title);
    out.line(tr("end.header"), WinRow::Kind::Dim);
    static constexpr const char* kOutcomes[] = {"hud.outcome.playing", "hud.outcome.won", "hud.outcome.lost"};
    for (const std::uint8_t p : towns) {
        const sim::PlayerState& ps = game.player(p);
        std::string name = tr("hud.trade.town", static_cast<int>(p) + 1);
        if (net::NetSession* net = services_.net()) {
            for (const net::LobbyPlayer& lp : net->lobby().players) {
                name = lp.slot == p ? lp.name : name;
            }
        }
        out.line(tr("end.row", name, tr(kOutcomes[static_cast<std::size_t>(ps.outcome) % 3]), game.score(p), game.population(p),
                    game.military_power(p)),
                 p == s->town() ? WinRow::Kind::Accent : WinRow::Kind::Text);
    }
    out.buttons({out.button(tr("end.watch"), tr("end.watch.tooltip"),
                            [this](GameSession&, const RowInput&, RowEffects&) { end_seen_ = true; })});
    out.buttons({out.button(tr("gameMenu.leave"), tr("gameMenu.leave.tooltip"),
                            [this](GameSession&, const RowInput&, RowEffects&) {
                                end_seen_ = true;
                                leave_pending_ = true;  // Not from inside the game's own event: with the next frame.
                            })});
    hud_.panel("end", std::move(out), GameHud::PanelPlace::Center, 560.0f);
    (void)ctx;
}

void UiHost::game_menu(ui::Context& ctx) {
    const float button_h = ctx.s(48.0f);
    const float gap = ctx.s(10.0f);
    struct Entry {
        const char* id;
        const char* label;
        const char* tooltip;
    };
    static constexpr Entry kEntries[] = {
        {"resume", "gameMenu.resume", "gameMenu.resume.tooltip"},
        {"save", "gameMenu.save", "gameMenu.save.tooltip"},
        {"load", "menu.main.loadGame", "menu.main.loadGame.tooltip"},
        {"open", "gameMenu.open", "gameMenu.open.tooltip"},
        {"access", "gameMenu.access", "gameMenu.access.tooltip"},
        {"watch", "gameMenu.watch", "gameMenu.watch.tooltip"},
        {"play", "gameMenu.play", "gameMenu.play.tooltip"},
        {"settings", "menu.main.settings", "menu.main.settings.tooltip"},
        {"leave", "gameMenu.leave", "gameMenu.leave.tooltip"},
        {"quit", "gameMenu.quit", "menu.main.quit.tooltip"},
    };
    const bool playing = services_.session() != nullptr;
    const bool networked = playing && services_.session()->networked();
    if (access_dialog_) {
        access_dialog(ctx);
        return;
    }
    std::vector<const Entry*> entries;
    for (const Entry& e : kEntries) {
        const std::string_view id = e.id;
        // Loading a saved game is for single player only. Opening the game
        // to others too (phase 76), and not the tutorial's; once open, its
        // host changes who may come in.
        // Phase 79: a player goes to watch, where the game lets people
        // watch, and comes back to its town.
        const GameSession* session = services_.session();
        const bool seated = networked && session->seat() != GameSession::kNoSeat;
        if (id == "watch" ? seated && !session->spectating() && (session->game().access() & sim::access::kWatch) != 0
            : id == "play" ? seated && session->spectating()
            : id == "open" ? playing && !networked && !tutorial_
            : id == "access" ? services_.hosting()
                             : (id != "save" && id != "load") || (id == "save" && playing) ||
                                   (id == "load" && playing && !networked)) {
            entries.push_back(&e);
        }
    }
    const float content_h = static_cast<float>(entries.size()) * (button_h + gap) - gap;
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, content_h, tr("gameMenu.title"), y);
    for (const Entry* ep : entries) {
        const Entry& e = *ep;
        const ui::Rect r{content.x, std::round(y), content.w, std::round(button_h)};
        if (ctx.button(ctx.id(std::string("game_menu_") + e.id), r, tr(e.label), tr(e.tooltip))) {
            const std::string_view id = e.id;
            if (id == "resume") {
                game_menu_open_ = false;
            } else if (id == "save") {
                services_.save_game();
            } else if (id == "load") {
                saves_ = services_.list_saves();
                load_return_ = Screen::MapView;
                screen_ = Screen::Load;
            } else if (id == "watch") {
                services_.watch_game();
                game_menu_open_ = false;
            } else if (id == "play") {
                services_.play_game(0);
                game_menu_open_ = false;
            } else if (id == "open" || id == "access") {
                // What the game allows now; a game never opened offers both.
                const std::uint8_t now = services_.session()->game().access();
                access_dialog_ = true;
                access_open_ = id == "open" || (now & sim::access::kOpen) != 0;
                access_join_ = id == "open" || (now & sim::access::kJoin) != 0;
                access_found_ = id == "open" || (now & sim::access::kFound) != 0;
                access_watch_ = id == "open" || (now & sim::access::kWatch) != 0;
            } else if (id == "settings") {
                settings_return_ = Screen::MapView;
                screen_ = Screen::Settings;
            } else if (id == "leave") {
                game_menu_open_ = false;
                services_.leave_map();
                services_.leave_network();
                screen_ = Screen::MainMenu;
            } else {
                services_.request_quit();
            }
            return;
        }
        y += button_h + gap;
    }
    if (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open()) {
        game_menu_open_ = false;
    }
}

// Phase 76. Who may come into the game: opening a single-player game to
// others, or changing it as the host.
void UiHost::access_dialog(ui::Context& ctx) {
    const bool hosting = services_.hosting();
    const float button_h = ctx.s(48.0f);
    const float row_h = ctx.s(40.0f);
    const float gap = ctx.s(10.0f);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    struct Row {
        const char* id;
        const char* label;
        bool* value;
        bool shown;
        bool enabled;
    };
    const Row rows[] = {
        {"open", "access.open", &access_open_, hosting, true},
        {"join", "access.join", &access_join_, true, access_open_ || !hosting},
        {"found", "access.found", &access_found_, true, access_open_ || !hosting},
        {"watch", "access.watch", &access_watch_, true, true},
    };
    int shown = 0;
    for (const Row& r : rows) {
        shown += r.shown ? 1 : 0;
    }
    const float note_h = ctx.text().line_height(body);
    const float content_h = static_cast<float>(shown) * (row_h + gap) + note_h + gap + button_h;
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, content_h, tr(hosting ? "access.title.change" : "access.title.open"), y);
    const float check = std::round(ctx.s(28.0f));
    for (const Row& r : rows) {
        if (!r.shown) {
            continue;
        }
        const std::string tip = tr(std::string(r.label) + ".tooltip");
        const ui::Rect box{content.x, std::round(y + (row_h - check) * 0.5f), check, check};
        (void)ctx.checkbox(ctx.id(std::string("access_") + r.id), box, *r.value, tip, r.enabled);
        ctx.label({content.x + check + gap, std::round(y), content.w - check - gap, row_h}, tr(r.label), body,
                  r.enabled ? ctx.theme().text : ctx.theme().text_dim);
        y += row_h + gap;
    }
    ctx.label({content.x, std::round(y), content.w, note_h}, tr(hosting ? "access.note.change" : "access.note.open"),
              ctx.style(ctx.theme().small), ctx.theme().text_dim);
    y += note_h + gap;
    // Opening the game (not hosting yet): open to play if it lets people
    // join or found; it may also be only to watch. Open to nobody's use is
    // no use: one thing at least.
    const bool open = hosting ? access_open_ : access_join_ || access_found_;
    const bool valid = hosting ? !access_open_ || access_join_ || access_found_
                               : access_join_ || access_found_ || access_watch_;
    const float bw = (content.w - gap) * 0.5f;
    const std::uint8_t access = static_cast<std::uint8_t>((open ? sim::access::kOpen : 0) |
                                                         (access_join_ ? sim::access::kJoin : 0) |
                                                         (access_found_ ? sim::access::kFound : 0) |
                                                         (access_watch_ ? sim::access::kWatch : 0));
    if (ctx.button(ctx.id("access_ok"), {content.x, std::round(y), bw, button_h},
                   tr(hosting ? "access.apply" : "access.confirm"), {}, valid, true)) {
        if (hosting) {
            services_.set_access(access);
        } else if (!services_.open_game(access)) {
            show_message(tr("access.failed.title"), tr("lobby.hostFailed.body"));
        }
        access_dialog_ = false;
        game_menu_open_ = false;
        return;
    }
    if (ctx.button(ctx.id("access_back"), {content.x + bw + gap, std::round(y), bw, button_h}, tr("access.back")) ||
        (ctx.input().key(SDL_SCANCODE_ESCAPE) && !modal_open())) {
        access_dialog_ = false;
    }
}

void UiHost::load_screen(ui::Context& ctx, bool modal) {
    const float button_h = ctx.s(44.0f);
    const float row_h = ctx.s(64.0f);
    const float gap = ctx.s(8.0f);
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const ui::TextStyle small = ctx.style(ctx.theme().small);
    const float list_h = saves_.empty() ? ctx.text().line_height(body)
                                        : std::min(ctx.height() * 0.6f, static_cast<float>(saves_.size()) * (row_h + gap));
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, list_h + gap * 2 + button_h, tr("load.title"), y);
    bool back = false;
    if (saves_.empty()) {
        ctx.label({content.x, y, content.w, list_h}, tr("load.empty"), body, ctx.theme().text_dim);
    } else {
        const ui::Rect view{content.x, y, content.w, list_h};
        float ry = ctx.begin_scroll(ctx.id("load_list"), view);
        const float bw = std::min(ctx.s(140.0f), content.w * 0.3f);
        for (std::size_t i = 0; i < saves_.size(); ++i) {
            const save::Entry& e = saves_[i];
            const ui::Rect row{content.x, ry, content.w - ctx.s(12.0f), row_h};
            ctx.draw().rect(row, ctx.theme().button_active.with_alpha(0.6f));
            const float line = ctx.text().line_height(body);
            // Phase 78: two buttons, to play it or to host it for others.
            const float host_w = std::min(ctx.s(170.0f), content.w * 0.3f);
            ctx.label({row.x + gap, row.y + gap, row.w - bw - host_w - 4 * gap, line}, e.header.name, body,
                      e.readable ? ctx.theme().text : ctx.theme().text_disabled);
            const std::string detail = e.readable ? tr("load.detail", e.header.saved_at, static_cast<int>(e.header.population),
                                                       e.header.game_version)
                                                  : tr("load.unreadable");
            ctx.label({row.x + gap, row.y + gap + line, row.w - bw - host_w - 4 * gap, ctx.text().line_height(small)}, detail,
                      small, ctx.theme().text_dim);
            ctx.push_id("load_row");
            if (ctx.button(ctx.id("host" + std::to_string(i)),
                           {row.right() - bw - host_w - 2 * gap, row.y + (row_h - button_h) * 0.5f, host_w, button_h},
                           tr("load.host"), tr("load.host.tooltip"), e.readable && services_.scene_available())) {
                if (services_.load_game_as_host(e.file)) {
                    lobby_screen_.open();
                    screen_ = Screen::Lobby;
                    game_menu_open_ = false;
                    ctx.pop_id();
                    ctx.end_scroll(static_cast<float>(saves_.size()) * (row_h + gap));
                    return;
                }
            }
            if (ctx.button(ctx.id(std::to_string(i)), {row.right() - bw - gap, row.y + (row_h - button_h) * 0.5f, bw, button_h},
                           tr("load.load"), tr("load.load.tooltip"), e.readable)) {
                if (services_.load_game(e.file)) {
                    screen_ = Screen::MapView;
                    game_menu_open_ = false;
                    ctx.pop_id();
                    ctx.end_scroll(static_cast<float>(saves_.size()) * (row_h + gap));
                    return;
                }
            }
            ctx.pop_id();
            ry += row_h + gap;
        }
        ctx.end_scroll(static_cast<float>(saves_.size()) * (row_h + gap));
    }
    const float bw = std::min(ctx.s(180.0f), content.w);
    back = ctx.button(ctx.id("load_back"), {content.right() - bw, content.bottom() - button_h, bw, button_h},
                      tr("load.back"), tr("load.back.tooltip")) ||
           (!modal && ctx.input().key(SDL_SCANCODE_ESCAPE));
    if (back) {
        screen_ = load_return_ == Screen::MapView && services_.current_map() != nullptr ? Screen::MapView
                                                                                         : Screen::MainMenu;
    }
}

void UiHost::message_dialog(ui::Context& ctx) {
    const Message& m = messages_.front();
    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const float w = std::min(ctx.s(560.0f), ctx.width() - ctx.s(32.0f)) - 2 * ctx.s(24.0f);
    const float text_h = ctx.paragraph_height(w, m.body, body);
    const float button_h = ctx.s(44.0f);
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, text_h + ctx.s(20.0f) + button_h, m.title, y);
    ctx.paragraph({content.x, y, content.w, text_h}, m.body, body, ctx.theme().text);
    const float bw = std::min(ctx.s(160.0f), content.w);
    const ui::Rect ok{content.right() - bw, content.bottom() - button_h, bw, button_h};
    const bool enter = ctx.input().key(SDL_SCANCODE_RETURN) || ctx.input().key(SDL_SCANCODE_ESCAPE) ||
                       ctx.input().key(SDL_SCANCODE_KP_ENTER);
    if (ctx.button(ctx.id("message_ok"), ok, tr("dialog.ok"), {}, true, true) || enter) {
        messages_.erase(messages_.begin());
    }
}

void UiHost::display_confirm_dialog(ui::Context& ctx) {
    PendingDisplay& p = *pending_display_;
    if (!p.started) {
        p.started = true;
        p.deadline_ns = ctx.now_ns() + kDisplayConfirmNs;
    }
    const std::uint64_t left_ns = p.deadline_ns > ctx.now_ns() ? p.deadline_ns - ctx.now_ns() : 0;
    const auto seconds = static_cast<std::int64_t>((left_ns + 999'999'999ull) / 1'000'000'000ull);

    const ui::TextStyle body = ctx.style(ctx.theme().body);
    const std::string text = i18n::tr_n("dialog.keepDisplay.body", seconds);
    const float w = std::min(ctx.s(560.0f), ctx.width() - ctx.s(32.0f)) - 2 * ctx.s(24.0f);
    const float text_h = ctx.paragraph_height(w, text, body);
    const float button_h = ctx.s(44.0f);
    float y = 0.0f;
    const ui::Rect content = dialog_frame(ctx, text_h + ctx.s(20.0f) + button_h, tr("dialog.keepDisplay.title"), y);
    ctx.paragraph({content.x, y, content.w, text_h}, text, body, ctx.theme().text);

    const float gap = ctx.s(12.0f);
    const float bw = std::min(ctx.s(180.0f), (content.w - gap) * 0.5f);
    const ui::Rect keep{content.right() - bw, content.bottom() - button_h, bw, button_h};
    const ui::Rect revert{keep.x - gap - bw, keep.y, bw, button_h};
    const bool keep_clicked = ctx.button(ctx.id("display_keep"), keep, tr("dialog.keepDisplay.keep"), {}, true, true);
    const bool revert_clicked = ctx.button(ctx.id("display_revert"), revert, tr("dialog.keepDisplay.revert")) ||
                                ctx.input().key(SDL_SCANCODE_ESCAPE);
    if (keep_clicked) {
        pending_display_.reset();
    } else if (revert_clicked || left_ns == 0) {
        const DisplaySettings previous = p.previous;
        pending_display_.reset();
        if (services_.apply_display(previous)) {
            services_.settings().display = previous;
            services_.settings_changed();
        }
    }
}

}  // namespace sc
