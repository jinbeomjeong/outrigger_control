# Independent Julia construction of the R8 d = 1 lifted (multirate) C2 loop from the raw continuous plant
# (r8d1_export.json): valve lag augmentation, ZOH at the IMU substep h via ControlSystemsBase.c2d, substep tilt mean
# from an augmented integral state (difference of the ZOH-propagated integral, not the Van Loan average map),
# 100 Hz two-stage filter, lifting by explicit substep iteration of the state transition, delay line, late attitude
# read, 10 Hz controller (PI, heave P + LPF, twist P + optional LPF, optional F_min guard on one leg),
# loop broken at the decoupled command, negative feedback; channel M_s with the other loops closed, dense grid.
using ControlSystemsBase, LinearAlgebra, JSON3

tomat(rows) = reduce(vcat, [permutedims(Float64.(r)) for r in rows])

function lifted(d)
    A = tomat(d.A); B = tomat(d.B); C = tomat(d.C); D = tomat(d.D)
    c = d.cfg; T = Float64(c.T); N = Int(c.N); h = T / N; tv = Float64(c.tau_v)
    nx = size(A, 1)
    if tv > 0
        Aa = [A B; zeros(4, nx) -I(4) / tv]; Ba = [zeros(nx, 4); I(4) / tv]; Ca = [C D]; Da = zeros(size(D))
    else
        Aa = A; Ba = B; Ca = C; Da = D
    end
    na = size(Aa, 1)
    ia = [d.i_pa, d.i_ta]
    # integral of the tilt: q' = Ct x + Dt u  -> augmented continuous system, ZOH at h
    Ct = Ca[ia, :]; Dt = Da[ia, :]
    Aq = [Aa zeros(na, 2); Ct zeros(2, 2)]; Bq = [Ba; Dt]
    sysq = c2d(ss(Aq, Bq, I(na + 2), 0), h, :zoh)
    Ad = sysq.A; Bd = sysq.B
    a = h / Float64(c.tau_f); ns = Int(c.n_st)
    nz = na + 2 * ns
    # one substep as a function of (z, u): explicit, used to build M, Nin column by column
    function sub(z, u)
        x = z[1:na]
        xq = Ad * [x; zeros(2)] + Bd * u
        xn = xq[1:na]; tilt = xq[na+1:na+2] / h
        f = reshape(z[na+1:end], 2, ns) |> copy
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
    m = Int(c.m_att); dd = Int(c.d)
    Nt = nz + 4 * dd
    A10 = zeros(Nt, Nt); B10 = zeros(Nt, 4)
    A10[1:nz, 1:nz] = Mp[N + 1]
    if dd == 0
        B10[1:nz, :] = Gam[N + 1] * Tdec
    else
        A10[1:nz, nz+4*(dd-1)+1:nz+4*dd] = Gam[N + 1]
        B10[nz+1:nz+4, :] = Tdec
        for j in 1:dd-1
            A10[nz+4*j+1:nz+4*j+4, nz+4*(j-1)+1:nz+4*j] = I(4)
        end
    end
    fsel = zeros(2, nz); fsel[:, na+2*(ns-1)+1:na+2*ns] = I(2)
    iP = Int.(d.iP); nvec = Float64.(d.n)
    padz(r) = [r; zeros(nz - na)]'
    C10 = zeros(4, Nt)
    C10[1, 1:nz] = vec(padz(Ca[d.i_clr, :])); C10[2:3, 1:nz] = fsel * Mp[m + 1]
    C10[4, 1:nz] = vec(padz(vec(nvec' * Ca[iP, :])))
    if m > 0
        C10[2:3, nz+4*(dd-1)+1:nz+4*dd] = fsel * Gam[m + 1]
    end
    g = Int(c.guard_leg)
    if g >= 0
        rg = zeros(1, Nt); rg[1, 1:nz] = sign(nvec[g + 1]) * padz(Ca[iP[g + 1], :])
        C10 = [C10; rg]
    end
    return ss(A10, B10, C10, zeros(size(C10, 1), 4), T)
end

function ctrl(d)
    c = d.cfg; T = Float64(c.T); kn = Float64(d.k_nom)
    z = tf("z", T)
    PI = (c.Kp + c.Ki * T) - c.Kp / z
    PI = minreal(((c.Kp + c.Ki * T) * z - c.Kp) / (z - 1))
    az = T / c.tau_z
    Kz = c.Kz * az * z / (z - (1 - az))
    Ktw = tf(c.Ktw / kn, T)
    if c.tau_tw > 0
        at = T / c.tau_tw
        Ktw = Ktw * at * z / (z - (1 - at))
    end
    blocks = [ss(Kz), ss(PI), ss(PI), ss(Ktw)]
    if c.guard_leg >= 0
        push!(blocks, ss(tf(c.Kg / kn, T)))
    end
    K = append(blocks...)
    if c.guard_leg >= 0
        S = zeros(4, 5); S[1:4, 1:4] = I(4); S[4, 5] = 1.0
        K = ss(K.A, K.B, S * K.C, S * K.D, T)
    end
    return K
end

out = []
for d in JSON3.read(read(ARGS[1], String))
    G = lifted(d); K = ctrl(d); L = K * G
    T = Float64(d.cfg.T)
    w = exp10.(range(-3, log10(pi / T * 0.99999), length = 200_000))
    res = Dict{String,Any}()
    for (j, ch) in enumerate(("z", "phi", "theta", "tw"))
        F = Matrix{Float64}(I, 4, 4); F[j, j] = 0.0
        H = vec(freqresp(feedback(L, ss(F, T))[j, j], w))
        res[ch] = maximum(abs.(1 ./ (1 .+ H)))
    end
    py = Dict(String(k) => Float64(v) for (k, v) in pairs(d.python_Ms))
    rel = maximum(abs(res[k] - py[k]) / py[k] for k in keys(py))
    push!(out, Dict("plant" => d.plant, "name" => d.name, "julia_Ms" => res, "python_Ms" => py, "max_rel" => rel))
end
println(JSON3.write(out))
