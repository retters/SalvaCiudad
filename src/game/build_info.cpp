#include "game/build_info.h"

#include "build_id.h"
#include "version.h"

namespace sc {

std::string_view build_id() {
    return SC_BUILD_ID;
}

std::string_view full_version() {
    return SC_VERSION_STRING "+" SC_BUILD_ID;
}

std::string_view version_number(std::string_view full) {
    return full.substr(0, full.find('+'));
}

}  // namespace sc
