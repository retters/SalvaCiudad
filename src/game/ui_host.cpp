#include "game/ui_host.h"

#include <algorithm>
#include <cmath>

#include "core/text.h"
#include "i18n/translator.h"
#include "version.h"

namespace sc {

using i18n::tr;

namespace {

constexpr std::uint64_t kDisplayConfirmNs = 15'000'000'000ull;

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

UiHost::UiHost(Services& services) : services_(services), settings_screen_(services) {}

void UiHost::show_message(std::string title, std::string body) {
    messages_.push_back({std::move(title), std::move(body)});
}

void UiHost::add_notice(std::string text) {
    notices_.push_back(std::move(text));
}

bool UiHost::wants_keyboard() const {
    return screen_ == Screen::Settings && settings_screen_.capturing_key();
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
    ctx.draw().rect({0, 0, ctx.width(), ctx.height()}, ctx.theme().background);

    if (screen_ == Screen::Settings) {
        if (!settings_screen_.frame(ctx, *this, modal)) {
            screen_ = Screen::MainMenu;
        }
    } else {
        ctx.set_input_blocked(modal);
        main_menu(ctx);
    }

    ctx.set_input_blocked(false);
    if (pending_display_) {
        display_confirm_dialog(ctx);
    } else if (!messages_.empty()) {
        message_dialog(ctx);
    }
}

void UiHost::draw_logo(ui::Context& ctx, float center_x, float y, float max_width, float max_height, float& height_out,
                       bool draw) {
    const std::string top = tr("app.logo.top");
    const std::string bottom = tr("app.logo.bottom");
    // The first letter of the bottom line is drawn larger.
    std::size_t first_len = 0;
    if (!bottom.empty()) {
        (void)text::next_codepoint(bottom, first_len);
    }
    const std::string_view first = std::string_view(bottom).substr(0, first_len);
    const std::string_view rest = std::string_view(bottom).substr(first_len);

    float factor = 1.0f;
    ui::TextStyle top_style;
    ui::TextStyle big_style;
    ui::TextStyle rest_style;
    float top_w = 0.0f;
    float bottom_w = 0.0f;
    float top_h = 0.0f;
    float bottom_h = 0.0f;
    // Shrink until the logo fits both the width and its share of the height.
    for (int attempt = 0; attempt < 12; ++attempt) {
        top_style = ctx.style(static_cast<int>(42.0f * factor), ui::FontRole::Logo);
        big_style = ctx.style(static_cast<int>(118.0f * factor), ui::FontRole::Logo);
        rest_style = ctx.style(static_cast<int>(88.0f * factor), ui::FontRole::Logo);
        top_w = ctx.text().measure(top_style, top);
        bottom_w = ctx.text().measure(big_style, first) + ctx.text().measure(rest_style, rest);
        top_h = ctx.text().line_height(top_style);
        bottom_h = ctx.text().line_height(big_style);
        if (std::max(top_w, bottom_w) <= max_width && top_h + bottom_h * 0.9f <= max_height) {
            break;
        }
        factor *= 0.85f;
    }
    const float big_ascent = ctx.text().ascent(big_style);
    height_out = top_h + bottom_h * 0.9f;
    if (!draw) {
        return;
    }
    const ui::Color gold = ctx.theme().accent;
    ctx.text().draw(ctx.draw(), top_style, std::round(center_x - top_w * 0.5f), y, top, ctx.theme().text);
    const float baseline = std::round(y + top_h + big_ascent * 0.95f);
    float x = std::round(center_x - bottom_w * 0.5f);
    x += ctx.text().draw(ctx.draw(), big_style, x, baseline - big_ascent, first, gold);
    ctx.text().draw(ctx.draw(), rest_style, x, baseline - ctx.text().ascent(rest_style), rest, gold);
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
        {"single", tr("menu.main.singlePlayer"), tr("menu.main.singlePlayer.tooltip"), false},
        {"host", tr("menu.main.hostGame"), tr("menu.main.hostGame.tooltip"), false},
        {"join", tr("menu.main.joinGame"), tr("menu.main.joinGame.tooltip"), false},
        {"load", tr("menu.main.loadGame"), tr("menu.main.loadGame.tooltip"), false},
        {"mods", tr("menu.main.mods"), tr("menu.main.mods.tooltip"), false},
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
            } else if (std::string_view(e.id) == "settings") {
                screen_ = Screen::Settings;
            } else if (std::string_view(e.id) == "quit") {
                services_.request_quit();
            }
        }
        y += button_h + gap;
    }
    const std::string version = tr("menu.main.version", std::string(SC_VERSION_STRING));
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
