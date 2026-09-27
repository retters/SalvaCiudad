#include <doctest.h>

#include <cmath>
#include <cstring>
#include <filesystem>
#include <vector>

#include "audio/mixer.h"
#include "core/file_io.h"
#include "test_util.h"

using namespace sc;

namespace {

std::vector<std::uint8_t> wav(int channels, int rate, int bits, const std::vector<std::int16_t>& samples) {
    std::vector<std::uint8_t> b;
    const auto put32 = [&](std::uint32_t v) {
        for (int i = 0; i < 4; ++i) {
            b.push_back(static_cast<std::uint8_t>(v >> (8 * i)));
        }
    };
    const auto put16 = [&](std::uint16_t v) {
        b.push_back(static_cast<std::uint8_t>(v));
        b.push_back(static_cast<std::uint8_t>(v >> 8));
    };
    const auto tag = [&](const char* t) { b.insert(b.end(), t, t + 4); };
    tag("RIFF");
    put32(static_cast<std::uint32_t>(36 + samples.size() * 2));
    tag("WAVE");
    tag("fmt ");
    put32(16);
    put16(1);
    put16(static_cast<std::uint16_t>(channels));
    put32(static_cast<std::uint32_t>(rate));
    put32(static_cast<std::uint32_t>(rate * channels * bits / 8));
    put16(static_cast<std::uint16_t>(channels * bits / 8));
    put16(static_cast<std::uint16_t>(bits));
    tag("data");
    put32(static_cast<std::uint32_t>(samples.size() * 2));
    for (const std::int16_t s : samples) {
        put16(static_cast<std::uint16_t>(s));
    }
    return b;
}

}  // namespace

TEST_SUITE("audio") {
    TEST_CASE("WAV files are read strictly") {
        std::string error;
        const auto good = audio::parse_wav(wav(1, audio::kRate, 16, {100, -200, 300}), error);
        REQUIRE(good.has_value());
        CHECK(good->samples == std::vector<std::int16_t>{100, -200, 300});
        CHECK_FALSE(audio::parse_wav(wav(2, audio::kRate, 16, {1, 2}), error).has_value());
        CHECK_FALSE(audio::parse_wav(wav(1, 44100, 16, {1, 2}), error).has_value());
        CHECK_FALSE(audio::parse_wav(wav(1, audio::kRate, 8, {1, 2}), error).has_value());
        std::vector<std::uint8_t> cut = wav(1, audio::kRate, 16, {1, 2, 3, 4});
        cut.resize(cut.size() - 5);
        CHECK_FALSE(audio::parse_wav(cut, error).has_value());
        const std::vector<std::uint8_t> junk(64, 0x41);
        CHECK_FALSE(audio::parse_wav(junk, error).has_value());
        CHECK_FALSE(audio::parse_wav({}, error).has_value());
    }

    TEST_CASE("the mixer mixes voices with the volumes") {
        audio::Mixer m;
        audio::Sound s;
        s.samples.assign(100, 16384);  // Half scale.
        const audio::SoundId id = m.add(s);
        audio::Volumes v;
        v.master = 100;
        m.set_volumes(v);
        m.play(id, audio::Category::Effects, 1.0f);
        std::vector<float> out(50);
        m.mix(out);
        CHECK(out[0] == doctest::Approx(0.5f));
        // Two voices add up; the category volume scales.
        m.play(id, audio::Category::Ui, 1.0f);
        v.category[static_cast<std::size_t>(audio::Category::Ui)] = 50;
        m.set_volumes(v);
        m.mix(out);
        CHECK(out[0] == doctest::Approx(0.5f + 0.25f));
        // Voices end with their sounds.
        m.mix(out);
        m.mix(out);
        CHECK(m.voices() == 0);
        // Master at zero: silence.
        v.master = 0;
        m.set_volumes(v);
        m.play(id, audio::Category::Effects, 1.0f);
        m.mix(out);
        CHECK(out[0] == 0.0f);
    }

    TEST_CASE("the voices are limited and the output never clips") {
        audio::Mixer m;
        audio::Sound s;
        s.samples.assign(1000, 32000);
        const audio::SoundId id = m.add(s);
        audio::Volumes v;
        v.master = 100;
        m.set_volumes(v);
        for (int i = 0; i < 100; ++i) {
            m.play(id, audio::Category::Effects, 1.0f);
        }
        CHECK(m.voices() == audio::kMaxVoices);
        std::vector<float> out(10);
        m.mix(out);
        for (const float o : out) {
            CHECK(o <= 1.0f);
        }
        m.stop_all();
        CHECK(m.voices() == 0);
        m.play(audio::kNoSound, audio::Category::Effects, 1.0f);  // Ignored.
        CHECK(m.voices() == 0);
    }

    TEST_CASE("loops fade in and keep going") {
        audio::Mixer m;
        audio::Sound s;
        s.samples.assign(10, 16384);
        const audio::SoundId id = m.add(s);
        audio::Volumes v;
        v.master = 100;
        m.set_volumes(v);
        m.set_loop(0, id, audio::Category::Ambient, 1.0f);
        std::vector<float> out(static_cast<std::size_t>(audio::kRate));
        m.mix(out);
        CHECK(out.front() < 0.01f);  // Fading in, no click.
        CHECK(out.back() == doctest::Approx(0.5f));
    }

    TEST_CASE("core's sounds are valid") {
        const std::filesystem::path dir = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods" / "core" / "sounds";
        int found = 0;
        for (const char* name : {"chop", "hammer", "bell", "fire", "click", "notify", "coins", "sword", "birds", "wind"}) {
            const fs::ReadResult r = fs::read_file(dir / (std::string(name) + ".wav"), audio::kMaxSoundBytes);
            REQUIRE(r.error == fs::IoError::None);
            std::string error;
            const auto s = audio::parse_wav(
                std::span(reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()), error);
            CHECK_MESSAGE(s.has_value(), name << ": " << error);
            found += s.has_value() ? 1 : 0;
        }
        CHECK(found == 10);
    }
}
