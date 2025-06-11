import time
start_time = time.time()
import sys
import os
import numpy as np
import gc


is_headless = False
# Redirect output to file to reduce memory buffering
sys.stdout = open('debug_output.txt', 'w')

# Debug the directory structure and sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
subsystem_dir = os.path.join(script_dir, 'Design/Subsystem')
module_dir = os.path.join(script_dir, 'Design/Module')

# Print paths for debugging
print(f"Script directory: {script_dir}")
print(f"Subsystem directory: {subsystem_dir}, Exists: {os.path.exists(subsystem_dir)}")
print(f"Module directory: {module_dir}, Exists: {os.path.exists(module_dir)}")

# Add directories to sys.path
sys.path.append(subsystem_dir)
sys.path.append(module_dir)
sys.path.append(script_dir)  # For custom_optomech.py

# Print sys.path to confirm
print(f"sys.path: {sys.path}")

from PyOpticL import layout, optomech, laser
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

# Mount hole coordinates (updated for 12x12 inch baseplate)
mount_holes = [
    (0 * layout.inch, 0 * layout.inch),  # Bottom-left
    (0 * layout.inch, 11 * layout.inch),  # Top-left
    (11 * layout.inch, 0 * layout.inch),  # Bottom-right
    (11 * layout.inch, 11 * layout.inch)  # Top-right
]

def isotope_separation_baseplate(x=0, y=0, angle=0):
    # Create baseplate (10x10 inches for the grid)
    baseplate = layout.baseplate(10 * layout.inch, 10 * layout.inch, 0.5 * layout.inch, x=x, y=y, angle=angle)
    master_doc = App.ActiveDocument
    #master_doc.addObject(baseplate)
    #master_doc.recompute()
    print(f"Baseplate dimensions: {10 * layout.inch} x {10 * layout.inch} x {0.5 * layout.inch}")

    created_objects = {}

    # Define input y-coordinates and Littrow angles
    input_y_588nm = 0.5 * layout.inch
    input_y_405nm_1 = 2.0 * layout.inch
    input_y_850nm = 3.5 * layout.inch
    

    # Littrow angles for tuned and SHG wavelengths with debug
    grating_pitch_d = 1/3600  # Lines per mm
    grating_pitch_d_866 = 1/1800  # Lines per mm for 866 nm and for 844 nm

    # Tuned wavelengths
    littrow_angle_294nm = np.arcsin(294e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~29.8° (SHG from 588 nm, Ga-68⁺ cooling)
    littrow_angle_397nm = np.arcsin(397e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~40.7° (tuned from 405 nm)
    littrow_angle_403nm = np.arcsin(403e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~41.5° (tuned from 405 nm)
    littrow_angle_422nm = np.arcsin(422e-6 / (2 * grating_pitch_d)) * 180 / np.pi  # ~49.4° (for Ca⁺ photoionization)
    littrow_angle_844nm = np.arcsin(844e-6 / (2 * grating_pitch_d_866)) * 180 / np.pi  # ~50.1° (tuned from 850 nm for 422 nm SHG)
    #littrow_angle_858nm = np.arcsin(858e-9 / (2 * grating_pitch_d)) * 180 / np.pi  # ~45.6° (SHG from 850 nm)
    littrow_angle_866nm = np.arcsin(866e-6 / (2 * grating_pitch_d_866)) * 180 / np.pi  # ~51.2° (SHG from 850 nm)

    gap = layout.inch/8

    # Group 1: 588 nm to 294 nm (manual handling)
    beam_588nm = baseplate.add_beam_path(x=gap, y=input_y_588nm, angle=layout.cardinal['right'])
    created_objects["Beam_588nm"] = beam_588nm
    master_doc.recompute()


    # add input fiberport, defined at the same coordinates as beam
    baseplate.place_element("Input Fiberport beam_588nm", optomech.fiberport_mount_hca3, x=gap, y=input_y_588nm, angle=layout.cardinal['right'])

    shg_588nm_to_294nm = baseplate.place_element_along_beam("SHG_588nm_to_294nm", optomech.cube_splitter, beam_588nm, beam_index=0b1, distance=2 * layout.inch, angle=layout.cardinal['right'], mount_type=optomech.skate_mount)
    #created_objects["SHG_588nm_to_294nm"] = shg_588nm_to_294nm
    master_doc.recompute()

    #beam_294nm = baseplate.add_beam_path(x=2 * layout.inch, y=input_y_588nm, angle=littrow_angle_294nm)
    #created_objects["Beam_294nm"] = beam_294nm
    #master_doc.recompute()

    #aom_294nm = baseplate.place_element_along_beam("AOM_294nm", aom, beam_588nm, beam_index=0b11, distance=2 * layout.inch, angle=layout.turn['right-up'])
    #created_objects["AOM_294nm"] = aom_294nm
    #master_doc.recompute()


    mirror_294nm_1 = baseplate.place_element_along_beam("Mirror_294nm_1", optomech.circular_mirror, beam_588nm, diameter=layout.inch/8, beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['right-up'])
    created_objects["Mirror_294nm_1"] = mirror_294nm_1

    mirror_294nm_2 = baseplate.place_element_along_beam("Mirror_294nm_2", optomech.circular_mirror, beam_588nm, diameter=layout.inch/8, beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['right-down'])
    created_objects["Mirror_294nm_2"] = mirror_294nm_2

    mirror_294nm_3 = baseplate.place_element_along_beam("Mirror_294nm_3", optomech.circular_mirror, beam_588nm, diameter=layout.inch/8, beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['left-down']-20)
    created_objects["Mirror_294nm_3"] = mirror_294nm_3
    
    #lens_294nm = baseplate.place_element_along_beam("Lens_294nm", optomech.lens, beam_588nm, beam_index=0b1, distance=1 * layout.inch, angle=0)
    #created_objects["Lens_294nm"] = lens_294nm

    



    # Group 2: 405 nm to 397 nm and 403 nm
    beam_405nm = baseplate.add_beam_path(x=gap, y=input_y_405nm_1, angle=layout.cardinal['right'])
    created_objects["Beam_405nm"] = beam_405nm

    # Add input fiberport, defined at the same coordinates as beam
    baseplate.place_element("Input Fiberport_beam_405nm", optomech.fiberport_mount_hca3, x=gap, y=input_y_405nm_1, angle=layout.cardinal['right'])

    beamsplitter_405nm = baseplate.place_element_along_beam("BeamSplitter_405nm", optomech.cube_splitter, beam_405nm, beam_index=0b1, distance=4.25 * layout.inch, angle=layout.cardinal['right'],mount_type=optomech.skate_mount)
    created_objects["BeamSplitter_405nm"] = beamsplitter_405nm
    master_doc.recompute()

    # Use laser_mount_km100pm_LMR1 for tuning 405 nm to 397 nm
    #tuner_397nm = App.ActiveDocument.addObject("Part::FeaturePython", "Tuner_397nm")

    tuner_397nm = baseplate.place_element_along_beam("Tuner_397nm", optomech.laser_mount_km100pm_LMR1, beam_405nm, beam_index=0b10, distance=4.5 * layout.inch, angle=layout.cardinal['right'],drill=True, littrow_angle=littrow_angle_397nm)

    #laser_mount_km100pm_LMR1(tuner_397nm, drill=True, littrow_angle=53.43)  # Adjust LittrowAngle for 397 nm
    #tuner_397nm.Placement.Base = App.Vector(gap + 2 * layout.inch, input_y_405nm_1, 0)  # Position after beamsplitter
    #master_doc.addObject(tuner_397nm)
    created_objects["Tuner_397nm"] = tuner_397nm
    master_doc.recompute()
    #'''

    # Mirror sequence following the tuned 397 nm beam
    mirror_397nm_1 = baseplate.place_element_along_beam("Mirror_397nm_1", optomech.circular_mirror, beam_405nm, diameter=layout.inch/8, beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['right-down'])
    created_objects["Mirror_397nm_1"] = mirror_397nm_1
    mirror_397nm_2 = baseplate.place_element_along_beam("Mirror_397nm_2", optomech.circular_mirror, beam_405nm, diameter=layout.inch/8, beam_index=0b10, distance=8 * layout.inch, angle=layout.turn['left-down']-13)
    created_objects["Mirror_397nm_2"] = mirror_397nm_2
    master_doc.recompute()

    tuner_403nm = baseplate.place_element_along_beam("Tuner_403nm", optomech.laser_mount_km100pm_LMR1_floating, beam_405nm, beam_index=0b11, distance=2.5 * layout.inch, angle=layout.cardinal['up'], littrow_angle=littrow_angle_403nm, drill=True)#, height_offset_in=0)
    created_objects["Tuner_403nm"] = tuner_403nm


    mirror_403nm_1 = baseplate.place_element_along_beam("Mirror_403nm_1", optomech.circular_mirror, beam_405nm, diameter=layout.inch/8, beam_index=0b11, distance=2.5 * layout.inch, angle=layout.turn['left-down']-10.5)
    created_objects["Mirror_403nm_1"] = mirror_403nm_1
    master_doc.recompute()

    '''
    






    # Group 3: 850 nm to 866 nm and 422 nm
    beam_850nm = baseplate.add_beam_path(x=0, y=input_y_850nm, angle=layout.cardinal['right'])
    created_objects["Beam_850nm"] = beam_850nm

    beamsplitter_850nm = baseplate.place_element_along_beam("BeamSplitter_850nm", optomech.cube_splitter, beam_850nm,
                                                            beam_index=0b1, distance=2 * layout.inch, angle=layout.cardinal['right'])
    created_objects["BeamSplitter_850nm"] = beamsplitter_850nm

    beam_850nm_transmitted = baseplate.add_beam_path(x=2 * layout.inch, y=input_y_850nm, angle=layout.cardinal['right'])
    created_objects["Beam_850nm_Transmitted"] = beam_850nm_transmitted

    shg_850nm_to_866nm = baseplate.place_element_along_beam("SHG_850nm_to_866nm", optomech.cube_splitter, beam_850nm_transmitted,
                                                            beam_index=0b10, distance=2 * layout.inch, angle=littrow_angle_866nm)
    created_objects["SHG_850nm_to_866nm"] = shg_850nm_to_866nm

    mirror_866nm_1 = baseplate.place_element_along_beam("Mirror_866nm_1", optomech.circular_mirror, shg_850nm_to_866nm,
                                                        beam_index=0b10, distance=2 * layout.inch, angle=layout.cardinal['up'] + littrow_angle_866nm)
    created_objects["Mirror_866nm_1"] = mirror_866nm_1

    mirror_866nm_2 = baseplate.place_element_along_beam("Mirror_866nm_2", optomech.circular_mirror, mirror_866nm_1,
                                                        beam_index=0b10, distance=2 * layout.inch, angle=layout.cardinal['left'])
    created_objects["Mirror_866nm_2"] = mirror_866nm_2

    mirror_866nm_3 = baseplate.place_element_along_beam("Mirror_866nm_3", optomech.circular_mirror, mirror_866nm_2,
                                                        beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['left-down'])
    created_objects["Mirror_866nm_3"] = mirror_866nm_3

    beam_850nm_reflected = baseplate.add_beam_path(x=2 * layout.inch, y=input_y_850nm - 0.5 * layout.inch, angle=layout.cardinal['right'])
    created_objects["Beam_850nm_Reflected"] = beam_850nm_reflected

    tuner_844nm = baseplate.place_element_along_beam("Tuner_844nm", optomech.tuning_stage, beam_850nm_reflected,
                                                     beam_index=0b11, distance=2 * layout.inch, angle=littrow_angle_422nm)  # Note: Using 422nm angle as placeholder
    created_objects["Tuner_844nm"] = tuner_844nm

    shg_844nm_to_422nm = baseplate.place_element_along_beam("SHG_844nm_to_422nm", optomech.cube_splitter, tuner_844nm,
                                                            beam_index=0b11, distance=2 * layout.inch, angle=littrow_angle_422nm)
    created_objects["SHG_844nm_to_422nm"] = shg_844nm_to_422nm

    aom_422nm = baseplate.place_element_along_beam("AOM_422nm", aom, shg_844nm_to_422nm,
                                                   beam_index=0b11, distance=2 * layout.inch, angle=layout.cardinal['up'])
    created_objects["AOM_422nm"] = aom_422nm

    mirror_422nm_1 = baseplate.place_element_along_beam("Mirror_422nm_1", optomech.circular_mirror, aom_422nm,
                                                        beam_index=0b11, distance=2 * layout.inch, angle=layout.cardinal['up'])
    created_objects["Mirror_422nm_1"] = mirror_422nm_1

    mirror_422nm_2 = baseplate.place_element_along_beam("Mirror_422nm_2", optomech.circular_mirror, mirror_422nm_1,
                                                        beam_index=0b11, distance=2 * layout.inch, angle=layout.cardinal['left'])
    created_objects["Mirror_422nm_2"] = mirror_422nm_2

    mirror_422nm_3 = baseplate.place_element_along_beam("Mirror_422nm_3", optomech.circular_mirror, mirror_422nm_2,
                                                        beam_index=0b11, distance=2 * layout.inch, angle=layout.turn['left-down'])
    created_objects["Mirror_422nm_3"] = mirror_422nm_3

    lens_422nm = baseplate.place_element_along_beam("Lens_422nm", optomech.lens, mirror_422nm_3,
                                                    beam_index=0b11, distance=1 * layout.inch, angle=0)
    created_objects["Lens_422nm"] = lens_422nm
    '''

    # Add ion trap target area (3.2 mm x 3.2 mm = 0.126 x 0.126 inches)
    ion_trap = master_doc.addObject("Part::Box", "IonTrap")
    ion_trap.Placement.Base = App.Vector(0, 0, 0)
    ion_trap.Length = 0.126 * layout.inch
    ion_trap.Width = 0.126 * layout.inch
    ion_trap.Height = 0.1 * layout.inch
    created_objects["IonTrap"] = ion_trap

    # Add to baseplate hierarchy if supported
    if hasattr(baseplate, 'ChildObjects'):
        baseplate.ChildObjects = list(created_objects.values())

    '''
    # Execute groups sequentially
    for group_idx, group in enumerate(component_groups):
        prev_obj = None
        for lambda_func, name in group:
            try:
                if prev_obj is not None and lambda_func.__code__.co_argcount > 1:
                    obj = lambda_func(baseplate, prev_obj)
                else:
                    obj = lambda_func(baseplate)
                if obj:
                    if isinstance(obj, list):
                        obj = obj[0]
                    created_objects[name] = obj
                    print(f"Created {name}: {obj.Label} at {obj.Placement.Base}")
                    prev_obj = obj if "Beam" in name or any(substring in name for substring in ["Tuner", "SHG", "AOM"]) else prev_obj
            except Exception as e:
                print(f"Error in group {group_idx + 1}: {e}")
        master_doc.recompute()

       #gc.collect()
    '''

    # Add ion trap target area (3.2 mm x 3.2 mm = 0.126 x 0.126 inches)
    ion_trap = master_doc.addObject("Part::Box", "IonTrap")
    ion_trap.Placement.Base = App.Vector(0, 0, 0)
    ion_trap.Length = 0.126 * layout.inch
    ion_trap.Width = 0.126 * layout.inch
    ion_trap.Height = 0.1 * layout.inch
    created_objects["IonTrap"] = ion_trap

    # Add to baseplate hierarchy if supported
    if hasattr(baseplate, 'ChildObjects'):
        baseplate.ChildObjects = list(created_objects.values())

    if not os.path.exists(script_dir):
        os.makedirs(script_dir)

    master_doc.recompute()
    master_doc.saveAs(os.path.join(script_dir, "IsotopeSeparation.fcstd"))
    if not is_headless:
        App.ActiveDocument.commitTransaction()
    else:
        App.closeDocument("IsotopeSeparation")

    print("Assembly completed successfully")
    return baseplate



if __name__ == "__main__":
  isotope_separation_baseplate()
  end_time = time.time()
  print(f"Execution time: {end_time - start_time} seconds")