#include "sim/content.h"

namespace sc::sim {

namespace {

template <typename T>
DefIndex find_def(const std::vector<T>& list, std::string_view id) {
    for (std::size_t i = 0; i < list.size(); ++i) {
        if (list[i].id == id) {
            return static_cast<DefIndex>(i);
        }
    }
    return kNoDef;
}

}  // namespace

DefIndex Content::find_resource(std::string_view id) const {
    return find_def(resources, id);
}

DefIndex Content::find_building(std::string_view id) const {
    return find_def(buildings, id);
}

DefIndex Content::find_recipe(std::string_view id) const {
    return find_def(recipes, id);
}

DefIndex Content::find_crop(std::string_view id) const {
    return find_def(crops, id);
}

std::string race_body_file(std::string_view body, bool female) {
    return "models/characters/" + std::string(body) + (female ? "_female.glb" : "_male.glb");
}

const FeatureDef* Content::feature(FeatureKind kind) const {
    for (const FeatureDef& f : features) {
        if (f.kind == kind) {
            return &f;
        }
    }
    return nullptr;
}

}  // namespace sc::sim
