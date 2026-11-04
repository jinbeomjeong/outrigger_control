# Independent recomputation of the judged force and SA-4 values from the raw 1 ms series (CSV export).
# Does not read any Python result. Output: JSON file next to this script.
using CSV, DataFrames, JSON3

const DIR = @__DIR__
const W0_N = 380112.91206408414
const RUNS = Dict("S8_on" => (W0_N, 50.3), "S8_off" => (W0_N, 48.6),
                  "S6_on" => (1.1 * W0_N, nothing), "S6_off" => (1.1 * W0_N, nothing),
                  "S1_on" => (W0_N, nothing), "S1_off" => (W0_N, nothing))

function spans_above(t, c, thr, istart)
    out = Vector{Vector{Float64}}()
    i = istart
    n = length(c)
    while i <= n
        if c[i] >= thr
            j = i
            while j < n && c[j + 1] >= thr
                j += 1
            end
            push!(out, [t[i], t[j], maximum(@view c[i:j])])
            i = j + 1
        else
            i += 1
        end
    end
    return out
end

results = Dict{String,Any}()
for (name, (w, tstop)) in RUNS
    df = CSV.read(joinpath(DIR, name * ".csv"), DataFrame)
    t, c = df.t_s, df.crawler_N
    F = hcat(df.F_FL_N, df.F_FR_N, df.F_RL_N, df.F_RR_N)
    thr = 0.01 * w
    # departure: first start of 100 consecutive samples below 0.01 W after the settle
    i0 = findfirst(>(10.0), t)
    run = 0
    kdep = 0
    for k in i0:length(c)
        run = c[k] < thr ? run + 1 : 0
        if run == 100
            kdep = k - 99
            break
        end
    end
    fmin_legs = [minimum(@view F[kdep:end, q]) for q in 1:4]
    r = Dict{String,Any}("t_dep_abs_s" => t[kdep], "F_min_after_dep_kN" => minimum(fmin_legs) / 1e3,
                         "F_min_legs_kN" => fmin_legs ./ 1e3,
                         "spans_after_dep" => [[s[1] - 8.0, s[2] - 8.0, s[3] / 1e3] for s in spans_above(t, c, thr, kdep)])
    if tstop !== nothing
        ks = searchsortedfirst(t, tstop - 1e-9)
        r["crawler_at_stop_kN"] = c[ks] / 1e3
        r["crawler_max_after_kN"] = maximum(@view c[ks:end]) / 1e3
        r["limit_kN"] = (c[ks] + thr) / 1e3
        r["clause_pass"] = maximum(@view c[ks:end]) <= c[ks] + thr
        r["F_min_after_stop_kN"] = [minimum(@view F[ks:end, q]) / 1e3 for q in 1:4]
    end
    results[name] = r
end
open(joinpath(DIR, "xcheck_julia.json"), "w") do io
    JSON3.write(io, results)
end
println(JSON3.write(results))
