# Independent check of the g8|29 numbers from the stored run rows (no Python results used as inputs to the formulas):
# 1) raw corner bias b_k = c_k(t_P) - (rho_k - min rho), rho_k = y_k dphi - x_k dtheta, against the controller's logged value;
# 2) least squares of the FR stroke at the end on the RL-corner bias, READY rows, with an arm term;
# 3) Fisher exact test of the guard-stop counts and Clopper-Pearson upper bounds.
using JSON3, Printf, LinearAlgebra

here = raw"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_g8"
geo = JSON3.read(read(joinpath(here, "geo.json"), String))
rows = JSON3.read(read(joinpath(here, "g8_29_table.json"), String))
xy = [collect(Float64, c) for c in geo.crawler_corners_xy_m]

function bias_err(r)
    d2r = pi / 180
    dphi = (r.att_tP[1] - r.settle[1]) * d2r
    dth = (r.att_tP[2] - r.settle[2]) * d2r
    rho = [c[2] * dphi - c[1] * dth for c in xy] .* 1e3
    b = collect(Float64, r.c_tP) .- (rho .- minimum(rho))
    return maximum(abs.(b .- collect(Float64, r.raw_b)))
end

base = [r for r in rows if r.case == "29" && r.tag in ("off", "c4g2")]
errs = [bias_err(r) for r in base]
@printf("bias reconstruction: n %d, max |b_julia - b_logged| %.3f mm\n", length(base), maximum(errs))

ready = [r for r in base if r.final == "ready"]
y = [Float64(r[Symbol("end")][2]) for r in ready]
b = [Float64(r.bias[3]) for r in ready]
arm = [r.tag == "c4g2" ? 1.0 : 0.0 for r in ready]
X = hcat(ones(length(y)), b, arm)
coef = X \ y
res = y - X * coef
sig = sqrt(sum(abs2, res) / (length(y) - 3))
se = sqrt.(diag(inv(X' * X))) .* sig
@printf("FR end stroke [mm] = %.2f + %.4f b_RL + %.3f C4G2; se %.4f, %.3f; rms %.3f mm, n %d\n", coef..., se[2], se[3], sqrt(sum(abs2, res) / length(y)), length(y))

count_stop(tag) = (s = [r for r in base if r.tag == tag && startswith(String(r.key), "L2")]; (sum(r.final == "fault" for r in s), length(s)))
s_on, n_on = count_stop("c4g2")
s_off, n_off = count_stop("off")
logC(n, k) = sum(log(i) for i in (n - k + 1):n; init = 0.0) - sum(log(i) for i in 1:k; init = 0.0)
hyp(k) = exp(logC(n_on, k) + logC(n_off, s_on + s_off - k) - logC(n_on + n_off, s_on + s_off))
p_one = sum(hyp(k) for k in s_on:min(n_on, s_on + s_off))
@printf("guard stops L2: C4G2 %d/%d, off %d/%d, Fisher one-sided p %.4f\n", s_on, n_on, s_off, n_off, p_one)

function bcdf(k, n, p)
    sum(exp(logC(n, i) + i * log(p) + (n - i) * log1p(-p)) for i in 0:k)
end
function cp(k, n)
    a, c = 1e-12, 1 - 1e-12
    for _ in 1:200
        m = (a + c) / 2
        bcdf(k, n, m) > 0.05 ? (a = m) : (c = m)
    end
    (a + c) / 2
end
@printf("CP95 off %.2f%%, C4G2 %.2f%%\n", 100cp(s_off, n_off), 100cp(s_on, n_on))
