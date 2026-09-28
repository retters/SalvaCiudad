// Included by Lua's own sources through LUA_USER_H (only when compiling the
// lua library). A fixed hash seed for strings, so `pairs` walks a table in
// the same order on every machine (decision D-702). CMake cannot pass a
// function-like macro on the command line, so it lives here.
#pragma once

#define luai_makeseed(L) 0u
