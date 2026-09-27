// Replays on disk. The simulation itself never touches files (section 7.3);
// this is the game side that stores and reads them.
#pragma once

#include <filesystem>
#include <string>

#include "sim/simulation.h"

namespace sc {

inline constexpr std::size_t kMaxReplayFileBytes = 256u * 1024u * 1024u;

// Atomic write. Returns false (and logs) on failure.
bool save_replay_file(const std::filesystem::path& file, const sim::Replay& replay);
// Size-limited, validated read.
bool load_replay_file(const std::filesystem::path& file, sim::Replay& out, std::string& error);

}  // namespace sc
