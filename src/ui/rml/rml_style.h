// The interface's styles (phase 119, section 5.7).
//
// A style is a folder styles/<id>/ under a root of the interface (data/ui,
// or the ui folder of a mod) with a style.json, its own .rcss sheets and
// their images. The sheets of the game and of the style use var(--token);
// RCSS has no variables, so the game substitutes them before RmlUi reads a
// sheet (D-11705). Every token has a fixed type and a default; a style
// redefines some of them. Everything is checked when the style loads: an
// unknown token, a value of the wrong type, a sheet that does not exist or a
// path out of the style's folder rejects the whole style, with its reason.
//
// Values are written as in CSS (so the mockups' values can be copied) and
// turned into RCSS: alphas from 0..1 to 0..255, px to dp (the mockups' px
// are the game's design units).
#pragma once

#include <cstdint>
#include <filesystem>
#include <functional>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace sc::rml {

enum class TokenType : std::uint8_t {
    Color,     // #rgb, #rgba, #rrggbb, #rrggbbaa, rgb(), rgba() with alpha 0..1, transparent.
    Paint,     // A decorator: linear-gradient(), radial-gradient() and image(<file> <fit>), or a color.
    Length,    // 0, or a number with dp, px or %.
    Number,
    Shadow,    // none, or box-shadows: [inset] <x> <y> [<blur> [<spread>]] <color>.
    Filter,    // none, or blur(), saturate(), brightness(), contrast(), opacity().
    Font,      // A font family id of data/fonts, "ui", "logo" or "logo-small".
    IconMode,  // stroke, duotone or solid.
};

struct TokenSpec {
    std::string_view name;
    TokenType type;
    std::string_view value;  // Default, in CSS form.
};

// Every token the sheets may use, with its default (the Frosted look).
[[nodiscard]] std::span<const TokenSpec> token_specs();
[[nodiscard]] const TokenSpec* find_token(std::string_view name);

// True if `id` is a font family the interface may use.
using FontCheck = std::function<bool(std::string_view id)>;

// Images a value may name: checked and rewritten to a path from the root
// ("/styles/<id>/grain.png"). Empty function: images are refused.
using ImageCheck = std::function<std::optional<std::string>(std::string_view file)>;

// `value` (CSS form) as RCSS, or nothing if it is not of `type`.
[[nodiscard]] std::optional<std::string> convert_token(TokenType type, std::string_view value, const FontCheck& fonts,
                                                       const ImageCheck& images);

using TokenMap = std::map<std::string, std::string, std::less<>>;

// Replaces every var(--name) in `text`; names not in `tokens` stay as
// written and are added to `unknown`.
[[nodiscard]] std::string substitute_tokens(std::string_view text, const TokenMap& tokens,
                                            std::vector<std::string>* unknown = nullptr);

struct Style {
    std::string id;
    std::map<std::string, std::string, std::less<>> names;  // By language code.
    TokenMap tokens;    // Every token, as RCSS (defaults included).
    bool glass = false;
    std::string sheet;  // Its own sheets, tokens substituted and image paths rewritten.
    std::string icon_mode = "duotone";
    // Swatches for the settings: panel, text, accent, ok, warn, bad (RGBA).
    std::vector<std::uint32_t> preview;

    // The name in `language` (or its base, "es" for "es-MX"), else in
    // English, else the id.
    [[nodiscard]] std::string name(std::string_view language) const;
};

namespace style_limits {
inline constexpr std::size_t kMaxJsonBytes = 64u * 1024u;
inline constexpr std::size_t kMaxSheetBytes = 256u * 1024u;
inline constexpr std::size_t kMaxSheets = 8;
inline constexpr std::size_t kMaxValueBytes = 512;
inline constexpr std::size_t kMaxStyles = 64;
}  // namespace style_limits

// Reads styles/<id>/ under `root`. On failure, `error` says why (English).
[[nodiscard]] std::optional<Style> load_style(const std::filesystem::path& root, std::string_view id,
                                              const FontCheck& fonts, std::string& error);

// The token defaults as RCSS (what the game's sheets get with no style).
[[nodiscard]] TokenMap default_tokens();

// Every valid style under the roots' styles folders, in the roots' order
// and then by id; an id already found is rejected. Rejected styles go to
// `errors` as "<id>: <reason>".
class StyleLibrary {
public:
    void scan(const std::vector<std::filesystem::path>& roots, const FontCheck& fonts);
    [[nodiscard]] const std::vector<Style>& styles() const { return styles_; }
    [[nodiscard]] const std::vector<std::string>& errors() const { return errors_; }
    [[nodiscard]] const Style* find(std::string_view id) const;

private:
    std::vector<Style> styles_;
    std::vector<std::string> errors_;
};

inline constexpr std::string_view kDefaultStyle = "frosted";

}  // namespace sc::rml
