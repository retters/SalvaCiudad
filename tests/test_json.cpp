#include <doctest.h>

#include "core/json.h"

using namespace sc;

TEST_SUITE("json") {
    TEST_CASE("parse errors are classified") {
        CHECK(json::parse_object("").error == json::ParseError::Empty);
        CHECK(json::parse_object("   ").error != json::ParseError::None);
        CHECK(json::parse_object("{\"a\": 1").error == json::ParseError::Malformed);
        CHECK(json::parse_object("{\"a\": 1,}").error == json::ParseError::Malformed);
        CHECK(json::parse_object("// comment\n{}").error == json::ParseError::Malformed);
        CHECK(json::parse_object("[1, 2]").error == json::ParseError::NotObject);
        CHECK(json::parse_object("42").error == json::ParseError::NotObject);
        CHECK(json::parse_object("{\"a\": \"\xC3\"}").error == json::ParseError::Malformed);
    }

    TEST_CASE("a UTF-8 BOM is tolerated") {
        const auto r = json::parse_object("\xEF\xBB\xBF{\"a\": true}");
        REQUIRE(r.error == json::ParseError::None);
        bool a = false;
        CHECK(json::get_bool(yyjson_mut_doc_get_root(r.doc.get()), "a", a) == json::Field::Ok);
        CHECK(a);
    }

    TEST_CASE("typed getters check type and range") {
        const auto r = json::parse_object(R"({
            "i": 5, "neg": -3, "big": 18446744073709551615, "f": 1.5, "s": "hola",
            "ctl": "a\nb", "b": false, "o": {}, "n": null
        })");
        REQUIRE(r.error == json::ParseError::None);
        yyjson_mut_val* root = yyjson_mut_doc_get_root(r.doc.get());

        std::int64_t i = 0;
        CHECK(json::get_int(root, "i", 0, 10, i) == json::Field::Ok);
        CHECK(i == 5);
        CHECK(json::get_int(root, "i", 6, 10, i) == json::Field::Invalid);
        CHECK(json::get_int(root, "neg", -5, 0, i) == json::Field::Ok);
        CHECK(i == -3);
        CHECK(json::get_int(root, "big", 0, INT64_MAX, i) == json::Field::Invalid);
        CHECK(json::get_int(root, "f", 0, 10, i) == json::Field::Invalid);
        CHECK(json::get_int(root, "s", 0, 10, i) == json::Field::Invalid);
        CHECK(json::get_int(root, "missing", 0, 10, i) == json::Field::Missing);

        double d = 0.0;
        CHECK(json::get_double(root, "f", 0.0, 2.0, d) == json::Field::Ok);
        CHECK(d == doctest::Approx(1.5));
        CHECK(json::get_double(root, "i", 0.0, 10.0, d) == json::Field::Ok);
        CHECK(json::get_double(root, "f", 0.0, 1.0, d) == json::Field::Invalid);

        std::string s;
        CHECK(json::get_string(root, "s", 16, s) == json::Field::Ok);
        CHECK(s == "hola");
        CHECK(json::get_string(root, "s", 3, s) == json::Field::Invalid);
        CHECK(json::get_string(root, "ctl", 16, s) == json::Field::Invalid);
        CHECK(json::get_string(root, "n", 16, s) == json::Field::Invalid);

        bool b = true;
        CHECK(json::get_bool(root, "b", b) == json::Field::Ok);
        CHECK_FALSE(b);
        CHECK(json::get_bool(root, "i", b) == json::Field::Invalid);

        yyjson_mut_val* o = nullptr;
        CHECK(json::get_object(root, "o", o) == json::Field::Ok);
        CHECK(json::get_object(root, "s", o) == json::Field::Invalid);
    }

    TEST_CASE("setters replace values and ensure_object replaces non-objects") {
        auto doc = json::new_object_doc();
        REQUIRE(doc);
        yyjson_mut_val* root = yyjson_mut_doc_get_root(doc.get());
        CHECK(json::set_int(doc.get(), root, "x", 1));
        CHECK(json::set_int(doc.get(), root, "x", 2));
        CHECK(yyjson_mut_obj_size(root) == 1);
        CHECK(json::set_string(doc.get(), root, "section", "not an object"));
        yyjson_mut_val* section = json::ensure_object(doc.get(), root, "section");
        REQUIRE(section != nullptr);
        CHECK(yyjson_mut_is_obj(section));
        CHECK(json::set_bool(doc.get(), section, "flag", true));

        const std::string out = json::write_pretty(doc.get());
        const auto back = json::parse_object(out);
        REQUIRE(back.error == json::ParseError::None);
        yyjson_mut_val* broot = yyjson_mut_doc_get_root(back.doc.get());
        std::int64_t x = 0;
        CHECK(json::get_int(broot, "x", 0, 10, x) == json::Field::Ok);
        CHECK(x == 2);
        yyjson_mut_val* bsection = nullptr;
        REQUIRE(json::get_object(broot, "section", bsection) == json::Field::Ok);
        bool flag = false;
        CHECK(json::get_bool(bsection, "flag", flag) == json::Field::Ok);
        CHECK(flag);
        CHECK(out.ends_with("\n"));
    }
}
