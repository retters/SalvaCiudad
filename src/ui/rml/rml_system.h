// RmlUi's system and file interfaces (phase 117, section 7.14).
//
// Texts: a document writes its fixed texts as @key (for example
// @hud.window.pin); RmlUi asks for every text it loads and each @key with a
// dot is replaced by the active language's text (D-11711). A key the
// language does not have stays as written, so a mistake shows on screen.
//
// Files: documents, style sheets and images are read only from the allowed
// roots (data/ui and the ui folders of active mods). Absolute paths, drive
// letters, ".." and anything that resolves outside a root are refused.
#pragma once

#include <cstddef>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include <RmlUi/Core/FileInterface.h>
#include <RmlUi/Core/SystemInterface.h>

namespace sc::rml {

// Replaces every @key (letters, digits, '_', '-' and '.', with at least one
// dot) found by `lookup`; returns how many were replaced.
using KeyLookup = std::function<std::optional<std::string>(std::string_view key)>;
int translate_keys(std::string_view text, const KeyLookup& lookup, std::string& out);

class System final : public Rml::SystemInterface {
public:
    double GetElapsedTime() override;
    int TranslateString(Rml::String& translated, const Rml::String& input) override;
    bool LogMessage(Rml::Log::Type type, const Rml::String& message) override;
    void SetClipboardText(const Rml::String& text) override;
    void GetClipboardText(Rml::String& text) override;

    // Errors and warnings RmlUi reported, for the tests and the F3 panel.
    [[nodiscard]] int errors() const { return errors_; }
    [[nodiscard]] int warnings() const { return warnings_; }

private:
    int errors_ = 0;
    int warnings_ = 0;
};

// The file a document path names under one of the roots, or nothing.
[[nodiscard]] std::optional<std::filesystem::path> resolve_ui_path(const std::vector<std::filesystem::path>& roots,
                                                                   std::string_view path);

class Files final : public Rml::FileInterface {
public:
    static constexpr std::size_t kMaxFileBytes = 16u * 1024u * 1024u;

    void set_roots(std::vector<std::filesystem::path> roots) { roots_ = std::move(roots); }
    [[nodiscard]] const std::vector<std::filesystem::path>& roots() const { return roots_; }

    Rml::FileHandle Open(const Rml::String& path) override;
    void Close(Rml::FileHandle file) override;
    size_t Read(void* buffer, size_t size, Rml::FileHandle file) override;
    bool Seek(Rml::FileHandle file, long offset, int origin) override;
    size_t Tell(Rml::FileHandle file) override;
    size_t Length(Rml::FileHandle file) override;

private:
    struct OpenFile {
        std::string data;
        std::size_t position = 0;
    };
    std::vector<std::filesystem::path> roots_;
};

}  // namespace sc::rml
