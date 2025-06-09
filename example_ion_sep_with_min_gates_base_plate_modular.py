import time
start_time = time.time()
import sys
import os
import FreeCAD as App
import FreeCADGui

import numpy as np
import gc
import zipfile
import json
import xml.etree.ElementTree as ET
from lxml import etree

is_headless = True
sys.stdout = open('debug_output.txt', 'w')
sys.stderr = open('debug_error.txt', 'w')

script_dir = os.path.dirname(os.path.abspath(__file__))
subsystem_dir = os.path.join(script_dir, 'Design/Subsystem')
module_dir = os.path.join(script_dir, 'Design/Module')

print(f"Script directory: {script_dir}")
print(f"Subsystem directory: {subsystem_dir}, Exists: {os.path.exists(subsystem_dir)}")
print(f"Module directory: {module_dir}, Exists: {os.path.exists(module_dir)}")

sys.path.append(subsystem_dir)
sys.path.append(module_dir)
sys.path.append(script_dir)

print(f"sys.path: {sys.path}")

from PyOpticL import layout, optomech, laser
import Part
from laser_cooling_subsystem import laser_cooling_subsystem
from Repump_subsystem import repump_subsystem_ECDL_mirrored
from custom_optomech import ion_trap, pmt_array, fpga_board, mass_selective_axial_ejection_cavity, stepper_motor, aom, ion_injection_port
from modular_doublepass import doublepass_f50
from input_telescope import telescope
from ECDL_Isolator_plate import ECDL_isolator_baseplate
from modular_singlepass import singlepass, singlepass_mirrored
from modular_beam_pickoff import Beam_pickoff
from modular_sourcebox import sourcebox

if not is_headless:
    # Start a transaction to batch operations
    App.ActiveDocument.openTransaction("Batch Object Creation")

# Monkey-patch for serialization
def make_serializable(cls):
    def __str__(self):
        return f"{self.__class__.__name__}"
    setattr(cls, '__str__', __str__)
    def __reduce__(self):
        return (str, (self.__class__.__name__,))
    setattr(cls, '__reduce__', __reduce__)
    return cls

make_serializable(ECDL_isolator_baseplate)
make_serializable(doublepass_f50)

# Baseplate constants
base_dx = 12 * layout.inch
base_dy = 12 * layout.inch
base_dz = layout.inch
gap = layout.inch / 4

mount_holes = [
    (0 * layout.inch, 0 * layout.inch),
    (0 * layout.inch, 11 * layout.inch),
    (11 * layout.inch, 0 * layout.inch),
    (11 * layout.inch, 11 * layout.inch)
]

input_y_588nm = 0.5 * layout.inch
input_y_405nm_1 = 1.0 * layout.inch
input_y_405nm_2 = 2.0 * layout.inch
input_y_850nm = 1.5 * layout.inch
input_y_850nm_2 = 2.5 * layout.inch

grating_pitch_d = 1/3600
grating_pitch_d_866 = 1/1800

littrow_angle_397nm = np.arcsin(397e-6 / (2 * grating_pitch_d)) * 180 / np.pi
littrow_angle_403nm = np.arcsin(403e-6 / (2 * grating_pitch_d)) * 180 / np.pi
littrow_angle_294nm = np.arcsin(294e-6 / (2 * grating_pitch_d)) * 180 / np.pi
littrow_angle_422nm = np.arcsin(422e-6 / (2 * grating_pitch_d)) * 180 / np.pi
littrow_angle_866nm = np.arcsin(866e-6 / (2 * grating_pitch_d_866)) * 180 / np.pi
littrow_angle_858nm = np.arcsin(858e-9 / (2 * grating_pitch_d)) * 180 / np.pi
littrow_angle_844nm = np.arcsin(844e-6 / (2 * grating_pitch_d_866)) * 180 / np.pi

print(f"Denominator 397nm: {2 * grating_pitch_d}, Angle: {littrow_angle_397nm}")
print(f"Denominator 403nm: {2 * grating_pitch_d}, Angle: {littrow_angle_403nm}")
print(f"Denominator 294nm: {2 * grating_pitch_d}, Angle: {littrow_angle_294nm}")
print(f"Denominator 422nm: {2 * grating_pitch_d}, Angle: {littrow_angle_422nm}")
print(f"Denominator 866nm: {2 * grating_pitch_d_866}, Angle: {littrow_angle_866nm}")

def add_beam_path(self, x, y, angle, name="Beam Path", color=(1.0, 0.0, 0.0), z=0, wavelength=850e-9, **args):
    obj = App.ActiveDocument.addObject('Part::FeaturePython', name)
    obj.Label = name
    laser.ViewProvider(obj.ViewObject)
    laser.beam_path(obj, **args)
    obj.addProperty("App::PropertyLinkHidden", "Baseplate").Baseplate = getattr(App.ActiveDocument, self.active_baseplate)
    obj.addProperty("App::PropertyPlacement", "BasePlacement")
    obj.BasePlacement = App.Placement(App.Vector(x, y, z), App.Rotation(angle, 0, 0), App.Vector(0, 0, 0))
    obj.addProperty("App::PropertyLinkListHidden", "PathObjects").PathObjects = []
    obj.addProperty("App::PropertyLength", "Wavelength", "Beam", "Wavelength in meters").Wavelength = wavelength * App.Units.Metre
    obj.ViewObject.ShapeColor = color
    return obj

def add_beam_path_general(self, x, y, z, angle_x, angle_y, angle_z, name="Beam Path", color=(1.0, 0.0, 0.0), wavelength=850e-9):
    obj = App.ActiveDocument.addObject('Part::FeaturePython', name)
    obj.Label = name
    laser.ViewProvider(obj.ViewObject)
    laser.beam_path(obj)
    obj.addProperty("App::PropertyLinkHidden", "Baseplate").Baseplate = getattr(App.ActiveDocument, self.active_baseplate)
    obj.addProperty("App::PropertyPlacement", "BasePlacement")
    obj.BasePlacement = App.Placement(App.Vector(x, y, z), App.Rotation(angle_x, angle_y, angle_z), App.Vector(0, 0, 0))
    obj.addProperty("App::PropertyLinkListHidden", "PathObjects").PathObjects = []
    obj.addProperty("App::PropertyLength", "Wavelength", "Beam", "Wavelength in meters").Wavelength = wavelength * App.Units.Metre
    obj.ViewObject.ShapeColor = color
    return obj

layout.baseplate.add_beam_path = add_beam_path
layout.baseplate.add_beam_path_general = add_beam_path_general

def General_Beam_Combiner(baseplate, input_beams, x=0, y=0, angle=layout.cardinal['right'], thumbscrews=True):
    if not input_beams or len(input_beams) > 6:
        print("Error: Number of input beams must be between 1 and 6", flush=True)
        raise ValueError("Number of input beams must be between 1 and 6")
    num_beams = len(input_beams)
    gap = layout.inch / 4

    if num_beams == 1:
        print("Single beam, returning directly", flush=True)
        return input_beams[0]

    ref_beam = input_beams[0]
    ref_x = ref_beam.Placement.Base.x
    ref_y = ref_beam.Placement.Base.y
    current_x = ref_x + 0.5 * layout.inch
    current_y = ref_y
    combined_beam = ref_beam
    print(f"Starting with ref_beam: Position={ref_beam.Placement.Base}, Angle={angle}", flush=True)

    for i in range(1, num_beams):
        beam_to_combine = input_beams[i]
        print(f"Processing beam {i+1}: Position={beam_to_combine.Placement.Base}", flush=True)
        redirect_angle = angle - 45 if beam_to_combine.Placement.Base.y > current_y else angle + 45
        mirror = baseplate.place_element_along_beam(f"Mirror_Beam_{i+1}", optomech.circular_mirror, beam_to_combine,
                                                   beam_index=0b1, distance=0.5 * layout.inch, angle=redirect_angle,
                                                   mount_type=optomech.mirror_mount_k05s2,
                                                   mount_args=dict(thumbscrews=thumbscrews))
        print(f"Mirror_Beam_{i+1}: Position={mirror.Placement.Base}", flush=True)

        mirror_x = beam_to_combine.Placement.Base.x + 0.5 * layout.inch * np.cos(np.radians(angle))
        mirror_y = beam_to_combine.Placement.Base.y + 0.5 * layout.inch * np.sin(np.radians(angle))
        redirected_beam = baseplate.add_beam_path(mirror_x, mirror_y, angle - 90 if beam_to_combine.Placement.Base.y > current_y else angle + 90)
        print(f"Redirected_Beam_{i+1}: Position={redirected_beam.Placement.Base}", flush=True)

        combine_element = baseplate.place_element_along_beam(f"Combiner_{i}", optomech.cube_splitter, combined_beam,
                                                             beam_index=0b1, distance=0.75 * layout.inch, angle=angle,
                                                             mount_type=optomech.skate_mount_crossholes)
        print(f"Combiner_{i}: Position={combine_element.Placement.Base}", flush=True)

        current_x += 0.75 * layout.inch
        current_y = ref_y
        combined_beam = baseplate.add_beam_path(current_x, current_y, angle)

        if i == 1 and num_beams == 2:
            lambda1 = combined_beam.Wavelength.getValueAs('m').Value
            lambda2 = beam_to_combine.Wavelength.getValueAs('m').Value
            if lambda1 and lambda2:
                if lambda1 > lambda2:
                    dfg_wavelength = 1 / (1/lambda2 - 1/lambda1)
                else:
                    dfg_wavelength = 1 / (1/lambda1 - 1/lambda2)
                combined_beam.Wavelength = dfg_wavelength * App.Units.Metre
                print(f"DFG Wavelength calculated: {dfg_wavelength * 1e9:.1f} nm", flush=True)

        wavelength_nm = combined_beam.Wavelength.getValueAs('m').Value * 1e9
        print(f"Combined_Beam after step {i}: Position={combined_beam.Placement.Base}, Wavelength={wavelength_nm:.1f} nm", flush=True)

    return combined_beam

def generate_866nm_subsystem(baseplate, x=0, y=input_y_850nm, angle=layout.cardinal['right']):
    beam_850nm = baseplate.add_beam_path(x, y, angle, wavelength=850e-9)
    wavelength_850nm = beam_850nm.Wavelength.getValueAs('m').Value * 1e9
    print(f"Beam_850nm: Position={beam_850nm.Placement.Base}, Wavelength={wavelength_850nm:.1f} nm")
    
    beam_858nm = baseplate.add_beam_path(x, y + 0.05 * layout.inch, angle, wavelength=858e-9)
    baseplate.place_element("ECDL_858nm", optomech.ECDL, x=x, y=y + 0.05 * layout.inch,
                           angle=angle, littrow_angle=littrow_angle_858nm, cover_box=False)
    wavelength_858nm = beam_858nm.Wavelength.getValueAs('m').Value * 1e9
    print(f"Beam_858nm: Position={beam_858nm.Placement.Base}, Wavelength={wavelength_858nm:.1f} nm")
    
    baseplate.place_element_along_beam("SHG_858nm_to_429nm", optomech.cube_splitter, beam_858nm,
                                      beam_index=0b1, distance=0.5 * layout.inch, angle=angle,
                                      mount_type=optomech.skate_mount_crossholes)
    beam_429nm = baseplate.add_beam_path(x + 0.5 * layout.inch, y + 0.05 * layout.inch, angle, wavelength=858e-9 / 2)
    wavelength_429nm = beam_429nm.Wavelength.getValueAs('m').Value * 1e9
    print(f"Beam_429nm: Position={beam_429nm.Placement.Base}, Wavelength={wavelength_429nm:.1f} nm")
    
    beam_866nm = General_Beam_Combiner(baseplate, [beam_850nm, beam_429nm], x=x + 0.75 * layout.inch, y=y, angle=angle)
    wavelength_866nm = beam_866nm.Wavelength.getValueAs('m').Value * 1e9
    print(f"Beam_866nm: Position={beam_866nm.Placement.Base}, Wavelength={wavelength_866nm:.1f} nm")
    
    return beam_866nm

def tune_and_shg_422nm(baseplate, x=1 * layout.inch, y=input_y_850nm_2, angle=layout.cardinal['right']):
    start = time.time()
    beam_850nm = baseplate.add_beam_path(x, y, angle, wavelength=850e-9, name="Beam_850nm")
    ecdl_844nm = baseplate.place_element("ECDL_844nm", optomech.ECDL, x=x, y=y,
                                        angle=angle, littrow_angle=littrow_angle_844nm, cover_box=False)
    beam_844nm = baseplate.add_beam_path(x, y, angle, wavelength=844e-9, name="Beam_844nm")

    shg_crystal = baseplate.place_element_along_beam("SHG_844nm_to_422nm", optomech.cube_splitter,
                                                    beam_844nm, beam_index=0b1, distance=0.5 * layout.inch,
                                                    angle=angle, mount_type=optomech.skate_mount)
    beam_422nm = baseplate.add_beam_path(x + 0.5 * layout.inch, y, angle, wavelength=422e-9, name="Beam_422nm")

    # Place components on the existing baseplate for Photoionization_Ca+
    baseplate.place_element("ECDL", optomech.ECDL, x=x + 4.3, y=y - 4,
                           angle=90 + angle, littrow_angle=littrow_angle_422nm, cover_box=False)
    baseplate.place_element("ECDL Isolator", ECDL_isolator_baseplate, x=x + 7, y=y + 1,
                           angle=optomech.layout.cardinal['up'])
    singlepass(baseplate, x=x, y=y + 7, angle=angle, thumbscrews=True)
    Beam_pickoff(baseplate, x=x + 7.5, y=y + 12, angle=90 + angle, thumbscrews=True)

    print(f"tune_and_shg_422nm time: {time.time() - start} seconds")

    return beam_422nm

def laser_cooling_subsystem(baseplate, ion_trap_x=3 * layout.inch, ion_trap_y=3 * layout.inch, angle=0, thumbscrews=True, littrow_angle=littrow_angle_397nm, beam_path=None, **args_for_doublepass):
    start = time.time()
    if beam_path is None:
        beam = baseplate.add_beam_path(x=ion_trap_x, y=ion_trap_y, angle=90 + angle)
    else:
        beam = beam_path

    baseplate.place_element(f"ECDL {littrow_angle:.1f}nm", optomech.ECDL, x=ion_trap_x - 20, y=ion_trap_y,
                           angle=90 + angle, littrow_angle=littrow_angle, cover_box=False)
    
    baseplate.place_element(f"ECDL Isolator {littrow_angle:.1f}nm", ECDL_isolator_baseplate, 
                           x=ion_trap_x, y=ion_trap_y + 1 * layout.inch,
                           angle=layout.cardinal['up'] + angle)
    
    baseplate.place_element(f"Telescope {littrow_angle:.1f}nm", telescope, x=ion_trap_x, y=ion_trap_y,
                           angle=90 + angle)
    
    baseplate.place_element(f"Doublepass {littrow_angle:.1f}nm", doublepass_f50, x=ion_trap_x, y=ion_trap_y + 20,
                           angle=90 + angle, thumbscrews=thumbscrews, **args_for_doublepass)
    
    beam = baseplate.add_beam_path(x=ion_trap_x, y=ion_trap_y + 20, angle=layout.cardinal['down'])
    baseplate.place_element_along_beam(f"Mirror {littrow_angle:.1f}nm to Trap", optomech.circular_mirror, beam,
                                      beam_index=0b1, distance=layout.inch, angle=layout.turn['up-right'],
                                      mount_type=optomech.mirror_mount_k05s1)
    print(f"laser_cooling_subsystem time: {time.time() - start} seconds")
    return beam

def repump_subsystem_ECDL_mirrored(baseplate, beam=None, x=4, y=0, angle=0, thumbscrews=True, littrow_angle=littrow_angle_866nm):
    start = time.time()
    if beam == None:
        beam = baseplate.add_beam_path(x + 0.3, y - 4, angle=90 + angle)
    
    baseplate.place_element("ECDL", optomech.ECDL, x=x + 0.3, y=y - 4,
                           angle=90 + angle, littrow_angle=littrow_angle, cover_box=False)
    baseplate.place_element("ECDL Isolator", ECDL_isolator_baseplate, x=x + 4, y=y + 1,
                           angle=optomech.layout.cardinal['up'])
    singlepass_mirrored(baseplate, x=x + 7, y=y + 12, angle=180 + angle, thumbscrews=thumbscrews)
    Beam_pickoff(baseplate, x=x + 1.5, y=y + 12, angle=90 + angle, thumbscrews=thumbscrews)
    print(f"repump_subsystem_ECDL_mirrored time: {time.time() - start} seconds")
    return beam

def isotope_separation_baseplate(x=0, y=0, angle=0):
    baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=x, y=y, angle=angle,
                                 gap=gap, mount_holes=mount_holes)
    print(f"Baseplate dimensions: dx={base_dx}, dy={base_dy}, dz={base_dz}", flush=True)
    print(baseplate.__dict__)

    subcomponents = [
        ("SHG_588nm_to_294nm", lambda bp: bp.place_element_along_beam("SHG 588nm to 294nm", optomech.cube_splitter, bp.add_beam_path(x=0, y=input_y_588nm, angle=layout.cardinal['right']),
                     beam_index=0b1, distance=0.5 * layout.inch, angle=layout.cardinal['right'],
                     mount_type=optomech.skate_mount)),
        ("Beam_294nm", lambda bp: bp.add_beam_path(x=0.5 * layout.inch, y=input_y_588nm, angle=layout.cardinal['right'])),
        ("Cooling_294nm", lambda bp: laser_cooling_subsystem(bp, ion_trap_x=3 * layout.inch, ion_trap_y=3 * layout.inch,
                                                            thumbscrews=True, littrow_angle=littrow_angle_294nm,
                                                            beam_path=bp.add_beam_path(x=0.5 * layout.inch, y=input_y_588nm, angle=layout.cardinal['right']))),
        ("Photoionization_422nm", lambda bp: tune_and_shg_422nm(bp)),
        ("Repumping_866nm", lambda bp: repump_subsystem_ECDL_mirrored(bp, beam=generate_866nm_subsystem(bp),
                                                                     x=gap + 0.5 * layout.inch, y=input_y_850nm,
                                                                     thumbscrews=True, littrow_angle=littrow_angle_866nm)),
        ("Cooling_397nm", lambda bp: laser_cooling_subsystem(bp, ion_trap_x=4 * layout.inch, ion_trap_y=input_y_405nm_1,
                                                            thumbscrews=True, littrow_angle=littrow_angle_397nm)),
        ("Repumping_403nm", lambda bp: repump_subsystem_ECDL_mirrored(bp, beam=None, x=gap + 1 * layout.inch, y=input_y_405nm_2,
                                                                     thumbscrews=True, littrow_angle=littrow_angle_403nm)),
        ("AOM_397nm", lambda bp: bp.place_element_along_beam("AOM 397nm", aom, bp.add_beam_path(x=4 * layout.inch, y=input_y_405nm_1, angle=layout.cardinal['right']),
                                                            beam_index=0b1, distance=0.5 * layout.inch, angle=layout.cardinal['right'])),
        ("AOM_866nm", lambda bp: bp.place_element_along_beam("AOM 866nm", aom, bp.add_beam_path(x=gap + 0.5 * layout.inch, y=input_y_850nm, angle=layout.cardinal['right']),
                                                            beam_index=0b1, distance=0.5 * layout.inch, angle=layout.cardinal['right'])),
        ("AOM_403nm", lambda bp: bp.place_element_along_beam("AOM 403nm", aom, bp.add_beam_path(x=gap + 1 * layout.inch, y=input_y_405nm_2, angle=layout.cardinal['right']),
                                                            beam_index=0b1, distance=0.5 * layout.inch, angle=layout.cardinal['right'])),
        ("AOM_294nm", lambda bp: bp.place_element_along_beam("AOM 294nm", aom, bp.add_beam_path(x=0.5 * layout.inch, y=input_y_588nm, angle=layout.cardinal['right']),
                                                            beam_index=0b1, distance=0.5 * layout.inch, angle=layout.cardinal['right'])),
        ("Mirror_866nm", lambda bp: bp.place_element_along_beam("Mirror 866nm", optomech.circular_mirror, bp.add_beam_path(x=gap + 0.5 * layout.inch, y=input_y_850nm, angle=layout.cardinal['right']),
                                                               beam_index=0b1, distance=1 * layout.inch, angle=layout.turn['up-right'],
                                                               mount_type=optomech.mirror_mount_k05s1)),
        ("Mirror_294nm", lambda bp: bp.place_element_along_beam("Mirror 294nm", optomech.circular_mirror, bp.add_beam_path(x=0.5 * layout.inch, y=input_y_588nm, angle=layout.cardinal['right']),
                                                               beam_index=0b1, distance=1 * layout.inch, angle=layout.turn['up-right'],
                                                               mount_type=optomech.mirror_mount_k05s1)),
        ("StepMotor_397nm", lambda bp: bp.place_element("Step Motor 397nm", stepper_motor, x=1.5 * layout.inch, y=input_y_405nm_1,
                                                       angle=layout.cardinal['right'])),
        ("StepMotor_866nm", lambda bp: bp.place_element("Step Motor 866nm", stepper_motor, x=1.5 * layout.inch, y=input_y_850nm,
                                                       angle=layout.cardinal['right'])),
        ("StepMotor_403nm", lambda bp: bp.place_element("Step Motor 403nm", stepper_motor, x=1.5 * layout.inch, y=input_y_405nm_2,
                                                       angle=layout.cardinal['right'])),
        ("StepMotor_294nm", lambda bp: bp.place_element("Step Motor 294nm", stepper_motor, x=1.5 * layout.inch, y=input_y_588nm,
                                                       angle=layout.cardinal['right'])),
        ("PMTArray", lambda bp: bp.place_element("PMT Array", pmt_array, x=base_dx - gap, y=0, angle=layout.cardinal['left'])),
        ("FPGA", lambda bp: bp.place_element("FPGA", fpga_board, x=4.5 * layout.inch, y=1.5 * layout.inch,
                                            angle=layout.cardinal['right'])),
        ("MSAE_Cavity", lambda bp: bp.place_element("MSAE Cavity", mass_selective_axial_ejection_cavity, x=3 * layout.inch, y=3.5 * layout.inch,
                                                   angle=layout.cardinal['right'])),
        ("ICPMS_Port", lambda bp: bp.place_element("ICP-MS Port", ion_injection_port, x=2.5 * layout.inch, y=3 * layout.inch,
                                                  angle=layout.cardinal['right']))
    ]

    placements = {
            "SHG_588nm_to_294nm": App.Placement(App.Vector(0, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Beam_294nm": App.Placement(App.Vector(0.5 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Cooling_294nm": App.Placement(App.Vector(3 * layout.inch, 3 * layout.inch, 0), App.Rotation(0, 0, 90)),
            "Photoionization_422nm": App.Placement(App.Vector(1 * layout.inch, input_y_850nm_2, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Repumping_866nm": App.Placement(App.Vector(gap + 0.5 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, 90)),
            "Cooling_397nm": App.Placement(App.Vector(4 * layout.inch, input_y_405nm_1, 0), App.Rotation(0, 0, 90)),
            "Repumping_403nm": App.Placement(App.Vector(gap + 1 * layout.inch, input_y_405nm_2, 0), App.Rotation(0, 0, 90)),
            "AOM_397nm": App.Placement(App.Vector(4 * layout.inch + 0.5 * layout.inch, input_y_405nm_1, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "AOM_866nm": App.Placement(App.Vector(gap + 0.5 * layout.inch + 0.5 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "AOM_403nm": App.Placement(App.Vector(gap + 1 * layout.inch + 0.5 * layout.inch, input_y_405nm_2, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "AOM_294nm": App.Placement(App.Vector(0.5 * layout.inch + 0.5 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Mirror_866nm": App.Placement(App.Vector(gap + 0.5 * layout.inch + 1 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, layout.turn['up-right'])),
            "Mirror_294nm": App.Placement(App.Vector(0.5 * layout.inch + 1 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.turn['up-right'])),
            "StepMotor_397nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_405nm_1, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "StepMotor_866nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "StepMotor_403nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_405nm_2, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "StepMotor_294nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "PMTArray": App.Placement(App.Vector(base_dx - gap, 0, 0), App.Rotation(0, 0, layout.cardinal['left'])),
            "FPGA": App.Placement(App.Vector(4.5 * layout.inch, 1.5 * layout.inch, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "MSAE_Cavity": App.Placement(App.Vector(3 * layout.inch, 3.5 * layout.inch, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "ICPMS_Port": App.Placement(App.Vector(2.5 * layout.inch, 3 * layout.inch, 0), App.Rotation(0, 0, layout.cardinal['right']))
        }

    is_mem = True
    if is_mem:
        #master_doc = App.newDocument("IsotopeSeparation")
        #App.ActiveDocument.openTransaction("Create Master")
        for name, create_func in subcomponents:
            obj = None
            is_collect = False
            try:
                obj = create_func(baseplate)
                if obj:
                    #if isinstance(obj, list):
                    #    obj = obj[0]  # Take the first object if a list is returned
                    #created_objects[name] = obj
                    print(f"Created {name}: {obj.Label} at {obj.Placement.Base}", flush=True)
                    is_collect = True
                    # Add to baseplate hierarchy if supported
                    #if hasattr(baseplate, 'ChildObjects'):
                   #     baseplate.ChildObjects = baseplate.ChildObjects + [obj]
                else:
                    print(f"Warning: No object created for {name}")
            except Exception as e:
                print(f"Error creating {name}: {e}", flush=True)
        #    App.ActiveDocument.recompute()  # Recompute after each addition to ensure consistency
            if is_collect:
                del obj
                gc.collect()  # Free memory periodically
        App.ActiveDocument.recompute()  # Recompute after each addition to ensure consistency
    else:
        '''
            TODO: FIGURE OUT HOW TO STICH TOGETHER PROPERLY
        '''
        output_dir = os.path.join(script_dir, 'output_components')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        main_component_name_map = {}

        # Generate individual files
        for name, create_func in subcomponents:
            doc = App.newDocument(name)
            App.ActiveDocument.openTransaction(f"Create {name}")
            bp = layout.baseplate(base_dx, base_dy, base_dz, x=x, y=y, angle=angle, gap=gap, mount_holes=mount_holes)
            baseplate_group = doc.addObject("App::DocumentObjectGroup", "BaseplateGroup")
            main_obj = create_func(bp)
            if main_obj:
                if isinstance(main_obj, list):
                    main_obj = main_obj[0]  # Take the first object if a list is returned
                print(f"Created primary object for {name}: {main_obj.Label} (Name: {main_obj.Name})")
                main_component_name_map[name] = main_obj.Name
                baseplate_group.addObject(main_obj)
            else:
                print(f"Warning: No primary object created for {name}")
            doc.recompute()  # Single recompute
            fcstd_path = os.path.join(output_dir, f"{name}.fcstd")
            doc.saveAs(fcstd_path)  # Save with explicit path
            # Ensure save is complete
            import time
            time.sleep(1)  # Brief delay to allow file write
            App.ActiveDocument.commitTransaction()
            App.closeDocument(name)
            del bp, baseplate_group, main_obj, doc  # Clear references
            gc.collect()

        # Create master document
        master_doc = App.newDocument("IsotopeSeparation")
        App.ActiveDocument.openTransaction("Create Master")
        master_baseplate = master_doc.addObject("Part::FeaturePython", "Baseplate")
        ECDL_isolator_baseplate(master_baseplate)
        master_doc.recompute()

        # Define placements
        placements = {
            "SHG_588nm_to_294nm": App.Placement(App.Vector(0, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Beam_294nm": App.Placement(App.Vector(0.5 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Cooling_294nm": App.Placement(App.Vector(3 * layout.inch, 3 * layout.inch, 0), App.Rotation(0, 0, 90)),
            "Photoionization_422nm": App.Placement(App.Vector(1 * layout.inch, input_y_850nm_2, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Repumping_866nm": App.Placement(App.Vector(gap + 0.5 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, 90)),
            "Cooling_397nm": App.Placement(App.Vector(4 * layout.inch, input_y_405nm_1, 0), App.Rotation(0, 0, 90)),
            "Repumping_403nm": App.Placement(App.Vector(gap + 1 * layout.inch, input_y_405nm_2, 0), App.Rotation(0, 0, 90)),
            "AOM_397nm": App.Placement(App.Vector(4 * layout.inch + 0.5 * layout.inch, input_y_405nm_1, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "AOM_866nm": App.Placement(App.Vector(gap + 0.5 * layout.inch + 0.5 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "AOM_403nm": App.Placement(App.Vector(gap + 1 * layout.inch + 0.5 * layout.inch, input_y_405nm_2, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "AOM_294nm": App.Placement(App.Vector(0.5 * layout.inch + 0.5 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "Mirror_866nm": App.Placement(App.Vector(gap + 0.5 * layout.inch + 1 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, layout.turn['up-right'])),
            "Mirror_294nm": App.Placement(App.Vector(0.5 * layout.inch + 1 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.turn['up-right'])),
            "StepMotor_397nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_405nm_1, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "StepMotor_866nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_850nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "StepMotor_403nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_405nm_2, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "StepMotor_294nm": App.Placement(App.Vector(1.5 * layout.inch, input_y_588nm, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "PMTArray": App.Placement(App.Vector(base_dx - gap, 0, 0), App.Rotation(0, 0, layout.cardinal['left'])),
            "FPGA": App.Placement(App.Vector(4.5 * layout.inch, 1.5 * layout.inch, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "MSAE_Cavity": App.Placement(App.Vector(3 * layout.inch, 3.5 * layout.inch, 0), App.Rotation(0, 0, layout.cardinal['right'])),
            "ICPMS_Port": App.Placement(App.Vector(2.5 * layout.inch, 3 * layout.inch, 0), App.Rotation(0, 0, layout.cardinal['right']))
        }
        linking = False

        # Import subcomponents and link based on Document.xml
        for name, _ in subcomponents:
            print(f"Processing subcomponent from file: {name}")
            fcstd_path = os.path.join(output_dir, f"{name}.fcstd")

            if os.path.exists(fcstd_path):
                if not linking:
                    temp_doc = App.openDocument(fcstd_path)
                    new_obj = None
                    primary_obj_name = main_component_name_map.get(name)
                    if primary_obj_name:
                        primary_obj = temp_doc.getObject(primary_obj_name)
                        if primary_obj:
                            # Copy the object to the master document, including dependencies
                            new_obj = master_doc.copyObject(primary_obj, True)
                            # Adjust placement if defined
                            if name in placements:
                                new_obj.Placement = placements[name]
                            else:
                                print(f"Warning: No placement defined for {name}, using original placement")
                            # Optionally add to baseplate hierarchy (if supported)
                            if hasattr(baseplate, 'ChildObjects'):
                                baseplate.ChildObjects += [new_obj]

                            '''
                                if hasattr(obj, "ChildObjects"):
                                    for child in obj.ChildObjects:
                                        if hasattr(child, 'BasePlacement') and hasattr(child, 'RelativePlacement'):
                                            child.BasePlacement.Base = obj.BasePlacement.Base + child.RelativePlacement.Base
                                            if hasattr(child, "Angle"):
                                                obj.BasePlacement.Rotation = App.Rotation(App.Vector(0, 0, 1), obj.Angle)
                                            else:
                                                child.BasePlacement = App.Placement(child.BasePlacement.Base, obj.BasePlacement.Rotation, -child.RelativePlacement.Base)
                                                child.BasePlacement.Rotation = child.BasePlacement.Rotation.multiply(child.RelativePlacement.Rotation)
                                            self.needs_recompute = True  # Mark for recompute
                                if hasattr(obj, "RelativeObjects"):
                                    for child in obj.RelativeObjects:
                                        if hasattr(child, 'BasePlacement') and hasattr(child, 'RelativePlacement'):
                                            child.BasePlacement.Base = obj.BasePlacement.Base + child.RelativePlacement.Base
                                            self.needs_recompute = True  # Mark for recompute
                            '''

                            #baseplate.ViewProvider.updateData(new_obj, "BasePlacement")
                            master_doc.recompute()
                        else:
                            print(f"Warning: Object {primary_obj_name} not found in {fcstd_path}")
                    else:
                        print(f"Warning: No primary object name defined for {name}")
                    del temp_doc, new_obj
                    gc.collect()
                else:
                    # Linking logic remains unchanged (use previous linking code)
                    with zipfile.ZipFile(fcstd_path, 'r') as zf:
                        with zf.open('Document.xml') as xml_file:
                            tree = ET.parse(xml_file)
                            root = tree.getroot()

                            objects_with_types = {obj.get('name'): {'type': obj.get('type'), 'touched': obj.get('Touched', '0') == '1'}
                                                for obj in root.find('.//Objects').findall('Object') if obj.get('name')}
                            print(f"Objects with types: {objects_with_types}")

                            objects_with_labels = {obj.get('name'): obj.find('.//Property[@name="Label"]/String').get('value')
                                                 for obj in root.find('.//ObjectData').findall('Object')
                                                 if obj.get('name') and obj.find('.//Property[@name="Label"]/String') is not None}

                            target_name = None
                            for obj_name, attrs in objects_with_types.items():
                                if obj_name == "Baseplate" or "Mount_Hole" in obj_name or "Hole" in obj_name:
                                    continue
                                if attrs['type'] in ["Part::FeaturePython", "Part::Box", "Part::Cylinder"]:
                                    if main_component_name_map[name] == obj_name:
                                        target_name = obj_name
                                        break
                            if not target_name:
                                print(f"Warning: No suitable primary object found in {name}.fcstd")
                                for obj_name, attrs in objects_with_types.items():
                                    if attrs['type'] in ["Part::FeaturePython", "Part::Box", "Part::Cylinder"] and not ("Mount_Hole" in obj_name or "Hole" in obj_name):
                                        target_name = obj_name
                                        print(f"Fallback: Linking {target_name} as primary object")
                                        break

                            target_obj = doc.getObject(target_name)
                            if target_obj:
                                doc.recompute()
                                link_name = f"Link_{name}_{target_name}"
                                print(f"Linking {link_name} from {target_name}")
                                link = master_doc.addObject("App::Link", link_name)
                                try:
                                    link.LinkedObject = (target_obj, [])
                                    if name in placements:
                                        link.Placement = placements[name]
                                    else:
                                        print(f"Warning: No placement defined for {name}, using default")
                                except (AttributeError, RuntimeError) as e:
                                    print(f"Error linking object: {e}")
                                master_doc.recompute()
                            App.closeDocument(doc.Name)
                            del doc, target_obj
                            gc.collect()
            else:
                print(f"Warning: Failed to open document {name}.fcstd")

        
        # Force save to ensure document state
        #master_doc.save()
        master_doc.saveAs(os.path.join(output_dir, "IsotopeSeparation.fcstd"))
        App.closeDocument("IsotopeSeparation")

if is_headless:
    FreeCADGui.showMainWindow()
    mw = FreeCADGui.getMainWindow()
    mw.hide()

    App.newDocument("IsotopeSeparation")
    App.ActiveDocument.openTransaction("Batch Object Creation")
    isotope_separation_baseplate()
    App.ActiveDocument.commitTransaction()
    App.ActiveDocument.recompute()
    App.getDocument("IsotopeSeparation").saveAs("PyOpticL/output.fcstd")
    App.closeDocument("IsotopeSeparation")
else:
    if __name__ == "__main__":
        isotope_separation_baseplate()
        App.ActiveDocument.commitTransaction()
        App.ActiveDocument.recompute()
        layout.redraw()

end_time = time.time()
print(f"Execution time: {end_time - start_time} seconds")