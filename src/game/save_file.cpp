#include "game/save_file.h"

#include <algorithm>
#include <cstring>
#include <format>
#include <system_error>

#include "core/file_io.h"
#include "core/json.h"
#include "core/log.h"
#include "core/text.h"

namespace sc::save {

namespace {

constexpr char kMagic[8] = {'S', 'C', 'S', 'A', 'V', 'E', '\r', '\n'};

void put_u32(std::vector<std::uint8_t>& out, std::uint32_t v) {
    for (int i = 0; i < 4; ++i) {
        out.push_back(static_cast<std::uint8_t>(v >> (8 * i)));
    }
}

bool get_u32(std::span<const std::uint8_t> in, std::size_t& pos, std::uint32_t& v) {
    if (in.size() - pos < 4) {
        return false;
    }
    v = 0;
    for (int i = 0; i < 4; ++i) {
        v |= static_cast<std::uint32_t>(in[pos + static_cast<std::size_t>(i)]) << (8 * i);
    }
    pos += 4;
    return true;
}

std::string hex64(std::uint64_t v) {
    return std::format("{:016x}", v);
}

bool parse_hex64(std::string_view s, std::uint64_t& out) {
    if (s.empty() || s.size() > 16) {
        return false;
    }
    out = 0;
    for (const char c : s) {
        int d = 0;
        if (c >= '0' && c <= '9') {
            d = c - '0';
        } else if (c >= 'a' && c <= 'f') {
            d = c - 'a' + 10;
        } else {
            return false;
        }
        out = (out << 4) | static_cast<std::uint64_t>(d);
    }
    return true;
}

std::string header_json(const Header& h) {
    json::MutDoc doc = json::new_object_doc();
    if (!doc) {
        return {};
    }
    yyjson_mut_doc* d = doc.get();
    yyjson_mut_val* root = yyjson_mut_doc_get_root(d);
    bool ok = json::set_int(d, root, "schemaVersion", kSchemaVersion);
    ok = ok && json::set_string(d, root, "name", h.name);
    ok = ok && json::set_string(d, root, "gameVersion", h.game_version);
    ok = ok && json::set_string(d, root, "savedAt", h.saved_at);
    ok = ok && json::set_string(d, root, "mode", h.mode);
    ok = ok && json::set_int(d, root, "players", h.players);
    ok = ok && json::set_int(d, root, "rulesVersion", h.rules_version);
    ok = ok && json::set_string(d, root, "contentHash", hex64(h.content_hash));
    ok = ok && json::set_string(d, root, "seed", hex64(h.seed));
    ok = ok && json::set_string(d, root, "tick", hex64(h.tick));
    ok = ok && json::set_int(d, root, "population", h.population);
    yyjson_mut_val* mods = yyjson_mut_arr(d);
    ok = ok && mods != nullptr && yyjson_mut_obj_add_val(d, root, "mods", mods);
    for (const ModRef& m : h.mods) {
        yyjson_mut_val* o = yyjson_mut_obj(d);
        ok = ok && o != nullptr && json::set_string(d, o, "id", m.id) && json::set_string(d, o, "version", m.version) &&
             json::set_string(d, o, "hash", m.hash) && yyjson_mut_arr_append(mods, o);
    }
    return ok ? json::write_pretty(d) : std::string{};
}

bool parse_header(std::string_view text, Header& h, std::uint32_t& schema) {
    json::ParseResult parsed = json::parse_object(text);
    if (parsed.error != json::ParseError::None) {
        return false;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
    std::int64_t v = 0;
    if (json::get_int(root, "schemaVersion", 1, 1'000'000, v) != json::Field::Ok) {
        return false;
    }
    schema = static_cast<std::uint32_t>(v);
    if (schema > kSchemaVersion) {
        return true;  // The caller reports a newer file; nothing else is trusted.
    }
    std::string s;
    const auto str = [&](const char* key, std::size_t max, std::string& out) {
        return json::get_string(root, key, max, out) == json::Field::Ok;
    };
    const auto hex = [&](const char* key, std::uint64_t& out) {
        return json::get_string(root, key, 16, s) == json::Field::Ok && parse_hex64(s, out);
    };
    if (!str("name", 200, h.name) || !str("gameVersion", 40, h.game_version) || !str("savedAt", 40, h.saved_at) ||
        !str("mode", 20, h.mode) || !hex("contentHash", h.content_hash) || !hex("seed", h.seed) || !hex("tick", h.tick)) {
        return false;
    }
    if (json::get_int(root, "players", 1, 12, v) != json::Field::Ok) {
        return false;
    }
    h.players = static_cast<std::uint32_t>(v);
    if (json::get_int(root, "rulesVersion", 0, 1'000'000, v) != json::Field::Ok) {
        return false;
    }
    h.rules_version = static_cast<std::uint32_t>(v);
    if (json::get_int(root, "population", 0, 1'000'000, v) != json::Field::Ok) {
        return false;
    }
    h.population = static_cast<std::uint32_t>(v);
    h.mods.clear();
    yyjson_mut_val* mods = yyjson_mut_obj_get(root, "mods");
    if (mods == nullptr || !yyjson_mut_is_arr(mods) || yyjson_mut_arr_size(mods) > 1000) {
        return false;
    }
    std::size_t idx = 0, max = 0;
    yyjson_mut_val* item = nullptr;
    yyjson_mut_arr_foreach(mods, idx, max, item) {
        ModRef m;
        if (!yyjson_mut_is_obj(item) || json::get_string(item, "id", 200, m.id) != json::Field::Ok ||
            json::get_string(item, "version", 40, m.version) != json::Field::Ok ||
            json::get_string(item, "hash", 16, m.hash) != json::Field::Ok) {
            return false;
        }
        h.mods.push_back(std::move(m));
    }
    return true;
}

}  // namespace

std::uint32_t crc32(std::span<const std::uint8_t> data) {
    static const auto table = [] {
        std::array<std::uint32_t, 256> t{};
        for (std::uint32_t i = 0; i < 256; ++i) {
            std::uint32_t c = i;
            for (int k = 0; k < 8; ++k) {
                c = (c & 1u) != 0 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            }
            t[i] = c;
        }
        return t;
    }();
    std::uint32_t c = 0xFFFFFFFFu;
    for (const std::uint8_t b : data) {
        c = table[(c ^ b) & 0xFFu] ^ (c >> 8);
    }
    return c ^ 0xFFFFFFFFu;
}

const Chunk* SaveData::find(std::string_view tag) const {
    for (const Chunk& c : chunks) {
        if (tag.size() == 4 && std::memcmp(c.tag.data(), tag.data(), 4) == 0) {
            return &c;
        }
    }
    return nullptr;
}

void SaveData::put(std::string_view tag, std::vector<std::uint8_t> data) {
    for (Chunk& c : chunks) {
        if (tag.size() == 4 && std::memcmp(c.tag.data(), tag.data(), 4) == 0) {
            c.data = std::move(data);
            return;
        }
    }
    Chunk c;
    std::memcpy(c.tag.data(), tag.data(), std::min<std::size_t>(4, tag.size()));
    c.data = std::move(data);
    chunks.push_back(std::move(c));
}

std::vector<std::uint8_t> encode(const SaveData& save) {
    std::vector<std::uint8_t> out(std::begin(kMagic), std::end(kMagic));
    put_u32(out, kSchemaVersion);
    const std::string header = header_json(save.header);
    put_u32(out, static_cast<std::uint32_t>(header.size()));
    out.insert(out.end(), header.begin(), header.end());
    put_u32(out, static_cast<std::uint32_t>(save.chunks.size()));
    for (const Chunk& c : save.chunks) {
        out.insert(out.end(), c.tag.begin(), c.tag.end());
        out.push_back(static_cast<std::uint8_t>(Compression::None));
        put_u32(out, static_cast<std::uint32_t>(c.data.size()));  // Size when unpacked.
        put_u32(out, static_cast<std::uint32_t>(c.data.size()));  // Size stored.
        put_u32(out, crc32(c.data));
        out.insert(out.end(), c.data.begin(), c.data.end());
    }
    return out;
}

LoadError decode(std::span<const std::uint8_t> bytes, SaveData& out, bool header_only) {
    if (bytes.size() > kMaxFileBytes) {
        return LoadError::TooLarge;
    }
    if (bytes.size() < sizeof(kMagic) + 8 || std::memcmp(bytes.data(), kMagic, sizeof(kMagic)) != 0) {
        return LoadError::NotASave;
    }
    std::size_t pos = sizeof(kMagic);
    std::uint32_t schema = 0;
    std::uint32_t header_len = 0;
    if (!get_u32(bytes, pos, schema) || schema == 0) {
        return LoadError::NotASave;
    }
    if (schema > kSchemaVersion) {
        return LoadError::NewerSchema;
    }
    if (!get_u32(bytes, pos, header_len) || header_len > kMaxHeaderBytes || bytes.size() - pos < header_len) {
        return LoadError::BadHeader;
    }
    SaveData result;
    std::uint32_t header_schema = 0;
    const std::string_view text(reinterpret_cast<const char*>(bytes.data() + pos), header_len);
    if (!parse_header(text, result.header, header_schema) || header_schema != schema) {
        return LoadError::BadHeader;
    }
    pos += header_len;
    if (header_only) {
        out = std::move(result);
        return LoadError::None;
    }
    std::uint32_t count = 0;
    if (!get_u32(bytes, pos, count) || count > kMaxChunks) {
        return LoadError::Corrupt;
    }
    for (std::uint32_t i = 0; i < count; ++i) {
        Chunk c;
        if (bytes.size() - pos < 5) {
            return LoadError::Corrupt;
        }
        std::memcpy(c.tag.data(), bytes.data() + pos, 4);
        const std::uint8_t compression = bytes[pos + 4];
        pos += 5;
        std::uint32_t raw = 0, stored = 0, crc = 0;
        if (!get_u32(bytes, pos, raw) || !get_u32(bytes, pos, stored) || !get_u32(bytes, pos, crc) ||
            bytes.size() - pos < stored) {
            return LoadError::Corrupt;
        }
        const std::span<const std::uint8_t> data = bytes.subspan(pos, stored);
        pos += stored;
        if (crc32(data) != crc) {
            return LoadError::Corrupt;
        }
        if (compression != static_cast<std::uint8_t>(Compression::None) || raw != stored) {
            return LoadError::Corrupt;  // Nothing else can be read yet.
        }
        c.data.assign(data.begin(), data.end());
        result.chunks.push_back(std::move(c));
    }
    if (pos != bytes.size()) {
        return LoadError::Corrupt;
    }
    out = std::move(result);
    return LoadError::None;
}

bool write_file(const std::filesystem::path& file, const SaveData& save) {
    const std::vector<std::uint8_t> bytes = encode(save);
    std::error_code ec;
    std::filesystem::create_directories(file.parent_path(), ec);
    const fs::IoError err = fs::write_file_atomic(
        file, std::string_view(reinterpret_cast<const char*>(bytes.data()), bytes.size()), [](std::string_view back) {
            SaveData check;
            return decode({reinterpret_cast<const std::uint8_t*>(back.data()), back.size()}, check) == LoadError::None;
        });
    if (err != fs::IoError::None) {
        log::error("save: cannot write the game: {}", fs::io_error_name(err));
        return false;
    }
    return true;
}

LoadError read_file(const std::filesystem::path& file, SaveData& out, bool header_only) {
    const fs::ReadResult r = fs::read_file(file, kMaxFileBytes);
    if (r.error == fs::IoError::TooLarge) {
        return LoadError::TooLarge;
    }
    if (r.error != fs::IoError::None) {
        return LoadError::Io;
    }
    return decode({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()}, out, header_only);
}

std::string file_stem(std::string_view name) {
    std::string out;
    for (const char c : name) {
        const bool plain = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' ||
                           c == '_' || c == ' ';
        out += plain ? c : '_';
        if (out.size() >= 60) {
            break;
        }
    }
    while (!out.empty() && (out.back() == ' ' || out.back() == '.')) {
        out.pop_back();
    }
    return out.empty() ? std::string("save") : out;
}

std::vector<Entry> list(const std::filesystem::path& dir) {
    std::vector<Entry> out;
    std::error_code ec;
    for (auto it = std::filesystem::directory_iterator(dir, ec); !ec && it != std::filesystem::directory_iterator();
         it.increment(ec)) {
        if (!it->is_regular_file(ec) || it->path().extension() != kExtension) {
            continue;
        }
        Entry e;
        e.file = it->path();
        SaveData data;
        e.readable = read_file(e.file, data, true) == LoadError::None;
        e.header = std::move(data.header);
        if (!e.readable) {
            e.header.name = text::path_to_utf8(e.file.stem());
        }
        out.push_back(std::move(e));
        if (out.size() >= 500) {
            break;
        }
    }
    std::sort(out.begin(), out.end(), [](const Entry& a, const Entry& b) { return a.header.saved_at > b.header.saved_at; });
    return out;
}

}  // namespace sc::save
