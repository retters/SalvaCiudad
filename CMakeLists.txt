cmake_minimum_required(VERSION 3.25)

project(SalvasProsperia
    VERSION 0.20.0
    DESCRIPTION "Multiplayer medieval town-building survival game"
    LANGUAGES C CXX)

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "SalvasProsperia requires a 64-bit target.")
endif()
if(MSVC AND MSVC_TOOLSET_VERSION LESS 143)
    message(FATAL_ERROR "SalvasProsperia requires MSVC v143 (Visual Studio 2022) or newer. Found: ${MSVC_TOOLSET_VERSION}")
endif()

option(SC_ENABLE_ASAN "Build SalvasProsperia targets with AddressSanitizer" OFF)
option(SC_BUILD_TESTS "Build the automated tests" ON)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

if(MSVC)
    # Static CRT: the portable ZIP must not require a redistributable runtime.
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "ProgramDatabase")
    # CMake's defaults add /EHsc and /GR; exceptions and RTTI are chosen per
    # target in sc_harden_target instead.
    set(CMAKE_CXX_FLAGS "/DWIN32 /D_WINDOWS")
endif()

set(SC_GENERATED_DIR "${CMAKE_BINARY_DIR}/generated")
configure_file(src/version.h.in "${SC_GENERATED_DIR}/version.h" @ONLY)

# ---------------------------------------------------------------------------
# Compiler and linker flags for SalvasProsperia's own code (section 10 of the
# specification). Third-party code is built with its own flags.
# ---------------------------------------------------------------------------
if(MSVC)
    set(SC_COMPILE_OPTIONS
        /W4 /WX /sdl /GS /guard:cf /permissive- /utf-8 /Zc:__cplusplus
        /external:anglebrackets /external:W0)
    set(SC_CXX_ONLY_OPTIONS /EHs-c- /GR-)
    set(SC_COMPILE_DEFINITIONS
        UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX
        $<$<COMPILE_LANGUAGE:CXX>:_HAS_EXCEPTIONS=0>)
    set(SC_LINK_OPTIONS
        /DYNAMICBASE /NXCOMPAT /HIGHENTROPYVA /GUARD:CF /CETCOMPAT)
    if(SC_ENABLE_ASAN)
        list(APPEND SC_COMPILE_OPTIONS /fsanitize=address)
        get_filename_component(SC_MSVC_BIN_DIR "${CMAKE_CXX_COMPILER}" DIRECTORY)
    endif()
else()
    set(SC_COMPILE_OPTIONS
        -Wall -Wextra -Wpedantic -Werror -Wshadow -Wconversion -Wsign-conversion
        -fstack-protector-strong)
    set(SC_CXX_ONLY_OPTIONS -fno-exceptions -fno-rtti)
    set(SC_COMPILE_DEFINITIONS $<$<NOT:$<CONFIG:Debug>>:_FORTIFY_SOURCE=2>)
    set(SC_LINK_OPTIONS)
    if(SC_ENABLE_ASAN)
        list(APPEND SC_COMPILE_OPTIONS -fsanitize=address,undefined -fno-omit-frame-pointer)
        list(APPEND SC_LINK_OPTIONS -fsanitize=address,undefined)
    endif()
endif()

# Applies the project flags. `exceptions` is only allowed for the test runner,
# because doctest reports failures through them.
function(sc_harden_target target)
    set(options ALLOW_EXCEPTIONS)
    cmake_parse_arguments(ARG "${options}" "" "" ${ARGN})
    target_compile_options(${target} PRIVATE
        $<$<COMPILE_LANGUAGE:C,CXX>:${SC_COMPILE_OPTIONS}>)
    target_compile_definitions(${target} PRIVATE ${SC_COMPILE_DEFINITIONS})
    if(NOT ARG_ALLOW_EXCEPTIONS)
        target_compile_options(${target} PRIVATE
            $<$<COMPILE_LANGUAGE:CXX>:${SC_CXX_ONLY_OPTIONS}>)
    elseif(MSVC)
        target_compile_options(${target} PRIVATE $<$<COMPILE_LANGUAGE:CXX>:/EHsc /GR->)
    endif()
    get_target_property(target_type ${target} TYPE)
    if(target_type STREQUAL "EXECUTABLE")
        target_link_options(${target} PRIVATE ${SC_LINK_OPTIONS})
    endif()
endfunction()

# ---------------------------------------------------------------------------
# Third-party libraries (vendored, see third_party/README.md).
# ---------------------------------------------------------------------------
set(SDL_SHARED OFF CACHE BOOL "" FORCE)
set(SDL_STATIC ON CACHE BOOL "" FORCE)
set(SDL_TEST_LIBRARY OFF CACHE BOOL "" FORCE)
set(SDL_TESTS OFF CACHE BOOL "" FORCE)
set(SDL_EXAMPLES OFF CACHE BOOL "" FORCE)
set(SDL_INSTALL OFF CACHE BOOL "" FORCE)
add_subdirectory(third_party/SDL3 EXCLUDE_FROM_ALL SYSTEM)

add_library(yyjson STATIC third_party/yyjson/yyjson.c)
target_include_directories(yyjson SYSTEM PUBLIC third_party/yyjson)
# Only the parts we use: no incremental reader, no utilities.
target_compile_definitions(yyjson PUBLIC YYJSON_DISABLE_INCR_READER=1 YYJSON_DISABLE_UTILS=1)

# zstd: the library's C sources, without assembly or legacy formats.
file(GLOB SC_ZSTD_SOURCES CONFIGURE_DEPENDS third_party/zstd/common/*.c third_party/zstd/compress/*.c
     third_party/zstd/decompress/*.c)
add_library(zstd STATIC ${SC_ZSTD_SOURCES})
target_include_directories(zstd SYSTEM PUBLIC third_party/zstd)
target_compile_definitions(zstd PRIVATE ZSTD_DISABLE_ASM=1 ZSTD_LEGACY_SUPPORT=0 XXH_NAMESPACE=ZSTD_)

# ENet: reliable UDP for multiplayer (phase 9).
add_library(enet STATIC third_party/enet/callbacks.c third_party/enet/compress.c third_party/enet/host.c
    third_party/enet/list.c third_party/enet/packet.c third_party/enet/peer.c third_party/enet/protocol.c
    $<IF:$<BOOL:${WIN32}>,third_party/enet/win32.c,third_party/enet/unix.c>)
target_include_directories(enet SYSTEM PUBLIC third_party/enet/include)
# ENet combines values of two enums with "|" on purpose; MSVC 17.x warns
# about it (C5287). Only for this unmodified library (decision D-816).
if(MSVC)
    target_compile_options(enet PRIVATE /wd5287)
endif()
if(WIN32)
    target_link_libraries(enet PUBLIC ws2_32 winmm)
else()
    target_compile_definitions(enet PRIVATE HAS_SOCKLEN_T=1 HAS_POLL=1 HAS_MSGHDR_FLAGS=1 HAS_GETADDRINFO=1
                                            HAS_GETNAMEINFO=1 HAS_INET_PTON=1 HAS_INET_NTOP=1)
endif()

add_library(stb_truetype STATIC third_party/stb/stb_truetype.c)
target_include_directories(stb_truetype SYSTEM PUBLIC third_party/stb)

add_library(stb_image STATIC third_party/stb/stb_image.c)
target_include_directories(stb_image SYSTEM PUBLIC third_party/stb)

add_library(cgltf STATIC third_party/cgltf/cgltf.c)
target_include_directories(cgltf SYSTEM PUBLIC third_party/cgltf)

# Dear ImGui: developer statistics only, never the player's interface.
add_library(imgui STATIC
    third_party/imgui/imgui.cpp
    third_party/imgui/imgui_draw.cpp
    third_party/imgui/imgui_tables.cpp
    third_party/imgui/imgui_widgets.cpp
    third_party/imgui/backends/imgui_impl_sdl3.cpp
    third_party/imgui/backends/imgui_impl_sdlgpu3.cpp)
target_include_directories(imgui SYSTEM PUBLIC third_party/imgui third_party/imgui/backends)
target_link_libraries(imgui PUBLIC SDL3::SDL3-static)
# No imgui.ini or log files, and no obsolete API.
target_compile_definitions(imgui PUBLIC IMGUI_DISABLE_OBSOLETE_FUNCTIONS)

# Lua 5.4 for mod scripts (section 7.13). Only the core and the libraries the
# sandbox opens; no io, os, package or debug. String hashes use a fixed seed
# so tables behave the same on every machine (decision D-702).
add_library(lua STATIC
    third_party/lua/lapi.c third_party/lua/lauxlib.c third_party/lua/lbaselib.c third_party/lua/lcode.c
    third_party/lua/lctype.c third_party/lua/ldebug.c third_party/lua/ldo.c third_party/lua/ldump.c
    third_party/lua/lfunc.c third_party/lua/lgc.c third_party/lua/llex.c third_party/lua/lmem.c
    third_party/lua/lobject.c third_party/lua/lopcodes.c third_party/lua/lparser.c third_party/lua/lstate.c
    third_party/lua/lstring.c third_party/lua/lstrlib.c third_party/lua/ltable.c third_party/lua/ltablib.c
    third_party/lua/ltm.c third_party/lua/lundump.c third_party/lua/lutf8lib.c third_party/lua/lvm.c
    third_party/lua/lzio.c)
target_include_directories(lua SYSTEM PUBLIC third_party/lua)
target_include_directories(lua PRIVATE src/script)
target_compile_definitions(lua PRIVATE "LUA_USER_H=\"lua_user.h\"")

add_library(doctest INTERFACE)
target_include_directories(doctest SYSTEM INTERFACE third_party/doctest)

# RmlUi 6.3 for the player's interface (phases 117 to 127, section 7.14). Only the
# core and the debugger, without its FreeType font engine (D-11703): the game
# gives it its own font engine.
file(GLOB SC_RMLUI_SOURCES CONFIGURE_DEPENDS third_party/rmlui/Source/Core/*.cpp
     third_party/rmlui/Source/Core/Elements/*.cpp third_party/rmlui/Source/Core/Layout/*.cpp)
add_library(rmlui STATIC ${SC_RMLUI_SOURCES})
target_include_directories(rmlui SYSTEM PUBLIC third_party/rmlui/Include)
# RmlUi throws nothing; like the game's code, its standard library is built
# without exceptions.
target_compile_definitions(rmlui PUBLIC RMLUI_STATIC_LIB ITLIB_FLAT_MAP_NO_THROW $<$<CXX_COMPILER_ID:MSVC>:_HAS_EXCEPTIONS=0>
    PRIVATE "RMLUI_VERSION=\"6.3\"" _CRT_SECURE_NO_WARNINGS)
file(GLOB SC_RMLUI_DEBUGGER_SOURCES CONFIGURE_DEPENDS third_party/rmlui/Source/Debugger/*.cpp)
add_library(rmlui_debugger STATIC ${SC_RMLUI_DEBUGGER_SOURCES})
target_link_libraries(rmlui_debugger PUBLIC rmlui)
# RmlUi hands standard containers to the game's code, so under AddressSanitizer
# both sides must agree on the container annotations (MSVC refuses to link
# otherwise): RmlUi is sanitized too.
if(SC_ENABLE_ASAN AND MSVC)
    target_compile_options(rmlui PRIVATE /fsanitize=address)
    target_compile_options(rmlui_debugger PRIVATE /fsanitize=address)
endif()

# ---------------------------------------------------------------------------
# Shaders: HLSL compiled to DXIL with the DirectX Shader Compiler from the
# Windows SDK, then embedded as byte arrays (decision D-201). SPIR-V and MSL
# for Linux and macOS come later.
# ---------------------------------------------------------------------------
if(WIN32)
    set(SC_SDK_BIN_HINTS)
    if(DEFINED ENV{WindowsSdkVerBinPath})
        list(APPEND SC_SDK_BIN_HINTS "$ENV{WindowsSdkVerBinPath}/x64")
    endif()
    find_program(SC_DXC dxc HINTS ${SC_SDK_BIN_HINTS} REQUIRED)
else()
    message(FATAL_ERROR "Shader compilation for this platform is not set up yet (see docs/DECISIONES.md, D-201).")
endif()
message(STATUS "Shader compiler: ${SC_DXC}")

set(SC_SHADER_OUT "${SC_GENERATED_DIR}/shaders")
set(SC_SHADER_HEADERS)
function(sc_add_shader source profile symbol)
    get_filename_component(name "${source}" NAME_WE)
    get_filename_component(stage_ext "${source}" EXT)
    string(REPLACE ".hlsl" "" stage_ext "${stage_ext}")
    string(REPLACE "." "_" stage_ext "${stage_ext}")
    set(dxil "${SC_SHADER_OUT}/${name}${stage_ext}.dxil")
    set(header "${SC_SHADER_OUT}/${name}${stage_ext}_dxil.h")
    add_custom_command(
        OUTPUT "${header}"
        COMMAND ${CMAKE_COMMAND} -E make_directory "${SC_SHADER_OUT}"
        COMMAND "${SC_DXC}" -nologo -T ${profile} -E main -WX -O3 -Fo "${dxil}" "${CMAKE_CURRENT_SOURCE_DIR}/${source}"
        COMMAND ${CMAKE_COMMAND} -DINPUT=${dxil} -DOUTPUT=${header} -DSYMBOL=${symbol}
                -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/EmbedBinary.cmake"
        DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${source}" "${CMAKE_CURRENT_SOURCE_DIR}/cmake/EmbedBinary.cmake"
                "${CMAKE_CURRENT_SOURCE_DIR}/shaders/scene_common.hlsli"
                "${CMAKE_CURRENT_SOURCE_DIR}/shaders/skinning.hlsli"
                "${CMAKE_CURRENT_SOURCE_DIR}/shaders/terrain_common.hlsli"
                "${CMAKE_CURRENT_SOURCE_DIR}/shaders/lighting.hlsli"
        COMMENT "Compiling shader ${source}"
        VERBATIM)
    set(SC_SHADER_HEADERS ${SC_SHADER_HEADERS} "${header}" PARENT_SCOPE)
endfunction()
sc_add_shader(shaders/ui.vert.hlsl vs_6_0 kUiVertDxil)
sc_add_shader(shaders/ui.frag.hlsl ps_6_0 kUiFragDxil)
sc_add_shader(shaders/mesh.vert.hlsl vs_6_0 kMeshVertDxil)
sc_add_shader(shaders/mesh.frag.hlsl ps_6_0 kMeshFragDxil)
sc_add_shader(shaders/shadow.vert.hlsl vs_6_0 kShadowVertDxil)
sc_add_shader(shaders/shadow.frag.hlsl ps_6_0 kShadowFragDxil)
sc_add_shader(shaders/sky.vert.hlsl vs_6_0 kSkyVertDxil)
sc_add_shader(shaders/sky.frag.hlsl ps_6_0 kSkyFragDxil)
sc_add_shader(shaders/skinned.vert.hlsl vs_6_0 kSkinnedVertDxil)
sc_add_shader(shaders/skinned_shadow.vert.hlsl vs_6_0 kSkinnedShadowVertDxil)
sc_add_shader(shaders/facet.vert.hlsl vs_6_0 kFacetVertDxil)
sc_add_shader(shaders/facet.frag.hlsl ps_6_0 kFacetFragDxil)
sc_add_shader(shaders/water.vert.hlsl vs_6_0 kWaterVertDxil)
sc_add_shader(shaders/water.frag.hlsl ps_6_0 kWaterFragDxil)
sc_add_shader(shaders/grass.vert.hlsl vs_6_0 kGrassVertDxil)
sc_add_shader(shaders/blur.frag.hlsl ps_6_0 kBlurFragDxil)
sc_add_shader(shaders/rml.vert.hlsl vs_6_0 kRmlVertDxil)
sc_add_shader(shaders/rml.frag.hlsl ps_6_0 kRmlFragDxil)
sc_add_shader(shaders/rml_gradient.frag.hlsl ps_6_0 kRmlGradientFragDxil)
sc_add_shader(shaders/rml_quad.vert.hlsl vs_6_0 kRmlQuadVertDxil)
sc_add_shader(shaders/rml_post.frag.hlsl ps_6_0 kRmlPostFragDxil)
sc_add_shader(shaders/rml_blur.frag.hlsl ps_6_0 kRmlBlurFragDxil)

# The base language is built in, so the game shows text even if data/lang
# is missing.
set(SC_LANG_EN_HEADER "${SC_GENERATED_DIR}/embedded/lang_en.h")
add_custom_command(
    OUTPUT "${SC_LANG_EN_HEADER}"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${SC_GENERATED_DIR}/embedded"
    COMMAND ${CMAKE_COMMAND} -DINPUT=${CMAKE_CURRENT_SOURCE_DIR}/data/lang/en.json -DOUTPUT=${SC_LANG_EN_HEADER}
            -DSYMBOL=kLangEn -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/EmbedBinary.cmake"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/data/lang/en.json" "${CMAKE_CURRENT_SOURCE_DIR}/cmake/EmbedBinary.cmake"
    COMMENT "Embedding the base language"
    VERBATIM)
# Which sources this build comes from, so the lobby refuses another build
# with the same version number (decision D-3321). It is worked out on every
# build; the header only changes when the sources do.
set(SC_BUILD_ID_HEADER "${SC_GENERATED_DIR}/build_id.h")
file(GLOB_RECURSE SC_ALL_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/*")
add_custom_command(
    OUTPUT "${SC_GENERATED_DIR}/build_id.stamp"
    BYPRODUCTS "${SC_BUILD_ID_HEADER}"
    COMMAND ${CMAKE_COMMAND} -DSOURCE_DIR=${CMAKE_CURRENT_SOURCE_DIR} -DOUTPUT=${SC_BUILD_ID_HEADER}
            -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/BuildId.cmake"
    COMMAND ${CMAKE_COMMAND} -E touch "${SC_GENERATED_DIR}/build_id.stamp"
    DEPENDS ${SC_ALL_SOURCES} "${CMAKE_CURRENT_SOURCE_DIR}/cmake/BuildId.cmake"
    COMMENT "Working out the build identifier"
    VERBATIM)
add_custom_target(sc_generated DEPENDS ${SC_SHADER_HEADERS} "${SC_LANG_EN_HEADER}" "${SC_GENERATED_DIR}/build_id.stamp")

# ---------------------------------------------------------------------------
# Engine library: everything except the program entry point, so the tests can
# link it.
# ---------------------------------------------------------------------------
set(SC_ENGINE_SOURCES
    src/core/file_io.cpp
    src/core/json.cpp
    src/core/log.cpp
    src/core/png.cpp
    src/core/text.cpp
    src/game/animal_motion.cpp
    src/game/app.cpp
    src/game/build_info.cpp
    src/game/dev_tools.cpp
    src/game/camera.cpp
    src/game/day_light.cpp
    src/game/game_clock.cpp
    src/game/game_hud.cpp
    src/game/hud_windows.cpp
    src/game/hud_founding.cpp
    src/game/hud_model.cpp
    src/game/hud_rml.cpp
    src/game/hud_rml_windows.cpp
    src/game/thing_rows.cpp
    src/game/minimap.cpp
    src/game/people.cpp
    src/game/sound_director.cpp
    src/audio/mixer.cpp
    src/game/fog_view.cpp
    src/game/game_session.cpp
    src/game/save_file.cpp
    src/game/input_actions.cpp
    src/game/map_generation.cpp
    src/game/map_scene.cpp
    src/game/mods_screen.cpp
    src/game/multiplayer_screens.cpp
    src/game/new_game_screen.cpp
    src/game/settings.cpp
    src/game/settings_screen.cpp
    src/game/map_report.cpp
    src/game/terrain_names.cpp
    src/game/menu_backgrounds.cpp
    src/game/model_studio.cpp
    src/game/model_file.cpp
    src/game/occluders.cpp
    src/game/ui_host.cpp
    src/game/variants.cpp
    src/game/ambient_fauna.cpp
    src/game/ground_cover.cpp
    src/game/village_props.cpp
    src/game/village_view.cpp
    src/game/walkers.cpp
    src/game/window_list.cpp
    src/i18n/catalog.cpp
    src/mods/defs.cpp
    src/net/enet_link.cpp
    src/net/link.cpp
    src/net/lockstep.cpp
    src/net/protocol.cpp
    src/mods/mod_library.cpp
    src/mods/mod_manifest.cpp
    src/mods/mod_settings.cpp
    src/script/lua_sandbox.cpp
    src/script/map_script.cpp
    src/script/tutorial_script.cpp
    src/i18n/plural.cpp
    src/i18n/translator.cpp
    src/math/vec.cpp
    src/platform/paths.cpp
    src/sim/command.cpp
    src/sim/climate.cpp
    src/sim/content.cpp
    src/sim/entity.cpp
    src/sim/fixed.cpp
    src/sim/game.cpp
    src/sim/flora.cpp
    src/sim/map.cpp
    src/sim/nav.cpp
    src/sim/noise.cpp
    src/sim/rng.cpp
    src/sim/serialize.cpp
    src/sim/vision.cpp
    src/sim/worldgen.cpp
    src/sim/worldgen_hier.cpp
    src/platform/window.cpp
    src/render/debug_overlay.cpp
    src/render/gpu_device.cpp
    src/render/model.cpp
    src/render/rml_renderer.cpp
    src/render/scene_renderer.cpp
    src/render/terrain_layer.cpp
    src/render/terrain_mesh.cpp
    src/render/ui_renderer.cpp
    src/ui/context.cpp
    src/ui/draw_list.cpp
    src/ui/font.cpp
    src/ui/font_library.cpp
    src/ui/glow.cpp
    src/ui/glyph_atlas.cpp
    src/ui/text.cpp
    src/ui/rml/rml_font_engine.cpp
    src/ui/rml/rml_input.cpp
    src/ui/rml/rml_system.cpp
    src/ui/rml/rml_style.cpp
    src/ui/rml/rml_test_window.cpp
    src/ui/rml/rml_ui.cpp)

add_library(sc_engine STATIC ${SC_ENGINE_SOURCES})
target_include_directories(sc_engine PUBLIC src "${SC_GENERATED_DIR}")
# Map generation runs on a worker thread.
find_package(Threads REQUIRED)
target_link_libraries(sc_engine PUBLIC SDL3::SDL3-static yyjson stb_truetype stb_image cgltf imgui lua zstd enet rmlui
    rmlui_debugger Threads::Threads)
add_dependencies(sc_engine sc_generated)
sc_harden_target(sc_engine)

# ---------------------------------------------------------------------------
# Game executable.
# ---------------------------------------------------------------------------
add_executable(SalvasProsperia WIN32 src/main.cpp)
target_link_libraries(SalvasProsperia PRIVATE sc_engine)
sc_harden_target(SalvasProsperia)
set_target_properties(SalvasProsperia PROPERTIES
    VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

# The game and the model viewer read data/ next to the executable. One target
# copies it for both, so two copies never run at the same time (decision
# D-3107). The stamp reruns the copy only when a file in data/ changes; the
# CONFIGURE_DEPENDS glob notices new files.
file(GLOB_RECURSE SC_DATA_FILES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/data/*")
set(SC_DATA_STAMP "${CMAKE_CURRENT_BINARY_DIR}/sc_data.stamp")
add_custom_command(OUTPUT "${SC_DATA_STAMP}"
    # A mirror: files deleted from data/ must not stay next to the executables
    # (the game would still read them).
    COMMAND ${CMAKE_COMMAND} -E remove_directory "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/data"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/data" "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/data"
    COMMAND ${CMAKE_COMMAND} -E touch "${SC_DATA_STAMP}"
    DEPENDS ${SC_DATA_FILES}
    COMMENT "Copying data/ next to the executables"
    VERBATIM)
add_custom_target(sc_data ALL DEPENDS "${SC_DATA_STAMP}")
add_dependencies(SalvasProsperia sc_data)

# ---------------------------------------------------------------------------
# Model viewer (phase 30): a developer tool apart from the game. Its catalog
# is a library so the tests can check it.
# ---------------------------------------------------------------------------
add_library(sc_viewer STATIC src/viewer/model_catalog.cpp)
target_link_libraries(sc_viewer PUBLIC sc_engine)
sc_harden_target(sc_viewer)

add_executable(SalvasProsperiaModelos WIN32 src/viewer/main.cpp src/viewer/viewer_app.cpp)
target_link_libraries(SalvasProsperiaModelos PRIVATE sc_viewer)
# Reads the source tree's mods while that folder exists (decision D-3003).
target_compile_definitions(SalvasProsperiaModelos PRIVATE SC_VIEWER_SOURCE_DATA="${CMAKE_CURRENT_SOURCE_DIR}/data")
sc_harden_target(SalvasProsperiaModelos)
set_target_properties(SalvasProsperiaModelos PROPERTIES
    VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
# It reads the game's data/ next to it, like the game.
add_dependencies(SalvasProsperiaModelos sc_data)

# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------
if(SC_BUILD_TESTS)
    enable_testing()

    add_executable(salvasprosperia_tests
        tests/test_main.cpp
        tests/test_file_io.cpp
        tests/test_game_clock.cpp
        tests/test_json.cpp
        tests/test_log.cpp
        tests/test_paths.cpp
        tests/test_settings.cpp
        tests/test_text.cpp
        tests/test_i18n.cpp
        tests/test_input_actions.cpp
        tests/test_menus.cpp
        tests/test_ui.cpp
        tests/test_rml.cpp
        tests/test_studio.cpp
        tests/test_hud.cpp
        tests/test_math.cpp
        tests/test_model.cpp
        tests/test_camera.cpp
        tests/test_scene.cpp
        tests/test_sim.cpp
        tests/test_worldgen.cpp
        tests/test_map_view.cpp
        tests/test_terrain_mesh.cpp
        tests/test_mods.cpp
        tests/test_village.cpp
        tests/test_save.cpp
        tests/test_net.cpp
        tests/test_climate.cpp
        tests/test_farming.cpp
        tests/test_needs.cpp
        tests/test_health.cpp
        tests/test_trade.cpp
        tests/test_wildlife.cpp
        tests/test_army.cpp
        tests/test_audio.cpp
        tests/test_people.cpp
        tests/test_cover.cpp
        tests/test_fauna.cpp
        tests/test_trace.cpp
        tests/test_fences.cpp
        tests/test_roads.cpp
        tests/test_lanterns.cpp
        tests/test_rain.cpp
        tests/test_forage.cpp
        tests/test_berries.cpp
        tests/test_wine.cpp
        tests/test_deposits.cpp
        tests/test_stones.cpp
        tests/test_annexes.cpp
        tests/test_gardens.cpp
        tests/test_coop.cpp
        tests/test_pets.cpp
        tests/test_herds.cpp
        tests/test_smallgame.cpp
        tests/test_fishing.cpp
        tests/test_mammoths.cpp
        tests/test_unicorn.cpp
        tests/test_happenings.cpp
        tests/test_turtles.cpp
        tests/test_races.cpp
        tests/test_perf.cpp
        tests/test_viewer.cpp
        tests/test_variants.cpp
        tests/test_fog.cpp
        tests/test_terrain_names.cpp
        tests/test_map_report.cpp
        tests/test_worldgen_hier.cpp
        tests/test_windows.cpp
        tests/test_explorer.cpp
        tests/test_founding.cpp
        tests/test_seats.cpp
        tests/test_spectator.cpp
        tests/test_resources.cpp)
    target_link_libraries(salvasprosperia_tests PRIVATE sc_engine sc_viewer doctest)
    target_compile_definitions(salvasprosperia_tests PRIVATE
        SC_TEST_FIXTURES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures"
        SC_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    sc_harden_target(salvasprosperia_tests ALLOW_EXCEPTIONS)
    if(MSVC)
        # A full link every time: with incremental linking the debug tests
        # sometimes ended with 0xC0000409 at exit after every check had
        # passed (the suites that scan the sources, D-5507).
        target_link_options(salvasprosperia_tests PRIVATE /INCREMENTAL:NO)
    endif()

    set(SC_TEST_SUITES file_io game_clock json log paths settings text i18n input_actions ui menus math model camera scene sim_fixed sim_rng sim_core sim_rules worldgen worldgen_sea worldgen_large flora worldgen_perf map_view new_game dev_tools terrain_mesh mods lua village village_years save net net_enet climate farming needs health trade gold auto_trade wildlife army audio races people sim_perf viewer variants fog terrain_names map_report worldgen_hier worldgen_hier_structures worldgen_hier_water worldgen_hier_life worldgen_hier_giants minimap nav windows explorer night rest rest_hour founding seats spectator resources resources_years cover fauna trace fences roads lanterns rain forage berries wine deposits stones annexes gardens coop pets herds smallgame fishing mammoths unicorn happenings turtles rml studio hud)
    # AddressSanitizer runs about twice as slow, and its times vary up to
    # twice between runs (D-3110).
    set(SC_TEST_TIMEOUT 120)
    if(SC_ENABLE_ASAN)
        set(SC_TEST_TIMEOUT 240)
    endif()
    foreach(suite IN LISTS SC_TEST_SUITES)
        add_test(NAME ${suite} COMMAND salvasprosperia_tests --test-suite=${suite})
        set_tests_properties(${suite} PROPERTIES TIMEOUT ${SC_TEST_TIMEOUT})
        if(MSVC AND SC_ENABLE_ASAN)
            set_tests_properties(${suite} PROPERTIES
                ENVIRONMENT_MODIFICATION "PATH=path_list_prepend:${SC_MSVC_BIN_DIR}")
        endif()
    endforeach()
endif()
