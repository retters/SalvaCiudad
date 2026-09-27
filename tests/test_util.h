// Helpers shared by the tests. Tests only touch files inside their own
// temporary folders, never the user's real data.
#pragma once

#include <chrono>
#include <filesystem>
#include <format>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>

#include "core/file_io.h"

namespace sc::test {

class TempDir {
public:
    TempDir() {
        static int counter = 0;
        const auto ticks = std::chrono::steady_clock::now().time_since_epoch().count();
        path_ = std::filesystem::temp_directory_path() /
                std::format("salvaciudad-test-{:x}-{}", static_cast<unsigned long long>(ticks), ++counter);
        std::filesystem::create_directories(path_);
    }
    ~TempDir() {
        std::error_code ec;
        std::filesystem::remove_all(path_, ec);
    }
    TempDir(const TempDir&) = delete;
    TempDir& operator=(const TempDir&) = delete;

    [[nodiscard]] const std::filesystem::path& path() const { return path_; }
    [[nodiscard]] std::filesystem::path operator/(std::string_view name) const { return path_ / name; }

    // Number of entries directly inside the folder.
    [[nodiscard]] int count_entries() const {
        int n = 0;
        for ([[maybe_unused]] const auto& e : std::filesystem::directory_iterator(path_)) {
            ++n;
        }
        return n;
    }

private:
    std::filesystem::path path_;
};

inline void write_text(const std::filesystem::path& path, std::string_view text) {
    const fs::IoError err = fs::write_file_atomic(path, text);
    if (err != fs::IoError::None) {
        throw std::runtime_error("test setup: cannot write file");
    }
}

inline std::string read_text(const std::filesystem::path& path) {
    return fs::read_file(path, 64u * 1024u * 1024u).data;
}

inline std::filesystem::path fixture(std::string_view name) {
    return std::filesystem::path(SC_TEST_FIXTURES_DIR) / name;
}

}  // namespace sc::test
