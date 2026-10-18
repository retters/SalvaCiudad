#include "game/thing_rows.h"

#include <algorithm>
#include <cmath>
#include <format>

#include "game/game_hud.h"
#include "game/game_session.h"
#include "game/model_studio.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

// A command about the window's building.
sim::Command command(sim::CommandType type, sim::EntityId entity, std::int32_t value = 0) {
    sim::Command c;
    c.type = type;
    c.entity = entity;
    c.value = value;
    return c;
}

RowFn issue(sim::Command c) {
    return [c](GameSession& s, int, RowEffects&) { s.issue(c); };
}

void house_lines(const sim::Game& game, const sim::Building& b, std::vector<std::string>& lines) {
    const sim::BuildingDef& d = game.content().buildings[b.def];
    lines.push_back(tr("hud.house.level", static_cast<int>(b.level) + 1, static_cast<int>(d.levels.size()) + 1));
    lines.push_back(tr("hud.house.happiness", b.happiness, b.desirability));
    // Phase 104: its garden and the flowers around it.
    if ((b.garden & sim::garden::kHouse) != 0) {
        for (const sim::BuildingDef& gd : game.content().buildings) {
            if (gd.garden_house) {
                lines.push_back(tr("hud.house.garden", gd.garden_desirability));
                break;
            }
        }
    }
    if (b.cat != 0) {
        lines.push_back(tr("hud.house.cat", sim::village::kCatBeauty));
    }
    // Phase 112: a unicorn grazing near.
    if (game.unicorn_near(b.x + b.width / 2, b.z + b.depth / 2, sim::village::kUnicornMeters)) {
        lines.push_back(tr("hud.house.unicorn", sim::village::kUnicornBeauty));
        lines.push_back(tr("hud.house.unicornHeals"));
    }
    // Phase 113: the mood a happening left in the town.
    if (const std::int32_t mood = game.town_mood(b.owner); mood > 0) {
        lines.push_back(tr("hud.house.mood", mood));
    }
    if (const std::int32_t flowers = game.flower_beauty(b); flowers > 0) {
        lines.push_back(tr("hud.house.flowers", flowers));
    }
    // Phase 103: the annexes that serve it (the window wraps the line).
    if (b.annexes != 0) {
        std::string list;
        for (const sim::BuildingDef& ad : game.content().buildings) {
            if (ad.annex_bit >= 0 && ((b.annexes >> ad.annex_bit) & 1u) != 0) {
                list += (list.empty() ? "" : ", ") + tr(ad.name_key);
            }
        }
        if (!list.empty()) {
            lines.push_back(tr("hud.house.annexes", list));
        }
    }
    if (b.upgrading) {
        lines.push_back(tr("hud.house.upgrading"));
    } else if (b.level < d.levels.size()) {
        // What the next level still needs.
        const sim::LevelDef& next = d.levels[b.level];
        std::string missing;
        for (std::uint8_t n = 0; n < static_cast<std::uint8_t>(sim::Need::Count); ++n) {
            const bool needed = ((next.needs >> n) & 1u) != 0;
            const bool met = ((b.needs >> n) & 1u) != 0;
            if (needed && !met) {
                missing += (missing.empty() ? "" : ", ") + tr(need_text_key(n));
            }
        }
        if (next.tier > game.tier(b.owner)) {
            missing += (missing.empty() ? "" : ", ") + tr("hud.house.needsTier", next.tier);
        }
        lines.push_back(missing.empty() ? tr("hud.house.readyToGrow") : tr("hud.house.missing", missing));
    }
}

// Its residents or its workers, each a link to its own window.
void people_rows(ThingRows& out, const sim::Game& game, const std::vector<sim::EntityId>& list, const char* title_key) {
    if (list.empty()) {
        return;
    }
    WinRow& row = out.line(tr(title_key, static_cast<int>(list.size())), WinRow::Kind::People);
    for (const sim::EntityId id : list) {
        const sim::Villager* v = game.villagers().get(id);
        if (v == nullptr) {
            continue;
        }
        std::string name = game.villager_name(*v);
        if (name.empty()) {
            name = tr(v->sex == sim::Sex::Female ? "hud.villager.woman" : "hud.villager.man");
        }
        RowPerson p;
        const std::string key = portrait_key(game.content(), *v);
        p.image = key.empty() ? std::string() : "/thumbs/" + key;
        p.name = tr("hud.villager.listed", name, game.age_years(*v));
        p.sub = tr(task_text_key(v->task));
        p.act = static_cast<int>(out.acts.size());
        out.acts.push_back([id](GameSession&, int, RowEffects& e) {
            e.link = true;
            e.kind = WindowList::Kind::Villager;
            e.entity = id;
        });
        row.people.push_back(std::move(p));
    }
    row.tip = tr("hud.villager.open.tooltip");
}

void farm_fields(ThingRows& out, const GameSession& s, const sim::Building& b, sim::EntityId entity) {
    const sim::Content& content = s.game().content();
    static constexpr const char* kStateKeys[] = {"hud.farm.waiting", "hud.farm.growing", "hud.farm.ripe", "hud.farm.done"};
    const auto crop_name = [&](sim::DefIndex c) {
        return c < content.crops.size() ? tr(content.crops[c].name_key) : tr("hud.farm.fallow");
    };
    for (std::size_t i = 0; i < b.fields.size(); ++i) {
        const sim::Field& f = b.fields[i];
        std::string state = tr(kStateKeys[static_cast<std::size_t>(f.state) % 4]);
        if (f.state == sim::FieldState::Growing) {
            state = tr("hud.farm.growingPercent", f.growth / 10);
        } else if (f.state == sim::FieldState::Done && f.plan[f.slot] == sim::kNoDef) {
            state = tr("hud.farm.resting");
        }
        out.line(tr("hud.farm.field", static_cast<int>(i + 1), f.w, f.d, f.fertility, state), WinRow::Kind::Dim);
        // The three years of the plan; this year's is highlighted. A click
        // moves to the next crop (fallow last).
        std::vector<RowButton> row;
        for (std::size_t year = 0; year < sim::kPlanYears; ++year) {
            sim::DefIndex next = sim::kNoDef;
            if (f.plan[year] == sim::kNoDef) {
                next = content.crops.empty() ? sim::kNoDef : 0;
            } else if (f.plan[year] + 1u < content.crops.size()) {
                next = static_cast<sim::DefIndex>(f.plan[year] + 1);
            }
            sim::Command c = command(sim::CommandType::SetCrop, entity,
                                     static_cast<std::int32_t>(i) | static_cast<std::int32_t>(year << 8));
            c.def = next;
            row.push_back(out.button(crop_name(f.plan[year]), tr("hud.farm.plan.tooltip"), issue(c), true, year == f.slot));
        }
        RowButton remove = out.button({}, tr("hud.farm.remove.tooltip"),
                                      issue(command(sim::CommandType::RemoveField, entity, static_cast<std::int32_t>(i))));
        remove.icon = "icon-x";
        row.push_back(std::move(remove));
        out.buttons(std::move(row));
    }
    const bool room = static_cast<std::int32_t>(b.fields.size()) < content.buildings[b.def].fields;
    out.buttons({out.button(
        tr("hud.farm.newField"), tr(room ? "hud.farm.newField.tooltip" : "hud.farm.full"),
        [entity](GameSession& gs, int, RowEffects&) {
            gs.ui().field_farm = entity;
            gs.ui().placing = sim::kNoDef;
        },
        room, s.ui().field_farm == entity)});
}

// What the merchant sells, and what the town has to sell him.
std::vector<sim::DefIndex> merchant_rows(const sim::Game& game, std::uint8_t town) {
    std::vector<sim::DefIndex> rows;
    for (const sim::MerchantGood& m : game.player(town).merchant) {
        if ((m.stock > 0 || (m.sell > 0 && game.tradeable(town, m.resource) >= 10)) && rows.size() < 14) {
            rows.push_back(m.resource);
        }
    }
    return rows;
}

std::string goods_name(const sim::Game& game, sim::DefIndex r) {
    return r < game.content().resources.size() ? tr(game.content().resources[r].name_key) : std::string();
}

void merchant(ThingRows& out, const GameSession& s, sim::EntityId entity) {
    const sim::Game& game = s.game();
    const std::uint8_t town = s.town();
    const sim::PlayerState& ps = game.player(town);
    if (!game.merchant_here(town)) {
        const std::uint64_t next = ps.merchant_arrives > game.tick() ? ps.merchant_arrives - game.tick() : 0;
        const auto days = static_cast<int>((next + game.calendar_day_ticks() - 1) / game.calendar_day_ticks());
        out.line(ps.merchant_arrives == 0 ? tr("hud.merchant.none") : tr("hud.merchant.next", days), WinRow::Kind::Dim);
        return;
    }
    const std::uint64_t left = ps.merchant_leaves - game.tick();
    out.line(tr("hud.merchant.here", static_cast<int>((left + game.calendar_day_ticks() - 1) / game.calendar_day_ticks())),
             WinRow::Kind::Accent);
    for (const sim::DefIndex r : merchant_rows(game, town)) {
        const sim::MerchantGood* m = nullptr;
        for (const sim::MerchantGood& g : ps.merchant) {
            m = g.resource == r ? &g : m;
        }
        if (m == nullptr) {
            continue;
        }
        const std::int32_t have = game.tradeable(town, r);
        const std::int32_t buy = std::min(10, m->stock);
        const std::int32_t sell = std::min(10, have);
        const auto trade = [&](std::int32_t n) {
            sim::Command c = command(sim::CommandType::Trade, entity, n);
            c.def = r;
            return issue(c);
        };
        out.stepper(tr("hud.merchant.row", goods_name(game, r), have, m->stock),
                    out.button(tr("hud.merchant.buy"), tr("hud.merchant.buy.tooltip", buy, buy * m->buy), trade(buy),
                               buy > 0 && game.gold(town) >= buy * m->buy),
                    out.button(tr("hud.merchant.sell"), tr("hud.merchant.sell.tooltip", sell, sell * m->sell), trade(-sell),
                               sell > 0 && m->sell > 0));
    }
}

// The goods merchants trade, which automatic trade can name.
std::vector<sim::DefIndex> rule_goods(const sim::Content& content) {
    std::vector<sim::DefIndex> out;
    for (std::size_t r = 0; r < content.resources.size(); ++r) {
        if (content.resources[r].value > 0) {
            out.push_back(static_cast<sim::DefIndex>(r));
        }
    }
    return out;
}

// "Sell over N, buy under M" for one good at a time, applied with a
// button; the rules in force listed below.
void auto_trade(ThingRows& out, const GameSession& s, TradeDraft& draft) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const std::vector<sim::DefIndex> goods = rule_goods(content);
    const std::vector<sim::TradeRule>& rules = game.player(s.town()).trade_rules;
    out.line(tr("hud.auto.title"), WinRow::Kind::Section).tip = tr("hud.auto.tooltip");
    if (goods.empty()) {
        return;
    }
    draft.pick = std::clamp(draft.pick, 0, static_cast<int>(goods.size()) - 1);
    const sim::DefIndex picked = goods[static_cast<std::size_t>(draft.pick)];
    const sim::TradeRule* current = nullptr;
    for (const sim::TradeRule& rule : rules) {
        current = rule.resource == picked ? &rule : current;
    }
    if (draft.loaded != draft.pick) {
        // A new good: show its rule, or none.
        draft.loaded = draft.pick;
        draft.sell = current != nullptr && current->sell_above != sim::kNoRule ? current->sell_above : -10;
        draft.buy = current != nullptr && current->buy_below != sim::kNoRule ? current->buy_below : -10;
        draft.sell_min = current != nullptr && current->sell_min != 0 ? current->sell_min : 70;
        draft.buy_max = current != nullptr && current->buy_max != 0 ? current->buy_max : 70;
    }
    TradeDraft* d = &draft;
    const int count = static_cast<int>(goods.size());
    // The good: the arrows go through them.
    RowButton prev = out.button({}, {}, [d, count](GameSession&, int, RowEffects&) { d->pick = (d->pick + count - 1) % count; });
    prev.icon = "icon-left";
    RowButton next = out.button({}, {}, [d, count](GameSession&, int, RowEffects&) { d->pick = (d->pick + 1) % count; });
    next.icon = "icon-right";
    out.stepper(tr(content.resources[picked].name_key), std::move(prev), std::move(next));
    const auto slider = [&](std::string text, std::string tip, int value, int lo, int hi, int step, bool enabled, int* field) {
        out.line(std::move(text)).tip = tip;
        WinRow& row = out.line({}, WinRow::Kind::Slider);
        row.tip = std::move(tip);
        row.value = value;
        row.min = lo;
        row.max = hi;
        row.step = step;
        row.enabled = enabled;
        row.act = out.add_act([field](GameSession&, int v, RowEffects&) { *field = v; });
    };
    const auto amount = [](const char* key, int v) { return v < 0 ? tr("hud.auto.off") : tr(key, v); };
    // Only at a good price: over a share of the good's value when selling.
    const auto price = [](const char* key, int v) { return v < sim::kMinPriceLimit ? tr("hud.auto.anyPrice") : tr(key, v); };
    slider(amount("hud.auto.sell", draft.sell), tr("hud.auto.sell.tooltip"), draft.sell, -10, 2000, 10, true, &d->sell);
    slider(price("hud.auto.sellMin", draft.sell_min), tr("hud.auto.sellMin.tooltip"), draft.sell_min, 70,
           sim::kMaxPriceLimit, 5, draft.sell >= 0, &d->sell_min);
    slider(amount("hud.auto.buy", draft.buy), tr("hud.auto.buy.tooltip"), draft.buy, -10, 2000, 10, true, &d->buy);
    slider(price("hud.auto.buyMax", draft.buy_max), tr("hud.auto.buyMax.tooltip"), draft.buy_max, 70, sim::kMaxPriceLimit,
           5, draft.buy >= 0, &d->buy_max);
    const std::int32_t sell = draft.sell < 0 ? sim::kNoRule : draft.sell;
    const std::int32_t buy = draft.buy < 0 ? sim::kNoRule : draft.buy;
    const bool valid = sell == sim::kNoRule || buy == sim::kNoRule || buy <= sell;
    const int sell_min = sell == sim::kNoRule || draft.sell_min < sim::kMinPriceLimit ? 0 : draft.sell_min;
    const int buy_max = buy == sim::kNoRule || draft.buy_max < sim::kMinPriceLimit ? 0 : draft.buy_max;
    const bool same = current != nullptr ? current->sell_above == sell && current->buy_below == buy &&
                                               current->sell_min == sell_min && current->buy_max == buy_max
                                         : sell == sim::kNoRule && buy == sim::kNoRule;
    sim::Command c;
    c.type = sim::CommandType::SetTradeRule;
    c.def = picked;
    c.value = sell;
    c.value2 = buy;
    c.count = static_cast<std::uint16_t>(sell_min);
    c.def2 = static_cast<std::uint16_t>(buy_max);
    out.buttons({out.button(tr("hud.auto.apply"), valid ? tr("hud.auto.apply.tooltip") : tr("hud.auto.apply.invalid"),
                            issue(c), valid && !same)});
    // The rules in force.
    out.line(tr(rules.empty() ? "hud.auto.none" : "hud.auto.rules"), WinRow::Kind::Dim);
    for (std::size_t i = 0; i < rules.size() && i < 8; ++i) {
        const sim::TradeRule& rule = rules[i];
        std::string parts;
        if (rule.sell_above != sim::kNoRule) {
            parts = tr("hud.auto.sell", rule.sell_above);
            if (rule.sell_min != 0) {
                parts += " (" + tr("hud.auto.sellMin", static_cast<int>(rule.sell_min)) + ")";
            }
        }
        if (rule.buy_below != sim::kNoRule) {
            parts += (parts.empty() ? "" : " · ") + tr("hud.auto.buy", rule.buy_below);
            if (rule.buy_max != 0) {
                parts += " (" + tr("hud.auto.buyMax", static_cast<int>(rule.buy_max)) + ")";
            }
        }
        out.line(tr("hud.auto.rule", goods_name(game, rule.resource), parts));
    }
}

void barracks(ThingRows& out, const GameSession& s, const sim::Building& b, sim::EntityId entity) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    // What is being trained.
    std::string queue = tr("hud.barracks.idle");
    if (!b.training.empty() && b.training.front() < content.units.size()) {
        const sim::UnitDef& u = content.units[b.training.front()];
        queue = tr("hud.barracks.training", tr(u.name_key), static_cast<int>(b.training.size()));
    }
    RowButton cancel = out.button(tr("hud.barracks.cancel"), tr("hud.barracks.cancel.tooltip"),
                                  issue(command(sim::CommandType::TrainUnit, entity, 0)), !b.training.empty());
    out.stepper(queue, std::move(cancel), RowButton{});
    if (!b.training.empty() && b.training.front() < content.units.size()) {
        out.line({}, WinRow::Kind::Meter).fraction =
            static_cast<float>(b.train_progress) / static_cast<float>(std::max(1, content.units[b.training.front()].train_work));
    }
    for (std::size_t i = 0; i < content.units.size(); ++i) {
        const sim::UnitDef& u = content.units[i];
        std::string cost;
        for (const sim::ResourceAmount& c : u.cost) {
            cost += (cost.empty() ? "" : ", ") + tr("hud.amount", tr(content.resources[c.resource].name_key), c.amount);
        }
        const bool locked = u.tier > game.tier(b.owner);
        sim::Command c = command(sim::CommandType::TrainUnit, entity, 1);
        c.def = static_cast<sim::DefIndex>(i);
        out.stepper(locked ? tr("hud.barracks.locked", tr(u.name_key), static_cast<int>(u.tier))
                           : tr("hud.barracks.unit", tr(u.name_key), cost),
                    out.button(tr("hud.barracks.train"), tr("hud.barracks.train.tooltip", u.health, u.damage, u.range),
                               issue(c), !locked && b.training.size() < 10),
                    RowButton{});
        if (locked) {
            out.rows.back().cls = "locked";
        }
    }
}

// The "keep N" of a workshop or the reserve of a trading post.
void limit_row(ThingRows& out, std::string text, const char* tip_key, sim::EntityId entity, std::int32_t limit,
               std::int32_t step, std::int32_t most, bool can_more) {
    const auto set = [&](std::int32_t n) { return issue(command(sim::CommandType::SetLimit, entity, std::clamp(n, 0, 10000))); };
    RowButton less = out.button({}, tr(tip_key), set(limit - step), limit > 0);
    less.icon = "icon-minus";
    RowButton more = out.button({}, tr(tip_key), set(std::min(limit + step, most)), can_more);
    more.icon = "icon-plus";
    out.stepper(std::move(text), std::move(less), std::move(more));
}

}  // namespace

int ThingRows::add_act(RowFn fn) {
    acts.push_back(std::move(fn));
    return static_cast<int>(acts.size()) - 1;
}

WinRow& ThingRows::line(std::string text, WinRow::Kind kind) {
    WinRow row;
    row.kind = kind;
    row.text = std::move(text);
    rows.push_back(std::move(row));
    return rows.back();
}

RowButton ThingRows::button(std::string label, std::string tip, RowFn fn, bool enabled, bool on) {
    RowButton b;
    b.label = std::move(label);
    b.tip = std::move(tip);
    b.enabled = enabled;
    b.on = on;
    b.act = add_act(std::move(fn));
    return b;
}

void ThingRows::buttons(std::vector<RowButton> list) {
    line({}, WinRow::Kind::Buttons).buttons = std::move(list);
}

void ThingRows::stepper(std::string text, RowButton minus, RowButton plus) {
    WinRow& row = line(std::move(text), WinRow::Kind::Stepper);
    for (RowButton* b : {&minus, &plus}) {
        if (b->act >= 0) {
            row.buttons.push_back(std::move(*b));
        }
    }
}

ThingRows building_rows(const GameSession& s, sim::EntityId entity, TradeDraft& draft) {
    const sim::Game& game = s.game();
    const sim::Content& content = game.content();
    const sim::Building* b = game.buildings().get(entity);
    if (b == nullptr) {
        return gone_rows(WindowList::Kind::Building);
    }
    ThingRows out;
    const sim::BuildingDef& d = content.buildings[b->def];
    out.icon = "/thumbs/building/" + d.id;
    std::replace(out.icon.begin(), out.icon.end(), ':', '/');

    // The lines, as the old window had them.
    std::vector<std::string> lines;
    if (b->damage > 0) {
        lines.push_back(tr("hud.building.damage", b->damage * 100 / std::max(1, d.hp)));
    }
    if (d.attack_range > 0 && b->state == sim::BuildingState::Complete) {
        lines.push_back(tr("hud.building.tower", d.attack_range, d.attack_damage));
    }
    if (d.trap && b->state == sim::BuildingState::Complete) {
        lines.push_back(tr(b->rearm > 0 ? "hud.building.trapRearming" : "hud.building.trapArmed"));
    }
    if (d.light > 0 && b->state == sim::BuildingState::Complete && game.rules().day_night.enabled()) {
        lines.push_back(tr("hud.building.light", d.light));
    }
    if (d.warmth > 0 && b->state == sim::BuildingState::Complete) {
        lines.push_back(tr("hud.building.campfire", d.warmth));
        if (!b->heated) {
            lines.push_back(tr("hud.building.campfireOut"));
        }
    }
    if (b->fire > 0) {
        lines.push_back(tr("hud.building.fire", b->fire, b->burned / 10));
    } else if (b->burned > 0) {
        lines.push_back(tr("hud.building.burned", b->burned / 10));
    }
    float progress = -1.0f;
    if (b->state == sim::BuildingState::Construction) {
        progress = d.build_work > 0 ? static_cast<float>(b->work_done) / static_cast<float>(d.build_work) : 1.0f;
        lines.push_back(tr("hud.building.construction", static_cast<int>(std::lround(progress * 100.0f))));
        if (const std::int32_t trees = game.trees_on_site(*b); trees > 0) {
            lines.push_back(i18n::tr_n("hud.building.clearing", trees));  // Phase 88.
        }
        for (const sim::ResourceAmount& c : d.cost) {
            std::int32_t have = 0;
            for (const sim::Stock& st : b->delivered) {
                have += st.resource == c.resource ? st.amount : 0;
            }
            lines.push_back(tr("hud.building.material", tr(content.resources[c.resource].name_key), have, c.amount));
        }
    } else {
        if ((b->garden & sim::garden::kFormal) != 0) {
            lines.push_back(tr("hud.decor.formal"));
        }
        if (game.fells_by_unicorn(b->def, b->x, b->z)) {
            lines.push_back(tr("hud.unicorn.fells"));  // Phase 112.
        }
        if (d.hunt_arms != sim::kNoDef) {
            // Phase 111: the mammoths within its reach (none: it says nothing), and its weapons.
            if (const sim::Game::BigGame big = game.big_game(*b); big.zones > 0) {
                lines.push_back(big.animals > 0 ? tr("hud.lodge.mammoths", big.animals) : tr("hud.lodge.mammothsWinter"));
                std::int32_t arms = 0;
                for (const sim::Stock& st : b->stock) {
                    arms += st.resource == d.hunt_arms ? st.amount : 0;
                }
                lines.push_back(tr("hud.lodge.arms", arms, sim::village::kLodgeArms));
                if (b->workers.size() < 2) {
                    lines.push_back(tr("hud.lodge.two"));
                }
            }
        }
        if (d.work == sim::WorkKind::Fish) {
            // Phase 110: what it has within its reach, and how its shoals are.
            const sim::Game::FishSpots spots = game.fish_spots(*b);
            lines.push_back(spots.spent > 0 ? tr("hud.fisher.shoalsSpent", spots.shoals, spots.spent)
                                            : tr("hud.fisher.shoals", spots.shoals));
            lines.push_back(tr("hud.fisher.reeds", spots.reeds));
            if (spots.ducks > 0) {
                lines.push_back(tr("hud.fisher.ducks"));
            }
            lines.push_back(tr("hud.fisher.pace", sim::Game::fish_percent(spots) * 100 / sim::village::kFishMost));
        }
        if (d.coop_gives != sim::kNoDef) {
            lines.push_back(tr("hud.coop.hens", static_cast<int>(b->flock), d.coop_hens));
            std::int32_t grain = 0;
            for (const sim::DefIndex feed : d.coop_feed) {
                for (const sim::Stock& st : b->stock) {
                    grain += st.resource == feed ? st.amount : 0;
                }
            }
            const std::int32_t fed = b->produced + grain * d.coop_feed_days;
            lines.push_back(fed > 0 ? tr("hud.coop.fed", fed) : tr("hud.coop.hungry"));
            lines.push_back(tr(game.coop_safe(*b) ? "hud.coop.safe" : "hud.coop.unsafe"));
        }
        if (d.guard_radius > 0) {
            lines.push_back(tr("hud.guard.dog"));
            lines.push_back(tr("hud.guard.wolf"));
            lines.push_back(tr("hud.guard.coops", d.guard_radius));
        }
        if (d.hive_gives != sim::kNoDef) {
            if (game.calendar().season == sim::Season::Winter) {
                lines.push_back(tr("hud.hive.winter"));
            } else {
                lines.push_back(tr("hud.hive.flowers", d.hive_radius,
                                   game.per_year(game.nectar(*b)) * 100 / sim::village::kNectarPerUnit));
            }
        }
        if (d.annex) {
            lines.push_back(tr("hud.annex.serves", d.annex_radius));
            if (d.annex_desirability != 0) {
                lines.push_back(tr("hud.annex.desirability", d.annex_desirability));
            }
            if (d.annex_need != sim::kNoNeed) {
                lines.push_back(tr("hud.annex.need", tr(need_text_key(d.annex_need))));
            }
            if (d.annex_happiness != 0) {
                lines.push_back(tr("hud.annex.happiness", d.annex_happiness));
            }
            if (d.annex_children) {
                lines.push_back(tr("hud.annex.children"));
            }
            if (d.annex_firewood > 0) {
                lines.push_back(tr("hud.annex.firewood", d.annex_firewood));
            }
            if (d.annex_rain) {
                lines.push_back(tr(game.barrels_full() ? "hud.annex.barrelFull" : "hud.annex.barrelEmpty"));
            }
        }
        if (d.residents > 0) {
            lines.push_back(tr("hud.building.residents", static_cast<int>(b->residents.size()), d.residents));
            if (d.kind == sim::BuildingKind::House) {
                house_lines(game, *b, lines);
                const sim::DefIndex fw = content.find_resource("core:firewood");
                std::int32_t wood = 0;
                for (const sim::Stock& st : b->stock) {
                    wood += st.resource == fw ? st.amount : 0;
                }
                lines.push_back(tr("hud.building.firewood", wood, game.firewood_room(*b)));
                if (!b->heated) {
                    lines.push_back(tr("hud.building.cold"));
                }
            }
        }
        if (d.storage > 0) {
            std::int32_t total = 0;
            for (const sim::Stock& st : b->stock) {
                total += st.amount;
            }
            lines.push_back(tr("hud.building.storage", total, d.storage));
            for (const sim::Stock& st : b->stock) {
                if (st.amount > 0 && lines.size() < (d.trade ? 4u : 16u)) {
                    lines.push_back("  " + tr("hud.amount", tr(content.resources[st.resource].name_key), st.amount));
                }
            }
        }
    }
    if (const char* key = supply_key(d, *b)) {
        lines.push_back(tr(key));
    }
    const bool mine = b->owner == s.town();
    const bool complete = b->state == sim::BuildingState::Complete;
    const bool has_workers = d.workers > 0 && complete;
    const sim::HerdDef* herd = complete ? game.herd_of(*b) : nullptr;  // Phase 107.
    if (herd != nullptr) {
        lines.push_back(tr(b->males > 0 ? "hud.fold.herd" : "hud.fold.herdNoMale", tr(herd->name_key), static_cast<int>(b->females)));
        if (b->fields.empty()) {
            lines.push_back(tr("hud.fold.noPasture"));
        } else {
            lines.push_back(tr("hud.fold.pasture", b->fields[0].w, b->fields[0].d, game.herd_room(*b)));
        }
        if (b->workers.empty()) {
            lines.push_back(tr("hud.fold.shepherd"));
        }
    }

    // Its picture, with whether it works.
    WinRow& hero = out.line({}, WinRow::Kind::Hero);
    hero.image = out.icon;
    if (has_workers) {
        hero.text = tr(b->stopped ? "hud.building.stopped" : "hud.building.working");
        hero.cls = b->stopped ? "warn" : "ok";
    }
    // The switch stops its work and lets its workers go (it remembers how
    // many it wanted).
    if (has_workers && mine) {
        out.buttons({out.button(tr(b->stopped ? "hud.building.stopped" : "hud.building.working"),
                                tr("hud.building.production.tooltip"),
                                issue(command(sim::CommandType::SetProduction, entity, b->stopped ? 1 : 0)), true,
                                b->stopped)});
    }
    // Phase 85: the options of a workplace.
    const std::uint8_t options = mine && complete ? sim::workplace_options(d) : std::uint8_t{0};
    for (const WorkplaceOption& o : workplace_option_list()) {
        if ((options & o.bit) == 0) {
            continue;
        }
        const bool on = (b->options & o.bit) != 0;
        sim::Command c = command(sim::CommandType::SetOption, entity, on ? 0 : 1);
        c.count = o.number;
        out.buttons({out.button(tr(on ? o.on : o.off), tr(o.tooltip), issue(c), true, on)});
    }
    if (progress >= 0.0f) {
        out.line({}, WinRow::Kind::Meter).fraction = progress;
    }
    for (std::string& l : lines) {
        out.line(std::move(l));
    }
    if (mine && complete) {
        people_rows(out, game, b->residents, "hud.building.residentList");
        people_rows(out, game, b->workers, "hud.building.workerList");
    }
    if (has_workers) {
        const auto set_workers = [&](std::int32_t n) { return issue(command(sim::CommandType::SetWorkers, entity, n)); };
        RowButton fewer = out.button({}, tr("hud.building.fewer.tooltip"), set_workers(b->wanted_workers - 1),
                                     b->wanted_workers > 0);
        fewer.icon = "icon-minus";
        RowButton more = out.button({}, tr("hud.building.more.tooltip"), set_workers(b->wanted_workers + 1),
                                    b->wanted_workers < d.workers);
        more.icon = "icon-plus";
        more.mark = "workers";
        out.stepper(tr("hud.building.workers", static_cast<int>(b->workers.size()), b->wanted_workers, d.workers),
                    std::move(fewer), std::move(more));
    }
    if (d.work == sim::WorkKind::Farm && complete) {
        farm_fields(out, s, *b, entity);
    }
    if (herd != nullptr && mine) {
        // Its pasture: marked like a field, or taken away; and another male when it has none.
        if (b->fields.empty()) {
            out.buttons({out.button(
                tr("hud.fold.mark"), tr("hud.fold.mark.tooltip"),
                [entity](GameSession& gs, int, RowEffects&) {
                    gs.ui().field_farm = entity;
                    gs.ui().placing = sim::kNoDef;
                },
                true, s.ui().field_farm == entity)});
        } else {
            out.buttons({out.button(tr("hud.fold.unmark"), tr("hud.fold.marked"),
                                    issue(command(sim::CommandType::RemoveField, entity, 0)))});
        }
        for (std::size_t k = 0; k < d.herds.size(); ++k) {
            if (k == b->herd || d.herds[k] >= content.herds.size()) {
                continue;
            }
            // Phase 108: another herd in this fold.
            out.buttons({out.button(tr("hud.fold.change", tr(content.herds[d.herds[k]].name_key)),
                                    tr("hud.fold.change.tooltip"),
                                    issue(command(sim::CommandType::SetHerd, entity, static_cast<std::int32_t>(k))))});
        }
        if (b->males == 0) {
            const bool rich = game.gold(s.town()) >= herd->male_price;
            out.buttons({out.button(tr("hud.fold.buyMale", herd->male_price),
                                    tr(rich ? "hud.fold.buyMale.tooltip" : "hud.fold.buyMale.poor"),
                                    issue(command(sim::CommandType::BuyMale, entity)), rich)});
        }
    }
    if (d.trade && complete) {
        // How much gold to keep here, for buying (phase 28).
        limit_row(out, tr("hud.post.reserve", b->limit), "hud.post.reserve.tooltip", entity, b->limit, 50, d.storage,
                  b->limit < d.storage);
        merchant(out, s, entity);
        auto_trade(out, s, draft);
    }
    if (d.trains && complete) {
        barracks(out, s, *b, entity);
    }
    if (d.work == sim::WorkKind::Produce && complete) {
        // How much of its product to keep: automatic, or a set amount.
        limit_row(out, b->limit > 0 ? tr("hud.building.limit", b->limit) : tr("hud.building.limitAuto"),
                  "hud.building.limit.tooltip", entity, b->limit, 10, 10000, true);
    }
    if (d.kind == sim::BuildingKind::TownCenter && complete) {
        out.line(tr("hud.tc.level", game.tier(b->owner)), WinRow::Kind::Section);
        const bool has_next = b->level < d.levels.size();
        std::string req = tr("hud.tc.max");
        bool can = false;
        if (has_next) {
            const sim::LevelDef& next = d.levels[b->level];
            std::string cost;
            for (const sim::ResourceAmount& c : next.cost) {
                cost += (cost.empty() ? "" : ", ") + tr("hud.amount", tr(content.resources[c.resource].name_key), c.amount);
            }
            req = b->upgrading ? tr("hud.tc.upgrading") : tr("hud.tc.next", next.population, cost);
            can = !b->upgrading && game.population(b->owner) >= next.population;
        }
        out.line(req, WinRow::Kind::Dim);
        out.buttons({out.button(tr("hud.tc.upgrade"), tr("hud.tc.upgrade.tooltip"),
                                issue(command(sim::CommandType::UpgradeBuilding, entity)), can)});
        // The bell: the militia.
        const bool alarm = game.player(b->owner).alarm;
        RowButton bell = out.button(tr(alarm ? "hud.bell.stop" : "hud.bell.ring"), tr("hud.bell.tooltip"),
                                    issue(command(sim::CommandType::RingBell, {}, alarm ? 0 : 1)), true, alarm);
        bell.icon = "icon-bell";
        out.buttons({std::move(bell)});
    }
    if (entity != game.player(s.town()).town_center && !d.cart) {
        const bool building = b->state == sim::BuildingState::Construction;
        RowButton remove = out.button(tr(building ? "hud.building.cancel" : "hud.building.demolish"),
                                      tr(building ? "hud.building.cancel.tooltip" : "hud.building.demolish.tooltip"),
                                      [entity](GameSession& gs, int, RowEffects& e) {
                                          gs.issue(command(sim::CommandType::RemoveBuilding, entity));
                                          e.close = true;
                                      });
        remove.icon = "icon-trash";
        remove.danger = true;
        out.buttons({std::move(remove)});
    }
    return out;
}

ThingRows gone_rows(WindowList::Kind kind) {
    ThingRows out;
    out.gone = true;
    out.line(tr(kind == WindowList::Kind::Building   ? "hud.window.gone.building"
                : kind == WindowList::Kind::Villager ? "hud.window.gone.villager"
                                                     : "hud.window.gone.thing"),
             WinRow::Kind::Dim);
    return out;
}

std::string rml_escape(std::string_view text) {
    std::string out;
    out.reserve(text.size());
    for (const char c : text) {
        switch (c) {
            case '&': out += "&amp;"; break;
            case '<': out += "&lt;"; break;
            case '>': out += "&gt;"; break;
            case '"': out += "&quot;"; break;
            case '\n': out += "<br/>"; break;
            default: out += c;
        }
    }
    return out;
}

namespace {

std::string tip_attr(const std::string& tip) {
    return tip.empty() ? std::string() : " tip=\"" + rml_escape(tip) + "\"";
}

std::string button_rml(const RowButton& b) {
    std::string cls = b.danger ? "btn danger" : "btn";
    if (b.on) {
        cls += " on";
    }
    if (!b.enabled) {
        cls += " off";
    }
    if (b.label.empty()) {
        cls += " square";
    }
    std::string out = "<div class=\"" + cls + "\"";
    if (b.enabled && b.act >= 0) {
        out += std::format(" data-act=\"{}\"", b.act);
    }
    out += tip_attr(b.tip);
    if (!b.mark.empty()) {
        out += " mark=\"" + rml_escape(b.mark) + "\"";
    }
    out += ">";
    if (!b.icon.empty()) {
        out += "<img sprite=\"" + rml_escape(b.icon) + "\"/>";
    }
    if (!b.label.empty()) {
        out += "<span>" + rml_escape(b.label) + "</span>";
    }
    return out + "</div>";
}

std::string row_rml(const WinRow& row, bool with_value) {
    const std::string extra = row.cls.empty() ? std::string() : " " + rml_escape(row.cls);
    switch (row.kind) {
        case WinRow::Kind::Text:
        case WinRow::Kind::Dim:
        case WinRow::Kind::Accent:
        case WinRow::Kind::Section: {
            static constexpr const char* kClass[] = {"line", "line dim", "line accent", "section"};
            return std::format("<div class=\"{}{}\"{}>{}</div>", kClass[static_cast<int>(row.kind)], extra, tip_attr(row.tip),
                               rml_escape(row.text));
        }
        case WinRow::Kind::Hero: {
            std::string out = "<div class=\"hero\"><img src=\"" + rml_escape(row.image) + "\"/>";
            if (!row.text.empty()) {
                out += "<span class=\"chip " + rml_escape(row.cls) + "\">" + rml_escape(row.text) + "</span>";
            }
            return out + "</div>";
        }
        case WinRow::Kind::Meter:
            return std::format("<div class=\"meter\"><div class=\"fill\" style=\"width: {:.1f}%;\"></div></div>",
                               std::clamp(row.fraction, 0.0f, 1.0f) * 100.0f);
        case WinRow::Kind::Buttons: {
            std::string out = "<div class=\"btns\">";
            for (const RowButton& b : row.buttons) {
                out += button_rml(b);
            }
            return out + "</div>";
        }
        case WinRow::Kind::Stepper: {
            std::string out = "<div class=\"kv" + extra + "\"" + tip_attr(row.tip) + "><span class=\"k\">" +
                              rml_escape(row.text) + "</span><div class=\"v\">";
            for (const RowButton& b : row.buttons) {
                out += button_rml(b);
            }
            return out + "</div></div>";
        }
        case WinRow::Kind::People: {
            std::string out = "<div class=\"section dim\">" + rml_escape(row.text) + "</div><div class=\"people\">";
            for (const RowPerson& p : row.people) {
                out += "<div class=\"row\"";
                if (p.act >= 0) {
                    out += std::format(" data-act=\"{}\"", p.act);
                }
                out += tip_attr(row.tip) + ">";
                if (!p.image.empty()) {
                    out += "<img class=\"avatar\" src=\"" + rml_escape(p.image) + "\"/>";
                }
                out += "<div class=\"who\"><div>" + rml_escape(p.name) + "</div><div class=\"dim\">" + rml_escape(p.sub) +
                       "</div></div></div>";
            }
            return out + "</div>";
        }
        case WinRow::Kind::Slider: {
            std::string out = std::format("<input type=\"range\" class=\"slider\" min=\"{}\" max=\"{}\" step=\"{}\"", row.min,
                                          row.max, row.step);
            if (with_value) {
                out += std::format(" value=\"{}\"", row.value);
            }
            if (row.act >= 0) {
                out += std::format(" data-act=\"{}\"", row.act);
            }
            if (!row.enabled) {
                out += " disabled=\"\"";
            }
            return out + tip_attr(row.tip) + "/>";
        }
    }
    return {};
}

}  // namespace

std::string row_rml(const WinRow& row) {
    return row_rml(row, true);
}

std::string row_key(const WinRow& row) {
    return row_rml(row, false);
}

}  // namespace sc
