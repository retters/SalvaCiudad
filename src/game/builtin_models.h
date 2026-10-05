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
    // Phase 116: held upright (its long axis up) and not along the hand: a spear, its butt by the foot.
    bool upright = false;
};
inline constexpr Tool kTools[] = {
    {"axe", "models/tools/axe.glb", 90.0f},
    {"bow", "models/tools/bow.glb", 0.0f},
    {"rod", "models/tools/rod.glb", 0.0f},
    {"hammer", "models/tools/hammer.glb", 0.0f},
    // Phase 116: what the soldiers hold, by their unit (not named by any clip).
    {"club", "models/tools/club.glb", 0.0f},
    {"spear", "models/tools/spear.glb", 0.0f, true},
    {"shield", "models/tools/shield.glb", 0.0f},
};

// What a villager carries (phase 67), on its back or in its arms: rigid
// models pinned to the chest. In the order of people::Load, after None.
inline constexpr std::string_view kLoads[] = {
    "models/loads/logs_back.glb",  "models/loads/stone_back.glb",  "models/loads/sack_back.glb",
    "models/loads/basket_back.glb", "models/loads/crate_back.glb", "models/loads/logs_arms.glb",
    "models/loads/stone_arms.glb", "models/loads/basket_arms.glb", "models/loads/crate_arms.glb",
};
// Piles of goods beside sites and storages: by sim::LoadKind, three sizes each.
inline constexpr std::string_view kPiles[][3] = {
    {"models/props/pile_crates_1.glb", "models/props/pile_crates_2.glb", "models/props/pile_crates_3.glb"},
    {"models/props/pile_logs_1.glb", "models/props/pile_logs_2.glb", "models/props/pile_logs_3.glb"},
    {"models/props/pile_stone_1.glb", "models/props/pile_stone_2.glb", "models/props/pile_stone_3.glb"},
    {"models/props/pile_sacks_1.glb", "models/props/pile_sacks_2.glb", "models/props/pile_sacks_3.glb"},
    {"models/props/pile_baskets_1.glb", "models/props/pile_baskets_2.glb", "models/props/pile_baskets_3.glb"},
};
inline constexpr std::string_view kCart = "models/props/cart.glb";           // The merchant's.
inline constexpr std::string_view kArrow = "models/props/arrow_flight.glb";  // An arrow in the air.
// A building site's two stages, by its footprint: site_<w>x<d>_<stage>.glb
// (the viewer counts every file that starts like this as used).
inline constexpr std::string_view kSitePrefix = "models/buildings/site_";
// What dresses the ground (phase 91, game/ground_cover) and the animals that
// only give the map life (phase 92, game/ambient_fauna): every file that
// starts like these.
inline constexpr std::string_view kCoverPrefix = "models/props/cover_";
inline constexpr std::string_view kFaunaPrefix = "models/fauna/";

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
    {kTools[4].path, "tool"},  {kTools[5].path, "tool"},       {kTools[6].path, "tool"},
    {kLoads[0], "load"},       {kLoads[1], "load"},            {kLoads[2], "load"},       {kLoads[3], "load"},
    {kLoads[4], "load"},       {kLoads[5], "load"},            {kLoads[6], "load"},       {kLoads[7], "load"},
    {kLoads[8], "load"},
    {kPiles[0][0], "pile"},    {kPiles[0][1], "pile"},         {kPiles[0][2], "pile"},
    {kPiles[1][0], "pile"},    {kPiles[1][1], "pile"},         {kPiles[1][2], "pile"},
    {kPiles[2][0], "pile"},    {kPiles[2][1], "pile"},         {kPiles[2][2], "pile"},
    {kPiles[3][0], "pile"},    {kPiles[3][1], "pile"},         {kPiles[3][2], "pile"},
    {kPiles[4][0], "pile"},    {kPiles[4][1], "pile"},         {kPiles[4][2], "pile"},
    {kCart, "cart"},           {kArrow, "arrow"},
};

}  // namespace sc::builtin_models
