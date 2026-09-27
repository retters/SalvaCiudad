-- Example rule: a circle of standing stones around every start position,
-- and one giant sequoia nearby. Coordinates are whole centimeters; only
-- whole numbers are used, so every player gets the same map.

local stones = require("stones")

function on_map_generated(map)
  for _, start in ipairs(map.starts) do
    stones.circle(map, start.x, start.z, 4500, 12)
    -- A landmark: a huge sequoia somewhere between 60 and 90 m away.
    local angle = map.random(360)
    local dist = 6000 + map.random(3000)
    local x = start.x + math.cos_deg(angle) * dist // 10000
    local z = start.z + math.sin_deg(angle) * dist // 10000
    map.add_tree("core:sequoia", "huge", x, z, 4000)
  end
  print("stone circles placed around " .. #map.starts .. " start(s)")
end
