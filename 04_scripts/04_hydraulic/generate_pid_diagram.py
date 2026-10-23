"""
Piping and Instrumentation Diagram (P&ID) Generator
Project: REXOME35 Heavy-Duty Pile Driver Outrigger Hydraulic Control System
Location: C:/workspace/outrigger_control

Standard: ANSI/ISA-5.1 Instrumentation Symbols and Identification
Outputs:
  - C:/workspace/outrigger_control/00_docs/02_hydraulic/outrigger_pid_diagram.png (High-Res 300 DPI)
  - C:/workspace/논문작성/figures/outrigger_pid_diagram.png (300 DPI)
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, Wedge, PathPatch
import matplotlib.path as mpath
import numpy as np

# Font settings
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

def draw_pid():
    fig = plt.figure(figsize=(26, 16), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 260)
    ax.set_ylim(0, 160)
    ax.axis('off')

    # Background color: Blueprint/Modern Technical Drafting Off-White
    bg_color = "#FCFDFE"
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    # -------------------------------------------------------------------------
    # 0. Engineering Drawing Border & Title Block (P&ID Sheet Standard)
    # -------------------------------------------------------------------------
    # Outer Border
    ax.add_patch(Rectangle((3, 3), 254, 154, fill=False, edgecolor="#263238", linewidth=2.5))
    # Inner Border
    ax.add_patch(Rectangle((5, 5), 250, 150, fill=False, edgecolor="#37474F", linewidth=1.2))

    # Grid references (A-E, 1-8)
    for i, char in enumerate(['E', 'D', 'C', 'B', 'A']):
        y = 5 + (i + 0.5) * 30
        ax.text(4, y, char, ha='center', va='center', fontsize=9, fontweight='bold', color='#546E7A')
        ax.text(256, y, char, ha='center', va='center', fontsize=9, fontweight='bold', color='#546E7A')
    for j in range(8):
        x = 5 + (j + 0.5) * 31.25
        ax.text(x, 4, str(j + 1), ha='center', va='center', fontsize=9, fontweight='bold', color='#546E7A')
        ax.text(x, 156, str(j + 1), ha='center', va='center', fontsize=9, fontweight='bold', color='#546E7A')

    # Title Block (Bottom Right: x: 195 to 255, y: 5 to 30)
    tb = Rectangle((192, 5), 63, 27, facecolor='#ECEFF1', edgecolor='#263238', linewidth=1.5, zorder=5)
    ax.add_patch(tb)
    ax.plot([192, 255], [24, 24], color='#263238', lw=1.2, zorder=6)
    ax.plot([192, 255], [17, 17], color='#263238', lw=1.0, zorder=6)
    ax.plot([192, 255], [11, 11], color='#263238', lw=1.0, zorder=6)
    ax.plot([223, 223], [5, 24], color='#263238', lw=1.0, zorder=6)

    ax.text(223.5, 27.2, "PIPING & INSTRUMENTATION DIAGRAM (P&ID)",
            ha='center', va='center', fontsize=9.5, fontweight='bold', color='#0D47A1', zorder=7)
    ax.text(223.5, 25.4, "아우트리거 4점 지지 유압 구동계 및 전자제어 계장 배관도",
            ha='center', va='center', fontsize=8, fontweight='bold', color='#263238', zorder=7)
    
    ax.text(194, 20.5, "PROJECT: REXOME35 Pile Driver", ha='left', va='center', fontsize=7.2, fontweight='bold', color='#37474F', zorder=7)
    ax.text(194, 18.5, "SYSTEM: 4-Point Outrigger Levelling", ha='left', va='center', fontsize=6.8, color='#546E7A', zorder=7)
    ax.text(225, 20.5, "DWG NO: PID-HYD-OUT-001", ha='left', va='center', fontsize=7.2, fontweight='bold', color='#1A237E', zorder=7)
    ax.text(225, 18.5, "REVISION: Rev. 2.0 (REXOME35)", ha='left', va='center', fontsize=6.8, color='#37474F', zorder=7)

    ax.text(194, 14, "DATE: 2026-10-23", ha='left', va='center', fontsize=6.8, color='#37474F', zorder=7)
    ax.text(225, 14, "FLUID: ISO VG 46 Mineral Oil", ha='left', va='center', fontsize=6.8, color='#37474F', zorder=7)
    ax.text(194, 8, "DESIGN PRES: 210 / 350 bar", ha='left', va='center', fontsize=6.8, fontweight='bold', color='#C62828', zorder=7)
    ax.text(225, 8, "STANDARDS: ANSI/ISA-5.1 / ISO 1219", ha='left', va='center', fontsize=6.5, color='#37474F', zorder=7)

    # -------------------------------------------------------------------------
    # 1. Legend & Symbol Box (Top Right: x: 192 to 255, y: 110 to 153)
    # -------------------------------------------------------------------------
    leg_box = FancyBboxPatch((192, 114), 63, 39, boxstyle="round,pad=0.2,rounding_size=0.8",
                             facecolor='#FFFFFF', edgecolor='#455A64', linewidth=1.2, zorder=5)
    ax.add_patch(leg_box)
    ax.text(223.5, 150.5, "■ P&ID 기호 및 라인 범례 (LEGEND)", ha='center', va='center',
            fontsize=9, fontweight='bold', color='#1A237E', zorder=6)

    # Line conventions
    lines_legend = [
        ("고압 공급 라인 (P 라인, 1/2\" SAE 100R15, 210 bar)", "#C62828", "-", 2.5),
        ("저압 리턴 라인 (T 라인, 3/4\" Low Pressure, 2 bar)", "#1565C0", "-", 2.0),
        ("실린더 작업 라인 (A/B 라인, 3/8\" Hose, 210~350 bar)", "#2E7D32", "-", 1.8),
        ("로드센싱 / 파일럿 라인 (LS / Pilot Line, 1/4\")", "#E65100", "--", 1.4),
        ("전기 / 제어 신호선 (4~20mA / CAN Bus / PWM)", "#6A1B9A", ":", 1.5)
    ]
    for idx, (label, color, ls, lw) in enumerate(lines_legend):
        y_pos = 145 - idx * 4.2
        ax.plot([194, 203], [y_pos, y_pos], color=color, linestyle=ls, linewidth=lw, zorder=6)
        ax.text(205, y_pos, label, ha='left', va='center', fontsize=6.8, color='#263238', zorder=6)

    # Symbols legend
    ax.text(194, 122.5, "ISA 계측 태그: PT (압력전송기), ZT (변위센서), AT (자세IMU)", ha='left', va='center', fontsize=6.6, fontweight='bold', color='#37474F', zorder=6)
    ax.text(194, 118.5, "밸브 태그: PSV (릴리프), FV (비례제어), POC (파일럿체크), CBV (오버락)", ha='left', va='center', fontsize=6.6, fontweight='bold', color='#37474F', zorder=6)
    ax.text(194, 115.5, "제어기 태그: JC-500 (자세·비틀림 레벨링 마스터 제어기)", ha='left', va='center', fontsize=6.6, fontweight='bold', color='#0D47A1', zorder=6)

    # Helper function to draw ISA instrument bubble
    def draw_instrument(x, y, tag_prefix, loop_num, line_type='panel', color='#1A237E', bg='#FFFFFF'):
        circ = Circle((x, y), 3.2, facecolor=bg, edgecolor=color, linewidth=1.3, zorder=10)
        ax.add_patch(circ)
        if line_type == 'panel': # Shared controller/display (horizontal line in middle)
            ax.plot([x - 3.2, x + 3.2], [y, y], color=color, lw=1.0, zorder=11)
            ax.text(x, y + 1.2, tag_prefix, ha='center', va='center', fontsize=6.2, fontweight='bold', color=color, zorder=12)
            ax.text(x, y - 1.2, loop_num, ha='center', va='center', fontsize=5.8, fontweight='bold', color=color, zorder=12)
        elif line_type == 'field': # Field mounted (no line)
            ax.text(x, y + 1.0, tag_prefix, ha='center', va='center', fontsize=6.2, fontweight='bold', color=color, zorder=12)
            ax.text(x, y - 1.2, loop_num, ha='center', va='center', fontsize=5.8, fontweight='bold', color=color, zorder=12)
        elif line_type == 'plc': # PLC / computer function (square around circle or double line)
            sq = Rectangle((x - 3.5, y - 3.5), 7.0, 7.0, facecolor='none', edgecolor=color, lw=1.0, zorder=11)
            ax.add_patch(sq)
            ax.text(x, y + 1.1, tag_prefix, ha='center', va='center', fontsize=6.0, fontweight='bold', color=color, zorder=12)
            ax.text(x, y - 1.2, loop_num, ha='center', va='center', fontsize=5.8, fontweight='bold', color=color, zorder=12)

    # Helper function for check valve symbol
    def draw_check_valve(x, y, direction='right', size=2.0, color='#37474F'):
        if direction == 'right':
            tri = Polygon([[x - size, y - size], [x - size, y + size], [x + size, y]], closed=True, facecolor='#ECEFF1', edgecolor=color, lw=1.2, zorder=8)
            ax.add_patch(tri)
            ax.plot([x + size, x + size], [y - size, y + size], color=color, lw=1.5, zorder=8)
        elif direction == 'up':
            tri = Polygon([[x - size, y - size], [x + size, y - size], [x, y + size]], closed=True, facecolor='#ECEFF1', edgecolor=color, lw=1.2, zorder=8)
            ax.add_patch(tri)
            ax.plot([x - size, x + size], [y + size, y + size], color=color, lw=1.5, zorder=8)
        elif direction == 'down':
            tri = Polygon([[x - size, y + size], [x + size, y + size], [x, y - size]], closed=True, facecolor='#ECEFF1', edgecolor=color, lw=1.2, zorder=8)
            ax.add_patch(tri)
            ax.plot([x - size, x + size], [y - size, y - size], color=color, lw=1.5, zorder=8)

    # -------------------------------------------------------------------------
    # 2. Main System Sections Layout
    # -------------------------------------------------------------------------
    # [SECTION 1] Hydraulic Power Supply Unit (HPU / Power Pack)
    # x: 8 to 55, y: 8 to 110
    hpu_rect = FancyBboxPatch((7, 8), 48, 102, boxstyle="round,pad=0.5,rounding_size=1.0",
                             facecolor='#F5F5F5', edgecolor='#78909C', lw=1.4, linestyle='--', zorder=1)
    ax.add_patch(hpu_rect)
    ax.text(31, 106.5, "【 UNIT 100 】 유압 동력원 유닛 (HYDRAULIC POWER PACK)",
            ha='center', va='center', fontsize=8.8, fontweight='bold', color='#37474F')

    # Reservoir T-101
    tank = Rectangle((12, 14), 38, 20, facecolor='#E1F5FE', edgecolor='#0277BD', lw=1.8, zorder=3)
    ax.add_patch(tank)
    ax.text(31, 24, "T-101 유압 오일 탱크 (Reservoir)\n용량: 250 L | 대기압 개방형 (Patm = 1.0 bar)\n작동유: ISO VG 46 (ρ = 860 kg/m³, β = 1.0 GPa)",
            ha='center', va='center', fontsize=7.2, fontweight='bold', color='#01579B', zorder=4)

    # Tank Level & Temp Indicators
    draw_instrument(16, 39, "LG", "101", line_type='field', color='#0277BD')
    draw_instrument(25, 39, "TI", "101", line_type='field', color='#0277BD')
    ax.plot([16, 16], [34, 35.8], color='#0277BD', lw=1.2, zorder=5)
    ax.plot([25, 25], [34, 35.8], color='#0277BD', lw=1.2, zorder=5)

    # Suction Strainer FLT-101
    ax.plot([31, 31], [34, 48], color='#1565C0', lw=2.2, zorder=4)
    flt_box = Rectangle((27, 43), 8, 5, facecolor='#CFD8DC', edgecolor='#37474F', lw=1.2, zorder=5)
    ax.add_patch(flt_box)
    ax.text(31, 45.5, "FLT-101\n100 Mesh", ha='center', va='center', fontsize=6.0, fontweight='bold', color='#263238', zorder=6)

    # Fixed Displacement Pump P-101
    pump_y = 62
    pump_c = Circle((31, pump_y), 6.5, facecolor='#FFFFFF', edgecolor='#0D47A1', lw=2.0, zorder=5)
    ax.add_patch(pump_c)
    tri_p = Polygon([[31, pump_y + 4.8], [27.5, pump_y - 2.5], [34.5, pump_y - 2.5]], closed=True, facecolor='#0D47A1', zorder=6)
    ax.add_patch(tri_p)
    ax.text(31, pump_y - 9.5, "P-101 메인 펌프 (P6)\nVg = 30 cc/rev (2000 rpm)\nQnom = 60.2 L/min",
            ha='center', va='center', fontsize=7.0, fontweight='bold', color='#0D47A1')

    # Engine / Motor Drive M-101
    ax.plot([17, 24.5], [pump_y, pump_y], color='#37474F', lw=2.0, zorder=4)
    eng = Circle((13, pump_y), 4.2, facecolor='#ECEFF1', edgecolor='#37474F', lw=1.5, zorder=5)
    ax.add_patch(eng)
    ax.text(13, pump_y, "M-101\n디젤/전동", ha='center', va='center', fontsize=6.2, fontweight='bold', color='#263238', zorder=6)

    # Suction check valve
    draw_check_valve(31, 55, direction='up', size=1.8, color='#0D47A1')

    # Pump discharge high pressure line P
    ax.plot([31, 31], [pump_y + 6.5, 96], color='#C62828', lw=2.8, zorder=4)
    ax.text(28, 88, "1/2\" 고압 공급선 (Line P)\n최대 210 bar", ha='right', va='center', fontsize=6.8, fontweight='bold', color='#C62828')

    # Pressure Indicator PI-101 & Transmitter PT-101 (M Port gauge)
    ax.plot([31, 18], [78, 78], color='#C62828', lw=1.5, zorder=4)
    draw_instrument(14, 78, "PI", "101", line_type='field', color='#C62828')
    ax.text(14, 83, "M 포트 압력계\n0~400 bar", ha='center', va='bottom', fontsize=6.0, color='#C62828')

    # Main Relief Valve PSV-101 (210 bar)
    ax.plot([31, 44], [84, 84], color='#C62828', lw=1.8, zorder=4)
    psv_box = Rectangle((40, 80), 8, 8, facecolor='#FFEBEE', edgecolor='#D32F2F', lw=1.5, zorder=5)
    ax.add_patch(psv_box)
    ax.plot([40, 48], [80, 88], color='#D32F2F', lw=1.2, zorder=6)
    ax.text(44, 76.5, "PSV-101\n주 릴리프 210 bar\n(오버라이드 218.6 bar)", ha='center', va='top', fontsize=6.5, fontweight='bold', color='#B71C1C')

    # Relief return line to Tank
    ax.plot([44, 44], [80, 34], color='#1565C0', lw=2.0, zorder=4)
    ax.plot([44, 38], [34, 34], color='#1565C0', lw=2.0, zorder=4)
    ax.text(45, 60, "3/4\" T 라인 (릴리프 드레인)", ha='left', va='center', rotation=90, fontsize=6.8, color='#1565C0', fontweight='bold')

    # Return Filter FLT-103 & Cooler HE-101 on T line
    return_x = 48
    ax.plot([55, return_x], [96, 96], color='#1565C0', lw=2.2, zorder=4)
    ax.plot([return_x, return_x], [96, 34], color='#1565C0', lw=2.2, zorder=4)
    ax.plot([return_x, 46], [34, 34], color='#1565C0', lw=2.2, zorder=4)

    flt_ret = Rectangle((return_x - 3.5, 48), 7, 6, facecolor='#CFD8DC', edgecolor='#1565C0', lw=1.2, zorder=5)
    ax.add_patch(flt_ret)
    ax.text(return_x, 51, "FLT-103\n10 μm 리턴", ha='center', va='center', fontsize=5.8, fontweight='bold', color='#0D47A1')

    # -------------------------------------------------------------------------
    # [SECTION 2] 4-Section Proportional Directional MCV Bank
    # x: 62 to 125, y: 8 to 110
    # -------------------------------------------------------------------------
    mcv_rect = FancyBboxPatch((60, 8), 66, 102, boxstyle="round,pad=0.5,rounding_size=1.0",
                              facecolor='#E8EAF6', edgecolor='#3949AB', lw=1.5, zorder=1)
    ax.add_patch(mcv_rect)
    ax.text(93, 106.5, "【 UNIT 200 】 4섹션 비례 방향 제어 밸브 뱅크 (PROPORTIONAL MCV BANK)",
            ha='center', va='center', fontsize=8.8, fontweight='bold', color='#1A237E')

    # Line P entering MCV manifold
    ax.plot([31, 64], [96, 96], color='#C62828', lw=2.8, zorder=4)
    ax.plot([64, 64], [96, 16], color='#C62828', lw=2.8, zorder=4) # Internal P Rail

    # Line T exiting MCV manifold
    ax.plot([68, 68], [16, 92], color='#1565C0', lw=2.2, zorder=4)
    ax.plot([68, 55], [92, 92], color='#1565C0', lw=2.2, zorder=4)
    ax.plot([55, 55], [92, 96], color='#1565C0', lw=2.2, zorder=4)

    # 4 Valve Sections (FL, FR, RL, RR)
    sections_info = [
        ("FL-201", "전방 좌 (FL)", 86, "#E8F5E9", "#2E7D32", "132.7 cm²", "17.54 L/min"),
        ("FR-202", "전방 우 (FR)", 64, "#E8F5E9", "#2E7D32", "132.7 cm²", "17.54 L/min"),
        ("RL-203", "후방 좌 (RL)", 42, "#FFF3E0", "#E65100", "95.0 cm²", "12.56 L/min"),
        ("RR-204", "후방 우 (RR)", 20, "#FFF3E0", "#E65100", "95.0 cm²", "12.56 L/min")
    ]

    for tag, desc, y_s, bg_c, bd_c, area, flow in sections_info:
        # Section Box
        s_box = FancyBboxPatch((72, y_s - 8), 52, 17, boxstyle="round,pad=0.2,rounding_size=0.6",
                               facecolor=bg_c, edgecolor=bd_c, lw=1.2, zorder=2)
        ax.add_patch(s_box)

        # 4/3 Valve Spool Symbol (3 envelopes)
        spool_x = 74
        spool_y = y_s - 5
        spool_w = 15
        spool_h = 10
        sp_rect = Rectangle((spool_x, spool_y), spool_w, spool_h, facecolor='#FFFFFF', edgecolor='#37474F', lw=1.2, zorder=3)
        ax.add_patch(sp_rect)
        ax.plot([spool_x + 5, spool_x + 5], [spool_y, spool_y + spool_h], color='#90A4AE', lw=0.9, zorder=4)
        ax.plot([spool_x + 10, spool_x + 10], [spool_y, spool_y + spool_h], color='#90A4AE', lw=0.9, zorder=4)

        # Solenoid symbols
        ax.add_patch(Rectangle((spool_x - 1.8, spool_y + 2), 1.8, 6, facecolor='#CFD8DC', edgecolor='#37474F', lw=0.8, zorder=3))
        ax.add_patch(Rectangle((spool_x + spool_w, spool_y + 2), 1.8, 6, facecolor='#CFD8DC', edgecolor='#37474F', lw=0.8, zorder=3))

        # Valve ports text inside symbol
        ax.text(spool_x + 2.5, spool_y + 5, "Ext", ha='center', va='center', fontsize=5.2, fontweight='bold', color='#2E7D32')
        ax.text(spool_x + 7.5, spool_y + 5, "Hold", ha='center', va='center', fontsize=5.0, fontweight='bold', color='#455A64')
        ax.text(spool_x + 12.5, spool_y + 5, "Ret", ha='center', va='center', fontsize=5.2, fontweight='bold', color='#C62828')

        # Local Pressure Compensator PCV & LS shuttle
        pcv = Circle((spool_x + 22, spool_y + 5), 2.8, facecolor='#FFF9C4', edgecolor='#FBC02D', lw=1.2, zorder=4)
        ax.add_patch(pcv)
        ax.text(spool_x + 22, spool_y + 5, "PCV", ha='center', va='center', fontsize=5.0, fontweight='bold', color='#F57F17')

        # Section Info Text
        ax.text(spool_x + 27, y_s + 4.2, f"FV-{tag[-3:]} : {desc}", ha='left', va='center', fontsize=7.2, fontweight='bold', color=bd_c)
        ax.text(spool_x + 27, y_s + 0.8, f"4/3 비례 서보 | 불감대 12% | τv=30ms", ha='left', va='center', fontsize=6.2, color='#37474F')
        ax.text(spool_x + 27, y_s - 2.4, f"설계 유효면적: Ap = {area} | Qmax = {flow}", ha='left', va='center', fontsize=6.0, color='#546E7A')
        ax.text(spool_x + 27, y_s - 5.5, f"공통 속도 상한: vmax = 22.026 mm/s", ha='left', va='center', fontsize=5.8, fontweight='bold', color='#0D47A1')

        # Connection from P & T rails to this valve
        ax.plot([64, spool_x], [y_s - 2, y_s - 2], color='#C62828', lw=1.5, zorder=3) # P tap
        ax.plot([68, spool_x], [y_s - 4, y_s - 4], color='#1565C0', lw=1.2, zorder=3) # T tap

        # Outflow Ports A and B lines (Exiting MCV to the right)
        ax.plot([spool_x + spool_w + 1.8, 126], [y_s + 2, y_s + 2], color='#2E7D32', lw=2.0, zorder=4) # A
        ax.plot([spool_x + spool_w + 1.8, 126], [y_s - 2, y_s - 2], color='#1565C0', lw=1.8, zorder=4) # B
        ax.text(125, y_s + 3.5, "Port A (3/8\" Hose)", ha='right', va='center', fontsize=5.5, fontweight='bold', color='#2E7D32')
        ax.text(125, y_s - 3.5, "Port B (3/8\" Hose)", ha='right', va='center', fontsize=5.5, color='#1565C0')

        # Instrument loop bubble for Proportional Valve Actuator FY
        draw_instrument(spool_x + 9, y_s + 7.5, "FY", tag[-3:], line_type='plc', color='#6A1B9A', bg='#F3E5F5')
        ax.plot([spool_x + 9, spool_x + 9], [spool_y + spool_h, y_s + 4.5], color='#6A1B9A', linestyle=':', lw=1.2, zorder=4)

    # -------------------------------------------------------------------------
    # [SECTION 3] Cylinder Direct-Mount Lock Valve Blocks & Sensors
    # x: 133 to 175, y: 8 to 110
    # -------------------------------------------------------------------------
    lkv_rect = FancyBboxPatch((130, 8), 44, 102, boxstyle="round,pad=0.5,rounding_size=1.0",
                             facecolor='#FFFDE7', edgecolor='#FBC02D', lw=1.4, zorder=1)
    ax.add_patch(lkv_rect)
    ax.text(152, 106.5, "【 UNIT 300 】 실린더 직결 로크 밸브 블록 (LOCK VALVE & SENSORS)",
            ha='center', va='center', fontsize=8.8, fontweight='bold', color='#F57F17')

    # Draw 4 Lock Valve Blocks corresponding to the 4 sections
    for tag, desc, y_s, bg_c, bd_c, area, flow in sections_info:
        blk_x = 132
        blk_w = 40
        blk_h = 17
        blk_y = y_s - 8

        b_card = FancyBboxPatch((blk_x, blk_y), blk_w, blk_h, boxstyle="round,pad=0.2,rounding_size=0.5",
                                facecolor='#FFFFFF', edgecolor='#FF8F00', lw=1.2, zorder=2)
        ax.add_patch(b_card)

        # Lines A and B coming in from MCV
        ax.plot([126, blk_x + 4], [y_s + 2, y_s + 2], color='#2E7D32', lw=2.0, zorder=3)
        ax.plot([126, blk_x + 4], [y_s - 2, y_s - 2], color='#1565C0', lw=1.8, zorder=3)

        # Dual Pilot-Operated Check Valves (POC-A, POC-B)
        draw_check_valve(blk_x + 8, y_s + 2, direction='right', size=1.6, color='#2E7D32')
        draw_check_valve(blk_x + 8, y_s - 2, direction='right', size=1.6, color='#1565C0')
        ax.text(blk_x + 8, y_s + 5.2, "POC-A", ha='center', va='bottom', fontsize=5.2, fontweight='bold', color='#2E7D32')
        ax.text(blk_x + 8, y_s - 5.2, "POC-B", ha='center', va='top', fontsize=5.2, fontweight='bold', color='#1565C0')

        # Pilot cross lines (Pilot ratio 3.5:1, Cracking 3 bar)
        ax.plot([blk_x + 6, blk_x + 8], [y_s + 2, y_s - 2], color='#E65100', linestyle='--', lw=1.0, zorder=4)
        ax.plot([blk_x + 6, blk_x + 8], [y_s - 2, y_s + 2], color='#E65100', linestyle='--', lw=1.0, zorder=4)

        # Counterbalance Valve CBV (350 bar)
        cbv_box = Rectangle((blk_x + 13, y_s - 0.5), 5.5, 5, facecolor='#FFEBEE', edgecolor='#C62828', lw=1.0, zorder=4)
        ax.add_patch(cbv_box)
        ax.text(blk_x + 15.7, y_s + 2, "CBV\n350b", ha='center', va='center', fontsize=4.8, fontweight='bold', color='#B71C1C')

        # WIKA A-10 Pressure Transmitters (PT-A on Head, PT-B on Rod)
        pt_a_x = blk_x + 25
        pt_a_y = y_s + 4.5
        draw_instrument(pt_a_x, pt_a_y, "PT", f"{tag[-3:]}A", line_type='field', color='#0D47A1')
        ax.plot([blk_x + 16, pt_a_x], [y_s + 2, pt_a_y - 3.2], color='#0D47A1', lw=1.0, zorder=3)

        pt_b_x = blk_x + 34
        pt_b_y = y_s - 4.5
        draw_instrument(pt_b_x, pt_b_y, "PT", f"{tag[-3:]}B", line_type='field', color='#0277BD')
        ax.plot([blk_x + 16, pt_b_x], [y_s - 2, pt_b_y + 3.2], color='#0277BD', lw=1.0, zorder=3)

        # Text specs
        ax.text(blk_x + 20, y_s - 6.2, "WIKA A-10 (0~400 bar, 4~20mA)", ha='left', va='center', fontsize=5.0, color='#37474F')

        # Lines going directly to cylinder ports
        ax.plot([blk_x + 16, 172], [y_s + 2, y_s + 2], color='#C62828', lw=2.2, zorder=4) # Head line C1
        ax.plot([blk_x + 16, 172], [y_s - 2, y_s - 2], color='#1565C0', lw=1.8, zorder=4) # Rod line C2

    # -------------------------------------------------------------------------
    # [SECTION 4] Hydraulic Outrigger Cylinders & Contact Pads
    # x: 178 to 252, y: 8 to 110
    # -------------------------------------------------------------------------
    cyl_rect = FancyBboxPatch((176, 8), 76, 102, boxstyle="round,pad=0.5,rounding_size=1.0",
                             facecolor='#E0F2F1', edgecolor='#00897B', lw=1.4, zorder=1)
    ax.add_patch(cyl_rect)
    ax.text(214, 106.5, "【 UNIT 400 】 아우트리거 복동 실린더 및 접지 메커니즘 (CYLINDERS & PADS)",
            ha='center', va='center', fontsize=8.8, fontweight='bold', color='#004D40')

    cylinders_spec = [
        ("CYL-401", "전방 좌 (FL)", 86, "ø130 / ø110 mm", "s=700 mm", "278.7 kN (신장) / 464.6 kN (350b)"),
        ("CYL-402", "전방 우 (FR)", 64, "ø130 / ø110 mm", "s=700 mm", "278.7 kN (신장) / 464.6 kN (350b)"),
        ("CYL-403", "후방 좌 (RL)", 42, "ø110 / ø90 mm", "s=700 mm", "199.6 kN (신장) / 332.6 kN (350b)"),
        ("CYL-404", "후방 우 (RR)", 20, "ø110 / ø90 mm", "s=700 mm", "199.6 kN (신장) / 332.6 kN (350b)")
    ]

    for tag, desc, y_s, bore_rod, stroke, force_cap in cylinders_spec:
        # Cylinder barrel
        c_barrel_x = 180
        c_barrel_w = 28
        c_barrel_h = 10
        c_barrel_y = y_s - 5

        barrel = Rectangle((c_barrel_x, c_barrel_y), c_barrel_w, c_barrel_h, facecolor='#ECEFF1', edgecolor='#263238', lw=1.5, zorder=3)
        ax.add_patch(barrel)

        # Connection from lock block to cylinder ports
        ax.plot([172, c_barrel_x + 4], [y_s + 2, y_s + 2], color='#C62828', lw=2.2, zorder=4)
        ax.plot([172, c_barrel_x + 24], [y_s - 2, y_s - 2], color='#1565C0', lw=1.8, zorder=4)
        ax.plot([c_barrel_x + 4, c_barrel_x + 4], [y_s + 2, c_barrel_y + c_barrel_h], color='#C62828', lw=2.2, zorder=4) # Port A
        ax.plot([c_barrel_x + 24, c_barrel_x + 24], [y_s - 2, c_barrel_y + c_barrel_h], color='#1565C0', lw=1.8, zorder=4) # Port B

        # Piston & Rod (at extension s ~ 40%)
        p_pos = c_barrel_x + 12
        piston = Rectangle((p_pos, c_barrel_y + 0.6), 3.0, c_barrel_h - 1.2, facecolor='#546E7A', edgecolor='#263238', lw=1.2, zorder=5)
        ax.add_patch(piston)

        # Rod extending right
        rod_w = 26
        rod_h = 5.0
        rod = Rectangle((p_pos + 3.0, y_s - 2.5), rod_w, rod_h, facecolor='#B0BEC5', edgecolor='#37474F', lw=1.2, zorder=4)
        ax.add_patch(rod)

        # Chamber A fill (Red)
        head_vol = Rectangle((c_barrel_x + 0.5, c_barrel_y + 0.6), (p_pos - c_barrel_x - 0.5), c_barrel_h - 1.2,
                             facecolor='#FFCDD2', edgecolor='none', alpha=0.6, zorder=3)
        ax.add_patch(head_vol)
        ax.text((c_barrel_x + p_pos)/2, y_s, "VA", ha='center', va='center', fontsize=5.5, fontweight='bold', color='#B71C1C', zorder=6)

        # Chamber B fill (Blue)
        ax.text(c_barrel_x + 21, y_s + 2.8, "VB", ha='center', va='center', fontsize=5.2, fontweight='bold', color='#0D47A1', zorder=6)

        # Swivel Ball Joint & Contact Pad
        pad_x = p_pos + 3.0 + rod_w
        pad_ball = Circle((pad_x, y_s), 2.2, facecolor='#FFD54F', edgecolor='#FF8F00', lw=1.2, zorder=6)
        ax.add_patch(pad_ball)

        # Contact Pad Plate (ø450 mm octagon / circular)
        pad_plate = FancyBboxPatch((pad_x + 1.2, y_s - 6), 2.0, 12, boxstyle="round,pad=0.2,rounding_size=0.4",
                                  facecolor='#FFA000', edgecolor='#E65100', lw=1.4, zorder=7)
        ax.add_patch(pad_plate)
        ax.text(pad_x + 2.2, y_s, "패드\nø450", ha='center', va='center', fontsize=4.8, fontweight='bold', color='#FFFFFF', zorder=8)

        # Ground Surface Hatch
        ax.plot([pad_x + 3.4, pad_x + 3.4], [y_s - 7, y_s + 7], color='#5D4037', lw=2.0, zorder=6)
        for gy in np.linspace(y_s - 6.5, y_s + 6.5, 7):
            ax.plot([pad_x + 3.4, pad_x + 5.0], [gy, gy + 1.2], color='#8D6E63', lw=1.0, zorder=5)

        # Stroke Position Transmitter ZT
        zt_x = c_barrel_x + 14
        zt_y = y_s - 8.2
        draw_instrument(zt_x, zt_y, "ZT", tag[-3:], line_type='field', color='#4527A0')
        ax.plot([p_pos + 1.5, zt_x], [c_barrel_y, zt_y + 3.2], color='#4527A0', linestyle=':', lw=1.0, zorder=4)

        # Cylinder Specifications Text
        ax.text(c_barrel_x + 2, y_s + 6.8, f"● {tag} ({desc}) : {bore_rod}", ha='left', va='center', fontsize=6.8, fontweight='bold', color='#004D40')
        ax.text(c_barrel_x + 29, y_s - 6.8, f"Fmax: {force_cap}", ha='left', va='center', fontsize=5.8, color='#37474F')

    # -------------------------------------------------------------------------
    # [SECTION 5] Automation & Master Controller JC-500 Architecture (Top Area)
    # x: 60 to 180, y: 114 to 153
    # -------------------------------------------------------------------------
    ctrl_rect = FancyBboxPatch((60, 114), 126, 39, boxstyle="round,pad=0.5,rounding_size=1.0",
                               facecolor='#EDE7F6', edgecolor='#512DA8', lw=1.5, zorder=1)
    ax.add_patch(ctrl_rect)
    ax.text(123, 150.5, "【 UNIT 500 】 전자동 아우트리거 레벨링 마스터 컨트롤러 (JC-500 CONTROLLER)",
            ha='center', va='center', fontsize=9.2, fontweight='bold', color='#311B92')

    # Master Controller Box (PLC / Industrial Controller)
    plc_x = 100
    plc_y = 120
    plc_w = 46
    plc_h = 24
    plc_box = FancyBboxPatch((plc_x, plc_y), plc_w, plc_h, boxstyle="round,pad=0.3,rounding_size=0.6",
                             facecolor='#FFFFFF', edgecolor='#512DA8', lw=1.8, zorder=3)
    ax.add_patch(plc_box)

    ax.text(plc_x + plc_w/2, plc_y + plc_h - 3.5, "JC-500 / AIC-500 : 마스터 제어기",
            ha='center', va='center', fontsize=8.2, fontweight='bold', color='#311B92', zorder=4)
    ctrl_desc = (
        "● C2 자세·비틀림 이중 루프 (Kinematics Decoupling + Twist Null-Space)\n"
        "● 4점 하중 불균형 능동 해소 (n^T·P = 0 균등화, Ktwist = 0.5 s^-1)\n"
        "● 최소 접지력 가드 (Fmin = 9.45 kN) & 결합 탐침 시퀀스 (S6/S8)\n"
        "● 실행 주기: T = 20 ms (50 Hz) | 독립 2중 교차검증 (Julia PM=60.25°)"
    )
    ax.text(plc_x + 2, plc_y + 10.5, ctrl_desc, ha='left', va='center', fontsize=6.2, color='#263238', linespacing=1.35, zorder=4)

    # Attitude Sensor AT-100 (IMU)
    draw_instrument(72, 134, "AT", "100", line_type='field', color='#512DA8')
    ax.text(72, 142, "차체 2축 경사각 IMU\n(Roll φ, Pitch θ)", ha='center', va='bottom', fontsize=6.2, fontweight='bold', color='#512DA8')
    ax.annotate('', xy=(plc_x, 134), xytext=(75.5, 134),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#512DA8', linestyle=':'))

    # Auger Mast Elevation Sensor ZT-100
    draw_instrument(88, 126, "ZT", "100", line_type='field', color='#512DA8')
    ax.text(88, 118, "오거 마스트 승강 위치\n(zCoG = 0.78~1.94 m)", ha='center', va='top', fontsize=5.8, color='#512DA8')
    ax.annotate('', xy=(plc_x, 126), xytext=(91.5, 126),
                arrowprops=dict(arrowstyle='->', lw=1.2, color='#512DA8', linestyle=':'))

    # Signal Routing from Sensors (PT-401..404, ZT-401..404) to JC-500
    # Pressure signal bus (Purple dashed)
    ax.plot([156, 156], [98, 130], color='#6A1B9A', linestyle=':', lw=1.5, zorder=3)
    ax.plot([156, plc_x + plc_w], [130, 130], color='#6A1B9A', linestyle=':', lw=1.5, zorder=3)
    ax.text(160, 131.5, "8ch 유압 센서 신호 (PT-401~404 A/B: 4~20mA)", ha='left', va='bottom', fontsize=6.0, fontweight='bold', color='#6A1B9A')

    # Stroke signal bus
    ax.plot([170, 170], [98, 124], color='#4527A0', linestyle=':', lw=1.5, zorder=3)
    ax.plot([170, plc_x + plc_w], [124, 124], color='#4527A0', linestyle=':', lw=1.5, zorder=3)
    ax.text(172, 125.5, "4ch 스트로크 신호 (ZT-401~404: 0~700mm)", ha='left', va='bottom', fontsize=6.0, fontweight='bold', color='#4527A0')

    # Control Output to MCV Solenoids (PWM command)
    ax.plot([115, 115], [plc_y, 98], color='#C2185B', linestyle=':', lw=1.8, zorder=3)
    ax.text(116, 102, "4-Ch 비례 솔레노이드 명령\n(PWM/Current: ui = s'_cmd)", ha='left', va='center', fontsize=6.0, fontweight='bold', color='#C2185B')

    # -------------------------------------------------------------------------
    # 3. Save Drawing as High-Resolution Image Files
    # -------------------------------------------------------------------------
    out_dir_doc = r"C:\workspace\outrigger_control\00_docs\02_hydraulic"
    out_dir_fig = r"C:\workspace\논문작성\figures"
    os.makedirs(out_dir_doc, exist_ok=True)
    os.makedirs(out_dir_fig, exist_ok=True)

    path_doc = os.path.join(out_dir_doc, "outrigger_pid_diagram.png")
    path_fig = os.path.join(out_dir_fig, "outrigger_pid_diagram.png")

    plt.savefig(path_doc, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(path_fig, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()

    print(f"P&ID Successfully generated:\n  - {path_doc}\n  - {path_fig}")

if __name__ == "__main__":
    draw_pid()
