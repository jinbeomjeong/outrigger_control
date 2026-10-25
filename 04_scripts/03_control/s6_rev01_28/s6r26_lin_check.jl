# Julia cross-check (spec rev. 26): channel M_s with the other three loops closed, for the exported discrete loop
# matrices L (4x4, channels z, phi, theta, tw), negative feedback, dense frequency grid up to Nyquist.
using ControlSystemsBase, JSON3, LinearAlgebra
for f in ARGS
    d = JSON3.read(read(f, String))
    out = Dict{String,Any}("tag" => d.tag)
    for (name, l) in pairs(d.loops)
        T = Float64(l.T)
        A = reduce(vcat, [permutedims(Float64.(r)) for r in l.A]); B = reduce(vcat, [permutedims(Float64.(r)) for r in l.B])
        C = reduce(vcat, [permutedims(Float64.(r)) for r in l.C]); D = reduce(vcat, [permutedims(Float64.(r)) for r in l.D])
        L = ss(A, B, C, D, T)
        w = exp10.(range(-4, log10(pi / T * 0.9999), length = 200_000))
        res = Dict{String,Float64}()
        for (j, ch) in enumerate(("z", "phi", "theta", "tw"))
            F = Matrix{Float64}(I, 4, 4); F[j, j] = 0.0
            Lc = feedback(L, ss(F, T))
            Lj = Lc[j, j]
            H = vec(freqresp(Lj, w))
            res[ch] = maximum(abs.(1 ./ (1 .+ H)))
        end
        out[String(name)] = Dict("julia_Ms" => res, "python_Ms" => l.python_Ms)
    end
    println(JSON3.write(out))
end
