#include <doctest.h>

#include <ostream>
#include <set>

#include "game/input_actions.h"

using namespace sc;

TEST_SUITE("input_actions") {
    TEST_CASE("the table covers every action in order, with unique ids and keys") {
        std::set<std::string_view> ids;
        std::set<int> keys;
        std::size_t i = 0;
        for (const ActionInfo& info : action_table()) {
            CHECK(static_cast<std::size_t>(info.action) == i++);
            CHECK(ids.insert(info.id).second);
            for (const SDL_Scancode k : info.default_keys) {
                if (k != SDL_SCANCODE_UNKNOWN) {
                    CHECK_MESSAGE(keys.insert(static_cast<int>(k)).second, "duplicate default key in " << info.id);
                }
            }
        }
        CHECK(i == kActionCount);
    }

    TEST_CASE("key names round-trip") {
        for (const ActionInfo& info : action_table()) {
            for (const SDL_Scancode k : info.default_keys) {
                SDL_Scancode back = SDL_SCANCODE_UNKNOWN;
                const std::string name = scancode_to_name(k);
                REQUIRE(scancode_from_name(name, back));
                CHECK(back == k);
            }
        }
        SDL_Scancode sc = SDL_SCANCODE_A;
        CHECK(scancode_from_name("", sc));
        CHECK(sc == SDL_SCANCODE_UNKNOWN);
        CHECK_FALSE(scancode_from_name("NotAKey", sc));
        CHECK_FALSE(scancode_from_name(std::string(100, 'x'), sc));
    }

    TEST_CASE("bindings find, match and reset") {
        KeyBindings b;
        CHECK(b.matches(Action::CameraForward, SDL_SCANCODE_W));
        CHECK(b.matches(Action::CameraForward, SDL_SCANCODE_UP));
        CHECK_FALSE(b.matches(Action::CameraForward, SDL_SCANCODE_S));
        CHECK_FALSE(b.matches(Action::CameraForward, SDL_SCANCODE_UNKNOWN));
        Action a{};
        std::size_t slot = 9;
        REQUIRE(b.find(SDL_SCANCODE_F11, a, slot));
        CHECK(a == Action::UiToggleFullscreen);
        CHECK(slot == 0);
        b.set_key(Action::CameraForward, 0, SDL_SCANCODE_I);
        CHECK(b.matches(Action::CameraForward, SDL_SCANCODE_I));
        CHECK_FALSE(b == KeyBindings{});
        b.reset_to_defaults();
        CHECK(b == KeyBindings{});
    }
}
