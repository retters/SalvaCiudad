// Tutorial goals written in Lua (section 6.5): a step whose goal is "lua"
// names a function of its mod's main.lua that receives what the town has
// and returns true when the step is done. The state is read only: the
// function sees a copy.
#pragma once

#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "mods/mod_library.h"

namespace sc::script {

class LuaSandbox;

// What a tutorial goal can look at.
struct TutorialState {
    std::int32_t population = 0;
    std::int32_t year = 1;
    std::int32_t month = 1;
    std::int32_t day = 1;
    std::map<std::string, std::int32_t> stored;  // Resource id -> amount.
    std::map<std::string, std::int32_t> built;   // Building id -> finished ones.
};

class TutorialScript {
public:
    TutorialScript();
    ~TutorialScript();
    TutorialScript(const TutorialScript&) = delete;
    TutorialScript& operator=(const TutorialScript&) = delete;

    // Opens `mod`'s main.lua; false (with `error`) if it has none or fails.
    bool open(const std::vector<mods::ModScript>& scripts, const std::string& mod, std::string& error);
    // Calls `function(state)`; `done` is its result read as a boolean.
    bool check(const std::string& function, const TutorialState& state, bool& done, std::string& error);

private:
    std::unique_ptr<LuaSandbox> sandbox_;
};

}  // namespace sc::script
