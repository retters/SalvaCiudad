#include "script/tutorial_script.h"

extern "C" {
#include <lua.h>
}

#include "script/lua_sandbox.h"

namespace sc::script {

namespace {

bool valid_function_name(const std::string& name) {
    if (name.empty() || name.size() > 64) {
        return false;
    }
    for (const char c : name) {
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) {
            return false;
        }
    }
    return true;
}

void push_counts(lua_State* L, const std::map<std::string, std::int32_t>& counts) {
    lua_createtable(L, 0, static_cast<int>(counts.size()));
    for (const auto& [key, value] : counts) {
        lua_pushinteger(L, value);
        lua_setfield(L, -2, key.c_str());
    }
}

}  // namespace

TutorialScript::TutorialScript() = default;
TutorialScript::~TutorialScript() = default;

bool TutorialScript::open(const std::vector<mods::ModScript>& scripts, const std::string& mod, std::string& error) {
    sandbox_.reset();
    for (const mods::ModScript& s : scripts) {
        if (s.mod != mod) {
            continue;
        }
        auto box = std::make_unique<LuaSandbox>();
        if (!box->open(s.mod, s.dir, s.source, error)) {
            return false;
        }
        sandbox_ = std::move(box);
        return true;
    }
    error = "no scripts/main.lua in " + mod;
    return false;
}

bool TutorialScript::check(const std::string& function, const TutorialState& state, bool& done, std::string& error) {
    done = false;
    if (sandbox_ == nullptr) {
        error = "no script open";
        return false;
    }
    if (!valid_function_name(function) || !sandbox_->has_function(function.c_str())) {
        error = "no function " + function;
        return false;
    }
    lua_State* L = sandbox_->state();
    lua_createtable(L, 0, 6);
    lua_pushinteger(L, state.population);
    lua_setfield(L, -2, "population");
    lua_pushinteger(L, state.year);
    lua_setfield(L, -2, "year");
    lua_pushinteger(L, state.month);
    lua_setfield(L, -2, "month");
    lua_pushinteger(L, state.day);
    lua_setfield(L, -2, "day");
    push_counts(L, state.stored);
    lua_setfield(L, -2, "stored");
    push_counts(L, state.built);
    lua_setfield(L, -2, "built");
    if (!sandbox_->call(function.c_str(), 1, 1, error)) {
        return false;
    }
    done = lua_toboolean(L, -1) != 0;
    lua_pop(L, 1);
    return true;
}

}  // namespace sc::script
