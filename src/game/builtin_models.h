// Models the game loads by file name instead of through a definition. All
// are in the core mod. The model viewer (phase 30) counts them as used.
#pragma once

#include <string_view>

namespace sc::builtin_models {

inline constexpr std::string_view kCloud = "models/props/cloud.glb";
inline constexpr std::string_view kSampleHouse = "models/props/house_small.glb";  // Map preview and test scene.
inline constexpr std::string_view kTestTree = "models/props/tree_pine.glb";
inline constexpr std::string_view kTestRock = "models/props/rock.glb";
// In the order of sim::CreatureKind.
inline constexpr std::string_view kAnimals[] = {"models/animals/deer.glb", "models/animals/boar.glb",
                                                "models/animals/wolf.glb", "models/animals/bear.glb"};
// Accessories of every body, and the bones they are pinned to.
inline constexpr const char* kHeadBone = "head";  // Hats and the beard.
inline constexpr const char* kHipsBone = "hips";  // Aprons.
inline constexpr std::string_view kHats[] = {"models/characters/hat_straw.glb", "models/characters/hat_cap.glb"};
inline constexpr std::string_view kBeard = "models/characters/beard.glb";
inline constexpr std::string_view kApronMale = "models/characters/apron_male.glb";
inline constexpr std::string_view kApronFemale = "models/characters/apron_female.glb";

// Each file with the group the viewer shows it in.
struct Use {
    std::string_view path;
    std::string_view group;
};
inline constexpr Use kAll[] = {
    {kCloud, "cloud"},         {kSampleHouse, "sample_house"}, {kTestTree, "test_scene"}, {kTestRock, "test_scene"},
    {kAnimals[0], "deer"},     {kAnimals[1], "boar"},          {kAnimals[2], "wolf"},     {kAnimals[3], "bear"},
    {kHats[0], "hat"},         {kHats[1], "hat"},              {kBeard, "beard"},         {kApronMale, "apron"},
    {kApronFemale, "apron"},
};

}  // namespace sc::builtin_models
