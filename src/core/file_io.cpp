#include "core/file_io.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <format>
#include <system_error>

#ifdef _WIN32
#include <windows.h>
#else
#include <cerrno>
#include <fcntl.h>
#include <unistd.h>
#endif

namespace sc::fs {

namespace {

std::FILE* open_read(const std::filesystem::path& path) {
#ifdef _WIN32
    std::FILE* f = nullptr;
    return _wfopen_s(&f, path.c_str(), L"rb") == 0 ? f : nullptr;
#else
    return std::fopen(path.c_str(), "rb");
#endif
}

// Unique temporary name in the same folder, so the final rename never
// crosses volumes.
std::filesystem::path temp_path_for(const std::filesystem::path& path) {
    const auto ticks = std::chrono::steady_clock::now().time_since_epoch().count();
    std::filesystem::path temp = path;
    temp += std::format(".tmp-{:x}", static_cast<std::uint64_t>(ticks));
    return temp;
}

#ifdef _WIN32

IoError write_and_flush(const std::filesystem::path& path, std::string_view data) {
    HANDLE h = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                           FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        return IoError::OpenFailed;
    }
    IoError result = IoError::None;
    std::size_t offset = 0;
    while (offset < data.size()) {
        const std::size_t chunk = std::min<std::size_t>(data.size() - offset, 1u << 30);
        DWORD written = 0;
        if (!WriteFile(h, data.data() + offset, static_cast<DWORD>(chunk), &written, nullptr) ||
            written != chunk) {
            result = IoError::WriteFailed;
            break;
        }
        offset += chunk;
    }
    if (result == IoError::None && !FlushFileBuffers(h)) {
        result = IoError::FlushFailed;
    }
    if (!CloseHandle(h) && result == IoError::None) {
        result = IoError::WriteFailed;
    }
    return result;
}

bool replace_file(const std::filesystem::path& from, const std::filesystem::path& to) {
    return MoveFileExW(from.c_str(), to.c_str(),
                       MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
}

#else

IoError write_and_flush(const std::filesystem::path& path, std::string_view data) {
    const int fd = ::open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0644);
    if (fd < 0) {
        return IoError::OpenFailed;
    }
    IoError result = IoError::None;
    std::size_t offset = 0;
    while (offset < data.size()) {
        const ssize_t n = ::write(fd, data.data() + offset, data.size() - offset);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            result = IoError::WriteFailed;
            break;
        }
        offset += static_cast<std::size_t>(n);
    }
    if (result == IoError::None && ::fsync(fd) != 0) {
        result = IoError::FlushFailed;
    }
    if (::close(fd) != 0 && result == IoError::None) {
        result = IoError::WriteFailed;
    }
    return result;
}

bool replace_file(const std::filesystem::path& from, const std::filesystem::path& to) {
    if (::rename(from.c_str(), to.c_str()) != 0) {
        return false;
    }
    // Make the rename itself durable.
    const int dir_fd = ::open(to.parent_path().empty() ? "." : to.parent_path().c_str(),
                              O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (dir_fd >= 0) {
        (void)::fsync(dir_fd);
        (void)::close(dir_fd);
    }
    return true;
}

#endif

}  // namespace

std::string_view io_error_name(IoError error) {
    switch (error) {
        case IoError::None: return "none";
        case IoError::NotFound: return "not found";
        case IoError::TooLarge: return "too large";
        case IoError::OpenFailed: return "open failed";
        case IoError::ReadFailed: return "read failed";
        case IoError::WriteFailed: return "write failed";
        case IoError::FlushFailed: return "flush failed";
        case IoError::ReplaceFailed: return "replace failed";
        case IoError::VerifyFailed: return "verify failed";
    }
    return "unknown";
}

ReadResult read_file(const std::filesystem::path& path, std::size_t max_bytes) {
    ReadResult result;
    std::error_code ec;
    const auto status = std::filesystem::status(path, ec);
    if (ec || !std::filesystem::is_regular_file(status)) {
        result.error = std::filesystem::exists(status) ? IoError::OpenFailed : IoError::NotFound;
        return result;
    }
    const std::uintmax_t size = std::filesystem::file_size(path, ec);
    if (ec) {
        result.error = IoError::ReadFailed;
        return result;
    }
    if (size > max_bytes) {
        result.error = IoError::TooLarge;
        return result;
    }
    std::FILE* f = open_read(path);
    if (f == nullptr) {
        result.error = IoError::OpenFailed;
        return result;
    }
    // Read up to one byte past the limit to catch a file that grew meanwhile.
    result.data.resize(static_cast<std::size_t>(size) + 1);
    const std::size_t n = std::fread(result.data.data(), 1, result.data.size(), f);
    const bool failed = std::ferror(f) != 0;
    std::fclose(f);
    if (failed) {
        result.error = IoError::ReadFailed;
        result.data.clear();
        return result;
    }
    if (n > max_bytes) {
        result.error = IoError::TooLarge;
        result.data.clear();
        return result;
    }
    result.data.resize(n);
    return result;
}

IoError write_file_atomic(const std::filesystem::path& path, std::string_view data,
                          const VerifyFn& verify) {
    const auto temp = temp_path_for(path);
    std::error_code ec;
    IoError error = write_and_flush(temp, data);
    if (error == IoError::None) {
        const ReadResult back = read_file(temp, data.size());
        if (back.error != IoError::None || back.data != data || (verify && !verify(back.data))) {
            error = IoError::VerifyFailed;
        }
    }
    if (error == IoError::None && !replace_file(temp, path)) {
        error = IoError::ReplaceFailed;
    }
    if (error != IoError::None) {
        std::filesystem::remove(temp, ec);
    }
    return error;
}

std::filesystem::path quarantine_file(const std::filesystem::path& path) {
    const auto now = std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now());
    const std::string stamp = std::format("{:%Y%m%d-%H%M%S}", now);
    std::error_code ec;
    for (int attempt = 0; attempt < 100; ++attempt) {
        std::filesystem::path target = path;
        target += attempt == 0 ? std::format(".bad-{}", stamp) : std::format(".bad-{}-{}", stamp, attempt);
        if (std::filesystem::exists(target, ec)) {
            continue;
        }
        std::filesystem::rename(path, target, ec);
        if (!ec) {
            return target;
        }
        return {};
    }
    return {};
}

}  // namespace sc::fs
