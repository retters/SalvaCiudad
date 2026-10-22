// What a frame costs (phases 129 to 131): the measures of the log.
#include <doctest.h>

#include "game/perf_window.h"

using namespace sc;

TEST_SUITE("scene") {
    TEST_CASE("the perf window keeps averages, the worst frame and the slow ones") {
        PerfWindow w;
        FrameSample fast;
        fast.frame_ms = 10.0f;
        fast.sim_ms = 2.0f;
        fast.world_ms = 1.0f;
        fast.scene_ms = 3.0f;
        fast.prepare_ms = 0.5f;
        fast.cull_ms = 1.0f;
        FrameSample slow = fast;
        slow.frame_ms = 410.0f;
        slow.scene_ms = 403.0f;
        slow.prepare_ms = 400.0f;
        for (int i = 0; i < 9; ++i) {
            w.add(fast);
        }
        w.add(slow);
        CHECK(w.frames() == 10);
        CHECK(w.seconds() == doctest::Approx(0.5f));
        const PerfSummary s = w.take();
        CHECK(s.frames == 10);
        CHECK(s.fps == doctest::Approx(20.0f));
        CHECK(s.worst_ms == doctest::Approx(410.0f));
        CHECK(s.slow_frames == 1);
        CHECK(s.sim_ms == doctest::Approx(2.0f));
        CHECK(s.world_ms == doctest::Approx(1.0f));
        CHECK(s.scene_ms == doctest::Approx((9.0f * 3.0f + 403.0f) / 10.0f));
        // 50 ms a frame on average, of which 2 + 1 + 43 are known.
        CHECK(s.other_ms == doctest::Approx(4.0f));
        CHECK(s.worst_prepare_ms == doctest::Approx(400.0f));
        CHECK(s.worst_cull_ms == doctest::Approx(1.0f));
        // Taking it starts over.
        CHECK(w.frames() == 0);
        CHECK(w.seconds() == doctest::Approx(0.0f));
        CHECK(w.take().frames == 0);
    }

    TEST_CASE("an empty perf window reports nothing and the rest is never negative") {
        PerfWindow w;
        const PerfSummary empty = w.take();
        CHECK(empty.fps == doctest::Approx(0.0f));
        CHECK(empty.worst_ms == doctest::Approx(0.0f));
        FrameSample odd;
        odd.frame_ms = 5.0f;
        odd.scene_ms = 8.0f;  // Timed against another frame's start: may exceed it.
        w.add(odd);
        CHECK(w.take().other_ms == doctest::Approx(0.0f));
    }
}
