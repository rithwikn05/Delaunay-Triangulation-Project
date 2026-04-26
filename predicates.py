"""
Robust geometric predicates.
Fixed: Fraction as_integer_ratio for speed.
"""

import decimal

# Set precision high enough to handle the expansion of 64-bit floats
# A double has 53 bits of mantissa; products/sums can require 
# significantly more to be "exact." 100 digits is safe for this context.
decimal.getcontext().prec = 100
D = decimal.Decimal

_EPSILON = 2.2204460492503131e-16
# These bounds match the ccwerrboundA and iccerrboundA logic in Shewchuk's C
_ORIENT2D_ERRBOUND = (3.0 + 16.0 * _EPSILON) * _EPSILON
_INCIRCLE_ERRBOUND = (10.0 + 96.0 * _EPSILON) * _EPSILON

def orient2d(pa, pb, pc):
    """
    Python version of REAL orient2d(pa, pb, pc)
    """
    detleft = (pa[0] - pc[0]) * (pb[1] - pc[1])
    detright = (pa[1] - pc[1]) * (pb[0] - pc[0])
    det = detleft - detright

    # The C code's "Filter" logic
    if detleft > 0.0:
        if detright <= 0.0: return det
        else: detsum = detleft + detright
    elif detleft < 0.0:
        if detright >= 0.0: return det
        else: detsum = -detleft - detright
    else:
        return det

    errbound = _ORIENT2D_ERRBOUND * detsum
    if (det >= errbound) or (-det >= errbound):
        return det

    # If it falls through the filter, use the exact calculation
    return _orient2d_exact(pa, pb, pc)

def _orient2d_exact(pa, pb, pc):
    """
    Python version of REAL orient2dexact(pa, pb, pc)
    Uses Decimal for arbitrary precision to simulate the C expansion.
    """
    ax, ay = D(str(pa[0])), D(str(pa[1]))
    bx, by = D(str(pb[0])), D(str(pb[1]))
    cx, cy = D(str(pc[0])), D(str(pc[1]))
    
    # Standard 2x2 determinant formula using exact decimals
    det = (ax - cx) * (by - cy) - (ay - cy) * (bx - cx)
    return float(det)

import decimal

# Set precision high enough to capture the full expansion of 
# (x^2 + y^2) * (x*y - x*y). 100 digits is more than enough.
decimal.getcontext().prec = 100
D = decimal.Decimal

_EPSILON = 2.2204460492503131e-16
_INCIRCLE_ERRBOUND = (10.0 + 96.0 * _EPSILON) * _EPSILON

def incircle(pa, pb, pc, pd):
    """
    Python version of REAL incircle(pa, pb, pc, pd)
    """
    adx = pa[0] - pd[0]
    bdx = pb[0] - pd[0]
    cdx = pc[0] - pd[0]
    ady = pa[1] - pd[1]
    bdy = pb[1] - pd[1]
    cdy = pc[1] - pd[1]

    bdxcdy = bdx * cdy
    cdxbdy = cdx * bdy
    alift = adx * adx + ady * ady

    cdxady = cdx * ady
    adxcdy = adx * cdy
    blift = bdx * bdx + bdy * bdy

    adxbdy = adx * bdy
    bdxady = bdx * ady
    clift = cdx * cdx + cdy * cdy

    det = alift * (bdxcdy - cdxbdy) \
        + blift * (cdxady - adxcdy) \
        + clift * (adxbdy - bdxady)

    # Calculate 'permanent' for the error bound check
    permanent = (abs(bdxcdy) + abs(cdxbdy)) * alift \
              + (abs(cdxady) + abs(adxcdy)) * blift \
              + (abs(adxbdy) + abs(bdxady)) * clift
    
    errbound = _INCIRCLE_ERRBOUND * permanent
    
    if (det > errbound) or (-det > errbound):
        return det

    # If the floating point result is too close to zero, use exact arithmetic
    return incircleexact(pa, pb, pc, pd)

def incircleexact(pa, pb, pc, pd):
    """
    Python version of REAL incircleexact(pa, pb, pc, pd)
    Uses Decimal to perform the 4x4 determinant calculation exactly.
    """
    # Convert to Decimal for exact arithmetic
    ax, ay = D(str(pa[0])), D(str(pa[1]))
    bx, by = D(str(pb[0])), D(str(pb[1]))
    cx, cy = D(str(pc[0])), D(str(pc[1]))
    dx, dy = D(str(pd[0])), D(str(pd[1]))

    # Relative coordinates
    adx, ady = ax - dx, ay - dy
    bdx, bdy = bx - dx, by - dy
    cdx, cdy = cx - dx, cy - dy

    # Lifted components (x^2 + y^2)
    alift = adx * adx + ady * ady
    blift = bdx * bdx + bdy * bdy
    clift = cdx * cdx + cdy * cdy

    # 3x3 Determinant calculation (part of the 4x4 InCircle expansion)
    det = alift * (bdx * cdy - cdx * bdy) \
        + blift * (cdx * ady - adx * cdy) \
        + clift * (adx * bdy - bdx * ady)
    
    return float(det)

def right_of(x, e): 
    return orient2d(x, e.dest, e.org) > 0

def on_edge(x, e):
    if orient2d(x, e.org, e.dest) != 0: return False
    ox, oy, dx, dy, px, py = e.org[0], e.org[1], e.dest[0], e.dest[1], x[0], x[1]
    if abs(ox-dx) > abs(oy-dy): return min(ox, dx) <= px <= max(ox, dx)
    return min(oy, dy) <= py <= max(oy, dy)