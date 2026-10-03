#include <doctest.h>

#include <map>
#include <string>
#include <vector>

#include "game/window_list.h"

using sc::WindowList;
using sc::sim::EntityId;
using sc::ui::Rect;

TEST_SUITE("windows") {
    TEST_CASE("selecting things opens one passing window that the next selection takes over") {
        WindowList w;
        const EntityId house{1, 0};
        const EntityId mill{2, 0};
        const EntityId ana{7, 0};
        const std::string first = w.select(WindowList::Kind::Building, house);
        CHECK(first == "obj1");
        CHECK(w.objects().size() == 1);
        REQUIRE(w.passing() != nullptr);
        CHECK(w.passing()->entity == house);
        // Another selection: the same window shows it.
        CHECK(w.select(WindowList::Kind::Building, mill) == first);
        CHECK(w.objects().size() == 1);
        CHECK(w.passing()->entity == mill);
        // And a villager: the kind changes with it.
        CHECK(w.select(WindowList::Kind::Villager, ana) == first);
        CHECK(w.passing()->kind == WindowList::Kind::Villager);
        // A building and a villager may share a number: they are not the same thing.
        CHECK(w.select(WindowList::Kind::Building, EntityId{7, 0}) == first);
        CHECK(w.passing()->kind == WindowList::Kind::Building);
        // A tree and an animal too (phase 63).
        CHECK(w.select(WindowList::Kind::Node, EntityId{7, 0}) == first);
        CHECK(w.passing()->kind == WindowList::Kind::Node);
        w.set_pinned(first, true);
        const std::string second = w.select(WindowList::Kind::Creature, EntityId{7, 0});
        CHECK(second != first);
        CHECK(w.objects().size() == 2);
    }

    TEST_CASE("a pinned window stays and the next selection opens another") {
        WindowList w;
        const EntityId a{1, 0}, b{2, 0}, c{3, 0};
        const std::string wa = w.select(WindowList::Kind::Villager, a);
        w.set_pinned(wa, true);
        CHECK(w.passing() == nullptr);
        const std::string wb = w.select(WindowList::Kind::Villager, b);
        CHECK(wb != wa);
        CHECK(w.objects().size() == 2);
        // Esc, or a click on the ground: only the passing one goes.
        w.close_passing();
        CHECK(w.objects().size() == 1);
        CHECK(w.object(wa) != nullptr);
        CHECK(w.open(wa));
        CHECK_FALSE(w.open(wb));
        w.close_passing();  // Nothing to close: the pinned one stays.
        CHECK(w.objects().size() == 1);
        // Selecting the pinned thing again brings its window forward, no new one.
        const std::string wc = w.select(WindowList::Kind::Villager, c);
        CHECK(w.order().back() == wc);
        CHECK(w.select(WindowList::Kind::Villager, a) == wa);
        CHECK(w.order().back() == wa);
        CHECK(w.objects().size() == 2);
        // Its own X closes it.
        w.close(wa);
        CHECK(w.object(wa) == nullptr);
        CHECK(w.objects().size() == 1);
        // Letting go a pinned window makes it the passing one: the other goes.
        w.set_pinned(wc, true);
        const std::string wd = w.select(WindowList::Kind::Villager, a);
        CHECK(w.objects().size() == 2);
        w.set_pinned(wc, false);
        CHECK(w.objects().size() == 1);
        CHECK(w.object(wd) == nullptr);
        CHECK(w.passing()->id == wc);
    }

    TEST_CASE("three villagers and two buildings open at once, and no more than sixteen") {
        WindowList w;
        std::vector<std::string> ids;
        for (std::uint32_t i = 0; i < 5; ++i) {
            const WindowList::Kind kind = i < 3 ? WindowList::Kind::Villager : WindowList::Kind::Building;
            ids.push_back(w.select(kind, EntityId{i, 0}));
            w.set_pinned(ids.back(), true);
        }
        CHECK(w.objects().size() == 5);
        for (std::uint32_t i = 0; i < 5; ++i) {
            REQUIRE(w.object(ids[i]) != nullptr);
            CHECK(w.object(ids[i])->entity == EntityId{i, 0});  // Each keeps its own.
        }
        for (std::uint32_t i = 5; i < WindowList::kMaxObjects; ++i) {
            w.set_pinned(w.select(WindowList::Kind::Villager, EntityId{i, 0}), true);
        }
        CHECK(w.objects().size() == WindowList::kMaxObjects);
        CHECK(w.select(WindowList::Kind::Villager, EntityId{99, 0}).empty());
        CHECK(w.objects().size() == WindowList::kMaxObjects);
        // Closing one makes room, and its number is used again.
        w.close(ids[2]);
        CHECK(w.select(WindowList::Kind::Villager, EntityId{99, 0}) == ids[2]);
        // Another game: none.
        w.clear_objects();
        CHECK(w.objects().empty());
        CHECK(w.order().empty());
    }

    TEST_CASE("the window touched comes forward and only the one in front gets the click") {
        WindowList w;
        w.raise("goods");
        w.raise("stats");
        w.raise("log");
        CHECK(w.order() == std::vector<std::string>{"goods", "stats", "log"});
        const std::map<std::string, Rect> rects = {
            {"goods", {100, 100, 200, 200}}, {"stats", {200, 150, 200, 200}}, {"log", {600, 100, 100, 100}}};
        CHECK(w.top_at(rects, 150, 120) == "goods");
        CHECK(w.top_at(rects, 250, 200) == "stats");  // Both are there: the one in front.
        CHECK(w.top_at(rects, 650, 150) == "log");
        CHECK(w.top_at(rects, 500, 500).empty());
        w.raise("goods");
        CHECK(w.order() == std::vector<std::string>{"stats", "log", "goods"});
        CHECK(w.top_at(rects, 250, 200) == "goods");
        // A closed window is not in the way.
        w.close("goods");
        CHECK_FALSE(w.open("goods"));
        CHECK(w.top_at(rects, 250, 200) == "stats");
        CHECK(w.top_at(rects, 150, 120).empty());
    }

    TEST_CASE("windows are drawn to the edges, the build bar and each other") {
        const WindowList::Area area{1600, 900, 44, 800};
        const float snap = 12;
        Rect box{5, 50, 300, 200};
        WindowList::magnets(box, {}, area, snap);
        CHECK(box.x == 0);
        CHECK(box.y == 44);
        // The right edge and the build bar.
        box = {1292, 595, 300, 200};
        WindowList::magnets(box, {}, area, snap);
        CHECK(box.x == 1300);
        CHECK(box.y == 600);
        // The bottom of the screen, where there is no build bar.
        box = {700, 693, 300, 200};
        WindowList::magnets(box, {}, WindowList::Area{1600, 900, 44, 0}, snap);
        CHECK(box.y == 700);
        // Far from everything: where it was put.
        box = {700, 300, 300, 200};
        WindowList::magnets(box, {}, area, snap);
        CHECK(box.x == 700);
        CHECK(box.y == 300);

        const std::vector<Rect> other = {{400, 200, 300, 250}};
        box = {706, 260, 200, 100};  // Beside it, on the right.
        WindowList::magnets(box, other, area, snap);
        CHECK(box.x == 700);
        box = {195, 260, 200, 100};  // On the left.
        WindowList::magnets(box, other, area, snap);
        CHECK(box.x == 200);
        box = {450, 455, 200, 100};  // Under it.
        WindowList::magnets(box, other, area, snap);
        CHECK(box.y == 450);
        box = {450, 93, 200, 100};  // Over it.
        WindowList::magnets(box, other, area, snap);
        CHECK(box.y == 100);
        // Equal edges in line: tops, bottoms, lefts and rights.
        box = {704, 207, 200, 100};
        WindowList::magnets(box, other, area, snap);
        CHECK(box.x == 700);
        CHECK(box.y == 200);
        box = {704, 345, 200, 100};
        WindowList::magnets(box, other, area, snap);
        CHECK(box.y == 350);
        box = {405, 455, 200, 100};
        WindowList::magnets(box, other, area, snap);
        CHECK(box.x == 400);
        box = {495, 455, 200, 100};
        WindowList::magnets(box, other, area, snap);
        CHECK(box.x == 500);
        // A window far above or below does not pull sideways.
        box = {706, 700, 200, 100};
        WindowList::magnets(box, other, area, snap);
        CHECK(box.x == 706);

        CHECK(WindowList::touching({700, 260, 200, 100}, other[0]));
        CHECK(WindowList::touching({450, 450, 200, 100}, other[0]));
        CHECK_FALSE(WindowList::touching({710, 260, 200, 100}, other[0]));
        CHECK_FALSE(WindowList::touching({700, 500, 200, 100}, other[0]));  // In line, but not beside.
    }

    TEST_CASE("docked windows form a group that ends when a member closes") {
        WindowList w;
        for (const char* id : {"goods", "stats", "log"}) {
            w.raise(id);
            w.place(id).placed = true;
        }
        w.dock("stats", "goods");
        CHECK(w.place("goods").group != 0);
        CHECK(w.place("stats").group == w.place("goods").group);
        CHECK(w.place("log").group == 0);
        w.dock("log", "stats");
        CHECK(w.place("log").group == w.place("goods").group);
        // One of three closes: the other two go on together.
        w.close("log");
        CHECK(w.place("log").group == 0);
        CHECK(w.place("stats").group == w.place("goods").group);
        CHECK(w.place("goods").group != 0);
        // One of two: no group is left.
        w.close("stats");
        CHECK(w.place("stats").group == 0);
        CHECK(w.place("goods").group == 0);
        // Ctrl+drag takes one out the same way.
        w.dock("stats", "goods");
        w.leave_group("goods");
        CHECK(w.place("stats").group == 0);
        // Moving from one group to another ends the one left with a single window.
        w.dock("stats", "goods");
        w.dock("stats", "log");
        CHECK(w.place("goods").group == 0);
        CHECK(w.place("stats").group == w.place("log").group);
        CHECK(w.place("log").group != 0);
    }

    TEST_CASE("the windows' places are remembered, and a layout of before is read") {
        // As written before phase 62: five values, and the windows of the
        // selected building and villager among them.
        WindowList old;
        old.load("goods:150,60,440,1,3;stats:150,300,380,0,3;building:1200,300,0,1,0;villager:1200,300,0,0,7;log:10,500,0,0,9;");
        CHECK(old.place("goods").placed);
        CHECK(old.place("goods").x == 150);
        CHECK(old.place("goods").y == 60);
        CHECK(old.place("goods").w == 440);
        CHECK(old.place("goods").pinned);
        CHECK_FALSE(old.place("goods").minimized);
        CHECK(old.place("goods").group == 3);
        CHECK(old.place("stats").group == 3);
        CHECK(old.place("log").group == 0);  // A group of one is no group.
        CHECK_FALSE(old.places().contains("building"));
        CHECK_FALSE(old.places().contains("villager"));
        // New groups take numbers after the ones read.
        old.place("layers").placed = true;
        old.dock("layers", "log");
        CHECK(old.place("log").group > 3);

        // Round trip, with "minimized"; the windows of things are not kept.
        WindowList w;
        w.load("goods:150,60,440,1,2,1;stats:150,300,380,0,2,0;");
        CHECK(w.place("goods").minimized);
        const std::string thing = w.select(WindowList::Kind::Building, EntityId{4, 0});
        w.place(thing).placed = true;
        w.place(thing).x = 900;
        w.set_pinned(thing, true);
        w.dock(thing, "goods");
        const std::string text = w.save();
        CHECK(text == "goods:150,60,440,1,2,1,0,0;stats:150,300,380,0,2,0,0,0;");
        WindowList again;
        again.load(text);
        CHECK(again.save() == text);
        // A group kept only by a window of a thing is not written.
        WindowList solo;
        solo.load("goods:150,60,440,0,0,0;");
        const std::string t2 = solo.select(WindowList::Kind::Villager, EntityId{1, 0});
        solo.place(t2).placed = true;
        solo.dock(t2, "goods");
        CHECK(solo.save() == "goods:150,60,440,0,0,0,0,0;");

        // Damaged entries are skipped, the rest is read.
        WindowList bad;
        bad.load("goods:abc;stats:1,2;log:-5,0,0,0,0;layers:1,2,3,4,5;trade:10,20,0,1,0,1,9;army:10,20,0,1,0;:1,2,3,0,0;"
                 "averyveryverylongwindowname:1,2,3,0,0;GOODS:1,2,3,0,0;obj3:5,5,0,1,0");
        CHECK(bad.places().size() == 1);
        CHECK(bad.place("army").pinned);
        CHECK(bad.save() == "army:10,20,0,1,0,0,0,0;");
        WindowList empty;
        empty.load("");
        CHECK(empty.save().empty());
    }

    TEST_CASE("four windows joined as tabs of one, and taken apart again") {
        WindowList w;
        for (const char* id : {"goods", "stats", "log", "layers"}) {
            w.raise(id);
            w.place(id).placed = true;
        }
        w.place("goods").x = 100;
        w.place("goods").y = 80;
        w.place("goods").w = 440;
        w.place("stats").x = 700;
        CHECK(w.tabs("goods").empty());
        CHECK_FALSE(w.hidden("goods"));

        // Stats dropped on the title of goods: one window, two tabs, stats showing.
        w.merge("stats", "goods");
        CHECK(w.tabs("goods") == std::vector<std::string>{"goods", "stats"});
        CHECK(w.tabs("stats") == w.tabs("goods"));
        CHECK(w.hidden("goods"));
        CHECK_FALSE(w.hidden("stats"));
        CHECK(w.place("stats").x == 100);  // Where goods was.
        CHECK(w.place("stats").y == 80);
        CHECK(w.place("stats").w == 440);
        w.merge("log", "stats");
        w.merge("layers", "goods");
        CHECK(w.tabs("log") == std::vector<std::string>{"goods", "stats", "log", "layers"});
        int showing = 0;
        for (const char* id : {"goods", "stats", "log", "layers"}) {
            showing += w.hidden(id) ? 0 : 1;
        }
        CHECK(showing == 1);
        CHECK_FALSE(w.hidden("layers"));
        // A click on a tab shows it.
        w.raise("goods");
        CHECK_FALSE(w.hidden("goods"));
        CHECK(w.hidden("layers"));
        // Moving the window moves its tabs.
        w.place("goods").x = 300;
        w.sync_stack("goods");
        CHECK(w.place("log").x == 300);
        // Joining again what is joined changes nothing.
        w.merge("stats", "log");
        CHECK(w.tabs("log").size() == 4);

        // Remembered: the stack and which tab shows.
        const std::string text = w.save();
        WindowList again;
        again.load(text);
        CHECK(again.save() == text);
        // Nothing is open yet: opening them brings the tabs back.
        CHECK(again.tabs("goods").empty());
        again.raise("log");
        CHECK(again.tabs("log").empty());   // One open window is a window alone.
        CHECK_FALSE(again.hidden("log"));
        again.raise("stats");
        CHECK(again.tabs("log") == std::vector<std::string>{"stats", "log"});
        CHECK(again.hidden("log"));

        // A closed tab leaves the others showing, and comes back to its place.
        w.close("goods");
        CHECK(w.tabs("stats") == std::vector<std::string>{"stats", "log", "layers"});
        showing = 0;
        for (const char* id : {"stats", "log", "layers"}) {
            showing += w.hidden(id) ? 0 : 1;
        }
        CHECK(showing == 1);
        w.raise("goods");
        CHECK(w.tabs("stats").size() == 4);

        // Pulled out one by one: four windows again.
        w.split("goods");
        CHECK(w.tabs("goods").empty());
        CHECK_FALSE(w.hidden("goods"));
        CHECK(w.tabs("stats").size() == 3);
        w.split("log");
        w.split("layers");
        for (const char* id : {"goods", "stats", "log", "layers"}) {
            CHECK(w.tabs(id).empty());
            CHECK_FALSE(w.hidden(id));
        }
        CHECK(w.save().find(",0,0;") != std::string::npos);  // No stack is written.
        CHECK(w.save().find(",1,") == std::string::npos);
    }

    TEST_CASE("the windows of things can be tabs too, until they close") {
        WindowList w;
        w.raise("goods");
        w.place("goods").placed = true;
        const std::string a = w.select(WindowList::Kind::Villager, EntityId{1, 0});
        w.set_pinned(a, true);
        const std::string b = w.select(WindowList::Kind::Villager, EntityId{2, 0});
        w.merge(b, a);
        w.merge(a, "goods");  // The two of them, onto goods.
        CHECK(w.tabs("goods") == std::vector<std::string>{"goods", a, b});
        CHECK_FALSE(w.hidden(a));
        // The next selection takes the passing window, wherever it is, and shows it.
        CHECK(w.select(WindowList::Kind::Villager, EntityId{3, 0}) == b);
        CHECK_FALSE(w.hidden(b));
        // Closed for good: out of the stack.
        w.close(b);
        CHECK(w.tabs("goods") == std::vector<std::string>{"goods", a});
        w.close(a);
        CHECK(w.tabs("goods").empty());
        CHECK_FALSE(w.hidden("goods"));
        // Stacks with windows of things are not written.
        CHECK(w.save() == "goods:0,0,0,0,0,0,0,0;");
        // A layout of phase 62 (six values) is still read.
        WindowList old;
        old.load("goods:150,60,440,1,0,1;");
        CHECK(old.place("goods").minimized);
    }
}
