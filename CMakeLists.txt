cmake_minimum_required(VERSION 3.25)

project(SalvaCiudad
    VERSION 0.1.0
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

add_library(doctest INTERFACE)
target_include_directories(doctest SYSTEM INTERFACE third_party/doctest)

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
    src/game/game_clock.cpp
    src/game/settings.cpp
    src/platform/paths.cpp
    src/platform/window.cpp
    src/render/gpu_device.cpp)

add_library(sc_engine STATIC ${SC_ENGINE_SOURCES})
target_include_directories(sc_engine PUBLIC src "${SC_GENERATED_DIR}")
target_link_libraries(sc_engine PUBLIC SDL3::SDL3-static yyjson)
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
        tests/test_text.cpp)
    target_link_libraries(salvaciudad_tests PRIVATE sc_engine doctest)
    target_compile_definitions(salvaciudad_tests PRIVATE
        SC_TEST_FIXTURES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures")
    sc_harden_target(salvaciudad_tests ALLOW_EXCEPTIONS)

    set(SC_TEST_SUITES file_io game_clock json log paths settings text)
    foreach(suite IN LISTS SC_TEST_SUITES)
        add_test(NAME ${suite} COMMAND salvaciudad_tests --test-suite=${suite})
        set_tests_properties(${suite} PROPERTIES TIMEOUT 120)
        if(MSVC AND SC_ENABLE_ASAN)
            set_tests_properties(${suite} PROPERTIES
                ENVIRONMENT_MODIFICATION "PATH=path_list_prepend:${SC_MSVC_BIN_DIR}")
        endif()
    endforeach()
endif()
