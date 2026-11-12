# B1 K-R 대조 결과 (판정 후 감사, verif-protocol-auditor, 2026-11-12)

- 대응표 `b1_kr_map.md` d0f30e15 + 결정 `b1_kr_map_decisions.md` 1c00dc75. 허용: 이산 완전 일치, m·m/s·s 절대 1e-9, N 절대 1e-6, rad 절대 1e-12, r_sigma 절대 1e-12, 무차원·m/N 상대 1e-9.
- 입력 p1: `C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_metrics_path1.json` sha256 `6ad863abd3933e7f9353197bcd1af811188559722e76d69210dd80d47c336ee5`
- 입력 p2: `C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_metrics_path2.json` sha256 `5c3185c4930ec6f9f4a1a013a12266cb7680299071ead8120c623b9165949e35`
- 입력 harness: `C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\b1\b1_H.jsonl` sha256 `a7099db61b58198c9e9b7975b02c5641a8bbe04b695eec6ae9f0abcf174fc2f7`
- 입력 p1_constants: `C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_harness_constants_rev1.json` sha256 `3d35a1d81a7c4c4a2e4a40d9c2e3c498753dc0e674fe41491e57007ec52f5ffe`
- 입력 p2_constants: `C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_constants_path2_rev1_run.json` sha256 `3b5e775b3542f8f1efeb8033f894c4f765944358db73f389d3bb8996b454665c`
- 대조 스크립트는 두 경로 도구를 import하지 않고 두 출력 json·상수 파일·하네스 jsonl(줄 번호 → 실행 이름)만 읽었다.

## 요약

- 펼친 단위 2751개: both_NA 120, match 2629, mismatch 1, no_counterpart 1
- 항목 K-01~K-109: excluded 1, match 102, mismatch 1, no_counterpart 1, ref 4
- 불일치 항목: K-77

## 항목별 상태

| K | 상태 | 단위 수 |
|---|---|---|
| K-01 | match | match 6 |
| K-02 | match | match 1 |
| K-03 | match | match 1 |
| K-04 | match | match 6 |
| K-05 | match | match 6 |
| K-06 | match | match 6 |
| K-07 | match | both_NA 3, match 3 |
| K-08 | match | match 6 |
| K-09 | match | match 6 |
| K-10 | match | match 6 |
| K-11 | match | match 24 |
| K-12 | match | both_NA 12, match 12 |
| K-13 | match | match 24 |
| K-14 | match | match 6 |
| K-15 | match | match 6 |
| K-16 | match | both_NA 3, match 3 |
| K-17 | match | both_NA 3, match 3 |
| K-18 | match | match 6 |
| K-19 | match | match 6 |
| K-20 | match | match 24 |
| K-21 | match | match 24 |
| K-22 | match | both_NA 12, match 108 |
| K-23 | match | match 24 |
| K-24 | match | match 24 |
| K-25 | match | match 24 |
| K-26 | match | both_NA 12, match 12 |
| K-27 | match | both_NA 12, match 12 |
| K-28 | match | both_NA 12, match 12 |
| K-29 | match | both_NA 12, match 12 |
| K-30 | match | both_NA 12, match 12 |
| K-31 | match | match 6 |
| K-32 | match | match 30 |
| K-33 | match | match 30 |
| K-34 | match | match 30 |
| K-35 | match | match 6 |
| K-36 | match | match 6 |
| K-37 | match | match 6 |
| K-38 | match | match 6 |
| K-39 | match | match 12 |
| K-40 | match | match 6 |
| K-41 | match | match 24 |
| K-42 | match | match 24 |
| K-43 | match | match 24 |
| K-44 | match | match 72 |
| K-45 | match | match 6 |
| K-46 | match | match 6 |
| K-47 | match | match 6 |
| K-48 | match | match 6 |
| K-49 | match | match 6 |
| K-50 | match | match 6 |
| K-51 | match | match 6 |
| K-52 | match | match 12 |
| K-53 | match | match 120 |
| K-54 | match | match 108 |
| K-55 | match | match 108 |
| K-56 | match | match 81 |
| K-57 | match | match 81 |
| K-58 | match | match 81 |
| K-59 | match | match 162 |
| K-60 | match | match 81 |
| K-61 | match | both_NA 8, match 16 |
| K-62 | match | both_NA 4, match 1 |
| K-63 | match | match 1 |
| K-64 | match | both_NA 4, match 142 |
| K-65 | match | match 152 |
| K-66 | match | match 28 |
| K-67 | match | match 6 |
| K-68 | match | match 6 |
| K-69 | match | match 6 |
| K-70 | match | match 2 |
| K-71 | match | match 2 |
| K-72 | match | match 1 |
| K-73 | match | match 8 |
| K-74 | match | match 4 |
| K-75 | match | match 4 |
| K-76 | match | match 4 |
| K-77 | mismatch | both_NA 7, match 40, mismatch 1 |
| K-78 | match | match 1 |
| K-79 | match | match 421 |
| K-80 | match | match 90 |
| K-81 | match | match 5 |
| K-82 | match | match 5 |
| K-83 | match | match 3 |
| K-84 | ref:K-53 | - |
| K-85 | match | match 6 |
| K-86 | match | match 6 |
| K-87 | ref:K-01 | - |
| K-88 | ref:K-08 | - |
| K-89 | ref:K-69 | - |
| K-90 | match | match 3 |
| K-91 | match | match 3 |
| K-92 | match | match 1 |
| K-93 | excluded | - |
| K-94 | match | match 2 |
| K-95 | match | match 2 |
| K-96 | match | match 2 |
| K-97 | match | match 15 |
| K-98 | match | match 10 |
| K-99 | match | match 1 |
| K-100 | match | match 7 |
| K-101 | match | match 2 |
| K-102 | match | match 2 |
| K-103 | match | both_NA 1, match 11 |
| K-104 | match | match 1 |
| K-105 | match | match 1 |
| K-106 | match | both_NA 3, match 1 |
| K-107 | no_counterpart | no_counterpart 1 |
| K-108 | match | match 1 |
| K-109 | match | match 21 |

## 펼친 단위 전부

| K | 단위 | 허용 | 경로 1 | 경로 2 | 차 | 결과 | 비고 |
|---|---|---|---|---|---|---|---|
| K-01 | C1 status | exact | "VALID" | "VALID" |  | match |  |
| K-01 | C2 status | exact | "VALID" | "VALID" |  | match |  |
| K-01 | C3 status | exact | "VALID" | "VALID" |  | match |  |
| K-01 | C4 status | exact | "VALID" | "VALID" |  | match |  |
| K-01 | C5 status | exact | "VALID" | "VALID" |  | match |  |
| K-01 | C6 status | exact | "VALID" | "VALID" |  | match |  |
| K-02 | bundle (P1 COMPLETE + blocked []) | exact | "COMPLETE" | "COMPLETE" |  | match |  |
| K-03 | exit code (prelaunch 10.2/10.3 record) | exact | 0 | 0 |  | match | from prelaunch record (path 2 "종료 0", path 1 "종료 0"); not re-observed by auditor |
| K-04 | C1 n_L1 | exact | 461 | 461 |  | match |  |
| K-05 | C1 n_L | exact | 461 | 461 |  | match |  |
| K-06 | C1 loc_revokes | exact | 0 | 0 |  | match |  |
| K-07 | C1 n_R | exact | 1161 | 1161 |  | match |  |
| K-08 | C1 n_creep | exact | 1177 | 1177 |  | match |  |
| K-09 | C1 n_max | exact | 747 | 747 |  | match |  |
| K-10 | C1 n_end | exact | 1680 | 1680 |  | match |  |
| K-11 | C1 s_L FL | m | 0.599169170252744 | 0.599169170252744 | 0 | match |  |
| K-11 | C1 s_L FR | m | 0.598714626108668 | 0.598714626108668 | 0 | match |  |
| K-11 | C1 s_L RL | m | 0.367249717137888 | 0.367249717137888 | 0 | match |  |
| K-11 | C1 s_L RR | m | 0.366909836457215 | 0.366909836457215 | 0 | match |  |
| K-12 | C1 s_R FL | m | 0.660275718666261 | 0.660275718666261 | 0 | match |  |
| K-12 | C1 s_R FR | m | 0.648866182558014 | 0.648866182558014 | 0 | match |  |
| K-12 | C1 s_R RL | m | 0.459370422687565 | 0.459370422687565 | 0 | match |  |
| K-12 | C1 s_R RR | m | 0.44426956302479 | 0.44426956302479 | 0 | match |  |
| K-13 | C1 s_max FL | m | 0.680176489351771 | 0.680176489351771 | 0 | match |  |
| K-13 | C1 s_max FR | m | 0.674816440257135 | 0.674816440257135 | 0 | match |  |
| K-13 | C1 s_max RL | m | 0.461903329636694 | 0.461903329636694 | 0 | match |  |
| K-13 | C1 s_max RR | m | 0.446667128769851 | 0.446667128769851 | 0 | match |  |
| K-14 | C1 b* | exact | "FL" | "FL" |  | match |  |
| K-15 | C1 g | m | 0.00262351064822863 | 0.00262351064822863 | 0 | match |  |
| K-16 | C1 n_sgs | exact | null | null |  | both_NA |  |
| K-17 | C1 n_warn_lift | exact | null | null |  | both_NA |  |
| K-18 | C1 SGS | exact | false | false |  | match |  |
| K-19 | C1 n_e | exact | 1161 | 1161 |  | match |  |
| K-20 | C1 n_e_leg FL | exact | 1161 | 1161 |  | match |  |
| K-21 | C1 n_max_leg FL | exact | 747 | 747 |  | match |  |
| K-20 | C1 n_e_leg FR | exact | 1161 | 1161 |  | match |  |
| K-21 | C1 n_max_leg FR | exact | 909 | 909 |  | match |  |
| K-20 | C1 n_e_leg RL | exact | 1161 | 1161 |  | match |  |
| K-21 | C1 n_max_leg RL | exact | 1115 | 1115 |  | match |  |
| K-20 | C1 n_e_leg RR | exact | 1161 | 1161 |  | match |  |
| K-21 | C1 n_max_leg RR | exact | 1146 | 1146 |  | match |  |
| K-22 | C1 z(t_L) FL | m | 0.0867021628861416 | 0.0867021628861416 | 0 | match |  |
| K-22 | C1 z(t_L) FR | m | 0.0806699579406181 | 0.0806699579406181 | 0 | match |  |
| K-22 | C1 z(t_L) RL | m | 0.106274851963313 | 0.106274851963313 | 0 | match |  |
| K-22 | C1 z(t_L) RR | m | 0.100796738642827 | 0.100796738642827 | 0 | match |  |
| K-22 | C1 z(t_R) FL | m | 0.0986202887162046 | 0.0986202887162046 | 0 | match |  |
| K-22 | C1 z(t_R) FR | m | 0.089702748500458 | 0.089702748500458 | 0 | match |  |
| K-22 | C1 z(t_R) RL | m | 0.14389508053663 | 0.14389508053663 | 0 | match |  |
| K-22 | C1 z(t_R) RR | m | 0.131110847591515 | 0.131110847591515 | 0 | match |  |
| K-22 | C1 z(t_max) FL | m | 0.090215770648777 | 0.090215770648777 | 0 | match |  |
| K-22 | C1 z(t_max) FR | m | 0.080855498632575 | 0.080855498632575 | 0 | match |  |
| K-22 | C1 z(t_max) RL | m | 0.115916181013585 | 0.115916181013585 | 0 | match |  |
| K-22 | C1 z(t_max) RR | m | 0.105088401005114 | 0.105088401005114 | 0 | match |  |
| K-22 | C1 z(t_e) FL | m | 0.0986202887162046 | 0.0986202887162046 | 0 | match |  |
| K-22 | C1 z(t_e) FR | m | 0.089702748500458 | 0.089702748500458 | 0 | match |  |
| K-22 | C1 z(t_e) RL | m | 0.14389508053663 | 0.14389508053663 | 0 | match |  |
| K-22 | C1 z(t_e) RR | m | 0.131110847591515 | 0.131110847591515 | 0 | match |  |
| K-22 | C1 z(t_end) FL | m | 0.0986543665725676 | 0.0986543665725676 | 0 | match |  |
| K-22 | C1 z(t_end) FR | m | 0.0896762847826326 | 0.0896762847826326 | 0 | match |  |
| K-22 | C1 z(t_end) RL | m | 0.143829722772543 | 0.143829722772543 | 0 | match |  |
| K-22 | C1 z(t_end) RR | m | 0.131177501009239 | 0.131177501009239 | 0 | match |  |
| K-23 | C1 dz_post FL | m | 0.011918125830063 | 0.011918125830063 | 0 | match |  |
| K-23 | C1 dz_post FR | m | 0.00903279055983994 | 0.00903279055983994 | 0 | match |  |
| K-23 | C1 dz_post RL | m | 0.0376202285733178 | 0.0376202285733178 | 0 | match |  |
| K-23 | C1 dz_post RR | m | 0.0303141089486872 | 0.0303141089486872 | 0 | match |  |
| K-24 | C1 dz_post_leg_window FL | m | 0.011918125830063 | 0.011918125830063 | 0 | match |  |
| K-24 | C1 dz_post_leg_window FR | m | 0.00903279055983994 | 0.00903279055983994 | 0 | match |  |
| K-24 | C1 dz_post_leg_window RL | m | 0.0376202285733178 | 0.0376202285733178 | 0 | match |  |
| K-24 | C1 dz_post_leg_window RR | m | 0.0303141089486872 | 0.0303141089486872 | 0 | match |  |
| K-25 | C1 dz_L_to_max FL | m | 0.00351360776263546 | 0.00351360776263546 | 0 | match |  |
| K-25 | C1 dz_L_to_max FR | m | 0.000185540691956934 | 0.000185540691956934 | 0 | match |  |
| K-25 | C1 dz_L_to_max RL | m | 0.00964132905027283 | 0.00964132905027283 | 0 | match |  |
| K-25 | C1 dz_L_to_max RR | m | 0.00429166236228685 | 0.00429166236228685 | 0 | match |  |
| K-26 | C1 dz_max_to_R FL | m | 0.00840451806742751 | 0.00840451806742751 | 0 | match |  |
| K-26 | C1 dz_max_to_R FR | m | 0.008847249867883 | 0.008847249867883 | 0 | match |  |
| K-26 | C1 dz_max_to_R RL | m | 0.0279788995230449 | 0.0279788995230449 | 0 | match |  |
| K-26 | C1 dz_max_to_R RR | m | 0.0260224465864004 | 0.0260224465864004 | 0 | match |  |
| K-27 | C1 dz_L_to_R FL | m | 0.011918125830063 | 0.011918125830063 | 0 | match |  |
| K-27 | C1 dz_L_to_R FR | m | 0.00903279055983994 | 0.00903279055983994 | 0 | match |  |
| K-27 | C1 dz_L_to_R RL | m | 0.0376202285733178 | 0.0376202285733178 | 0 | match |  |
| K-27 | C1 dz_L_to_R RR | m | 0.0303141089486872 | 0.0303141089486872 | 0 | match |  |
| K-28 | C1 dz_R_to_end FL | m | 3.40778563630156e-05 | 3.40778563630156e-05 | 0 | match |  |
| K-28 | C1 dz_R_to_end FR | m | -2.64637178254284e-05 | -2.64637178254284e-05 | 0 | match |  |
| K-28 | C1 dz_R_to_end RL | m | -6.53577640871428e-05 | -6.53577640871428e-05 | 0 | match |  |
| K-28 | C1 dz_R_to_end RR | m | 6.66534177240774e-05 | 6.66534177240774e-05 | 0 | match |  |
| K-29 | C1 secant_L_to_R_m_per_N FL | rel | -2.23476737285239e-06 | -2.23476737285239e-06 | 0 | match |  |
| K-29 | C1 secant_L_to_R_m_per_N FR | rel | -2.19703064983289e-06 | -2.19703064983289e-06 | 0 | match |  |
| K-29 | C1 secant_L_to_R_m_per_N RL | rel | -1.10526825052323e-05 | -1.10526825052323e-05 | 0 | match |  |
| K-29 | C1 secant_L_to_R_m_per_N RR | rel | -3.2508999443032e-06 | -3.2508999443032e-06 | 0 | match |  |
| K-30 | C1 delta_os FL | m | 0.0199007706855101 | 0.0199007706855101 | 0 | match |  |
| K-30 | C1 delta_os FR | m | 0.0259502576991205 | 0.0259502576991205 | 0 | match |  |
| K-30 | C1 delta_os RL | m | 0.00253290694912855 | 0.00253290694912855 | 0 | match |  |
| K-30 | C1 delta_os RR | m | 0.00239756574506139 | 0.00239756574506139 | 0 | match |  |
| K-31 | C1 t_max - t_L | s | 28.6 | 28.6 | 0 | match |  |
| K-32 | C1 s_hat P-A @b*=FL | m | 0.674076653388193 | 0.674076653388193 | 0 | match |  |
| K-33 | C1 e P-A @b*=FL | m | 0.00609983596357788 | 0.00609983596357788 | 0 | match |  |
| K-34 | C1 e P-A @b=FL | m | 0.00609983596357788 | 0.00609983596357788 | 0 | match |  |
| K-32 | C1 s_hat P-B @b*=FL | m | 0.674076653388193 | 0.674076653388193 | 0 | match |  |
| K-33 | C1 e P-B @b*=FL | m | 0.00609983596357788 | 0.00609983596357788 | 0 | match |  |
| K-34 | C1 e P-B @b=FL | m | 0.00609983596357788 | 0.00609983596357788 | 0 | match |  |
| K-32 | C1 s_hat P-D @b*=FL | m | 0.674076653388193 | 0.674076653388193 | 0 | match |  |
| K-33 | C1 e P-D @b*=FL | m | 0.00609983596357788 | 0.00609983596357788 | 0 | match |  |
| K-34 | C1 e P-D @b=FL | m | 0.00609983596357788 | 0.00609983596357788 | 0 | match |  |
| K-32 | C1 s_hat P-G @b*=FL | m | 0.673187473623878 | 0.673187473623878 | 0 | match |  |
| K-33 | C1 e P-G @b*=FL | m | 0.00698901572789368 | 0.00698901572789368 | 0 | match |  |
| K-34 | C1 e P-G @b=FL | m | 0.00698901572789368 | 0.00698901572789368 | 0 | match |  |
| K-32 | C1 s_hat P-C @b*=FL | m | 0.693931441244684 | 0.693931441244684 | 0 | match |  |
| K-33 | C1 e P-C @b*=FL | m | -0.0137549518929131 | -0.0137549518929131 | 0 | match |  |
| K-34 | C1 e P-C @b=FL | m | -0.0137549518929131 | -0.0137549518929131 | 0 | match |  |
| K-35 | C1 lower bound (M-6) vs sgs | exact | false | false |  | match |  |
| K-36 | C1 P-G k* | exact | "RR" | "RR" |  | match |  |
| K-37 | C1 rho_k* | m | -0.0020585754600866 | -0.0020585754600866 | 0 | match |  |
| K-38 | C1 Zhat_k* | m | 0.00240706675242037 | 0.00240706675242037 | 4.34e-19 | match |  |
| K-39 | C1 phi_L | rad | -0.00211917880897767 | -0.00211917880897767 | 0 | match |  |
| K-39 | C1 theta_L | rad | -0.000454468909226573 | -0.000454468909226573 | 0 | match |  |
| K-40 | C1 c_hat(t_L) | m | 0.00685542498789116 | 0.00685542498789116 | 0 | match |  |
| K-41 | C1 c_hat_corner RR | m | 0.00739611345987323 | 0.00739611345987323 | 0 | match |  |
| K-43 | C1 rho RR | m | -0.0020585754600866 | -0.0020585754600866 | 0 | match |  |
| K-41 | C1 c_hat_corner RL | m | 0.00685542498789116 | 0.00685542498789116 | 0 | match |  |
| K-43 | C1 rho RL | m | 0.00373102104604039 | 0.00373102104604039 | 0 | match |  |
| K-41 | C1 c_hat_corner FR | m | 0.196767594688152 | 0.196767594688152 | 0 | match |  |
| K-43 | C1 rho FR | m | -0.00373283892167729 | -0.00373283892167729 | 0 | match |  |
| K-41 | C1 c_hat_corner FL | m | 0.19622690621617 | 0.19622690621617 | 0 | match |  |
| K-43 | C1 rho FL | m | 0.00205675758444969 | 0.00205675758444969 | 0 | match |  |
| K-42 | C1 ds_geo FL | m | 0.00176290812334072 | 0.00176290812334072 | 0 | match |  |
| K-44 | C1 W_hat FL | N | -1005.1225682776 | -1005.12256827758 | 1.46e-11 | match |  |
| K-44 | C1 E_hat FL | N | 122344.006678553 | 122344.006678554 | 1.46e-11 | match |  |
| K-44 | C1 F_pk FL | N | 123472.436758881 | 123472.436758881 | 0 | match |  |
| K-42 | C1 ds_geo FR | m | -0.00384782969130855 | -0.00384782969130855 | 0 | match |  |
| K-44 | C1 W_hat FR | N | -327.555702303929 | -327.555702303915 | 1.46e-11 | match |  |
| K-44 | C1 E_hat FR | N | 120279.267491625 | 120279.267491625 | 1.46e-11 | match |  |
| K-44 | C1 F_pk FR | N | 122626.474577129 | 122626.474577129 | 0 | match |  |
| K-42 | C1 ds_geo RL | m | 0.00363661146298814 | 0.00363661146298814 | 0 | match |  |
| K-44 | C1 W_hat RL | N | 1114.86390045717 | 1114.86390045717 | 0 | match |  |
| K-44 | C1 E_hat RL | N | 74688.0941465391 | 74688.0941465391 | 0 | match |  |
| K-44 | C1 F_pk RL | N | 74158.9409265569 | 74158.9409265569 | 0 | match |  |
| K-42 | C1 ds_geo RR | m | -0.00147230480969522 | -0.00147230480969522 | 0 | match |  |
| K-44 | C1 W_hat RR | N | 217.814370124353 | 217.814370124353 | 0 | match |  |
| K-44 | C1 E_hat RR | N | 72807.9911872387 | 72807.9911872387 | 0 | match |  |
| K-44 | C1 F_pk RR | N | 73277.7929091394 | 73277.7929091394 | 0 | match |  |
| K-45 | C1 sum F / sum W_static | rel | 1.03594359888055 | 1.03594359888055 | 2.22e-16 | match |  |
| K-46 | C1 E3c10 events | exact | ["INFO_LOC_CLEARANCE_MARGIN:80"] | ["INFO_LOC_CLEARANCE_MARGIN:80"] |  | match |  |
| K-47 | C1 R4c30 count | exact | 0 | 0 |  | match |  |
| K-48 | C1 M-8 loc_revoked | exact | 0 | 0 |  | match |  |
| K-49 | C1 M-8 sgs>0 | exact | false | false |  | match |  |
| K-50 | C1 pair diff s_max(b*) | m | -0.00223453464348833 | -0.00223453464348833 | 0 | match |  |
| K-51 | C1 pair diff dz_post(b*) | m | 0.010729652565087 | 0.010729652565087 | 0 | match |  |
| K-52 | C1 harness s_max spread min (n=4) | m | 0.681976916808451 | 0.681976916808451 | 0 | match |  |
| K-52 | C1 harness s_max spread max (n=4) | m | 0.682421072345616 | 0.682421072345616 | 0 | match |  |
| K-53 | C1 L FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 L FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C1 L FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C1 L FL b_hull | m | 0.169263127822496 | 0.169263127822496 | 0 | match |  |
| K-57 | C1 L FL r_sigma | rsig | 0.000767679668737207 | 0.000767679668737207 | 0 | match |  |
| K-58 | C1 L FL f | rel | 1.01550499873236 | 1.01550499873236 | 0 | match |  |
| K-59 | C1 L FL z/f | m | 0.0853783713466408 | 0.0853783713466408 | 0 | match |  |
| K-59 | C1 L FL delta_grid | m | 0.00132379153950084 | 0.00132379153950084 | 0 | match |  |
| K-60 | C1 L FL dz_1n | m | 0.000404772002269569 | 0.000404772002269569 | 1.08e-19 | match |  |
| K-53 | C1 L FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 L FR N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C1 L FR N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-56 | C1 L FR b_hull | m | 0.171237086820195 | 0.171237086820195 | 0 | match |  |
| K-57 | C1 L FR r_sigma | rsig | 0.0031821964935199 | 0.00318219649351992 | 2.56e-17 | match |  |
| K-58 | C1 L FR f | rel | 1.00913625894508 | 1.00913625894508 | 6.66e-16 | match |  |
| K-59 | C1 L FR z/f | m | 0.0799396089730717 | 0.0799396089730717 | 5.55e-17 | match |  |
| K-59 | C1 L FR delta_grid | m | 0.00073034896754638 | 0.000730348967546326 | 5.38e-17 | match |  |
| K-60 | C1 L FR dz_1n | m | 0.000376610447902045 | 0.000376610447902045 | 0 | match |  |
| K-53 | C1 L RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 L RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C1 L RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C1 L RL b_hull | m | 0.128783963641942 | 0.128783963641942 | 0 | match |  |
| K-57 | C1 L RL r_sigma | rsig | 0.00153483738940328 | 0.00153483738940328 | 0 | match |  |
| K-58 | C1 L RL f | rel | 0.987116946578811 | 0.987116946578811 | 0 | match |  |
| K-59 | C1 L RL z/f | m | 0.107661865528339 | 0.107661865528339 | 0 | match |  |
| K-59 | C1 L RL delta_grid | m | -0.00138701356502642 | -0.00138701356502642 | 0 | match |  |
| K-60 | C1 L RL dz_1n | m | 0.000875410642201916 | 0.000875410642201916 | 0 | match |  |
| K-53 | C1 L RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 L RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C1 L RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C1 L RR b_hull | m | 0.128790966737605 | 0.128790966737605 | 0 | match |  |
| K-57 | C1 L RR r_sigma | rsig | 0.00080379467135659 | 0.00080379467135659 | 0 | match |  |
| K-58 | C1 L RR f | rel | 0.995293531275907 | 0.995293531275907 | 0 | match |  |
| K-59 | C1 L RR z/f | m | 0.101273378631942 | 0.101273378631942 | 0 | match |  |
| K-59 | C1 L RR delta_grid | m | -0.000476639989114439 | -0.000476639989114439 | 0 | match |  |
| K-60 | C1 L RR dz_1n | m | 0.000830286150270406 | 0.000830286150270406 | 0 | match |  |
| K-53 | C1 R FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C1 R FL N_h | exact | 1068 | 1068 |  | match |  |
| K-55 | C1 R FL N_h D2/A | rel | 0.997198879551821 | 0.997198879551821 | 0 | match |  |
| K-53 | C1 R FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 R FR N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C1 R FR N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C1 R FR b_hull | m | 0.171306718907584 | 0.171306718907584 | 0 | match |  |
| K-57 | C1 R FR r_sigma | rsig | 0.000518400109665735 | 0.000518400109665735 | 0 | match |  |
| K-58 | C1 R FR f | rel | 1.02352588473931 | 1.02352588473931 | 0 | match |  |
| K-59 | C1 R FR z/f | m | 0.0876409183567498 | 0.0876409183567498 | 0 | match |  |
| K-59 | C1 R FR delta_grid | m | 0.0020618301437082 | 0.0020618301437082 | 0 | match |  |
| K-60 | C1 R FR dz_1n | m | 0.000418780338470859 | 0.000418780338470859 | 0 | match |  |
| K-53 | C1 R RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 R RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C1 R RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C1 R RL b_hull | m | 0.128708901537396 | 0.128708901537396 | 0 | match |  |
| K-57 | C1 R RL r_sigma | rsig | 0.00319276690239008 | 0.00319276690239008 | 0 | match |  |
| K-58 | C1 R RL f | rel | 0.995075024762734 | 0.995075024762734 | 0 | match |  |
| K-59 | C1 R RL z/f | m | 0.144607267749425 | 0.144607267749425 | 0 | match |  |
| K-59 | C1 R RL delta_grid | m | -0.000712187212794572 | -0.000712187212794572 | 0 | match |  |
| K-60 | C1 R RL dz_1n | m | 0.00118529720376137 | 0.00118529720376137 | 0 | match |  |
| K-53 | C1 R RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C1 R RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C1 R RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-53 | C1 max FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 max FL N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C1 max FL N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C1 max FL b_hull | m | 0.169187542284191 | 0.169187542284191 | 0 | match |  |
| K-57 | C1 max FL r_sigma | rsig | 0.00160861453576824 | 0.00160861453576824 | 0 | match |  |
| K-58 | C1 max FL f | rel | 1.02015567418494 | 1.02015567418494 | 0 | match |  |
| K-59 | C1 max FL z/f | m | 0.0884333371187253 | 0.0884333371187253 | 0 | match |  |
| K-59 | C1 max FL delta_grid | m | 0.00178243353005175 | 0.00178243353005175 | 0 | match |  |
| K-60 | C1 max FL dz_1n | m | 0.000421175399854235 | 0.000421175399854235 | 0 | match |  |
| K-53 | C1 max FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 max FR N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C1 max FR N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C1 max FR b_hull | m | 0.171306718907584 | 0.171306718907584 | 0 | match |  |
| K-57 | C1 max FR r_sigma | rsig | 0.000905617155823483 | 0.000905617155823483 | 0 | match |  |
| K-58 | C1 max FR f | rel | 1.02352588473931 | 1.02352588473931 | 0 | match |  |
| K-59 | C1 max FR z/f | m | 0.0789970237569211 | 0.0789970237569211 | 0 | match |  |
| K-59 | C1 max FR delta_grid | m | 0.00185847487565388 | 0.00185847487565388 | 0 | match |  |
| K-60 | C1 max FR dz_1n | m | 0.000377476650945728 | 0.000377476650945728 | 0 | match |  |
| K-53 | C1 max RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 max RL N_h | exact | 606 | 606 |  | match |  |
| K-55 | C1 max RL N_h D2/A | rel | 0.99835255354201 | 0.99835255354201 | 1.11e-16 | match |  |
| K-56 | C1 max RL b_hull | m | 0.12859835077688 | 0.12859835077688 | 0 | match |  |
| K-57 | C1 max RL r_sigma | rsig | 0.00110626248683558 | 0.00110626248683554 | 4.01e-17 | match |  |
| K-58 | C1 max RL f | rel | 1.00301521451522 | 1.00301521451522 | 1.11e-15 | match |  |
| K-59 | C1 max RL z/f | m | 0.115567719548113 | 0.115567719548113 | 1.25e-16 | match |  |
| K-59 | C1 max RL delta_grid | m | 0.000348461465472225 | 0.000348461465472341 | 1.16e-16 | match |  |
| K-60 | C1 max RL dz_1n | m | 0.000954828509172862 | 0.000954828509172862 | 0 | match |  |
| K-53 | C1 max RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 max RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C1 max RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C1 max RR b_hull | m | 0.12884208585609 | 0.12884208585609 | 0 | match |  |
| K-57 | C1 max RR r_sigma | rsig | 0.000832923161755787 | 0.000832923161755787 | 0 | match |  |
| K-58 | C1 max RR f | rel | 0.995429529225932 | 0.995429529225932 | 0 | match |  |
| K-59 | C1 max RR z/f | m | 0.105570909762777 | 0.105570909762777 | 0 | match |  |
| K-59 | C1 max RR delta_grid | m | -0.000482508757662544 | -0.000482508757662544 | 0 | match |  |
| K-60 | C1 max RR dz_1n | m | 0.000865637570058601 | 0.000865637570058601 | 0 | match |  |
| K-53 | C1 e FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C1 e FL N_h | exact | 1068 | 1068 |  | match |  |
| K-55 | C1 e FL N_h D2/A | rel | 0.997198879551821 | 0.997198879551821 | 0 | match |  |
| K-53 | C1 e FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 e FR N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C1 e FR N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C1 e FR b_hull | m | 0.171306718907584 | 0.171306718907584 | 0 | match |  |
| K-57 | C1 e FR r_sigma | rsig | 0.000518400109665735 | 0.000518400109665735 | 0 | match |  |
| K-58 | C1 e FR f | rel | 1.02352588473931 | 1.02352588473931 | 0 | match |  |
| K-59 | C1 e FR z/f | m | 0.0876409183567498 | 0.0876409183567498 | 0 | match |  |
| K-59 | C1 e FR delta_grid | m | 0.0020618301437082 | 0.0020618301437082 | 0 | match |  |
| K-60 | C1 e FR dz_1n | m | 0.000418780338470859 | 0.000418780338470859 | 0 | match |  |
| K-53 | C1 e RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 e RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C1 e RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C1 e RL b_hull | m | 0.128708901537396 | 0.128708901537396 | 0 | match |  |
| K-57 | C1 e RL r_sigma | rsig | 0.00319276690239008 | 0.00319276690239008 | 0 | match |  |
| K-58 | C1 e RL f | rel | 0.995075024762734 | 0.995075024762734 | 0 | match |  |
| K-59 | C1 e RL z/f | m | 0.144607267749425 | 0.144607267749425 | 0 | match |  |
| K-59 | C1 e RL delta_grid | m | -0.000712187212794572 | -0.000712187212794572 | 0 | match |  |
| K-60 | C1 e RL dz_1n | m | 0.00118529720376137 | 0.00118529720376137 | 0 | match |  |
| K-53 | C1 e RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C1 e RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C1 e RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-53 | C1 end FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C1 end FL N_h | exact | 1068 | 1068 |  | match |  |
| K-55 | C1 end FL N_h D2/A | rel | 0.997198879551821 | 0.997198879551821 | 0 | match |  |
| K-53 | C1 end FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C1 end FR N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C1 end FR N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C1 end FR b_hull | m | 0.171306718907584 | 0.171306718907584 | 0 | match |  |
| K-57 | C1 end FR r_sigma | rsig | 0.00190599361424363 | 0.00190599361424363 | 0 | match |  |
| K-58 | C1 end FR f | rel | 1.02352588473931 | 1.02352588473931 | 0 | match |  |
| K-59 | C1 end FR z/f | m | 0.0876150629111573 | 0.0876150629111573 | 0 | match |  |
| K-59 | C1 end FR delta_grid | m | 0.00206122187147531 | 0.00206122187147531 | 0 | match |  |
| K-60 | C1 end FR dz_1n | m | 0.0004186567917023 | 0.0004186567917023 | 0 | match |  |
| K-53 | C1 end RL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C1 end RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C1 end RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-53 | C1 end RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C1 end RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C1 end RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-61 | C1 dz_post_corr FL | m | null | null |  | both_NA |  |
| K-61 | C1 dz_post_corr FR | m | 0.00770130938367812 | 0.00770130938367806 | 5.55e-17 | match |  |
| K-61 | C1 dz_post_corr RL | m | 0.0369454022210859 | 0.0369454022210859 | 0 | match |  |
| K-61 | C1 dz_post_corr RR | m | null | null |  | both_NA |  |
| K-62 | C1 z_e(f_e-f_L) @b*=FL | m | null | null |  | both_NA |  P2 key absent |
| K-67 | C1 m_L | m | 0.03 | 0.03 | 0 | match |  |
| K-68 | C1 m_L source | exact | "E3c10" | "E3c10" |  | match |  |
| K-69 | C1 T-14 (checked True ok True) | exact | true | true |  | match | both None counted as both_NA |
| K-80 | C1 R1-4 n_L | exact | 461 | 461 |  | match |  |
| K-80 | C1 R1-4 sum ratio | rel | 1.03594359888055 | 1.03594359888055 | 2.22e-16 | match |  |
| K-80 | C1 R1-4 W_hat FL | N | -1005.1225682776 | -1005.12256827758 | 1.46e-11 | match |  |
| K-80 | C1 R1-4 E-Fpk FL | N | -1128.4300803276 | -1128.43008032758 | 1.46e-11 | match |  |
| K-80 | C1 R1-4 stroke rate FL | m/s | 0.0133112609335773 | 0.0133112609335773 | 0 | match |  |
| K-80 | C1 R1-4 W_hat FR | N | -327.555702303929 | -327.555702303915 | 1.46e-11 | match |  |
| K-80 | C1 R1-4 E-Fpk FR | N | -2347.20708550393 | -2347.20708550392 | 1.46e-11 | match |  |
| K-80 | C1 R1-4 stroke rate FR | m/s | 0.0153627322762784 | 0.0153627322762784 | 0 | match |  |
| K-80 | C1 R1-4 W_hat RL | N | 1114.86390045717 | 1114.86390045717 | 0 | match |  |
| K-80 | C1 R1-4 E-Fpk RL | N | 529.153219982181 | 529.153219982181 | 0 | match |  |
| K-80 | C1 R1-4 stroke rate RL | m/s | 0.0061849077913001 | 0.0061849077913001 | 0 | match |  |
| K-80 | C1 R1-4 W_hat RR | N | 217.814370124353 | 217.814370124353 | 0 | match |  |
| K-80 | C1 R1-4 E-Fpk RR | N | -469.801721900643 | -469.801721900643 | 0 | match |  |
| K-80 | C1 R1-4 stroke rate RR | m/s | 0.00560066754210053 | 0.00560066754210053 | 0 | match |  |
| K-80 | C1 R1-4 flag | exact | false | false |  | match |  |
| K-85 | C1 T-8 leg liftoff set | exact | [] | [] |  | match |  |
| K-86 | C1 T-9 crawler retouch | exact | false | false |  | match |  |
| K-04 | C2 n_L1 | exact | 465 | 465 |  | match |  |
| K-05 | C2 n_L | exact | 465 | 465 |  | match |  |
| K-06 | C2 loc_revokes | exact | 0 | 0 |  | match |  |
| K-07 | C2 n_R | exact | 1357 | 1357 |  | match |  |
| K-08 | C2 n_creep | exact | 1370 | 1370 |  | match |  |
| K-09 | C2 n_max | exact | 733 | 733 |  | match |  |
| K-10 | C2 n_end | exact | 1680 | 1680 |  | match |  |
| K-11 | C2 s_L FL | m | 0.5839164993666 | 0.5839164993666 | 0 | match |  |
| K-11 | C2 s_L FR | m | 0.583642566942439 | 0.583642566942439 | 0 | match |  |
| K-11 | C2 s_L RL | m | 0.365186406589641 | 0.365186406589641 | 0 | match |  |
| K-11 | C2 s_L RR | m | 0.364939423722986 | 0.364939423722986 | 0 | match |  |
| K-12 | C2 s_R FL | m | 0.657546349421083 | 0.657546349421083 | 0 | match |  |
| K-12 | C2 s_R FR | m | 0.647454118393547 | 0.647454118393547 | 0 | match |  |
| K-12 | C2 s_R RL | m | 0.448925621740996 | 0.448925621740996 | 0 | match |  |
| K-12 | C2 s_R RR | m | 0.439566479774129 | 0.439566479774129 | 0 | match |  |
| K-13 | C2 s_max FL | m | 0.678929226571688 | 0.678929226571688 | 0 | match |  |
| K-13 | C2 s_max FR | m | 0.670740409208579 | 0.670740409208579 | 0 | match |  |
| K-13 | C2 s_max RL | m | 0.456401446147001 | 0.456401446147001 | 0 | match |  |
| K-13 | C2 s_max RR | m | 0.443139745289437 | 0.443139745289437 | 0 | match |  |
| K-14 | C2 b* | exact | "FL" | "FL" |  | match |  |
| K-15 | C2 g | m | 0.00387077342831199 | 0.00387077342831199 | 0 | match |  |
| K-16 | C2 n_sgs | exact | null | null |  | both_NA |  |
| K-17 | C2 n_warn_lift | exact | null | null |  | both_NA |  |
| K-18 | C2 SGS | exact | false | false |  | match |  |
| K-19 | C2 n_e | exact | 1357 | 1357 |  | match |  |
| K-20 | C2 n_e_leg FL | exact | 1357 | 1357 |  | match |  |
| K-21 | C2 n_max_leg FL | exact | 733 | 733 |  | match |  |
| K-20 | C2 n_e_leg FR | exact | 1357 | 1357 |  | match |  |
| K-21 | C2 n_max_leg FR | exact | 882 | 882 |  | match |  |
| K-20 | C2 n_e_leg RL | exact | 1357 | 1357 |  | match |  |
| K-21 | C2 n_max_leg RL | exact | 1071 | 1071 |  | match |  |
| K-20 | C2 n_e_leg RR | exact | 1357 | 1357 |  | match |  |
| K-21 | C2 n_max_leg RR | exact | 1099 | 1099 |  | match |  |
| K-22 | C2 z(t_L) FL | m | 0.0855768901311082 | 0.0855768901311082 | 0 | match |  |
| K-22 | C2 z(t_L) FR | m | 0.082608199064193 | 0.082608199064193 | 0 | match |  |
| K-22 | C2 z(t_L) RL | m | 0.0975211138506324 | 0.0975211138506324 | 0 | match |  |
| K-22 | C2 z(t_L) RR | m | 0.0947917927697547 | 0.0947917927697547 | 0 | match |  |
| K-22 | C2 z(t_R) FL | m | 0.0989138699007713 | 0.0989138699007713 | 0 | match |  |
| K-22 | C2 z(t_R) FR | m | 0.0894412425778445 | 0.0894412425778445 | 0 | match |  |
| K-22 | C2 z(t_R) RL | m | 0.138405542403889 | 0.138405542403889 | 0 | match |  |
| K-22 | C2 z(t_R) RR | m | 0.129486419075154 | 0.129486419075154 | 0 | match |  |
| K-22 | C2 z(t_max) FL | m | 0.0920250730516688 | 0.0920250730516688 | 0 | match |  |
| K-22 | C2 z(t_max) FR | m | 0.082694804784604 | 0.082694804784604 | 0 | match |  |
| K-22 | C2 z(t_max) RL | m | 0.113032445186186 | 0.113032445186186 | 0 | match |  |
| K-22 | C2 z(t_max) RR | m | 0.104854139265836 | 0.104854139265836 | 0 | match |  |
| K-22 | C2 z(t_e) FL | m | 0.0989138699007713 | 0.0989138699007713 | 0 | match |  |
| K-22 | C2 z(t_e) FR | m | 0.0894412425778445 | 0.0894412425778445 | 0 | match |  |
| K-22 | C2 z(t_e) RL | m | 0.138405542403889 | 0.138405542403889 | 0 | match |  |
| K-22 | C2 z(t_e) RR | m | 0.129486419075154 | 0.129486419075154 | 0 | match |  |
| K-22 | C2 z(t_end) FL | m | 0.098947633300121 | 0.098947633300121 | 0 | match |  |
| K-22 | C2 z(t_end) FR | m | 0.0893943451710338 | 0.0893943451710338 | 0 | match |  |
| K-22 | C2 z(t_end) RL | m | 0.138367574329769 | 0.138367574329769 | 0 | match |  |
| K-22 | C2 z(t_end) RR | m | 0.129567800017443 | 0.129567800017443 | 0 | match |  |
| K-23 | C2 dz_post FL | m | 0.0133369797696631 | 0.0133369797696631 | 0 | match |  |
| K-23 | C2 dz_post FR | m | 0.00683304351365153 | 0.00683304351365153 | 0 | match |  |
| K-23 | C2 dz_post RL | m | 0.0408844285532568 | 0.0408844285532568 | 0 | match |  |
| K-23 | C2 dz_post RR | m | 0.0346946263053994 | 0.0346946263053994 | 0 | match |  |
| K-24 | C2 dz_post_leg_window FL | m | 0.0133369797696631 | 0.0133369797696631 | 0 | match |  |
| K-24 | C2 dz_post_leg_window FR | m | 0.00683304351365153 | 0.00683304351365153 | 0 | match |  |
| K-24 | C2 dz_post_leg_window RL | m | 0.0408844285532568 | 0.0408844285532568 | 0 | match |  |
| K-24 | C2 dz_post_leg_window RR | m | 0.0346946263053994 | 0.0346946263053994 | 0 | match |  |
| K-25 | C2 dz_L_to_max FL | m | 0.00644818292056061 | 0.00644818292056061 | 0 | match |  |
| K-25 | C2 dz_L_to_max FR | m | 8.66057204110676e-05 | 8.66057204110676e-05 | 0 | match |  |
| K-25 | C2 dz_L_to_max RL | m | 0.0155113313355537 | 0.0155113313355537 | 0 | match |  |
| K-25 | C2 dz_L_to_max RR | m | 0.0100623464960811 | 0.0100623464960811 | 0 | match |  |
| K-26 | C2 dz_max_to_R FL | m | 0.00688879684910251 | 0.00688879684910251 | 0 | match |  |
| K-26 | C2 dz_max_to_R FR | m | 0.00674643779324047 | 0.00674643779324047 | 0 | match |  |
| K-26 | C2 dz_max_to_R RL | m | 0.0253730972177031 | 0.0253730972177031 | 0 | match |  |
| K-26 | C2 dz_max_to_R RR | m | 0.0246322798093183 | 0.0246322798093183 | 0 | match |  |
| K-27 | C2 dz_L_to_R FL | m | 0.0133369797696631 | 0.0133369797696631 | 0 | match |  |
| K-27 | C2 dz_L_to_R FR | m | 0.00683304351365153 | 0.00683304351365153 | 0 | match |  |
| K-27 | C2 dz_L_to_R RL | m | 0.0408844285532568 | 0.0408844285532568 | 0 | match |  |
| K-27 | C2 dz_L_to_R RR | m | 0.0346946263053994 | 0.0346946263053994 | 0 | match |  |
| K-28 | C2 dz_R_to_end FL | m | 3.37633993497122e-05 | 3.37633993497122e-05 | 0 | match |  |
| K-28 | C2 dz_R_to_end FR | m | -4.68974068106726e-05 | -4.68974068106726e-05 | 0 | match |  |
| K-28 | C2 dz_R_to_end RL | m | -3.79680741204036e-05 | -3.79680741204036e-05 | 0 | match |  |
| K-28 | C2 dz_R_to_end RR | m | 8.13809422892664e-05 | 8.13809422892664e-05 | 0 | match |  |
| K-29 | C2 secant_L_to_R_m_per_N FL | rel | -3.74488259671958e-06 | -3.74488259671958e-06 | 0 | match |  |
| K-29 | C2 secant_L_to_R_m_per_N FR | rel | -1.36274444750323e-06 | -1.36274444750323e-06 | 0 | match |  |
| K-29 | C2 secant_L_to_R_m_per_N RL | rel | -1.56053874993511e-05 | -1.56053874993511e-05 | 0 | match |  |
| K-29 | C2 secant_L_to_R_m_per_N RR | rel | -3.59844984052137e-06 | -3.59844984052137e-06 | 0 | match |  |
| K-30 | C2 delta_os FL | m | 0.0213828771506045 | 0.0213828771506045 | 0 | match |  |
| K-30 | C2 delta_os FR | m | 0.0232862908150318 | 0.0232862908150318 | 0 | match |  |
| K-30 | C2 delta_os RL | m | 0.00747582440600469 | 0.00747582440600469 | 0 | match |  |
| K-30 | C2 delta_os RR | m | 0.00357326551530746 | 0.00357326551530746 | 0 | match |  |
| K-31 | C2 t_max - t_L | s | 26.8 | 26.8 | 0 | match |  |
| K-32 | C2 s_hat P-A @b*=FL | m | 0.668479114254833 | 0.668479114254833 | 0 | match |  |
| K-33 | C2 e P-A @b*=FL | m | 0.0104501123168554 | 0.0104501123168554 | 0 | match |  |
| K-34 | C2 e P-A @b=FL | m | 0.0104501123168554 | 0.0104501123168554 | 0 | match |  |
| K-32 | C2 s_hat P-B @b*=FL | m | 0.668667918045638 | 0.668667918045638 | 0 | match |  |
| K-33 | C2 e P-B @b*=FL | m | 0.0102613085260497 | 0.0102613085260497 | 0 | match |  |
| K-34 | C2 e P-B @b=FL | m | 0.0102613085260497 | 0.0102613085260497 | 0 | match |  |
| K-32 | C2 s_hat P-D @b*=FL | m | 0.668479114254833 | 0.668479114254833 | 0 | match |  |
| K-33 | C2 e P-D @b*=FL | m | 0.0104501123168554 | 0.0104501123168554 | 0 | match |  |
| K-34 | C2 e P-D @b=FL | m | 0.0104501123168554 | 0.0104501123168554 | 0 | match |  |
| K-32 | C2 s_hat P-G @b*=FL | m | 0.667601174042092 | 0.667601174042092 | 1.11e-16 | match |  |
| K-33 | C2 e P-G @b*=FL | m | 0.0113280525295959 | 0.011328052529596 | 1.11e-16 | match |  |
| K-34 | C2 e P-G @b=FL | m | 0.0113280525295959 | 0.011328052529596 | 1.11e-16 | match |  |
| K-32 | C2 s_hat P-C @b*=FL | m | 0.688522705902129 | 0.688522705902129 | 0 | match |  |
| K-33 | C2 e P-C @b*=FL | m | -0.0095934793304413 | -0.0095934793304413 | 0 | match |  |
| K-34 | C2 e P-C @b=FL | m | -0.0095934793304413 | -0.0095934793304413 | 0 | match |  |
| K-35 | C2 lower bound (M-6) vs sgs | exact | false | false |  | match |  |
| K-36 | C2 P-G k* | exact | "RR" | "RR" |  | match |  |
| K-37 | C2 rho_k* | m | -0.00859086198408168 | -0.00859086198408168 | 0 | match |  |
| K-38 | C2 Zhat_k* | m | 0.00806045126818403 | 0.0080604512681841 | 7.11e-17 | match |  |
| K-39 | C2 phi_L | rad | -0.000870553020069628 | -0.000870553020069628 | 0 | match |  |
| K-39 | C2 theta_L | rad | 0.00402265573840574 | 0.00402265573840574 | 0 | match |  |
| K-40 | C2 c_hat(t_L) | m | 0.005816990932491 | 0.005816990932491 | 0 | match |  |
| K-41 | C2 c_hat_corner RR | m | 0.00722534186112916 | 0.00722534186112916 | 0 | match |  |
| K-43 | C2 rho RR | m | -0.00859086198408168 | -0.00859086198408168 | 0 | match |  |
| K-41 | C2 c_hat_corner RL | m | 0.005816990932491 | 0.005816990932491 | 0 | match |  |
| K-43 | C2 rho RL | m | -0.00621251113325146 | -0.00621251113325146 | 0 | match |  |
| K-41 | C2 c_hat_corner FR | m | 0.184266833865649 | 0.184266833865649 | 0 | match |  |
| K-43 | C2 rho FR | m | 0.00622860175620508 | 0.00622860175620508 | 0 | match |  |
| K-41 | C2 c_hat_corner FL | m | 0.182858482937011 | 0.182858482937011 | 0 | match |  |
| K-43 | C2 rho FL | m | 0.0086069526070353 | 0.0086069526070353 | 0 | match |  |
| K-42 | C2 ds_geo FL | m | 0.0103796058207233 | 0.0103796058207233 | 0 | match |  |
| K-44 | C2 W_hat FL | N | 228.328435478237 | 228.328435478252 | 1.46e-11 | match |  |
| K-44 | C2 E_hat FL | N | 122022.762013459 | 122022.762013459 | 1.46e-11 | match |  |
| K-44 | C2 F_pk FL | N | 122847.259819381 | 122847.259819381 | 0 | match |  |
| K-42 | C2 ds_geo FR | m | 0.00807472964478692 | 0.00807472964478692 | 0 | match |  |
| K-44 | C2 W_hat FR | N | -1799.87767919188 | -1799.87767919186 | 1.46e-11 | match |  |
| K-44 | C2 E_hat FR | N | 119963.444313587 | 119963.444313587 | 1.46e-11 | match |  |
| K-44 | C2 F_pk FR | N | 123049.215140379 | 123049.215140379 | 0 | match |  |
| K-42 | C2 ds_geo RL | m | -0.00926518919522576 | -0.00926518919522576 | 0 | match |  |
| K-44 | C2 W_hat RL | N | 1211.70521969914 | 1211.70521969916 | 1.46e-11 | match |  |
| K-44 | C2 E_hat RL | N | 74491.981950756 | 74491.9819507561 | 1.46e-11 | match |  |
| K-44 | C2 F_pk RL | N | 73280.2767310569 | 73280.2767310569 | 0 | match |  |
| K-42 | C2 ds_geo RR | m | -0.0113639184160096 | -0.0113639184160096 | 0 | match |  |
| K-44 | C2 W_hat RR | N | 359.844024014499 | 359.844024014499 | 0 | match |  |
| K-44 | C2 E_hat RR | N | 72616.8156701039 | 72616.8156701039 | 0 | match |  |
| K-44 | C2 F_pk RR | N | 72446.0562538144 | 72446.0562538144 | 0 | match |  |
| K-45 | C2 sum F / sum W_static | rel | 1.03322347091095 | 1.03322347091095 | 2.22e-16 | match |  |
| K-46 | C2 E3c10 events | exact | ["INFO_LOC_CLEARANCE_MARGIN:80"] | ["INFO_LOC_CLEARANCE_MARGIN:80"] |  | match |  |
| K-47 | C2 R4c30 count | exact | 0 | 0 |  | match |  |
| K-48 | C2 M-8 loc_revoked | exact | 0 | 0 |  | match |  |
| K-49 | C2 M-8 sgs>0 | exact | false | false |  | match |  |
| K-50 | C2 pair diff s_max(b*) | m | 0.0094596807955678 | 0.0094596807955678 | 0 | match |  |
| K-51 | C2 pair diff dz_post(b*) | m | 0.00780615068166983 | 0.00780615068166983 | 0 | match |  |
| K-52 | C2 harness s_max spread min (n=4) | m | 0.66946954577612 | 0.66946954577612 | 0 | match |  |
| K-52 | C2 harness s_max spread max (n=4) | m | 0.682608512224058 | 0.682608512224058 | 0 | match |  |
| K-53 | C2 L FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 L FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 L FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C2 L FL b_hull | m | 0.170553305013154 | 0.170553305013154 | 0 | match |  |
| K-57 | C2 L FL r_sigma | rsig | 0.000621737114813706 | 0.000621737114813706 | 0 | match |  |
| K-58 | C2 L FL f | rel | 1.017554042214 | 1.017554042214 | 0 | match |  |
| K-59 | C2 L FL z/f | m | 0.084100584913318 | 0.084100584913318 | 0 | match |  |
| K-59 | C2 L FL delta_grid | m | 0.00147630521779019 | 0.00147630521779019 | 0 | match |  |
| K-60 | C2 L FL dz_1n | m | 0.000399518628063063 | 0.000399518628063063 | 0 | match |  |
| K-53 | C2 L FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 L FR N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C2 L FR N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C2 L FR b_hull | m | 0.171329427131543 | 0.171329427131543 | 0 | match |  |
| K-57 | C2 L FR r_sigma | rsig | 0.00181742302201894 | 0.00181742302201894 | 0 | match |  |
| K-58 | C2 L FR f | rel | 1.02356161842427 | 1.02356161842427 | 0 | match |  |
| K-59 | C2 L FR z/f | m | 0.0807066204684044 | 0.0807066204684044 | 0 | match |  |
| K-59 | C2 L FR delta_grid | m | 0.00190157859578853 | 0.00190157859578853 | 0 | match |  |
| K-60 | C2 L FR dz_1n | m | 0.000385659192643291 | 0.000385659192643291 | 0 | match |  |
| K-53 | C2 L RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 L RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C2 L RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C2 L RL b_hull | m | 0.126946215763021 | 0.126946215763021 | 0 | match |  |
| K-57 | C2 L RL r_sigma | rsig | 0.00234317951127771 | 0.00234317951127771 | 0 | match |  |
| K-58 | C2 L RL f | rel | 0.982210368530664 | 0.982210368530664 | 0 | match |  |
| K-59 | C2 L RL z/f | m | 0.099287400108104 | 0.099287400108104 | 0 | match |  |
| K-59 | C2 L RL delta_grid | m | -0.00176628625747164 | -0.00176628625747164 | 0 | match |  |
| K-60 | C2 L RL dz_1n | m | 0.000803304067962376 | 0.000803304067962376 | 0 | match |  |
| K-53 | C2 L RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 L RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C2 L RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C2 L RR b_hull | m | 0.128897526805776 | 0.128897526805776 | 0 | match |  |
| K-57 | C2 L RR r_sigma | rsig | 0.00181857963348841 | 0.00181857963348841 | 0 | match |  |
| K-58 | C2 L RR f | rel | 0.98741650568807 | 0.98741650568807 | 0 | match |  |
| K-59 | C2 L RR z/f | m | 0.0959998057797303 | 0.0959998057797303 | 0 | match |  |
| K-59 | C2 L RR delta_grid | m | -0.0012080130099756 | -0.0012080130099756 | 0 | match |  |
| K-60 | C2 L RR dz_1n | m | 0.000780822016225327 | 0.000780822016225327 | 0 | match |  |
| K-53 | C2 R FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C2 R FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 R FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-53 | C2 R FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 R FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 R FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C2 R FR b_hull | m | 0.171406659931775 | 0.171406659931775 | 0 | match |  |
| K-57 | C2 R FR r_sigma | rsig | 3.15593698548366e-05 | 3.15593698548366e-05 | 0 | match |  |
| K-58 | C2 R FR f | rel | 1.01889506011373 | 1.01889506011373 | 0 | match |  |
| K-59 | C2 R FR z/f | m | 0.0877825853507046 | 0.0877825853507046 | 0 | match |  |
| K-59 | C2 R FR delta_grid | m | 0.00165865722713995 | 0.00165865722713995 | 0 | match |  |
| K-60 | C2 R FR dz_1n | m | 0.000417559489158938 | 0.000417559489158938 | 0 | match |  |
| K-53 | C2 R RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 R RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C2 R RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C2 R RL b_hull | m | 0.126871391412716 | 0.126871391412716 | 0 | match |  |
| K-57 | C2 R RL r_sigma | rsig | 0.00126577660426362 | 0.00126577660426362 | 0 | match |  |
| K-58 | C2 R RL f | rel | 0.990123941224759 | 0.990123941224759 | 0 | match |  |
| K-59 | C2 R RL z/f | m | 0.139786077925441 | 0.139786077925441 | 0 | match |  |
| K-59 | C2 R RL delta_grid | m | -0.00138053552155203 | -0.00138053552155203 | 0 | match |  |
| K-60 | C2 R RL dz_1n | m | 0.00114007860299744 | 0.00114007860299744 | 2.17e-19 | match |  |
| K-53 | C2 R RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C2 R RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C2 R RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-53 | C2 max FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 max FL N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C2 max FL N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-56 | C2 max FL b_hull | m | 0.171323995921224 | 0.171323995921224 | 0 | match |  |
| K-57 | C2 max FL r_sigma | rsig | 0.00365859962337149 | 0.00365859962337149 | 0 | match |  |
| K-58 | C2 max FL f | rel | 1.00927116071224 | 1.00927116071224 | 0 | match |  |
| K-59 | C2 max FL z/f | m | 0.091179731110841 | 0.091179731110841 | 0 | match |  |
| K-59 | C2 max FL delta_grid | m | 0.000845341940827776 | 0.000845341940827776 | 0 | match |  |
| K-60 | C2 max FL dz_1n | m | 0.000429622189783701 | 0.000429622189783701 | 0 | match |  |
| K-53 | C2 max FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 max FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 max FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C2 max FR b_hull | m | 0.171406659931775 | 0.171406659931775 | 0 | match |  |
| K-57 | C2 max FR r_sigma | rsig | 0.000977312065553155 | 0.000977312065553155 | 0 | match |  |
| K-58 | C2 max FR f | rel | 1.01889506011373 | 1.01889506011373 | 0 | match |  |
| K-59 | C2 max FR z/f | m | 0.0811612579369791 | 0.0811612579369791 | 0 | match |  |
| K-59 | C2 max FR delta_grid | m | 0.00153354684762494 | 0.00153354684762494 | 0 | match |  |
| K-60 | C2 max FR dz_1n | m | 0.000386063514400579 | 0.000386063514400579 | 0 | match |  |
| K-53 | C2 max RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 max RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C2 max RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C2 max RL b_hull | m | 0.126838360469514 | 0.126838360469514 | 0 | match |  |
| K-57 | C2 max RL r_sigma | rsig | 0.00159800444757624 | 0.00159800444757624 | 0 | match |  |
| K-58 | C2 max RL f | rel | 0.990033903281609 | 0.990033903281609 | 0 | match |  |
| K-59 | C2 max RL z/f | m | 0.114170277211239 | 0.114170277211239 | 0 | match |  |
| K-59 | C2 max RL delta_grid | m | -0.00113783202505271 | -0.00113783202505271 | 0 | match |  |
| K-60 | C2 max RL dz_1n | m | 0.000931074507299721 | 0.000931074507299721 | 0 | match |  |
| K-53 | C2 max RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 max RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C2 max RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C2 max RR b_hull | m | 0.12884208585609 | 0.12884208585609 | 0 | match |  |
| K-57 | C2 max RR r_sigma | rsig | 0.000936543711125041 | 0.000936543711125041 | 0 | match |  |
| K-58 | C2 max RR f | rel | 0.995429529225932 | 0.995429529225932 | 0 | match |  |
| K-59 | C2 max RR z/f | m | 0.105335572421056 | 0.105335572421056 | 0 | match |  |
| K-59 | C2 max RR delta_grid | m | -0.000481433155220162 | -0.000481433155220162 | 0 | match |  |
| K-60 | C2 max RR dz_1n | m | 0.000863707901695517 | 0.000863707901695517 | 1.08e-19 | match |  |
| K-53 | C2 e FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C2 e FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 e FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-53 | C2 e FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 e FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 e FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C2 e FR b_hull | m | 0.171406659931775 | 0.171406659931775 | 0 | match |  |
| K-57 | C2 e FR r_sigma | rsig | 3.15593698548366e-05 | 3.15593698548366e-05 | 0 | match |  |
| K-58 | C2 e FR f | rel | 1.01889506011373 | 1.01889506011373 | 0 | match |  |
| K-59 | C2 e FR z/f | m | 0.0877825853507046 | 0.0877825853507046 | 0 | match |  |
| K-59 | C2 e FR delta_grid | m | 0.00165865722713995 | 0.00165865722713995 | 0 | match |  |
| K-60 | C2 e FR dz_1n | m | 0.000417559489158938 | 0.000417559489158938 | 0 | match |  |
| K-53 | C2 e RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 e RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C2 e RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C2 e RL b_hull | m | 0.126871391412716 | 0.126871391412716 | 0 | match |  |
| K-57 | C2 e RL r_sigma | rsig | 0.00126577660426362 | 0.00126577660426362 | 0 | match |  |
| K-58 | C2 e RL f | rel | 0.990123941224759 | 0.990123941224759 | 0 | match |  |
| K-59 | C2 e RL z/f | m | 0.139786077925441 | 0.139786077925441 | 0 | match |  |
| K-59 | C2 e RL delta_grid | m | -0.00138053552155203 | -0.00138053552155203 | 0 | match |  |
| K-60 | C2 e RL dz_1n | m | 0.00114007860299744 | 0.00114007860299744 | 2.17e-19 | match |  |
| K-53 | C2 e RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C2 e RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C2 e RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-53 | C2 end FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C2 end FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 end FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-53 | C2 end FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 end FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C2 end FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C2 end FR b_hull | m | 0.171406659931775 | 0.171406659931775 | 0 | match |  |
| K-57 | C2 end FR r_sigma | rsig | 0.00174227294874648 | 0.00174227294874648 | 0 | match |  |
| K-58 | C2 end FR f | rel | 1.01889506011373 | 1.01889506011373 | 0 | match |  |
| K-59 | C2 end FR z/f | m | 0.0877365576402498 | 0.0877365576402498 | 0 | match |  |
| K-59 | C2 end FR delta_grid | m | 0.00165778753078401 | 0.00165778753078401 | 0 | match |  |
| K-60 | C2 end FR dz_1n | m | 0.000417340547016965 | 0.000417340547016965 | 0 | match |  |
| K-53 | C2 end RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C2 end RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C2 end RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C2 end RL b_hull | m | 0.126871391412716 | 0.126871391412716 | 0 | match |  |
| K-57 | C2 end RL r_sigma | rsig | 0.00298234467836275 | 0.00298234467836275 | 0 | match |  |
| K-58 | C2 end RL f | rel | 0.990123941224759 | 0.990123941224759 | 0 | match |  |
| K-59 | C2 end RL z/f | m | 0.139747731136176 | 0.139747731136176 | 0 | match |  |
| K-59 | C2 end RL delta_grid | m | -0.00138015680640741 | -0.00138015680640741 | 0 | match |  |
| K-60 | C2 end RL dz_1n | m | 0.00113976585115131 | 0.00113976585115131 | 0 | match |  |
| K-53 | C2 end RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C2 end RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C2 end RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-61 | C2 dz_post_corr FL | m | null | null |  | both_NA |  |
| K-61 | C2 dz_post_corr FR | m | 0.00707596488230011 | 0.00707596488230011 | 0 | match |  |
| K-61 | C2 dz_post_corr RL | m | 0.0404986778173372 | 0.0404986778173372 | 0 | match |  |
| K-61 | C2 dz_post_corr RR | m | null | null |  | both_NA |  |
| K-62 | C2 z_e(f_e-f_L) @b*=FL | m | null | null |  | both_NA |  P2 key absent |
| K-67 | C2 m_L | m | 0.03 | 0.03 | 0 | match |  |
| K-68 | C2 m_L source | exact | "E3c10" | "E3c10" |  | match |  |
| K-69 | C2 T-14 (checked True ok True) | exact | true | true |  | match | both None counted as both_NA |
| K-80 | C2 R1-4 n_L | exact | 465 | 465 |  | match |  |
| K-80 | C2 R1-4 sum ratio | rel | 1.03322347091095 | 1.03322347091095 | 2.22e-16 | match |  |
| K-80 | C2 R1-4 W_hat FL | N | 228.328435478237 | 228.328435478252 | 1.46e-11 | match |  |
| K-80 | C2 R1-4 E-Fpk FL | N | -824.497805921739 | -824.497805921725 | 1.46e-11 | match |  |
| K-80 | C2 R1-4 stroke rate FL | m/s | 0.018361749837984 | 0.018361749837984 | 0 | match |  |
| K-80 | C2 R1-4 W_hat FR | N | -1799.87767919188 | -1799.87767919186 | 1.46e-11 | match |  |
| K-80 | C2 R1-4 E-Fpk FR | N | -3085.77082679188 | -3085.77082679186 | 1.46e-11 | match |  |
| K-80 | C2 R1-4 stroke rate FR | m/s | 0.0212535512181011 | 0.0212535512181011 | 0 | match |  |
| K-80 | C2 R1-4 W_hat RL | N | 1211.70521969914 | 1211.70521969916 | 1.46e-11 | match |  |
| K-80 | C2 R1-4 E-Fpk RL | N | 1211.70521969914 | 1211.70521969916 | 1.46e-11 | match |  |
| K-80 | C2 R1-4 stroke rate RL | m/s | 0.00418061475762066 | 0.00418061475762066 | 0 | match |  |
| K-80 | C2 R1-4 W_hat RR | N | 359.844024014499 | 359.844024014499 | 0 | match |  |
| K-80 | C2 R1-4 E-Fpk RR | N | 170.759416289511 | 170.759416289511 | 0 | match |  |
| K-80 | C2 R1-4 stroke rate RR | m/s | 0.00437105024421014 | 0.00437105024421014 | 0 | match |  |
| K-80 | C2 R1-4 flag | exact | false | false |  | match |  |
| K-85 | C2 T-8 leg liftoff set | exact | [] | [] |  | match |  |
| K-86 | C2 T-9 crawler retouch | exact | false | false |  | match |  |
| K-04 | C3 n_L1 | exact | 460 | 460 |  | match |  |
| K-05 | C3 n_L | exact | 460 | 460 |  | match |  |
| K-06 | C3 loc_revokes | exact | 0 | 0 |  | match |  |
| K-07 | C3 n_R | exact | 1162 | 1162 |  | match |  |
| K-08 | C3 n_creep | exact | 1500 | 1500 |  | match |  |
| K-09 | C3 n_max | exact | 610 | 610 |  | match |  |
| K-10 | C3 n_end | exact | 1680 | 1680 |  | match |  |
| K-11 | C3 s_L FL | m | 0.573207051061131 | 0.573207051061131 | 0 | match |  |
| K-11 | C3 s_L FR | m | 0.57276747503214 | 0.57276747503214 | 0 | match |  |
| K-11 | C3 s_L RL | m | 0.369872339239985 | 0.369872339239985 | 0 | match |  |
| K-11 | C3 s_L RR | m | 0.369688762461184 | 0.369688762461184 | 0 | match |  |
| K-12 | C3 s_R FL | m | 0.660278224761247 | 0.660278224761247 | 0 | match |  |
| K-12 | C3 s_R FR | m | 0.648076103154572 | 0.648076103154572 | 0 | match |  |
| K-12 | C3 s_R RL | m | 0.455145004687116 | 0.455145004687116 | 0 | match |  |
| K-12 | C3 s_R RR | m | 0.445615380077543 | 0.445615380077543 | 0 | match |  |
| K-13 | C3 s_max FL | m | 0.683475434468135 | 0.683475434468135 | 0 | match |  |
| K-13 | C3 s_max FR | m | 0.675954955979387 | 0.675954955979387 | 0 | match |  |
| K-13 | C3 s_max RL | m | 0.457688599550895 | 0.457688599550895 | 0 | match |  |
| K-13 | C3 s_max RR | m | 0.448035984543783 | 0.448035984543783 | 0 | match |  |
| K-14 | C3 b* | exact | "FL" | "FL" |  | match |  |
| K-15 | C3 g | m | -0.000675434468135339 | -0.000675434468135339 | 0 | match |  |
| K-16 | C3 n_sgs | exact | null | null |  | both_NA |  |
| K-17 | C3 n_warn_lift | exact | null | null |  | both_NA |  |
| K-18 | C3 SGS | exact | false | false |  | match |  |
| K-19 | C3 n_e | exact | 1162 | 1162 |  | match |  |
| K-20 | C3 n_e_leg FL | exact | 1162 | 1162 |  | match |  |
| K-21 | C3 n_max_leg FL | exact | 610 | 610 |  | match |  |
| K-20 | C3 n_e_leg FR | exact | 1162 | 1162 |  | match |  |
| K-21 | C3 n_max_leg FR | exact | 642 | 642 |  | match |  |
| K-20 | C3 n_e_leg RL | exact | 1162 | 1162 |  | match |  |
| K-21 | C3 n_max_leg RL | exact | 1115 | 1115 |  | match |  |
| K-20 | C3 n_e_leg RR | exact | 1162 | 1162 |  | match |  |
| K-21 | C3 n_max_leg RR | exact | 1146 | 1146 |  | match |  |
| K-22 | C3 z(t_L) FL | m | 0.0906610120395832 | 0.0906610120395832 | 0 | match |  |
| K-22 | C3 z(t_L) FR | m | 0.0876858734657192 | 0.0876858734657192 | 0 | match |  |
| K-22 | C3 z(t_L) RL | m | 0.0938368654949788 | 0.0938368654949788 | 0 | match |  |
| K-22 | C3 z(t_L) RR | m | 0.0910745325007193 | 0.0910745325007193 | 0 | match |  |
| K-22 | C3 z(t_R) FL | m | 0.100543794369471 | 0.100543794369471 | 0 | match |  |
| K-22 | C3 z(t_R) FR | m | 0.0915020395134391 | 0.0915020395134391 | 0 | match |  |
| K-22 | C3 z(t_R) RL | m | 0.141606655148413 | 0.141606655148413 | 0 | match |  |
| K-22 | C3 z(t_R) RR | m | 0.135232326865384 | 0.135232326865384 | 0 | match |  |
| K-22 | C3 z(t_max) FL | m | 0.0944278533692304 | 0.0944278533692304 | 0 | match |  |
| K-22 | C3 z(t_max) FR | m | 0.0878200782583052 | 0.0878200782583052 | 0 | match |  |
| K-22 | C3 z(t_max) RL | m | 0.111011250883068 | 0.111011250883068 | 0 | match |  |
| K-22 | C3 z(t_max) RR | m | 0.106831979853007 | 0.106831979853007 | 0 | match |  |
| K-22 | C3 z(t_e) FL | m | 0.100543794369471 | 0.100543794369471 | 0 | match |  |
| K-22 | C3 z(t_e) FR | m | 0.0915020395134391 | 0.0915020395134391 | 0 | match |  |
| K-22 | C3 z(t_e) RL | m | 0.141606655148413 | 0.141606655148413 | 0 | match |  |
| K-22 | C3 z(t_e) RR | m | 0.135232326865384 | 0.135232326865384 | 0 | match |  |
| K-22 | C3 z(t_end) FL | m | 0.101643511436799 | 0.101643511436799 | 0 | match |  |
| K-22 | C3 z(t_end) FR | m | 0.0926916514709925 | 0.0926916514709925 | 0 | match |  |
| K-22 | C3 z(t_end) RL | m | 0.142667547130426 | 0.142667547130426 | 0 | match |  |
| K-22 | C3 z(t_end) RR | m | 0.137022477375732 | 0.137022477375732 | 0 | match |  |
| K-23 | C3 dz_post FL | m | 0.00988278232988825 | 0.00988278232988825 | 0 | match |  |
| K-23 | C3 dz_post FR | m | 0.00381616604771992 | 0.00381616604771992 | 0 | match |  |
| K-23 | C3 dz_post RL | m | 0.0477697896534337 | 0.0477697896534337 | 0 | match |  |
| K-23 | C3 dz_post RR | m | 0.0441577943646642 | 0.0441577943646642 | 0 | match |  |
| K-24 | C3 dz_post_leg_window FL | m | 0.00988278232988825 | 0.00988278232988825 | 0 | match |  |
| K-24 | C3 dz_post_leg_window FR | m | 0.00381616604771992 | 0.00381616604771992 | 0 | match |  |
| K-24 | C3 dz_post_leg_window RL | m | 0.0477697896534337 | 0.0477697896534337 | 0 | match |  |
| K-24 | C3 dz_post_leg_window RR | m | 0.0441577943646642 | 0.0441577943646642 | 0 | match |  |
| K-25 | C3 dz_L_to_max FL | m | 0.00376684132964714 | 0.00376684132964714 | 0 | match |  |
| K-25 | C3 dz_L_to_max FR | m | 0.000134204792586065 | 0.000134204792586065 | 0 | match |  |
| K-25 | C3 dz_L_to_max RL | m | 0.0171743853880891 | 0.0171743853880891 | 0 | match |  |
| K-25 | C3 dz_L_to_max RR | m | 0.0157574473522882 | 0.0157574473522882 | 0 | match |  |
| K-26 | C3 dz_max_to_R FL | m | 0.00611594100024111 | 0.00611594100024111 | 0 | match |  |
| K-26 | C3 dz_max_to_R FR | m | 0.00368196125513386 | 0.00368196125513386 | 0 | match |  |
| K-26 | C3 dz_max_to_R RL | m | 0.0305954042653446 | 0.0305954042653446 | 0 | match |  |
| K-26 | C3 dz_max_to_R RR | m | 0.0284003470123761 | 0.0284003470123761 | 0 | match |  |
| K-27 | C3 dz_L_to_R FL | m | 0.00988278232988825 | 0.00988278232988825 | 0 | match |  |
| K-27 | C3 dz_L_to_R FR | m | 0.00381616604771992 | 0.00381616604771992 | 0 | match |  |
| K-27 | C3 dz_L_to_R RL | m | 0.0477697896534337 | 0.0477697896534337 | 0 | match |  |
| K-27 | C3 dz_L_to_R RR | m | 0.0441577943646642 | 0.0441577943646642 | 0 | match |  |
| K-28 | C3 dz_R_to_end FL | m | 0.00109971706732764 | 0.00109971706732764 | 0 | match |  |
| K-28 | C3 dz_R_to_end FR | m | 0.00118961195755346 | 0.00118961195755346 | 0 | match |  |
| K-28 | C3 dz_R_to_end RL | m | 0.00106089198201365 | 0.00106089198201365 | 0 | match |  |
| K-28 | C3 dz_R_to_end RR | m | 0.00179015051034878 | 0.00179015051034878 | 0 | match |  |
| K-29 | C3 secant_L_to_R_m_per_N FL | rel | -1.68975046856838e-06 | -1.68975046856838e-06 | 0 | match |  |
| K-29 | C3 secant_L_to_R_m_per_N FR | rel | -8.86902171158217e-07 | -8.86902171158217e-07 | 0 | match |  |
| K-29 | C3 secant_L_to_R_m_per_N RL | rel | -1.51186640247071e-05 | -1.51186640247071e-05 | 0 | match |  |
| K-29 | C3 secant_L_to_R_m_per_N RR | rel | -5.61897362198217e-06 | -5.61897362198217e-06 | 0 | match |  |
| K-30 | C3 delta_os FL | m | 0.0231972097068885 | 0.0231972097068885 | 0 | match |  |
| K-30 | C3 delta_os FR | m | 0.0278788528248144 | 0.0278788528248144 | 0 | match |  |
| K-30 | C3 delta_os RL | m | 0.00254359486377909 | 0.00254359486377909 | 0 | match |  |
| K-30 | C3 delta_os RR | m | 0.00242060446624026 | 0.00242060446624026 | 0 | match |  |
| K-31 | C3 t_max - t_L | s | 15 | 15 | 0 | match |  |
| K-32 | C3 s_hat P-A @b*=FL | m | 0.669814131035993 | 0.669814131035993 | 0 | match |  |
| K-33 | C3 e P-A @b*=FL | m | 0.0136613034321427 | 0.0136613034321427 | 0 | match |  |
| K-34 | C3 e P-A @b=FL | m | 0.0136613034321427 | 0.0136613034321427 | 0 | match |  |
| K-32 | C3 s_hat P-B @b*=FL | m | 0.669814131035993 | 0.669814131035993 | 0 | match |  |
| K-33 | C3 e P-B @b*=FL | m | 0.0136613034321427 | 0.0136613034321427 | 0 | match |  |
| K-34 | C3 e P-B @b=FL | m | 0.0136613034321427 | 0.0136613034321427 | 0 | match |  |
| K-32 | C3 s_hat P-D @b*=FL | m | 0.669814131035993 | 0.669814131035993 | 0 | match |  |
| K-33 | C3 e P-D @b*=FL | m | 0.0136613034321427 | 0.0136613034321427 | 0 | match |  |
| K-34 | C3 e P-D @b=FL | m | 0.0136613034321427 | 0.0136613034321427 | 0 | match |  |
| K-32 | C3 s_hat P-G @b*=FL | m | 0.66883145387714 | 0.66883145387714 | 3.33e-16 | match |  |
| K-33 | C3 e P-G @b*=FL | m | 0.0146439805909954 | 0.0146439805909957 | 3.33e-16 | match |  |
| K-34 | C3 e P-G @b=FL | m | 0.0146439805909954 | 0.0146439805909957 | 3.33e-16 | match |  |
| K-32 | C3 s_hat P-C @b*=FL | m | 0.689668918892484 | 0.689668918892484 | 0 | match |  |
| K-33 | C3 e P-C @b*=FL | m | -0.00619348442434831 | -0.00619348442434831 | 0 | match |  |
| K-34 | C3 e P-C @b=FL | m | -0.00619348442434831 | -0.00619348442434831 | 0 | match |  |
| K-35 | C3 lower bound (M-6) vs sgs | exact | false | false |  | match |  |
| K-36 | C3 P-G k* | exact | "RR" | "RR" |  | match |  |
| K-37 | C3 rho_k* | m | -0.0178214970097941 | -0.0178214970097941 | 0 | match |  |
| K-38 | C3 Zhat_k* | m | 0.0177148780330551 | 0.0177148780330555 | 3.92e-16 | match |  |
| K-39 | C3 phi_L | rad | -0.000904628643568507 | -0.000904628643568507 | 0 | match |  |
| K-39 | C3 theta_L | rad | 0.00901400776232581 | 0.00901400776232581 | 0 | match |  |
| K-40 | C3 c_hat(t_L) | m | 0.00526679842871691 | 0.00526679842871691 | 0 | match |  |
| K-41 | C3 c_hat_corner RR | m | 0.00635609456430855 | 0.00635609456430855 | 0 | match |  |
| K-43 | C3 rho RR | m | -0.0178214970097941 | -0.0178214970097941 | 0 | match |  |
| K-41 | C3 c_hat_corner RL | m | 0.00526679842871691 | 0.00526679842871691 | 0 | match |  |
| K-43 | C3 rho RL | m | -0.0153500515555649 | -0.0153500515555649 | 0 | match |  |
| K-41 | C3 c_hat_corner FR | m | 0.170569083858471 | 0.170569083858471 | 0 | match |  |
| K-43 | C3 rho FR | m | 0.0153861075866142 | 0.0153861075866142 | 0 | match |  |
| K-41 | C3 c_hat_corner FL | m | 0.169479787722879 | 0.169479787722879 | 0 | match |  |
| K-43 | C3 rho FL | m | 0.0178575530408434 | 0.0178575530408434 | 0 | match |  |
| K-42 | C3 ds_geo FL | m | 0.0218738784035789 | 0.0218738784035789 | 0 | match |  |
| K-44 | C3 W_hat FL | N | -1554.97371470313 | -1554.97371470308 | 4.37e-11 | match |  |
| K-44 | C3 E_hat FL | N | 122514.758349178 | 122514.758349178 | 4.37e-11 | match |  |
| K-44 | C3 F_pk FL | N | 124069.732063881 | 124069.732063881 | 0 | match |  |
| K-42 | C3 ds_geo FR | m | 0.019478783606867 | 0.019478783606867 | 0 | match |  |
| K-44 | C3 W_hat FR | N | -1639.76856697784 | -1639.7685669778 | 4.37e-11 | match |  |
| K-44 | C3 E_hat FR | N | 120447.137470901 | 120447.137470901 | 4.37e-11 | match |  |
| K-44 | C3 F_pk FR | N | 124195.896461929 | 124195.896461929 | 0 | match |  |
| K-42 | C3 ds_geo RL | m | -0.0219832880476811 | -0.0219832880476811 | 0 | match |  |
| K-44 | C3 W_hat RL | N | 1916.34093715189 | 1916.34093715192 | 2.91e-11 | match |  |
| K-44 | C3 E_hat RL | N | 74792.3339634088 | 74792.3339634088 | 2.91e-11 | match |  |
| K-44 | C3 F_pk RL | N | 72875.9930262569 | 72875.9930262569 | 0 | match |  |
| K-42 | C3 ds_geo RR | m | -0.0241641667815961 | -0.0241641667815961 | 0 | match |  |
| K-44 | C3 W_hat RR | N | 1278.401344529 | 1278.40134452902 | 1.46e-11 | match |  |
| K-44 | C3 E_hat RR | N | 72909.6070037184 | 72909.6070037184 | 1.46e-11 | match |  |
| K-44 | C3 F_pk RR | N | 72327.4611311394 | 72327.4611311394 | 0 | match |  |
| K-45 | C3 sum F / sum W_static | rel | 1.03738943268135 | 1.03738943268135 | 2.22e-16 | match |  |
| K-46 | C3 E3c10 events | exact | ["INFO_LOC_CLEARANCE_MARGIN:80"] | ["INFO_LOC_CLEARANCE_MARGIN:80"] |  | match |  |
| K-47 | C3 R4c30 count | exact | 0 | 0 |  | match |  |
| K-48 | C3 M-8 loc_revoked | exact | 0 | 0 |  | match |  |
| K-49 | C3 M-8 sgs>0 | exact | false | false |  | match |  |
| K-50 | C3 pair diff s_max(b*) | m | 0.0123214508243965 | 0.0123214508243965 | 0 | match |  |
| K-51 | C3 pair diff dz_post(b*) | m | 0.00418236346466831 | 0.00418236346466831 | 0 | match |  |
| K-52 | C3 harness s_max spread min (n=4) | m | 0.670828667054484 | 0.670828667054484 | 0 | match |  |
| K-52 | C3 harness s_max spread max (n=4) | m | 0.67159766853138 | 0.67159766853138 | 0 | match |  |
| K-53 | C3 L FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 L FL N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C3 L FL N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C3 L FL b_hull | m | 0.171699317262445 | 0.171699317262445 | 0 | match |  |
| K-57 | C3 L FL r_sigma | rsig | 0.000506851116588573 | 0.000506851116588573 | 0 | match |  |
| K-58 | C3 L FL f | rel | 1.02414255692996 | 1.02414255692996 | 0 | match |  |
| K-59 | C3 L FL z/f | m | 0.0885238206596503 | 0.0885238206596503 | 0 | match |  |
| K-59 | C3 L FL delta_grid | m | 0.0021371913799329 | 0.0021371913799329 | 0 | match |  |
| K-60 | C3 L FL dz_1n | m | 0.000423254024461173 | 0.000423254024461173 | 0 | match |  |
| K-53 | C3 L FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 L FR N_h | exact | 1065 | 1065 |  | match |  |
| K-55 | C3 L FR N_h D2/A | rel | 0.994397759103642 | 0.994397759103642 | 0 | match |  |
| K-56 | C3 L FR b_hull | m | 0.171244954639421 | 0.171244954639421 | 0 | match |  |
| K-57 | C3 L FR r_sigma | rsig | 0.00284129874154502 | 0.00284129874154502 | 0 | match |  |
| K-58 | C3 L FR f | rel | 1.02824251304083 | 1.02824251304083 | 0 | match |  |
| K-59 | C3 L FR z/f | m | 0.0852774246869109 | 0.0852774246869109 | 0 | match |  |
| K-59 | C3 L FR delta_grid | m | 0.00240844877880821 | 0.00240844877880821 | 0 | match |  |
| K-60 | C3 L FR dz_1n | m | 0.000409364488635477 | 0.000409364488635477 | 5.42e-20 | match |  |
| K-53 | C3 L RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 L RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C3 L RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C3 L RL b_hull | m | 0.128783963641942 | 0.128783963641942 | 0 | match |  |
| K-57 | C3 L RL r_sigma | rsig | 0.00238216029970298 | 0.00238216029970298 | 0 | match |  |
| K-58 | C3 L RL f | rel | 0.987116946578811 | 0.987116946578811 | 0 | match |  |
| K-59 | C3 L RL z/f | m | 0.0950615485026392 | 0.0950615485026392 | 0 | match |  |
| K-59 | C3 L RL delta_grid | m | -0.00122468300766041 | -0.00122468300766041 | 0 | match |  |
| K-60 | C3 L RL dz_1n | m | 0.000772956058442989 | 0.000772956058442989 | 0 | match |  |
| K-53 | C3 L RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 L RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C3 L RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C3 L RR b_hull | m | 0.128947286493012 | 0.128947286493012 | 0 | match |  |
| K-57 | C3 L RR r_sigma | rsig | 0.00193709701628208 | 0.00193709701628208 | 0 | match |  |
| K-58 | C3 L RR f | rel | 0.995709137074873 | 0.995709137074873 | 0 | match |  |
| K-59 | C3 L RR z/f | m | 0.0914670048808349 | 0.0914670048808349 | 0 | match |  |
| K-59 | C3 L RR delta_grid | m | -0.000392472380115549 | -0.000392472380115549 | 0 | match |  |
| K-60 | C3 L RR dz_1n | m | 0.000750202079907079 | 0.000750202079907078 | 1.08e-19 | match |  |
| K-53 | C3 R FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C3 R FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C3 R FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-53 | C3 R FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 R FR N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C3 R FR N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C3 R FR b_hull | m | 0.171320346158871 | 0.171320346158871 | 0 | match |  |
| K-57 | C3 R FR r_sigma | rsig | 0.0039468198636171 | 0.0039468198636171 | 0 | match |  |
| K-58 | C3 R FR f | rel | 1.0235473295532 | 1.0235473295532 | 0 | match |  |
| K-59 | C3 R FR z/f | m | 0.0893969793789423 | 0.0893969793789423 | 0 | match |  |
| K-59 | C3 R FR delta_grid | m | 0.00210506013449676 | 0.00210506013449676 | 0 | match |  |
| K-60 | C3 R FR dz_1n | m | 0.000427180389885337 | 0.000427180389885337 | 0 | match |  |
| K-53 | C3 R RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 R RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C3 R RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C3 R RL b_hull | m | 0.12879197224422 | 0.12879197224422 | 0 | match |  |
| K-57 | C3 R RL r_sigma | rsig | 0.00326921445115824 | 0.00326921445115824 | 0 | match |  |
| K-58 | C3 R RL f | rel | 0.987138085561253 | 0.987138085561253 | 0 | match |  |
| K-59 | C3 R RL z/f | m | 0.143451718882774 | 0.143451718882774 | 0 | match |  |
| K-59 | C3 R RL delta_grid | m | -0.00184506373436143 | -0.00184506373436143 | 0 | match |  |
| K-60 | C3 R RL dz_1n | m | 0.0011664469122604 | 0.0011664469122604 | 0 | match |  |
| K-53 | C3 R RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C3 R RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C3 R RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-53 | C3 max FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C3 max FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C3 max FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-53 | C3 max FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 max FR N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C3 max FR N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-56 | C3 max FR b_hull | m | 0.171471784654952 | 0.171471784654952 | 0 | match |  |
| K-57 | C3 max FR r_sigma | rsig | 0.000221436311838369 | 0.000221436311838418 | 4.87e-17 | match |  |
| K-58 | C3 max FR f | rel | 1.0095002964638 | 1.0095002964638 | 1.11e-15 | match |  |
| K-59 | C3 max FR z/f | m | 0.0869936131429896 | 0.0869936131429897 | 8.33e-17 | match |  |
| K-59 | C3 max FR delta_grid | m | 0.000826465115315607 | 0.00082646511531551 | 9.75e-17 | match |  |
| K-60 | C3 max FR dz_1n | m | 0.000409991028283404 | 0.000409991028283404 | 0 | match |  |
| K-53 | C3 max RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 max RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C3 max RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C3 max RL b_hull | m | 0.128914635756229 | 0.128914635756229 | 0 | match |  |
| K-57 | C3 max RL r_sigma | rsig | 2.52241985646779e-05 | 2.52241985646779e-05 | 0 | match |  |
| K-58 | C3 max RL f | rel | 0.995622394965852 | 0.995622394965852 | 0 | match |  |
| K-59 | C3 max RL z/f | m | 0.111499351003324 | 0.111499351003324 | 0 | match |  |
| K-59 | C3 max RL delta_grid | m | -0.000488100120256404 | -0.000488100120256404 | 0 | match |  |
| K-60 | C3 max RL dz_1n | m | 0.000914425460321812 | 0.000914425460321812 | 2.17e-19 | match |  |
| K-53 | C3 max RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 max RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C3 max RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C3 max RR b_hull | m | 0.128875610757964 | 0.128875610757964 | 0 | match |  |
| K-57 | C3 max RR r_sigma | rsig | 0.000485586833932381 | 0.000485586833932381 | 0 | match |  |
| K-58 | C3 max RR f | rel | 0.987358727734864 | 0.987358727734864 | 0 | match |  |
| K-59 | C3 max RR z/f | m | 0.108199762509918 | 0.108199762509918 | 0 | match |  |
| K-59 | C3 max RR delta_grid | m | -0.00136778265691094 | -0.00136778265691094 | 0 | match |  |
| K-60 | C3 max RR dz_1n | m | 0.000879999834044543 | 0.000879999834044543 | 0 | match |  |
| K-53 | C3 e FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C3 e FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C3 e FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-53 | C3 e FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 e FR N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C3 e FR N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C3 e FR b_hull | m | 0.171320346158871 | 0.171320346158871 | 0 | match |  |
| K-57 | C3 e FR r_sigma | rsig | 0.0039468198636171 | 0.0039468198636171 | 0 | match |  |
| K-58 | C3 e FR f | rel | 1.0235473295532 | 1.0235473295532 | 0 | match |  |
| K-59 | C3 e FR z/f | m | 0.0893969793789423 | 0.0893969793789423 | 0 | match |  |
| K-59 | C3 e FR delta_grid | m | 0.00210506013449676 | 0.00210506013449676 | 0 | match |  |
| K-60 | C3 e FR dz_1n | m | 0.000427180389885337 | 0.000427180389885337 | 0 | match |  |
| K-53 | C3 e RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 e RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C3 e RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C3 e RL b_hull | m | 0.12879197224422 | 0.12879197224422 | 0 | match |  |
| K-57 | C3 e RL r_sigma | rsig | 0.00326921445115824 | 0.00326921445115824 | 0 | match |  |
| K-58 | C3 e RL f | rel | 0.987138085561253 | 0.987138085561253 | 0 | match |  |
| K-59 | C3 e RL z/f | m | 0.143451718882774 | 0.143451718882774 | 0 | match |  |
| K-59 | C3 e RL delta_grid | m | -0.00184506373436143 | -0.00184506373436143 | 0 | match |  |
| K-60 | C3 e RL dz_1n | m | 0.0011664469122604 | 0.0011664469122604 | 0 | match |  |
| K-53 | C3 e RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C3 e RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C3 e RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-53 | C3 end FL state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C3 end FL N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C3 end FL N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-53 | C3 end FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 end FR N_h | exact | 1065 | 1065 |  | match |  |
| K-55 | C3 end FR N_h D2/A | rel | 0.994397759103642 | 0.994397759103642 | 0 | match |  |
| K-56 | C3 end FR b_hull | m | 0.171244954639421 | 0.171244954639421 | 0 | match |  |
| K-57 | C3 end FR r_sigma | rsig | 0.00327357075780142 | 0.00327357075780142 | 0 | match |  |
| K-58 | C3 end FR f | rel | 1.02824251304083 | 1.02824251304083 | 0 | match |  |
| K-59 | C3 end FR z/f | m | 0.0901457100785252 | 0.0901457100785252 | 0 | match |  |
| K-59 | C3 end FR delta_grid | m | 0.00254594139246734 | 0.00254594139246734 | 0 | match |  |
| K-60 | C3 end FR dz_1n | m | 0.000432734133851506 | 0.000432734133851506 | 0 | match |  |
| K-53 | C3 end RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C3 end RL N_h | exact | 607 | 607 |  | match |  |
| K-55 | C3 end RL N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C3 end RL b_hull | m | 0.128685867997088 | 0.128685867997088 | 0 | match |  |
| K-57 | C3 end RL r_sigma | rsig | 0.00491282139813701 | 0.00491282139813701 | 0 | match |  |
| K-58 | C3 end RL f | rel | 0.995013656008041 | 0.995013656008041 | 0 | match |  |
| K-59 | C3 end RL z/f | m | 0.143382501605861 | 0.143382501605861 | 0 | match |  |
| K-59 | C3 end RL delta_grid | m | -0.000714954475434404 | -0.000714954475434404 | 0 | match |  |
| K-60 | C3 end RL dz_1n | m | 0.00117518572595079 | 0.00117518572595079 | 0 | match |  |
| K-53 | C3 end RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C3 end RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C3 end RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-61 | C3 dz_post_corr FL | m | null | null |  | both_NA |  |
| K-61 | C3 dz_post_corr FR | m | 0.00411955469203136 | 0.00411955469203136 | 0 | match |  |
| K-61 | C3 dz_post_corr RL | m | 0.0483901703801347 | 0.0483901703801347 | 0 | match |  |
| K-61 | C3 dz_post_corr RR | m | null | null |  | both_NA |  |
| K-62 | C3 z_e(f_e-f_L) @b*=FL | m | null | null |  | both_NA |  P2 key absent |
| K-67 | C3 m_L | m | 0.03 | 0.03 | 0 | match |  |
| K-68 | C3 m_L source | exact | "E3c10" | "E3c10" |  | match |  |
| K-69 | C3 T-14 (checked True ok True) | exact | true | true |  | match | both None counted as both_NA |
| K-80 | C3 R1-4 n_L | exact | 460 | 460 |  | match |  |
| K-80 | C3 R1-4 sum ratio | rel | 1.03738943268135 | 1.03738943268135 | 2.22e-16 | match |  |
| K-80 | C3 R1-4 W_hat FL | N | -1554.97371470313 | -1554.97371470308 | 4.37e-11 | match |  |
| K-80 | C3 R1-4 E-Fpk FL | N | -1554.97371470313 | -1554.97371470308 | 4.37e-11 | match |  |
| K-80 | C3 R1-4 stroke rate FL | m/s | 0.0210622994574561 | 0.0210622994574561 | 0 | match |  |
| K-80 | C3 R1-4 W_hat FR | N | -1639.76856697784 | -1639.7685669778 | 4.37e-11 | match |  |
| K-80 | C3 R1-4 E-Fpk FR | N | -3748.75899102785 | -3748.7589910278 | 4.37e-11 | match |  |
| K-80 | C3 R1-4 stroke rate FR | m/s | 0.0200859123144781 | 0.0200859123144781 | 0 | match |  |
| K-80 | C3 R1-4 W_hat RL | N | 1916.34093715189 | 1916.34093715192 | 2.91e-11 | match |  |
| K-80 | C3 R1-4 E-Fpk RL | N | 1916.34093715189 | 1916.34093715192 | 2.91e-11 | match |  |
| K-80 | C3 R1-4 stroke rate RL | m/s | 0.00310470592422618 | 0.00310470592422618 | 0 | match |  |
| K-80 | C3 R1-4 W_hat RR | N | 1278.401344529 | 1278.40134452902 | 1.46e-11 | match |  |
| K-80 | C3 R1-4 E-Fpk RR | N | 582.145872579 | 582.145872579014 | 1.46e-11 | match |  |
| K-80 | C3 R1-4 stroke rate RR | m/s | 0.00444494239995652 | 0.00444494239995652 | 0 | match |  |
| K-80 | C3 R1-4 flag | exact | false | false |  | match |  |
| K-85 | C3 T-8 leg liftoff set | exact | [] | [] |  | match |  |
| K-86 | C3 T-9 crawler retouch | exact | false | false |  | match |  |
| K-04 | C4 n_L1 | exact | 432 | 432 |  | match |  |
| K-05 | C4 n_L | exact | 481 | 481 |  | match |  |
| K-06 | C4 loc_revokes | exact | 2 | 2 |  | match |  |
| K-07 | C4 n_R | exact | null | null |  | both_NA |  |
| K-08 | C4 n_creep | exact | 513 | 513 |  | match |  |
| K-09 | C4 n_max | exact | 596 | 596 |  | match |  |
| K-10 | C4 n_end | exact | 1680 | 1680 |  | match |  |
| K-11 | C4 s_L FL | m | 0.520541635001269 | 0.520541635001269 | 0 | match |  |
| K-11 | C4 s_L FR | m | 0.645020993485377 | 0.645020993485377 | 0 | match |  |
| K-11 | C4 s_L RL | m | 0.399072027659948 | 0.399072027659948 | 0 | match |  |
| K-11 | C4 s_L RR | m | 0.511099840957435 | 0.511099840957435 | 0 | match |  |
| K-12 | C4 s_R FL | m | null | null |  | both_NA |  |
| K-12 | C4 s_R FR | m | null | null |  | both_NA |  |
| K-12 | C4 s_R RL | m | null | null |  | both_NA |  |
| K-12 | C4 s_R RR | m | null | null |  | both_NA |  |
| K-13 | C4 s_max FL | m | 0.552914822401738 | 0.552914822401738 | 0 | match |  |
| K-13 | C4 s_max FR | m | 0.681197257404756 | 0.681197257404756 | 0 | match |  |
| K-13 | C4 s_max RL | m | 0.433532230120297 | 0.433532230120297 | 0 | match |  |
| K-13 | C4 s_max RR | m | 0.544795017401645 | 0.544795017401645 | 0 | match |  |
| K-14 | C4 b* | exact | "FR" | "FR" |  | match |  |
| K-15 | C4 g | m | 0.00160274259524362 | 0.00160274259524362 | 0 | match |  |
| K-16 | C4 n_sgs | exact | 505 | 505 |  | match |  |
| K-17 | C4 n_warn_lift | exact | 505 | 505 |  | match |  |
| K-18 | C4 SGS | exact | true | true |  | match |  |
| K-19 | C4 n_e | exact | 596 | 596 |  | match |  |
| K-20 | C4 n_e_leg FL | exact | 1074 | 1074 |  | match |  |
| K-21 | C4 n_max_leg FL | exact | 1074 | 1074 |  | match |  |
| K-20 | C4 n_e_leg FR | exact | 596 | 596 |  | match |  |
| K-21 | C4 n_max_leg FR | exact | 596 | 596 |  | match |  |
| K-20 | C4 n_e_leg RL | exact | 897 | 897 |  | match |  |
| K-21 | C4 n_max_leg RL | exact | 897 | 897 |  | match |  |
| K-20 | C4 n_e_leg RR | exact | 532 | 532 |  | match |  |
| K-21 | C4 n_max_leg RR | exact | 532 | 532 |  | match |  |
| K-22 | C4 z(t_L) FL | m | 0.0931680480036787 | 0.0931680480036787 | 0 | match |  |
| K-22 | C4 z(t_L) FR | m | 0.111523541338356 | 0.111523541338356 | 0 | match |  |
| K-22 | C4 z(t_L) RL | m | 0.0945908295298464 | 0.0945908295298464 | 0 | match |  |
| K-22 | C4 z(t_L) RR | m | 0.109586306561168 | 0.109586306561168 | 0 | match |  |
| K-22 | C4 z(t_R) FL | m | null | null |  | both_NA |  |
| K-22 | C4 z(t_R) FR | m | null | null |  | both_NA |  |
| K-22 | C4 z(t_R) RL | m | null | null |  | both_NA |  |
| K-22 | C4 z(t_R) RR | m | null | null |  | both_NA |  |
| K-22 | C4 z(t_max) FL | m | 0.10117919821885 | 0.10117919821885 | 0 | match |  |
| K-22 | C4 z(t_max) FR | m | 0.111504813194249 | 0.111504813194249 | 0 | match |  |
| K-22 | C4 z(t_max) RL | m | 0.106422660757476 | 0.106422660757476 | 0 | match |  |
| K-22 | C4 z(t_max) RR | m | 0.110180201431644 | 0.110180201431644 | 0 | match |  |
| K-22 | C4 z(t_e) FL | m | 0.10117919821885 | 0.10117919821885 | 0 | match |  |
| K-22 | C4 z(t_e) FR | m | 0.111504813194249 | 0.111504813194249 | 0 | match |  |
| K-22 | C4 z(t_e) RL | m | 0.106422660757476 | 0.106422660757476 | 0 | match |  |
| K-22 | C4 z(t_e) RR | m | 0.110180201431644 | 0.110180201431644 | 0 | match |  |
| K-22 | C4 z(t_end) FL | m | 0.101179193301677 | 0.101179193301677 | 0 | match |  |
| K-22 | C4 z(t_end) FR | m | 0.111504769937182 | 0.111504769937182 | 0 | match |  |
| K-22 | C4 z(t_end) RL | m | 0.106422684395556 | 0.106422684395556 | 0 | match |  |
| K-22 | C4 z(t_end) RR | m | 0.110180191903339 | 0.110180191903339 | 0 | match |  |
| K-23 | C4 dz_post FL | m | 0.0080111502151709 | 0.0080111502151709 | 0 | match |  |
| K-23 | C4 dz_post FR | m | -1.87281441069997e-05 | -1.87281441069997e-05 | 0 | match |  |
| K-23 | C4 dz_post RL | m | 0.0118318312276295 | 0.0118318312276295 | 0 | match |  |
| K-23 | C4 dz_post RR | m | 0.000593894870476855 | 0.000593894870476855 | 0 | match |  |
| K-24 | C4 dz_post_leg_window FL | m | 0.00801117217947549 | 0.00801117217947549 | 0 | match |  |
| K-24 | C4 dz_post_leg_window FR | m | -1.87281441069997e-05 | -1.87281441069997e-05 | 0 | match |  |
| K-24 | C4 dz_post_leg_window RL | m | 0.0118319112802007 | 0.0118319112802007 | 0 | match |  |
| K-24 | C4 dz_post_leg_window RR | m | 0.000593700437768865 | 0.000593700437768865 | 0 | match |  |
| K-25 | C4 dz_L_to_max FL | m | 0.0080111502151709 | 0.0080111502151709 | 0 | match |  |
| K-25 | C4 dz_L_to_max FR | m | -1.87281441069997e-05 | -1.87281441069997e-05 | 0 | match |  |
| K-25 | C4 dz_L_to_max RL | m | 0.0118318312276295 | 0.0118318312276295 | 0 | match |  |
| K-25 | C4 dz_L_to_max RR | m | 0.000593894870476855 | 0.000593894870476855 | 0 | match |  |
| K-26 | C4 dz_max_to_R FL | m | null | null |  | both_NA |  |
| K-26 | C4 dz_max_to_R FR | m | null | null |  | both_NA |  |
| K-26 | C4 dz_max_to_R RL | m | null | null |  | both_NA |  |
| K-26 | C4 dz_max_to_R RR | m | null | null |  | both_NA |  |
| K-27 | C4 dz_L_to_R FL | m | null | null |  | both_NA |  |
| K-27 | C4 dz_L_to_R FR | m | null | null |  | both_NA |  |
| K-27 | C4 dz_L_to_R RL | m | null | null |  | both_NA |  |
| K-27 | C4 dz_L_to_R RR | m | null | null |  | both_NA |  |
| K-28 | C4 dz_R_to_end FL | m | null | null |  | both_NA |  |
| K-28 | C4 dz_R_to_end FR | m | null | null |  | both_NA |  |
| K-28 | C4 dz_R_to_end RL | m | null | null |  | both_NA |  |
| K-28 | C4 dz_R_to_end RR | m | null | null |  | both_NA |  |
| K-29 | C4 secant_L_to_R_m_per_N FL | rel | null | null |  | both_NA |  |
| K-29 | C4 secant_L_to_R_m_per_N FR | rel | null | null |  | both_NA |  |
| K-29 | C4 secant_L_to_R_m_per_N RL | rel | null | null |  | both_NA |  |
| K-29 | C4 secant_L_to_R_m_per_N RR | rel | null | null |  | both_NA |  |
| K-30 | C4 delta_os FL | m | null | null |  | both_NA |  |
| K-30 | C4 delta_os FR | m | null | null |  | both_NA |  |
| K-30 | C4 delta_os RL | m | null | null |  | both_NA |  |
| K-30 | C4 delta_os RR | m | null | null |  | both_NA |  |
| K-31 | C4 t_max - t_L | s | 11.5 | 11.5 | 0 | match |  |
| K-32 | C4 s_hat P-A @b*=FR | m | 0.708586787554084 | 0.708586787554084 | 0 | match |  |
| K-33 | C4 e P-A @b*=FR | m | -0.0273895301493281 | -0.0273895301493281 | 0 | match |  |
| K-34 | C4 e P-A @b=FR | m | -0.0273895301493281 | -0.0273895301493281 | 0 | match |  |
| K-32 | C4 s_hat P-B @b*=FR | m | 0.709864519022961 | 0.709864519022961 | 0 | match |  |
| K-33 | C4 e P-B @b*=FR | m | -0.0286672616182043 | -0.0286672616182043 | 0 | match |  |
| K-34 | C4 e P-B @b=FR | m | -0.0286672616182043 | -0.0286672616182043 | 0 | match |  |
| K-32 | C4 s_hat P-D @b*=FR | m | 0.708586787554084 | 0.708586787554084 | 0 | match |  |
| K-33 | C4 e P-D @b*=FR | m | -0.0273895301493281 | -0.0273895301493281 | 0 | match |  |
| K-34 | C4 e P-D @b=FR | m | -0.0273895301493281 | -0.0273895301493281 | 0 | match |  |
| K-32 | C4 s_hat P-G @b*=FR | m | 0.659976837264627 | 0.659976837264627 | 2.22e-16 | match |  |
| K-33 | C4 e P-G @b*=FR | m | 0.0212204201401296 | 0.0212204201401298 | 2.22e-16 | match |  |
| K-34 | C4 e P-G @b=FR | m | 0.0212204201401296 | 0.0212204201401298 | 2.22e-16 | match |  |
| K-32 | C4 s_hat P-C @b*=FR | m | 0.729719306879452 | 0.729719306879452 | 0 | match |  |
| K-33 | C4 e P-C @b*=FR | m | -0.0485220494746953 | -0.0485220494746953 | 0 | match |  |
| K-34 | C4 e P-C @b=FR | m | -0.0485220494746953 | -0.0485220494746953 | 0 | match |  |
| K-35 | C4 lower bound (M-6) vs sgs | exact | true | true |  | match |  |
| K-36 | C4 P-G k* | exact | "RL" | "RL" |  | match |  |
| K-37 | C4 rho_k* | m | 0.00806122615736284 | 0.00806122615736284 | 0 | match |  |
| K-38 | C4 Zhat_k* | m | 0.0405487241320949 | 0.0405487241320952 | 2.43e-16 | match |  |
| K-39 | C4 phi_L | rad | -0.00633568966491988 | -0.00633568966491988 | 0 | match |  |
| K-39 | C4 theta_L | rad | 0.000322459741803108 | 0.000322459741803108 | 0 | match |  |
| K-40 | C4 c_hat(t_L) | m | 0.00878667810861988 | 0.00878667810861988 | 0 | match |  |
| K-41 | C4 c_hat_corner RR | m | 0.108390208887436 | 0.108390208887436 | 0 | match |  |
| K-43 | C4 rho RR | m | -0.00924787800719828 | -0.00924787800719828 | 0 | match |  |
| K-41 | C4 c_hat_corner RL | m | 0.00878667810861988 | 0.00878667810861988 | 0 | match |  |
| K-43 | C4 rho RL | m | 0.00806122615736284 | 0.00806122615736284 | 0 | match |  |
| K-41 | C4 c_hat_corner FR | m | 0.203451724252318 | 0.203451724252318 | 0 | match |  |
| K-43 | C4 rho FR | m | -0.00805993631839563 | -0.00805993631839563 | 0 | match |  |
| K-41 | C4 c_hat_corner FL | m | 0.103848193473503 | 0.103848193473503 | 0 | match |  |
| K-43 | C4 rho FL | m | 0.00924916784616549 | 0.00924916784616549 | 0 | match |  |
| K-42 | C4 ds_geo FL | m | 0.00912684413416891 | 0.00912684413416891 | 0 | match |  |
| K-44 | C4 W_hat FL | N | -2631.27575529278 | -2631.27575529277 | 1.46e-11 | match |  |
| K-44 | C4 E_hat FL | N | 122368.760436638 | 122368.760436638 | 1.46e-11 | match |  |
| K-44 | C4 F_pk FL | N | 125000.036191931 | 125000.036191931 | 0 | match |  |
| K-42 | C4 ds_geo FR | m | -0.00764752782267297 | -0.00764752782267297 | 0 | match |  |
| K-44 | C4 W_hat FR | N | 1545.21488156961 | 1545.21488156963 | 1.46e-11 | match |  |
| K-44 | C4 E_hat FR | N | 120303.603492798 | 120303.603492798 | 1.46e-11 | match |  |
| K-44 | C4 F_pk FR | N | 129903.384931929 | 129903.384931929 | 0 | match |  |
| K-42 | C4 ds_geo RL | m | 0.00657524485961119 | 0.00657524485961119 | 0 | match |  |
| K-44 | C4 W_hat RL | N | 2420.97371007621 | 2420.97371007623 | 1.46e-11 | match |  |
| K-44 | C4 E_hat RL | N | 74703.2057246581 | 74703.2057246581 | 1.46e-11 | match |  |
| K-44 | C4 F_pk RL | N | 72321.3055731319 | 72321.3055731319 | 0 | match |  |
| K-42 | C4 ds_geo RR | m | -0.00869883578457767 | -0.00869883578457767 | 0 | match |  |
| K-44 | C4 W_hat RR | N | -1334.91283635309 | -1334.91283635308 | 1.46e-11 | match |  |
| K-44 | C4 E_hat RR | N | 72822.7223657363 | 72822.7223657363 | 1.46e-11 | match |  |
| K-44 | C4 F_pk RR | N | 74553.8685756894 | 74553.8685756894 | 0 | match |  |
| K-45 | C4 sum F / sum W_static | rel | 1.03615320046163 | 1.03615320046163 | 2.22e-16 | match |  |
| K-46 | C4 E3c10 events | exact | ["INFO_LOC_CLEARANCE_MARGIN:80"] | ["INFO_LOC_CLEARANCE_MARGIN:80"] |  | match |  |
| K-47 | C4 R4c30 count | exact | 0 | 0 |  | match |  |
| K-48 | C4 M-8 loc_revoked | exact | 2 | 2 |  | match |  |
| K-49 | C4 M-8 sgs>0 | exact | true | true |  | match |  |
| K-50 | C4 pair diff s_max(b*) | m | -0.00123121032403872 | -0.00123121032403872 | 0 | match |  |
| K-51 | C4 pair diff dz_post(b*) | m | -1.89968265484342e-05 | -1.89968265484342e-05 | 0 | match |  |
| K-52 | C4 harness s_max spread min (n=4) | m | 0.682428467728795 | 0.682428467728795 | 0 | match |  |
| K-52 | C4 harness s_max spread max (n=4) | m | 0.682766304167964 | 0.682766304167964 | 0 | match |  |
| K-53 | C4 L FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 L FL N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C4 L FL N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-56 | C4 L FL b_hull | m | 0.17155201244688 | 0.17155201244688 | 0 | match |  |
| K-57 | C4 L FL r_sigma | rsig | 0.00182000240435264 | 0.00182000240435262 | 2.41e-17 | match |  |
| K-58 | C4 L FL f | rel | 1.00962454462416 | 1.00962454462416 | 1.11e-15 | match |  |
| K-59 | C4 L FL z/f | m | 0.0922798960264588 | 0.0922798960264589 | 1.11e-16 | match |  |
| K-59 | C4 L FL delta_grid | m | 0.000888151977219911 | 0.000888151977219808 | 1.03e-16 | match |  |
| K-60 | C4 L FL dz_1n | m | 0.000434958207300087 | 0.000434958207300087 | 0 | match |  |
| K-53 | C4 L FR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C4 L FR N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C4 L FR N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-53 | C4 L RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 L RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 L RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 L RL b_hull | m | 0.129919180339624 | 0.129919180339624 | 0 | match |  |
| K-57 | C4 L RL r_sigma | rsig | 0.00162338104694527 | 0.00162338104694527 | 0 | match |  |
| K-58 | C4 L RL f | rel | 0.990092724917083 | 0.990092724917083 | 0 | match |  |
| K-59 | C4 L RL z/f | m | 0.0955373442803229 | 0.0955373442803229 | 0 | match |  |
| K-59 | C4 L RL delta_grid | m | -0.000946514750476503 | -0.000946514750476503 | 0 | match |  |
| K-60 | C4 L RL dz_1n | m | 0.000779166635336462 | 0.000779166635336462 | 0 | match |  |
| K-53 | C4 L RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 L RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 L RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 L RR b_hull | m | 0.128991171533509 | 0.128991171533509 | 0 | match |  |
| K-57 | C4 L RR r_sigma | rsig | 0.000298876078989371 | 0.000298876078989371 | 0 | match |  |
| K-58 | C4 L RR f | rel | 0.987663208636148 | 0.987663208636148 | 0 | match |  |
| K-59 | C4 L RR z/f | m | 0.110955136936298 | 0.110955136936298 | 0 | match |  |
| K-59 | C4 L RR delta_grid | m | -0.00136883037513076 | -0.00136883037513076 | 0 | match |  |
| K-60 | C4 L RR dz_1n | m | 0.000902687862942073 | 0.000902687862942072 | 1.08e-19 | match |  |
| K-53 | C4 R FL state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C4 R FR state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C4 R RL state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C4 R RR state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C4 max FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 max FL N_h | exact | 1068 | 1068 |  | match |  |
| K-55 | C4 max FL N_h D2/A | rel | 0.997198879551821 | 0.997198879551821 | 0 | match |  |
| K-56 | C4 max FL b_hull | m | 0.171449592648599 | 0.171449592648599 | 0 | match |  |
| K-57 | C4 max FL r_sigma | rsig | 0.00018314738719263 | 0.00018314738719263 | 0 | match |  |
| K-58 | C4 max FL f | rel | 1.0142007329977 | 1.0142007329977 | 0 | match |  |
| K-59 | C4 max FL z/f | m | 0.0997624976268663 | 0.0997624976268663 | 0 | match |  |
| K-59 | C4 max FL delta_grid | m | 0.00141670059198326 | 0.00141670059198326 | 0 | match |  |
| K-60 | C4 max FL dz_1n | m | 0.000472358535102006 | 0.000472358535102006 | 0 | match |  |
| K-53 | C4 max FR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C4 max FR N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C4 max FR N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-53 | C4 max RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 max RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 max RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 max RL b_hull | m | 0.129919180339624 | 0.129919180339624 | 0 | match |  |
| K-57 | C4 max RL r_sigma | rsig | 0.000233610795379498 | 0.000233610795379498 | 0 | match |  |
| K-58 | C4 max RL f | rel | 0.990092724917083 | 0.990092724917083 | 0 | match |  |
| K-59 | C4 max RL z/f | m | 0.107487569678273 | 0.107487569678273 | 0 | match |  |
| K-59 | C4 max RL delta_grid | m | -0.00106490892079685 | -0.00106490892079685 | 0 | match |  |
| K-60 | C4 max RL dz_1n | m | 0.000876628177573937 | 0.000876628177573937 | 0 | match |  |
| K-53 | C4 max RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 max RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 max RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 max RR b_hull | m | 0.128991171533509 | 0.128991171533509 | 0 | match |  |
| K-57 | C4 max RR r_sigma | rsig | 0.00154488971998468 | 0.00154488971998468 | 0 | match |  |
| K-58 | C4 max RR f | rel | 0.987663208636148 | 0.987663208636148 | 0 | match |  |
| K-59 | C4 max RR z/f | m | 0.111556450081593 | 0.111556450081593 | 0 | match |  |
| K-59 | C4 max RR delta_grid | m | -0.0013762486499486 | -0.0013762486499486 | 0 | match |  |
| K-60 | C4 max RR dz_1n | m | 0.000907579912946 | 0.000907579912946 | 0 | match |  |
| K-53 | C4 e FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 e FL N_h | exact | 1068 | 1068 |  | match |  |
| K-55 | C4 e FL N_h D2/A | rel | 0.997198879551821 | 0.997198879551821 | 0 | match |  |
| K-56 | C4 e FL b_hull | m | 0.171449592648599 | 0.171449592648599 | 0 | match |  |
| K-57 | C4 e FL r_sigma | rsig | 0.00018314738719263 | 0.00018314738719263 | 0 | match |  |
| K-58 | C4 e FL f | rel | 1.0142007329977 | 1.0142007329977 | 0 | match |  |
| K-59 | C4 e FL z/f | m | 0.0997624976268663 | 0.0997624976268663 | 0 | match |  |
| K-59 | C4 e FL delta_grid | m | 0.00141670059198326 | 0.00141670059198326 | 0 | match |  |
| K-60 | C4 e FL dz_1n | m | 0.000472358535102006 | 0.000472358535102006 | 0 | match |  |
| K-53 | C4 e FR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C4 e FR N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C4 e FR N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-53 | C4 e RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 e RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 e RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 e RL b_hull | m | 0.129919180339624 | 0.129919180339624 | 0 | match |  |
| K-57 | C4 e RL r_sigma | rsig | 0.000233610795379498 | 0.000233610795379498 | 0 | match |  |
| K-58 | C4 e RL f | rel | 0.990092724917083 | 0.990092724917083 | 0 | match |  |
| K-59 | C4 e RL z/f | m | 0.107487569678273 | 0.107487569678273 | 0 | match |  |
| K-59 | C4 e RL delta_grid | m | -0.00106490892079685 | -0.00106490892079685 | 0 | match |  |
| K-60 | C4 e RL dz_1n | m | 0.000876628177573937 | 0.000876628177573937 | 0 | match |  |
| K-53 | C4 e RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 e RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 e RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 e RR b_hull | m | 0.128991171533509 | 0.128991171533509 | 0 | match |  |
| K-57 | C4 e RR r_sigma | rsig | 0.00154488971998468 | 0.00154488971998468 | 0 | match |  |
| K-58 | C4 e RR f | rel | 0.987663208636148 | 0.987663208636148 | 0 | match |  |
| K-59 | C4 e RR z/f | m | 0.111556450081593 | 0.111556450081593 | 0 | match |  |
| K-59 | C4 e RR delta_grid | m | -0.0013762486499486 | -0.0013762486499486 | 0 | match |  |
| K-60 | C4 e RR dz_1n | m | 0.000907579912946 | 0.000907579912946 | 0 | match |  |
| K-53 | C4 end FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 end FL N_h | exact | 1068 | 1068 |  | match |  |
| K-55 | C4 end FL N_h D2/A | rel | 0.997198879551821 | 0.997198879551821 | 0 | match |  |
| K-56 | C4 end FL b_hull | m | 0.171449592648599 | 0.171449592648599 | 0 | match |  |
| K-57 | C4 end FL r_sigma | rsig | 0.000186438409087756 | 0.000186438409087756 | 0 | match |  |
| K-58 | C4 end FL f | rel | 1.0142007329977 | 1.0142007329977 | 0 | match |  |
| K-59 | C4 end FL z/f | m | 0.0997624927785432 | 0.0997624927785432 | 0 | match |  |
| K-59 | C4 end FL delta_grid | m | 0.00141670052313352 | 0.00141670052313352 | 0 | match |  |
| K-60 | C4 end FL dz_1n | m | 0.000472358512146016 | 0.000472358512146016 | 0 | match |  |
| K-53 | C4 end FR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C4 end FR N_h | exact | 1069 | 1069 |  | match |  |
| K-55 | C4 end FR N_h D2/A | rel | 0.99813258636788 | 0.998132586367881 | 2.22e-16 | match |  |
| K-53 | C4 end RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 end RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 end RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 end RL b_hull | m | 0.129919180339624 | 0.129919180339624 | 0 | match |  |
| K-57 | C4 end RL r_sigma | rsig | 0.000233249689521768 | 0.000233249689521768 | 0 | match |  |
| K-58 | C4 end RL f | rel | 0.990092724917083 | 0.990092724917083 | 0 | match |  |
| K-59 | C4 end RL z/f | m | 0.107487593552886 | 0.107487593552886 | 0 | match |  |
| K-59 | C4 end RL delta_grid | m | -0.00106490915732921 | -0.00106490915732921 | 0 | match |  |
| K-60 | C4 end RL dz_1n | m | 0.000876628372286297 | 0.000876628372286296 | 2.17e-19 | match |  |
| K-53 | C4 end RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C4 end RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C4 end RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C4 end RR b_hull | m | 0.128991171533509 | 0.128991171533509 | 0 | match |  |
| K-57 | C4 end RR r_sigma | rsig | 0.00154253500993491 | 0.00154253500993491 | 0 | match |  |
| K-58 | C4 end RR f | rel | 0.987663208636148 | 0.987663208636148 | 0 | match |  |
| K-59 | C4 end RR z/f | m | 0.11155644043427 | 0.11155644043427 | 0 | match |  |
| K-59 | C4 end RR delta_grid | m | -0.00137624853093159 | -0.00137624853093159 | 0 | match |  |
| K-60 | C4 end RR dz_1n | m | 0.000907579834459131 | 0.000907579834459131 | 0 | match |  |
| K-61 | C4 dz_post_corr FL | m | 0.00748260160040756 | 0.00748260160040745 | 1.11e-16 | match |  |
| K-61 | C4 dz_post_corr FR | m | null | null |  | both_NA |  |
| K-61 | C4 dz_post_corr RL | m | 0.0119502253979498 | 0.0119502253979498 | 0 | match |  |
| K-61 | C4 dz_post_corr RR | m | 0.000601313145294699 | 0.000601313145294699 | 0 | match |  |
| K-62 | C4 z_e(f_e-f_L) @b*=FR | m | null | null |  | both_NA |  P2 key absent |
| K-67 | C4 m_L | m | 0.03 | 0.03 | 0 | match |  |
| K-68 | C4 m_L source | exact | "E3c10" | "E3c10" |  | match |  |
| K-69 | C4 T-14 (checked True ok True) | exact | true | true |  | match | both None counted as both_NA |
| K-80 | C4 R1-4 n_L | exact | 481 | 481 |  | match |  |
| K-80 | C4 R1-4 sum ratio | rel | 1.03615320046163 | 1.03615320046163 | 2.22e-16 | match |  |
| K-80 | C4 R1-4 W_hat FL | N | -2631.27575529278 | -2631.27575529277 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 E-Fpk FL | N | -2631.27575529278 | -2631.27575529277 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 stroke rate FL | m/s | 0.0133527704037617 | 0.0133527704037617 | 0 | match |  |
| K-80 | C4 R1-4 W_hat FR | N | 1545.21488156961 | 1545.21488156963 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 E-Fpk FR | N | -9599.78143913038 | -9599.78143913037 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 stroke rate FR | m/s | 0.0152069619663875 | 0.0152069619663875 | 0 | match |  |
| K-80 | C4 R1-4 W_hat RL | N | 2420.97371007621 | 2420.97371007623 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 E-Fpk RL | N | 2381.90015152622 | 2381.90015152624 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 stroke rate RL | m/s | 0.00790245222894004 | 0.00790245222894004 | 0 | match |  |
| K-80 | C4 R1-4 W_hat RR | N | -1334.91283635309 | -1334.91283635308 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 E-Fpk RR | N | -1731.14620995308 | -1731.14620995306 | 1.46e-11 | match |  |
| K-80 | C4 R1-4 stroke rate RR | m/s | 0.0124459668588683 | 0.0124459668588683 | 0 | match |  |
| K-80 | C4 R1-4 flag | exact | false | false |  | match |  |
| K-85 | C4 T-8 leg liftoff set | exact | [] | [] |  | match |  |
| K-86 | C4 T-9 crawler retouch | exact | false | false |  | match |  |
| K-04 | C5 n_L1 | exact | 464 | 464 |  | match |  |
| K-05 | C5 n_L | exact | 464 | 464 |  | match |  |
| K-06 | C5 loc_revokes | exact | 0 | 0 |  | match |  |
| K-07 | C5 n_R | exact | null | null |  | both_NA |  |
| K-08 | C5 n_creep | exact | 500 | 500 |  | match |  |
| K-09 | C5 n_max | exact | 897 | 897 |  | match |  |
| K-10 | C5 n_end | exact | 1680 | 1680 |  | match |  |
| K-11 | C5 s_L FL | m | 0.372931708632748 | 0.372931708632748 | 0 | match |  |
| K-11 | C5 s_L FR | m | 0.37228743426705 | 0.37228743426705 | 0 | match |  |
| K-11 | C5 s_L RL | m | 0.607614736524543 | 0.607614736524543 | 0 | match |  |
| K-11 | C5 s_L RR | m | 0.607225102997147 | 0.607225102997147 | 0 | match |  |
| K-12 | C5 s_R FL | m | null | null |  | both_NA |  |
| K-12 | C5 s_R FR | m | null | null |  | both_NA |  |
| K-12 | C5 s_R RL | m | null | null |  | both_NA |  |
| K-12 | C5 s_R RR | m | null | null |  | both_NA |  |
| K-13 | C5 s_max FL | m | 0.424873884713297 | 0.424873884713297 | 0 | match |  |
| K-13 | C5 s_max FR | m | 0.420799929370958 | 0.420799929370958 | 0 | match |  |
| K-13 | C5 s_max RL | m | 0.681296846760447 | 0.681296846760447 | 0 | match |  |
| K-13 | C5 s_max RR | m | 0.67746642411091 | 0.67746642411091 | 0 | match |  |
| K-14 | C5 b* | exact | "RL" | "RL" |  | match |  |
| K-15 | C5 g | m | 0.00150315323955319 | 0.00150315323955319 | 0 | match |  |
| K-16 | C5 n_sgs | exact | 502 | 502 |  | match |  |
| K-17 | C5 n_warn_lift | exact | 502 | 502 |  | match |  |
| K-18 | C5 SGS | exact | true | true |  | match |  |
| K-19 | C5 n_e | exact | 897 | 897 |  | match |  |
| K-20 | C5 n_e_leg FL | exact | 1074 | 1074 |  | match |  |
| K-21 | C5 n_max_leg FL | exact | 1074 | 1074 |  | match |  |
| K-20 | C5 n_e_leg FR | exact | 596 | 596 |  | match |  |
| K-21 | C5 n_max_leg FR | exact | 596 | 596 |  | match |  |
| K-20 | C5 n_e_leg RL | exact | 897 | 897 |  | match |  |
| K-21 | C5 n_max_leg RL | exact | 897 | 897 |  | match |  |
| K-20 | C5 n_e_leg RR | exact | 532 | 532 |  | match |  |
| K-21 | C5 n_max_leg RR | exact | 532 | 532 |  | match |  |
| K-22 | C5 z(t_L) FL | m | 0.0792570116607092 | 0.0792570116607092 | 0 | match |  |
| K-22 | C5 z(t_L) FR | m | 0.0753935101543777 | 0.0753935101543777 | 0 | match |  |
| K-22 | C5 z(t_L) RL | m | 0.11456426797833 | 0.11456426797833 | 0 | match |  |
| K-22 | C5 z(t_L) RR | m | 0.111129574696516 | 0.111129574696516 | 0 | match |  |
| K-22 | C5 z(t_R) FL | m | null | null |  | both_NA |  |
| K-22 | C5 z(t_R) FR | m | null | null |  | both_NA |  |
| K-22 | C5 z(t_R) RL | m | null | null |  | both_NA |  |
| K-22 | C5 z(t_R) RR | m | null | null |  | both_NA |  |
| K-22 | C5 z(t_max) FL | m | 0.0936211836340227 | 0.0936211836340227 | 0 | match |  |
| K-22 | C5 z(t_max) FR | m | 0.077082939202933 | 0.077082939202933 | 0 | match |  |
| K-22 | C5 z(t_max) RL | m | 0.125910038316629 | 0.125910038316629 | 0 | match |  |
| K-22 | C5 z(t_max) RR | m | 0.111007653622758 | 0.111007653622758 | 0 | match |  |
| K-22 | C5 z(t_e) FL | m | 0.0936211836340227 | 0.0936211836340227 | 0 | match |  |
| K-22 | C5 z(t_e) FR | m | 0.077082939202933 | 0.077082939202933 | 0 | match |  |
| K-22 | C5 z(t_e) RL | m | 0.125910038316629 | 0.125910038316629 | 0 | match |  |
| K-22 | C5 z(t_e) RR | m | 0.111007653622758 | 0.111007653622758 | 0 | match |  |
| K-22 | C5 z(t_end) FL | m | 0.0936211106043429 | 0.0936211106043429 | 0 | match |  |
| K-22 | C5 z(t_end) FR | m | 0.0770828633048725 | 0.0770828633048725 | 0 | match |  |
| K-22 | C5 z(t_end) RL | m | 0.125910033707996 | 0.125910033707996 | 0 | match |  |
| K-22 | C5 z(t_end) RR | m | 0.111007648451417 | 0.111007648451417 | 0 | match |  |
| K-23 | C5 dz_post FL | m | 0.0143641719733134 | 0.0143641719733134 | 0 | match |  |
| K-23 | C5 dz_post FR | m | 0.0016894290485553 | 0.0016894290485553 | 0 | match |  |
| K-23 | C5 dz_post RL | m | 0.0113457703382992 | 0.0113457703382992 | 0 | match |  |
| K-23 | C5 dz_post RR | m | -0.000121921073757983 | -0.000121921073757983 | 0 | match |  |
| K-24 | C5 dz_post_leg_window FL | m | 0.0143640004395866 | 0.0143640004395866 | 0 | match |  |
| K-24 | C5 dz_post_leg_window FR | m | 0.00168836558923502 | 0.00168836558923502 | 0 | match |  |
| K-24 | C5 dz_post_leg_window RL | m | 0.0113457703382992 | 0.0113457703382992 | 0 | match |  |
| K-24 | C5 dz_post_leg_window RR | m | -0.000121372630852823 | -0.000121372630852823 | 0 | match |  |
| K-25 | C5 dz_L_to_max FL | m | 0.0143641719733134 | 0.0143641719733134 | 0 | match |  |
| K-25 | C5 dz_L_to_max FR | m | 0.0016894290485553 | 0.0016894290485553 | 0 | match |  |
| K-25 | C5 dz_L_to_max RL | m | 0.0113457703382992 | 0.0113457703382992 | 0 | match |  |
| K-25 | C5 dz_L_to_max RR | m | -0.000121921073757983 | -0.000121921073757983 | 0 | match |  |
| K-26 | C5 dz_max_to_R FL | m | null | null |  | both_NA |  |
| K-26 | C5 dz_max_to_R FR | m | null | null |  | both_NA |  |
| K-26 | C5 dz_max_to_R RL | m | null | null |  | both_NA |  |
| K-26 | C5 dz_max_to_R RR | m | null | null |  | both_NA |  |
| K-27 | C5 dz_L_to_R FL | m | null | null |  | both_NA |  |
| K-27 | C5 dz_L_to_R FR | m | null | null |  | both_NA |  |
| K-27 | C5 dz_L_to_R RL | m | null | null |  | both_NA |  |
| K-27 | C5 dz_L_to_R RR | m | null | null |  | both_NA |  |
| K-28 | C5 dz_R_to_end FL | m | null | null |  | both_NA |  |
| K-28 | C5 dz_R_to_end FR | m | null | null |  | both_NA |  |
| K-28 | C5 dz_R_to_end RL | m | null | null |  | both_NA |  |
| K-28 | C5 dz_R_to_end RR | m | null | null |  | both_NA |  |
| K-29 | C5 secant_L_to_R_m_per_N FL | rel | null | null |  | both_NA |  |
| K-29 | C5 secant_L_to_R_m_per_N FR | rel | null | null |  | both_NA |  |
| K-29 | C5 secant_L_to_R_m_per_N RL | rel | null | null |  | both_NA |  |
| K-29 | C5 secant_L_to_R_m_per_N RR | rel | null | null |  | both_NA |  |
| K-30 | C5 delta_os FL | m | null | null |  | both_NA |  |
| K-30 | C5 delta_os FR | m | null | null |  | both_NA |  |
| K-30 | C5 delta_os RL | m | null | null |  | both_NA |  |
| K-30 | C5 delta_os RR | m | null | null |  | both_NA |  |
| K-31 | C5 t_max - t_L | s | 43.3 | 43.3 | 0 | match |  |
| K-32 | C5 s_hat P-A @b*=RL | m | 0.699561044224105 | 0.699561044224105 | 0 | match |  |
| K-33 | C5 e P-A @b*=RL | m | -0.0182641974636583 | -0.0182641974636583 | 0 | match |  |
| K-34 | C5 e P-A @b=RL | m | -0.0182641974636583 | -0.0182641974636583 | 0 | match |  |
| K-32 | C5 s_hat P-B @b*=RL | m | 0.699561044224105 | 0.699561044224105 | 0 | match |  |
| K-33 | C5 e P-B @b*=RL | m | -0.0182641974636583 | -0.0182641974636583 | 0 | match |  |
| K-34 | C5 e P-B @b=RL | m | -0.0182641974636583 | -0.0182641974636583 | 0 | match |  |
| K-32 | C5 s_hat P-D @b*=RL | m | 0.699561044224105 | 0.699561044224105 | 0 | match |  |
| K-33 | C5 e P-D @b*=RL | m | -0.0182641974636583 | -0.0182641974636583 | 0 | match |  |
| K-34 | C5 e P-D @b=RL | m | -0.0182641974636583 | -0.0182641974636583 | 0 | match |  |
| K-32 | C5 s_hat P-G @b*=RL | m | 0.712158742006317 | 0.712158742006317 | 0 | match |  |
| K-33 | C5 e P-G @b*=RL | m | -0.0308618952458699 | -0.0308618952458699 | 0 | match |  |
| K-34 | C5 e P-G @b=RL | m | -0.0308618952458699 | -0.0308618952458699 | 0 | match |  |
| K-32 | C5 s_hat P-C @b*=RL | m | 0.719415832080596 | 0.719415832080596 | 0 | match |  |
| K-33 | C5 e P-C @b*=RL | m | -0.0381189853201492 | -0.0381189853201492 | 0 | match |  |
| K-34 | C5 e P-C @b=RL | m | -0.0381189853201492 | -0.0381189853201492 | 0 | match |  |
| K-35 | C5 lower bound (M-6) vs sgs | exact | true | true |  | match |  |
| K-36 | C5 P-G k* | exact | "FR" | "FR" |  | match |  |
| K-37 | C5 rho_k* | m | -0.0128586844636685 | -0.0128586844636685 | 0 | match |  |
| K-38 | C5 Zhat_k* | m | 0.000260986681456851 | 0.000260986681456851 | 3.79e-19 | match |  |
| K-39 | C5 phi_L | rad | -0.000999292708193345 | -0.000999292708193345 | 0 | match |  |
| K-39 | C5 theta_L | rad | -0.00623299925394596 | -0.00623299925394596 | 0 | match |  |
| K-40 | C5 c_hat(t_L) | m | 0.00515231234742242 | 0.00515231234742242 | 0 | match |  |
| K-41 | C5 c_hat_corner RR | m | 0.154948176625632 | 0.154948176625632 | 0 | match |  |
| K-43 | C5 rho RR | m | 0.0101036847878685 | 0.0101036847878685 | 0 | match |  |
| K-41 | C5 c_hat_corner RL | m | 0.155473985786455 | 0.155473985786455 | 0 | match |  |
| K-43 | C5 rho RL | m | 0.0128337524666527 | 0.0128337524666527 | 0 | match |  |
| K-41 | C5 c_hat_corner FR | m | 0.00515231234742242 | 0.00515231234742242 | 0 | match |  |
| K-43 | C5 rho FR | m | -0.0128586844636685 | -0.0128586844636685 | 0 | match |  |
| K-41 | C5 c_hat_corner FL | m | 0.00567812150824623 | 0.00567812150824623 | 0 | match |  |
| K-43 | C5 rho FL | m | -0.0101286167848842 | -0.0101286167848842 | 0 | match |  |
| K-42 | C5 ds_geo FL | m | -0.0129743900015949 | -0.0129743900015949 | 0 | match |  |
| K-44 | C5 W_hat FL | N | 1688.97148406731 | 1688.97148406734 | 2.91e-11 | match |  |
| K-44 | C5 E_hat FL | N | 122279.782373448 | 122279.782373448 | 2.91e-11 | match |  |
| K-44 | C5 F_pk FL | N | 120590.810889381 | 120590.810889381 | 0 | match |  |
| K-42 | C5 ds_geo FR | m | -0.0156201173758076 | -0.0156201173758076 | 0 | match |  |
| K-44 | C5 W_hat FR | N | 372.121842519133 | 372.121842519147 | 1.46e-11 | match |  |
| K-44 | C5 E_hat FR | N | 120216.127068298 | 120216.127068298 | 1.46e-11 | match |  |
| K-44 | C5 F_pk FR | N | 120361.386267879 | 120361.386267879 | 0 | match |  |
| K-42 | C5 ds_geo RL | m | 0.0170986200469849 | 0.0170986200469849 | 0 | match |  |
| K-44 | C5 W_hat RL | N | -840.518673621278 | -840.518673621264 | 1.46e-11 | match |  |
| K-44 | C5 E_hat RL | N | 74648.8867421356 | 74648.8867421356 | 1.46e-11 | match |  |
| K-44 | C5 F_pk RL | N | 75655.7134769069 | 75655.7134769069 | 0 | match |  |
| K-42 | C5 ds_geo RR | m | 0.0146895251860724 | 0.0146895251860724 | 0 | match |  |
| K-44 | C5 W_hat RR | N | -1220.57465296518 | -1220.57465296517 | 1.46e-11 | match |  |
| K-44 | C5 E_hat RR | N | 72769.7707400992 | 72769.7707400992 | 1.46e-11 | match |  |
| K-44 | C5 F_pk RR | N | 75344.7645262894 | 75344.7645262894 | 0 | match |  |
| K-45 | C5 sum F / sum W_static | rel | 1.03539978182263 | 1.03539978182263 | 2.22e-16 | match |  |
| K-46 | C5 E3c10 events | exact | ["INFO_LOC_CLEARANCE_MARGIN:80"] | ["INFO_LOC_CLEARANCE_MARGIN:80"] |  | match |  |
| K-47 | C5 R4c30 count | exact | 0 | 0 |  | match |  |
| K-48 | C5 M-8 loc_revoked | exact | 0 | 0 |  | match |  |
| K-49 | C5 M-8 sgs>0 | exact | true | true |  | match |  |
| K-50 | C5 pair diff s_max(b*) | m | 0.000847457748429759 | 0.000847457748429759 | 0 | match |  |
| K-51 | C5 pair diff dz_post(b*) | m | 0.00437296027337448 | 0.00437296027337448 | 0 | match |  |
| K-52 | C5 harness s_max spread min (n=4) | m | 0.68005103415547 | 0.68005103415547 | 0 | match |  |
| K-52 | C5 harness s_max spread max (n=4) | m | 0.680449389012017 | 0.680449389012017 | 0 | match |  |
| K-53 | C5 L FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 L FL N_h | exact | 1066 | 1066 |  | match |  |
| K-55 | C5 L FL N_h D2/A | rel | 0.995331465919701 | 0.995331465919701 | 0 | match |  |
| K-56 | C5 L FL b_hull | m | 0.170676981302742 | 0.170676981302742 | 0 | match |  |
| K-57 | C5 L FL r_sigma | rsig | 0.00149332086945739 | 0.00149332086945739 | 0 | match |  |
| K-58 | C5 L FL f | rel | 1.02253174147803 | 1.02253174147803 | 0 | match |  |
| K-59 | C5 L FL z/f | m | 0.0775105636780977 | 0.0775105636780977 | 0 | match |  |
| K-59 | C5 L FL delta_grid | m | 0.0017464479826115 | 0.0017464479826115 | 0 | match |  |
| K-60 | C5 L FL dz_1n | m | 0.000370014060040659 | 0.000370014060040659 | 0 | match |  |
| K-53 | C5 L FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 L FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C5 L FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C5 L FR b_hull | m | 0.170583638179312 | 0.170583638179312 | 0 | match |  |
| K-57 | C5 L FR r_sigma | rsig | 0.000593812191384963 | 0.000593812191384963 | 0 | match |  |
| K-58 | C5 L FR f | rel | 1.01760190323782 | 1.01760190323782 | 0 | match |  |
| K-59 | C5 L FR z/f | m | 0.0740893957789288 | 0.0740893957789288 | 0 | match |  |
| K-59 | C5 L FR delta_grid | m | 0.00130411437544893 | 0.00130411437544893 | 0 | match |  |
| K-60 | C5 L FR dz_1n | m | 0.000351977171589065 | 0.000351977171589065 | 5.42e-20 | match |  |
| K-53 | C5 L RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 L RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C5 L RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C5 L RL b_hull | m | 0.128843108065374 | 0.128843108065374 | 0 | match |  |
| K-57 | C5 L RL r_sigma | rsig | 0.000775918048214573 | 0.000775918048214573 | 0 | match |  |
| K-58 | C5 L RL f | rel | 0.987273011166632 | 0.987273011166632 | 0 | match |  |
| K-59 | C5 L RL z/f | m | 0.11604112204278 | 0.11604112204278 | 0 | match |  |
| K-59 | C5 L RL delta_grid | m | -0.00147685406444999 | -0.00147685406444999 | 0 | match |  |
| K-60 | C5 L RL dz_1n | m | 0.000943692487465652 | 0.000943692487465652 | 1.08e-19 | match |  |
| K-53 | C5 L RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 L RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C5 L RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C5 L RR b_hull | m | 0.128677219616302 | 0.128677219616302 | 0 | match |  |
| K-57 | C5 L RR r_sigma | rsig | 0.00265101096463325 | 0.00265101096463325 | 0 | match |  |
| K-58 | C5 L RR f | rel | 0.994990609441823 | 0.994990609441823 | 0 | match |  |
| K-59 | C5 L RR z/f | m | 0.111689068863533 | 0.111689068863533 | 0 | match |  |
| K-59 | C5 L RR delta_grid | m | -0.000559494167016575 | -0.000559494167016575 | 0 | match |  |
| K-60 | C5 L RR dz_1n | m | 0.000915400121058616 | 0.000915400121058616 | 0 | match |  |
| K-53 | C5 R FL state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C5 R FR state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C5 R RL state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C5 R RR state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C5 max FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 max FL N_h | exact | 1065 | 1065 |  | match |  |
| K-55 | C5 max FL N_h D2/A | rel | 0.994397759103642 | 0.994397759103642 | 0 | match |  |
| K-56 | C5 max FL b_hull | m | 0.170595719192959 | 0.170595719192959 | 0 | match |  |
| K-57 | C5 max FL r_sigma | rsig | 0.00108057683723705 | 0.00108057683723705 | 0 | match |  |
| K-58 | C5 max FL f | rel | 1.02721204286649 | 1.02721204286649 | 0 | match |  |
| K-59 | C5 max FL z/f | m | 0.091141049488446 | 0.091141049488446 | 0 | match |  |
| K-59 | C5 max FL delta_grid | m | 0.00248013414557667 | 0.00248013414557667 | 0 | match |  |
| K-60 | C5 max FL dz_1n | m | 0.000437073686433346 | 0.000437073686433346 | 0 | match |  |
| K-53 | C5 max FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 max FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C5 max FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C5 max FR b_hull | m | 0.170580722595817 | 0.170580722595817 | 0 | match |  |
| K-57 | C5 max FR r_sigma | rsig | 0.00159938006325163 | 0.00159938006325163 | 0 | match |  |
| K-58 | C5 max FR f | rel | 1.01759730352209 | 1.01759730352209 | 0 | match |  |
| K-59 | C5 max FR z/f | m | 0.0757499444388606 | 0.0757499444388606 | 0 | match |  |
| K-59 | C5 max FR delta_grid | m | 0.00133299476407242 | 0.00133299476407242 | 0 | match |  |
| K-60 | C5 max FR dz_1n | m | 0.000359864328678492 | 0.000359864328678492 | 0 | match |  |
| K-53 | C5 max RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 max RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C5 max RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C5 max RL b_hull | m | 0.128875610757965 | 0.128875610757965 | 0 | match |  |
| K-57 | C5 max RL r_sigma | rsig | 0.00120132025456224 | 0.00120132025456224 | 0 | match |  |
| K-58 | C5 max RL f | rel | 0.987358727734867 | 0.987358727734867 | 0 | match |  |
| K-59 | C5 max RL z/f | m | 0.127522079645241 | 0.127522079645241 | 0 | match |  |
| K-59 | C5 max RL delta_grid | m | -0.00161204132861144 | -0.00161204132861144 | 0 | match |  |
| K-60 | C5 max RL dz_1n | m | 0.00103715023325065 | 0.00103715023325065 | 0 | match |  |
| K-53 | C5 max RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C5 max RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C5 max RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-53 | C5 e FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 e FL N_h | exact | 1065 | 1065 |  | match |  |
| K-55 | C5 e FL N_h D2/A | rel | 0.994397759103642 | 0.994397759103642 | 0 | match |  |
| K-56 | C5 e FL b_hull | m | 0.170595719192959 | 0.170595719192959 | 0 | match |  |
| K-57 | C5 e FL r_sigma | rsig | 0.00108057683723705 | 0.00108057683723705 | 0 | match |  |
| K-58 | C5 e FL f | rel | 1.02721204286649 | 1.02721204286649 | 0 | match |  |
| K-59 | C5 e FL z/f | m | 0.091141049488446 | 0.091141049488446 | 0 | match |  |
| K-59 | C5 e FL delta_grid | m | 0.00248013414557667 | 0.00248013414557667 | 0 | match |  |
| K-60 | C5 e FL dz_1n | m | 0.000437073686433346 | 0.000437073686433346 | 0 | match |  |
| K-53 | C5 e FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 e FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C5 e FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C5 e FR b_hull | m | 0.170580722595817 | 0.170580722595817 | 0 | match |  |
| K-57 | C5 e FR r_sigma | rsig | 0.00159938006325163 | 0.00159938006325163 | 0 | match |  |
| K-58 | C5 e FR f | rel | 1.01759730352209 | 1.01759730352209 | 0 | match |  |
| K-59 | C5 e FR z/f | m | 0.0757499444388606 | 0.0757499444388606 | 0 | match |  |
| K-59 | C5 e FR delta_grid | m | 0.00133299476407242 | 0.00133299476407242 | 0 | match |  |
| K-60 | C5 e FR dz_1n | m | 0.000359864328678492 | 0.000359864328678492 | 0 | match |  |
| K-53 | C5 e RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 e RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C5 e RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C5 e RL b_hull | m | 0.128875610757965 | 0.128875610757965 | 0 | match |  |
| K-57 | C5 e RL r_sigma | rsig | 0.00120132025456224 | 0.00120132025456224 | 0 | match |  |
| K-58 | C5 e RL f | rel | 0.987358727734867 | 0.987358727734867 | 0 | match |  |
| K-59 | C5 e RL z/f | m | 0.127522079645241 | 0.127522079645241 | 0 | match |  |
| K-59 | C5 e RL delta_grid | m | -0.00161204132861144 | -0.00161204132861144 | 0 | match |  |
| K-60 | C5 e RL dz_1n | m | 0.00103715023325065 | 0.00103715023325065 | 0 | match |  |
| K-53 | C5 e RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C5 e RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C5 e RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-53 | C5 end FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 end FL N_h | exact | 1065 | 1065 |  | match |  |
| K-55 | C5 end FL N_h D2/A | rel | 0.994397759103642 | 0.994397759103642 | 0 | match |  |
| K-56 | C5 end FL b_hull | m | 0.170595719192959 | 0.170595719192959 | 0 | match |  |
| K-57 | C5 end FL r_sigma | rsig | 0.00108321444106953 | 0.00108321444106953 | 0 | match |  |
| K-58 | C5 end FL f | rel | 1.02721204286649 | 1.02721204286649 | 0 | match |  |
| K-59 | C5 end FL z/f | m | 0.0911409783934075 | 0.0911409783934075 | 0 | match |  |
| K-59 | C5 end FL delta_grid | m | 0.00248013221093544 | 0.00248013221093544 | 0 | match |  |
| K-60 | C5 end FL dz_1n | m | 0.000437073345491797 | 0.000437073345491797 | 0 | match |  |
| K-53 | C5 end FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 end FR N_h | exact | 1067 | 1067 |  | match |  |
| K-55 | C5 end FR N_h D2/A | rel | 0.996265172735761 | 0.996265172735761 | 0 | match |  |
| K-56 | C5 end FR b_hull | m | 0.170580722595817 | 0.170580722595817 | 0 | match |  |
| K-57 | C5 end FR r_sigma | rsig | 0.00160131964993019 | 0.00160131964993019 | 0 | match |  |
| K-58 | C5 end FR f | rel | 1.01759730352209 | 1.01759730352209 | 0 | match |  |
| K-59 | C5 end FR z/f | m | 0.0757498698533047 | 0.0757498698533047 | 0 | match |  |
| K-59 | C5 end FR delta_grid | m | 0.00133299345156775 | 0.00133299345156775 | 0 | match |  |
| K-60 | C5 end FR dz_1n | m | 0.00035986397434581 | 0.00035986397434581 | 0 | match |  |
| K-53 | C5 end RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C5 end RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C5 end RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C5 end RL b_hull | m | 0.128875610757965 | 0.128875610757965 | 0 | match |  |
| K-57 | C5 end RL r_sigma | rsig | 0.00119886410725599 | 0.00119886410725599 | 0 | match |  |
| K-58 | C5 end RL f | rel | 0.987358727734867 | 0.987358727734867 | 0 | match |  |
| K-59 | C5 end RL z/f | m | 0.127522074977603 | 0.127522074977603 | 0 | match |  |
| K-59 | C5 end RL delta_grid | m | -0.00161204126960656 | -0.00161204126960656 | 0 | match |  |
| K-60 | C5 end RL dz_1n | m | 0.00103715019528827 | 0.00103715019528827 | 0 | match |  |
| K-53 | C5 end RR state | exact | "invalid" | "invalid" |  | match |  |
| K-54 | C5 end RR N_h | exact | 608 | 608 |  | match |  |
| K-55 | C5 end RR N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-61 | C5 dz_post_corr FL | m | 0.0136304858103483 | 0.0136304858103483 | 0 | match |  |
| K-61 | C5 dz_post_corr FR | m | 0.00166054865993182 | 0.00166054865993182 | 0 | match |  |
| K-61 | C5 dz_post_corr RL | m | 0.0114809576024607 | 0.0114809576024607 | 0 | match |  |
| K-61 | C5 dz_post_corr RR | m | null | null |  | both_NA |  |
| K-62 | C5 z_e(f_e-f_L) @b*=RL | m | 1.07925763908913e-05 | 1.07925763908913e-05 | 0 | match |  |
| K-67 | C5 m_L | m | 0.03 | 0.03 | 0 | match |  |
| K-68 | C5 m_L source | exact | "E3c10" | "E3c10" |  | match |  |
| K-69 | C5 T-14 (checked True ok True) | exact | true | true |  | match | both None counted as both_NA |
| K-80 | C5 R1-4 n_L | exact | 464 | 464 |  | match |  |
| K-80 | C5 R1-4 sum ratio | rel | 1.03539978182263 | 1.03539978182263 | 2.22e-16 | match |  |
| K-80 | C5 R1-4 W_hat FL | N | 1688.97148406731 | 1688.97148406734 | 2.91e-11 | match |  |
| K-80 | C5 R1-4 E-Fpk FL | N | 1688.97148406731 | 1688.97148406734 | 2.91e-11 | match |  |
| K-80 | C5 R1-4 stroke rate FL | m/s | 0.00507541648832877 | 0.00507541648832877 | 0 | match |  |
| K-80 | C5 R1-4 W_hat FR | N | 372.121842519133 | 372.121842519147 | 1.46e-11 | match |  |
| K-80 | C5 R1-4 E-Fpk FR | N | -145.259199580862 | -145.259199580847 | 1.46e-11 | match |  |
| K-80 | C5 R1-4 stroke rate FR | m/s | 0.00364509766651144 | 0.00364509766651144 | 0 | match |  |
| K-80 | C5 R1-4 W_hat RL | N | -840.518673621278 | -840.518673621264 | 1.46e-11 | match |  |
| K-80 | C5 R1-4 E-Fpk RL | N | -1006.82673477127 | -1006.82673477125 | 1.46e-11 | match |  |
| K-80 | C5 R1-4 stroke rate RL | m/s | 0.0185720575721293 | 0.0185720575721293 | 0 | match |  |
| K-80 | C5 R1-4 W_hat RR | N | -1220.57465296518 | -1220.57465296517 | 1.46e-11 | match |  |
| K-80 | C5 R1-4 E-Fpk RR | N | -2574.99378619019 | -2574.99378619017 | 1.46e-11 | match |  |
| K-80 | C5 R1-4 stroke rate RR | m/s | 0.0183286282761164 | 0.0183286282761164 | 0 | match |  |
| K-80 | C5 R1-4 flag | exact | false | false |  | match |  |
| K-85 | C5 T-8 leg liftoff set | exact | [] | [] |  | match |  |
| K-86 | C5 T-9 crawler retouch | exact | false | false |  | match |  |
| K-04 | C6 n_L1 | exact | 488 | 488 |  | match |  |
| K-05 | C6 n_L | exact | 488 | 488 |  | match |  |
| K-06 | C6 loc_revokes | exact | 0 | 0 |  | match |  |
| K-07 | C6 n_R | exact | null | null |  | both_NA |  |
| K-08 | C6 n_creep | exact | 536 | 536 |  | match |  |
| K-09 | C6 n_max | exact | 596 | 596 |  | match |  |
| K-10 | C6 n_end | exact | 1880 | 1880 |  | match |  |
| K-11 | C6 s_L FL | m | 0.640438416384986 | 0.640438416384986 | 0 | match |  |
| K-11 | C6 s_L FR | m | 0.640214979777015 | 0.640214979777015 | 0 | match |  |
| K-11 | C6 s_L RL | m | 0.38134628432228 | 0.38134628432228 | 0 | match |  |
| K-11 | C6 s_L RR | m | 0.381100538387375 | 0.381100538387375 | 0 | match |  |
| K-12 | C6 s_R FL | m | null | null |  | both_NA |  |
| K-12 | C6 s_R FR | m | null | null |  | both_NA |  |
| K-12 | C6 s_R RL | m | null | null |  | both_NA |  |
| K-12 | C6 s_R RR | m | null | null |  | both_NA |  |
| K-13 | C6 s_max FL | m | 0.682221032879607 | 0.682221032879607 | 0 | match |  |
| K-13 | C6 s_max FR | m | 0.682522392118792 | 0.682522392118792 | 0 | match |  |
| K-13 | C6 s_max RL | m | 0.43002200842492 | 0.43002200842492 | 0 | match |  |
| K-13 | C6 s_max RR | m | 0.429462642710937 | 0.429462642710937 | 0 | match |  |
| K-14 | C6 b* | exact | "FR" | "FR" |  | match |  |
| K-15 | C6 g | m | 0.000277607881208342 | 0.000277607881208342 | 0 | match |  |
| K-16 | C6 n_sgs | exact | 520 | 520 |  | match |  |
| K-17 | C6 n_warn_lift | exact | 520 | 520 |  | match |  |
| K-18 | C6 SGS | exact | true | true |  | match |  |
| K-19 | C6 n_e | exact | 596 | 596 |  | match |  |
| K-20 | C6 n_e_leg FL | exact | 1074 | 1074 |  | match |  |
| K-21 | C6 n_max_leg FL | exact | 1074 | 1074 |  | match |  |
| K-20 | C6 n_e_leg FR | exact | 596 | 596 |  | match |  |
| K-21 | C6 n_max_leg FR | exact | 596 | 596 |  | match |  |
| K-20 | C6 n_e_leg RL | exact | 897 | 897 |  | match |  |
| K-21 | C6 n_max_leg RL | exact | 897 | 897 |  | match |  |
| K-20 | C6 n_e_leg RR | exact | 532 | 532 |  | match |  |
| K-21 | C6 n_max_leg RR | exact | 532 | 532 |  | match |  |
| K-22 | C6 z(t_L) FL | m | 0.116840583334416 | 0.116840583334416 | 0 | match |  |
| K-22 | C6 z(t_L) FR | m | 0.11620785318021 | 0.11620785318021 | 0 | match |  |
| K-22 | C6 z(t_L) RL | m | 0.126666244945319 | 0.126666244945319 | 0 | match |  |
| K-22 | C6 z(t_L) RR | m | 0.12610692580785 | 0.12610692580785 | 0 | match |  |
| K-22 | C6 z(t_R) FL | m | null | null |  | both_NA |  |
| K-22 | C6 z(t_R) FR | m | null | null |  | both_NA |  |
| K-22 | C6 z(t_R) RL | m | null | null |  | both_NA |  |
| K-22 | C6 z(t_R) RR | m | null | null |  | both_NA |  |
| K-22 | C6 z(t_max) FL | m | 0.133103892798676 | 0.133103892798676 | 0 | match |  |
| K-22 | C6 z(t_max) FR | m | 0.119811431244505 | 0.119811431244505 | 0 | match |  |
| K-22 | C6 z(t_max) RL | m | 0.183479816944753 | 0.183479816944753 | 0 | match |  |
| K-22 | C6 z(t_max) RR | m | 0.170519001523466 | 0.170519001523466 | 0 | match |  |
| K-22 | C6 z(t_e) FL | m | 0.133103892798676 | 0.133103892798676 | 0 | match |  |
| K-22 | C6 z(t_e) FR | m | 0.119811431244505 | 0.119811431244505 | 0 | match |  |
| K-22 | C6 z(t_e) RL | m | 0.183479816944753 | 0.183479816944753 | 0 | match |  |
| K-22 | C6 z(t_e) RR | m | 0.170519001523466 | 0.170519001523466 | 0 | match |  |
| K-22 | C6 z(t_end) FL | m | 0.133103789417161 | 0.133103789417161 | 0 | match |  |
| K-22 | C6 z(t_end) FR | m | 0.119811503914742 | 0.119811503914742 | 0 | match |  |
| K-22 | C6 z(t_end) RL | m | 0.183479670327333 | 0.183479670327333 | 0 | match |  |
| K-22 | C6 z(t_end) RR | m | 0.170519016456491 | 0.170519016456491 | 0 | match |  |
| K-23 | C6 dz_post FL | m | 0.0162633094642594 | 0.0162633094642594 | 0 | match |  |
| K-23 | C6 dz_post FR | m | 0.00360357806429537 | 0.00360357806429537 | 0 | match |  |
| K-23 | C6 dz_post RL | m | 0.0568135719994342 | 0.0568135719994342 | 0 | match |  |
| K-23 | C6 dz_post RR | m | 0.0444120757156154 | 0.0444120757156154 | 0 | match |  |
| K-24 | C6 dz_post_leg_window FL | m | 0.0162632042854926 | 0.0162632042854926 | 0 | match |  |
| K-24 | C6 dz_post_leg_window FR | m | 0.00360357806429537 | 0.00360357806429537 | 0 | match |  |
| K-24 | C6 dz_post_leg_window RL | m | 0.0568134258950412 | 0.0568134258950412 | 0 | match |  |
| K-24 | C6 dz_post_leg_window RR | m | 0.0444047154605642 | 0.0444047154605642 | 0 | match |  |
| K-25 | C6 dz_L_to_max FL | m | 0.0162633094642594 | 0.0162633094642594 | 0 | match |  |
| K-25 | C6 dz_L_to_max FR | m | 0.00360357806429537 | 0.00360357806429537 | 0 | match |  |
| K-25 | C6 dz_L_to_max RL | m | 0.0568135719994342 | 0.0568135719994342 | 0 | match |  |
| K-25 | C6 dz_L_to_max RR | m | 0.0444120757156154 | 0.0444120757156154 | 0 | match |  |
| K-26 | C6 dz_max_to_R FL | m | null | null |  | both_NA |  |
| K-26 | C6 dz_max_to_R FR | m | null | null |  | both_NA |  |
| K-26 | C6 dz_max_to_R RL | m | null | null |  | both_NA |  |
| K-26 | C6 dz_max_to_R RR | m | null | null |  | both_NA |  |
| K-27 | C6 dz_L_to_R FL | m | null | null |  | both_NA |  |
| K-27 | C6 dz_L_to_R FR | m | null | null |  | both_NA |  |
| K-27 | C6 dz_L_to_R RL | m | null | null |  | both_NA |  |
| K-27 | C6 dz_L_to_R RR | m | null | null |  | both_NA |  |
| K-28 | C6 dz_R_to_end FL | m | null | null |  | both_NA |  |
| K-28 | C6 dz_R_to_end FR | m | null | null |  | both_NA |  |
| K-28 | C6 dz_R_to_end RL | m | null | null |  | both_NA |  |
| K-28 | C6 dz_R_to_end RR | m | null | null |  | both_NA |  |
| K-29 | C6 secant_L_to_R_m_per_N FL | rel | null | null |  | both_NA |  |
| K-29 | C6 secant_L_to_R_m_per_N FR | rel | null | null |  | both_NA |  |
| K-29 | C6 secant_L_to_R_m_per_N RL | rel | null | null |  | both_NA |  |
| K-29 | C6 secant_L_to_R_m_per_N RR | rel | null | null |  | both_NA |  |
| K-30 | C6 delta_os FL | m | null | null |  | both_NA |  |
| K-30 | C6 delta_os FR | m | null | null |  | both_NA |  |
| K-30 | C6 delta_os RL | m | null | null |  | both_NA |  |
| K-30 | C6 delta_os RR | m | null | null |  | both_NA |  |
| K-31 | C6 t_max - t_L | s | 10.8 | 10.8 | 0 | match |  |
| K-32 | C6 s_hat P-A @b*=FR | m | 0.704812586944557 | 0.704812586944557 | 0 | match |  |
| K-33 | C6 e P-A @b*=FR | m | -0.0222901948257656 | -0.0222901948257656 | 0 | match |  |
| K-34 | C6 e P-A @b=FL | m | -0.0230585346937779 | -0.0230585346937779 | 0 | match |  |
| K-32 | C6 s_hat P-B @b*=FR | m | 0.704812586944557 | 0.704812586944557 | 0 | match |  |
| K-33 | C6 e P-B @b*=FR | m | -0.0222901948257656 | -0.0222901948257656 | 0 | match |  |
| K-34 | C6 e P-B @b=FL | m | -0.0230585346937779 | -0.0230585346937779 | 0 | match |  |
| K-32 | C6 s_hat P-D @b*=FR | m | 0.704812586944557 | 0.704812586944557 | 0 | match |  |
| K-33 | C6 e P-D @b*=FR | m | -0.0222901948257656 | -0.0222901948257656 | 0 | match |  |
| K-34 | C6 e P-D @b=FL | m | -0.0230585346937779 | -0.0230585346937779 | 0 | match |  |
| K-32 | C6 s_hat P-G @b*=FR | m | 0.661035935852897 | 0.661035935852897 | 0 | match |  |
| K-33 | C6 e P-G @b*=FR | m | 0.0214864562658948 | 0.0214864562658948 | 0 | match |  |
| K-34 | C6 e P-G @b=FL | m | 0.0207181163978825 | 0.0207181163978825 | 0 | match |  |
| K-32 | C6 s_hat P-C @b*=FR | m | 0.724667374801048 | 0.724667374801048 | 0 | match |  |
| K-33 | C6 e P-C @b*=FR | m | -0.0421449826822565 | -0.0421449826822565 | 0 | match |  |
| K-34 | C6 e P-C @b=FL | m | -0.0429133225502689 | -0.0429133225502689 | 0 | match |  |
| K-35 | C6 lower bound (M-6) vs sgs | exact | true | true |  | match |  |
| K-36 | C6 P-G k* | exact | "RR" | "RR" |  | match |  |
| K-37 | C6 rho_k* | m | 0.00651147035797358 | 0.00651147035797358 | 0 | match |  |
| K-38 | C6 Zhat_k* | m | 0.0372644495958286 | 0.0372644495958286 | 0 | match |  |
| K-39 | C6 phi_L | rad | -9.19867128181699e-05 | -9.19867128181699e-05 | 0 | match |  |
| K-39 | C6 theta_L | rad | -0.00360713272156696 | -0.00360713272156696 | 0 | match |  |
| K-40 | C6 c_hat(t_L) | m | 0.0070065797852992 | 0.0070065797852992 | 0 | match |  |
| K-41 | C6 c_hat_corner RR | m | 0.00700731092315743 | 0.00700731092315743 | 0 | match |  |
| K-43 | C6 rho RR | m | 0.00651147035797358 | 0.00651147035797358 | 0 | match |  |
| K-41 | C6 c_hat_corner RL | m | 0.0070065797852992 | 0.0070065797852992 | 0 | match |  |
| K-43 | C6 rho RL | m | 0.00676277805739282 | 0.00676277805739282 | 0 | match |  |
| K-41 | C6 c_hat_corner FR | m | 0.208373405610302 | 0.208373405610302 | 0 | match |  |
| K-43 | C6 rho FR | m | -0.00677720658827909 | -0.00677720658827909 | 0 | match |  |
| K-41 | C6 c_hat_corner FL | m | 0.208372674472444 | 0.208372674472444 | 0 | match |  |
| K-43 | C6 rho FL | m | -0.00652589888885985 | -0.00652589888885985 | 0 | match |  |
| K-42 | C6 ds_geo FL | m | -0.00815226902630159 | -0.00815226902630159 | 0 | match |  |
| K-44 | C6 W_hat FL | N | -446.596540197046 | -446.596540197046 | 0 | match |  |
| K-44 | C6 E_hat FL | N | 130112.684217084 | 130112.684217084 | 0 | match |  |
| K-44 | C6 F_pk FL | N | 131422.433341631 | 131422.433341631 | 0 | match |  |
| K-42 | C6 ds_geo FR | m | -0.00839581304715898 | -0.00839581304715898 | 0 | match |  |
| K-44 | C6 W_hat FR | N | -4257.72316964848 | -4257.72316964848 | 0 | match |  |
| K-44 | C6 E_hat FR | N | 127916.83690823 | 127916.83690823 | 0 | match |  |
| K-44 | C6 F_pk FR | N | 132614.579399629 | 132614.579399629 | 0 | match |  |
| K-42 | C6 ds_geo RL | m | 0.00932726251822548 | 0.00932726251822548 | 0 | match |  |
| K-44 | C6 W_hat RL | N | 3141.35279976524 | 3141.35279976524 | 0 | match |  |
| K-44 | C6 E_hat RL | N | 79430.6862451971 | 79430.6862451971 | 0 | match |  |
| K-44 | C6 F_pk RL | N | 76336.8500343319 | 76336.8500343319 | 0 | match |  |
| K-42 | C6 ds_geo RR | m | 0.00910550095096344 | 0.00910550095096344 | 0 | match |  |
| K-44 | C6 W_hat RR | N | 1562.96691008031 | 1562.96691008031 | 0 | match |  |
| K-44 | C6 E_hat RR | N | 77431.1993125697 | 77431.1993125697 | 0 | match |  |
| K-44 | C6 F_pk RR | N | 76414.8695244144 | 76414.8695244144 | 0 | match |  |
| K-45 | C6 sum F / sum W_static | rel | 1.10172460431184 | 1.10172460431184 | 0 | match |  |
| K-46 | C6 E3c10 events | exact | ["INFO_LOC_CLEARANCE_MARGIN:80"] | ["INFO_LOC_CLEARANCE_MARGIN:80"] |  | match |  |
| K-47 | C6 R4c30 count | exact | 0 | 0 |  | match |  |
| K-48 | C6 M-8 loc_revoked | exact | 0 | 0 |  | match |  |
| K-49 | C6 M-8 sgs>0 | exact | true | true |  | match |  |
| K-50 | C6 pair diff s_max(b*) | m | 0.00493177439484149 | 0.00493177439484149 | 0 | match |  |
| K-51 | C6 pair diff dz_post(b*) | m | 0.00362030862454296 | 0.00362030862454296 | 0 | match |  |
| K-52 | C6 harness s_max spread min (n=4) | m | 0.677513563193588 | 0.677513563193588 | 0 | match |  |
| K-52 | C6 harness s_max spread max (n=4) | m | 0.677818858388749 | 0.677818858388749 | 0 | match |  |
| K-53 | C6 L FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 L FL N_h | exact | 1074 | 1074 |  | match |  |
| K-55 | C6 L FL N_h D2/A | rel | 1.00280112044818 | 1.00280112044818 | 0 | match |  |
| K-56 | C6 L FL b_hull | m | 0.171299930880114 | 0.171299930880114 | 0 | match |  |
| K-57 | C6 L FL r_sigma | rsig | 7.8243076481818e-06 | 7.8243076481818e-06 | 0 | match |  |
| K-58 | C6 L FL f | rel | 0.985959132313336 | 0.985959132313336 | 0 | match |  |
| K-59 | C6 L FL z/f | m | 0.118504489187372 | 0.118504489187372 | 0 | match |  |
| K-59 | C6 L FL delta_grid | m | -0.00166390585295557 | -0.00166390585295557 | 0 | match |  |
| K-60 | C6 L FL dz_1n | m | 0.000545474245258712 | 0.000545474245258712 | 0 | match |  |
| K-53 | C6 L FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 L FR N_h | exact | 1075 | 1075 |  | match |  |
| K-55 | C6 L FR N_h D2/A | rel | 1.00373482726424 | 1.00373482726424 | 0 | match |  |
| K-56 | C6 L FR b_hull | m | 0.171357585730418 | 0.171357585730418 | 0 | match |  |
| K-57 | C6 L FR r_sigma | rsig | 0.000456882039602323 | 0.000456882039602323 | 0 | match |  |
| K-58 | C6 L FR f | rel | 0.98146878161519 | 0.98146878161519 | 0 | match |  |
| K-59 | C6 L FR z/f | m | 0.118401986244502 | 0.118401986244502 | 0 | match |  |
| K-59 | C6 L FR delta_grid | m | -0.00219413306429215 | -0.00219413306429215 | 0 | match |  |
| K-60 | C6 L FR dz_1n | m | 0.000542520322970167 | 0.000542520322970167 | 0 | match |  |
| K-53 | C6 L RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 L RL N_h | exact | 606 | 606 |  | match |  |
| K-55 | C6 L RL N_h D2/A | rel | 0.99835255354201 | 0.99835255354201 | 1.11e-16 | match |  |
| K-56 | C6 L RL b_hull | m | 0.128524629629069 | 0.128524629629069 | 0 | match |  |
| K-57 | C6 L RL r_sigma | rsig | 0.00169241423926825 | 0.00169241423926825 | 0 | match |  |
| K-58 | C6 L RL f | rel | 1.00281683954224 | 1.00281683954225 | 4.44e-16 | match |  |
| K-59 | C6 L RL z/f | m | 0.126310448678882 | 0.126310448678882 | 5.55e-17 | match |  |
| K-59 | C6 L RL delta_grid | m | 0.00035579626643735 | 0.000355796266437406 | 5.62e-17 | match |  |
| K-60 | C6 L RL dz_1n | m | 0.00104337928291037 | 0.00104337928291037 | 0 | match |  |
| K-53 | C6 L RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 L RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C6 L RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C6 L RR b_hull | m | 0.128755812510712 | 0.128755812510712 | 0 | match |  |
| K-57 | C6 L RR r_sigma | rsig | 0.00168904303841944 | 0.00168904303841944 | 0 | match |  |
| K-58 | C6 L RR f | rel | 0.995199956809847 | 0.995199956809847 | 0 | match |  |
| K-59 | C6 L RR z/f | m | 0.126715164068225 | 0.126715164068225 | 0 | match |  |
| K-59 | C6 L RR delta_grid | m | -0.000608238260374762 | -0.000608238260374762 | 0 | match |  |
| K-60 | C6 L RR dz_1n | m | 0.00103877204125083 | 0.00103877204125083 | 0 | match |  |
| K-53 | C6 R FL state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C6 R FR state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C6 R RL state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C6 R RR state | exact | "no_record" | "no_record" |  | match |  |
| K-53 | C6 max FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 max FL N_h | exact | 1076 | 1076 |  | match |  |
| K-55 | C6 max FL N_h D2/A | rel | 1.0046685340803 | 1.0046685340803 | 0 | match |  |
| K-56 | C6 max FL b_hull | m | 0.171458376729704 | 0.171458376729704 | 0 | match |  |
| K-57 | C6 max FL r_sigma | rsig | 0.000551178130710214 | 0.000551178130710214 | 0 | match |  |
| K-58 | C6 max FL f | rel | 0.977067759150139 | 0.977067759150139 | 0 | match |  |
| K-59 | C6 max FL z/f | m | 0.136227903901415 | 0.136227903901415 | 0 | match |  |
| K-59 | C6 max FL delta_grid | m | -0.00312401110273898 | -0.00312401110273898 | 0 | match |  |
| K-60 | C6 max FL dz_1n | m | 0.000621400059751053 | 0.000621400059751053 | 1.08e-19 | match |  |
| K-53 | C6 max FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 max FR N_h | exact | 1073 | 1073 |  | match |  |
| K-55 | C6 max FR N_h D2/A | rel | 1.00186741363212 | 1.00186741363212 | 0 | match |  |
| K-56 | C6 max FR b_hull | m | 0.171386525123097 | 0.171386525123097 | 0 | match |  |
| K-57 | C6 max FR r_sigma | rsig | 0.00229866097851526 | 0.00229866097851526 | 0 | match |  |
| K-58 | C6 max FR f | rel | 0.99069395313148 | 0.99069395313148 | 0 | match |  |
| K-59 | C6 max FR z/f | m | 0.120936875475816 | 0.120936875475816 | 0 | match |  |
| K-59 | C6 max FR delta_grid | m | -0.00112544423131028 | -0.00112544423131028 | 0 | match |  |
| K-60 | C6 max FR dz_1n | m | 0.000559343749974348 | 0.000559343749974347 | 1.08e-19 | match |  |
| K-53 | C6 max RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 max RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C6 max RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C6 max RL b_hull | m | 0.128739853808863 | 0.128739853808863 | 0 | match |  |
| K-57 | C6 max RL r_sigma | rsig | 0.000605716433120749 | 0.000605716433120749 | 0 | match |  |
| K-58 | C6 max RL f | rel | 0.987000479757732 | 0.987000479757732 | 0 | match |  |
| K-59 | C6 max RL z/f | m | 0.185896380708741 | 0.185896380708741 | 0 | match |  |
| K-59 | C6 max RL delta_grid | m | -0.0024165637639877 | -0.0024165637639877 | 0 | match |  |
| K-60 | C6 max RL dz_1n | m | 0.00151136587269154 | 0.00151136587269154 | 2.17e-19 | match |  |
| K-53 | C6 max RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 max RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C6 max RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C6 max RR b_hull | m | 0.128816064538277 | 0.128816064538277 | 0 | match |  |
| K-57 | C6 max RR r_sigma | rsig | 0.000938660456333394 | 0.000938660456333394 | 0 | match |  |
| K-58 | C6 max RR f | rel | 0.995360312484106 | 0.995360312484106 | 0 | match |  |
| K-59 | C6 max RR z/f | m | 0.171313844227829 | 0.171313844227829 | 0 | match |  |
| K-59 | C6 max RR delta_grid | m | -0.000794842704363731 | -0.000794842704363731 | 0 | match |  |
| K-60 | C6 max RR dz_1n | m | 0.00140460462539922 | 0.00140460462539922 | 0 | match |  |
| K-53 | C6 e FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 e FL N_h | exact | 1076 | 1076 |  | match |  |
| K-55 | C6 e FL N_h D2/A | rel | 1.0046685340803 | 1.0046685340803 | 0 | match |  |
| K-56 | C6 e FL b_hull | m | 0.171458376729704 | 0.171458376729704 | 0 | match |  |
| K-57 | C6 e FL r_sigma | rsig | 0.000551178130710214 | 0.000551178130710214 | 0 | match |  |
| K-58 | C6 e FL f | rel | 0.977067759150139 | 0.977067759150139 | 0 | match |  |
| K-59 | C6 e FL z/f | m | 0.136227903901415 | 0.136227903901415 | 0 | match |  |
| K-59 | C6 e FL delta_grid | m | -0.00312401110273898 | -0.00312401110273898 | 0 | match |  |
| K-60 | C6 e FL dz_1n | m | 0.000621400059751053 | 0.000621400059751053 | 1.08e-19 | match |  |
| K-53 | C6 e FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 e FR N_h | exact | 1073 | 1073 |  | match |  |
| K-55 | C6 e FR N_h D2/A | rel | 1.00186741363212 | 1.00186741363212 | 0 | match |  |
| K-56 | C6 e FR b_hull | m | 0.171386525123097 | 0.171386525123097 | 0 | match |  |
| K-57 | C6 e FR r_sigma | rsig | 0.00229866097851526 | 0.00229866097851526 | 0 | match |  |
| K-58 | C6 e FR f | rel | 0.99069395313148 | 0.99069395313148 | 0 | match |  |
| K-59 | C6 e FR z/f | m | 0.120936875475816 | 0.120936875475816 | 0 | match |  |
| K-59 | C6 e FR delta_grid | m | -0.00112544423131028 | -0.00112544423131028 | 0 | match |  |
| K-60 | C6 e FR dz_1n | m | 0.000559343749974348 | 0.000559343749974347 | 1.08e-19 | match |  |
| K-53 | C6 e RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 e RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C6 e RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C6 e RL b_hull | m | 0.128739853808863 | 0.128739853808863 | 0 | match |  |
| K-57 | C6 e RL r_sigma | rsig | 0.000605716433120749 | 0.000605716433120749 | 0 | match |  |
| K-58 | C6 e RL f | rel | 0.987000479757732 | 0.987000479757732 | 0 | match |  |
| K-59 | C6 e RL z/f | m | 0.185896380708741 | 0.185896380708741 | 0 | match |  |
| K-59 | C6 e RL delta_grid | m | -0.0024165637639877 | -0.0024165637639877 | 0 | match |  |
| K-60 | C6 e RL dz_1n | m | 0.00151136587269154 | 0.00151136587269154 | 2.17e-19 | match |  |
| K-53 | C6 e RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 e RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C6 e RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C6 e RR b_hull | m | 0.128816064538277 | 0.128816064538277 | 0 | match |  |
| K-57 | C6 e RR r_sigma | rsig | 0.000938660456333394 | 0.000938660456333394 | 0 | match |  |
| K-58 | C6 e RR f | rel | 0.995360312484106 | 0.995360312484106 | 0 | match |  |
| K-59 | C6 e RR z/f | m | 0.171313844227829 | 0.171313844227829 | 0 | match |  |
| K-59 | C6 e RR delta_grid | m | -0.000794842704363731 | -0.000794842704363731 | 0 | match |  |
| K-60 | C6 e RR dz_1n | m | 0.00140460462539922 | 0.00140460462539922 | 0 | match |  |
| K-53 | C6 end FL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 end FL N_h | exact | 1076 | 1076 |  | match |  |
| K-55 | C6 end FL N_h D2/A | rel | 1.0046685340803 | 1.0046685340803 | 0 | match |  |
| K-56 | C6 end FL b_hull | m | 0.171458376729704 | 0.171458376729704 | 0 | match |  |
| K-57 | C6 end FL r_sigma | rsig | 0.000554232545310865 | 0.000554232545310865 | 0 | match |  |
| K-58 | C6 end FL f | rel | 0.977067759150139 | 0.977067759150139 | 0 | match |  |
| K-59 | C6 end FL z/f | m | 0.136227798093487 | 0.136227798093487 | 0 | match |  |
| K-59 | C6 end FL delta_grid | m | -0.00312400867632611 | -0.00312400867632611 | 0 | match |  |
| K-60 | C6 end FL dz_1n | m | 0.00062139957711093 | 0.00062139957711093 | 0 | match |  |
| K-53 | C6 end FR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 end FR N_h | exact | 1073 | 1073 |  | match |  |
| K-55 | C6 end FR N_h D2/A | rel | 1.00186741363212 | 1.00186741363212 | 0 | match |  |
| K-56 | C6 end FR b_hull | m | 0.171386525123097 | 0.171386525123097 | 0 | match |  |
| K-57 | C6 end FR r_sigma | rsig | 0.00229367653328335 | 0.00229367653328335 | 0 | match |  |
| K-58 | C6 end FR f | rel | 0.99069395313148 | 0.99069395313148 | 0 | match |  |
| K-59 | C6 end FR z/f | m | 0.120936948828678 | 0.120936948828678 | 0 | match |  |
| K-59 | C6 end FR delta_grid | m | -0.00112544491393545 | -0.00112544491393545 | 0 | match |  |
| K-60 | C6 end FR dz_1n | m | 0.000559344089237827 | 0.000559344089237827 | 1.08e-19 | match |  |
| K-53 | C6 end RL state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 end RL N_h | exact | 608 | 608 |  | match |  |
| K-55 | C6 end RL N_h D2/A | rel | 1.00164744645799 | 1.00164744645799 | 0 | match |  |
| K-56 | C6 end RL b_hull | m | 0.128739853808863 | 0.128739853808863 | 0 | match |  |
| K-57 | C6 end RL r_sigma | rsig | 0.000612109102465094 | 0.000612109102465094 | 0 | match |  |
| K-58 | C6 end RL f | rel | 0.987000479757732 | 0.987000479757732 | 0 | match |  |
| K-59 | C6 end RL z/f | m | 0.185896232160262 | 0.185896232160262 | 0 | match |  |
| K-59 | C6 end RL delta_grid | m | -0.00241656183292873 | -0.00241656183292873 | 0 | match |  |
| K-60 | C6 end RL dz_1n | m | 0.00151136466496979 | 0.00151136466496979 | 0 | match |  |
| K-53 | C6 end RR state | exact | "valid" | "valid" |  | match |  |
| K-54 | C6 end RR N_h | exact | 607 | 607 |  | match |  |
| K-55 | C6 end RR N_h D2/A | rel | 1 | 1 | 0 | match |  |
| K-56 | C6 end RR b_hull | m | 0.128816064538277 | 0.128816064538277 | 0 | match |  |
| K-57 | C6 end RR r_sigma | rsig | 0.000933429375198855 | 0.000933429375198855 | 0 | match |  |
| K-58 | C6 end RR f | rel | 0.995360312484106 | 0.995360312484106 | 0 | match |  |
| K-59 | C6 end RR z/f | m | 0.171313859230462 | 0.171313859230462 | 0 | match |  |
| K-59 | C6 end RR delta_grid | m | -0.000794842773971261 | -0.000794842773971261 | 0 | match |  |
| K-60 | C6 end RR dz_1n | m | 0.00140460474840602 | 0.00140460474840602 | 0 | match |  |
| K-61 | C6 dz_post_corr FL | m | 0.0177234147140428 | 0.0177234147140428 | 0 | match |  |
| K-61 | C6 dz_post_corr FR | m | 0.00253488923131351 | 0.00253488923131351 | 0 | match |  |
| K-61 | C6 dz_post_corr RL | m | 0.0595859320298592 | 0.0595859320298593 | 5.55e-17 | match |  |
| K-61 | C6 dz_post_corr RR | m | 0.0445986801596044 | 0.0445986801596044 | 0 | match |  |
| K-67 | C6 m_L | m | 0.03 | 0.03 | 0 | match |  |
| K-68 | C6 m_L source | exact | "E3c10" | "E3c10" |  | match |  |
| K-69 | C6 T-14 (checked True ok True) | exact | true | true |  | match | both None counted as both_NA |
| K-80 | C6 R1-4 n_L | exact | 488 | 488 |  | match |  |
| K-80 | C6 R1-4 sum ratio | rel | 1.10172460431184 | 1.10172460431184 | 0 | match |  |
| K-80 | C6 R1-4 W_hat FL | N | -446.596540197046 | -446.596540197046 | 0 | match |  |
| K-80 | C6 R1-4 E-Fpk FL | N | -1309.74912454702 | -1309.74912454702 | 0 | match |  |
| K-80 | C6 R1-4 stroke rate FL | m/s | 0.0104028306918125 | 0.0104028306918125 | 0 | match |  |
| K-80 | C6 R1-4 W_hat FR | N | -4257.72316964848 | -4257.72316964848 | 0 | match |  |
| K-80 | C6 R1-4 E-Fpk FR | N | -4697.74249139846 | -4697.74249139846 | 0 | match |  |
| K-80 | C6 R1-4 stroke rate FR | m/s | 0.0107005743090205 | 0.0107005743090205 | 0 | match |  |
| K-80 | C6 R1-4 W_hat RL | N | 3141.35279976524 | 3141.35279976524 | 0 | match |  |
| K-80 | C6 R1-4 E-Fpk RL | N | 3093.83621086524 | 3093.83621086524 | 0 | match |  |
| K-80 | C6 R1-4 stroke rate RL | m/s | 0.00525810496024293 | 0.00525810496024293 | 0 | match |  |
| K-80 | C6 R1-4 W_hat RR | N | 1562.96691008031 | 1562.96691008031 | 0 | match |  |
| K-80 | C6 R1-4 E-Fpk RR | N | 1016.3297881553 | 1016.3297881553 | 0 | match |  |
| K-80 | C6 R1-4 stroke rate RR | m/s | 0.00586904801144594 | 0.00586904801144594 | 0 | match |  |
| K-80 | C6 R1-4 flag | exact | false | false |  | match |  |
| K-85 | C6 T-8 leg liftoff set | exact | [] | [] |  | match |  |
| K-86 | C6 T-9 crawler retouch | exact | false | false |  | match |  |
| K-63 | shadow usable | exact | true | true |  | match |  |
| K-64 | H-P\|C1\|V0\|e0.002 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C1\|V0\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|V0\|e0.002 loc0 n_P | exact | 307 | 307 |  | match |  |
| K-64 | H-P\|C1\|V0\|e0.002 loc0 n_L | exact | 316 | 316 |  | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc0 c_min_tP_m | m | 0.0438302097554253 | 0.0438302097554253 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc0 c_hat_m | m | 0.00657192831188014 | 0.00657192831188014 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc0 c_hat_A_m | m | 0.00657192831188014 | 0.00657192831188014 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C1\|V0\|e0.002 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|V0\|e0.002 loc1 n_P | exact | 329 | 329 |  | match |  |
| K-64 | H-P\|C1\|V0\|e0.002 loc1 n_L | exact | 338 | 338 |  | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc1 c_min_tP_m | m | 0.0678503155832424 | 0.0678503155832424 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc1 c_hat_m | m | 0.00957539460455625 | 0.00957539460455625 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc1 c_hat_A_m | m | 0.00957539460455625 | 0.00957539460455625 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0.002 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C1\|V0\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C1\|V0\|e0 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C1\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|V0\|e0 loc0 n_P | exact | 307 | 307 |  | match |  |
| K-64 | H-P\|C1\|V0\|e0 loc0 n_L | exact | 316 | 316 |  | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc0 c_min_tP_m | m | 0.0436299022857449 | 0.0436299022857449 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc0 c_hat_m | m | 0.00653200886781735 | 0.00653200886781735 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc0 c_hat_A_m | m | 0.00653200886781735 | 0.00653200886781735 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C1\|V0\|e0 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|V0\|e0 loc1 n_P | exact | 329 | 329 |  | match |  |
| K-64 | H-P\|C1\|V0\|e0 loc1 n_L | exact | 338 | 338 |  | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc1 c_min_tP_m | m | 0.0678949368897661 | 0.0678949368897661 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc1 c_hat_m | m | 0.00965882142064589 | 0.00965882142064589 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc1 c_hat_A_m | m | 0.00965882142064589 | 0.00965882142064589 | 0 | match |  |
| K-65 | H-P\|C1\|V0\|e0 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C1\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C2\|V0\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C2\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C2\|V0\|e0 loc0 n_P | exact | 307 | 307 |  | match |  |
| K-64 | H-P\|C2\|V0\|e0 loc0 n_L | exact | 315 | 315 |  | match |  |
| K-65 | H-P\|C2\|V0\|e0 loc0 c_min_tP_m | m | 0.044012437972379 | 0.044012437972379 | 0 | match |  |
| K-65 | H-P\|C2\|V0\|e0 loc0 c_hat_m | m | 0.00582323631641035 | 0.00582323631641035 | 0 | match |  |
| K-65 | H-P\|C2\|V0\|e0 loc0 c_hat_A_m | m | 0.00582323631641035 | 0.00582323631641035 | 0 | match |  |
| K-65 | H-P\|C2\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C2\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C2\|V0\|e0.002 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C2\|V0\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C2\|V0\|e0.002 loc0 n_P | exact | 308 | 308 |  | match |  |
| K-64 | H-P\|C2\|V0\|e0.002 loc0 n_L | exact | 316 | 316 |  | match |  |
| K-65 | H-P\|C2\|V0\|e0.002 loc0 c_min_tP_m | m | 0.0453672049491489 | 0.0453672049491489 | 0 | match |  |
| K-65 | H-P\|C2\|V0\|e0.002 loc0 c_hat_m | m | 0.00580262256162412 | 0.00580262256162412 | 0 | match |  |
| K-65 | H-P\|C2\|V0\|e0.002 loc0 c_hat_A_m | m | 0.00580262256162412 | 0.00580262256162412 | 0 | match |  |
| K-65 | H-P\|C2\|V0\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C2\|V0\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C3\|V0\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C3\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C3\|V0\|e0 loc0 n_P | exact | 307 | 307 |  | match |  |
| K-64 | H-P\|C3\|V0\|e0 loc0 n_L | exact | 315 | 315 |  | match |  |
| K-65 | H-P\|C3\|V0\|e0 loc0 c_min_tP_m | m | 0.0444720445424176 | 0.0444720445424176 | 0 | match |  |
| K-65 | H-P\|C3\|V0\|e0 loc0 c_hat_m | m | 0.00557718104952909 | 0.00557718104952909 | 0 | match |  |
| K-65 | H-P\|C3\|V0\|e0 loc0 c_hat_A_m | m | 0.00557718104952909 | 0.00557718104952909 | 0 | match |  |
| K-65 | H-P\|C3\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C3\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C1\|VB\|e0 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C1\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|VB\|e0 loc0 n_P | exact | 324 | 324 |  | match |  |
| K-64 | H-P\|C1\|VB\|e0 loc0 n_L | exact | 333 | 333 |  | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc0 c_min_tP_m | m | 0.0438475200484984 | 0.0438475200484984 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc0 c_hat_m | m | 0.00657323030111678 | 0.00657323030111678 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc0 c_hat_A_m | m | 0.00657323030111678 | 0.00657323030111678 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C1\|VB\|e0 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|VB\|e0 loc1 n_P | exact | 346 | 346 |  | match |  |
| K-64 | H-P\|C1\|VB\|e0 loc1 n_L | exact | 355 | 355 |  | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc1 c_min_tP_m | m | 0.0678576075439161 | 0.0678576075439161 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc1 c_hat_m | m | 0.00957167175189344 | 0.00957167175189344 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc1 c_hat_A_m | m | 0.00957167175189344 | 0.00957167175189344 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C1\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C3\|V0\|e0.002 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C3\|V0\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C3\|V0\|e0.002 loc0 n_P | exact | 307 | 307 |  | match |  |
| K-64 | H-P\|C3\|V0\|e0.002 loc0 n_L | exact | 315 | 315 |  | match |  |
| K-65 | H-P\|C3\|V0\|e0.002 loc0 c_min_tP_m | m | 0.0448866100877936 | 0.0448866100877936 | 0 | match |  |
| K-65 | H-P\|C3\|V0\|e0.002 loc0 c_hat_m | m | 0.00545306222042341 | 0.00545306222042341 | 0 | match |  |
| K-65 | H-P\|C3\|V0\|e0.002 loc0 c_hat_A_m | m | 0.00545306222042341 | 0.00545306222042341 | 0 | match |  |
| K-65 | H-P\|C3\|V0\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C3\|V0\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C2\|VB\|e0.002 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C2\|VB\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C2\|VB\|e0.002 loc0 n_P | exact | 326 | 326 |  | match |  |
| K-64 | H-P\|C2\|VB\|e0.002 loc0 n_L | exact | 334 | 334 |  | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc0 c_min_tP_m | m | 0.0431195461548852 | 0.0431195461548852 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc0 c_hat_m | m | 0.00587537734572785 | 0.00587537734572785 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc0 c_hat_A_m | m | 0.00587537734572785 | 0.00587537734572785 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C2\|VB\|e0.002 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C2\|VB\|e0.002 loc1 n_P | exact | 347 | 347 |  | match |  |
| K-64 | H-P\|C2\|VB\|e0.002 loc1 n_L | exact | 356 | 356 |  | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc1 c_min_tP_m | m | 0.0663467407030722 | 0.0663467407030722 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc1 c_hat_m | m | 0.00951019028919009 | 0.00951019028919009 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc1 c_hat_A_m | m | 0.00951019028919009 | 0.00951019028919009 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0.002 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C2\|VB\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C1\|VB\|e0.002 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C1\|VB\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|VB\|e0.002 loc0 n_P | exact | 324 | 324 |  | match |  |
| K-64 | H-P\|C1\|VB\|e0.002 loc0 n_L | exact | 333 | 333 |  | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc0 c_min_tP_m | m | 0.0437702807550309 | 0.0437702807550309 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc0 c_hat_m | m | 0.00658506712859297 | 0.00658506712859297 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc0 c_hat_A_m | m | 0.00658506712859297 | 0.00658506712859297 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C1\|VB\|e0.002 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C1\|VB\|e0.002 loc1 n_P | exact | 346 | 346 |  | match |  |
| K-64 | H-P\|C1\|VB\|e0.002 loc1 n_L | exact | 355 | 355 |  | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc1 c_min_tP_m | m | 0.0676680558796825 | 0.0676680558796825 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc1 c_hat_m | m | 0.00954633612527811 | 0.00954633612527811 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc1 c_hat_A_m | m | 0.00954633612527811 | 0.00954633612527811 | 0 | match |  |
| K-65 | H-P\|C1\|VB\|e0.002 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C1\|VB\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C2\|VB\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C2\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C2\|VB\|e0 loc0 n_P | exact | 325 | 325 |  | match |  |
| K-64 | H-P\|C2\|VB\|e0 loc0 n_L | exact | 333 | 333 |  | match |  |
| K-65 | H-P\|C2\|VB\|e0 loc0 c_min_tP_m | m | 0.0437867102112088 | 0.0437867102112088 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0 loc0 c_hat_m | m | 0.00587284824256828 | 0.00587284824256828 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0 loc0 c_hat_A_m | m | 0.00587284824256828 | 0.00587284824256828 | 0 | match |  |
| K-65 | H-P\|C2\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C2\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|V0\|e0.002 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C4\|V0\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|V0\|e0.002 loc0 n_P | exact | 312 | 312 |  | match |  |
| K-64 | H-P\|C4\|V0\|e0.002 loc0 n_L | exact | 320 | 320 |  | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc0 c_min_tP_m | m | 0.0247586367976735 | 0.0247586367976735 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc0 c_hat_m | m | 0.00425675057184693 | 0.00425675057184693 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc0 c_hat_A_m | m | 0.00425675057184693 | 0.00425675057184693 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|V0\|e0.002 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|V0\|e0.002 loc1 n_P | exact | 329 | 329 |  | match |  |
| K-64 | H-P\|C4\|V0\|e0.002 loc1 n_L | exact | 335 | 335 |  | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc1 c_min_tP_m | m | 0.0385980647015958 | 0.0385980647015958 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc1 c_hat_m | m | 0.00857255045093752 | 0.00857255045093752 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc1 c_hat_A_m | m | 0.00857255045093752 | 0.00857255045093752 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0.002 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C4\|V0\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|V0\|e0 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C4\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|V0\|e0 loc0 n_P | exact | 310 | 310 |  | match |  |
| K-64 | H-P\|C4\|V0\|e0 loc0 n_L | exact | 318 | 318 |  | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc0 c_min_tP_m | m | 0.0243522793383395 | 0.0243522793383395 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc0 c_hat_m | m | 0.00423900383501485 | 0.00423900383501485 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc0 c_hat_A_m | m | 0.00423900383501485 | 0.00423900383501485 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|V0\|e0 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|V0\|e0 loc1 n_P | exact | 327 | 327 |  | match |  |
| K-64 | H-P\|C4\|V0\|e0 loc1 n_L | exact | 333 | 333 |  | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc1 c_min_tP_m | m | 0.0380489298742182 | 0.0380489298742182 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc1 c_hat_m | m | 0.00845616767613921 | 0.00845616767613921 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc1 c_hat_A_m | m | 0.00845616767613921 | 0.00845616767613921 | 0 | match |  |
| K-65 | H-P\|C4\|V0\|e0 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C4\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C3\|VB\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C3\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C3\|VB\|e0 loc0 n_P | exact | 327 | 327 |  | match |  |
| K-64 | H-P\|C3\|VB\|e0 loc0 n_L | exact | 335 | 335 |  | match |  |
| K-65 | H-P\|C3\|VB\|e0 loc0 c_min_tP_m | m | 0.0436703482224916 | 0.0436703482224916 | 0 | match |  |
| K-65 | H-P\|C3\|VB\|e0 loc0 c_hat_m | m | 0.00574602392483192 | 0.00574602392483192 | 0 | match |  |
| K-65 | H-P\|C3\|VB\|e0 loc0 c_hat_A_m | m | 0.00574602392483192 | 0.00574602392483192 | 0 | match |  |
| K-65 | H-P\|C3\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C3\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C3\|VB\|e0.002 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C3\|VB\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C3\|VB\|e0.002 loc0 n_P | exact | 324 | 324 |  | match |  |
| K-64 | H-P\|C3\|VB\|e0.002 loc0 n_L | exact | 332 | 332 |  | match |  |
| K-65 | H-P\|C3\|VB\|e0.002 loc0 c_min_tP_m | m | 0.0448466529174867 | 0.0448466529174867 | 0 | match |  |
| K-65 | H-P\|C3\|VB\|e0.002 loc0 c_hat_m | m | 0.00550060909976158 | 0.00550060909976158 | 0 | match |  |
| K-65 | H-P\|C3\|VB\|e0.002 loc0 c_hat_A_m | m | 0.00550060909976158 | 0.00550060909976158 | 0 | match |  |
| K-65 | H-P\|C3\|VB\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C3\|VB\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C5\|V0\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C5\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C5\|V0\|e0 loc0 n_P | exact | 320 | 320 |  | match |  |
| K-64 | H-P\|C5\|V0\|e0 loc0 n_L | exact | 329 | 329 |  | match |  |
| K-65 | H-P\|C5\|V0\|e0 loc0 c_min_tP_m | m | 0.0359647010147772 | 0.0359647010147772 | 0 | match |  |
| K-65 | H-P\|C5\|V0\|e0 loc0 c_hat_m | m | 0.00584134665333313 | 0.00584134665333313 | 0 | match |  |
| K-65 | H-P\|C5\|V0\|e0 loc0 c_hat_A_m | m | 0.00584134665333313 | 0.00584134665333313 | 0 | match |  |
| K-65 | H-P\|C5\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C5\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C5\|V0\|e0.002 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C5\|V0\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C5\|V0\|e0.002 loc0 n_P | exact | 321 | 321 |  | match |  |
| K-64 | H-P\|C5\|V0\|e0.002 loc0 n_L | exact | 330 | 330 |  | match |  |
| K-65 | H-P\|C5\|V0\|e0.002 loc0 c_min_tP_m | m | 0.0362631440662111 | 0.0362631440662111 | 0 | match |  |
| K-65 | H-P\|C5\|V0\|e0.002 loc0 c_hat_m | m | 0.00584319336743233 | 0.00584319336743233 | 0 | match |  |
| K-65 | H-P\|C5\|V0\|e0.002 loc0 c_hat_A_m | m | 0.00584319336743233 | 0.00584319336743233 | 0 | match |  |
| K-65 | H-P\|C5\|V0\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C5\|V0\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C5\|VB\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C5\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C5\|VB\|e0 loc0 n_P | exact | 338 | 338 |  | match |  |
| K-64 | H-P\|C5\|VB\|e0 loc0 n_L | exact | 347 | 347 |  | match |  |
| K-65 | H-P\|C5\|VB\|e0 loc0 c_min_tP_m | m | 0.0362675452083827 | 0.0362675452083827 | 0 | match |  |
| K-65 | H-P\|C5\|VB\|e0 loc0 c_hat_m | m | 0.00584230060331059 | 0.00584230060331059 | 0 | match |  |
| K-65 | H-P\|C5\|VB\|e0 loc0 c_hat_A_m | m | 0.00584230060331059 | 0.00584230060331059 | 0 | match |  |
| K-65 | H-P\|C5\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C5\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|VB\|e0 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C4\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|VB\|e0 loc0 n_P | exact | 329 | 329 |  | match |  |
| K-64 | H-P\|C4\|VB\|e0 loc0 n_L | exact | 337 | 337 |  | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc0 c_min_tP_m | m | 0.0247517080412731 | 0.0247517080412731 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc0 c_hat_m | m | 0.00425700590648637 | 0.00425700590648637 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc0 c_hat_A_m | m | 0.00425700590648637 | 0.00425700590648637 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|VB\|e0 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|VB\|e0 loc1 n_P | exact | 346 | 346 |  | match |  |
| K-64 | H-P\|C4\|VB\|e0 loc1 n_L | exact | 352 | 352 |  | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc1 c_min_tP_m | m | 0.0385861952521207 | 0.0385861952521207 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc1 c_hat_m | m | 0.00856706671060836 | 0.00856706671060836 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc1 c_hat_A_m | m | 0.00856706671060836 | 0.00856706671060836 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C4\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|VB\|e0.002 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-P\|C4\|VB\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|VB\|e0.002 loc0 n_P | exact | 329 | 329 |  | match |  |
| K-64 | H-P\|C4\|VB\|e0.002 loc0 n_L | exact | 337 | 337 |  | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc0 c_min_tP_m | m | 0.0248077248419998 | 0.0248077248419998 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc0 c_hat_m | m | 0.00425781460202823 | 0.00425781460202823 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc0 c_hat_A_m | m | 0.00425781460202823 | 0.00425781460202823 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C4\|VB\|e0.002 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C4\|VB\|e0.002 loc1 n_P | exact | 346 | 346 |  | match |  |
| K-64 | H-P\|C4\|VB\|e0.002 loc1 n_L | exact | 352 | 352 |  | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc1 c_min_tP_m | m | 0.0386555007057403 | 0.0386555007057403 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc1 c_hat_m | m | 0.00857794496354258 | 0.00857794496354258 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc1 c_hat_A_m | m | 0.00857794496354258 | 0.00857794496354258 | 0 | match |  |
| K-65 | H-P\|C4\|VB\|e0.002 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C4\|VB\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-W\|C6\|V0\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-W\|C6\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-W\|C6\|V0\|e0 loc0 n_P | exact | 386 | 386 |  | match |  |
| K-64 | H-W\|C6\|V0\|e0 loc0 n_L | exact | 399 | 399 |  | match |  |
| K-65 | H-W\|C6\|V0\|e0 loc0 c_min_tP_m | m | 0.0969072827538247 | 0.0969072827538247 | 0 | match |  |
| K-65 | H-W\|C6\|V0\|e0 loc0 c_hat_m | m | 0.0129650476139482 | 0.0129650476139482 | 0 | match |  |
| K-65 | H-W\|C6\|V0\|e0 loc0 c_hat_A_m | m | 0.0129650476139482 | 0.0129650476139482 | 0 | match |  |
| K-65 | H-W\|C6\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-W\|C6\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-W\|C6\|V0\|e0.002 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-W\|C6\|V0\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-W\|C6\|V0\|e0.002 loc0 n_P | exact | 387 | 387 |  | match |  |
| K-64 | H-W\|C6\|V0\|e0.002 loc0 n_L | exact | 400 | 400 |  | match |  |
| K-65 | H-W\|C6\|V0\|e0.002 loc0 c_min_tP_m | m | 0.0969776153961788 | 0.0969776153961788 | 0 | match |  |
| K-65 | H-W\|C6\|V0\|e0.002 loc0 c_hat_m | m | 0.0130415473226442 | 0.0130415473226442 | 0 | match |  |
| K-65 | H-W\|C6\|V0\|e0.002 loc0 c_hat_A_m | m | 0.0130415473226442 | 0.0130415473226442 | 0 | match |  |
| K-65 | H-W\|C6\|V0\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-W\|C6\|V0\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-P\|C5\|VB\|e0.002 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-P\|C5\|VB\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-P\|C5\|VB\|e0.002 loc0 n_P | exact | 338 | 338 |  | match |  |
| K-64 | H-P\|C5\|VB\|e0.002 loc0 n_L | exact | 347 | 347 |  | match |  |
| K-65 | H-P\|C5\|VB\|e0.002 loc0 c_min_tP_m | m | 0.0363155029740658 | 0.0363155029740658 | 0 | match |  |
| K-65 | H-P\|C5\|VB\|e0.002 loc0 c_hat_m | m | 0.00584114493142374 | 0.00584114493142374 | 0 | match |  |
| K-65 | H-P\|C5\|VB\|e0.002 loc0 c_hat_A_m | m | 0.00584114493142374 | 0.00584114493142374 | 0 | match |  |
| K-65 | H-P\|C5\|VB\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-P\|C5\|VB\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-M0\|C5\|V0\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-M0\|C5\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-M0\|C5\|V0\|e0 loc0 n_P | exact | 320 | 320 |  | match |  |
| K-64 | H-M0\|C5\|V0\|e0 loc0 n_L | exact | 329 | 329 |  | match |  |
| K-65 | H-M0\|C5\|V0\|e0 loc0 c_min_tP_m | m | 0.0359647010147772 | 0.0359647010147772 | 0 | match |  |
| K-65 | H-M0\|C5\|V0\|e0 loc0 c_hat_m | m | 0.00584134665333313 | 0.00584134665333313 | 0 | match |  |
| K-65 | H-M0\|C5\|V0\|e0 loc0 c_hat_A_m | m | 0.00584134665333313 | 0.00584134665333313 | 0 | match |  |
| K-65 | H-M0\|C5\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-M0\|C5\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-M0\|C1\|V0\|e0 LOC count | exact | 2 | 2 |  | match |  |
| K-64 | H-M0\|C1\|V0\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-M0\|C1\|V0\|e0 loc0 n_P | exact | 307 | 307 |  | match |  |
| K-64 | H-M0\|C1\|V0\|e0 loc0 n_L | exact | 316 | 316 |  | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc0 c_min_tP_m | m | 0.0436299022857449 | 0.0436299022857449 | 0 | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc0 c_hat_m | m | 0.00653200886781735 | 0.00653200886781735 | 0 | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc0 c_hat_A_m | m | 0.00653200886781735 | 0.00653200886781735 | 0 | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-64 | H-M0\|C1\|V0\|e0 loc1 path | exact | "1" | "1" |  | match |  |
| K-64 | H-M0\|C1\|V0\|e0 loc1 n_P | exact | 329 | 329 |  | match |  |
| K-64 | H-M0\|C1\|V0\|e0 loc1 n_L | exact | 341 | 341 |  | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc1 c_min_tP_m | m | 0.0664722891455667 | 0.0664722891455667 | 0 | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc1 c_hat_m | m | 0.00963756358662726 | 0.00963756358662726 | 0 | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc1 c_hat_A_m | m | 0.00963756358662726 | 0.00963756358662726 | 0 | match |  |
| K-65 | H-M0\|C1\|V0\|e0 loc1 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-M0\|C1\|V0\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-W\|C6\|VB\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-W\|C6\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-W\|C6\|VB\|e0 loc0 n_P | exact | 404 | 404 |  | match |  |
| K-64 | H-W\|C6\|VB\|e0 loc0 n_L | exact | 417 | 417 |  | match |  |
| K-65 | H-W\|C6\|VB\|e0 loc0 c_min_tP_m | m | 0.0972519218553864 | 0.0972519218553864 | 0 | match |  |
| K-65 | H-W\|C6\|VB\|e0 loc0 c_hat_m | m | 0.0130538058969509 | 0.0130538058969509 | 0 | match |  |
| K-65 | H-W\|C6\|VB\|e0 loc0 c_hat_A_m | m | 0.0130538058969509 | 0.0130538058969509 | 0 | match |  |
| K-65 | H-W\|C6\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-W\|C6\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-W\|C6\|VB\|e0.002 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-W\|C6\|VB\|e0.002 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-W\|C6\|VB\|e0.002 loc0 n_P | exact | 404 | 404 |  | match |  |
| K-64 | H-W\|C6\|VB\|e0.002 loc0 n_L | exact | 417 | 417 |  | match |  |
| K-65 | H-W\|C6\|VB\|e0.002 loc0 c_min_tP_m | m | 0.0973870501465934 | 0.0973870501465934 | 0 | match |  |
| K-65 | H-W\|C6\|VB\|e0.002 loc0 c_hat_m | m | 0.0130526730733125 | 0.0130526730733125 | 0 | match |  |
| K-65 | H-W\|C6\|VB\|e0.002 loc0 c_hat_A_m | m | 0.0130526730733125 | 0.0130526730733125 | 0 | match |  |
| K-65 | H-W\|C6\|VB\|e0.002 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-W\|C6\|VB\|e0.002 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-M0\|C5\|VB\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-M0\|C5\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-M0\|C5\|VB\|e0 loc0 n_P | exact | 338 | 338 |  | match |  |
| K-64 | H-M0\|C5\|VB\|e0 loc0 n_L | exact | 347 | 347 |  | match |  |
| K-65 | H-M0\|C5\|VB\|e0 loc0 c_min_tP_m | m | 0.0362675452083827 | 0.0362675452083827 | 0 | match |  |
| K-65 | H-M0\|C5\|VB\|e0 loc0 c_hat_m | m | 0.00584230060331059 | 0.00584230060331059 | 0 | match |  |
| K-65 | H-M0\|C5\|VB\|e0 loc0 c_hat_A_m | m | 0.00584230060331059 | 0.00584230060331059 | 0 | match |  |
| K-65 | H-M0\|C5\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-M0\|C5\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-SH0\|C1\|VB\|e0 (shadow-off line) | exact | "NA" | null |  | both_NA | P1 "NA", P2 line not output (map 9 note) |
| K-64 | H-SH0\|C4\|VB\|e0 (shadow-off line) | exact | "NA" | null |  | both_NA | P1 "NA", P2 line not output (map 9 note) |
| K-64 | H-M0\|C1\|VB\|e0 LOC count | exact | 1 | 1 |  | match |  |
| K-64 | H-M0\|C1\|VB\|e0 loc0 path | exact | "1" | "1" |  | match |  |
| K-64 | H-M0\|C1\|VB\|e0 loc0 n_P | exact | 324 | 324 |  | match |  |
| K-64 | H-M0\|C1\|VB\|e0 loc0 n_L | exact | 333 | 333 |  | match |  |
| K-65 | H-M0\|C1\|VB\|e0 loc0 c_min_tP_m | m | 0.0438475200484984 | 0.0438475200484984 | 0 | match |  |
| K-65 | H-M0\|C1\|VB\|e0 loc0 c_hat_m | m | 0.00657323030111678 | 0.00657323030111678 | 0 | match |  |
| K-65 | H-M0\|C1\|VB\|e0 loc0 c_hat_A_m | m | 0.00657323030111678 | 0.00657323030111678 | 0 | match |  |
| K-65 | H-M0\|C1\|VB\|e0 loc0 d_m | m | 0 | 0 | 0 | match |  |
| K-66 | H-M0\|C1\|VB\|e0 max\|d\| | m | 0 | 0 | 0 | match |  |
| K-64 | H-SH0\|C5\|VB\|e0 (shadow-off line) | exact | "NA" | null |  | both_NA | P1 "NA", P2 line not output (map 9 note) |
| K-64 | H-SH0\|C2\|VB\|e0 (shadow-off line) | exact | "NA" | null |  | both_NA | P1 "NA", P2 line not output (map 9 note) |
| K-70 | kappa front | rel | 8.26895653230022e-07 | 8.26895653230006e-07 | 1.63e-20 | match |  |
| K-71 | C_type front | rel | 8.24860003225718e-28 | 8.24860003225701e-28 | 1.69e-41 | match |  |
| K-73 | kappa_fit front | exact | 13 | 13 |  | match |  |
| K-73 | kappa_excluded front | exact | 27 | 27 |  | match |  |
| K-73 | c_fit front | exact | 4 | 4 |  | match |  |
| K-73 | c_excluded front | exact | 36 | 36 |  | match |  |
| K-74 | kappa_fit_legs front (n=13/13) | exact | ["H-P\|C1\|V0\|e0.002\|FR", "H-P\|C1\|V0\|e0\|FR", "H-P\|C1\|VB\|e0.002\|FR", "H-P\|C1\|VB\|e0\|FR", "H-P\|C2\|VB\|e0.002\|FR", "H-P\|C4\|V... | ["H-P\|C1\|V0\|e0.002\|FR", "H-P\|C1\|V0\|e0\|FR", "H-P\|C1\|VB\|e0.002\|FR", "H-P\|C1\|VB\|e0\|FR", "H-P\|C2\|VB\|e0.002\|FR", "H-P\|C4\|V... |  | match |  |
| K-74 | c_fit_legs front (n=4/4) | exact | ["H-P\|C5\|V0\|e0.002\|FR", "H-P\|C5\|V0\|e0\|FR", "H-P\|C5\|VB\|e0.002\|FR", "H-P\|C5\|VB\|e0\|FR"] | ["H-P\|C5\|V0\|e0.002\|FR", "H-P\|C5\|V0\|e0\|FR", "H-P\|C5\|VB\|e0.002\|FR", "H-P\|C5\|VB\|e0\|FR"] |  | match |  |
| K-75 | kappa_argmax front | exact | "H-P\|C5\|V0\|e0\|FR" | "H-P\|C5\|V0\|e0\|FR" |  | match |  |
| K-75 | c_argmax front | exact | "H-P\|C5\|V0\|e0\|FR" | "H-P\|C5\|V0\|e0\|FR" |  | match |  |
| K-76 | kappa ratio front | rel | 8223.87753941856 | 8223.87753941853 | 2.73e-11 | match |  |
| K-76 | kappa nonlinear front | exact | true | true |  | match |  |
| K-70 | kappa rear | rel | 2.52957015611653e-05 | 2.52957015611653e-05 | 0 | match |  |
| K-71 | C_type rear | rel | 1.69112699370557e-25 | 1.69112699370557e-25 | 0 | match |  |
| K-73 | kappa_fit rear | exact | 8 | 8 |  | match |  |
| K-73 | kappa_excluded rear | exact | 32 | 32 |  | match |  |
| K-73 | c_fit rear | exact | 8 | 8 |  | match |  |
| K-73 | c_excluded rear | exact | 32 | 32 |  | match |  |
| K-74 | kappa_fit_legs rear (n=8/8) | exact | ["H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|VB\|e0\|RL", "H-P\|C4\|V0\|e0.002\|RL", "H-P\|C4\|V... | ["H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|VB\|e0\|RL", "H-P\|C4\|V0\|e0.002\|RL", "H-P\|C4\|V... |  | match |  |
| K-74 | c_fit_legs rear (n=8/8) | exact | ["H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|VB\|e0\|RL", "H-P\|C4\|V0\|e0.002\|RL", "H-P\|C4\|V... | ["H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|VB\|e0\|RL", "H-P\|C4\|V0\|e0.002\|RL", "H-P\|C4\|V... |  | match |  |
| K-75 | kappa_argmax rear | exact | "H-P\|C3\|VB\|e0\|RL" | "H-P\|C3\|VB\|e0\|RL" |  | match |  |
| K-75 | c_argmax rear | exact | "H-P\|C3\|VB\|e0\|RL" | "H-P\|C3\|VB\|e0\|RL" |  | match |  |
| K-76 | kappa ratio rear | rel | 2.20148383610098 | 2.20148383610101 | 2.18e-14 | match |  |
| K-76 | kappa nonlinear rear | exact | true | true |  | match |  |
| K-72 | delta_allow | m | 0.019854787856491 | 0.019854787856491 | 0 | match |  |
| K-77 | sens 600: kappa front | rel | 1.0787754318205e-05 | 1.07877543182049e-05 | 1.86e-19 | match |  |
| K-77 | sens 600: C_type front | rel | 9.78486442719142e-27 | 9.78486442719124e-27 | 1.81e-40 | match |  |
| K-77 | sens 600: kappa_fit front | exact | 21 | 21 |  | match |  |
| K-77 | sens 600: kappa_excluded front | exact | 19 | 19 |  | match |  |
| K-77 | sens 600: c_fit front | exact | 8 | 8 |  | match |  |
| K-77 | sens 600: c_excluded front | exact | 32 | 32 |  | match |  |
| K-77 | sens 600: kappa_fit_legs front (n=21/21) | exact | ["H-P\|C1\|V0\|e0.002\|FR", "H-P\|C1\|V0\|e0\|FR", "H-P\|C1\|VB\|e0.002\|FR", "H-P\|C1\|VB\|e0\|FR", "H-P\|C2\|V0\|e0.002\|FR", "H-P\|C2\|V... | ["H-P\|C1\|V0\|e0.002\|FR", "H-P\|C1\|V0\|e0\|FR", "H-P\|C1\|VB\|e0.002\|FR", "H-P\|C1\|VB\|e0\|FR", "H-P\|C2\|V0\|e0.002\|FR", "H-P\|C2\|V... |  | match |  |
| K-77 | sens 600: c_fit_legs front (n=8/8) | exact | ["H-P\|C5\|V0\|e0.002\|FL", "H-P\|C5\|V0\|e0.002\|FR", "H-P\|C5\|V0\|e0\|FL", "H-P\|C5\|V0\|e0\|FR", "H-P\|C5\|VB\|e0.002\|FL", "H-P\|C5\|V... | ["H-P\|C5\|V0\|e0.002\|FL", "H-P\|C5\|V0\|e0.002\|FR", "H-P\|C5\|V0\|e0\|FL", "H-P\|C5\|V0\|e0\|FR", "H-P\|C5\|VB\|e0.002\|FL", "H-P\|C5\|V... |  | match |  |
| K-77 | sens 600: kappa_argmax front | exact | "H-P\|C5\|VB\|e0.002\|FL" | "H-P\|C5\|VB\|e0.002\|FL" |  | match |  |
| K-77 | sens 600: c_argmax front | exact | "H-P\|C5\|VB\|e0.002\|FL" | "H-P\|C5\|VB\|e0.002\|FL" |  | match |  |
| K-77 | sens 600: kappa ratio front | rel | 107289.438627117 | 107289.438627117 | 1.02e-10 | match |  |
| K-77 | sens 600: kappa nonlinear front | exact | true | true |  | match |  |
| K-77 | sens 600: kappa rear | rel | 3.11955084233154e-05 | 3.11955084233154e-05 | 0 | match |  |
| K-77 | sens 600: C_type rear | rel | 2.06405136807871e-25 | 2.06405136807871e-25 | 0 | match |  |
| K-77 | sens 600: kappa_fit rear | exact | 10 | 10 |  | match |  |
| K-77 | sens 600: kappa_excluded rear | exact | 30 | 30 |  | match |  |
| K-77 | sens 600: c_fit rear | exact | 10 | 10 |  | match |  |
| K-77 | sens 600: c_excluded rear | exact | 30 | 30 |  | match |  |
| K-77 | sens 600: kappa_fit_legs rear (n=10/10) | exact | ["H-P\|C2\|V0\|e0.002\|RL", "H-P\|C2\|V0\|e0\|RL", "H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|V... | ["H-P\|C2\|V0\|e0.002\|RL", "H-P\|C2\|V0\|e0\|RL", "H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|V... |  | match |  |
| K-77 | sens 600: c_fit_legs rear (n=10/10) | exact | ["H-P\|C2\|V0\|e0.002\|RL", "H-P\|C2\|V0\|e0\|RL", "H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|V... | ["H-P\|C2\|V0\|e0.002\|RL", "H-P\|C2\|V0\|e0\|RL", "H-P\|C3\|V0\|e0.002\|RL", "H-P\|C3\|V0\|e0\|RL", "H-P\|C3\|VB\|e0.002\|RL", "H-P\|C3\|V... |  | match |  |
| K-77 | sens 600: kappa_argmax rear | exact | "H-P\|C2\|V0\|e0\|RL" | "H-P\|C2\|V0\|e0\|RL" |  | match |  |
| K-77 | sens 600: c_argmax rear | exact | "H-P\|C2\|V0\|e0\|RL" | "H-P\|C2\|V0\|e0\|RL" |  | match |  |
| K-77 | sens 600: kappa ratio rear | rel | 2.71494377757505 | 2.71494377757507 | 2.66e-14 | match |  |
| K-77 | sens 600: kappa nonlinear rear | exact | true | true |  | match |  |
| K-77 | sens 2000: kappa front | rel | 6.23603836383369e-08 | 6.23603836383365e-08 | 3.44e-22 | match |  |
| K-77 | sens 2000: C_type front | rel | "NA" | null |  | both_NA |  |
| K-77 | sens 2000: kappa_fit front | exact | 4 | 4 |  | match |  |
| K-77 | sens 2000: kappa_excluded front | exact | 36 | 36 |  | match |  |
| K-77 | sens 2000: c_fit front | exact | 0 | 0 |  | match |  |
| K-77 | sens 2000: c_excluded front | exact | 40 | 40 |  | match |  |
| K-77 | sens 2000: kappa_fit_legs front (n=4/4) | exact | ["H-P\|C4\|V0\|e0.002\|FR", "H-P\|C4\|V0\|e0\|FR", "H-P\|C4\|VB\|e0.002\|FR", "H-P\|C4\|VB\|e0\|FR"] | ["H-P\|C4\|V0\|e0.002\|FR", "H-P\|C4\|V0\|e0\|FR", "H-P\|C4\|VB\|e0.002\|FR", "H-P\|C4\|VB\|e0\|FR"] |  | match |  |
| K-77 | sens 2000: c_fit_legs front (n=0/0) | exact | [] | [] |  | match |  |
| K-77 | sens 2000: kappa_argmax front | exact | "H-P\|C4\|V0\|e0\|FR" | "H-P\|C4\|V0\|e0\|FR" |  | match |  |
| K-77 | sens 2000: c_argmax front | exact | null | null |  | both_NA |  |
| K-77 | sens 2000: kappa ratio front | rel | 620.20420152116 | 620.204201521167 | 6.71e-12 | match |  |
| K-77 | sens 2000: kappa nonlinear front | exact | true | true |  | match |  |
| K-77 | sens 2000: kappa rear | rel | "NA" | null |  | both_NA |  |
| K-77 | sens 2000: C_type rear | rel | "NA" | null |  | both_NA |  |
| K-77 | sens 2000: kappa_fit rear | exact | 0 | 0 |  | match |  |
| K-77 | sens 2000: kappa_excluded rear | exact | 40 | 40 |  | match |  |
| K-77 | sens 2000: c_fit rear | exact | 0 | 0 |  | match |  |
| K-77 | sens 2000: c_excluded rear | exact | 40 | 40 |  | match |  |
| K-77 | sens 2000: kappa_fit_legs rear (n=0/0) | exact | [] | [] |  | match |  |
| K-77 | sens 2000: c_fit_legs rear (n=0/0) | exact | [] | [] |  | match |  |
| K-77 | sens 2000: kappa_argmax rear | exact | null | null |  | both_NA |  |
| K-77 | sens 2000: c_argmax rear | exact | null | null |  | both_NA |  |
| K-77 | sens 2000: kappa ratio rear | rel | "NA" | null |  | both_NA |  |
| K-77 | sens 2000: kappa nonlinear rear | exact | null | false |  | mismatch |  |
| K-78 | runs used (n=20/20) | exact | ["H-P\|C1\|V0\|e0", "H-P\|C1\|V0\|e0.002", "H-P\|C1\|VB\|e0", "H-P\|C1\|VB\|e0.002", "H-P\|C2\|V0\|e0", "H-P\|C2\|V0\|e0.002", "H-P\|C2\|... | ["H-P\|C1\|V0\|e0", "H-P\|C1\|V0\|e0.002", "H-P\|C1\|VB\|e0", "H-P\|C1\|VB\|e0.002", "H-P\|C2\|V0\|e0", "H-P\|C2\|V0\|e0.002", "H-P\|C2\|... |  | match |  |
| K-79 | R1-4 harness run set (n=28/28) | exact | ["H-M0\|C1\|V0\|e0", "H-M0\|C1\|VB\|e0", "H-M0\|C5\|V0\|e0", "H-M0\|C5\|VB\|e0", "H-P\|C1\|V0\|e0", "H-P\|C1\|V0\|e0.002", "H-P\|C1\|VB\|e... | ["H-M0\|C1\|V0\|e0", "H-M0\|C1\|VB\|e0", "H-M0\|C5\|V0\|e0", "H-M0\|C5\|VB\|e0", "H-P\|C1\|V0\|e0", "H-P\|C1\|V0\|e0.002", "H-P\|C1\|VB\|e... |  | match |  |
| K-79 | H-M0\|C1\|V0\|e0 n_L | exact | 341 | 341 |  | match |  |
| K-79 | H-M0\|C1\|V0\|e0 sum ratio | rel | 1.03775146538292 | 1.03775146538292 | 4.44e-16 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 W_hat FL | N | -235.90831759588 | -235.908317595851 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 E-Fpk FL | N | -633.039198050654 | -633.039198050625 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 stroke rate FL | m/s | 0.00785397077376571 | 0.00785397077376571 | 0 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 W_hat FR | N | 1632.19373350777 | 1632.19373350781 | 4.37e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 E-Fpk FR | N | -442.460725445941 | -442.460725445897 | 4.37e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 stroke rate FR | m/s | 0.00663523524055742 | 0.00663523524055742 | 0 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 W_hat RL | N | -378.078083221189 | -378.07808322116 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 E-Fpk RL | N | -378.078083221189 | -378.07808322116 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 stroke rate RL | m/s | 0.00634108935324895 | 0.00634108935324895 | 0 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 W_hat RR | N | -1018.20733269077 | -1018.20733269074 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 E-Fpk RR | N | -1018.20733269077 | -1018.20733269074 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 stroke rate RR | m/s | 0.00523135690747134 | 0.00523135690747134 | 0 | match |  |
| K-79 | H-M0\|C1\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-M0\|C1\|VB\|e0 n_L | exact | 333 | 333 |  | match |  |
| K-79 | H-M0\|C1\|VB\|e0 sum ratio | rel | 1.03429844138062 | 1.03429844138062 | 2.22e-16 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 W_hat FL | N | -655.339103221631 | -655.339103221602 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 E-Fpk FL | N | -655.339103221631 | -655.339103221602 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 stroke rate FL | m/s | 0.0175236534787504 | 0.0175236534787504 | 0 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 W_hat FR | N | 818.31208321391 | 818.312083213939 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 E-Fpk FR | N | -880.937389351559 | -880.937389351529 | 2.91e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 stroke rate FR | m/s | 0.0173661225529931 | 0.0173661225529931 | 0 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 W_hat RL | N | 369.517629184353 | 369.517629184367 | 1.46e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 E-Fpk RL | N | 369.517629184353 | 369.517629184367 | 1.46e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 stroke rate RL | m/s | 0.00537443399919124 | 0.00537443399919124 | 0 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 W_hat RR | N | -532.490609176675 | -532.490609176661 | 1.46e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 E-Fpk RR | N | -532.490609176675 | -532.490609176661 | 1.46e-11 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 stroke rate RR | m/s | 0.00523099255946846 | 0.00523099255946846 | 0 | match |  |
| K-79 | H-M0\|C1\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-M0\|C5\|V0\|e0 n_L | exact | 329 | 329 |  | match |  |
| K-79 | H-M0\|C5\|V0\|e0 sum ratio | rel | 1.03522005707768 | 1.03522005707768 | 2.22e-16 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 W_hat FL | N | 883.965896547554 | 883.965896547568 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 E-Fpk FL | N | 883.965896547554 | 883.965896547568 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 stroke rate FL | m/s | 0.00532230396862898 | 0.00532230396862898 | 0 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 W_hat FR | N | 1474.16714651746 | 1474.16714651749 | 2.91e-11 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 E-Fpk FR | N | 1450.71168652973 | 1450.71168652976 | 2.91e-11 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 stroke rate FR | m/s | 0.00523106699881537 | 0.00523106699881537 | 0 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 W_hat RL | N | -1325.90602520316 | -1325.90602520316 | 0 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 E-Fpk RL | N | -1325.90602520316 | -1325.90602520316 | 0 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 stroke rate RL | m/s | 0.0176573050012818 | 0.0176573050012818 | 0 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 W_hat RR | N | -1032.22701786188 | -1032.22701786186 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 E-Fpk RR | N | -2335.46669254925 | -2335.46669254923 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 stroke rate RR | m/s | 0.0175742282197189 | 0.0175742282197189 | 0 | match |  |
| K-79 | H-M0\|C5\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-M0\|C5\|VB\|e0 n_L | exact | 347 | 347 |  | match |  |
| K-79 | H-M0\|C5\|VB\|e0 sum ratio | rel | 1.03536332847571 | 1.03536332847571 | 2.22e-16 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 W_hat FL | N | 852.384232284501 | 852.38423228453 | 2.91e-11 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 E-Fpk FL | N | 852.384232284501 | 852.38423228453 | 2.91e-11 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 stroke rate FL | m/s | 0.00532545906989146 | 0.00532545906989146 | 0 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 W_hat FR | N | 1506.61925418198 | 1506.61925418199 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 E-Fpk FR | N | 1469.53611098246 | 1469.53611098247 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 stroke rate FR | m/s | 0.00523106752991387 | 0.00523106752991387 | 0 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 W_hat RL | N | -1350.30489485328 | -1350.30489485328 | 0 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 E-Fpk RL | N | -1350.30489485328 | -1350.30489485328 | 0 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 stroke rate RL | m/s | 0.0176278190057011 | 0.0176278190057011 | 0 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 W_hat RR | N | -1008.69859161321 | -1008.6985916132 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 E-Fpk RR | N | -2350.12276427538 | -2350.12276427537 | 1.46e-11 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 stroke rate RR | m/s | 0.0175418697971463 | 0.0175418697971463 | 0 | match |  |
| K-79 | H-M0\|C5\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C1\|V0\|e0 n_L | exact | 338 | 338 |  | match |  |
| K-79 | H-P\|C1\|V0\|e0 sum ratio | rel | 1.03735595696558 | 1.03735595696558 | 4.44e-16 | match |  |
| K-79 | H-P\|C1\|V0\|e0 W_hat FL | N | -224.188679408748 | -224.188679408719 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 E-Fpk FL | N | -661.792979493155 | -661.792979493126 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 stroke rate FL | m/s | 0.00863729176346473 | 0.00863729176346473 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0 W_hat FR | N | 1479.68477007751 | 1479.68477007755 | 4.37e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 E-Fpk FR | N | -488.381625750597 | -488.381625750553 | 4.37e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 stroke rate FR | m/s | 0.00749470258637475 | 0.00749470258637475 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0 W_hat RL | N | -290.953786537386 | -290.953786537357 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 E-Fpk RL | N | -290.953786537386 | -290.953786537357 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 stroke rate RL | m/s | 0.00630311298956965 | 0.00630311298956965 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0 W_hat RR | N | -964.542304131435 | -964.542304131421 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 E-Fpk RR | N | -1056.22169117549 | -1056.22169117548 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0 stroke rate RR | m/s | 0.00526271640844844 | 0.00526271640844844 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 n_L | exact | 338 | 338 |  | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 sum ratio | rel | 1.03735662890674 | 1.03735662890674 | 2.22e-16 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 W_hat FL | N | -251.624396849889 | -251.62439684986 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 E-Fpk FL | N | -665.66153326082 | -665.661533260791 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 stroke rate FL | m/s | 0.00900197693594951 | 0.00900197693594951 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 W_hat FR | N | 1461.79608673716 | 1461.79608673719 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 E-Fpk FR | N | -524.307834248088 | -524.307834248058 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 stroke rate FR | m/s | 0.00787715102213316 | 0.00787715102213316 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 W_hat RL | N | -262.568516780535 | -262.56851678052 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 E-Fpk RL | N | -262.568516780535 | -262.56851678052 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 stroke rate RL | m/s | 0.00628484803467333 | 0.00628484803467333 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 W_hat RR | N | -947.603173106749 | -947.603173106734 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 E-Fpk RR | N | -1024.33440249646 | -1024.33440249645 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 stroke rate RR | m/s | 0.0052606259795529 | 0.0052606259795529 | 0 | match |  |
| K-79 | H-P\|C1\|V0\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C1\|VB\|e0 n_L | exact | 355 | 355 |  | match |  |
| K-79 | H-P\|C1\|VB\|e0 sum ratio | rel | 1.03735747956945 | 1.03735747956945 | 2.22e-16 | match |  |
| K-79 | H-P\|C1\|VB\|e0 W_hat FL | N | -252.815269392566 | -252.815269392551 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0 E-Fpk FL | N | -666.155425397097 | -666.155425397083 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0 stroke rate FL | m/s | 0.00901853945753261 | 0.00901853945753261 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0 W_hat FR | N | 1460.91203389312 | 1460.91203389315 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0 E-Fpk FR | N | -525.76470139937 | -525.764701399341 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0 stroke rate FR | m/s | 0.00789382992729681 | 0.00789382992729681 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0 W_hat RL | N | -261.269038350234 | -261.269038350219 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0 E-Fpk RL | N | -261.269038350234 | -261.269038350219 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0 stroke rate RL | m/s | 0.00628461668735869 | 0.00628461668735869 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0 W_hat RR | N | -946.827726150354 | -946.827726150354 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0 E-Fpk RR | N | -1023.02834159986 | -1023.02834159986 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0 stroke rate RR | m/s | 0.00526050060654759 | 0.00526050060654759 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 n_L | exact | 355 | 355 |  | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 sum ratio | rel | 1.03734570104166 | 1.03734570104166 | 4.44e-16 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 W_hat FL | N | -263.887691034601 | -263.887691034557 | 4.37e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 E-Fpk FL | N | -661.438262385869 | -661.438262385826 | 4.37e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 stroke rate FL | m/s | 0.00917532665321907 | 0.00917532665321907 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 W_hat FR | N | 1452.96188908858 | 1452.96188908862 | 4.37e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 E-Fpk FR | N | -534.866072588688 | -534.866072588644 | 4.37e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 stroke rate FR | m/s | 0.00806386722883579 | 0.00806386722883579 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 W_hat RL | N | -250.011298421348 | -250.011298421334 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 E-Fpk RL | N | -250.011298421348 | -250.011298421334 | 1.46e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 stroke rate RL | m/s | 0.00627230408015378 | 0.00627230408015378 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 W_hat RR | N | -939.0628996327 | -939.06289963267 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 E-Fpk RR | N | -1007.4722359079 | -1007.47223590787 | 2.91e-11 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 stroke rate RR | m/s | 0.00526025302244992 | 0.00526025302244992 | 0 | match |  |
| K-79 | H-P\|C1\|VB\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C2\|V0\|e0 n_L | exact | 315 | 315 |  | match |  |
| K-79 | H-P\|C2\|V0\|e0 sum ratio | rel | 1.03352790084475 | 1.03352790084475 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0 W_hat FL | N | -1176.27155822553 | -1176.27155822552 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0 E-Fpk FL | N | -1176.27155822553 | -1176.27155822552 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0 stroke rate FL | m/s | 0.0199079210158626 | 0.0199079210158626 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0 W_hat FR | N | 716.966815613428 | 716.966815613458 | 2.91e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0 E-Fpk FR | N | -1470.67552779627 | -1470.67552779624 | 2.91e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0 stroke rate FR | m/s | 0.0197748760766969 | 0.0197748760766969 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0 W_hat RL | N | 733.349770658344 | 733.349770658344 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0 E-Fpk RL | N | 733.349770658344 | 733.349770658344 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0 stroke rate RL | m/s | 0.00534385959933492 | 0.00534385959933492 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0 W_hat RR | N | -274.045028046268 | -274.045028046254 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0 E-Fpk RR | N | -274.045028046268 | -274.045028046254 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0 stroke rate RR | m/s | 0.0052227141320027 | 0.0052227141320027 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 n_L | exact | 316 | 316 |  | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 sum ratio | rel | 1.03391663053055 | 1.03391663053055 | 2.22e-16 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 W_hat FL | N | -1306.21575156241 | -1306.21575156237 | 4.37e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 E-Fpk FL | N | -1306.21575156241 | -1306.21575156237 | 4.37e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 stroke rate FL | m/s | 0.0202897484699482 | 0.0202897484699482 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 W_hat FR | N | 808.971945487152 | 808.971945487196 | 4.37e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 E-Fpk FR | N | -1512.649992709 | -1512.64999270896 | 4.37e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 stroke rate FR | m/s | 0.0201333447790075 | 0.0201333447790075 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 W_hat RL | N | 733.916630546053 | 733.916630546068 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 E-Fpk RL | N | 733.916630546053 | 733.916630546068 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 stroke rate RL | m/s | 0.00535696813906528 | 0.00535696813906528 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 W_hat RR | N | -236.672824470879 | -236.67282447085 | 2.91e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 E-Fpk RR | N | -236.672824470879 | -236.67282447085 | 2.91e-11 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 stroke rate RR | m/s | 0.00521455311483954 | 0.00521455311483954 | 0 | match |  |
| K-79 | H-P\|C2\|V0\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C2\|VB\|e0 n_L | exact | 333 | 333 |  | match |  |
| K-79 | H-P\|C2\|VB\|e0 sum ratio | rel | 1.03369776280946 | 1.03369776280946 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 W_hat FL | N | -1001.24910053919 | -1001.24910053918 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0 E-Fpk FL | N | -1001.24910053919 | -1001.24910053918 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0 stroke rate FL | m/s | 0.0185288153492458 | 0.0185288153492458 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 W_hat FR | N | 859.592961154922 | 859.592961154922 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 E-Fpk FR | N | -1359.24657534981 | -1359.24657534981 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 stroke rate FR | m/s | 0.018387284385466 | 0.018387284385466 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 W_hat RL | N | 569.270490260664 | 569.270490260664 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 E-Fpk RL | N | 569.270490260664 | 569.270490260664 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 stroke rate RL | m/s | 0.00535929950316927 | 0.00535929950316927 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 W_hat RR | N | -427.614350876378 | -427.614350876378 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 E-Fpk RR | N | -427.614350876378 | -427.614350876378 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 stroke rate RR | m/s | 0.00523042699693721 | 0.00523042699693721 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 n_L | exact | 356 | 356 |  | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 sum ratio | rel | 1.03709916526989 | 1.03709916526989 | 2.22e-16 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 W_hat FL | N | -592.160869732892 | -592.160869732863 | 2.91e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 E-Fpk FL | N | -1038.66470979215 | -1038.66470979212 | 2.91e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 stroke rate FL | m/s | 0.00957027953158995 | 0.00957027953158995 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 W_hat FR | N | 1861.21472701995 | 1861.21472701996 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 E-Fpk FR | N | -958.401808225914 | -958.401808225899 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 stroke rate FR | m/s | 0.00849080055850715 | 0.00849080055850715 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 W_hat RL | N | -195.412184494271 | -195.412184494271 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 E-Fpk RL | N | -195.412184494271 | -195.412184494271 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 stroke rate RL | m/s | 0.00624562479354274 | 0.00624562479354274 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 W_hat RR | N | -1073.64167279279 | -1073.64167279277 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 E-Fpk RR | N | -1073.64167279279 | -1073.64167279277 | 1.46e-11 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 stroke rate RR | m/s | 0.00526259451080424 | 0.00526259451080424 | 0 | match |  |
| K-79 | H-P\|C2\|VB\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C3\|V0\|e0 n_L | exact | 315 | 315 |  | match |  |
| K-79 | H-P\|C3\|V0\|e0 sum ratio | rel | 1.03365413874408 | 1.03365413874408 | 2.22e-16 | match |  |
| K-79 | H-P\|C3\|V0\|e0 W_hat FL | N | -1704.3074593209 | -1704.30745932089 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 E-Fpk FL | N | -1704.3074593209 | -1704.30745932089 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 stroke rate FL | m/s | 0.020924301600056 | 0.020924301600056 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0 W_hat FR | N | 479.146159179276 | 479.146159179305 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 E-Fpk FR | N | -2210.52997683552 | -2210.52997683549 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 stroke rate FR | m/s | 0.0207963218507667 | 0.0207963218507667 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0 W_hat RL | N | 1165.28315804337 | 1165.28315804338 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 E-Fpk RL | N | 1165.28315804337 | 1165.28315804338 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 stroke rate RL | m/s | 0.00509786149240021 | 0.00509786149240021 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0 W_hat RR | N | 59.8781420981977 | 59.8781420982123 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 E-Fpk RR | N | 59.8781420981977 | 59.8781420982123 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0 stroke rate RR | m/s | 0.00498132818696484 | 0.00498132818696484 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 n_L | exact | 315 | 315 |  | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 sum ratio | rel | 1.03362738641865 | 1.03362738641865 | 2.22e-16 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 W_hat FL | N | -1822.26414711321 | -1822.26414711319 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 E-Fpk FL | N | -1822.26414711321 | -1822.26414711319 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 stroke rate FL | m/s | 0.020924301600056 | 0.020924301600056 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 W_hat FR | N | 334.158787007691 | 334.15878700772 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 E-Fpk FR | N | -2354.59944529101 | -2354.59944529098 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 stroke rate FR | m/s | 0.020808724673651 | 0.020808724673651 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 W_hat RL | N | 1299.74956917478 | 1299.74956917478 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 E-Fpk RL | N | 1299.74956917478 | 1299.74956917478 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 stroke rate RL | m/s | 0.0048824972091488 | 0.0048824972091488 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 W_hat RR | N | 188.355790930727 | 188.355790930742 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 E-Fpk RR | N | 188.355790930727 | 188.355790930742 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 stroke rate RR | m/s | 0.00477725742442092 | 0.00477725742442092 | 0 | match |  |
| K-79 | H-P\|C3\|V0\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C3\|VB\|e0 n_L | exact | 335 | 335 |  | match |  |
| K-79 | H-P\|C3\|VB\|e0 sum ratio | rel | 1.03318250582551 | 1.03318250582551 | 2.22e-16 | match |  |
| K-79 | H-P\|C3\|VB\|e0 W_hat FL | N | -1755.91197754999 | -1755.91197754996 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0 E-Fpk FL | N | -1755.91197754999 | -1755.91197754996 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0 stroke rate FL | m/s | 0.0206447889687378 | 0.0206447889687378 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 W_hat FR | N | 920.946341466319 | 920.946341466348 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0 E-Fpk FR | N | -2144.96287279989 | -2144.96287279986 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0 stroke rate FR | m/s | 0.02047402367783 | 0.02047402367783 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 W_hat RL | N | 1069.33935392094 | 1069.33935392094 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 E-Fpk RL | N | 1069.33935392094 | 1069.33935392094 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 stroke rate RL | m/s | 0.0053445371583527 | 0.0053445371583527 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 W_hat RR | N | -234.373717837283 | -234.373717837283 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 E-Fpk RR | N | -234.373717837283 | -234.373717837283 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 stroke rate RR | m/s | 0.00518904502838091 | 0.00518904502838091 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 n_L | exact | 332 | 332 |  | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 sum ratio | rel | 1.03368397193908 | 1.03368397193908 | 2.22e-16 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 W_hat FL | N | -1789.88451213298 | -1789.88451213295 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 E-Fpk FL | N | -1789.88451213298 | -1789.88451213295 | 2.91e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 stroke rate FL | m/s | 0.020924301600056 | 0.020924301600056 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 W_hat FR | N | 405.726411758733 | 405.726411758747 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 E-Fpk FR | N | -2305.53668548402 | -2305.53668548401 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 stroke rate FR | m/s | 0.0208023744741848 | 0.0208023744741848 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 W_hat RL | N | 1247.41845745713 | 1247.41845745713 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 E-Fpk RL | N | 1247.41845745713 | 1247.41845745713 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 stroke rate RL | m/s | 0.00496438321235138 | 0.00496438321235138 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 W_hat RR | N | 136.739642917077 | 136.739642917091 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 E-Fpk RR | N | 136.739642917077 | 136.739642917091 | 1.46e-11 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 stroke rate RR | m/s | 0.00485336118676072 | 0.00485336118676072 | 0 | match |  |
| K-79 | H-P\|C3\|VB\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C4\|V0\|e0 n_L | exact | 333 | 333 |  | match |  |
| K-79 | H-P\|C4\|V0\|e0 sum ratio | rel | 1.03377610568361 | 1.03377610568361 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0 W_hat FL | N | -1907.31735623714 | -1907.31735623711 | 2.91e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 E-Fpk FL | N | -1907.31735623714 | -1907.31735623711 | 2.91e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 stroke rate FL | m/s | 0.0173690257758397 | 0.0173690257758397 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0 W_hat FR | N | 2563.75695007034 | 2563.75695007035 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 E-Fpk FR | N | -7948.49226866405 | -7948.49226866403 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 stroke rate FR | m/s | 0.020924298438787 | 0.020924298438787 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0 W_hat RL | N | 1504.64454724202 | 1504.64454724203 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 E-Fpk RL | N | 1504.64454724202 | 1504.64454724203 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 stroke rate RL | m/s | 0.0146737167505284 | 0.0146737167505284 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0 W_hat RR | N | -2161.08414107525 | -2161.08414107523 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 E-Fpk RR | N | -2161.08414107525 | -2161.08414107523 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0 stroke rate RR | m/s | 0.017863834684384 | 0.017863834684384 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 n_L | exact | 335 | 335 |  | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 sum ratio | rel | 1.03394962281942 | 1.03394962281942 | 2.22e-16 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 W_hat FL | N | -1991.91478741747 | -1991.91478741745 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 E-Fpk FL | N | -1991.91478741747 | -1991.91478741745 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 stroke rate FL | m/s | 0.0175254846903528 | 0.0175254846903528 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 W_hat FR | N | 2675.36249246291 | 2675.36249246293 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 E-Fpk FR | N | -7936.03279409804 | -7936.03279409802 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 stroke rate FR | m/s | 0.0209242980073521 | 0.0209242980073521 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 W_hat RL | N | 1466.75790706802 | 1466.75790706804 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 E-Fpk RL | N | 1466.75790706802 | 1466.75790706804 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 stroke rate RL | m/s | 0.0148212402780146 | 0.0148212402780146 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 W_hat RR | N | -2150.2056121135 | -2150.20561211348 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 E-Fpk RR | N | -2150.2056121135 | -2150.20561211348 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 stroke rate RR | m/s | 0.0178643691875302 | 0.0178643691875302 | 0 | match |  |
| K-79 | H-P\|C4\|V0\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C4\|VB\|e0 n_L | exact | 352 | 352 |  | match |  |
| K-79 | H-P\|C4\|VB\|e0 sum ratio | rel | 1.03394449663965 | 1.03394449663965 | 2.22e-16 | match |  |
| K-79 | H-P\|C4\|VB\|e0 W_hat FL | N | -1990.41773917976 | -1990.41773917971 | 4.37e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 E-Fpk FL | N | -1990.41773917976 | -1990.41773917971 | 4.37e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 stroke rate FL | m/s | 0.0175231001758425 | 0.0175231001758425 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0 W_hat FR | N | 2672.17693879196 | 2672.17693879201 | 4.37e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 E-Fpk FR | N | -7937.00340533911 | -7937.00340533907 | 4.37e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 stroke rate FR | m/s | 0.0209242980306024 | 0.0209242980306024 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0 W_hat RL | N | 1468.6250049887 | 1468.62500498873 | 2.91e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 E-Fpk RL | N | 1468.6250049887 | 1468.62500498873 | 2.91e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 stroke rate RL | m/s | 0.0148115993302089 | 0.0148115993302089 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0 W_hat RR | N | -2150.38420460098 | -2150.38420460097 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 E-Fpk RR | N | -2150.38420460098 | -2150.38420460097 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0 stroke rate RR | m/s | 0.017857004199352 | 0.017857004199352 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 n_L | exact | 352 | 352 |  | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 sum ratio | rel | 1.03396537515825 | 1.03396537515825 | 2.22e-16 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 W_hat FL | N | -1998.0785259777 | -1998.07852597767 | 2.91e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 E-Fpk FL | N | -1998.0785259777 | -1998.07852597767 | 2.91e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 stroke rate FL | m/s | 0.0175354881480261 | 0.0175354881480261 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 W_hat FR | N | 2683.23157193221 | 2683.23157193222 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 E-Fpk FR | N | -7934.96649636058 | -7934.96649636056 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 stroke rate FR | m/s | 0.0209242979851809 | 0.0209242979851809 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 W_hat RL | N | 1464.36981596825 | 1464.36981596825 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 E-Fpk RL | N | 1464.36981596825 | 1464.36981596825 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 stroke rate RL | m/s | 0.0148253398409459 | 0.0148253398409459 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 W_hat RR | N | -2149.52286192281 | -2149.5228619228 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 E-Fpk RR | N | -2149.52286192281 | -2149.5228619228 | 1.46e-11 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 stroke rate RR | m/s | 0.0178590006863089 | 0.0178590006863089 | 0 | match |  |
| K-79 | H-P\|C4\|VB\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C5\|V0\|e0 n_L | exact | 329 | 329 |  | match |  |
| K-79 | H-P\|C5\|V0\|e0 sum ratio | rel | 1.03522005707768 | 1.03522005707768 | 2.22e-16 | match |  |
| K-79 | H-P\|C5\|V0\|e0 W_hat FL | N | 883.965896547554 | 883.965896547568 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|V0\|e0 E-Fpk FL | N | 883.965896547554 | 883.965896547568 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|V0\|e0 stroke rate FL | m/s | 0.00532230396862898 | 0.00532230396862898 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0 W_hat FR | N | 1474.16714651746 | 1474.16714651749 | 2.91e-11 | match |  |
| K-79 | H-P\|C5\|V0\|e0 E-Fpk FR | N | 1450.71168652973 | 1450.71168652976 | 2.91e-11 | match |  |
| K-79 | H-P\|C5\|V0\|e0 stroke rate FR | m/s | 0.00523106699881537 | 0.00523106699881537 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0 W_hat RL | N | -1325.90602520316 | -1325.90602520316 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0 E-Fpk RL | N | -1325.90602520316 | -1325.90602520316 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0 stroke rate RL | m/s | 0.0176573050012818 | 0.0176573050012818 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0 W_hat RR | N | -1032.22701786188 | -1032.22701786186 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|V0\|e0 E-Fpk RR | N | -2335.46669254925 | -2335.46669254923 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|V0\|e0 stroke rate RR | m/s | 0.0175742282197189 | 0.0175742282197189 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 n_L | exact | 330 | 330 |  | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 sum ratio | rel | 1.03536069380496 | 1.03536069380496 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 W_hat FL | N | 855.380913750574 | 855.380913750574 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 E-Fpk FL | N | 855.380913750574 | 855.380913750574 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 stroke rate FL | m/s | 0.00532510007197451 | 0.00532510007197451 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 W_hat FR | N | 1506.0645831116 | 1506.0645831116 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 E-Fpk FR | N | 1469.23624508828 | 1469.23624508828 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 stroke rate FR | m/s | 0.00523106725952793 | 0.00523106725952793 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 W_hat RL | N | -1350.91714899553 | -1350.91714899553 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 E-Fpk RL | N | -1350.91714899553 | -1350.91714899553 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 stroke rate RL | m/s | 0.0176403659109492 | 0.0176403659109492 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 W_hat RR | N | -1010.52834786662 | -1010.52834786662 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 E-Fpk RR | N | -2350.37666358509 | -2350.37666358509 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 stroke rate RR | m/s | 0.0175547433455159 | 0.0175547433455159 | 0 | match |  |
| K-79 | H-P\|C5\|V0\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C5\|VB\|e0 n_L | exact | 347 | 347 |  | match |  |
| K-79 | H-P\|C5\|VB\|e0 sum ratio | rel | 1.03536332847571 | 1.03536332847571 | 2.22e-16 | match |  |
| K-79 | H-P\|C5\|VB\|e0 W_hat FL | N | 852.384232284501 | 852.38423228453 | 2.91e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0 E-Fpk FL | N | 852.384232284501 | 852.38423228453 | 2.91e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0 stroke rate FL | m/s | 0.00532545906989146 | 0.00532545906989146 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0 W_hat FR | N | 1506.61925418198 | 1506.61925418199 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0 E-Fpk FR | N | 1469.53611098246 | 1469.53611098247 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0 stroke rate FR | m/s | 0.00523106752991387 | 0.00523106752991387 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0 W_hat RL | N | -1350.30489485328 | -1350.30489485328 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0 E-Fpk RL | N | -1350.30489485328 | -1350.30489485328 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0 stroke rate RL | m/s | 0.0176278190057011 | 0.0176278190057011 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0 W_hat RR | N | -1008.69859161321 | -1008.6985916132 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0 E-Fpk RR | N | -2350.12276427538 | -2350.12276427537 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0 stroke rate RR | m/s | 0.0175418697971463 | 0.0175418697971463 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 n_L | exact | 347 | 347 |  | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 sum ratio | rel | 1.03538495658031 | 1.03538495658031 | 2.22e-16 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 W_hat FL | N | 842.917162116428 | 842.917162116442 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 E-Fpk FL | N | 842.917162116428 | 842.917162116442 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 stroke rate FL | m/s | 0.00532660385839323 | 0.00532660385839323 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 W_hat FR | N | 1510.90954603182 | 1510.90954603185 | 2.91e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 E-Fpk FR | N | 1470.92330380014 | 1470.92330380017 | 2.91e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 stroke rate FR | m/s | 0.00523106794170669 | 0.00523106794170669 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 W_hat RL | N | -1352.63282832826 | -1352.63282832825 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 E-Fpk RL | N | -1352.63282832826 | -1352.63282832825 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 stroke rate RL | m/s | 0.0176041436636809 | 0.0176041436636809 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 W_hat RR | N | -1001.19387982004 | -1001.19387982003 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 E-Fpk RR | N | -2352.33495791513 | -2352.33495791511 | 1.46e-11 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 stroke rate RR | m/s | 0.0175171524308793 | 0.0175171524308793 | 0 | match |  |
| K-79 | H-P\|C5\|VB\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-W\|C6\|V0\|e0 n_L | exact | 399 | 399 |  | match |  |
| K-79 | H-W\|C6\|V0\|e0 sum ratio | rel | 1.13657243886574 | 1.13657243886574 | 2.22e-16 | match |  |
| K-79 | H-W\|C6\|V0\|e0 W_hat FL | N | -66.9255983951152 | -66.9255983950861 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 E-Fpk FL | N | -66.9255983951152 | -66.9255983950861 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 stroke rate FL | m/s | 0.00569883694143458 | 0.00569883694143458 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0 W_hat FR | N | 2256.98729666135 | 2256.98729666138 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 E-Fpk FR | N | 611.298829400621 | 611.29882940065 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 stroke rate FR | m/s | 0.00523107539995848 | 0.00523107539995848 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0 W_hat RL | N | -780.543616460534 | -780.54361646052 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 E-Fpk RL | N | -780.543616460534 | -780.54361646052 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 stroke rate RL | m/s | 0.0113107682851032 | 0.0113107682851032 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0 W_hat RR | N | -1409.51808180576 | -1409.51808180574 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 E-Fpk RR | N | -1409.51808180576 | -1409.51808180574 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0 stroke rate RR | m/s | 0.0108848430984732 | 0.0108848430984732 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 n_L | exact | 400 | 400 |  | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 sum ratio | rel | 1.13659896256415 | 1.13659896256415 | 2.22e-16 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 W_hat FL | N | -76.6841301513778 | -76.6841301513487 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 E-Fpk FL | N | -76.6841301513778 | -76.6841301513487 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 stroke rate FL | m/s | 0.00570910263257396 | 0.00570910263257396 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 W_hat FR | N | 2274.02359497687 | 2274.0235949769 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 E-Fpk FR | N | 619.628834766947 | 619.628834766976 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 stroke rate FR | m/s | 0.00523107539995848 | 0.00523107539995848 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 W_hat RL | N | -787.515887786736 | -787.515887786722 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 E-Fpk RL | N | -787.515887786736 | -787.515887786722 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 stroke rate RL | m/s | 0.0113701237446151 | 0.0113701237446151 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 W_hat RR | N | -1409.82357703878 | -1409.82357703877 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 E-Fpk RR | N | -1409.82357703878 | -1409.82357703877 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 stroke rate RR | m/s | 0.0109348510250717 | 0.0109348510250717 | 0 | match |  |
| K-79 | H-W\|C6\|V0\|e0.002 flag | exact | false | false |  | match |  |
| K-79 | H-W\|C6\|VB\|e0 n_L | exact | 417 | 417 |  | match |  |
| K-79 | H-W\|C6\|VB\|e0 sum ratio | rel | 1.13665190409824 | 1.13665190409824 | 2.22e-16 | match |  |
| K-79 | H-W\|C6\|VB\|e0 W_hat FL | N | -88.7722011474252 | -88.7722011473961 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 E-Fpk FL | N | -88.7722011474252 | -88.7722011473961 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 stroke rate FL | m/s | 0.00572214397215554 | 0.00572214397215554 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0 W_hat FR | N | 2290.40075387763 | 2290.40075387766 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 E-Fpk FR | N | 622.874074453721 | 622.87407445375 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 stroke rate FR | m/s | 0.00523107539995848 | 0.00523107539995848 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0 W_hat RL | N | -792.614259898721 | -792.614259898706 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 E-Fpk RL | N | -792.614259898721 | -792.614259898706 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 stroke rate RL | m/s | 0.0113805335778316 | 0.0113805335778316 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0 W_hat RR | N | -1409.01429283156 | -1409.01429283155 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 E-Fpk RR | N | -1409.01429283156 | -1409.01429283155 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0 stroke rate RR | m/s | 0.0109333859294936 | 0.0109333859294936 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0 flag | exact | false | false |  | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 n_L | exact | 417 | 417 |  | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 sum ratio | rel | 1.13667772337536 | 1.13667772337536 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 W_hat FL | N | -93.7536277537583 | -93.7536277537292 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 E-Fpk FL | N | -93.7536277537583 | -93.7536277537292 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 stroke rate FL | m/s | 0.00572807774162465 | 0.00572807774162465 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 W_hat FR | N | 2298.55778062122 | 2298.55778062125 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 E-Fpk FR | N | 624.742709757731 | 624.74270975776 | 2.91e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 stroke rate FR | m/s | 0.00523107539995848 | 0.00523107539995848 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 W_hat RL | N | -795.376012657318 | -795.376012657303 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 E-Fpk RL | N | -795.376012657318 | -795.376012657303 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 stroke rate RL | m/s | 0.0113792121578593 | 0.0113792121578593 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 W_hat RR | N | -1409.42814021021 | -1409.42814021019 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 E-Fpk RR | N | -1409.42814021021 | -1409.42814021019 | 1.46e-11 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 stroke rate RR | m/s | 0.0109266614533654 | 0.0109266614533654 | 0 | match |  |
| K-79 | H-W\|C6\|VB\|e0.002 flag | exact | false | false |  | match |  |
| K-81 | C1 D-c corr class | exact | "-" | "-" |  | match |  |
| K-82 | C1 D-c raw class | exact | "0" | "0" |  | match |  |
| K-81 | C2 D-c corr class | exact | "+" | "+" |  | match |  |
| K-82 | C2 D-c raw class | exact | "+" | "+" |  | match |  |
| K-81 | C3 D-c corr class | exact | "+" | "+" |  | match |  |
| K-82 | C3 D-c raw class | exact | "+" | "+" |  | match |  |
| K-81 | C4 D-c corr class | exact | "?" | "?" |  | match |  |
| K-82 | C4 D-c raw class | exact | "0" | "0" |  | match |  |
| K-81 | C5 D-c corr class | exact | "0" | "0" |  | match |  |
| K-82 | C5 D-c raw class | exact | "0" | "0" |  | match |  |
| K-83 | C1 D-e meets | exact | false | false |  | match |  |
| K-83 | C2 D-e meets | exact | false | false |  | match |  |
| K-83 | C4 D-e meets | exact | false | false |  | match |  |
| K-90 | D-a grade | exact | "ZA-2" | "ZA-2" |  | match |  |
| K-90 | D-a raw | exact | "ZA-2" | "ZA-2" |  | match |  |
| K-90 | D-a corr | exact | "ZA-2" | "ZA-2" |  | match |  |
| K-91 | D-a Z_ch | m | 0.0133369797696631 | 0.0133369797696631 | 0 | match |  |
| K-91 | D-a Z_corr | m | 0.0114809576024607 | 0.0114809576024607 | 0 | match |  |
| K-91 | D-a Z_hn | m | 0.00716820157194936 | 0.00716820157194936 | 0 | match |  |
| K-92 | D-a rows | exact | ["C1", "C2", "C3", "C4", "C5"] | ["C1", "C2", "C3", "C4", "C5"] |  | match |  |
| K-94 | D-b grade | exact | "OS-MAX" | "OS-MAX" |  | match |  |
| K-94 | D-b O | m | 0.0231972097068885 | 0.0231972097068885 | 0 | match |  |
| K-95 | D-b rows | exact | ["C1", "C2", "C3"] | ["C1", "C2", "C3"] |  | match |  |
| K-95 | D-b dropped | exact | ["C4", "C5"] | ["C4", "C5"] |  | match |  |
| K-96 | D-c grade | exact | "H-OPT" | "H-OPT" |  | match |  |
| K-96 | D-c raw grade | exact | "H-OPT" | "H-OPT" |  | match |  |
| K-97 | C1 D-c raw_m | m | -0.00223453464348833 | -0.00223453464348833 | 0 | match |  |
| K-97 | C1 D-c corr_low_m | m | -0.00401696817354008 | -0.00401696817354008 | 0 | match |  |
| K-97 | C1 D-c corr_high_m | m | -0.00401696817354008 | -0.00401696817354008 | 0 | match |  |
| K-98 | C1 D-c substitute | exact | false | false |  | match |  |
| K-98 | C1 D-c node step | exact | false | false |  | match |  |
| K-97 | C2 D-c raw_m | m | 0.0094596807955678 | 0.0094596807955678 | 0 | match |  |
| K-97 | C2 D-c corr_low_m | m | 0.00861433885474003 | 0.00861433885474003 | 0 | match |  |
| K-97 | C2 D-c corr_high_m | m | 0.00861433885474003 | 0.00861433885474003 | 0 | match |  |
| K-98 | C2 D-c substitute | exact | false | false |  | match |  |
| K-98 | C2 D-c node step | exact | false | false |  | match |  |
| K-97 | C3 D-c raw_m | m | 0.0123214508243965 | 0.0123214508243965 | 0 | match |  |
| K-97 | C3 D-c corr_low_m | m | 0.00782488637824267 | 0.00782488637824267 | 0 | match |  |
| K-97 | C3 D-c corr_high_m | m | 0.015041594748613 | 0.015041594748613 | 0 | match |  |
| K-98 | C3 D-c substitute | exact | true | true |  | match |  |
| K-98 | C3 D-c node step | exact | false | false |  | match |  |
| K-97 | C4 D-c raw_m | m | -0.00123121032403872 | -0.00123121032403872 | 0 | match |  |
| K-97 | C4 D-c corr_low_m | m | -0.00654096333328868 | -0.00654096333328868 | 0 | match |  |
| K-97 | C4 D-c corr_high_m | m | 0.00198086248402606 | 0.00198086248402606 | 0 | match |  |
| K-98 | C4 D-c substitute | exact | true | true |  | match |  |
| K-98 | C4 D-c node step | exact | false | false |  | match |  |
| K-97 | C5 D-c raw_m | m | 0.000847457748429759 | 0.000847457748429759 | 0 | match |  |
| K-97 | C5 D-c corr_low_m | m | 0.0024594990770412 | 0.0024594990770412 | 0 | match |  |
| K-97 | C5 D-c corr_high_m | m | 0.0024594990770412 | 0.0024594990770412 | 0 | match |  |
| K-98 | C5 D-c substitute | exact | false | false |  | match |  |
| K-98 | C5 D-c node step | exact | false | false |  | match |  |
| K-99 | D-c rows | exact | ["C1", "C2", "C3", "C4", "C5"] | ["C1", "C2", "C3", "C4", "C5"] |  | match |  |
| K-100 | D-d grade | exact | "PRED-FAIL" | "PRED-FAIL" |  | match |  |
| K-100 | D-d q* | exact | "P-A" | "P-A" |  | match |  |
| K-100 | D-d E P-A | m | 0.0273895301493281 | 0.0273895301493281 | 0 | match |  |
| K-100 | D-d E P-B | m | 0.0286672616182043 | 0.0286672616182043 | 0 | match |  |
| K-100 | D-d E P-D | m | 0.0273895301493281 | 0.0273895301493281 | 0 | match |  |
| K-100 | D-d E P-G | m | 0.0308618952458699 | 0.0308618952458699 | 0 | match |  |
| K-100 | D-d E P-C | m | 0.0485220494746953 | 0.0485220494746953 | 0 | match |  |
| K-101 | D-d rows | exact | ["C1", "C2", "C3", "C4", "C5"] | ["C1", "C2", "C3", "C4", "C5"] |  | match |  |
| K-101 | D-d T-14 excluded | exact | [] | [] |  | match |  |
| K-102 | D-e grade | exact | "B1-OPEN" | "B1-OPEN" |  | match |  |
| K-102 | D-e rows | exact | ["C1", "C2", "C4"] | ["C1", "C2", "C4"] |  | match |  |
| K-103 | C1 D-e g_m | m | 0.00262351064822863 | 0.00262351064822863 | 0 | match |  |
| K-103 | C1 D-e g_corr_m | m | 0.00440594417828038 | 0.00440594417828038 | 0 | match |  |
| K-103 | C1 D-e g_tilde_m | m | 0.000109955099767187 | 0.000109955099767187 | 0 | match |  |
| K-103 | C1 D-e sgs | exact | false | false |  | match |  |
| K-103 | C2 D-e g_m | m | 0.00387077342831199 | 0.00387077342831199 | 0 | match |  |
| K-103 | C2 D-e g_corr_m | m | 0.00471611536913977 | 0.00471611536913977 | 0 | match |  |
| K-103 | C2 D-e g_tilde_m | m | 0.000333969033346012 | 0.000333969033346012 | 0 | match |  |
| K-103 | C2 D-e sgs | exact | false | false |  | match |  |
| K-103 | C4 D-e g_m | m | 0.00160274259524362 | 0.00160274259524362 | 0 | match |  |
| K-103 | C4 D-e g_corr_m | m | null | null |  | both_NA |  |
| K-103 | C4 D-e g_tilde_m | m | -0.0070946328339078 | -0.0070946328339078 | 0 | match |  |
| K-103 | C4 D-e sgs | exact | true | true |  | match |  |
| K-104 | D-f grade | exact | "FUP-OUT" | "FUP-OUT" |  | match |  |
| K-105 | D-f pair count | exact | 2 | 2 |  | match |  |
| K-106 | D-g grade | exact | "W-NA" | "W-NA" |  | match |  |
| K-106 | D-g e_C6_m | m | null | null |  | both_NA | P1 key absent P2 key absent |
| K-106 | D-g E_q_star_m | m | null | null |  | both_NA | P1 key absent P2 key absent |
| K-106 | D-g ratio | rel | null | null |  | both_NA | P1 key absent P2 key absent |
| K-107 | D-g rows (P1 ['C6'], P2 grade W-NA, no list) | - | null | null |  | no_counterpart | map K-107 convention covers only non-W-NA; P2 outputs no row list |
| K-108 | D-h grade | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | D-h list sizes sum | exact | 20 | 20 |  | match |  |
| K-109 | H-P\|C1\|V0\|e0.002 (D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C1\|V0\|e0 (D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C2\|V0\|e0 (D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|V0\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C2\|V0\|e0.002 (D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|V0\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C3\|V0\|e0 (D1\|H-S-0\|J2\|T\|fdown-rec\|K1\|V0\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C1\|VB\|e0 (D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|VB\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C3\|V0\|e0.002 (D1\|H-S-0\|J2\|T\|fdown-rec\|K1\|V0\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C2\|VB\|e0.002 (D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|VB\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C1\|VB\|e0.002 (D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|VB\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C2\|VB\|e0 (D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|VB\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C4\|V0\|e0.002 (D1\|H-S-0\|J2\|B\|diag-rec\|K1\|V0\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C4\|V0\|e0 (D1\|H-S-0\|J2\|B\|diag-rec\|K1\|V0\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C3\|VB\|e0 (D1\|H-S-0\|J2\|T\|fdown-rec\|K1\|VB\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C3\|VB\|e0.002 (D1\|H-S-0\|J2\|T\|fdown-rec\|K1\|VB\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C5\|V0\|e0 (D1\|H-S-0\|J2\|T\|fup-rec\|K1\|V0\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C5\|V0\|e0.002 (D1\|H-S-0\|J2\|T\|fup-rec\|K1\|V0\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C5\|VB\|e0 (D1\|H-S-0\|J2\|T\|fup-rec\|K1\|VB\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C4\|VB\|e0 (D1\|H-S-0\|J2\|B\|diag-rec\|K1\|VB\|e0) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C4\|VB\|e0.002 (D1\|H-S-0\|J2\|B\|diag-rec\|K1\|VB\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |
| K-109 | H-P\|C5\|VB\|e0.002 (D1\|H-S-0\|J2\|T\|fup-rec\|K1\|VB\|e0.002) | exact | "K-SAME" | "K-SAME" |  | match |  |

## 대응표 밖 점검

- P1.constants == b1_harness_constants_rev1.json: `false`
- P2.constants == b1_constants_path2_rev1_run.json: `true`
- harness jsonl lines: `32`
- pad_nodes P1 consistent / P2 mismatch: `{"C1": [true, false], "C2": [true, false], "C3": [true, false], "C4": [true, false], "C5": [true, false], "C6": [true, false]}`
- K-93 (excluded) D-a harness correction: `[null, 0.006168778197713762]`
- D-d lower bound flag (U-12): `[["하한 포함"], {"C1": false, "C2": false, "C3": false, "C4": true, "C5": true}, false]`
- row counts per grade P1: `{"D-a": 5, "D-b": 3, "D-c": 5, "D-d": 5, "D-e": 3, "D-f": 3, "D-g": 1, "D-h": 20}`
- rows per grade P1: `{"D-a": ["C1", "C2", "C3", "C4", "C5"], "D-b": ["C1", "C2", "C3"], "D-c": ["C1", "C2", "C3", "C4", "C5"], "D-d": ["C1", "C2", "C3", "C4", "C5"], "D-e": ["C1", "C2", "C4"], "D-f": ["C5", "H-M0|C5|VB|e0", "H-M0|C5|V0|e0"], "D-g": ["C6"], "D-h": ["H-P|C1|V0|e0", "H-P|C1|V0|e0.002", "H-P|C1|VB|e0", "H-P|C1|VB|e0.002", "H-P|C2|V0|e0", "H-P|C2|V0|e0.002", "H-P|C2|VB|e0", "H-P|C2|VB|e0.002", "H-P|C3|V0|e0", "H-P|C3|V0|e0.002", "H-P|C3|VB|e0", "H-P|C3|VB|e0.002", "H-P|C4|V0|e0", "H-P|C4|V0|e0.002", "H-P|C4|VB|e0", "H-P|C4|VB|e0.002", "H-P|C5|V0|e0", "H-P|C5|V0|e0.002", "H-P|C5|VB|e0", "H-P|C5|VB|e0.002"]}`
- rows per grade P2: `{"D-a": ["C1", "C2", "C3", "C4", "C5"], "D-b": ["C1", "C2", "C3", "C4", "C5"], "D-c": ["C1", "C2", "C3", "C4", "C5"], "D-d": ["C1", "C2", "C3", "C4", "C5"], "D-e": ["C1", "C2", "C4"], "D-f": "<object object at 0x000002509D330430>", "D-g": "<object object at 0x000002509D330430>", "D-h": "<object object at 0x000002509D330430>"}`
