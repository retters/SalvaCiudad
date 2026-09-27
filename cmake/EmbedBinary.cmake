# Writes a C++ header that embeds a file as a byte array.
# Usage: cmake -DINPUT=<file> -DOUTPUT=<header> -DSYMBOL=<name> -P EmbedBinary.cmake
file(READ "${INPUT}" content HEX)
string(LENGTH "${content}" hex_length)
math(EXPR byte_count "${hex_length} / 2")
string(REGEX REPLACE "([0-9a-f][0-9a-f])" "0x\\1," bytes "${content}")
# Break the list into lines of 16 bytes to keep the header readable.
string(REGEX REPLACE "((0x[0-9a-f][0-9a-f],){16})" "\\1\n    " bytes "${bytes}")
file(WRITE "${OUTPUT}"
"// Generated from ${INPUT}. Do not edit.
#pragma once

#include <cstddef>
#include <cstdint>

inline constexpr std::uint8_t ${SYMBOL}[] = {
    ${bytes}
};
inline constexpr std::size_t ${SYMBOL}_size = ${byte_count};
")
