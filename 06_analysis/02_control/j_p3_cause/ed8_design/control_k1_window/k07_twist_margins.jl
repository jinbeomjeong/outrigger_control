# k07: Julia path of the twist-loop margins (independent of the Python loop JSON).
# L(z) = g K_tw z^-1 ZOH{1/(s(tau_v s+1))} 0.5 z/(z-0.5), Ts 0.1 s; built from the raw constants.
# Run: julia-mcp run_file with project C:\Users\jinbeom\.claude\tools\control-julia (2026-11-26 run
# from a scratchpad copy of this exact text).
using ControlSystemsBase, JSON3
const TS = 0.1; const KTW = 0.5; const TAUV = 0.1; const FP = 0.5
outdir = raw"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_k1_window\loops"
cplx(v) = Dict("re" => real.(v), "im" => imag.(v))
P = c2d(tf(1.0, [TAUV, 1.0, 0.0]), TS, :zoh)
D = tf(1.0, [1.0, 0.0], TS)
F = tf([1 - FP, 0.0], [1.0, -FP], TS)
w = exp10.(range(-4, log10(pi / TS) - 1e-9, length = 200_000))
for (name, g) in (("nominal_r1_sigma1", 1.0), ("r2.3_sigma1.5", 2.3 / 1.5), ("r3.6_sigma1.5", 3.6 / 1.5))
    L = g * KTW * D * P * F
    wgm, gm, wpm, pm = margin(L, w)
    gmv, wgmv, pmv, wpmv = vec(gm), vec(wgm), vec(pm), vec(wpm)
    ig = argmin(abs.(log.(gmv))); ip = argmin(abs.(pmv))
    S = feedback(1, L)
    resp = vec(freqresp(S, w))
    q = Dict("gm" => gmv[ig], "wpc" => wgmv[ig], "pm_deg" => pmv[ip], "wgc" => wpmv[ip],
             "dm_s" => deg2rad(pmv[ip]) / wpmv[ip], "ms" => maximum(abs.(resp)),
             "cl_poles" => cplx(poles(feedback(L, 1))))
    open(joinpath(outdir, "jl_$name.json"), "w") do io
        JSON3.write(io, Dict("schema" => "ctrl-xval/1", "source" => "julia ControlSystemsBase dense grid", "quantities" => q))
    end
    println(name, " ", q["gm"], " ", q["pm_deg"], " ", q["wgc"], " ", q["ms"])
end
