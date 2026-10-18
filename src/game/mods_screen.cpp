#include "game/mods_screen.h"

#include <algorithm>
#include <format>

#include "game/ui_host.h"
#include "i18n/translator.h"
#include "mods/mod_library.h"

namespace sc {

using i18n::tr;

namespace {

RowFn run(std::function<void()> fn) {
    return [fn = std::move(fn)](GameSession*, const RowInput&, RowEffects&) { fn(); };
}

}  // namespace

void ModsScreen::open() {
    enabled_ = services_.mod_library().enabled_ids();
    dirty_ = false;
}

bool ModsScreen::frame(ui::Context& ctx, UiHost& host, bool input_blocked) {
    if (!input_blocked && ctx.input().key(SDL_SCANCODE_ESCAPE)) {
        leave_ = true;
    }
    host.menu("mods", rows(), 900.0f);
    const bool stay = !leave_;
    leave_ = false;
    return stay;
}

ThingRows ModsScreen::rows() {
    mods::ModLibrary& library = services_.mod_library();
    ThingRows out;
    out.line(tr("mods.title"), WinRow::Kind::Title);
    out.line(tr("mods.hint"), WinRow::Kind::Dim);
    // Enabled mods in their order first, then the others by name.
    std::vector<const mods::ModInfo*> list;
    if (const mods::ModInfo* core = library.find(mods::kCoreModId)) {
        list.push_back(core);
    }
    for (const std::string& id : enabled_) {
        if (const mods::ModInfo* m = library.find(id)) {
            list.push_back(m);
        }
    }
    for (const mods::ModInfo& m : library.mods()) {
        if (std::find(list.begin(), list.end(), &m) == list.end()) {
            list.push_back(&m);
        }
    }
    for (const mods::ModInfo* m : list) {
        const std::string id = m->manifest.id;
        const bool core = id == mods::kCoreModId;
        const bool on = core || std::find(enabled_.begin(), enabled_.end(), id) != enabled_.end();
        std::string name = tr(m->manifest.name_key);
        if (name == m->manifest.name_key || name.empty()) {
            name = id;  // Its texts are only loaded while the mod is on.
        }
        // Its name with the switch, the order arrows, its details and its state.
        RowButton toggle = out.button(tr(on ? "settings.value.on" : "settings.value.off"),
                                      tr(core ? "mods.coreAlways" : "mods.toggle.tooltip"), run([this, id] {
                                          const auto it = std::find(enabled_.begin(), enabled_.end(), id);
                                          if (it != enabled_.end()) {
                                              enabled_.erase(it);
                                          } else {
                                              enabled_.push_back(id);
                                          }
                                          dirty_ = true;
                                      }),
                                      !core && (m->errors.empty() || on), on);
        toggle.icon = on ? "icon-check" : "icon-minus";
        const auto move = [this, id](int delta) {
            return run([this, id, delta] {
                const auto it = std::find(enabled_.begin(), enabled_.end(), id);
                if (it == enabled_.end()) {
                    return;
                }
                const auto pos = static_cast<int>(it - enabled_.begin());
                const int to = std::clamp(pos + delta, 0, static_cast<int>(enabled_.size()) - 1);
                std::swap(enabled_[static_cast<std::size_t>(pos)], enabled_[static_cast<std::size_t>(to)]);
                dirty_ = true;
            });
        };
        out.line(name, WinRow::Kind::Section);
        std::vector<RowButton> buttons;
        buttons.push_back(std::move(toggle));
        if (on && !core) {
            RowButton up = out.button({}, tr("mods.up.tooltip"), move(-1));
            up.icon = "icon-up";
            RowButton down = out.button({}, tr("mods.down.tooltip"), move(1));
            down.icon = "icon-down";
            buttons.push_back(std::move(up));
            buttons.push_back(std::move(down));
        }
        out.buttons(std::move(buttons));
        out.rows.back().cls = "modbar";
        out.line(tr("mods.details", mods::version_text(m->manifest.version),
                    m->manifest.authors.empty() ? std::string("-") : m->manifest.authors.front(),
                    tr(m->builtin ? "mods.builtin" : "mods.user"), std::format("{:016x}", m->hash)),
                 WinRow::Kind::Dim);
        if (!m->errors.empty()) {
            std::string status = tr("mods.status.errors");
            for (const std::string& e : m->errors) {
                status += "\n- " + e;
            }
            out.line(status, WinRow::Kind::Paragraph).cls = "bad";
        } else {
            out.line(on && !m->loaded ? tr("mods.status.pending")
                     : m->loaded      ? tr(m->manifest.affects_simulation ? "mods.status.loaded" : "mods.status.loadedVisual")
                                      : tr("mods.status.off"),
                     WinRow::Kind::Dim);
        }
    }
    RowButton apply = out.button(tr("mods.apply"), tr("mods.apply.tooltip"), run([this] {
                                     services_.apply_mods(enabled_);
                                     enabled_ = services_.mod_library().enabled_ids();
                                     dirty_ = false;
                                 }),
                                 true, dirty_);
    out.buttons({out.button(tr("mods.back"), tr("mods.back.tooltip"), run([this] { leave_ = true; })),
                 out.button(tr("mods.openFolder"), tr("mods.openFolder.tooltip"), run([this] { services_.open_mods_folder(); })),
                 std::move(apply)});
    out.rows.back().cls = "big";
    return out;
}

}  // namespace sc
