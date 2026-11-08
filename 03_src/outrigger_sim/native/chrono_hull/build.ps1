# Build chrono_hull_hook.dll (and the tests) with VS 2022 BuildTools + Ninja.
# Output: build\ (CMake tree) and bin\chrono_hull_hook.dll (install step).
# Does not touch any conda env; CHRONO_PREFIX only supplies headers and .lib files.
param(
    [string]$ChronoPrefix = 'C:/ProgramData/miniforge3/envs/Chrono-dev/Library',
    [switch]$NoTests
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$vcvars = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
$tests = if ($NoTests) { 'OFF' } else { 'ON' }
$configure = "cmake -S `"$here`" -B `"$here\build`" -G Ninja -DCMAKE_BUILD_TYPE=Release " +
             "-DCHRONO_PREFIX=`"$ChronoPrefix`" -DCHRONO_HULL_BUILD_TESTS=$tests " +
             "-DCMAKE_INSTALL_PREFIX=`"$here`" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
$build = "cmake --build `"$here\build`" && cmake --install `"$here\build`""
cmd /c "call `"$vcvars`" >nul 2>&1 && $configure && $build"
if ($LASTEXITCODE -ne 0) { throw "build failed ($LASTEXITCODE)" }
Get-FileHash "$here\bin\chrono_hull_hook.dll" -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $($_.Path)" }
