#include "ui/rml/rml_style.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <charconv>
#include <cmath>
#include <format>

#include "core/file_io.h"
#include "core/json.h"
#include "core/text.h"

namespace sc::rml {

namespace {

// Defaults: the Frosted look of the mockups (docs/propuestas/interfaz/temas/frosted.css).
constexpr TokenSpec kTokens[] = {
    {"font", TokenType::Font, "ui"},
    {"font-size", TokenType::Length, "16dp"},
    {"font-small", TokenType::Length, "14dp"},
    {"title-size", TokenType::Length, "19dp"},
    {"title-weight", TokenType::Number, "700"},
    {"text", TokenType::Color, "#1b1f24"},
    {"dim", TokenType::Color, "#4b5563"},
    {"accent", TokenType::Color, "#5b5bd6"},
    {"accent-text", TokenType::Color, "#ffffff"},
    {"ok", TokenType::Color, "#18794e"},
    {"warn", TokenType::Color, "#ad5700"},
    {"bad", TokenType::Color, "#cd2b31"},
    {"info", TokenType::Color, "#0d74ce"},
    {"ok-soft", TokenType::Color, "rgba(24, 121, 78, .14)"},
    {"warn-soft", TokenType::Color, "rgba(173, 87, 0, .14)"},
    {"bad-soft", TokenType::Color, "rgba(205, 43, 49, .16)"},
    {"title-text", TokenType::Color, "#1b1f24"},
    {"panel", TokenType::Paint, "linear-gradient(160deg, rgba(255, 255, 255, .62), rgba(255, 255, 255, .38))"},
    {"panel-simple", TokenType::Paint, "linear-gradient(160deg, rgba(248, 249, 252, .95), rgba(238, 240, 246, .9))"},
    {"panel-solid", TokenType::Color, "#eef0f4"},
    {"panel-border", TokenType::Color, "rgba(255, 255, 255, .7)"},
    {"panel-border-width", TokenType::Length, "1dp"},
    {"panel-radius", TokenType::Length, "16dp"},
    {"panel-shadow", TokenType::Shadow, "inset 0 1px 0 rgba(255, 255, 255, .9), 0 10px 32px rgba(20, 30, 70, .2)"},
    {"panel-blur", TokenType::Filter, "blur(18px) saturate(160%)"},
    {"panel-pad", TokenType::Length, "14dp"},
    {"sep", TokenType::Color, "rgba(20, 30, 70, .1)"},
    {"btn", TokenType::Color, "rgba(255, 255, 255, .5)"},
    {"btn-hover", TokenType::Color, "rgba(255, 255, 255, .75)"},
    {"btn-on", TokenType::Color, "#5b5bd6"},
    {"btn-on-text", TokenType::Color, "#ffffff"},
    {"btn-border", TokenType::Color, "rgba(255, 255, 255, .7)"},
    {"btn-radius", TokenType::Length, "10dp"},
    {"btn-size", TokenType::Length, "30dp"},
    {"btn-shadow", TokenType::Shadow, "0 1px 2px rgba(20, 30, 70, .08)"},
    {"chip", TokenType::Color, "rgba(255, 255, 255, .55)"},
    {"row", TokenType::Color, "rgba(255, 255, 255, .35)"},
    {"row-hover", TokenType::Color, "rgba(255, 255, 255, .6)"},
    {"row-border", TokenType::Color, "rgba(255, 255, 255, .5)"},
    {"row-radius", TokenType::Length, "12dp"},
    {"meter", TokenType::Color, "rgba(20, 30, 70, .1)"},
    {"switch-off", TokenType::Color, "rgba(20, 30, 70, .16)"},
    {"switch-on", TokenType::Paint, "#5b5bd6"},
    {"knob", TokenType::Color, "#ffffff"},
    {"thumb", TokenType::Paint, "radial-gradient(circle at 50% 75%, rgba(255, 255, 255, .7), transparent 65%)"},
    {"icon", TokenType::Color, "#4b5563"},
    {"icon-hover", TokenType::Color, "#1b1f24"},
    {"icon-on", TokenType::Color, "#5b5bd6"},
    {"icon-mode", TokenType::IconMode, "duotone"},
    {"tip", TokenType::Color, "rgba(28, 32, 40, .82)"},
    {"tip-text", TokenType::Color, "#ffffff"},
    {"tip-radius", TokenType::Length, "10dp"},
};

constexpr std::string_view kFits[] = {"fill", "contain", "cover", "scale-none", "scale-down",
                                      "repeat", "repeat-x", "repeat-y"};
constexpr std::string_view kGradientWords[] = {"to", "left", "right", "top", "bottom", "center", "circle", "ellipse",
                                               "at", "closest-side", "closest-corner", "farthest-side",
                                               "farthest-corner"};

std::string_view trim(std::string_view s) {
    while (!s.empty() && std::isspace(static_cast<unsigned char>(s.front())) != 0) {
        s.remove_prefix(1);
    }
    while (!s.empty() && std::isspace(static_cast<unsigned char>(s.back())) != 0) {
        s.remove_suffix(1);
    }
    return s;
}

// Splits at `sep` outside parentheses; nothing if they do not balance.
std::optional<std::vector<std::string_view>> split(std::string_view s, char sep) {
    std::vector<std::string_view> out;
    int depth = 0;
    std::size_t start = 0;
    for (std::size_t i = 0; i < s.size(); ++i) {
        const char c = s[i];
        if (c == '(') {
            ++depth;
        } else if (c == ')') {
            if (--depth < 0) {
                return std::nullopt;
            }
        } else if (depth == 0 && (sep == ' ' ? std::isspace(static_cast<unsigned char>(c)) != 0 : c == sep)) {
            const std::string_view part = trim(s.substr(start, i - start));
            if (!part.empty() || sep != ' ') {
                out.push_back(part);
            }
            start = i + 1;
        }
    }
    if (depth != 0) {
        return std::nullopt;
    }
    const std::string_view last = trim(s.substr(start));
    if (!last.empty() || sep != ' ') {
        out.push_back(last);
    }
    return out;
}

std::optional<double> number(std::string_view s) {
    if (s.empty() || s.size() > 32) {
        return std::nullopt;
    }
    std::string buf(s);
    if (buf.front() == '.') {
        buf.insert(0, "0");
    } else if (buf.size() > 1 && buf[0] == '-' && buf[1] == '.') {
        buf.insert(1, "0");
    } else if (buf.front() == '+') {
        buf.erase(0, 1);
    }
    double v = 0.0;
    const auto [p, ec] = std::from_chars(buf.data(), buf.data() + buf.size(), v);
    if (ec != std::errc() || p != buf.data() + buf.size() || !std::isfinite(v)) {
        return std::nullopt;
    }
    return v;
}

std::string format_number(double v) {
    std::string s = std::format("{:.3f}", v);
    while (s.back() == '0') {
        s.pop_back();
    }
    if (s.back() == '.') {
        s.pop_back();
    }
    return s == "-0" ? "0" : s;
}

struct Rgba {
    double r = 0;
    double g = 0;
    double b = 0;
    double a = 1;
};

int hex_digit(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return -1;
}

std::optional<Rgba> parse_color(std::string_view s) {
    s = trim(s);
    if (s == "transparent") {
        return Rgba{0, 0, 0, 0};
    }
    if (s == "white") {
        return Rgba{255, 255, 255, 1};
    }
    if (s == "black") {
        return Rgba{0, 0, 0, 1};
    }
    if (!s.empty() && s.front() == '#') {
        const std::string_view h = s.substr(1);
        if (h.size() != 3 && h.size() != 4 && h.size() != 6 && h.size() != 8) {
            return std::nullopt;
        }
        std::array<double, 4> c{0, 0, 0, 255};
        const bool shortform = h.size() <= 4;
        const std::size_t n = shortform ? h.size() : h.size() / 2;
        for (std::size_t i = 0; i < n; ++i) {
            const int hi = hex_digit(h[shortform ? i : i * 2]);
            const int lo = hex_digit(h[shortform ? i : i * 2 + 1]);
            if (hi < 0 || lo < 0) {
                return std::nullopt;
            }
            c[i] = shortform ? hi * 17 : hi * 16 + lo;
        }
        return Rgba{c[0], c[1], c[2], c[3] / 255.0};
    }
    const bool rgba = s.starts_with("rgba(");
    if ((!rgba && !s.starts_with("rgb(")) || s.back() != ')') {
        return std::nullopt;
    }
    const std::string_view inner = s.substr(rgba ? 5 : 4, s.size() - (rgba ? 6 : 5));
    const auto parts = split(inner, ',');
    if (!parts || parts->size() != (rgba ? 4u : 3u)) {
        return std::nullopt;
    }
    Rgba out;
    double* channels[3] = {&out.r, &out.g, &out.b};
    for (std::size_t i = 0; i < 3; ++i) {
        const auto v = number((*parts)[i]);
        if (!v || *v < 0 || *v > 255) {
            return std::nullopt;
        }
        *channels[i] = *v;
    }
    if (rgba) {
        std::string_view a = (*parts)[3];
        const bool percent = !a.empty() && a.back() == '%';
        const auto v = number(percent ? a.substr(0, a.size() - 1) : a);
        if (!v) {
            return std::nullopt;
        }
        out.a = percent ? *v / 100.0 : *v;
        if (out.a < 0 || out.a > 1) {
            return std::nullopt;
        }
    }
    return out;
}

std::string rcss_color(const Rgba& c) {
    return std::format("rgba({}, {}, {}, {})", std::lround(c.r), std::lround(c.g), std::lround(c.b),
                       std::lround(c.a * 255.0));
}

// A length: 0, or a number with dp, px (as dp), % or, if `angles`, deg.
std::optional<std::string> length(std::string_view s, bool angles = false) {
    s = trim(s);
    if (s == "0") {
        return std::string("0dp");
    }
    for (const std::string_view unit : {std::string_view("dp"), std::string_view("px"), std::string_view("%"),
                                        std::string_view("deg")}) {
        if (unit == "deg" && !angles) {
            continue;
        }
        if (s.size() > unit.size() && s.ends_with(unit)) {
            const auto v = number(s.substr(0, s.size() - unit.size()));
            if (!v || std::abs(*v) > 100000.0) {
                return std::nullopt;
            }
            return format_number(*v) + std::string(unit == "px" ? std::string_view("dp") : unit);
        }
    }
    return std::nullopt;
}

bool is_color_start(std::string_view s) {
    return s.starts_with("#") || s.starts_with("rgb") || s == "transparent" || s == "white" || s == "black";
}

std::optional<std::string> gradient(std::string_view fn, std::string_view inner) {
    const auto args = split(inner, ',');
    if (!args || args->size() < 2 || args->size() > 18) {
        return std::nullopt;
    }
    std::string out = std::string(fn) + "(";
    for (std::size_t i = 0; i < args->size(); ++i) {
        const auto words = split((*args)[i], ' ');
        if (!words || words->empty()) {
            return std::nullopt;
        }
        if (i > 0) {
            out += ", ";
        }
        for (std::size_t w = 0; w < words->size(); ++w) {
            const std::string_view word = (*words)[w];
            std::string converted;
            if (is_color_start(word)) {
                const auto c = parse_color(word);
                if (!c) {
                    return std::nullopt;
                }
                converted = rcss_color(*c);
            } else if (std::find(std::begin(kGradientWords), std::end(kGradientWords), word) !=
                       std::end(kGradientWords)) {
                converted = std::string(word);
            } else if (const auto l = length(word, true)) {
                converted = *l;
            } else {
                return std::nullopt;
            }
            out += (w > 0 ? " " : "") + converted;
        }
    }
    return out + ")";
}

std::optional<std::string> image(std::string_view inner, const ImageCheck& images) {
    const auto words = split(inner, ' ');
    if (!words || words->empty() || words->size() > 2 || !images) {
        return std::nullopt;
    }
    const auto file = images((*words)[0]);
    if (!file) {
        return std::nullopt;
    }
    std::string out = "image(" + *file;
    if (words->size() == 2) {
        if (std::find(std::begin(kFits), std::end(kFits), (*words)[1]) == std::end(kFits)) {
            return std::nullopt;
        }
        out += " " + std::string((*words)[1]);
    }
    return out + ")";
}

std::optional<std::string> paint(std::string_view value, const ImageCheck& images) {
    const auto items = split(value, ',');
    if (!items || items->empty() || items->size() > 4) {
        return std::nullopt;
    }
    std::string out;
    for (const std::string_view item : *items) {
        std::string converted;
        const std::size_t open = item.find('(');
        const std::string_view fn = open == std::string_view::npos ? item : item.substr(0, open);
        if (is_color_start(item)) {
            const auto c = parse_color(item);
            if (!c) {
                return std::nullopt;
            }
            converted = "linear-gradient(" + rcss_color(*c) + ", " + rcss_color(*c) + ")";
        } else if (open != std::string_view::npos && item.back() == ')' &&
                   (fn == "linear-gradient" || fn == "radial-gradient" || fn == "repeating-linear-gradient" ||
                    fn == "repeating-radial-gradient" || fn == "image")) {
            const std::string_view inner = item.substr(open + 1, item.size() - open - 2);
            const auto c = fn == "image" ? image(inner, images) : gradient(fn, inner);
            if (!c) {
                return std::nullopt;
            }
            converted = *c;
        } else {
            return std::nullopt;
        }
        out += (out.empty() ? "" : ", ") + converted;
    }
    return out;
}

std::optional<std::string> shadow(std::string_view value) {
    if (trim(value) == "none") {
        return std::string("none");
    }
    const auto items = split(value, ',');
    if (!items || items->empty() || items->size() > 4) {
        return std::nullopt;
    }
    std::string out;
    for (const std::string_view item : *items) {
        const auto words = split(item, ' ');
        if (!words) {
            return std::nullopt;
        }
        bool inset = false;
        std::optional<Rgba> color;
        std::vector<std::string> lengths;
        for (const std::string_view w : *words) {
            if (w == "inset" && !inset) {
                inset = true;
            } else if (is_color_start(w) && !color) {
                color = parse_color(w);
                if (!color) {
                    return std::nullopt;
                }
            } else if (const auto l = length(w)) {
                lengths.push_back(*l);
            } else {
                return std::nullopt;
            }
        }
        if (!color || lengths.size() < 2 || lengths.size() > 4) {
            return std::nullopt;
        }
        std::string one = rcss_color(*color);
        for (const std::string& l : lengths) {
            one += " " + l;
        }
        if (inset) {
            one += " inset";
        }
        out += (out.empty() ? "" : ", ") + one;
    }
    return out;
}

std::optional<std::string> filter(std::string_view value) {
    if (trim(value) == "none") {
        return std::string("none");
    }
    const auto items = split(value, ' ');
    if (!items || items->empty() || items->size() > 6) {
        return std::nullopt;
    }
    std::string out;
    for (const std::string_view item : *items) {
        const std::size_t open = item.find('(');
        if (open == std::string_view::npos || item.back() != ')') {
            return std::nullopt;
        }
        const std::string_view fn = item.substr(0, open);
        const std::string_view arg = trim(item.substr(open + 1, item.size() - open - 2));
        std::optional<std::string> v;
        if (fn == "blur") {
            v = length(arg);
            if (v && v->ends_with("%")) {
                v.reset();
            }
        } else if (fn == "saturate" || fn == "brightness" || fn == "contrast" || fn == "opacity") {
            if (arg.ends_with("%")) {
                const auto n = number(arg.substr(0, arg.size() - 1));
                if (n && *n >= 0 && *n <= 1000) {
                    v = format_number(*n) + "%";
                }
            } else if (const auto n = number(arg); n && *n >= 0 && *n <= 10) {
                v = format_number(*n);
            }
        }
        if (!v) {
            return std::nullopt;
        }
        out += (out.empty() ? "" : " ") + std::string(fn) + "(" + *v + ")";
    }
    return out;
}

bool plain_path(std::string_view p) {
    if (p.empty() || p.size() > 128 || p.front() == '/' || p.find("..") != std::string_view::npos) {
        return false;
    }
    return std::all_of(p.begin(), p.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.' || c == '/';
    });
}

// A file inside `folder`, existing and not leaving it through links.
std::optional<std::filesystem::path> inside(const std::filesystem::path& folder, std::string_view relative) {
    if (!plain_path(relative)) {
        return std::nullopt;
    }
    std::error_code ec;
    const std::filesystem::path base = std::filesystem::weakly_canonical(folder, ec);
    if (ec) {
        return std::nullopt;
    }
    const std::filesystem::path full = std::filesystem::weakly_canonical(base / text::path_from_utf8(relative), ec);
    if (ec || !std::filesystem::is_regular_file(full, ec)) {
        return std::nullopt;
    }
    // Every part of the folder must start the file's path.
    auto fi = full.begin();
    for (auto bi = base.begin(); bi != base.end(); ++bi, ++fi) {
        if (fi == full.end() || *bi != *fi) {
            return std::nullopt;
        }
    }
    return full;
}

// Rewrites the files a style sheet names (image(<file>) and src: <file>) to
// paths from the root; sprite names (no dot) stay. False if one is refused.
bool rewrite_paths(std::string& sheet, const ImageCheck& images, std::string& error) {
    std::string out;
    out.reserve(sheet.size());
    std::size_t i = 0;
    while (i < sheet.size()) {
        std::size_t at = std::string::npos;
        std::size_t skip = 0;
        for (const std::string_view key : {std::string_view("image("), std::string_view("src:")}) {
            const std::size_t p = sheet.find(key, i);
            if (p < at) {
                at = p;
                skip = key.size();
            }
        }
        if (at == std::string::npos) {
            out.append(sheet, i, std::string::npos);
            break;
        }
        std::size_t start = at + skip;
        while (start < sheet.size() && (sheet[start] == ' ' || sheet[start] == '\t')) {
            ++start;
        }
        std::size_t end = start;
        while (end < sheet.size() && std::string_view(" \t\r\n,);").find(sheet[end]) == std::string_view::npos) {
            ++end;
        }
        out.append(sheet, i, start - i);
        const std::string_view file(sheet.data() + start, end - start);
        if (file.find('.') == std::string_view::npos) {
            out.append(file);  // A sprite.
        } else {
            const auto rewritten = images ? images(file) : std::nullopt;
            if (!rewritten) {
                error = std::format("the file '{}' is not a PNG inside the style's folder", file);
                return false;
            }
            out += *rewritten;
        }
        i = end;
    }
    sheet = std::move(out);
    return true;
}

std::uint32_t pack(const Rgba& c) {
    const auto b = [](double v) { return static_cast<std::uint32_t>(std::clamp(std::lround(v), 0L, 255L)); };
    return (b(c.r) << 24) | (b(c.g) << 16) | (b(c.b) << 8) | b(c.a * 255.0);
}

bool valid_id(std::string_view id) {
    return !id.empty() && id.size() <= 40 && std::all_of(id.begin(), id.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';
    });
}

}  // namespace

std::span<const TokenSpec> token_specs() {
    return kTokens;
}

const TokenSpec* find_token(std::string_view name) {
    for (const TokenSpec& t : kTokens) {
        if (t.name == name) {
            return &t;
        }
    }
    return nullptr;
}

std::optional<std::string> convert_token(TokenType type, std::string_view value, const FontCheck& fonts,
                                         const ImageCheck& images) {
    value = trim(value);
    if (value.empty() || value.size() > style_limits::kMaxValueBytes) {
        return std::nullopt;
    }
    switch (type) {
    case TokenType::Color:
        if (const auto c = parse_color(value)) {
            return rcss_color(*c);
        }
        return std::nullopt;
    case TokenType::Paint:
        return paint(value, images);
    case TokenType::Length:
        return length(value);
    case TokenType::Number:
        if (const auto n = number(value); n && std::abs(*n) <= 100000.0) {
            return format_number(*n);
        }
        return std::nullopt;
    case TokenType::Shadow:
        return shadow(value);
    case TokenType::Filter:
        return filter(value);
    case TokenType::Font:
        if (value == "ui" || value == "logo" || value == "logo-small" || (fonts && valid_id(value) && fonts(value))) {
            return std::string(value);
        }
        return std::nullopt;
    case TokenType::IconMode:
        if (value == "stroke" || value == "duotone" || value == "solid") {
            return std::string(value);
        }
        return std::nullopt;
    }
    return std::nullopt;
}

std::string substitute_tokens(std::string_view text, const TokenMap& tokens, std::vector<std::string>* unknown) {
    std::string out;
    out.reserve(text.size());
    std::size_t i = 0;
    while (i < text.size()) {
        const std::size_t at = text.find("var(--", i);
        if (at == std::string_view::npos) {
            out.append(text.substr(i));
            break;
        }
        const std::size_t close = text.find(')', at);
        out.append(text.substr(i, at - i));
        if (close == std::string_view::npos) {
            out.append(text.substr(at));
            break;
        }
        const std::string_view name = text.substr(at + 6, close - at - 6);
        if (const auto it = tokens.find(name); it != tokens.end()) {
            out += it->second;
        } else {
            out.append(text.substr(at, close + 1 - at));
            if (unknown != nullptr) {
                unknown->emplace_back(name);
            }
        }
        i = close + 1;
    }
    return out;
}

TokenMap default_tokens() {
    TokenMap out;
    for (const TokenSpec& t : kTokens) {
        if (auto v = convert_token(t.type, t.value, nullptr, nullptr)) {
            out.emplace(std::string(t.name), std::move(*v));
        }
    }
    return out;
}

std::string Style::name(std::string_view language) const {
    if (const auto it = names.find(language); it != names.end()) {
        return it->second;
    }
    // "es-MX" takes the "es" name.
    if (const auto it = names.find(language.substr(0, language.find('-'))); it != names.end()) {
        return it->second;
    }
    if (const auto it = names.find("en"); it != names.end()) {
        return it->second;
    }
    return id;
}

std::optional<Style> load_style(const std::filesystem::path& root, std::string_view id, const FontCheck& fonts,
                                std::string& error) {
    if (!valid_id(id)) {
        error = "the folder name is not a valid id (a-z, 0-9 and '-')";
        return std::nullopt;
    }
    const std::filesystem::path folder = root / "styles" / text::path_from_utf8(id);
    const auto json_path = inside(folder, "style.json");
    if (!json_path) {
        error = "no style.json";
        return std::nullopt;
    }
    const fs::ReadResult r = fs::read_file(*json_path, style_limits::kMaxJsonBytes);
    if (r.error != fs::IoError::None) {
        error = std::format("cannot read style.json: {}", fs::io_error_name(r.error));
        return std::nullopt;
    }
    json::ParseResult parsed = json::parse_object(r.data);
    if (parsed.error != json::ParseError::None) {
        error = "style.json: " + parsed.message;
        return std::nullopt;
    }
    yyjson_mut_val* root_obj = yyjson_mut_doc_get_root(parsed.doc.get());
    {
        std::size_t idx = 0;
        std::size_t max = 0;
        yyjson_mut_val* key = nullptr;
        yyjson_mut_val* val = nullptr;
        yyjson_mut_obj_foreach(root_obj, idx, max, key, val) {
            const std::string_view k(yyjson_mut_get_str(key), yyjson_mut_get_len(key));
            if (k != "schemaVersion" && k != "name" && k != "tokens" && k != "glass" && k != "sheets") {
                error = std::format("style.json: unknown field '{}'", k);
                return std::nullopt;
            }
        }
    }
    std::int64_t version = 0;
    if (json::get_int(root_obj, "schemaVersion", 1, 1, version) != json::Field::Ok) {
        error = "style.json: schemaVersion must be 1";
        return std::nullopt;
    }
    Style style;
    style.id = std::string(id);
    const std::string prefix = "/styles/" + style.id + "/";
    const ImageCheck images = [&folder, &prefix](std::string_view file) -> std::optional<std::string> {
        if (!file.ends_with(".png") || !inside(folder, file)) {
            return std::nullopt;
        }
        return prefix + std::string(file);
    };

    yyjson_mut_val* names = nullptr;
    if (json::get_object(root_obj, "name", names) != json::Field::Ok) {
        error = "style.json: 'name' must be an object of texts by language";
        return std::nullopt;
    }
    {
        std::size_t idx = 0;
        std::size_t max = 0;
        yyjson_mut_val* key = nullptr;
        yyjson_mut_val* val = nullptr;
        yyjson_mut_obj_foreach(names, idx, max, key, val) {
            const std::string_view lang(yyjson_mut_get_str(key), yyjson_mut_get_len(key));
            if (!yyjson_mut_is_str(val) || lang.size() < 2 || lang.size() > 8 || yyjson_mut_get_len(val) == 0 ||
                yyjson_mut_get_len(val) > 64 || !text::is_safe_display_text(std::string_view(yyjson_mut_get_str(val), yyjson_mut_get_len(val)), 64)) {
                error = "style.json: every name must be a text of 1 to 64 bytes";
                return std::nullopt;
            }
            style.names.emplace(std::string(lang), std::string(yyjson_mut_get_str(val), yyjson_mut_get_len(val)));
        }
    }
    if (style.names.empty()) {
        error = "style.json: 'name' is empty";
        return std::nullopt;
    }

    style.tokens = default_tokens();
    std::map<std::string, std::string, std::less<>> raw;  // CSS values, for the preview.
    yyjson_mut_val* tokens = nullptr;
    const json::Field ft = json::get_object(root_obj, "tokens", tokens);
    if (ft == json::Field::Invalid) {
        error = "style.json: 'tokens' must be an object";
        return std::nullopt;
    }
    if (ft == json::Field::Ok) {
        std::size_t idx = 0;
        std::size_t max = 0;
        yyjson_mut_val* key = nullptr;
        yyjson_mut_val* val = nullptr;
        yyjson_mut_obj_foreach(tokens, idx, max, key, val) {
            const std::string_view name(yyjson_mut_get_str(key), yyjson_mut_get_len(key));
            const TokenSpec* spec = find_token(name);
            if (spec == nullptr) {
                error = std::format("unknown token '{}'", name);
                return std::nullopt;
            }
            if (!yyjson_mut_is_str(val)) {
                error = std::format("token '{}' is not a text", name);
                return std::nullopt;
            }
            const std::string_view value(yyjson_mut_get_str(val), yyjson_mut_get_len(val));
            auto converted = convert_token(spec->type, value, fonts, images);
            if (!converted) {
                error = std::format("token '{}': '{}' is not a valid value", name, value);
                return std::nullopt;
            }
            style.tokens[std::string(name)] = std::move(*converted);
            raw[std::string(name)] = std::string(value);
        }
    }
    bool glass = false;
    const json::Field fg = json::get_bool(root_obj, "glass", glass);
    if (fg == json::Field::Invalid) {
        error = "style.json: 'glass' must be true or false";
        return std::nullopt;
    }
    style.glass = glass;
    if (!glass) {
        style.tokens["panel-blur"] = "none";
    }
    style.icon_mode = style.tokens["icon-mode"];

    yyjson_mut_val* sheets = yyjson_mut_obj_get(root_obj, "sheets");
    if (sheets != nullptr) {
        if (!yyjson_mut_is_arr(sheets) || yyjson_mut_arr_size(sheets) > style_limits::kMaxSheets) {
            error = "style.json: 'sheets' must be a list of at most 8 files";
            return std::nullopt;
        }
        std::size_t idx = 0;
        std::size_t max = 0;
        yyjson_mut_val* val = nullptr;
        yyjson_mut_arr_foreach(sheets, idx, max, val) {
            const std::string_view file =
                yyjson_mut_is_str(val) ? std::string_view(yyjson_mut_get_str(val), yyjson_mut_get_len(val))
                                       : std::string_view();
            const auto path = file.ends_with(".rcss") ? inside(folder, file) : std::nullopt;
            if (!path) {
                error = std::format("the sheet '{}' is not an .rcss file inside the style's folder", file);
                return std::nullopt;
            }
            const fs::ReadResult sheet = fs::read_file(*path, style_limits::kMaxSheetBytes);
            if (sheet.error != fs::IoError::None) {
                error = std::format("cannot read the sheet '{}': {}", file, fs::io_error_name(sheet.error));
                return std::nullopt;
            }
            std::vector<std::string> unknown;
            std::string text = substitute_tokens(sheet.data, style.tokens, &unknown);
            if (!unknown.empty()) {
                error = std::format("the sheet '{}' uses the unknown token '{}'", file, unknown.front());
                return std::nullopt;
            }
            if (!rewrite_paths(text, images, error)) {
                error = std::format("the sheet '{}': {}", file, error);
                return std::nullopt;
            }
            style.sheet += std::format("/* {}/{} */\n", style.id, file) + text + "\n";
        }
    }

    for (const std::string_view t : {"panel-solid", "text", "accent", "ok", "warn", "bad"}) {
        const auto it = raw.find(t);
        const auto c = parse_color(it != raw.end() ? std::string_view(it->second) : find_token(t)->value);
        style.preview.push_back(c ? pack(*c) : 0u);
    }
    return style;
}

void StyleLibrary::scan(const std::vector<std::filesystem::path>& roots, const FontCheck& fonts) {
    styles_.clear();
    errors_.clear();
    for (const std::filesystem::path& root : roots) {
        std::error_code ec;
        const std::filesystem::path dir = root / "styles";
        if (!std::filesystem::is_directory(dir, ec)) {
            continue;
        }
        std::vector<std::string> ids;
        for (const auto& entry : std::filesystem::directory_iterator(dir, ec)) {
            if (entry.is_directory(ec)) {
                ids.push_back(text::path_to_utf8(entry.path().filename()));
            }
        }
        std::sort(ids.begin(), ids.end());
        for (const std::string& id : ids) {
            if (styles_.size() >= style_limits::kMaxStyles) {
                errors_.push_back(id + ": too many styles");
                continue;
            }
            if (find(id) != nullptr) {
                errors_.push_back(id + ": another style already has this id");
                continue;
            }
            std::string error;
            if (auto style = load_style(root, id, fonts, error)) {
                styles_.push_back(std::move(*style));
            } else {
                errors_.push_back(id + ": " + error);
            }
        }
    }
}

const Style* StyleLibrary::find(std::string_view id) const {
    for (const Style& s : styles_) {
        if (s.id == id) {
            return &s;
        }
    }
    return nullptr;
}

}  // namespace sc::rml
