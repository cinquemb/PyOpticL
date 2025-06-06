import time
start_time = time.time()
import sys
import os
import numpy as np

# Adjust path to include the Subsystem directory and custom components
print(os.path.join(os.path.dirname(__file__), 'Design/Subsystem'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Design/Subsystem'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Design/Module'))  # Optional, if Module exists
sys.path.append(os.path.dirname(__file__))  # To find custom_optomech.py

from PyOpticL import layout, optomech
import Part
from laser_cooling_subsystem import laser_cooling_subsystem
from Repump_subsystem import repump_subsystem_ECDL_mirrored
from Photoionization_subsystem import PI_subsystem_ECDL
from custom_optomech import ion_trap, pmt_array, fpga_board, mass_selective_axial_ejection_cavity, stepper_motor, aom, ion_injection_port

from modular_doublepass import doublepass_f50
from input_telescope import telescope
from ECDL_Isolator_plate import ECDL_isolator_baseplate

from modular_singlepass import singlepass, singlepass_mirrored
from modular_beam_pickoff import Beam_pickoff
from modular_sourcebox import sourcebox

# Start a transaction to batch operations
App.ActiveDocument.openTransaction("Batch Object Creation")

# Baseplate constants
base_dx = 6 * layout.inch
base_dy = 6 * layout.inch
base_dz = layout.inch
gap = layout.inch / 8

# Mount hole coordinates
mount_holes = [(0, 0), (0, 5), (5, 0), (5, 5)]

# Y-coordinates for laser beam inputs and SHG/tuning stages
input_y_588nm = 0.5 * layout.inch  # Input for 588 nm (for 294 nm SHG, Ga-68⁺ cooling)
input_y_422nm = 0.75 * layout.inch  # Input for 422 nm (Ca⁺ photoionization)
input_y_405nm_1 = 1.0 * layout.inch  # 405 nm tuned to 397 nm (Ca⁺ cooling)
input_y_405nm_2 = 2.0 * layout.inch  # 405 nm tuned to 403 nm (Ga-68⁺ repumping)
input_y_850nm = 1.5 * layout.inch  # 850 nm for 866 nm SHG (Ca⁺ repumping)

# Littrow angles for tuned and SHG wavelengths with debug
grating_pitch_d = 1/3600  # Lines per mm
grating_pitch_d_866 = 1/1800  # Lines per mm for 866 nm

# Tuned wavelengths
littrow_angle_397nm = np.arcsin(397e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~40.7° (tuned from 405 nm)
littrow_angle_403nm = np.arcsin(403e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~41.5° (tuned from 405 nm)
littrow_angle_294nm = np.arcsin(294e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~29.8° (SHG from 588 nm, Ga-68⁺ cooling)
littrow_angle_422nm = np.arcsin(422e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~49.4° (for Ca⁺ photoionization)
littrow_angle_866nm = np.arcsin(866e-6 / (2 * grating_pitch_d_866)) * 180 / np.pi  # ~51.2° (SHG from 850 nm)

# Debug print to check calculations
print(f"Denominator 397nm: {2 * grating_pitch_d}, Angle: {littrow_angle_397nm}")
print(f"Denominator 403nm: {2 * grating_pitch_d}, Angle: {littrow_angle_403nm}")
print(f"Denominator 294nm: {2 * grating_pitch_d}, Angle: {littrow_angle_294nm}")
print(f"Denominator 422nm: {2 * grating_pitch_d}, Angle: {littrow_angle_422nm}")
print(f"Denominator 866nm: {2 * grating_pitch_d_866}, Angle: {littrow_angle_866nm}")

def laser_cooling_subsystem(baseplate, ion_trap_x=3 * layout.inch, ion_trap_y=3 * layout.inch, angle=0, thumbscrews=True, littrow_angle=littrow_angle_397nm, beam_path=None, **args_for_doublepass):
    start = time.time()
    # Use provided beam path (e.g., beam_588nm for Ga-68⁺ cooling) or create a new one
    if beam_path is None:
        beam = baseplate.add_beam_path(x=ion_trap_x, y=ion_trap_y, angle=90 + angle)
    else:
        beam = beam_path

    # ECDL positioned 20 mm left of ion trap
    baseplate.place_element(f"ECDL {littrow_angle:.1f}nm", optomech.ECDL, x=ion_trap_x - 20, y=ion_trap_y,
                           angle=90 + angle, littrow_angle=littrow_angle)
    
    # Isolator baseplate 10 mm right of ECDL, angled upward
    baseplate.place_element(f"ECDL Isolator {littrow_angle:.1f}nm", ECDL_isolator_baseplate, x=ion_trap_x - 10, y=ion_trap_y,
                           angle=layout.cardinal['up'] + angle)
    
    # Telescope 10 mm right of isolator, aligned with beam path
    baseplate.place_element(f"Telescope {littrow_angle:.1f}nm", telescope, x=ion_trap_x, y=ion_trap_y,
                           angle=90 + angle)
    
    # Double-pass configuration 20 mm above ion trap for beam amplification
    baseplate.place_element(f"Doublepass {littrow_angle:.1f}nm", doublepass_f50, x=ion_trap_x, y=ion_trap_y + 20,
                           angle=90 + angle, thumbscrews=thumbscrews, **args_for_doublepass)
    
    # Define beam path from double-pass directed downward
    beam = baseplate.add_beam_path(x=ion_trap_x, y=ion_trap_y + 20, angle=layout.cardinal['down'])
    baseplate.place_element_along_beam(f"Mirror {littrow_angle:.1f}nm to Trap", optomech.circular_mirror, beam,
                                      beam_index=0b1, distance=layout.inch, angle=layout.turn['up-right'],
                                      mount_type=optomech.mirror_mount_k05s1)
    print(f"laser_cooling_subsystem time: {time.time() - start} seconds")
    return beam

# Placeholder for waveguide (to be customized based on your needs)
def add_waveguide(baseplate, start_x, start_y, end_x, end_y, angle=0):
    # Simple cylindrical path as a placeholder for the waveguide
    waveguide_length = np.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    waveguide = Part.makeCylinder(2, waveguide_length)  # 2 mm radius, length based on distance
    # Position and rotate the waveguide
    waveguide.translate(App.Vector(start_x, start_y, 0))
    angle_rad = np.arctan2(end_y - start_y, end_x - start_x) * 180 / np.pi
    waveguide.rotate(App.Vector(start_x, start_y, 0), App.Vector(0, 0, 1), angle_rad)
    # Add the waveguide to the FreeCAD document
    waveguide_obj = App.ActiveDocument.addObject("Part::Feature", "Waveguide")
    waveguide_obj.Shape = waveguide
    # Optionally, set the placement relative to the baseplate (if needed)
    # baseplate_obj = App.ActiveDocument.getObject(baseplate.Label)  # If baseplate has a label
    # waveguide_obj.Placement.Base = baseplate_obj.Placement.Base

def repump_subsystem_ECDL_mirrored(baseplate, x=4, y=0, angle=0, thumbscrews=True, littrow_angle=littrow_angle_866nm):
    start = time.time()
    # Create a beam path starting at the ECDL position
    beam = baseplate.add_beam_path(x + 0.3, y - 4, angle=90 + angle)
    baseplate.place_element("ECDL", optomech.ECDL, x=x + 0.3, y=y - 4,
                           angle=90 + angle, littrow_angle=littrow_angle)  # modeling of a home-made laser
    baseplate.place_element("ECDL Isolator", ECDL_isolator_baseplate, x=x + 3, y=y + 1,
                           angle=optomech.layout.cardinal['up'])
    singlepass_mirrored(baseplate, x=x + 7, y=y + 12, angle=180 + angle, thumbscrews=thumbscrews)  # Call as function
    Beam_pickoff(baseplate, x=x + 1.5, y=y + 12, angle=90 + angle, thumbscrews=thumbscrews)
    print(f"repump_subsystem_ECDL_mirrored time: {time.time() - start} seconds")
    return beam

# Function to define the baseplate
def isotope_separation_baseplate(x=0, y=0, angle=0):
    baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=x, y=y, angle=angle,
                                 gap=gap, mount_holes=mount_holes)

    # SHG for 294 nm from 588 nm (for Ga-68⁺ cooling)
    beam_588nm = baseplate.add_beam_path(x=0, y=input_y_588nm, angle=layout.cardinal['right'])
    baseplate.place_element_along_beam("SHG 588nm to 294nm", optomech.cube_splitter, beam_588nm,
                                      beam_index=0b1, distance=0.5 * layout.inch, angle=layout.cardinal['right'],
                                      mount_type=optomech.skate_mount)  # Placeholder for BBO crystal
    beam_294nm = baseplate.add_beam_path(x=0.5 * layout.inch, y=input_y_588nm, angle=layout.cardinal['right'])

    # Add photoionization for Ca⁺ at 422 nm, TODO: NEED TO SOURCE 422NM LASER
    #beam_422nm = baseplate.add_beam_path(x, y + input_y_422nm, angle=layout.cardinal['right'])
    #PI_subsystem_ECDL(baseplate, x=x + gap + 1.5 * layout.inch, y=y + input_y_422nm, thumbscrews=True, littrow_angle=littrow_angle_422nm)  # Ca⁺ photoionization

    # SHG for 866 nm from 850 nm (for Ca⁺ repumping)
    beam_850nm = baseplate.add_beam_path(x=0, y=input_y_850nm, angle=layout.cardinal['right'])
    baseplate.place_element_along_beam("SHG 850nm to 425nm", optomech.cube_splitter, beam_850nm,
                                      beam_index=0b1, distance=0.5 * layout.inch, angle=layout.cardinal['right'],
                                      mount_type=optomech.skate_mount)  # Placeholder for BBO crystal
    baseplate.place_element_along_beam("Tuner 425nm to 866nm", optomech.cube_splitter, beam_850nm,
                                      beam_index=0b1, distance=layout.inch, angle=layout.cardinal['right'],
                                      mount_type=optomech.skate_mount)  # Placeholder for mixing/tuning
    beam_866nm = baseplate.add_beam_path(x=1.5 * layout.inch, y=input_y_850nm, angle=layout.cardinal['right'])

    # Add subsystems
    # Ga-68⁺ cooling at 294 nm using beam_588nm (post-SHG)
    beam_294nm = laser_cooling_subsystem(baseplate, ion_trap_x=3 * layout.inch, ion_trap_y=3 * layout.inch,
                                        thumbscrews=True, littrow_angle=littrow_angle_294nm, beam_path=beam_294nm)  # Ga-68⁺ cooling

    # Ca⁺ cooling at 397 nm
    beam_397nm = laser_cooling_subsystem(baseplate, ion_trap_x=3 * layout.inch, ion_trap_y=input_y_405nm_1,
                                        thumbscrews=True, littrow_angle=littrow_angle_397nm)  # Ca⁺ cooling

    # Ca⁺ repumping at 866 nm
    beam_866nm = repump_subsystem_ECDL_mirrored(baseplate, x=gap + 0.5 * layout.inch, y=input_y_850nm, thumbscrews=True,
                              littrow_angle=littrow_angle_866nm)  # Ca⁺ repumping

    # Ga-68⁺ repumping at 403 nm
    beam_403nm = repump_subsystem_ECDL_mirrored(baseplate, x=gap + 0.5 * layout.inch, y=input_y_405nm_2, thumbscrews=True,
                              littrow_angle=littrow_angle_403nm)  # Ga-68⁺ repumping

    # Add AOMs using custom component (for beam modulation)
    baseplate.place_element_along_beam("AOM 397nm", aom, beam_397nm,
                                      beam_index=0b1, distance=30, angle=layout.cardinal['right'])  # Ca⁺ cooling
    baseplate.place_element_along_beam("AOM 866nm", aom, beam_866nm,
                                      beam_index=0b1, distance=30, angle=layout.cardinal['right'])  # Ca⁺ repumping
    baseplate.place_element_along_beam("AOM 403nm", aom, beam_403nm,
                                      beam_index=0b1, distance=30, angle=layout.cardinal['right'])  # Ga-68⁺ repumping
    baseplate.place_element_along_beam("AOM 294nm", aom, beam_294nm,
                                      beam_index=0b1, distance=30, angle=layout.cardinal['right'])  # Ga-68⁺ cooling

    # Add mirrors to direct beams to the trap
    baseplate.place_element_along_beam("Mirror 866nm", optomech.circular_mirror, beam_866nm,
                                      beam_index=0b1, distance=layout.inch * 3, angle=layout.turn['up-right'],
                                      mount_type=optomech.mirror_mount_k05s1)
    baseplate.place_element_along_beam("Mirror 294nm", optomech.circular_mirror, beam_294nm,
                                      beam_index=0b1, distance=layout.inch * 3, angle=layout.turn['up-right'],
                                      mount_type=optomech.mirror_mount_k05s1)

    # Add stepper motors using custom component (for beam alignment)
    baseplate.place_element("Step Motor 397nm", stepper_motor, x=1.5 * layout.inch, y=input_y_405nm_1,
                           angle=layout.cardinal['right'])
    baseplate.place_element("Step Motor 866nm", stepper_motor, x=1.5 * layout.inch, y=input_y_850nm,
                           angle=layout.cardinal['right'])
    baseplate.place_element("Step Motor 403nm", stepper_motor, x=1.5 * layout.inch, y=input_y_405nm_2,
                           angle=layout.cardinal['right'])
    baseplate.place_element("Step Motor 294nm", stepper_motor, x=1.5 * layout.inch, y=input_y_588nm,
                           angle=layout.cardinal['right'])

    # Add ion trap components using custom components
    baseplate.place_element("Ion Trap", ion_trap, x=3 * layout.inch, y=3 * layout.inch,
                           angle=layout.cardinal['right'])
    baseplate.place_element("PMT Array", pmt_array, x=base_dx - gap, y=0, angle=layout.cardinal['left'])
    baseplate.place_element("FPGA", fpga_board, x=4.5 * layout.inch, y=1.5 * layout.inch,
                           angle=layout.cardinal['right'])
    baseplate.place_element("MSAE Cavity", mass_selective_axial_ejection_cavity, x=3 * layout.inch, y=3.5 * layout.inch,
                           angle=layout.cardinal['right'])
    baseplate.place_element("ICP-MS Port", ion_injection_port, x=2.5 * layout.inch, y=3 * layout.inch,
                           angle=layout.cardinal['right'])

    # Add waveguide from ICP-MS port to ion trap for Ga-68⁺ transport
    #add_waveguide(baseplate, start_x=2.5 * layout.inch, start_y=3 * layout.inch, end_x=3 * layout.inch, end_y=3 * layout.inch)

    # Note: High-frequency electrode modulation for Ga-68⁺ positioning (~100 ns) should be added to ion_trap
    # This requires updating ion_trap in custom_optomech.py to include DC electrode switching at ~10 MHz (1/100 ns)

if __name__ == "__main__":
    isotope_separation_baseplate()
    # Commit the transaction and perform final recompute
    App.ActiveDocument.commitTransaction()
    App.ActiveDocument.recompute()
    layout.redraw()
    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")