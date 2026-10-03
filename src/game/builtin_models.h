// Models the game loads by file name instead of through a definition. All
// are in the core mod. The model viewer (phase 30) counts them as used.
#pragma once

#include <string_view>

namespace sc::builtin_models {

// The cloud shapes (phase 31); each cloud takes one.
inline constexpr std::string_view kClouds[] = {"models/props/cloud.glb", "models/props/cloud_2.glb",
                                               "models/props/cloud_3.glb", "models/props/cloud_4.glb"};
inline constexpr std::string_view kSampleHouse = "models/props/house_small.glb";  // Map preview.
// In the order of sim::CreatureKind.
inline constexpr std::string_view kAnimals[] = {"models/animals/deer.glb", "models/animals/boar.glb",
                                                "models/animals/wolf.glb", "models/animals/bear.glb"};
// The tools the characters hold while a clip plays (phase 57): a model's
// "<clip>_prop" names the kind; `roll` turns the tool about its own long
// axis in the hand, in degrees (art/blender/build_all.py GAME_TOOLS).
struct Tool {
    std::string_view kind;
    std::string_view path;
    float roll = 0.0f;
};
inline constexpr Tool kTools[] = {
    {"axe", "models/tools/axe.glb", 90.0f},
    {"bow", "models/tools/bow.glb", 0.0f},
    {"rod", "models/tools/rod.glb", 0.0f},
    {"hammer", "models/tools/hammer.glb", 0.0f},
};

// Each file with the group the viewer shows it in.
struct Use {
    std::string_view path;
    std::string_view group;
};
inline constexpr Use kAll[] = {
    {kClouds[0], "cloud"},     {kClouds[1], "cloud"},          {kClouds[2], "cloud"},     {kClouds[3], "cloud"},
    {kSampleHouse, "sample_house"},
    {kAnimals[0], "deer"},     {kAnimals[1], "boar"},          {kAnimals[2], "wolf"},     {kAnimals[3], "bear"},
    {kTools[0].path, "tool"},  {kTools[1].path, "tool"},       {kTools[2].path, "tool"},  {kTools[3].path, "tool"},
};

}  // namespace sc::builtin_models
