# Multi-Agent Code Review System -- Test Fixture
# Author: Maharshi Soni | License: MIT
"""Synthetic complex code for testing the PerformanceAgent."""

from typing import *

counter = 0


def deeply_nested(data):
    """Function with excessive nesting."""
    results = []
    for item in data:
        if isinstance(item, dict):
            for key, value in item.items():
                if isinstance(value, list):
                    for sub in value:
                        if isinstance(sub, str):
                            if len(sub) > 5:
                                results.append(sub.upper())
    return results


def high_complexity(x, y, z, w, a, b, c):
    """High cyclomatic complexity function."""
    global counter
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            elif z == 0:
                return x + y
            else:
                return x
        elif y == 0:
            if w > 0:
                return w
            else:
                return -1
        else:
            if a and b:
                return a
            elif a or c:
                return c
            else:
                return 0
    elif x == 0:
        if y > 10 or y < -10:
            return y
        else:
            return 0
    else:
        return -x


def nested_loops(matrix):
    """O(n^2) nested loops."""
    result = []
    for i in range(len(matrix)):
        for j in range(len(matrix)):
            result.append(matrix[i] + matrix[j])
    return result


def mutable_default_bug(items=[]):
    """Classic mutable default argument bug."""
    items.append("new")
    return items


def way_too_long():
    """A function that is unreasonably long."""
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    h = 8
    i = 9
    j = 10
    k = 11
    l = 12
    m = 13
    n = 14
    o = 15
    p = 16
    q = 17
    r = 18
    s = 19
    t = 20
    u = 21
    v = 22
    w = 23
    x = 24
    y = 25
    z = 26
    aa = 27
    bb = 28
    cc = 29
    dd = 30
    ee = 31
    ff = 32
    gg = 33
    hh = 34
    ii = 35
    jj = 36
    kk = 37
    ll = 38
    mm = 39
    nn = 40
    oo = 41
    pp = 42
    qq = 43
    rr = 44
    ss = 45
    tt = 46
    uu = 47
    vv = 48
    ww = 49
    xx = 50
    yy = 51
    return (
        a + b + c + d + e + f + g + h + i + j + k + l + m
        + n + o + p + q + r + s + t + u + v + w + x + y + z
        + aa + bb + cc + dd + ee + ff + gg + hh + ii + jj
        + kk + ll + mm + nn + oo + pp + qq + rr + ss + tt
        + uu + vv + ww + xx + yy
    )
