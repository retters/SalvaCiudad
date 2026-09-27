#include "audio/mixer.h"

#include <algorithm>
#include <cstring>

#include <SDL3/SDL_audio.h>
#include <SDL3/SDL_init.h>

namespace sc::audio {

namespace {

std::uint32_t u32(std::span<const std::uint8_t> b, std::size_t at) {
    return static_cast<std::uint32_t>(b[at]) | static_cast<std::uint32_t>(b[at + 1]) << 8 |
           static_cast<std::uint32_t>(b[at + 2]) << 16 | static_cast<std::uint32_t>(b[at + 3]) << 24;
}

std::uint16_t u16(std::span<const std::uint8_t> b, std::size_t at) {
    return static_cast<std::uint16_t>(b[at] | b[at + 1] << 8);
}

}  // namespace

std::optional<Sound> parse_wav(std::span<const std::uint8_t> bytes, std::string& error) {
    if (bytes.size() > kMaxSoundBytes) {
        error = "sound file too large";
        return std::nullopt;
    }
    if (bytes.size() < 12 || std::memcmp(bytes.data(), "RIFF", 4) != 0 || std::memcmp(bytes.data() + 8, "WAVE", 4) != 0) {
        error = "not a WAV file";
        return std::nullopt;
    }
    bool have_format = false;
    std::optional<Sound> sound;
    std::size_t at = 12;
    while (at + 8 <= bytes.size()) {
        const std::uint32_t size = u32(bytes, at + 4);
        const std::size_t body = at + 8;
        if (size > bytes.size() - body) {
            error = "truncated chunk";
            return std::nullopt;
        }
        if (std::memcmp(bytes.data() + at, "fmt ", 4) == 0) {
            if (size < 16) {
                error = "bad format chunk";
                return std::nullopt;
            }
            const std::uint16_t format = u16(bytes, body);
            const std::uint16_t channels = u16(bytes, body + 2);
            const std::uint32_t rate = u32(bytes, body + 4);
            const std::uint16_t bits = u16(bytes, body + 14);
            if (format != 1 || channels != 1 || rate != kRate || bits != 16) {
                error = "only mono 16-bit PCM at 22050 Hz";
                return std::nullopt;
            }
            have_format = true;
        } else if (std::memcmp(bytes.data() + at, "data", 4) == 0) {
            if (!have_format) {
                error = "data before format";
                return std::nullopt;
            }
            Sound s;
            s.samples.resize(size / 2);
            for (std::size_t i = 0; i < s.samples.size(); ++i) {
                s.samples[i] = static_cast<std::int16_t>(u16(bytes, body + i * 2));
            }
            sound = std::move(s);
        }
        at = body + size + (size & 1u);  // Chunks are padded to even sizes.
    }
    if (!sound.has_value() || sound->samples.empty()) {
        error = "no samples";
        return std::nullopt;
    }
    return sound;
}

SoundId Mixer::add(Sound sound) {
    const std::lock_guard lock(mutex_);
    sounds_.push_back(std::make_shared<const Sound>(std::move(sound)));
    return static_cast<SoundId>(sounds_.size() - 1);
}

std::size_t Mixer::sound_count() const {
    const std::lock_guard lock(mutex_);
    return sounds_.size();
}

void Mixer::play(SoundId sound, Category category, float gain) {
    const std::lock_guard lock(mutex_);
    if (sound >= sounds_.size() || gain <= 0.0f) {
        return;
    }
    if (voices_.size() >= kMaxVoices) {
        // The oldest of the same category, else the oldest of all.
        auto victim = voices_.end();
        for (auto it = voices_.begin(); it != voices_.end(); ++it) {
            if (it->category == category && (victim == voices_.end() || it->order < victim->order)) {
                victim = it;
            }
        }
        if (victim == voices_.end()) {
            victim = std::min_element(voices_.begin(), voices_.end(),
                                      [](const Voice& a, const Voice& b) { return a.order < b.order; });
        }
        voices_.erase(victim);
    }
    voices_.push_back({sound, category, std::clamp(gain, 0.0f, 1.0f), 0, next_order_++});
}

void Mixer::set_loop(std::size_t slot, SoundId sound, Category category, float gain) {
    const std::lock_guard lock(mutex_);
    if (slot >= kLoops) {
        return;
    }
    Loop& l = loops_[slot];
    if (l.sound != sound) {
        l.sound = sound < sounds_.size() ? sound : kNoSound;
        l.position = 0;
        l.current = 0.0f;
    }
    l.category = category;
    l.gain = std::clamp(gain, 0.0f, 1.0f);
}

void Mixer::set_volumes(const Volumes& v) {
    const std::lock_guard lock(mutex_);
    volumes_ = v;
}

void Mixer::stop_all() {
    const std::lock_guard lock(mutex_);
    voices_.clear();
    for (Loop& l : loops_) {
        l.gain = 0.0f;
        l.current = 0.0f;
    }
}

std::size_t Mixer::voices() const {
    const std::lock_guard lock(mutex_);
    return voices_.size();
}

float Mixer::scale(Category c) const {
    const auto i = static_cast<std::size_t>(c);
    const int cat = i < volumes_.category.size() ? volumes_.category[i] : 100;
    return static_cast<float>(std::clamp(volumes_.master, 0, 100)) / 100.0f *
           static_cast<float>(std::clamp(cat, 0, 100)) / 100.0f;
}

void Mixer::mix(std::span<float> out) {
    std::fill(out.begin(), out.end(), 0.0f);
    const std::lock_guard lock(mutex_);
    constexpr float kToFloat = 1.0f / 32768.0f;
    for (Voice& v : voices_) {
        const Sound& s = *sounds_[v.sound];
        const float g = v.gain * scale(v.category) * kToFloat;
        const std::size_t n = std::min(out.size(), s.samples.size() - v.position);
        for (std::size_t i = 0; i < n; ++i) {
            out[i] += static_cast<float>(s.samples[v.position + i]) * g;
        }
        v.position += n;
    }
    std::erase_if(voices_, [&](const Voice& v) { return v.position >= sounds_[v.sound]->samples.size(); });
    for (Loop& l : loops_) {
        if (l.sound == kNoSound || (l.gain <= 0.0f && l.current <= 0.0001f)) {
            continue;
        }
        const Sound& s = *sounds_[l.sound];
        const float target = l.gain * scale(l.category);
        // About half a second to change: no clicks when a bed starts or stops.
        const float step = 1.0f / (static_cast<float>(kRate) * 0.5f);
        for (float& o : out) {
            l.current += std::clamp(target - l.current, -step, step);
            o += static_cast<float>(s.samples[l.position]) * kToFloat * l.current;
            if (++l.position >= s.samples.size()) {
                l.position = 0;
            }
        }
    }
    for (float& o : out) {
        o = std::clamp(o, -1.0f, 1.0f);
    }
}

Output::~Output() {
    close();
}

bool Output::open() {
    if (stream_ != nullptr) {
        return true;
    }
    if (!SDL_WasInit(SDL_INIT_AUDIO) && !SDL_InitSubSystem(SDL_INIT_AUDIO)) {
        return false;
    }
    SDL_AudioSpec spec{};
    spec.format = SDL_AUDIO_F32;
    spec.channels = 1;
    spec.freq = kRate;
    SDL_AudioStream* stream = SDL_OpenAudioDeviceStream(
        SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec,
        [](void* self, SDL_AudioStream* s, int additional, int total) { feed(self, s, additional, total); }, this);
    if (stream == nullptr) {
        return false;
    }
    stream_ = stream;
    SDL_ResumeAudioStreamDevice(stream);
    return true;
}

void Output::close() {
    if (stream_ != nullptr) {
        SDL_DestroyAudioStream(static_cast<SDL_AudioStream*>(stream_));
        stream_ = nullptr;
    }
}

void Output::feed(void* self, void* stream, int additional, int total) {
    (void)total;
    auto* out = static_cast<Output*>(self);
    if (additional <= 0) {
        return;
    }
    const auto n = static_cast<std::size_t>(additional) / sizeof(float);
    out->buffer_.resize(n);
    out->mixer_.mix(out->buffer_);
    SDL_PutAudioStreamData(static_cast<SDL_AudioStream*>(stream), out->buffer_.data(), static_cast<int>(n * sizeof(float)));
}

}  // namespace sc::audio
