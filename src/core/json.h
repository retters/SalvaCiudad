// Thin helpers over yyjson for reading untrusted JSON field by field and for
// updating documents while keeping fields this version does not know.
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <string_view>

#include <yyjson.h>

namespace sc::json {

struct MutDocDeleter {
    void operator()(yyjson_mut_doc* doc) const { yyjson_mut_doc_free(doc); }
};
using MutDoc = std::unique_ptr<yyjson_mut_doc, MutDocDeleter>;

enum class ParseError : std::uint8_t { None, Empty, Malformed, NotObject, OutOfMemory };

struct ParseResult {
    MutDoc doc;  // Set only when error == None; the root is an object.
    ParseError error = ParseError::None;
    std::string message;  // English, for the log.
};

// Strict JSON (a UTF-8 BOM is tolerated) whose root must be an object.
[[nodiscard]] ParseResult parse_object(std::string_view text);

// A new document with an empty object as root.
[[nodiscard]] MutDoc new_object_doc();

// Pretty-printed with two spaces and a final newline. Empty on failure.
[[nodiscard]] std::string write_pretty(const yyjson_mut_doc* doc);

// Outcome of reading one field. Missing is not an error: the default is used
// silently. Invalid means the field exists but has the wrong type or range.
enum class Field : std::uint8_t { Missing, Invalid, Ok };

[[nodiscard]] Field get_object(yyjson_mut_val* obj, const char* key, yyjson_mut_val*& out);
[[nodiscard]] Field get_bool(yyjson_mut_val* obj, const char* key, bool& out);
[[nodiscard]] Field get_int(yyjson_mut_val* obj, const char* key, std::int64_t min, std::int64_t max,
                            std::int64_t& out);
[[nodiscard]] Field get_double(yyjson_mut_val* obj, const char* key, double min, double max, double& out);
// Accepts only UTF-8 text without control characters, up to `max_bytes`.
[[nodiscard]] Field get_string(yyjson_mut_val* obj, const char* key, std::size_t max_bytes, std::string& out);

// Returns the object stored under `key`, replacing any non-object value (or
// adding one) so callers can always write into it. Null on out-of-memory.
yyjson_mut_val* ensure_object(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key);

// Setters replace the value under `key` or add it. They return false on
// out-of-memory.
bool set_bool(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, bool value);
bool set_int(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, std::int64_t value);
bool set_double(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, double value);
bool set_string(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, std::string_view value);
bool remove_key(yyjson_mut_val* obj, const char* key);

}  // namespace sc::json
