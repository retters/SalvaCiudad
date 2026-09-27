#include "core/json.h"

#include <cmath>
#include <cstdlib>
#include <format>

#include "core/text.h"

namespace sc::json {

namespace {

struct DocDeleter {
    void operator()(yyjson_doc* doc) const { yyjson_doc_free(doc); }
};

yyjson_mut_val* get_value(yyjson_mut_val* obj, const char* key) {
    return yyjson_mut_is_obj(obj) ? yyjson_mut_obj_get(obj, key) : nullptr;
}

bool put(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, yyjson_mut_val* value) {
    if (value == nullptr || !yyjson_mut_is_obj(obj)) {
        return false;
    }
    yyjson_mut_val* key_val = yyjson_mut_strcpy(doc, key);
    return key_val != nullptr && yyjson_mut_obj_put(obj, key_val, value);
}

}  // namespace

ParseResult parse_object(std::string_view text) {
    ParseResult result;
    if (text.empty()) {
        result.error = ParseError::Empty;
        result.message = "empty content";
        return result;
    }
    yyjson_read_err err{};
    std::unique_ptr<yyjson_doc, DocDeleter> doc(yyjson_read_opts(
        const_cast<char*>(text.data()), text.size(), YYJSON_READ_ALLOW_BOM, nullptr, &err));
    if (!doc) {
        result.error = err.code == YYJSON_READ_ERROR_MEMORY_ALLOCATION ? ParseError::OutOfMemory
                       : err.code == YYJSON_READ_ERROR_EMPTY_CONTENT ? ParseError::Empty
                                                                      : ParseError::Malformed;
        result.message = std::format("{} at byte {}", err.msg != nullptr ? err.msg : "parse error", err.pos);
        return result;
    }
    if (!yyjson_is_obj(yyjson_doc_get_root(doc.get()))) {
        result.error = ParseError::NotObject;
        result.message = "root is not an object";
        return result;
    }
    result.doc.reset(yyjson_doc_mut_copy(doc.get(), nullptr));
    if (!result.doc) {
        result.error = ParseError::OutOfMemory;
        result.message = "out of memory";
    }
    return result;
}

MutDoc new_object_doc() {
    MutDoc doc(yyjson_mut_doc_new(nullptr));
    if (doc) {
        yyjson_mut_val* root = yyjson_mut_obj(doc.get());
        if (root == nullptr) {
            return {};
        }
        yyjson_mut_doc_set_root(doc.get(), root);
    }
    return doc;
}

std::string write_pretty(const yyjson_mut_doc* doc) {
    std::size_t len = 0;
    char* raw = yyjson_mut_write_opts(doc, YYJSON_WRITE_PRETTY_TWO_SPACES, nullptr, &len, nullptr);
    if (raw == nullptr) {
        return {};
    }
    std::string out(raw, len);
    std::free(raw);
    out += '\n';
    return out;
}

Field get_object(yyjson_mut_val* obj, const char* key, yyjson_mut_val*& out) {
    yyjson_mut_val* v = get_value(obj, key);
    if (v == nullptr) {
        return Field::Missing;
    }
    if (!yyjson_mut_is_obj(v)) {
        return Field::Invalid;
    }
    out = v;
    return Field::Ok;
}

Field get_bool(yyjson_mut_val* obj, const char* key, bool& out) {
    yyjson_mut_val* v = get_value(obj, key);
    if (v == nullptr) {
        return Field::Missing;
    }
    if (!yyjson_mut_is_bool(v)) {
        return Field::Invalid;
    }
    out = yyjson_mut_get_bool(v);
    return Field::Ok;
}

Field get_int(yyjson_mut_val* obj, const char* key, std::int64_t min, std::int64_t max, std::int64_t& out) {
    yyjson_mut_val* v = get_value(obj, key);
    if (v == nullptr) {
        return Field::Missing;
    }
    std::int64_t value = 0;
    if (yyjson_mut_is_sint(v)) {
        value = yyjson_mut_get_sint(v);
    } else if (yyjson_mut_is_uint(v)) {
        const std::uint64_t u = yyjson_mut_get_uint(v);
        if (u > static_cast<std::uint64_t>(INT64_MAX)) {
            return Field::Invalid;
        }
        value = static_cast<std::int64_t>(u);
    } else {
        return Field::Invalid;
    }
    if (value < min || value > max) {
        return Field::Invalid;
    }
    out = value;
    return Field::Ok;
}

Field get_double(yyjson_mut_val* obj, const char* key, double min, double max, double& out) {
    yyjson_mut_val* v = get_value(obj, key);
    if (v == nullptr) {
        return Field::Missing;
    }
    if (!yyjson_mut_is_num(v)) {
        return Field::Invalid;
    }
    const double value = yyjson_mut_get_num(v);
    if (!std::isfinite(value) || value < min || value > max) {
        return Field::Invalid;
    }
    out = value;
    return Field::Ok;
}

Field get_string(yyjson_mut_val* obj, const char* key, std::size_t max_bytes, std::string& out) {
    yyjson_mut_val* v = get_value(obj, key);
    if (v == nullptr) {
        return Field::Missing;
    }
    if (!yyjson_mut_is_str(v)) {
        return Field::Invalid;
    }
    const std::string_view s(yyjson_mut_get_str(v), yyjson_mut_get_len(v));
    if (!text::is_safe_display_text(s, max_bytes)) {
        return Field::Invalid;
    }
    out.assign(s);
    return Field::Ok;
}

yyjson_mut_val* ensure_object(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key) {
    yyjson_mut_val* v = get_value(obj, key);
    if (yyjson_mut_is_obj(v)) {
        return v;
    }
    yyjson_mut_val* fresh = yyjson_mut_obj(doc);
    return put(doc, obj, key, fresh) ? fresh : nullptr;
}

bool set_bool(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, bool value) {
    return put(doc, obj, key, yyjson_mut_bool(doc, value));
}

bool set_int(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, std::int64_t value) {
    return put(doc, obj, key, yyjson_mut_sint(doc, value));
}

bool set_double(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, double value) {
    return put(doc, obj, key, yyjson_mut_real(doc, value));
}

bool set_string(yyjson_mut_doc* doc, yyjson_mut_val* obj, const char* key, std::string_view value) {
    return put(doc, obj, key, yyjson_mut_strncpy(doc, value.data(), value.size()));
}

bool remove_key(yyjson_mut_val* obj, const char* key) {
    return yyjson_mut_is_obj(obj) && yyjson_mut_obj_remove_key(obj, key) != nullptr;
}

}  // namespace sc::json
