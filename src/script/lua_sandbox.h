// A Lua state for one mod's scripts, with no access to files, the system or
// the network (section 7.13): only the base functions without loading, the
// string, table and utf8 libraries, an integer-only `math`, and a `require`
// limited to the mod's own `scripts` folder. Each call runs with an
// instruction budget and the whole state with a memory limit, so a broken
// script cannot freeze or exhaust the game.
//
// Scripts that change the simulation must stay deterministic: integers only
// (values handed back to the game are checked), and no iteration with
// `pairs` over tables keyed by tables or functions (decision D-702).
#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>

struct lua_State;

namespace sc::script {

struct SandboxLimits {
    std::size_t memory_bytes = 64u * 1024u * 1024u;
    std::uint64_t instructions_per_call = 50'000'000;
};

class LuaSandbox {
public:
    LuaSandbox() = default;
    ~LuaSandbox();
    LuaSandbox(const LuaSandbox&) = delete;
    LuaSandbox& operator=(const LuaSandbox&) = delete;

    // Creates the state and runs `source` (the mod's main.lua). `mod_dir`
    // is where `require` looks, under scripts/.
    bool open(std::string_view mod_id, const std::filesystem::path& mod_dir, std::string_view source,
              std::string& error, const SandboxLimits& limits = {});

    [[nodiscard]] lua_State* state() const { return L_; }
    [[nodiscard]] bool has_function(const char* name) const;

    // Calls a global function; the arguments must already be pushed.
    // Results stay on the stack. On error, `error` explains it.
    bool call(const char* name, int nargs, int nresults, std::string& error);

    [[nodiscard]] const std::string& mod() const { return mod_; }

    // Internals, used by the C callbacks.
    struct Control {
        std::size_t used = 0;
        std::size_t limit = 0;
        std::uint64_t budget = 0;
        std::uint64_t spent = 0;
        std::filesystem::path scripts_dir;
        std::string mod;
    };

private:
    bool run_protected(int nargs, int nresults, std::string& error);

    lua_State* L_ = nullptr;
    Control control_;
    SandboxLimits limits_;
    std::string mod_;
};

// Names allowed for `require`: [a-z0-9_] and '.', as in "utils.stones".
[[nodiscard]] bool is_valid_module_name(std::string_view name);

}  // namespace sc::script
