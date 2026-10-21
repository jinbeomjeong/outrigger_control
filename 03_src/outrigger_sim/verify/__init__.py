"""V-check automation shared by pytest and the stage runners.

Present (00_docs/03_chrono/chrono_build_plan.md 3.1, 3.4): reference (R12 reference keys),
checks (``CheckResult`` and comparison helpers), metrics (modal projection, damped-sine fits),
s1, s2a, s2b, s3 (per-stage V checks).
The integrated runner 04_scripts/02_chrono/run_verify.py is not implemented yet; the per-stage
04_scripts/02_chrono/run_S*.py scripts take its place.
"""
