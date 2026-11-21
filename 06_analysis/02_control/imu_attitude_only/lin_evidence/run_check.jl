const _DIR = raw"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\control-imuatt"
empty!(ARGS)
push!(ARGS, joinpath(_DIR, "imuatt_export.json"), joinpath(_DIR, "imuatt_check_jl.json"))
include(joinpath(_DIR, "imuatt_check.jl"))
