# Independent Julia construction of the C2 R8-D1 lifted loop with an attitude-only sensor model, from the raw
# continuous plant of imuatt_export.json. Sensor states are appended here (not taken from Python):
#   A: tilt -> two first-order stages tau_s = 1/(2 pi f);  B: Mahony PI complementary filter
#   xh' = w + kP (acc - xh) - bh, bh' = -kI (acc - xh), kP = 2 wc, kI = wc^2.
# Then: valve lag, ZOH at h with an integral state (substep mean), IMU transport delay of p substeps
# (explicit shift buffer), 100 Hz two-stage controller filter, lifting by substep iteration, d = 1 delay line,
# 10 Hz controller, loop broken at the decoupled command, negative feedback; channel M_s on a dense grid.
using ControlSystemsBase, LinearAlgebra, JSON3

tomat(rows) = reduce(vcat, [permutedims(Float64.(r)) for r in rows])

function with_sensor(d)
    A = tomat(d.A); B = tomat(d.B); C = tomat(d.C); D = tomat(d.D)
    kind = String(d.sensor.kind)
    ia = [d.i_pa, d.i_ta]
    kind == "S0" && return A, B, C, D, ia
    nx = size(A, 1); nu = size(B, 2)
    Cacc = C[ia, :]; Dacc = D[ia, :]
    As = zeros(nx + 4, nx + 4); As[1:nx, 1:nx] = A
    Bs = zeros(nx + 4, nu); Bs[1:nx, :] = B
    f = Float64(d.sensor.f_hz)
    outs = Int[]
    for ax in 1:2
        s1 = nx + 2ax - 1; s2 = nx + 2ax
        if kind == "A"
            tau = 1 / (2pi * f)
            As[s1, 1:nx] = Cacc[ax, :] / tau; As[s1, s1] = -1 / tau; Bs[s1, :] = Dacc[ax, :] / tau
            As[s2, s1] = 1 / tau; As[s2, s2] = -1 / tau
            push!(outs, s2)
        else
            wc = 2pi * f; kP = 2wc; kI = wc^2
            ir = ax == 1 ? Int(d.i_phidot) : Int(d.i_thetadot)
            e = zeros(1, nx + 4); e[1, 1:nx] = Cacc[ax, :]; e[1, s1] -= 1.0      # acc - xh
            As[s1, :] = kP * vec(e); As[s1, ir] += 1.0; As[s1, s2] = -1.0; Bs[s1, :] = kP * Dacc[ax, :]
            As[s2, :] = -kI * vec(e); Bs[s2, :] = -kI * Dacc[ax, :]
            push!(outs, s1)
        end
    end
    Cs = [C zeros(size(C, 1), 4)]; Ds = copy(D)
    for (k, row) in enumerate(ia)
        Cs[row, :] .= 0.0; Cs[row, outs[k]] = 1.0; Ds[row, :] .= 0.0
    end
    return As, Bs, Cs, Ds, ia
end

function lifted(d)
    A, B, C, D, ia = with_sensor(d)
    c = d.cfg; T = Float64(c.T); N = Int(c.N); h = T / N; tv = Float64(c.tau_v)
    nx = size(A, 1)
    Aa = [A B; zeros(4, nx) -I(4) / tv]; Ba = [zeros(nx, 4); I(4) / tv]; Ca = [C D]; Da = zeros(size(D))
    na = size(Aa, 1)
    Ct = Ca[ia, :]; Dt = Da[ia, :]
    Aq = [Aa zeros(na, 2); Ct zeros(2, 2)]; Bq = [Ba; Dt]
    sysq = c2d(ss(Aq, Bq, I(na + 2), 0), h, :zoh)
    Ad = sysq.A; Bd = sysq.B
    a = h / Float64(c.tau_f); ns = Int(c.n_st); p = Int(c.p_imu)
    nz = na + 2p + 2ns                        # [x, delay buffer (2 per substep), filter stages]
    function sub(z, u)
        x = z[1:na]
        xq = Ad * [x; zeros(2)] + Bd * u
        xn = xq[1:na]; tilt = xq[na+1:na+2] / h
        buf = reshape(z[na+1:na+2p], 2, p) |> copy
        if p > 0
            inp = buf[:, p]
            for k in p:-1:2
                buf[:, k] = buf[:, k-1]
            end
            buf[:, 1] = tilt
        else
            inp = tilt
        end
        fs = reshape(z[na+2p+1:end], 2, ns) |> copy
        for s in 1:ns
            fs[:, s] = (1 - a) * fs[:, s] + a * inp
            inp = fs[:, s]
        end
        return [xn; vec(buf); vec(fs)]
    end
    M = hcat([sub(Matrix{Float64}(I, nz, nz)[:, j], zeros(4)) for j in 1:nz]...)
    Nin = hcat([sub(zeros(nz), Matrix{Float64}(I, 4, 4)[:, j]) for j in 1:4]...)
    Mp = [Matrix{Float64}(I, nz, nz)]; for _ in 1:N; push!(Mp, Mp[end] * M); end
    Gam = [zeros(nz, 4)]; for j in 1:N; push!(Gam, Gam[end] + Mp[j] * Nin); end
    Tdec = [tomat(d.Amat) Float64.(d.n)]
    dd = Int(c.d)
    Nt = nz + 4dd
    A10 = zeros(Nt, Nt); B10 = zeros(Nt, 4)
    A10[1:nz, 1:nz] = Mp[N + 1]
    A10[1:nz, nz+4*(dd-1)+1:nz+4*dd] = Gam[N + 1]
    B10[nz+1:nz+4, :] = Tdec
    for j in 1:dd-1
        A10[nz+4*j+1:nz+4*j+4, nz+4*(j-1)+1:nz+4*j] = I(4)
    end
    fsel = zeros(2, nz); fsel[:, na+2p+2*(ns-1)+1:na+2p+2*ns] = I(2)
    iP = Int.(d.iP); nvec = Float64.(d.n)
    padz(r) = [r; zeros(nz - na)]'
    C10 = zeros(4, Nt)
    C10[1, 1:nz] = vec(padz(Ca[d.i_clr, :])); C10[2:3, 1:nz] = fsel
    C10[4, 1:nz] = vec(padz(vec(nvec' * Ca[iP, :])))
    g = Int(d.guard_leg)
    if g >= 0
        rg = zeros(1, Nt); rg[1, 1:nz] = sign(nvec[g + 1]) * padz(Ca[iP[g + 1], :])
        C10 = [C10; rg]
    end
    return ss(A10, B10, C10, zeros(size(C10, 1), 4), T)
end

function ctrl(d)
    c = d.cfg; T = Float64(c.T); kn = Float64(d.k_nom)
    z = tf("z", T)
    PI = minreal(((c.Kp + c.Ki * T) * z - c.Kp) / (z - 1))
    az = T / c.tau_z
    Kz = c.Kz * az * z / (z - (1 - az))
    at = T / c.tau_tw
    Ktw = tf(c.Ktw / kn, T) * at * z / (z - (1 - at))
    blocks = [ss(Kz), ss(PI), ss(PI), ss(Ktw)]
    g = Int(d.guard_leg)
    g >= 0 && push!(blocks, ss(tf(c.Kg / kn, T)))
    K = append(blocks...)
    if g >= 0
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
    rel = Dict(k => (res[k] - py[k]) / py[k] for k in keys(py))
    push!(out, Dict("plant" => d.plant, "name" => d.name, "guard_leg" => d.guard_leg, "julia_Ms" => res,
                    "python_Ms" => py, "rel" => rel, "max_abs_rel" => maximum(abs.(values(rel)))))
end
open(ARGS[2], "w") do io
    JSON3.write(io, out)
end
println("cases ", length(out), " worst |rel| ", maximum(o["max_abs_rel"] for o in out))
