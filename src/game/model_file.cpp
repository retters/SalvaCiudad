#include "game/model_file.h"

#include <string>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"

namespace sc {

std::optional<render::ModelData> load_model_file(const std::filesystem::path& file) {
    const std::string name = text::path_to_utf8(file.filename());
    const fs::ReadResult r = fs::read_file(file, render::model_limits::kMaxFileBytes);
    if (r.error != fs::IoError::None) {
        log::warn("models: cannot read {} ({})", name, fs::io_error_name(r.error));
        return std::nullopt;
    }
    render::ModelLoadResult model =
        render::load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
    if (!model.ok) {
        log::warn("models: {} rejected: {}", name, model.error);
        return std::nullopt;
    }
    return std::move(model.model);
}

}  // namespace sc
