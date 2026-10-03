// Reads the game's models from disk.
#pragma once

#include <filesystem>
#include <optional>

#include "render/model.h"

namespace sc {

// Reads and validates one .glb from disk (models only come from the game's
// data folder, decision D-302).
[[nodiscard]] std::optional<render::ModelData> load_model_file(const std::filesystem::path& file);

}  // namespace sc
