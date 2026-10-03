#include "game/menu_backgrounds.h"

#include <algorithm>
#include <charconv>

#include "core/file_io.h"
#include "core/json.h"
#include "core/log.h"
#include "core/text.h"

namespace sc::menu_backgrounds {

namespace {

constexpr std::int64_t kSchemaVersion = 1;

}  // namespace

bool parse(std::string_view text, std::vector<std::uint64_t>& seeds, std::string& error) {
    const json::ParseResult parsed = json::parse_object(text);
    if (parsed.error != json::ParseError::None) {
        error = "not valid JSON: " + parsed.message;
        return false;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
    std::int64_t schema = 0;
    if (json::get_int(root, "schemaVersion", 1, 1000, schema) != json::Field::Ok || schema != kSchemaVersion) {
        error = "unknown schemaVersion";
        return false;
    }
    yyjson_mut_val* list = yyjson_mut_obj_get(root, "seeds");
    if (list == nullptr || !yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) > kMaxSeeds) {
        error = "seeds is missing, not a list or too long";
        return false;
    }
    std::vector<std::uint64_t> out;
    std::size_t idx = 0, max = 0;
    yyjson_mut_val* item = nullptr;
    yyjson_mut_arr_foreach(list, idx, max, item) {
        const char* s = yyjson_mut_get_str(item);
        const std::size_t n = yyjson_mut_get_len(item);
        std::uint64_t seed = 0;
        if (s == nullptr || n == 0 || n > 20) {
            error = "a seed is not a string of digits";
            return false;
        }
        const auto [p, ec] = std::from_chars(s, s + n, seed);
        if (ec != std::errc{} || p != s + n) {
            error = "a seed is not a number of 64 bits";
            return false;
        }
        if (std::find(out.begin(), out.end(), seed) == out.end()) {
            out.push_back(seed);
        }
    }
    seeds = std::move(out);
    return true;
}

std::string to_json(const std::vector<std::uint64_t>& seeds) {
    json::MutDoc doc = json::new_object_doc();
    yyjson_mut_val* root = yyjson_mut_doc_get_root(doc.get());
    (void)json::set_int(doc.get(), root, "schemaVersion", kSchemaVersion);
    yyjson_mut_val* list = yyjson_mut_obj_add_arr(doc.get(), root, "seeds");
    for (const std::uint64_t seed : seeds) {
        const std::string s = std::to_string(seed);
        (void)yyjson_mut_arr_add_strncpy(doc.get(), list, s.data(), s.size());
    }
    return json::write_pretty(doc.get());
}

std::vector<std::uint64_t> load(const std::filesystem::path& file) {
    std::vector<std::uint64_t> seeds;
    const fs::ReadResult r = fs::read_file(file, kMaxFileBytes);
    if (r.error == fs::IoError::NotFound) {
        return seeds;
    }
    std::string error;
    if (r.error != fs::IoError::None) {
        log::warn("menu: cannot read {} ({})", text::path_to_utf8(file), fs::io_error_name(r.error));
    } else if (!parse(r.data, seeds, error)) {
        log::warn("menu: {} ignored: {}", text::path_to_utf8(file), error);
        seeds.clear();
    }
    return seeds;
}

bool add(const std::filesystem::path& file, std::uint64_t seed) {
    std::vector<std::uint64_t> seeds = load(file);
    if (std::find(seeds.begin(), seeds.end(), seed) != seeds.end()) {
        return true;
    }
    if (seeds.size() >= kMaxSeeds) {
        return false;
    }
    seeds.push_back(seed);
    return fs::write_file_atomic(file, to_json(seeds)) == fs::IoError::None;
}

std::uint64_t choose(const std::vector<std::uint64_t>& shipped, const std::vector<std::uint64_t>& user,
                     std::uint64_t pick) {
    const std::size_t total = shipped.size() + user.size();
    if (total == 0) {
        return kFallbackSeed;
    }
    const auto i = static_cast<std::size_t>(pick % total);
    return i < shipped.size() ? shipped[i] : user[i - shipped.size()];
}

sim::MapSettings settings_for(std::uint64_t seed) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = sim::MapSize::Small;
    s.relief = sim::Relief::Gentle;
    return s;
}

}  // namespace sc::menu_backgrounds
