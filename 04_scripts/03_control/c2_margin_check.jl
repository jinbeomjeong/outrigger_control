# Independent Julia (ControlSystemsBase / RobustAndOptimalControl) cross-check of the C2 loop margins.
#
# Starts from the raw plant data exported by run_c2_design.py (M, K, C about the CoM, pad offsets, k_v, k_oil, c_n,
# IMU offset, controller constants and gains in 06_analysis/02_control/julia/c2_julia_input.json). It builds the
# continuous state space, the ZOH discretisation (c2d), the 20 ms interval average of the accelerometer tilt (own
# block exponential), the one-step availability delay of the average, the extra input delay, the 2nd-order filter,
# the PI and the twist / heave gains itself, then computes:
#   roll / pitch / twist SISO margins (others open) with margin(...; allMargins = true) on a dense log grid,
#   Ms = ||1/(1+L)||_inf (hinfnorm, tol 1e-12) for the roll channel,
#   spectral radius of the 4x4 closed loop.
# Run:
#   julia.exe --project=C:\Users\jinbeom\.claude\tools\control-julia --startup-file=no --threads=auto `
#       04_scripts/03_control/c2_margin_check.jl 06_analysis/02_control/julia/c2_julia_input.json `
#       06_analysis/02_control/julia/c2_julia_result.json
using ControlSystemsBase, RobustAndOptimalControl, LinearAlgebra, JSON3

mat(a) = reduce(vcat, [permutedims(Float64.(collect(r))) for r in a])
vecf(a) = Float64.(collect(a))

function avec(d)
    dx, dy, dz = d
    ax = [1.0, 0, 0, 0, dz, -dy]
    ay = [0.0, 1, 0, -dz, 0, dx]
    az = [0.0, 0, 1, dy, -dx, 0]
    return ax, ay, az
end

function build(c, g)
    M = mat(c.M); K = mat(c.K); Cd = mat(c.C)
    kv = vecf(c.kv); ko = vecf(c.ko); cn = vecf(c.cn)
    pad = mat(c.pad_rel); rho = vecf(c.imu_rel)
    Az = zeros(4, 6); Bk = zeros(6, 4); Bc = zeros(6, 4)
    for i in 1:4
        _, _, az = avec(pad[i, :])
        Az[i, :] = az; Bk[:, i] = kv[i] * az; Bc[:, i] = cn[i] * az
    end
    nx = 16
    A = zeros(nx, nx); B = zeros(nx, 4)
    A[1:6, 7:12] = I(6)
    A[7:12, 1:6] = -(M \ K); A[7:12, 7:12] = -(M \ Cd); A[7:12, 13:16] = M \ Bk
    B[7:12, :] = M \ Bc; B[13:16, :] = I(4)
    ax, ay, _ = avec(rho)
    Cphi = zeros(nx); Cphi[4] = 1; Cphi .+= (ay' * A[7:12, :])' ./ g
    Dphi = (ay' * B[7:12, :]) ./ g
    Cth = zeros(nx); Cth[5] = 1; Cth .-= (ax' * A[7:12, :])' ./ g
    Dth = -(ax' * B[7:12, :]) ./ g
    CP = zeros(4, nx)
    for i in 1:4
        CP[i, 1:6] = -kv[i] * Az[i, :]; CP[i, 12 + i] = kv[i]
    end
    CX = zeros(4, nx)
    for i in 1:4
        CX[i, :] = -CP[i, :] ./ ko[i]; CX[i, 12 + i] += 1
    end
    pxy = mat(c.pad_xy); cm = vecf(c.crawler_corner_mean_xy)
    Mfit = hcat(ones(4), pxy)
    wclr = (permutedims([1.0; cm]) * pinv(Mfit))[:]
    Cclr = (wclr' * CX)[:]
    return (; A, B, Cphi, Dphi = Dphi[:], Cth, Dth = Dth[:], CP, Cclr)
end

function loop(c, d)
    T = d.T; g = d.g
    p = build(c, g)
    nx = 16
    # ZOH via ControlSystemsBase.c2d
    sysd = c2d(ss(p.A, p.B, Matrix{Float64}(I, nx, nx), zeros(nx, 4)), T, :zoh)
    Ad, Bd = sysd.A, sysd.B
    # interval average: exp([[A B 0];[0 0 0];[I 0 0]] T)
    Big = zeros(2nx + 4, 2nx + 4)
    Big[1:nx, 1:nx] = p.A; Big[1:nx, nx+1:nx+4] = p.B; Big[nx+5:end, 1:nx] = I(nx)
    E = exp(Big * T)
    Ex = E[nx+5:end, 1:nx] ./ T; Eu = E[nx+5:end, nx+1:nx+4] ./ T
    Cacc = vcat(p.Cphi', p.Cth'); Dacc = vcat(p.Dphi', p.Dth')
    Cav = Cacc * Ex; Dav = Cacc * Eu + Dacc
    gains = d.gains
    dsteps = Int(gains.delay_steps)
    @assert dsteps == 1 "script written for one extra input delay step"
    Adec = mat(d.A_dec); n = vecf(d.n)
    Tdec = hcat(Adec, n)
    N = nx + 2 + 4
    Aa = zeros(N, N); Ba = zeros(N, 4)
    Aa[1:nx, 1:nx] = Ad; Aa[1:nx, nx+3:nx+6] = Bd
    Aa[nx+1:nx+2, 1:nx] = Cav; Aa[nx+1:nx+2, nx+3:nx+6] = Dav
    Ba[nx+3:nx+6, :] = Tdec
    Ca = zeros(4, N)
    Ca[1, 1:nx] = p.Cclr; Ca[2, nx+1] = 1; Ca[3, nx+2] = 1; Ca[4, 1:nx] = (n' * p.CP)[:]
    G = ss(Aa, Ba, Ca, zeros(4, 4), T)
    a = T / gains.tau_f
    zf = tf([a, 0.0], [1.0, -(1.0 - a)], T)
    F = zf^Int(gains.n_stages)
    PI = tf([gains.Kp + gains.Ki * T, -gains.Kp], [1.0, -1.0], T)
    Katt = ss(minreal(F * PI))
    Kztf = tf([gains.Kz], [1.0], T)
    if gains.tau_z > 0
        az_ = T / gains.tau_z
        Kztf = Kztf * tf([az_, 0.0], [1.0, -(1.0 - az_)], T)
    end
    Kz = ss(Kztf); Ktw = ss(tf([gains.Ktw / d.k_nom], [1.0], T))
    Kd = append(Kz, Katt, Katt, Ktw)
    L = Kd * G
    return L
end

function siso_summary(Lj, w)
    wgm, gm, wpm, pm = margin(Lj, w; allMargins = true)
    wgm = vec(wgm[1]); gm = vec(gm[1]); wpm = vec(wpm[1]); pm = vec(pm[1])
    k = argmin(wpm)            # primary (lowest-frequency) gain crossover
    up = findall(x -> x > 1, gm)
    kg = isempty(up) ? 0 : up[argmin(gm[up])]
    return (; PM = pm[k], wgc = wpm[k], GM = kg == 0 ? Inf : gm[kg], wpc = kg == 0 ? NaN : wgm[kg],
            all_pm = pm, all_wpm = wpm, all_gm = gm, all_wgm = wgm)
end

function main()
    inp = length(ARGS) >= 1 ? ARGS[1] : "06_analysis/02_control/julia/c2_julia_input.json"
    out = length(ARGS) >= 2 ? ARGS[2] : "06_analysis/02_control/julia/c2_julia_result.json"
    d = JSON3.read(read(inp, String))
    T = d.T
    w = exp10.(range(log10(1e-2), log10(pi / T * 0.9999), length = 200_000))
    res = []
    t0 = time()
    for c in d.cases
        L = loop(c, d)
        r1 = siso_summary(L[2, 2], w)
        r2 = siso_summary(L[3, 3], w)
        r4 = siso_summary(L[4, 4], w)
        S1 = feedback(ss(1.0, T), L[2, 2])
        Ms, wMs = hinfnorm(S1; tol = 1e-12)
        cl = feedback(L, ss(Matrix{Float64}(I, 4, 4), T))
        rho = maximum(abs.(poles(cl)))
        push!(res, Dict("tag" => c.tag, "roll_open_PM_deg" => r1.PM, "roll_open_wgc" => r1.wgc,
                        "roll_open_GM" => r1.GM, "roll_open_wpc" => r1.wpc, "pitch_open_PM_deg" => r2.PM,
                        "pitch_open_GM" => r2.GM, "twist_open_PM_deg" => r4.PM, "roll_open_Ms" => Ms,
                        "roll_open_w_Ms" => wMs, "cl_spectral_radius" => rho,
                        "roll_all_crossings" => Dict("wpm" => r1.all_wpm, "pm" => r1.all_pm, "wgm" => r1.all_wgm,
                                                     "gm" => r1.all_gm)))
    end
    meta = Dict("julia" => string(VERSION), "ControlSystemsBase" => string(pkgversion(ControlSystemsBase)),
                "RobustAndOptimalControl" => string(pkgversion(RobustAndOptimalControl)),
                "grid" => "200000 log points 1e-2 .. 0.9999 pi/T rad/s", "wall_s" => time() - t0)
    open(out, "w") do io
        JSON3.write(io, Dict("meta" => meta, "cases" => res))
    end
    println(JSON3.write(Dict("meta" => meta, "cases" => [Dict(k => v for (k, v) in r if k != "roll_all_crossings") for r in res])))
end

main()
