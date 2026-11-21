const _DIR2 = raw"C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\control-imuatt2"
empty!(ARGS)
push!(ARGS, joinpath(_DIR2, "export2.json"), joinpath(_DIR2, "check2_jl.json"))
include(joinpath(_DIR2, "check_jl2.jl"))
