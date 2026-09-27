// File input and output for user data: size-limited reads, atomic writes
// with verification, and quarantine of damaged files.
#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <string>
#include <string_view>

namespace sc::fs {

enum class IoError : std::uint8_t {
    None,
    NotFound,
    TooLarge,
    OpenFailed,
    ReadFailed,
    WriteFailed,
    FlushFailed,
    ReplaceFailed,
    VerifyFailed,
};

[[nodiscard]] std::string_view io_error_name(IoError error);

struct ReadResult {
    IoError error = IoError::None;
    std::string data;
};

// Reads a whole file. Fails with TooLarge, without reading it, if the file is
// bigger than `max_bytes`.
[[nodiscard]] ReadResult read_file(const std::filesystem::path& path, std::size_t max_bytes);

// Returns true if the bytes read back from disk are acceptable.
using VerifyFn = std::function<bool(std::string_view)>;

// Writes `data` to a temporary file next to `path`, flushes it to disk,
// reads it back, compares it and runs `verify` (if given), and only then
// replaces `path`. The original file is untouched on any failure.
[[nodiscard]] IoError write_file_atomic(const std::filesystem::path& path, std::string_view data,
                                        const VerifyFn& verify = {});

// Renames a damaged file to `<name>.bad-YYYYMMDD-HHMMSS[-n]` in the same
// folder, never deleting it. Returns the new path, or an empty path on
// failure.
[[nodiscard]] std::filesystem::path quarantine_file(const std::filesystem::path& path);

}  // namespace sc::fs
