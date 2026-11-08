cmake_minimum_required(VERSION 3.24)
project(outrigger_chrono_hull LANGUAGES CXX)

# Fast, bit-exact replacement of Chrono's 2D convex hull for SCMTerrain, loaded
# into a pychrono process as chrono_hull_hook.dll. See README.md.

if(NOT MSVC)
  message(FATAL_ERROR "chrono_hull targets the MSVC-built conda pychrono on Windows")
endif()

set(CHRONO_PREFIX "C:/ProgramData/miniforge3/envs/Chrono-dev/Library"
    CACHE PATH "conda Library folder of the pychrono env (headers and import libraries)")
option(CHRONO_HULL_BUILD_TESTS "Build the equivalence test, benchmark and SCM smoke test" ON)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# Must match the conda build: dynamic CRT (/MD) so heap and STL ABI are shared.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")

# Floating-point flags: /fp:precise without contraction reproduces the conda
# binary's SSE/AVX arithmetic (it contains no FMA). Verified by the
# reference-copy check in hull_equivalence_test.
set(CHRONO_HULL_CXX_FLAGS /W4 /permissive- /utf-8 /EHsc /fp:precise /arch:AVX2 /bigobj)

add_library(chrono_sdk INTERFACE)
target_include_directories(chrono_sdk SYSTEM INTERFACE
  "${CHRONO_PREFIX}/include" "${CHRONO_PREFIX}/include/eigen3"
  "${CHRONO_PREFIX}/include/chrono_thirdparty/yaml-cpp/include")
target_compile_definitions(chrono_sdk INTERFACE NOMINMAX WIN32_LEAN_AND_MEAN _USE_MATH_DEFINES)

# Algorithm core (no Chrono link dependency; uses header-only ChVector2).
add_library(exact_fast_hull STATIC src/exact_fast_hull.cpp src/patch_dump.cpp)
target_include_directories(exact_fast_hull PUBLIC src)
target_link_libraries(exact_fast_hull PUBLIC chrono_sdk)
target_compile_options(exact_fast_hull PRIVATE ${CHRONO_HULL_CXX_FLAGS})

# The hook DLL. It does not link Chrono: it finds Chrono_core/Chrono_vehicle
# already loaded in the process.
add_library(chrono_hull_hook SHARED src/chrono_hull_hook.cpp src/import_slots.cpp)
target_include_directories(chrono_hull_hook PUBLIC include)
target_compile_definitions(chrono_hull_hook PRIVATE CHRONO_HULL_HOOK_BUILD)
target_link_libraries(chrono_hull_hook PRIVATE exact_fast_hull bcrypt)
target_compile_options(chrono_hull_hook PRIVATE ${CHRONO_HULL_CXX_FLAGS})
# Reproducible binary (no timestamps), so the reported SHA-256 can be rebuilt.
target_compile_options(exact_fast_hull PRIVATE /Brepro)
target_compile_options(chrono_hull_hook PRIVATE /Brepro)
target_link_options(chrono_hull_hook PRIVATE /Brepro)

if(CHRONO_HULL_BUILD_TESTS)
  set(CHRONO_CORE_LIB "${CHRONO_PREFIX}/lib/Chrono_core.lib")
  set(CHRONO_VEHICLE_LIB "${CHRONO_PREFIX}/lib/Chrono_vehicle.lib")

  add_library(hull_cases STATIC tests/hull_cases.cpp)
  target_link_libraries(hull_cases PUBLIC chrono_sdk)
  target_compile_options(hull_cases PRIVATE ${CHRONO_HULL_CXX_FLAGS})

  add_executable(hull_equivalence_test tests/hull_equivalence_test.cpp)
  target_link_libraries(hull_equivalence_test PRIVATE exact_fast_hull hull_cases "${CHRONO_CORE_LIB}")
  target_compile_options(hull_equivalence_test PRIVATE ${CHRONO_HULL_CXX_FLAGS})

  add_executable(hull_bench tests/hull_bench.cpp)
  target_link_libraries(hull_bench PRIVATE exact_fast_hull hull_cases "${CHRONO_CORE_LIB}")
  target_compile_options(hull_bench PRIVATE ${CHRONO_HULL_CXX_FLAGS})

  add_executable(hook_scm_smoke tests/hook_scm_smoke.cpp)
  target_link_libraries(hook_scm_smoke PRIVATE chrono_hull_hook chrono_sdk
    "${CHRONO_CORE_LIB}" "${CHRONO_VEHICLE_LIB}")
  target_compile_options(hook_scm_smoke PRIVATE ${CHRONO_HULL_CXX_FLAGS})
endif()

install(TARGETS chrono_hull_hook RUNTIME DESTINATION bin)
install(FILES include/chrono_hull_hook.h DESTINATION include)
