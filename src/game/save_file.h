// Saved games (section 5.5): a readable JSON header followed by tagged
// chunks, each with its length and a CRC32. Unknown chunks are kept. The
// body of the game is the simulation's own serialization, the same bytes
// the network will send to players who join a game already started.
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace sc::save {

inline constexpr std::uint32_t kSchemaVersion = 1;
inline constexpr std::size_t kMaxFileBytes = 1024u * 1024u * 1024u;  // 1 GiB.
inline constexpr std::size_t kMaxHeaderBytes = 256u * 1024u;
inline constexpr std::size_t kMaxChunks = 64;
inline constexpr const char* kExtension = ".scsave";

// Compression of a chunk: zstd when it makes the chunk smaller (section 5.5).
enum class Compression : std::uint8_t { None = 0, Zstd = 1 };

struct ModRef {
    std::string id;
    std::string version;
    std::string hash;  // Hex.
    bool operator==(const ModRef&) const = default;
};

struct Header {
    std::string name;          // Shown in the load list.
    std::string game_version;  // The version that wrote it.
    std::string saved_at;      // ISO 8601, local time.
    std::string mode = "single";
    std::uint32_t players = 1;
    std::uint32_t rules_version = 0;  // sim::kGameRulesVersion.
    std::uint64_t content_hash = 0;
    std::uint64_t seed = 0;
    std::uint64_t tick = 0;
    std::uint32_t population = 0;  // Of the local player, for the list.
    std::vector<ModRef> mods;
    bool operator==(const Header&) const = default;
};

struct Chunk {
    std::array<char, 4> tag{};
    std::vector<std::uint8_t> data;
    bool operator==(const Chunk&) const = default;
};

struct SaveData {
    Header header;
    std::vector<Chunk> chunks;
    [[nodiscard]] const Chunk* find(std::string_view tag) const;
    // Replaces the chunk with `tag`, or adds it.
    void put(std::string_view tag, std::vector<std::uint8_t> data);
};

enum class LoadError : std::uint8_t { None, Io, TooLarge, NotASave, NewerSchema, BadHeader, Corrupt };

[[nodiscard]] std::uint32_t crc32(std::span<const std::uint8_t> data);

[[nodiscard]] std::vector<std::uint8_t> encode(const SaveData& save);
// Reads untrusted bytes. With `header_only`, stops after the header.
[[nodiscard]] LoadError decode(std::span<const std::uint8_t> bytes, SaveData& out, bool header_only = false);

// Atomic write, verified by decoding what was written.
[[nodiscard]] bool write_file(const std::filesystem::path& file, const SaveData& save);
[[nodiscard]] LoadError read_file(const std::filesystem::path& file, SaveData& out, bool header_only = false);

// A save file name from a name typed by the player: letters, digits,
// spaces, dashes and underscores; anything else becomes an underscore.
[[nodiscard]] std::string file_stem(std::string_view name);

struct Entry {
    std::filesystem::path file;
    Header header;
    bool readable = false;  // False: damaged, or from another version.
};
// Saves in a folder, newest first (by the time in their header).
[[nodiscard]] std::vector<Entry> list(const std::filesystem::path& dir);

}  // namespace sc::save
