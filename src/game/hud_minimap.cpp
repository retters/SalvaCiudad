// The minimap and the compass (phase 24): the whole map north up, with the
// four cardinal points around it, every town's buildings and what the
// camera sees; a click moves the camera there. Beside it, a compass whose
// arrow points north as the camera turns.
#include <algorithm>
#include <array>
#include <cmath>

#include "game/game_hud.h"
#include "game/minimap.h"
#include "game/multiplayer_screens.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

constexpr float kMinimapSize = 200.0f;  // Design units.
constexpr float kLetterBand = 18.0f;    // Room for the cardinal points around it.
constexpr float kCompassSize = 64.0f;

}  // namespace

void GameHud::minimap(ui::Context& ctx, GameSession& s, bool blocked) {
    const sim::Game& game = s.game();
    const sim::MapData& map = game.map();
    if (map.size <= 0) {
        return;
    }
    // The image, made again only for another map; the fog over it when it
    // changed, at most a few times a second.
    const FogView& fog = s.fog();
    bool redraw = false;
    if (minimap_session_ != &s || !(minimap_settings_ == map.settings)) {
        minimap_base_ = minimap::render(map);
        minimap_session_ = &s;
        minimap_settings_ = map.settings;
        redraw = true;
    }
    const int fog_mode = static_cast<int>(fog.mode());
    if (fog_mode != minimap_fog_mode_ || fog.generation() != minimap_fog_generation_) {
        redraw = true;
    } else if (fog.revision() != minimap_fog_revision_ && ctx.now_ns() - minimap_fog_ns_ > 250'000'000ull) {
        redraw = true;
    }
    if (redraw) {
        std::vector<std::uint8_t> image = minimap_base_;
        minimap::apply_fog(image, map.size, fog);
        services_.set_ui_image(minimap::kImageId, minimap::kImageSize, minimap::kImageSize, std::move(image));
        minimap_fog_mode_ = fog_mode;
        minimap_fog_generation_ = fog.generation();
        minimap_fog_revision_ = fog.revision();
        minimap_fog_ns_ = ctx.now_ns();
    }

    const float band = std::round(ctx.s(kLetterBand));
    const float margin = std::round(ctx.s(10.0f));
    const float size = std::round(std::min(ctx.s(kMinimapSize), ctx.height() * 0.3f));
    const ui::Rect image{std::round(ctx.width() - margin - band - size), std::round(top_bar_bottom_ + margin + band), size,
                         size};
    const ui::Rect frame = image.inset(-band);
    right_top_ = frame.bottom() + margin;
    const ui::Theme& theme = ctx.theme();
    ctx.draw().rect(frame, theme.panel);
    ctx.draw().rect_outline(frame, theme.panel_border, std::max(1.0f, std::round(ctx.s(1.0f))));
    block(s, frame);
    ctx.draw().picture(image, minimap::kImageId, 0.0f, 0.0f, 1.0f, 1.0f, ui::Color::rgb(0xFFFFFF));

    const float scale = size / static_cast<float>(map.size);
    const auto to_screen = [&](float x, float z) { return std::array<float, 2>{image.x + x * scale, image.y + z * scale}; };
    ctx.draw().push_clip(image);
    // Buildings in their town's color, at least a dot.
    const float dot = std::max(2.0f, std::round(ctx.s(2.0f)));
    for (const sim::Building& b : game.buildings().data()) {
        if (fog.mode() != sim::FogMode::None && game.town_group(b.owner) != fog.group() &&
            !fog.rect_shows(b.x, b.z, b.width, b.depth)) {
            continue;  // Under the fog of war.
        }
        const auto [x, y] = to_screen(static_cast<float>(b.x), static_cast<float>(b.z));
        const float w = std::max(dot, static_cast<float>(b.width) * scale);
        const float h = std::max(dot, static_cast<float>(b.depth) * scale);
        ctx.draw().rect({std::floor(x), std::floor(y), w, h}, player_color(b.owner));
    }
    // What the camera sees.
    const Services::CameraGround view = services_.camera_ground();
    const float thick = std::max(1.0f, std::round(ctx.s(1.5f)));
    for (int i = 0; i < 4; ++i) {
        const int j = (i + 1) % 4;
        const auto a = to_screen(view.corners[static_cast<std::size_t>(i) * 2], view.corners[static_cast<std::size_t>(i) * 2 + 1]);
        const auto b = to_screen(view.corners[static_cast<std::size_t>(j) * 2], view.corners[static_cast<std::size_t>(j) * 2 + 1]);
        ctx.draw().line(a[0], a[1], b[0], b[1], thick, ui::Color::rgb(0xFFFFFF, 220));
    }
    ctx.draw().pop_clip();

    // The four cardinal points: north (up) in red.
    const ui::TextStyle letter = ctx.style(theme.small, ui::FontRole::Bold);
    const struct {
        const char* key;
        ui::Rect r;
        ui::Color color;
    } points[] = {
        {"hud.minimap.north", {image.x, frame.y, image.w, band}, theme.danger},
        {"hud.minimap.south", {image.x, image.bottom(), image.w, band}, theme.text},
        {"hud.minimap.east", {image.right(), image.y, band, image.h}, theme.text},
        {"hud.minimap.west", {frame.x, image.y, band, image.h}, theme.text},
    };
    for (const auto& p : points) {
        ctx.label(p.r, tr(p.key), letter, p.color, ui::Align::Center);
    }
    ctx.tooltip_area(ctx.id("minimap"), image, tr("hud.minimap.tooltip"));

    // A click, or a drag that started on it, takes the camera there. Not
    // through a game window lying over it.
    const ui::Input& in = ctx.input();
    bool covered = false;
    for (const auto& [id, r] : shown_last_) {
        covered = covered || r.contains(in.mouse_x, in.mouse_y);
    }
    if (blocked || !in.mouse_down) {
        minimap_dragging_ = false;
    } else if (in.mouse_pressed && image.contains(in.mouse_x, in.mouse_y) && !covered) {
        minimap_dragging_ = true;
    }
    if (minimap_dragging_) {
        const float x = std::clamp((in.mouse_x - image.x) / scale, 0.0f, static_cast<float>(map.size));
        const float z = std::clamp((in.mouse_y - image.y) / scale, 0.0f, static_cast<float>(map.size));
        services_.focus_camera(x, z);
    }

    compass(ctx, {std::round(frame.x - margin - ctx.s(kCompassSize)), frame.y, std::round(ctx.s(kCompassSize)),
                  std::round(ctx.s(kCompassSize))},
            view.yaw);
    block(s, {std::round(frame.x - margin - ctx.s(kCompassSize)), frame.y, std::round(ctx.s(kCompassSize)),
              std::round(ctx.s(kCompassSize))});
}

void GameHud::compass(ui::Context& ctx, const ui::Rect& box, float yaw) {
    const ui::Theme& theme = ctx.theme();
    ui::DrawList& d = ctx.draw();
    const float cx = box.x + box.w * 0.5f;
    const float cy = box.y + box.h * 0.5f;
    const float radius = box.w * 0.5f;
    // A round dial from a fan of triangles.
    constexpr int kSides = 32;
    const float border = std::max(1.0f, std::round(ctx.s(1.5f)));
    for (int i = 0; i < kSides; ++i) {
        const float a0 = static_cast<float>(i) / kSides * 6.2831853f;
        const float a1 = static_cast<float>(i + 1) / kSides * 6.2831853f;
        d.triangle(cx, cy, cx + std::cos(a0) * radius, cy + std::sin(a0) * radius, cx + std::cos(a1) * radius,
                   cy + std::sin(a1) * radius, theme.panel_border);
        const float inner = radius - border;
        d.triangle(cx, cy, cx + std::cos(a0) * inner, cy + std::sin(a0) * inner, cx + std::cos(a1) * inner,
                   cy + std::sin(a1) * inner, theme.panel);
    }
    // The arrow: a red half toward north, a light half behind.
    const std::array<float, 2> north = minimap::north_on_screen(yaw);
    const float nx = north[0];
    const float ny = north[1];
    const float px = -ny;  // Across the arrow.
    const float py = nx;
    const float tip = radius * 0.5f;
    const float half = radius * 0.2f;
    d.triangle(cx + nx * tip, cy + ny * tip, cx + px * half, cy + py * half, cx - px * half, cy - py * half, theme.danger);
    d.triangle(cx - nx * tip, cy - ny * tip, cx + px * half, cy + py * half, cx - px * half, cy - py * half, theme.text);
    // The N at the arrow's head.
    const ui::TextStyle letter = ctx.style(theme.small, ui::FontRole::Bold);
    const float lh = ctx.text().line_height(letter);
    const float at = radius * 0.74f;
    ctx.label({cx + nx * at - lh * 0.5f, cy + ny * at - lh * 0.5f, lh, lh}, tr("hud.minimap.north"), letter, theme.text,
              ui::Align::Center);
    ctx.tooltip_area(ctx.id("compass"), box, tr("hud.compass.tooltip"));
}

}  // namespace sc
