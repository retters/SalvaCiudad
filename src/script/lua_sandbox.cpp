#include "script/lua_sandbox.h"

#include <algorithm>
#include <cstdlib>
#include <cstring>

extern "C" {
#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>
}

#include "core/file_io.h"
#include "core/log.h"
#include "sim/fixed.h"

namespace sc::script {

namespace {

// Note for every C callback below: Lua reports errors with longjmp, which
// skips C++ destructors. Callbacks read and check all their arguments first
// (the calls that may raise errors) and only then create C++ objects, or
// build error messages in plain buffers (decision D-702).

constexpr int kHookEvery = 1000;  // Instructions between budget checks.

LuaSandbox::Control* control(lua_State* L) {
    void* ud = nullptr;
    (void)lua_getallocf(L, &ud);
    return static_cast<LuaSandbox::Control*>(ud);
}

void* allocate(void* ud, void* ptr, std::size_t old_size, std::size_t new_size) {
    auto* c = static_cast<LuaSandbox::Control*>(ud);
    const std::size_t old_bytes = ptr != nullptr ? old_size : 0;
    if (new_size == 0) {
        std::free(ptr);
        c->used -= std::min(c->used, old_bytes);
        return nullptr;
    }
    if (new_size > old_bytes && c->used + (new_size - old_bytes) > c->limit) {
        return nullptr;  // Lua raises a memory error.
    }
    void* out = std::realloc(ptr, new_size);
    if (out != nullptr) {
        c->used = c->used - std::min(c->used, old_bytes) + new_size;
    }
    return out;
}

void count_hook(lua_State* L, lua_Debug*) {
    LuaSandbox::Control* c = control(L);
    c->spent += kHookEvery;
    if (c->spent > c->budget) {
        luaL_error(L, "the script ran too long (instruction limit)");
    }
}

int lua_print(lua_State* L) {
    const int n = lua_gettop(L);
    luaL_Buffer b;
    luaL_buffinit(L, &b);
    for (int i = 1; i <= n; ++i) {
        std::size_t len = 0;
        const char* s = luaL_tolstring(L, i, &len);
        if (i > 1) {
            luaL_addchar(&b, ' ');
        }
        luaL_addlstring(&b, s, std::min<std::size_t>(len, 1000));
        lua_pop(L, 1);
    }
    luaL_pushresult(&b);
    const char* text = lua_tostring(L, -1);
    log::info("mod {}: {}", control(L)->mod, text != nullptr ? text : "");
    return 0;
}

// Integer-only math: the parts that are deterministic on every machine.
int m_abs(lua_State* L) {
    const lua_Integer v = luaL_checkinteger(L, 1);
    lua_pushinteger(L, v < 0 ? -v : v);
    return 1;
}
int m_min(lua_State* L) {
    const int n = lua_gettop(L);
    lua_Integer v = luaL_checkinteger(L, 1);
    for (int i = 2; i <= n; ++i) {
        v = std::min(v, luaL_checkinteger(L, i));
    }
    lua_pushinteger(L, v);
    return 1;
}
int m_max(lua_State* L) {
    const int n = lua_gettop(L);
    lua_Integer v = luaL_checkinteger(L, 1);
    for (int i = 2; i <= n; ++i) {
        v = std::max(v, luaL_checkinteger(L, i));
    }
    lua_pushinteger(L, v);
    return 1;
}
int m_isqrt(lua_State* L) {
    const lua_Integer v = luaL_checkinteger(L, 1);
    luaL_argcheck(L, v >= 0, 1, "negative");
    lua_pushinteger(L, static_cast<lua_Integer>(sim::isqrt(static_cast<std::uint64_t>(v))));
    return 1;
}
// sin and cos of whole degrees, times 10000.
int m_sin(lua_State* L) {
    const lua_Integer deg = luaL_checkinteger(L, 1);
    const auto a = sim::Angle::from_degrees(static_cast<std::int32_t>(((deg % 360) + 360) % 360));
    lua_pushinteger(L, static_cast<lua_Integer>((static_cast<std::int64_t>(sim::sin(a).raw()) * 10000) / 65536));
    return 1;
}
int m_cos(lua_State* L) {
    const lua_Integer deg = luaL_checkinteger(L, 1);
    const auto a = sim::Angle::from_degrees(static_cast<std::int32_t>(((deg % 360) + 360) % 360));
    lua_pushinteger(L, static_cast<lua_Integer>((static_cast<std::int64_t>(sim::cos(a).raw()) * 10000) / 65536));
    return 1;
}

int open_math(lua_State* L) {
    static const luaL_Reg kFunctions[] = {{"abs", m_abs},   {"min", m_min},       {"max", m_max},
                                          {"isqrt", m_isqrt}, {"sin_deg", m_sin}, {"cos_deg", m_cos},
                                          {nullptr, nullptr}};
    luaL_newlib(L, kFunctions);
    lua_pushinteger(L, LUA_MAXINTEGER);
    lua_setfield(L, -2, "maxinteger");
    lua_pushinteger(L, LUA_MININTEGER);
    lua_setfield(L, -2, "mininteger");
    return 1;
}

// require "name" loads scripts/name.lua (dots become folders) of the mod,
// once; the result is cached in package-like table _LOADED.
int lua_require(lua_State* L) {
    const char* name = luaL_checkstring(L, 1);
    if (!is_valid_module_name(name)) {
        return luaL_error(L, "require: invalid module name");
    }
    lua_getfield(L, LUA_REGISTRYINDEX, "sc_loaded");
    lua_getfield(L, -1, name);
    if (!lua_isnil(L, -1)) {
        return 1;
    }
    lua_pop(L, 1);
    char path_text[160];
    std::size_t len = std::strlen(name);
    if (len > 120) {
        return luaL_error(L, "require: name too long");
    }
    for (std::size_t i = 0; i < len; ++i) {
        path_text[i] = name[i] == '.' ? '/' : name[i];
    }
    std::memcpy(path_text + len, ".lua", 5);
    int status = 0;
    {
        // A scope, so the C++ objects are gone before any Lua error.
        const fs::ReadResult r = fs::read_file(control(L)->scripts_dir / path_text, 1024u * 1024u);
        if (r.error != fs::IoError::None) {
            status = -1;
        } else {
            status = luaL_loadbufferx(L, r.data.data(), r.data.size(), name, "t");
        }
    }
    if (status == -1) {
        return luaL_error(L, "require: module '%s' not found in the mod", name);
    }
    if (status != LUA_OK) {
        return lua_error(L);
    }
    lua_call(L, 0, 1);
    if (lua_isnil(L, -1)) {
        lua_pop(L, 1);
        lua_pushboolean(L, 1);
    }
    lua_pushvalue(L, -1);
    lua_setfield(L, -3, name);
    return 1;
}

int traceback(lua_State* L) {
    const char* msg = lua_tostring(L, 1);
    luaL_traceback(L, L, msg != nullptr ? msg : "(error object is not a string)", 1);
    return 1;
}

}  // namespace

bool is_valid_module_name(std::string_view name) {
    if (name.empty() || name.size() > 100 || name.front() == '.' || name.back() == '.' ||
        name.find("..") != std::string_view::npos) {
        return false;
    }
    return std::all_of(name.begin(), name.end(),
                       [](char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '.'; });
}

LuaSandbox::~LuaSandbox() {
    if (L_ != nullptr) {
        lua_close(L_);
    }
}

bool LuaSandbox::open(std::string_view mod_id, const std::filesystem::path& mod_dir, std::string_view source,
                      std::string& error, const SandboxLimits& limits) {
    limits_ = limits;
    mod_ = std::string(mod_id);
    control_.limit = limits.memory_bytes;
    control_.budget = limits.instructions_per_call;
    control_.scripts_dir = mod_dir / "scripts";
    control_.mod = mod_;
    L_ = lua_newstate(allocate, &control_);
    if (L_ == nullptr) {
        error = "cannot create the Lua state";
        return false;
    }
    luaL_requiref(L_, LUA_GNAME, luaopen_base, 1);
    luaL_requiref(L_, LUA_STRLIBNAME, luaopen_string, 1);
    luaL_requiref(L_, LUA_TABLIBNAME, luaopen_table, 1);
    luaL_requiref(L_, LUA_UTF8LIBNAME, luaopen_utf8, 1);
    luaL_requiref(L_, LUA_MATHLIBNAME, open_math, 1);
    lua_pop(L_, 5);
    // No loading of code or files from the base library.
    for (const char* name : {"dofile", "loadfile", "load", "collectgarbage"}) {
        lua_pushnil(L_);
        lua_setglobal(L_, name);
    }
    lua_pushcfunction(L_, lua_print);
    lua_setglobal(L_, "print");
    lua_pushcfunction(L_, lua_require);
    lua_setglobal(L_, "require");
    lua_newtable(L_);
    lua_setfield(L_, LUA_REGISTRYINDEX, "sc_loaded");
    lua_sethook(L_, count_hook, LUA_MASKCOUNT, kHookEvery);

    const std::string chunk = "@" + mod_ + "/scripts/main.lua";
    if (luaL_loadbufferx(L_, source.data(), source.size(), chunk.c_str(), "t") != LUA_OK) {
        const char* msg = lua_tostring(L_, -1);
        error = msg != nullptr ? msg : "syntax error";
        lua_pop(L_, 1);
        return false;
    }
    return run_protected(0, 0, error);
}

bool LuaSandbox::run_protected(int nargs, int nresults, std::string& error) {
    control_.spent = 0;
    const int base = lua_gettop(L_) - nargs;
    lua_pushcfunction(L_, traceback);
    lua_insert(L_, base);
    const int status = lua_pcall(L_, nargs, nresults, base);
    lua_remove(L_, base);
    if (status != LUA_OK) {
        const char* msg = lua_tostring(L_, -1);
        error = msg != nullptr ? msg : "script error";
        if (error.size() > 2000) {
            error.resize(2000);
        }
        lua_pop(L_, 1);
        return false;
    }
    return true;
}

bool LuaSandbox::has_function(const char* name) const {
    if (L_ == nullptr) {
        return false;
    }
    const int type = lua_getglobal(L_, name);
    lua_pop(L_, 1);
    return type == LUA_TFUNCTION;
}

bool LuaSandbox::call(const char* name, int nargs, int nresults, std::string& error) {
    if (L_ == nullptr) {
        error = "no script";
        return false;
    }
    if (lua_getglobal(L_, name) != LUA_TFUNCTION) {
        lua_pop(L_, 1 + nargs);
        error = std::string("no function '") + name + "'";
        return false;
    }
    lua_insert(L_, -(nargs + 1));  // Function below its arguments.
    return run_protected(nargs, nresults, error);
}

}  // namespace sc::script
