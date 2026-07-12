"""Shared helpers for the interrogator v1.1 circuit modules."""

from skidl import Part, Net, TEMPLATE

from lib_parts import mkpart, PAS

# Generic passives come from the KiCad-official Device library (symbol source:
# kicad-official; the library is provided by the Ubuntu-packaged KiCad 7.0.11).
_C = Part("Device", "C", dest=TEMPLATE, footprint="Capacitor_SMD:C_0402_1005Metric")
_C_BULK = Part("Device", "C", dest=TEMPLATE, footprint="Capacitor_SMD:C_0805_2012Metric")
_R = Part("Device", "R", dest=TEMPLATE, footprint="Resistor_SMD:R_0402_1005Metric")
_L = Part("Device", "L", dest=TEMPLATE, footprint="Inductor_SMD:L_0805_2012Metric")
_LED = Part("Device", "LED", dest=TEMPLATE, footprint="LED_SMD:LED_0603_1608Metric")
_D = Part("Device", "D_Schottky", dest=TEMPLATE, footprint="Diode_SMD:D_SOD-323")

TESTPOINT = mkpart("TESTPOINT", "TP", [(1, "TP", PAS)],
                   description="Test pad",
                   footprint="TestPoint:TestPoint_Pad_1.0x1.0mm")


def C(value, bulk=False):
    c = (_C_BULK if bulk else _C)()
    c.value = value
    return c


def R(value):
    r = _R()
    r.value = value
    return r


def L(value):
    l = _L()
    l.value = value
    return l


def LED(color):
    d = _LED()
    d.value = color
    return d


def SCHOTTKY(value="BAT54"):
    d = _D()
    d.value = value
    return d


def gnd():
    return Net.fetch("GND")


def decouple(rail, n=1, bulk_uF=None):
    """Attach n x 100nF (and optionally one bulk cap) between rail and GND."""
    g = gnd()
    for _ in range(n):
        c = C("100nF")
        rail += c[1]
        g += c[2]
    if bulk_uF:
        cb = C(f"{bulk_uF}uF", bulk=True)
        rail += cb[1]
        g += cb[2]


def pullup(net, rail, value="2.2k"):
    r = R(value)
    net += r[1]
    rail += r[2]
    return r


def tp(net):
    t = TESTPOINT()
    net += t[1]
    return t


def join(name, *pins):
    """Fetch/create net `name` and attach pins (Net.fetch() can't take +=)."""
    n = Net.fetch(name)
    n += pins
    return n
