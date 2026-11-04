# Independent recomputation of the S8 SA-4 clause from the raw 1 ms series (CSV export). The stop time is read from each
# run's result.json event list here, no Python result is read. Args: set SCRATCH to the CSV folder before include.
using CSV, DataFrames, JSON3

const SCRATCH_DIR = raw"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_final10"
const OUT = raw"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono\xcheck_s8off_julia.json"
const S9 = raw"C:\workspace\outrigger_control\07_results\S9"
const CASE_NAME = "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
const BATCHES = Dict("off_stored" => "batch_FINAL-REP_20261030_223359", "off_eps1e-3" => "batch_s8off_eps1e-3_20261104",
                     "off_eps2e-3" => "batch_s8off_eps2e-3_20261104", "on_stored" => "batch_COUPLED_eta085_20261104_142213")
const MARGIN_N = 0.01 * 380112.91206408414

results = Dict{String,Any}()
for (name, batch) in BATCHES
    res = JSON3.read(read(joinpath(S9, batch, CASE_NAME, "result.json"), String))
    ev = res.events[findfirst(e -> startswith(String(e.name), "FAULT_LIFT_STROKE_LIMIT"), res.events)]
    tstop = Float64(ev.t_s)
    df = CSV.read(joinpath(SCRATCH_DIR, "s8off_" * name * ".csv"), DataFrame)
    t, c = df.t_s, df.crawler_N
    k = searchsortedfirst(t, tstop)
    mx = maximum(@view c[k:end])
    results[name] = Dict("t_stop_abs_s" => tstop, "event" => String(ev.name), "crawler_at_stop_kN" => c[k] / 1e3, "crawler_max_after_kN" => mx / 1e3,
                         "limit_kN" => (c[k] + MARGIN_N) / 1e3, "clause_pass" => mx <= c[k] + MARGIN_N, "crawler_end_kN" => c[end] / 1e3,
                         "F_min_after_stop_kN" => [minimum(@view df[k:end, q]) / 1e3 for q in (:F_FL_N, :F_FR_N, :F_RL_N, :F_RR_N)])
end
open(OUT, "w") do io
    JSON3.write(io, results)
end
println(JSON3.write(results))
