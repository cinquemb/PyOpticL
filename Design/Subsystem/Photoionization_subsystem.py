import time
start_time = time.time()
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Module')))
from PyOpticL import optomech
from ECDL_Isolator_plate import ECDL_isolator_baseplate
from modular_singlepass import singlepass, singlepass_mirrored
from modular_beam_pickoff import Beam_pickoff
from modular_sourcebox import sourcebox
from ECDL import ECDL
import numpy as np

# 405 or 461 for 88Sr+
def PI_subsystem_commercial(baseplate, x=0, y=0, angle=0, thumbscrews=True):
    # Place components on the existing baseplate
    sourcebox(baseplate, x=x - 1, y=y - 6, angle=angle)  # modeling of a commercial laser
    baseplate.place_element("Periscope", optomech.periscope, x=x + 1.5, y=y + 6, z=0,
                           angle=optomech.layout.cardinal['up'], mirror_args=dict(mount_type=optomech.mirror_mount_k05s1))
    singlepass_mirrored(baseplate, x=x + 7, y=y + 12, angle=180 + angle, thumbscrews=thumbscrews)
    Beam_pickoff(baseplate, x=x + 1.5, y=y + 12, angle=90 + angle, thumbscrews=thumbscrews)

wavelength = 405e-6  # wavelength in mm
grating_pitch_d = 1/3600  # Lines per mm
littrow_angle = np.arcsin(wavelength / (2 * grating_pitch_d)) * 180 / np.pi
print("current wavelength is " + str(wavelength * 1e6) + " nm")
print("current littrow angle is " + str(littrow_angle))

def PI_subsystem_ECDL(baseplate, x=0, y=0, angle=0, thumbscrews=True, littrow_angle=littrow_angle):
    # Place components on the existing baseplate
    baseplate.place_element("ECDL", ECDL, x=x + 4.3, y=y - 4,
                           angle=90 + angle, littrow_angle=littrow_angle)  # modeling of a home-made laser
    baseplate.place_element("ECDL Isolator", ECDL_isolator_baseplate, x=x + 7, y=y + 1,
                           angle=optomech.layout.cardinal['up'])
    singlepass(baseplate, x=x, y=y + 7, angle=angle, thumbscrews=thumbscrews)
    Beam_pickoff(baseplate, x=x + 7.5, y=y + 12, angle=90 + angle, thumbscrews=thumbscrews)

if __name__ == "__main__":
    baseplate = optomech.layout.baseplate(10 * optomech.layout.inch, 10 * optomech.layout.inch, optomech.layout.inch)
    PI_subsystem_ECDL(baseplate, x=10)
    PI_subsystem_commercial(baseplate)
    optomech.layout.redraw()