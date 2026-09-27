#include "game/replay_file.h"

#include "core/file_io.h"
#include "core/log.h"

namespace sc {

bool save_replay_file(const std::filesystem::path& file, const sim::Replay& replay) {
    const std::vector<std::uint8_t> bytes = sim::encode_replay(replay);
    const std::string_view view(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    const fs::IoError err = fs::write_file_atomic(file, view);
    if (err != fs::IoError::None) {
        log::error("replay: save failed ({})", fs::io_error_name(err));
        return false;
    }
    return true;
}

bool load_replay_file(const std::filesystem::path& file, sim::Replay& out, std::string& error) {
    const fs::ReadResult r = fs::read_file(file, kMaxReplayFileBytes);
    if (r.error != fs::IoError::None) {
        error = std::string(fs::io_error_name(r.error));
        return false;
    }
    return sim::decode_replay({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()}, out, error);
}

}  // namespace sc
