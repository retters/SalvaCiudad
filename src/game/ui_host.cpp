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
    // Phase 127: a small panel near the top.
    ThingRows out;
    out.line(toast_).cls = "center";
    menus_.give("toast", std::move(out), RmlPanels::Place::Center, 420.0f, std::round(ctx.s(60.0f)));
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
        const NewGameScreen::Result r = new_game_.frame(ctx, *this, modal);
        // The preview's picture, when a new one is ready (phase 56).
        if (std::optional<std::vector<std::uint8_t>> image = new_game_.take_preview()) {
            services_.set_hud_image("preview", minimap::kImageSize, minimap::kImageSize, *image);  // Phase 126: /live/preview.
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
        const JoinScreen::Result r = join_.frame(ctx, *this, modal);
        if (r == JoinScreen::Result::Back) {
            screen_ = Screen::MainMenu;
        } else if (r == JoinScreen::Result::Joining) {
            lobby_screen_.open();
            screen_ = Screen::Lobby;
        }
    } else if (screen_ == Screen::Lobby) {
        ctx.set_input_blocked(modal);
        if (lobby_screen_.frame(ctx, *this, modal) == LobbyScreen::Result::Leave) {
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
        if (!mods_screen_.frame(ctx, *this, modal)) {
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
    // Phase 126: the menus given this frame show; the others close.
    menus_.show(services_.rml(), ctx.width(), ctx.height(), ctx.s(1.0f), 0.0f, 0.0f);
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
    static constexpr const char* kSizeKeys[] = {"newGame.size.small", "newGame.size.medium", "newGame.size.large",
                                                "newGame.size.huge"};
    const auto size_index = static_cast<std::size_t>(map->settings.size);
    const std::string size = tr(kSizeKeys[std::min<std::size_t>(size_index, 3)], map->size);
    // Phase 127: what the map is, as a panel.
    ThingRows out;
    out.line(tr("map.info", std::to_string(map->settings.seed), size));
    out.line(tr("map.hint"), WinRow::Kind::Dim);
    out.line(camera_line(), WinRow::Kind::Dim);
    menus_.give("map_info", std::move(out), RmlPanels::Place::Center, 600.0f, std::round(ctx.s(12.0f)));
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
                                      [this](GameSession*, const RowInput&, RowEffects&) {
                                          services_.settings().gameplay.tutorial_seen = true;
                                          services_.settings_changed();
                                          tutorial_.reset();
                                      });
        finish.on = true;
        out.buttons({std::move(finish)});
    } else {
        out.buttons({out.button(tr("tutorial.skip"), tr("tutorial.skip.tooltip"),
                                [this](GameSession*, const RowInput&, RowEffects&) {
                                    if (tutorial_) {
                                        ++tutorial_->step;
                                        tutorial_->step_started = false;
                                    }
                                }),
                     out.button(tr("tutorial.quit"), tr("tutorial.quit.tooltip"),
                                [this](GameSession*, const RowInput&, RowEffects&) { tutorial_.reset(); })});
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
                            [this](GameSession*, const RowInput&, RowEffects&) { end_seen_ = true; })});
    out.buttons({out.button(tr("gameMenu.leave"), tr("gameMenu.leave.tooltip"),
                            [this](GameSession*, const RowInput&, RowEffects&) {
                                end_seen_ = true;
                                leave_pending_ = true;  // Not from inside the game's own event: with the next frame.
                            })});
    hud_.panel("end", std::move(out), GameHud::PanelPlace::Center, 560.0f);
    (void)ctx;
}

}  // namespace sc
