// Sound effects (phase 18): WAV files read with strict checks, voices mixed
// in software with a volume per category, and an SDL output that pulls from
// the mixer on the audio thread. The mixing itself needs no device, so the
// tests can run it.
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <mutex>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace sc::audio {

inline constexpr int kRate = 22050;  // Mono, like the files.
inline constexpr std::size_t kMaxVoices = 24;
inline constexpr std::size_t kMaxSoundBytes = 16u * 1024u * 1024u;

// Mono 16-bit samples at kRate.
struct Sound {
    std::vector<std::int16_t> samples;
};

// Reads a PCM WAV: mono, 16-bit, kRate. Anything else is refused.
[[nodiscard]] std::optional<Sound> parse_wav(std::span<const std::uint8_t> bytes, std::string& error);

enum class Category : std::uint8_t { Effects, Ambient, Ui, Count };

// Volumes, 0..100, as in the settings.
struct Volumes {
    int master = 80;
    std::array<int, static_cast<std::size_t>(Category::Count)> category{100, 100, 100};
};

using SoundId = std::uint32_t;
inline constexpr SoundId kNoSound = ~0u;

class Mixer {
public:
    // Adds a sound; returns its id.
    SoundId add(Sound sound);
    [[nodiscard]] std::size_t sound_count() const;

    // Plays a sound once at `gain` (0..1). The oldest voice of the same
    // category makes way when all voices are busy.
    void play(SoundId sound, Category category, float gain = 1.0f);
    // A looping sound per slot (ambient beds); gain 0 silences it.
    void set_loop(std::size_t slot, SoundId sound, Category category, float gain);
    void set_volumes(const Volumes& v);
    void stop_all();

    // Mixes `out.size()` samples (mono floats, -1..1).
    void mix(std::span<float> out);
    [[nodiscard]] std::size_t voices() const;

    static constexpr std::size_t kLoops = 3;

private:
    struct Voice {
        SoundId sound = kNoSound;
        Category category = Category::Effects;
        float gain = 1.0f;
        std::size_t position = 0;
        std::uint64_t order = 0;
    };
    struct Loop {
        SoundId sound = kNoSound;
        Category category = Category::Ambient;
        float gain = 0.0f;
        float current = 0.0f;  // Follows `gain` smoothly.
        std::size_t position = 0;
    };
    mutable std::mutex mutex_;
    std::vector<std::shared_ptr<const Sound>> sounds_;
    std::vector<Voice> voices_;
    std::array<Loop, kLoops> loops_{};
    Volumes volumes_;
    std::uint64_t next_order_ = 0;
    [[nodiscard]] float scale(Category c) const;
};

// The sound device (SDL). Without a device the game stays silent.
class Output {
public:
    explicit Output(Mixer& mixer) : mixer_(mixer) {}
    ~Output();
    Output(const Output&) = delete;
    Output& operator=(const Output&) = delete;

    bool open();
    void close();
    [[nodiscard]] bool is_open() const { return stream_ != nullptr; }

private:
    Mixer& mixer_;
    void* stream_ = nullptr;  // SDL_AudioStream.
    std::vector<float> buffer_;
    static void feed(void* self, void* stream, int additional, int total);
};

}  // namespace sc::audio
