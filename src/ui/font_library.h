// The fonts listed in data/fonts/fonts.json: interface families the player
// can choose in the settings, and the logo font. Adding a family is a data
// change: drop the files in data/fonts and list them in the manifest.
#pragma once

#include <filesystem>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "ui/font.h"

namespace sc::ui {

struct FontFamily {
    std::string id;    // "alegreya-sans"
    std::string name;  // "Alegreya Sans", shown as is (a proper name).
    std::unique_ptr<Font> regular;
    std::unique_ptr<Font> bold;  // May be null; Regular is used instead.
};

class FontLibrary {
public:
    // Loads the manifest and every font in it. Invalid entries are skipped
    // and logged. Returns false if no interface family could be loaded.
    bool load(const std::filesystem::path& fonts_dir);

    [[nodiscard]] const std::vector<FontFamily>& ui_families() const { return ui_families_; }
    // The family with `id`, or the first one.
    [[nodiscard]] const FontFamily* ui_family(std::string_view id) const;
    [[nodiscard]] const Font* logo() const { return logo_.get(); }

private:
    std::vector<FontFamily> ui_families_;
    std::unique_ptr<Font> logo_;
};

}  // namespace sc::ui
