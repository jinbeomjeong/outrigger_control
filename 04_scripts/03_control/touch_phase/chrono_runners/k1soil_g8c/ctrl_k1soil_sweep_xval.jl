# Independent recomputation of the sweep statistics from the phase values in sweep_values.json: delta medians, sign counts, phase width, separated flag, rule estimate below-F_min counts, worst margins.
using JSON3, Statistics

const S = raw"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil\sweep"
const LEGS = ["FL", "FR", "RL", "RR"]
const FMIN = 9.4146
v = JSON3.read(read(joinpath(S, "sweep_values.json"), String))
dense = [string(round(0.01 * k; digits = 2)) for k in 0:10]
fmt(x) = lpad(string(round(Int, 100x) ÷ 100), 1) * "." * lpad(string(round(Int, 100x) % 100), 2, '0')
out = Dict{String,Any}()
for row in ("FLFs0", "FLFs8", "RRFs0")
    r = v.rows[Symbol(row)]
    ph = r.phases
    keys_all = String.(collect(keys(ph)))
    dkeys = [fmt(0.01 * k) for k in 0:10]
    res = Dict{String,Any}()
    for leg in LEGS
        A = [Float64(ph[Symbol(d)].A[Symbol(leg)]) for d in dkeys]
        B = [Float64(ph[Symbol(d)].B[Symbol(leg)]) for d in dkeys]
        D = B .- A
        S_ = maximum(A) - minimum(A)
        n = max(count(>(0), D), count(<(0), D))
        res[leg] = Dict("median" => median(D), "S_A" => S_, "n_same" => n, "separated" => (n >= 9 && abs(median(D)) > S_ / 2))
    end
    MA = [minimum(Float64(ph[Symbol(d)].A[Symbol(l)]) for l in LEGS) - FMIN for d in keys_all]
    MB = [minimum(Float64(ph[Symbol(d)].B[Symbol(l)]) for l in LEGS) - FMIN for d in keys_all]
    e = r.estimate
    a = Symbol(fmt(Float64(e.anchor_delta)))
    below_B = 0
    below_A = 0
    mbmin = Inf
    for d in keys_all
        s = Symbol(d)
        Ah = Dict(l => Float64(e.chrono_common_A[Symbol(l)]) + Float64(ph[s].A[Symbol(l)]) - Float64(ph[a].A[Symbol(l)]) for l in LEGS)
        Bh = Dict{String,Float64}()
        for l in LEGS
            dh = Float64(ph[s].B[Symbol(l)]) - Float64(ph[s].A[Symbol(l)])
            Bh[l] = Ah[l] + (dh < 0 ? Float64(e.g[Symbol(l)]) * dh : dh)
        end
        mb = minimum(values(Bh)) - FMIN
        below_B += mb < 0
        below_A += (minimum(values(Ah)) - FMIN) < 0
        mbmin = min(mbmin, mb)
    end
    res["worst_MA"] = minimum(MA)
    res["worst_MB"] = minimum(MB)
    res["n_below_B"] = below_B
    res["n_below_A"] = below_A
    res["MB_est_min"] = mbmin
    out[row] = res
end
open(joinpath(S, "sweep_xval_julia.json"), "w") do io
    JSON3.write(io, out)
end
println(JSON3.write(out))
