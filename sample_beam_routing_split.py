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

def group1_baseplate_588nm(x=0, y=0, angle=0):
    # Create smaller baseplate for Group 1, aligned with ECDL y-position
    x_max = 10
    y_max = 10
    z_max = 0.5
    input_y_588nm = 0.5 * layout.inch
    baseplate = layout.baseplate(x_max * layout.inch, y_max * layout.inch, z_max * layout.inch, x=x, y=y, angle=angle)  # Shift y to align with ECDL
    master_doc = App.ActiveDocument
    #master_doc.addObject(baseplate)
    #master_doc.recompute()
    print(f"Baseplate dimensions: {x_max * layout.inch} x {y_max * layout.inch} x {z_max * layout.inch}")

    created_objects = {}

    # Define input y-coordinates and Littrow angles
    gap = layout.inch/8

    # Littrow angles for tuned and SHG wavelengths with debug
    grating_pitch_d_588 = 1/1200
    littrow_angle_588nm = np.arcsin(588e-6 / (2 * grating_pitch_d_588)) * 180 / np.pi  # ~29.8° (incomping from ecdl)

    # Group 1: 588 nm to 294 nm (manual handling)
    beam_588nm = baseplate.add_beam_path(x=gap, y=input_y_588nm + 0.05 * layout.inch - (input_y_588nm - 0.5 * layout.inch)+ (2 * layout.inch), angle=layout.cardinal['right'])
    #print(beam_588nm.BasePlacement.__dict__)
    baseplate.place_element("ECDL_588nm", optomech.ECDL, x=gap, y=input_y_588nm - (input_y_588nm - 0.5 * layout.inch)+ (2 * layout.inch), stage_thickness=1, stage_length=50,  angle=layout.cardinal['right'], littrow_angle=littrow_angle_588nm, cover_box=True)
    created_objects["ECDL_588nm"] = beam_588nm
    #master_doc.recompute()

    mirror_ECDL_588nm = baseplate.place_element_along_beam("Mirror_ECDL_588nm", optomech.circular_mirror, beam_588nm, diameter=layout.inch/8, beam_index=0b1, distance=3.25 * layout.inch, angle=layout.turn['left-down']+24)
    created_objects["Mirror_ECDL_588nm"] = mirror_ECDL_588nm

    shg_588nm_to_294nm = baseplate.place_element_along_beam("SHG_588nm_to_294nm", optomech.cube_splitter, beam_588nm, beam_index=0b1, distance=3.5 * layout.inch, angle=layout.cardinal['right'], mount_type=optomech.skate_mount)
    created_objects["SHG_588nm_to_294nm"] = shg_588nm_to_294nm
    #master_doc.recompute()

    
    #master_doc.recompute()

    mirror_294nm_1 = baseplate.place_element_along_beam("Mirror_294nm_1", optomech.circular_mirror, beam_588nm, diameter=layout.inch/8, beam_index=0b11, distance=3.25 * layout.inch, angle=layout.turn['right-down']+0.25,mount_type=optomech.skate_mount)
    created_objects["Mirror_294nm_1"] = mirror_294nm_1

    # Adding AOM from ca 40 example
    aom_294nm = baseplate.place_element_along_beam("AOM_294nm", optomech.isomet_1205c_on_km100pm, beam_588nm, beam_index=0b11, distance=50, angle=layout.cardinal['right'], forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    created_objects["AOM_294nm"] = aom_294nm

    #mirror_294nm_2 = baseplate.place_element_along_beam("Mirror_294nm_2", optomech.circular_mirror, beam_588nm, diameter=layout.inch/8, beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['right-down'],mount_type=optomech.skate_mount)
    #created_objects["Mirror_294nm_2"] = mirror_294nm_2

    #mirror_294nm_3 = baseplate.place_element_along_beam("Mirror_294nm_3", optomech.circular_mirror, beam_588nm, diameter=layout.inch/8, beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['left-down']-20,mount_type=optomech.skate_mount)
    #created_objects["Mirror_294nm_3"] = mirror_294nm_3

    # add output fiberport, defined at the same coordinates as output beam
    baseplate.place_element("Output Fiberport beam_588nm", optomech.fiberport_mount_hca3, x=gap, y=3.5 *layout.inch - (input_y_588nm - 0.5 * layout.inch) + (2 * layout.inch) + (1 * layout.inch), angle=layout.cardinal['right'])
    master_doc.recompute()

    #lens_294nm = baseplate.place_element_along_beam("Lens_294nm", optomech.lens, beam_588nm, beam_index=0b1, distance=1 * layout.inch, angle=0)
    #created_objects["Lens_294nm"] = lens_294nm

    if not os.path.exists(script_dir):
        os.makedirs(script_dir)

    master_doc.recompute()
    master_doc.saveAs(os.path.join(script_dir, "Group1_588nm.fcstd"))
    if not is_headless:
        App.ActiveDocument.commitTransaction()
    else:
        App.closeDocument("Group1_588nm")

    print("Group 1 (588 nm) assembly completed successfully")
    return baseplate

def group2_baseplate_405nm(x=0, y=0, angle=0):
    # Create smaller baseplate for Group 2, aligned with ECDL y-position
    x_max = 12
    y_max = 12
    z_max = 0.5
    input_y_405nm_1 = 2.0 * layout.inch
    y_offset = 5 * layout.inch
    input_y_405nm_1 += y_offset
    baseplate = layout.baseplate(x_max * layout.inch, y_max * layout.inch, z_max * layout.inch, x=x, y=input_y_405nm_1/12, angle=angle)  # Shift y to align with ECDL
    master_doc = App.ActiveDocument
    #master_doc.addObject(baseplate)
    #master_doc.recompute()
    print(f"Baseplate dimensions: {x_max * layout.inch} x {y_max * layout.inch} x {z_max * layout.inch}")

    created_objects = {}

    # Define input y-coordinates and Littrow angles
    gap = layout.inch/8

    # Littrow angles for tuned and SHG wavelengths with debug
    grating_pitch_d_405 = 1/1745
    littrow_angle_405nm = np.arcsin(403e-6 / (2 * grating_pitch_d_405)) * 180 / np.pi
    littrow_angle_397nm = np.arcsin(397e-6 / (2 * grating_pitch_d_405)) * 180 / np.pi  # ~40.7° (tuned from 405 nm)
    littrow_angle_403nm = np.arcsin(403e-6 / (2 * grating_pitch_d_405)) * 180 / np.pi  # ~41.5° (tuned from 405 nm)

    # Group 2: 405 nm to 397 nm and 403 nm
    baseplate.place_element("ECDL_405nm", optomech.ECDL, x=gap, y=input_y_405nm_1 - (input_y_405nm_1 - 0.5 * layout.inch) + (2 * layout.inch), stage_thickness=1, stage_length=50,  angle=layout.cardinal['right'], littrow_angle=littrow_angle_405nm, cover_box=True)

    beam_405nm = baseplate.add_beam_path(x=gap, y=input_y_405nm_1 + 0.05 * layout.inch - (input_y_405nm_1 - 0.5 * layout.inch) + (2 * layout.inch), angle=layout.cardinal['right'])
    created_objects["Beam_405nm"] = beam_405nm

    mirror_ECDL_405nm = baseplate.place_element_along_beam("Mirror_ECDL_405nm", optomech.circular_mirror, beam_405nm, diameter=layout.inch/8, beam_index=0b1, distance=3.25 * layout.inch, angle=layout.turn['left-down']+24)
    created_objects["Mirror_ECDL_405nm"] = mirror_ECDL_405nm
    

    beamsplitter_405nm = baseplate.place_element_along_beam("BeamSplitter_405nm", optomech.cube_splitter, beam_405nm, beam_index=0b1, distance=3.5 * layout.inch, angle=layout.cardinal['right'],mount_type=optomech.skate_mount)
    created_objects["BeamSplitter_405nm"] = beamsplitter_405nm


    tuner_397nm = baseplate.place_element_along_beam("Tuner_397nm", optomech.laser_mount_km100pm_LMR1, beam_405nm, beam_index=0b10, distance=1.0 * layout.inch, angle=layout.cardinal['right'],drill=True, littrow_angle=littrow_angle_397nm)
    created_objects["Tuner_397nm"] = tuner_397nm
    #master_doc.recompute()

    # Mirror sequence following the tuned 397 nm beam
    mirror_397nm_1 = baseplate.place_element_along_beam("Mirror_397nm_1", optomech.circular_mirror, beam_405nm, diameter=layout.inch/8, beam_index=0b10, distance=2.25 * layout.inch, angle=layout.turn['right-down'],mount_type=optomech.skate_mount)
    created_objects["Mirror_397nm_1"] = mirror_397nm_1


    #aom_397nm = baseplate.place_element_along_beam("AOM_397nm", aom, beam_405nm, beam_index=0b10, distance=2 * layout.inch, angle=layout.turn['right-up'])
    #created_objects["AOM_397nm"] = aom_397nm
    #master_doc.recompute()

    # Adding AOM from ca 40 example
    aom_397nm = baseplate.place_element_along_beam("AOM_397nm", optomech.isomet_1205c_on_km100pm, beam_405nm, beam_index=0b10, distance=70, angle=layout.cardinal['down'], forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    created_objects["AOM_397nm"] = aom_397nm

    # Add output fiberport, defined at the same coordinates as beam
    baseplate.place_element_relative("Output Fiberport_beam_397nm", optomech.fiberport_mount_hca3, mirror_397nm_1, x_off= 0.0 * layout.inch, y_off=-4*layout.inch, angle=layout.cardinal['up'])


    tuner_403nm = baseplate.place_element_along_beam("Tuner_403nm", optomech.laser_mount_km100pm_LMR1_floating, beam_405nm, stage_length=50, beam_index=0b11, distance=3.0 * layout.inch, angle=layout.cardinal['up'], littrow_angle=littrow_angle_403nm, drill=True)#, height_offset_in=0)
    created_objects["Tuner_403nm"] = tuner_403nm
    master_doc.recompute()


    mirror_403nm_1 = baseplate.place_element_along_beam("Mirror_403nm_1", optomech.circular_mirror, beam_405nm, diameter=layout.inch/8, beam_index=0b11, distance=2.0 * layout.inch, angle=layout.turn['right-up']-21, mount_type=optomech.skate_mount)
    created_objects["Mirror_403nm_1"] = mirror_403nm_1


    beamsplitter_403nm = baseplate.place_element_along_beam("BeamSplitter_403nm", optomech.cube_splitter, beam_405nm, beam_index=0b11, distance=1.0 * layout.inch, angle=layout.cardinal['up'],mount_type=optomech.skate_mount)
    created_objects["BeamSplitter_403nm"] = beamsplitter_403nm

    mirror_403nm_2 = baseplate.place_element_along_beam("Mirror_403nm_2", optomech.circular_mirror, beam_405nm, diameter=layout.inch/8, beam_index=0b111, distance=4.0 * layout.inch, angle=layout.turn['right-down'],mount_type=optomech.skate_mount)
    created_objects["Mirror_403nm_2"] = mirror_403nm_2


    # Adding AOM from ca 40 example
    aom_403nm = baseplate.place_element_along_beam("AOM_403nm", optomech.isomet_1205c_on_km100pm, beam_405nm, beam_index=0b110, distance=20, angle=layout.cardinal['right'], forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    created_objects["AOM_403nm"] = aom_403nm

    # Adding AOM from ca 40 example
    aom_403nm_2 = baseplate.place_element_along_beam("AOM_403nm_2", optomech.isomet_1205c_on_km100pm, beam_405nm, beam_index=0b111, distance=20, angle=layout.cardinal['right'], forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    created_objects["AOM_403nm_2"] = aom_403nm_2

    baseplate.place_element("Output Fiberport_beam_403nm", optomech.fiberport_mount_hca3, x=gap, y=y_offset+(1.75*3*layout.inch) - (input_y_405nm_1 - 0.5 * layout.inch) + (3 * layout.inch), angle=layout.cardinal['right'])   

    baseplate.place_element("Output Fiberport_beam_403nm_2", optomech.fiberport_mount_hca3, x=gap, y=y_offset+(2*layout.inch)+(1.75*3*layout.inch) - (input_y_405nm_1 - 0.5 * layout.inch) + (2 * layout.inch) + (3 *layout.inch), angle=layout.cardinal['right'])    

    if not os.path.exists(script_dir):
        os.makedirs(script_dir)

    master_doc.recompute()
    master_doc.saveAs(os.path.join(script_dir, "Group2_405nm.fcstd"))
    if not is_headless:
        App.ActiveDocument.commitTransaction()
    else:
        App.closeDocument("Group2_405nm")

    print("Group 2 (405 nm) assembly completed successfully")
    return baseplate

def group3_baseplate_850nm(x=0, y=0, angle=0):
    # Create smaller baseplate for Group 3, aligned with ECDL y-position
    x_max = 10
    y_max = 10
    z_max = 0.5
    input_y_850nm = 6.5 * layout.inch
    y_offset = 5 * layout.inch
    y_offset *= 1.6
    input_y_850nm += y_offset
    baseplate = layout.baseplate(x_max * layout.inch, y_max * layout.inch, z_max * layout.inch, x=x, y=input_y_850nm/12, angle=angle)  # Shift y to align with ECDL
    master_doc = App.ActiveDocument
    #master_doc.addObject(baseplate)
    #master_doc.recompute()
    print(f"Baseplate dimensions: {x_max * layout.inch} x {y_max * layout.inch} x {z_max * layout.inch}")

    created_objects = {}

    # Define input y-coordinates and Littrow angles
    gap = layout.inch/8

    # Littrow angles for tuned and SHG wavelengths with debug
    grating_pitch_d_850 = 1/833
    grating_pitch_d_844 = 1/833
    grating_pitch_d_866 = 1/600
    littrow_angle_850nm = np.arcsin(850e-6 / (2 * grating_pitch_d_850)) * 180 / np.pi
    littrow_angle_844nm = np.arcsin(844e-6 / (2 * grating_pitch_d_844)) * 180 / np.pi  # ~50.1° (tuned from 850 nm for 422 nm SHG)
    littrow_angle_866nm = np.arcsin(866e-6 / (2 * grating_pitch_d_866)) * 180 / np.pi  # ~51.2° (SHG from 850 nm)

    # Group 3: 850 nm to 866 nm and 422 nm
    baseplate.place_element("ECDL_850nm", optomech.ECDL, x=gap, y=input_y_850nm - (input_y_850nm - 0.5 * layout.inch) + (2 * layout.inch), stage_thickness=1, stage_length=50,  angle=layout.cardinal['right'], littrow_angle=littrow_angle_850nm, cover_box=True)

    beam_850nm = baseplate.add_beam_path(x=gap, y=input_y_850nm - (input_y_850nm - 0.5 * layout.inch) + (2 * layout.inch), angle=layout.cardinal['right'])
    created_objects["Beam_850nm"] = beam_850nm

    mirror_ECDL_850nm = baseplate.place_element_along_beam("Mirror_ECDL_850nm", optomech.circular_mirror, beam_850nm, diameter=layout.inch/8, beam_index=0b1, distance=3.25 * layout.inch, angle=layout.turn['left-down']+24)
    created_objects["Mirror_ECDL_850nm"] = mirror_ECDL_850nm

    beamsplitter_850nm = baseplate.place_element_along_beam("BeamSplitter_850nm", optomech.cube_splitter, beam_850nm, beam_index=0b1, distance=3.5* layout.inch, angle=layout.cardinal['right'],mount_type=optomech.skate_mount)
    created_objects["BeamSplitter_850nm"] = beamsplitter_850nm

    tuner_866nm = baseplate.place_element_along_beam("Tuner_866nm", optomech.laser_mount_km100pm_LMR1_floating, beam_850nm, stage_thickness=6, stage_length=55, beam_index=0b10, distance=1 * layout.inch, angle=layout.cardinal['right'],drill=True, littrow_angle=littrow_angle_866nm)
    created_objects["Tuner_866nm"] = tuner_866nm

    mirror_866nm_1 = baseplate.place_element_along_beam("Mirror_866nm_1", optomech.circular_mirror, beam_850nm, diameter=layout.inch/8, beam_index=0b10, distance=3.25 * layout.inch, angle=layout.turn['right-down'],mount_type=optomech.skate_mount)
    created_objects["Mirror_866nm_1"] = mirror_866nm_1

    # Adding AOM from ca 40 example
    aom_866nm = baseplate.place_element_along_beam("AOM_866nm", optomech.isomet_1205c_on_km100pm, beam_850nm, beam_index=0b10, distance=50, angle=layout.cardinal['up'], forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    created_objects["AOM_866nm"] = aom_866nm
    baseplate.place_element_relative("Output Fiberport_beam_866nm", optomech.fiberport_mount_hca3, mirror_866nm_1, x_off= 0.0 * layout.inch, y_off=-4*layout.inch, angle=layout.cardinal['up'])

    tuner_844nm = baseplate.place_element_along_beam("Tuner_844nm", optomech.laser_mount_km100pm_LMR1_floating, beam_850nm, stage_thickness=6, stage_length=40, beam_index=0b11, distance=2 * layout.inch, angle=layout.cardinal['up'], drill=True, littrow_angle=littrow_angle_844nm)  # Note: Using 422nm angle as placeholder
    #created_objects["Tuner_844nm"] = tuner_844nm

    shg_844nm_to_422nm = baseplate.place_element_along_beam("SHG_844nm_to_422nm", optomech.cube_splitter, beam_850nm, beam_index=0b11, distance=2 * layout.inch,  angle=layout.cardinal['up'], mount_type=optomech.skate_mount)
    created_objects["SHG_844nm_to_422nm"] = shg_844nm_to_422nm

    # Add output fiberport, defined at the same coordinates as beam

    # Adding AOM from ca 40 example
    aom_422nm = baseplate.place_element_along_beam("AOM_422nm", optomech.isomet_1205c_on_km100pm, beam_850nm, beam_index=0b111, distance=50, angle=layout.cardinal['right'], forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    created_objects["AOM_422nm"] = aom_422nm

    baseplate.place_element("Output Fiberport_beam_422nm", optomech.fiberport_mount_hca3, x=gap, y=input_y_850nm-2+(1.40*3*layout.inch) - (input_y_850nm - 0.5 * layout.inch) + (2 * layout.inch), angle=layout.cardinal['right'])    

    master_doc.recompute()

    if not os.path.exists(script_dir):
        os.makedirs(script_dir)

    master_doc.recompute()
    master_doc.saveAs(os.path.join(script_dir, "Group3_850nm.fcstd"))
    if not is_headless:
        App.ActiveDocument.commitTransaction()
    else:
        App.closeDocument("Group3_850nm")

    print("Group 3 (850 nm) assembly completed successfully")
    return baseplate

if __name__ == "__main__":
    group1_baseplate_588nm()
    group2_baseplate_405nm()
    group3_baseplate_850nm()
    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")