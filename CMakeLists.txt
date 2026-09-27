cmake_minimum_required(VERSION 3.25)

project(SalvaCiudad
    VERSION 0.20.0
    DESCRIPTION "Multiplayer medieval town-building survival game"
    LANGUAGES C CXX)

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "SalvaCiudad requires a 64-bit target.")
endif()
if(MSVC AND MSVC_TOOLSET_VERSION LESS 143)
    message(FATAL_ERROR "SalvaCiudad requires MSVC v143 (Visual Studio 2022) or newer. Found: ${MSVC_TOOLSET_VERSION}")
endif()

option(SC_ENABLE_ASAN "Build SalvaCiudad targets with AddressSanitizer" OFF)
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
# Compiler and linker flags for SalvaCiudad's own code (section 10 of the
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
target_compile_definitions(lua PRIVATE "luai_makeseed(L)=0u")

add_library(doctest INTERFACE)
target_include_directories(doctest SYSTEM INTERFACE third_party/doctest)

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
add_custom_target(sc_generated DEPENDS ${SC_SHADER_HEADERS} "${SC_LANG_EN_HEADER}")

# ---------------------------------------------------------------------------
# Engine library: everything except the program entry point, so the tests can
# link it.
# ---------------------------------------------------------------------------
set(SC_ENGINE_SOURCES
    src/core/file_io.cpp
    src/core/json.cpp
    src/core/log.cpp
    src/core/text.cpp
    src/game/app.cpp
    src/game/dev_tools.cpp
    src/game/camera.cpp
    src/game/game_clock.cpp
    src/game/game_hud.cpp
    src/game/hud_windows.cpp
    src/game/sound_director.cpp
    src/audio/mixer.cpp
    src/game/game_session.cpp
    src/game/replay_file.cpp
    src/game/save_file.cpp
    src/game/input_actions.cpp
    src/game/map_generation.cpp
    src/game/map_scene.cpp
    src/game/mods_screen.cpp
    src/game/multiplayer_screens.cpp
    src/game/new_game_screen.cpp
    src/game/settings.cpp
    src/game/settings_screen.cpp
    src/game/test_scene.cpp
    src/game/ui_host.cpp
    src/game/village_view.cpp
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
    src/sim/simulation.cpp
    src/sim/world.cpp
    src/sim/worldgen.cpp
    src/platform/window.cpp
    src/render/debug_overlay.cpp
    src/render/gpu_device.cpp
    src/render/model.cpp
    src/render/scene_renderer.cpp
    src/render/terrain_layer.cpp
    src/render/terrain_mesh.cpp
    src/render/ui_renderer.cpp
    src/ui/context.cpp
    src/ui/draw_list.cpp
    src/ui/font.cpp
    src/ui/font_library.cpp
    src/ui/glyph_atlas.cpp
    src/ui/text.cpp)

add_library(sc_engine STATIC ${SC_ENGINE_SOURCES})
target_include_directories(sc_engine PUBLIC src "${SC_GENERATED_DIR}")
# Map generation runs on a worker thread.
find_package(Threads REQUIRED)
target_link_libraries(sc_engine PUBLIC SDL3::SDL3-static yyjson stb_truetype stb_image cgltf imgui lua zstd enet Threads::Threads)
add_dependencies(sc_engine sc_generated)
sc_harden_target(sc_engine)

# ---------------------------------------------------------------------------
# Game executable.
# ---------------------------------------------------------------------------
add_executable(SalvaCiudad WIN32 src/main.cpp)
target_link_libraries(SalvaCiudad PRIVATE sc_engine)
sc_harden_target(SalvaCiudad)
set_target_properties(SalvaCiudad PROPERTIES
    VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

# The game reads data/ next to the executable.
add_custom_command(TARGET SalvaCiudad POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/data" "$<TARGET_FILE_DIR:SalvaCiudad>/data"
    VERBATIM)

# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------
if(SC_BUILD_TESTS)
    enable_testing()

    add_executable(salvaciudad_tests
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
        tests/test_races.cpp
        tests/test_perf.cpp)
    target_link_libraries(salvaciudad_tests PRIVATE sc_engine doctest)
    target_compile_definitions(salvaciudad_tests PRIVATE
        SC_TEST_FIXTURES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures"
        SC_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}")
    sc_harden_target(salvaciudad_tests ALLOW_EXCEPTIONS)

    set(SC_TEST_SUITES file_io game_clock json log paths settings text i18n input_actions ui menus math model camera scene sim_fixed sim_rng sim_core sim_replay sim_rules worldgen flora worldgen_perf map_view new_game dev_tools terrain_mesh mods lua village save net net_enet climate farming needs health trade wildlife army audio races sim_perf)
    foreach(suite IN LISTS SC_TEST_SUITES)
        add_test(NAME ${suite} COMMAND salvaciudad_tests --test-suite=${suite})
        set_tests_properties(${suite} PROPERTIES TIMEOUT 120)
        if(MSVC AND SC_ENABLE_ASAN)
            set_tests_properties(${suite} PROPERTIES
                ENVIRONMENT_MODIFICATION "PATH=path_list_prepend:${SC_MSVC_BIN_DIR}")
        endif()
    endforeach()
endif()
