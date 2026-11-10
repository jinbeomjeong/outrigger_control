"""SCMLoader::Initialize grid spacing (SCMTerrain.cpp:439-447): m_nx = ceil((sizeX/2)/delta), m_delta = sizeX/(2 m_nx)."""
import math

for sx in (1.2, 8.0, 6.0):
    for d in (0.04, 0.02, 0.01, 0.005):
        nx = math.ceil((sx / 2) / d)
        md = sx / (2 * nx)
        print(f"sizeX {sx} delta {d}: (sizeX/2)/delta = {(sx/2)/d!r}, m_nx {nx}, m_delta {md!r}, rel {md/d-1:+.2e}")
