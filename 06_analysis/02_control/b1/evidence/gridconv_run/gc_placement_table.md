# B1 GC-1~4 placement table (2026-11-10, compute-scheduler-expert, plan only)

State at planning: P 2.1 % / E 44.1 % (E busy: Chrono k2 check x2, dynamics-dev touch_phase acceptance 5 workers, pytest -n 6; all pinned 0x0FFF0000) / available 16587 MB (usable 12491) / commit 38 % / reservations 0. Speed table 2026-10-26 (E/P micro 1.34-1.47; observed SCM E/P 1.5-1.9).

Decision: E pool, 3 lanes, 12 threads (4 threads per row, fixed), self_pin ecore kept (mask 0x0FFF0000, EcoQoS off), OMP_WAIT_POLICY=PASSIVE.
- Lane 1: GC-4 (est 16 min solo)
- Lane 2: GC-2 (10.6 min)
- Lane 3: GC-3 (5.4) then GC-1 (4.4) = 9.8 min
Memory 4 x ~132 MB (3 concurrent ~400 MB) vs usable 12491 MB: fine, no big-memory task.
Wall (estimate, E already ~5 logical busy by other tenants): 18-24 min, ends with GC-4.
Narrow per-row masks rejected: other tenants occupy the whole E pool, narrow masks gain nothing, and place_process would override outer mask anyway.
Not 4-at-once: 16 threads + ~5 busy on 12 logical = 1.75x oversubscription, no wall gain (GC-4 is the critical path).

launcher: gc_lanes.ps1 (sha256 346CD7B24566A25B9BAD4AAF34EAA0232BE7634551613BDEFC7B252F7AB1B8EC); caller fills $rowArgs (placeholders) before running.
