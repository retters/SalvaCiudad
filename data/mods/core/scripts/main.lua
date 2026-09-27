-- Rules of the core mod written in Lua (docs/CREAR_MODS.md).

-- Tutorial "basics": ready for the winter with 60 firewood stored.
function tutorial_winter_ready(state)
  return (state.stored["core:firewood"] or 0) >= 60
end
