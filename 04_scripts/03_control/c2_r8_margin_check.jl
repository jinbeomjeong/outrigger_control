# Julia cross-check of run_c2_r8_linear_check.py (00_docs/04_control/s6_control_spec.md rev. 26, 99.1):
# channel M_s with the other three loops closed (negative feedback), from the exported discrete broken-loop
# matrices L (channels z, phi, theta, tw), dense grid up to Nyquist. Moved from the scratchpad (s6r26_lin_check.jl).
# Run: julia --project=<control-julia> --startup-file=no 04_scripts/03_control/c2_r8_margin_check.jl <export.json>...
using ControlSystemsBase, JSON3, LinearAlgebra
tomat(rows) = reduce(vcat, [permutedims(Float64.(r)) for r in rows])
for f in ARGS
    d = JSON3.read(read(f, String))
    out = Dict{String,Any}()
    for (name, l) in pairs(d.loops)
        T = Float64(l.T)
        L = ss(tomat(l.A), tomat(l.B), tomat(l.C), tomat(l.D), T)
        w = exp10.(range(-4, log10(pi / T * 0.9999), length = 200_000))
        res = Dict{String,Float64}()
        for (j, ch) in enumerate(("z", "phi", "theta", "tw"))
            F = Matrix{Float64}(I, 4, 4); F[j, j] = 0.0
            H = vec(freqresp(feedback(L, ss(F, T))[j, j], w))
            res[ch] = maximum(abs.(1 ./ (1 .+ H)))
        end
        out[String(name)] = Dict("tag" => get(l, :tag, ""), "julia_Ms" => res, "python_Ms" => l.python_Ms)
    end
    println(JSON3.write(out))
end
