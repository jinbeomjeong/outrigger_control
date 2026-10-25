# Independent cross-check of s6r25_margins.py (spec rev. 25): same loops from the same raw constants,
# ControlSystemsBase delay systems, margin on a dense log grid (tol note: grid interpolation), Ms from the grid.
using ControlSystemsBase, JSON3
taus = Dict("base_50Hz" => 0.030, "p10i_mean" => 0.080, "p10i_worst" => 0.130, "p10a_mean" => 0.130,
            "p10a_worst" => 0.180, "c10_mean" => 0.150, "c10_worst" => 0.200)
loops = Dict("twist" => (1.2, 0.0), "guard" => (1.0, 0.0), "heave" => (0.5, 0.2))
w = exp10.(range(-3, 3, length = 200_000))
out = Dict{String,Any}()
function loopsys(K, tf_, tau)
    s = tf("s")
    base = tf_ == 0.0 ? K / s : K / (s * (tf_ * s + 1))
    return base * delay(tau)
end
for (ln, (K, tf_)) in loops, (tn, tau) in taus
    L = loopsys(K, tf_, tau)
    wgm, gm, wpm, pm = margin(L, w)
    mag = vec(abs.(freqresp(L, w)))
    S = vec(abs.(1 ./ (1 .+ freqresp(L, w))))
    out["$(ln)|$(tn)"] = Dict("wpc" => wgm[1], "GM" => gm[1], "wgc" => wpm[1], "PM_deg" => pm[1], "Ms" => maximum(S))
end
println(JSON3.write(out))
