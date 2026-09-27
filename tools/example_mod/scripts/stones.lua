-- Helpers for the example mod, loaded with require("stones").
local M = {}

-- `count` stones on a circle of `radius` centimeters around (cx, cz).
function M.circle(map, cx, cz, radius, count)
  local step = 360 // count
  for i = 0, count - 1 do
    local a = i * step
    local x = cx + math.cos_deg(a) * radius // 10000
    local z = cz + math.sin_deg(a) * radius // 10000
    map.add_feature("stone", x, z, 150)
  end
end

return M
