# Independent recomputation of the K1 soil event metrics from the exported 1 ms rows; no shared code with the r67 judge.
# Columns: t, contact FL FR RL RR, F_cyl FL FR RL RR. Same cut as the judge. Lift = contact <= 0, after = t >= 0.
using JSON3

const DIR = raw"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_k1soil\xval"
const LEGS = ["FL", "FR", "RL", "RR"]
const DIAG = Dict("FL" => "RR", "RR" => "FL", "FR" => "RL", "RL" => "FR")
const T3 = 0.82
const FMIN = 9414.6

function runs_of(mask, t)
    out = Tuple{Float64,Float64}[]
    i = 1
    n = length(mask)
    while i <= n
        if mask[i]
            j = i
            while j < n && mask[j+1]
                j += 1
            end
            push!(out, (t[i], j < n ? t[j+1] : t[j]))
            i = j + 1
        else
            i += 1
        end
    end
    return out
end

function metrics(path, nrows, tev, leg)
    raw = Vector{Float64}(undef, nrows * 9)
    read!(path, raw)
    a = permutedims(reshape(raw, 9, nrows))
    t = a[:, 1] .- tev
    c = a[:, 2:5]
    f = a[:, 6:9]
    lifted = c .<= 0.0
    after = t .>= 0.0
    res = Dict{String,Any}()
    lifts = Dict{String,Any}()
    for (i, name) in enumerate(LEGS)
        iv = runs_of(after .& lifted[:, i], t)
        lifts[name] = Dict("sum_s" => sum(b - x for (x, b) in iv; init = 0.0), "last_touch_s" => isempty(iv) ? 0.0 : iv[end][2], "n" => length(iv))
    end
    p = [findfirst(==(leg), LEGS), findfirst(==(DIAG[leg]), LEGS)]
    adj = setdiff(1:4, p)
    iv = runs_of(after .& vec(any(lifted[:, p]; dims = 2)), t)
    pu = sum(b - x for (x, b) in iv; init = 0.0)
    plast = isempty(iv) ? 0.0 : iv[end][2]
    wend = min(round(plast; digits = 3) + T3, 5.0)
    inw = after .& (t .<= wend)
    post = t .> wend
    res["pair_union_s"] = pu
    res["pair_last_touch_s"] = plast
    res["W_end_s"] = wend
    res["lifts"] = lifts
    res["adj_min_F_in_W_kN"] = Dict(LEGS[i] => minimum(f[inw, i]) / 1e3 for i in adj)
    res["min_F_after_W_kN"] = Dict(LEGS[i] => minimum(f[post, i]) / 1e3 for i in 1:4)
    res["min_F_after_event_kN"] = Dict(LEGS[i] => minimum(f[after, i]) / 1e3 for i in 1:4)
    res["margin_Fmin_after_W_kN"] = (minimum(f[post, :]) - FMIN) / 1e3
    res["rows"] = nrows
    return res
end

idx = JSON3.read(read(joinpath(DIR, "index.json"), String))
out = Dict{String,Any}()
for (k, v) in pairs(idx)
    out[String(k)] = metrics(String(v.path), Int(v.rows), Float64(v.t_ev), String(v.leg))
end
open(joinpath(DIR, "julia_metrics.json"), "w") do io
    JSON3.write(io, out)
end
println("ok ", length(out), " rows")
