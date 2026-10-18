#include "ui/context.h"

#include <algorithm>
#include <cmath>

namespace sc::ui {

bool Input::key(SDL_Scancode k) const {
    return std::find(keys.begin(), keys.end(), k) != keys.end();
}

void Context::begin_frame(const Input& input, float width, float height, float scale, std::uint64_t now_ns,
                          float white_u, float white_v) {
    input_ = input;
    width_ = width;
    height_ = height;
    scale_ = scale;
    now_ns_ = now_ns;
    blocked_ = false;
    draw_.reset(width, height, white_u, white_v);
}

TextStyle Context::style(int design_px, FontRole role) const {
    return {role, std::max(6, static_cast<int>(std::lround(static_cast<float>(design_px) * scale_)))};
}

}  // namespace sc::ui
