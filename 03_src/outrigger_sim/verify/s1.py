"""S1 checks: V0 (model = YAML), V1-V3 (level statics), V13 (solver health).

``00_docs/03_chrono/chrono_build_plan.md`` S1 table; ``dynamics_model.md`` 5 (V0-V3, V13,
V0 crawler addendum) and 4.5. Engine independent: the inputs are the model inventory
(``L1Model.v0_inventory()``, a JSON-ready dict) and window statistics computed from copied
states. Tolerances are those of the plan; where Chrono stores a value in single precision
the comparison says so (``ChContactMaterialSMC`` keeps ``kn``, ``gn``, ``kt``, ``gt`` and the
friction as 32-bit floats, measured 2026-10-20: ``SetKn(20813595.4)`` reads back
``20813596.0``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.geometry import leg_com_body_m, pad_sphere_centre_body_m
from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.verify.checks import (
    CheckResult,
    check_abs,
    check_equal,
    check_max,
    check_rel,
)
from outrigger_sim.verify.reference import (
    L1_CONTACT_FORCE_N,
    L1_CYLINDER_FORCE_N,
    L1_STATIC_ATTITUDE_DEG,
    L1_STATIC_PENETRATION_MM,
    TOTAL_WEIGHT_INCL_RODS_N,
    References,
)

V0_REL_TOL = 1.0e-9
V0_POS_ABS_TOL_M = 1.0e-9
FLOAT32_REL_TOL = 2.0**-24
"""Half an ulp of a float32 (relative), the best a 32-bit stored material value can do."""

V1_SUM_REL_TOL = 1.0e-4
V1_LEG_FRACTION_OF_QUARTER_WEIGHT = 1.0e-2
V2_REL_TOL = 0.05
V3_ABS_TOL_DEG = 0.002
V13_DRIFT_DEG = 1.0e-4
V13_FORCE_FRACTION_OF_QUARTER_WEIGHT = 1.0e-3
V13_MOTOR_VIOLATION_M = 1.0e-6

CRAWLER_KN_KEY = "contact.crawler.kn_per_sphere_N_m"
CRAWLER_GN_KEY = "contact.crawler.gn_per_sphere_1_s"


def _f32(value: float) -> float:
    return float(np.float32(value))


def _pad_dashpot(params: Params, leg_index: int, head_only: bool) -> tuple[float, float]:
    """YAML pad dashpot ``(gn, cn)`` the model uses (``chrono/contact.pad_material_values``):
    ``gn_per_pad_1_s`` / ``cn_per_pad_N_s_m`` (LOCK basis with the REXOME35 YAML,
    dynamics_model.md 5.12.8 Q-D3), or the head-only regression keys when the model was built
    with ``head_only_dashpot``."""
    l1 = params.contact.rigid_floor.L1
    if not head_only:
        return float(l1.gn_per_pad_1_s[leg_index]), float(l1.cn_per_pad_N_s_m[leg_index])
    name = params.legs[leg_index].name
    return (
        float(params.get("contact.rigid_floor.L1.gn_per_pad_head_only_1_s")[name]),
        float(params.get("contact.rigid_floor.L1.cn_per_pad_head_only_N_s_m")[name]),
    )


def _material_checks(
    prefix: str, entries: Sequence[Mapping[str, Any]], kn: float, gn: float
) -> list[CheckResult]:
    kn_got = [e["kn_N_m"] for e in entries]
    gn_got = [e["gn_1_s"] for e in entries]
    zeros = [[e["kt_N_m"], e["gt_1_s"], e["friction"], e["static_friction"]] for e in entries]
    note = "Chrono stores SMC material values as float32: compared with the float32 of the YAML"
    return [
        check_equal(
            "V0",
            f"{prefix} kn = float32(YAML)",
            kn_got,
            [_f32(kn)] * len(entries),
            "N/m",
            note=note,
        ),
        check_rel(
            "V0",
            f"{prefix} kn vs YAML (float32 rounding)",
            kn_got,
            [kn] * len(entries),
            FLOAT32_REL_TOL,
            "N/m",
        ),
        check_equal(
            "V0",
            f"{prefix} gn = float32(YAML)",
            gn_got,
            [_f32(gn)] * len(entries),
            "1/s",
            note=note,
        ),
        check_rel(
            "V0",
            f"{prefix} gn vs YAML (float32 rounding)",
            gn_got,
            [gn] * len(entries),
            FLOAT32_REL_TOL,
            "1/s",
        ),
        check_equal(
            "V0",
            f"{prefix} kt, gt, mu, mu_s = 0 (R8)",
            zeros,
            [[0.0, 0.0, 0.0, 0.0]] * len(entries),
        ),
    ]


def v0_checks(params: Params, inventory: Mapping[str, Any]) -> list[CheckResult]:
    """V0: model values = YAML (plan S1 V0 row, R1, R2, R5-R8, R13, R14)."""
    out: list[CheckResult] = []
    g = params.meta.gravity_m_s2
    out.append(
        check_equal("V0", "gravity vector (R1)", inventory["gravity_m_s2"], [0.0, 0.0, -g], "m/s^2")
    )
    out.append(
        check_equal(
            "V0",
            "floor mass 1e9 kg (R6)",
            inventory["floor"]["mass_kg"],
            params.contact.rigid_floor.ground_body_mass_kg,
            "kg",
        )
    )
    out.append(check_equal("V0", "floor fixed (R6)", inventory["floor"]["fixed"], True))

    # superstructure mass properties
    props = params.superstructure.mass_properties
    sup = inventory["superstructure"]
    level = params.level.value
    out.append(
        check_rel(
            "V0", f"superstructure mass ({level})", sup["mass_kg"], props.mass_kg, V0_REL_TOL, "kg"
        )
    )
    out.append(
        check_abs(
            "V0",
            f"superstructure COM, body coords ({level})",
            sup["com_body_m"],
            props.com_m,
            V0_POS_ABS_TOL_M,
            "m",
        )
    )
    out.append(
        check_rel(
            "V0",
            f"superstructure inertia about COM, body axes ({level})",
            sup["inertia_kg_m2"],
            props.inertia_kg_m2,
            V0_REL_TOL,
            "kg m^2",
        )
    )

    # legs
    ext = inventory["extensions_m"]
    for i, leg in enumerate(params.legs):
        got = inventory["legs"][i]
        mp = leg.moving_part
        out.append(
            check_rel(
                "V0", f"{leg.name} moving part mass", got["mass_kg"], mp.mass_kg, V0_REL_TOL, "kg"
            )
        )
        out.append(
            check_abs(
                "V0",
                f"{leg.name} moving part COM at e",
                got["com_body_m"],
                leg_com_body_m(params, i, ext[i]),
                V0_POS_ABS_TOL_M,
                "m",
            )
        )
        out.append(
            check_rel(
                "V0",
                f"{leg.name} moving part inertia",
                got["inertia_kg_m2"],
                mp.inertia_kg_m2,
                V0_REL_TOL,
                "kg m^2",
            )
        )
        spheres = got["collision"]
        out.append(
            check_equal(
                "V0", f"{leg.name} one pad sphere", [s["type"] for s in spheres], ["SPHERE"]
            )
        )
        out.append(
            check_rel(
                "V0",
                f"{leg.name} pad sphere radius = swivel height",
                spheres[0]["radius_m"],
                leg.pad.swivel_center_above_pad_bottom_m,
                V0_REL_TOL,
                "m",
            )
        )
        centre_body = np.asarray(spheres[0]["pos_local_m"]) + np.asarray(got["com_body_m"])
        out.append(
            check_abs(
                "V0",
                f"{leg.name} pad sphere centre = swivel centre at e",
                centre_body,
                pad_sphere_centre_body_m(params, i, ext[i]),
                V0_POS_ABS_TOL_M,
                "m",
            )
        )
        l1 = params.contact.rigid_floor.L1
        gn_yaml, cn_yaml = _pad_dashpot(params, i, bool(inventory.get("head_only_dashpot")))
        out.extend(
            _material_checks(f"{leg.name} pad sphere", spheres, l1.kn_per_pad_N_m[i], gn_yaml)
        )
        out.append(
            check_rel(
                "V0",
                f"{leg.name} gn = cn / m_moving (R5)",
                gn_yaml,
                cn_yaml / mp.mass_kg,
                1e-8,
                "1/s",
                note="YAML consistency (9 significant digits)",
            )
        )
        patch = next(
            p for p in inventory["floor"]["collision_named"] if p["name"] == f"pad_{leg.name}"
        )
        out.append(
            check_equal(
                "V0",
                f"{leg.name} pad patch material = pad sphere material",
                [
                    patch["kn_N_m"],
                    patch["gn_1_s"],
                    patch["kt_N_m"],
                    patch["gt_1_s"],
                    patch["friction"],
                ],
                [spheres[0]["kn_N_m"], spheres[0]["gn_1_s"], 0.0, 0.0, 0.0],
            )
        )
        bushing = inventory["bushings"][i]
        if bushing is not None:
            k = l1.bushing_stiffness_per_pad_N_m[i]
            out.append(
                check_equal(
                    "V0",
                    f"{leg.name} bushing stiffness (kt, kt, 0)",
                    bushing["stiffness_N_m"],
                    [k, k, 0.0],
                    "N/m",
                )
            )
            c = l1.bushing_damping_input_per_pad_N_s_m[i]
            out.append(
                check_equal(
                    "V0",
                    f"{leg.name} bushing damping input (c, c, 0)",
                    bushing["damping_input_N_s_m"],
                    [c, c, 0.0],
                    "N s/m",
                )
            )
            out.append(
                check_rel(
                    "V0",
                    f"{leg.name} bushing damping input = ct / 2 (R7)",
                    c,
                    0.5 * l1.ct_per_pad_N_s_m[i],
                    1e-8,
                    "N s/m",
                    note="YAML consistency (9 significant digits)",
                )
            )
        out.append(
            check_abs(
                "V0",
                f"{leg.name} motor position = extension (R4)",
                inventory["motor_pos_m"][i],
                ext[i],
                V0_POS_ABS_TOL_M,
                "m",
            )
        )
        out.append(
            check_equal(
                "V0",
                f"{leg.name} motor link constraints (guide 5 + motor 1)",
                inventory["motor_constraints"][i],
                6,
            )
        )

    # crawler (R13, V0 addendum)
    layout = inventory.get("crawler_layout")
    if layout is not None:
        kn = float(params.get(CRAWLER_KN_KEY))
        gn = float(params.get(CRAWLER_GN_KEY))
        spheres = sup["collision"]
        out.append(
            check_equal(
                "V0",
                "crawler spheres 24 (12 roller + 12 end shoe)",
                [len(spheres), layout["n_roller"]],
                [24, 12],
            )
        )
        centres = np.asarray([s["pos_local_m"] for s in spheres]) + np.asarray(sup["com_body_m"])
        out.append(
            check_abs(
                "V0",
                "crawler sphere centres = YAML layout D",
                centres,
                layout["centres_body_m"],
                V0_POS_ABS_TOL_M,
                "m",
            )
        )
        radius = float(params.get("contact.crawler.sphere_layout.sphere_radius_m"))
        out.append(
            check_equal(
                "V0",
                "crawler sphere radius",
                [s["radius_m"] for s in spheres],
                [radius] * len(spheres),
                "m",
            )
        )
        out.extend(_material_checks("crawler sphere", spheres, kn, gn))
        strips = [
            p for p in inventory["floor"]["collision_named"] if p["name"].startswith("crawler")
        ]
        out.append(
            check_equal(
                "V0",
                "crawler patches (2) material = crawler sphere material",
                [
                    [p["kn_N_m"], p["gn_1_s"], p["kt_N_m"], p["gt_1_s"], p["friction"]]
                    for p in strips
                ],
                [[spheres[0]["kn_N_m"], spheres[0]["gn_1_s"], 0.0, 0.0, 0.0]] * 2,
            )
        )

    # collision families (R14)
    collides = inventory["collides"]
    out.append(
        check_equal(
            "V0",
            "rod - superstructure/crawler pairs disabled (R14)",
            collides["rod_with_superstructure"],
            [False] * len(LEG_ORDER),
        )
    )
    out.append(
        check_equal(
            "V0", "rod - floor pairs enabled", collides["rod_with_floor"], [True] * len(LEG_ORDER)
        )
    )
    if collides["superstructure_with_floor"] is not None:
        out.append(
            check_equal(
                "V0",
                "superstructure (crawler) - floor enabled",
                collides["superstructure_with_floor"],
                True,
            )
        )
    out.append(
        check_equal(
            "V0", "collision system Bullet (R2)", inventory["collision_system_name"], "BULLET"
        )
    )
    return out


@dataclass(frozen=True)
class StillWindowStats:
    """Statistics of the still window (copied states, sampled every ``sample_dt_s``)."""

    t_start_s: float
    t_end_s: float
    n_samples: int
    contact_force_mean_N: NDArray[np.float64]
    contact_force_span_N: NDArray[np.float64]
    cylinder_force_mean_N: NDArray[np.float64]
    penetration_mean_mm: NDArray[np.float64]
    roll_mean_deg: float
    pitch_mean_deg: float
    roll_span_deg: float
    pitch_span_deg: float
    motor_violation_max_m: float
    contacts_per_leg_min: NDArray[np.int64]
    contacts_per_leg_max: NDArray[np.int64]
    system_contacts_range: tuple[int, int]
    any_nan: bool


def v1_v3_checks(params: Params, refs: References, stats: StillWindowStats) -> list[CheckResult]:
    """V1 (forces), V2 (penetration), V3 (attitude) against the level reference values."""
    level = params.level.value
    contact_ref = np.asarray(refs.get(L1_CONTACT_FORCE_N, level=level), dtype=float)
    cyl_ref = np.asarray(refs.get(L1_CYLINDER_FORCE_N, level=level), dtype=float)
    total = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N))
    pen_ref = np.asarray(refs.get(L1_STATIC_PENETRATION_MM, level=level), dtype=float)
    att_ref = np.asarray(refs.get(L1_STATIC_ATTITUDE_DEG, level=level), dtype=float)
    quarter = total / 4.0
    key = lambda k: k.resolve(level=level).notation()  # noqa: E731
    return [
        check_rel(
            "V1",
            "sum of pad contact forces",
            float(stats.contact_force_mean_N.sum()),
            total,
            V1_SUM_REL_TOL,
            "N",
            ref_key=key(TOTAL_WEIGHT_INCL_RODS_N),
        ),
        check_abs(
            "V1",
            "pad contact force per leg",
            stats.contact_force_mean_N,
            contact_ref,
            V1_LEG_FRACTION_OF_QUARTER_WEIGHT * quarter,
            "N",
            ref_key=key(L1_CONTACT_FORCE_N),
            note="tol = 1 % W/4",
        ),
        check_abs(
            "V1",
            "cylinder force per leg (motor reaction)",
            stats.cylinder_force_mean_N,
            cyl_ref,
            V1_LEG_FRACTION_OF_QUARTER_WEIGHT * quarter,
            "N",
            ref_key=key(L1_CYLINDER_FORCE_N),
            note="tol = 1 % W/4",
        ),
        check_rel(
            "V2",
            "pad penetration",
            stats.penetration_mean_mm,
            pen_ref,
            V2_REL_TOL,
            "mm",
            ref_key=key(L1_STATIC_PENETRATION_MM),
        ),
        check_abs(
            "V3",
            "attitude (roll, pitch)",
            [stats.roll_mean_deg, stats.pitch_mean_deg],
            att_ref,
            V3_ABS_TOL_DEG,
            "deg",
            ref_key=key(L1_STATIC_ATTITUDE_DEG),
        ),
    ]


def v13_checks(refs: References, stats: StillWindowStats) -> list[CheckResult]:
    """V13 / ``dynamics_model.md`` 4.5 item 1 on the still window."""
    quarter = float(refs.get(TOTAL_WEIGHT_INCL_RODS_N)) / 4.0
    return [
        check_max(
            "V13",
            "attitude drift in the still window (roll, pitch span)",
            [stats.roll_span_deg, stats.pitch_span_deg],
            V13_DRIFT_DEG,
            "deg",
        ),
        check_max(
            "V13",
            "contact force variation per leg (span)",
            stats.contact_force_span_N,
            V13_FORCE_FRACTION_OF_QUARTER_WEIGHT * quarter,
            "N",
            note="tol = 0.1 % W/4",
        ),
        check_equal("V13", "no NaN", stats.any_nan, False),
        check_max(
            "V13",
            "motor constraint violation (leg COG offset from its locked position)",
            stats.motor_violation_max_m,
            V13_MOTOR_VIOLATION_M,
            "m",
        ),
        check_equal(
            "V13",
            "one contact per leg (callback count min, max)",
            [stats.contacts_per_leg_min.tolist(), stats.contacts_per_leg_max.tolist()],
            [[1] * len(LEG_ORDER), [1] * len(LEG_ORDER)],
        ),
    ]
