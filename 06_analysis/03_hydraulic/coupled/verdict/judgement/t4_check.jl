# Independent Julia assembly of the T-4 loops from the raw continuous plant (t4_export.json):
# flow-saturation structure, valve lag, ZOH at the IMU substep via c2d, substep tilt mean from an
# integral state, 100 Hz two-stage filter, explicit lifting, one-period delay line, 10 Hz controller,
# negative feedback; channel M_s with the other loops closed, closed-loop eigenvalues.
# Same construction as r8d1_check.jl; the structure is applied here from Mu, Mf, not read from Python.
using ControlSystemsBase, LinearAlgebra, JSON3

tomat(rows) = reduce(vcat, [permutedims(Float64.(r)) for r in rows])

function structured(d)
    A = tomat(d.A); B = tomat(d.B); C = tomat(d.C); D = tomat(d.D)
    Mu = tomat(d.Mu); Mf = tomat(d.Mf)
    iP = Int.(d.iP)
    CP = C[iP, :]; DP = D[iP, :]
    W = inv(Matrix{Float64}(I, 4, 4) - Mf * DP)
    return A + B * W * Mf * CP, B * W * Mu, C + D * W * Mf * CP, D * W * Mu
end

function lifted(d)
    A, B, C, D = structured(d)
    c = d.cfg; T = Float64(c.T); N = Int(c.N); h = T / N; tv = Float64(c.tau_v)
    nx = size(A, 1)
    Aa = [A B; zeros(4, nx) -I(4) / tv]; Ba = [zeros(nx, 4); I(4) / tv]; Ca = [C D]; Da = zeros(size(D))
    na = size(Aa, 1)
    ia = [d.i_pa, d.i_ta]
    Ct = Ca[ia, :]; Dt = Da[ia, :]
    Aq = [Aa zeros(na, 2); Ct zeros(2, 2)]; Bq = [Ba; Dt]
    sysq = c2d(ss(Aq, Bq, Matrix{Float64}(I, na + 2, na + 2), zeros(na + 2, 4)), h, :zoh)
    Ad = sysq.A; Bd = sysq.B
    a = h / Float64(c.tau_f); ns = Int(c.n_st)
    nz = na + 2 * ns
    function sub(z, u)
        x = z[1:na]
        xq = Ad * [x; zeros(2)] + Bd * u
        xn = xq[1:na]; tilt = xq[na+1:na+2] / h
        f = copy(reshape(z[na+1:end], 2, ns))
        inp = tilt
        for s in 1:ns
            f[:, s] = (1 - a) * f[:, s] + a * inp
            inp = f[:, s]
        end
        return [xn; vec(f)]
    end
    M = hcat([sub(Matrix{Float64}(I, nz, nz)[:, j], zeros(4)) for j in 1:nz]...)
    Nin = hcat([sub(zeros(nz), Matrix{Float64}(I, 4, 4)[:, j]) for j in 1:4]...)
    Mp = [Matrix{Float64}(I, nz, nz)]; for _ in 1:N; push!(Mp, Mp[end] * M); end
    Gam = [zeros(nz, 4)]; for j in 1:N; push!(Gam, Gam[end] + Mp[j] * Nin); end
    Tdec = [tomat(d.Amat) Float64.(d.n)]
    dd = Int(c.d)
    Nt = nz + 4 * dd
    A10 = zeros(Nt, Nt); B10 = zeros(Nt, 4)
    A10[1:nz, 1:nz] = Mp[N + 1]
    A10[1:nz, nz+4*(dd-1)+1:nz+4*dd] = Gam[N + 1]
    B10[nz+1:nz+4, :] = Tdec
    fsel = zeros(2, nz); fsel[:, na+2*(ns-1)+1:na+2*ns] = Matrix{Float64}(I, 2, 2)
    iP = Int.(d.iP); nvec = Float64.(d.n)
    padz(r) = [r; zeros(nz - na)]'
    C10 = zeros(4, Nt)
    C10[1, 1:nz] = vec(padz(Ca[d.i_clr, :])); C10[2:3, 1:nz] = fsel
    C10[4, 1:nz] = vec(padz(vec(nvec' * Ca[iP, :])))
    return ss(A10, B10, C10, zeros(4, 4), T)
end

function ctrl(d)
    c = d.cfg; T = Float64(c.T); kn = Float64(d.k_nom)
    z = tf("z", T)
    PI = minreal(((c.Kp + c.Ki * T) * z - c.Kp) / (z - 1))
    az = T / c.tau_z
    Kz = c.Kz * az * z / (z - (1 - az))
    at = T / c.tau_tw
    Ktw = tf(c.Ktw / kn, T) * at * z / (z - (1 - at))
    return append(ss(Kz), ss(PI), ss(PI), ss(Ktw))
end

function run_all(path)
    out = []
    for d in JSON3.read(read(path, String))
        G = lifted(d); K = ctrl(d); L = K * G
        T = Float64(d.cfg.T)
        w = exp10.(range(-3, log10(pi / T * 0.9999), length = 20_000))
        res = Dict{String,Float64}()
        H = freqresp(L, w)
        for (j, ch) in enumerate(("z", "phi", "theta", "tw"))
            F = Matrix{Float64}(I, 4, 4); F[j, j] = 0.0
            best = 0.0
            for k in axes(H, 3)
                Hk = H[:, :, k]
                Cl = (Matrix{ComplexF64}(I, 4, 4) + Hk * F) \ Hk
                best = max(best, abs(1 / (1 + Cl[j, j])))
            end
            res[ch] = best
        end
        Lc = feedback(L, ss(Matrix{Float64}(I, 4, 4), T))
        p = poles(Lc)
        i1 = argmin(abs.(p .- 1))
        rest = deleteat!(copy(p), i1)
        res["rho_all"] = maximum(abs.(p))
        res["rho_excl"] = maximum(abs.(rest))
        py = Dict(String(k) => Float64(v) for (k, v) in pairs(d.python))
        rel = Dict(k => abs(res[k] - py[k]) / max(abs(py[k]), 1e-12) for k in keys(py))
        push!(out, Dict("struct" => String(d.struct), "plant" => String(d.plant), "julia" => res, "python" => py, "rel" => rel,
                        "max_rel_Ms" => maximum(rel[k] for k in ("z", "phi", "theta", "tw")), "rel_rho" => rel["rho_excl"]))
    end
    return out
end

out = run_all(raw"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement\t4_export.json")
write(raw"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement\t4_check_julia.json", JSON3.write(out))
for r in out
    println(r["struct"], " | ", r["plant"], " | py ", round.(Float64[r["python"][k] for k in ("phi", "theta", "tw", "rho_excl")], digits = 6),
            " jl ", round.(Float64[r["julia"][k] for k in ("phi", "theta", "tw", "rho_excl")], digits = 6), " relMs ", r["max_rel_Ms"], " relrho ", r["rel_rho"])
end
