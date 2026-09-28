// Which build of the game this is (decision D-3321).
#pragma once

#include <string_view>

namespace sc {

// A hash of the sources this build comes from, 12 hex digits.
[[nodiscard]] std::string_view build_id();
// The version number and the build, as "0.20.0+1a2b3c4d5e6f": what the
// lobby compares, so only the very same build can play together.
[[nodiscard]] std::string_view full_version();
// The version number alone, from a full version ("0.20.0+..." gives "0.20.0").
[[nodiscard]] std::string_view version_number(std::string_view full);

}  // namespace sc
