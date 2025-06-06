from math import *
from pathlib import Path

import FreeCAD as App
import Mesh
import numpy as np
import Part

from PyOpticL import layout

stl_path = str(Path(__file__).parent.resolve()) + "/PyOpticL/stl/"
drill_depth = 100
inch = 25.4

bolt_4_40 = {
    "clear_dia":0.120*inch,
    "tap_dia":0.089*inch,
    "head_dia":5.50,
    "head_dz":2.5 # TODO measure this
}

bolt_8_32 = {
    "clear_dia":0.172*inch,
    "tap_dia":0.136*inch,
    "head_dia":7,
    "head_dz":4.4
}

bolt_14_20 = {
    "clear_dia":0.260*inch,
    "tap_dia":0.201*inch,
    "head_dia":9.8,
    "head_dz":8,
    "washer_dia":9/16*inch
}

adapter_color = (0.6, 0.9, 0.6)
mount_color = (0.5, 0.5, 0.55)
glass_color = (0.5, 0.5, 0.8)
misc_color = (0.2, 0.2, 0.2)

# Custom components for PyOpticL to support ion trapping setup
# Updated with realistic properties, mounts, and STL imports based on provided parts

# Placeholder imports and constants (assumed from PyOpticL)
adapter_color = (0.5, 0.5, 0.5, 1.0)  # Gray color for components
glass_color = (0.8, 0.8, 1.0, 0.5)  # Light blue for optical components
misc_color = (0.3, 0.3, 0.3, 1.0)  # Dark gray for misc components
mount_color = (0.4, 0.4, 0.4, 1.0)  # Medium gray for mounts
bolt_8_32 = {'clear_dia': 4.2, 'head_dia': 8.0, 'head_dz': 3.0, 'tap_dia': 3.5}  # 8-32 bolt dimensions (mm)
bolt_14_20 = {'clear_dia': 5.0, 'head_dia': 9.0, 'head_dz': 3.5, 'tap_dia': 4.0, 'washer_dia': 10.0}  # 14-20 bolt dimensions (mm)
drill_depth = 10  # Default drilling depth (mm)
inch = 25.4  # Conversion factor for inches to mm
layout = type('layout', (), {'inch': inch, 'cardinal': {'right': 0, 'left': 180}, 'turn': {'up-right': 45}})

# Placeholder geometry functions (assumed from PyOpticL)
# Used to tranform an STL such that it's placement matches the optical center
def _import_stl(stl_name, rotate, translate, scale=1):
    mesh_cache = getattr(_import_stl, 'cache', {})
    if stl_name not in mesh_cache:
        mesh = Mesh.read(stl_path + stl_name)
        mat = App.Matrix()
        mat.scale(App.Vector(scale, scale, scale))
        mesh.transform(mat)
        mesh.rotate(*np.deg2rad(rotate))
        mesh.translate(*translate)
        mesh_cache[stl_name] = mesh
    return mesh_cache[stl_name]
_import_stl.cache = {}

def _bounding_box(obj, tol, fillet, x_tol=True, y_tol=True, z_tol=False, min_offset=(0, 0, 0), max_offset=(0, 0, 0), plate_off=0):
    if hasattr(obj, "Shape"):
        obj_body = obj.Shape.copy()
    elif hasattr(obj, "Mesh"):
        obj_body = obj.Mesh.copy()
    else:
        obj_body = obj
    obj_body.Placement = App.Placement()
    if hasattr(obj, "RelativePlacement"):
        obj_body.Placement = obj.RelativePlacement
        temp = obj
        while hasattr(temp, "ParentObject") and hasattr(temp.ParentObject, "RelativePlacement"):
            temp = temp.ParentObject
    global_bound = obj_body.BoundBox
    obj_body.Placement = App.Placement()
    bound = obj_body.BoundBox

    x_min, x_max = bound.XMin-tol*x_tol+min_offset[0], bound.XMax+tol*x_tol+max_offset[0]
    y_min, y_max = bound.YMin-tol*y_tol+min_offset[1], bound.YMax+tol*y_tol+max_offset[1]
    z_min = min(global_bound.ZMin-tol*z_tol+min_offset[2], -layout.inch/2+plate_off)-global_bound.ZMin+bound.ZMin
    z_max = max(global_bound.ZMax+tol*z_tol+max_offset[2], -layout.inch/2+plate_off)-global_bound.ZMax+bound.ZMax
    bound_part = _custom_box(dx=x_max-x_min, dy=y_max-y_min, dz=z_max-z_min,
                    x=x_min, y=y_min, z=z_min, dir=(1, 1, 1),
                    fillet=fillet, fillet_dir=(0, 0, 1))
    return bound_part

def _add_linked_object(obj, obj_name, obj_class, pos_offset=(0, 0, 0), rot_offset=(0, 0, 0), **args):
    if not hasattr(obj, "ChildObjects"):
        obj.addProperty("App::PropertyLinkListChild", "ChildObjects")
    if not any(child.Label == obj_name for child in obj.ChildObjects):
        new_obj = App.ActiveDocument.addObject(obj_class.type, obj_name)
        new_obj.addProperty("App::PropertyLinkHidden", "Baseplate").Baseplate = obj.Baseplate
        new_obj.Label = obj_name
        obj_class(new_obj, **args)
        new_obj.setEditorMode('Placement', 2)
        new_obj.addProperty("App::PropertyPlacement", "BasePlacement")
        obj.ChildObjects += [new_obj]
        new_obj.addProperty("App::PropertyLinkHidden", "ParentObject").ParentObject = obj
        new_obj.addProperty("App::PropertyPlacement", "RelativePlacement").RelativePlacement
        rotx = App.Rotation(App.Vector(1, 0, 0), rot_offset[0])
        roty = App.Rotation(App.Vector(0, 1, 0), rot_offset[1])
        rotz = App.Rotation(App.Vector(0, 0, 1), rot_offset[2])
        new_obj.RelativePlacement.Rotation = App.Rotation(rotz * roty * rotx)
        new_obj.RelativePlacement.Base = App.Vector(*pos_offset)
    return new_obj

def _drill_part(part, obj, drill_obj):
    if hasattr(drill_obj, "DrillPart"):
        drill = drill_obj.DrillPart.copy()
        drill.Placement = obj.BasePlacement.inverse().multiply(drill.Placement)
        part = part.cut(drill)
    if hasattr(drill_obj, "ChildObjects"):
        for sub in drill_obj.ChildObjects:
            part = _drill_part(part, obj, sub)
    return part

def _custom_box(dx, dy, dz, x, y, z, fillet=0, dir=(0,0,1), fillet_dir=None):
    if fillet_dir == None:
        fillet_dir = np.abs(dir)
    part = Part.makeBox(dx, dy, dz)
    if fillet != 0:
        for i in part.Edges:
            if i.tangentAt(i.FirstParameter) == App.Vector(*fillet_dir):
                part = part.makeFillet(fillet-1e-3, [i])
    part.translate(App.Vector(x-(1-dir[0])*dx/2, y-(1-dir[1])*dy/2, z-(1-dir[2])*dz/2))
    part = part.fuse(part)
    return part

def _fillet_all(part, fillet, dir=(0, 0, 1)):
    for i in part.Edges:
        if i.tangentAt(i.FirstParameter) == App.Vector(*dir):
            try:
                part = part.makeFillet(fillet-1e-3, [i])
            except:
                pass
    return part

def _custom_cylinder(dia, dz, x, y, z, head_dia=0, head_dz=0, dir=(0, 0, -1), countersink=False):
    part = Part.makeCylinder(dia/2, dz, App.Vector(0, 0, 0), App.Vector(*dir))
    if head_dia != 0 and head_dz != 0:
        if countersink:
            part = part.fuse(Part.makeCone(head_dia/2, dia/2, head_dz, App.Vector(0, 0, 0), App.Vector(*dir)))
        else:
            part = part.fuse(Part.makeCylinder(head_dia/2, head_dz, App.Vector(0, 0, 0), App.Vector(*dir)))
    part.translate(App.Vector(x, y, z))
    part = part.fuse(part)
    return part.removeSplitter()

class ViewProvider:
    def __init__(self, view_obj):
        self.view_obj = view_obj

class ion_trap:
    '''
    A 32x32 surface-electrode ion trap (gold-on-alumina), 5 µm electrode spacing
    Dimensions: 10x10x2 mm chip, with surface adapter for mounting
    Sub-Parts: surface_adapter_wide (adapter_args)
    '''
    type = 'Part::FeaturePython'
    def __init__(self, obj, drill=True, width=10, height=10, thickness=2, adapter_args=dict()):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'Width').Width = width
        obj.addProperty('App::PropertyLength', 'Height').Height = height
        obj.addProperty('App::PropertyLength', 'Thickness').Thickness = thickness
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = adapter_color
        self.mount_bolt = bolt_8_32
        self.mount_dz = -obj.Baseplate.OpticsDz.Value if hasattr(obj, 'Baseplate') else -2

        adapter_args.setdefault("mount_hole_dy", 15)
        adapter_args.setdefault("adapter_height", 5)
        _add_linked_object(obj, "Surface Adapter", surface_adapter_wide, pos_offset=(0, 0, -thickness), **adapter_args)

    def execute(self, obj):
        print("Starting ion_trap execute")
        # Base chip
        part = _custom_box(dx=obj.Width.Value, dy=obj.Height.Value, dz=obj.Thickness.Value,
                           x=0, y=0, z=self.mount_dz, dir=(0, 0, 0))
        print("ion_trap: Base chip created")
        # Simulate 32x32 electrode grid (1,024 electrodes) with a single compound cutout
        electrode_spacing = 0.005  # 5 µm in mm
        electrode_width = electrode_spacing * 0.5
        cuts = []
        for i in range(32):
            for j in range(32):
                electrode_x = (i - 15.5) * electrode_spacing
                electrode_y = (j - 15.5) * electrode_spacing
                cuts.append(_custom_box(dx=electrode_width, dy=electrode_width, dz=obj.Thickness.Value / 2,
                                        x=electrode_x, y=electrode_y, z=self.mount_dz + obj.Thickness.Value / 2))
        part = part.cut(Part.Compound(cuts))
        print("ion_trap: Electrode cuts completed")
        # Mounting hole
        part = part.cut(_custom_cylinder(dia=self.mount_bolt['clear_dia'], dz=obj.Thickness.Value,
                                         head_dia=self.mount_bolt['head_dia'], head_dz=self.mount_bolt['head_dz'],
                                         x=0, y=0, z=obj.Thickness.Value + self.mount_dz))
        print("ion_trap: Mounting hole cut")
        obj.Shape = part
        print("ion_trap: Shape assigned")

        # Drill part for baseplate
        part = _bounding_box(obj, 2, 2, min_offset=(0, 0, -5))
        for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            part = part.fuse(_custom_cylinder(dia=self.mount_bolt['tap_dia'], dz=drill_depth,
                                              x=x * (obj.Width.Value / 2 - 1), y=y * (obj.Height.Value / 2 - 1), z=self.mount_dz))
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("ion_trap: Drill part completed")

class pmt_array:
    '''
    A 16-PMT array (Hamamatsu R7600U) for fluorescence detection
    Dimensions: 50x20x10 mm for a 4x4 grid of PMTs, with surface adapter
    Sub-Parts: surface_adapter_wide (adapter_args)
    '''
    type = 'Part::FeaturePython'
    def __init__(self, obj, drill=True, length=50, width=20, height=10, adapter_args=dict()):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'Length').Length = length
        obj.addProperty('App::PropertyLength', 'Width').Width = width
        obj.addProperty('App::PropertyLength', 'Height').Height = height
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = misc_color
        self.mount_bolt = bolt_8_32
        self.mount_dz = -obj.Baseplate.OpticsDz.Value if hasattr(obj, 'Baseplate') else -2

        adapter_args.setdefault("mount_hole_dy", 40)
        adapter_args.setdefault("adapter_height", 8)
        _add_linked_object(obj, "Surface Adapter", surface_adapter_wide, pos_offset=(0, 0, -height), **adapter_args)

    def execute(self, obj):
        print("Starting pmt_array execute")
        # Base housing
        part = _custom_box(dx=obj.Length.Value, dy=obj.Width.Value, dz=obj.Height.Value,
                           x=0, y=0, z=self.mount_dz, dir=(0, 0, 0))
        print("pmt_array: Base housing created")
        # 4x4 grid of PMT windows (16 PMTs, each ~10x10 mm)
        pmt_size = 10
        for i in range(4):
            for j in range(4):
                pmt_x = (i - 1.5) * pmt_size
                pmt_y = (j - 1.5) * pmt_size
                part = part.cut(_custom_box(dx=pmt_size * 0.8, dy=pmt_size * 0.8, dz=obj.Height.Value / 2,
                                            x=pmt_x, y=pmt_y, z=self.mount_dz + obj.Height.Value / 2))
        print("pmt_array: PMT windows cut")
        # Mounting hole
        part = part.cut(_custom_cylinder(dia=self.mount_bolt['clear_dia'], dz=obj.Height.Value,
                                         head_dia=self.mount_bolt['head_dia'], head_dz=self.mount_bolt['head_dz'],
                                         x=0, y=0, z=obj.Height.Value + self.mount_dz))
        print("pmt_array: Mounting hole cut")
        obj.Shape = part
        print("pmt_array: Shape assigned")

        # Drill part for baseplate
        part = _bounding_box(obj, 2, 2, min_offset=(0, 0, -5))
        for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            part = part.fuse(_custom_cylinder(dia=self.mount_bolt['tap_dia'], dz=drill_depth,
                                              x=x * (obj.Length.Value / 2 - 5), y=y * (obj.Width.Value / 2 - 2), z=self.mount_dz))
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("pmt_array: Drill part completed")

class fpga_board:
    '''
    A Xilinx Spartan-6 FPGA board (50 MHz clock) for control
    Dimensions: 60x40x5 mm, with surface adapter for mounting
    Sub-Parts: surface_adapter_wide (adapter_args)
    '''
    type = 'Part::FeaturePython'
    def __init__(self, obj, drill=True, length=60, width=40, height=5, adapter_args=dict()):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'Length').Length = length
        obj.addProperty('App::PropertyLength', 'Width').Width = width
        obj.addProperty('App::PropertyLength', 'Height').Height = height
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = misc_color
        self.mount_bolt = bolt_8_32
        self.mount_dz = -obj.Baseplate.OpticsDz.Value if hasattr(obj, 'Baseplate') else -2

        adapter_args.setdefault("mount_hole_dy", 50)
        adapter_args.setdefault("adapter_height", 8)
        _add_linked_object(obj, "Surface Adapter", surface_adapter_wide, pos_offset=(0, 0, -height), **adapter_args)

    def execute(self, obj):
        print("Starting fpga_board execute")
        # Base board
        part = _custom_box(dx=obj.Length.Value, dy=obj.Width.Value, dz=obj.Height.Value,
                           x=0, y=0, z=self.mount_dz, dir=(0, 0, 0))
        print("fpga_board: Base board created")
        # Simulate connectors on one edge
        part = part.cut(_custom_box(dx=5, dy=obj.Width.Value * 0.8, dz=obj.Height.Value / 2,
                                    x=obj.Length.Value / 2 - 2.5, y=0, z=self.mount_dz + obj.Height.Value / 2))
        print("fpga_board: Connectors cut")
        # Mounting hole
        part = part.cut(_custom_cylinder(dia=self.mount_bolt['clear_dia'], dz=obj.Height.Value,
                                         head_dia=self.mount_bolt['head_dia'], head_dz=self.mount_bolt['head_dz'],
                                         x=0, y=0, z=obj.Height.Value + self.mount_dz))
        print("fpga_board: Mounting hole cut")
        obj.Shape = part
        print("fpga_board: Shape assigned")

        # Drill part for baseplate
        part = _bounding_box(obj, 2, 2, min_offset=(0, 0, -5))
        for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            part = part.fuse(_custom_cylinder(dia=self.mount_bolt['tap_dia'], dz=drill_depth,
                                              x=x * (obj.Length.Value / 2 - 5), y=y * (obj.Width.Value / 2 - 5), z=self.mount_dz))
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("fpga_board: Drill part completed")

class mass_selective_axial_ejection_cavity:
    '''
    A mass selective axial ejection cavity for ion trap mass spectrometry
    Dimensions: 40x20x15 mm, with quadrupole structure and surface adapter
    Sub-Parts: surface_adapter_wide (adapter_args)
    '''
    type = 'Part::FeaturePython'
    def __init__(self, obj, drill=True, length=40, width=20, height=15, adapter_args=dict()):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'Length').Length = length
        obj.addProperty('App::PropertyLength', 'Width').Width = width
        obj.addProperty('App::PropertyLength', 'Height').Height = height
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = adapter_color
        self.mount_bolt = bolt_8_32
        self.mount_dz = -obj.Baseplate.OpticsDz.Value if hasattr(obj, 'Baseplate') else -2

        adapter_args.setdefault("mount_hole_dy", 30)
        adapter_args.setdefault("adapter_height", 8)
        _add_linked_object(obj, "Surface Adapter", surface_adapter_wide, pos_offset=(0, 0, -height), **adapter_args)

    def execute(self, obj):
        print("Starting mass_selective_axial_ejection_cavity execute")
        # Base housing
        part = _custom_box(dx=obj.Length.Value, dy=obj.Width.Value, dz=obj.Height.Value,
                           x=0, y=0, z=self.mount_dz, dir=(0, 0, 0))
        print("mass_selective_axial_ejection_cavity: Base housing created")
        # Quadrupole structure: four cylindrical electrodes (simplified as cutouts)
        electrode_dia = 5
        for x, y in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            part = part.cut(_custom_cylinder(dia=electrode_dia, dz=obj.Length.Value,
                                             x=x * (obj.Width.Value / 2 - electrode_dia / 2),
                                             y=y * (obj.Height.Value / 2 - electrode_dia / 2),
                                             z=self.mount_dz, dir=(1, 0, 0)))
        print("mass_selective_axial_ejection_cavity: Quadrupole electrodes cut")
        # Axial ejection path
        part = part.cut(_custom_cylinder(dia=electrode_dia / 2, dz=obj.Length.Value,
                                         x=0, y=0, z=self.mount_dz, dir=(1, 0, 0)))
        print("mass_selective_axial_ejection_cavity: Axial ejection path cut")
        # Mounting hole
        part = part.cut(_custom_cylinder(dia=self.mount_bolt['clear_dia'], dz=obj.Height.Value,
                                         head_dia=self.mount_bolt['head_dia'], head_dz=self.mount_bolt['head_dz'],
                                         x=0, y=0, z=obj.Height.Value + self.mount_dz))
        print("mass_selective_axial_ejection_cavity: Mounting hole cut")
        obj.Shape = part
        print("mass_selective_axial_ejection_cavity: Shape assigned")

        # Drill part for baseplate
        part = _bounding_box(obj, 2, 2, min_offset=(0, 0, -5))
        for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            part = part.fuse(_custom_cylinder(dia=self.mount_bolt['tap_dia'], dz=drill_depth,
                                              x=x * (obj.Length.Value / 2 - 5), y=y * (obj.Width.Value / 2 - 2), z=self.mount_dz))
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("mass_selective_axial_ejection_cavity: Drill part completed")

class stepper_motor:
    '''
    A Thorlabs Z812 stepper motor for laser tuning, based on rotation_stage_rsp05_vertical
    Dimensions: 20x20x30 mm, with realistic mount and bolt pattern
    '''
    type = 'Mesh::FeaturePython'
    def __init__(self, obj, drill=True, width=20, height=20, length=30):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'Width').Width = width
        obj.addProperty('App::PropertyLength', 'Height').Height = height
        obj.addProperty('App::PropertyLength', 'Length').Length = length
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = mount_color
        self.mount_bolt = bolt_8_32
        self.mount_dz = -obj.Baseplate.OpticsDz.Value if hasattr(obj, 'Baseplate') else -2

    def execute(self, obj):
        print("Starting stepper_motor execute")
        # Use rotation stage model as a proxy
        mesh = _import_stl("RSP05-Step.stl", (90, 0, 90), (2.084, -1.148, 0.498))
        print("stepper_motor: STL imported")
        mesh.Placement = obj.Mesh.Placement
        obj.Mesh = mesh
        print("stepper_motor: Mesh assigned")

        # Realistic drill part with pinholes and washer, similar to lens_mount_sm1tc
        part = _custom_box(dx=obj.Width.Value, dy=obj.Height.Value, dz=5,
                           x=0, y=0, z=self.mount_dz - 5, dir=(0, 0, -1))
        print("stepper_motor: Drill base created")
        part = part.fuse(_custom_cylinder(dia=self.mount_bolt['clear_dia'] + 0.35, dz=obj.Length.Value + 5,
                                          head_dia=self.mount_bolt['clear_dia'] + 0.35, head_dz=obj.Length.Value / 2,
                                          x=0, y=0, z=self.mount_dz - 5))
        print("stepper_motor: Central hole fused")
        for i in [-1, 1]:
            part = part.fuse(_custom_cylinder(dia=2, dz=2.2,
                                              x=i * 5, y=0, z=self.mount_dz - 5))
        print("stepper_motor: Pinholes fused")
        # Square washer for stability
        part = part.fuse(_custom_box(dx=0.55 * inch, dy=0.55 * inch, dz=5,
                                     x=0, y=0, z=self.mount_dz - 10, dir=(0, 0, -1)))
        print("stepper_motor: Washer fused")
        for j in [1, -1]:
            for k in [1, -1]:
                part = part.fuse(_custom_cylinder(dia=self.mount_bolt['tap_dia'] * 2, dz=drill_depth,
                                                  x=j * 0.25 * inch, y=k * 0.25 * inch, z=self.mount_dz - 10))
        print("stepper_motor: Mounting holes fused")
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("stepper_motor: Drill part completed")

class aom:
    '''
    A G&H 80 MHz AOM for frequency modulation, based on isomet_1205c_on_km100pm
    Dimensions: 25x15x10 mm, with realistic mount and diffraction properties
    Sub-Parts: surface_adapter_wide (adapter_args)
    '''
    type = 'Mesh::FeaturePython'
    def __init__(self, obj, drill=True, length=25, width=15, height=10, adapter_args=dict()):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'Length').Length = length
        obj.addProperty('App::PropertyLength', 'Width').Width = width
        obj.addProperty('App::PropertyLength', 'Height').Height = height
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = misc_color
        self.mount_bolt = bolt_8_32
        self.mount_dz = -obj.Baseplate.OpticsDz.Value if hasattr(obj, 'Baseplate') else -2
        self.transmission = True
        self.max_angle = 10
        self.max_width = 5
        self.diffraction_angle = 0.01  # Small diffraction angle for 80 MHz AOM
        self.diffraction_dir = (1, 1)  # Forward and backward diffraction to the right

        adapter_args.setdefault("mount_hole_dy", 20)
        adapter_args.setdefault("adapter_height", 5)
        _add_linked_object(obj, "Surface Adapter", surface_adapter_wide, pos_offset=(0, 0, -height), **adapter_args)

    def execute(self, obj):
        print("Starting aom execute")
        # Use Isomet 1205C model as a proxy
        mesh = _import_stl("isomet_1205c.stl", (0, 0, 90), (0, 0, 0))
        print("aom: STL imported")
        mesh.Placement = obj.Mesh.Placement
        obj.Mesh = mesh
        print("aom: Mesh assigned")

        # Realistic drill part with pinholes and washer
        part = _custom_box(dx=obj.Length.Value, dy=obj.Width.Value, dz=5,
                           x=0, y=0, z=self.mount_dz - 5, dir=(0, 0, -1))
        print("aom: Drill base created")
        part = part.fuse(_custom_cylinder(dia=self.mount_bolt['clear_dia'] + 0.35, dz=obj.Height.Value + 5,
                                          head_dia=self.mount_bolt['clear_dia'] + 0.35, head_dz=obj.Height.Value / 2,
                                          x=0, y=0, z=self.mount_dz - 5))
        print("aom: Central hole fused")
        for i in [-1, 1]:
            part = part.fuse(_custom_cylinder(dia=2, dz=2.2,
                                              x=i * 5, y=0, z=self.mount_dz - 5))
        print("aom: Pinholes fused")
        # Square washer for stability
        part = part.fuse(_custom_box(dx=0.55 * inch, dy=0.55 * inch, dz=5,
                                     x=0, y=0, z=self.mount_dz - 10, dir=(0, 0, -1)))
        print("aom: Washer fused")
        for j in [1, -1]:
            for k in [1, -1]:
                part = part.fuse(_custom_cylinder(dia=self.mount_bolt['tap_dia'] * 2, dz=drill_depth,
                                                  x=j * 0.25 * inch, y=k * 0.25 * inch, z=self.mount_dz - 10))
        print("aom: Mounting holes fused")
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("aom: Drill part completed")

class ion_injection_port:
    '''
    An ICP-MS ion injection port, aligned with trap's axial direction
    Dimensions: 15x15x20 mm, with a cylindrical ion optic path and periscope-style mount
    Sub-Parts: periscope mount (custom)
    '''
    type = 'Part::FeaturePython'
    def __init__(self, obj, drill=True, width=15, height=15, length=20):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'Width').Width = width
        obj.addProperty('App::PropertyLength', 'Height').Height = height
        obj.addProperty('App::PropertyLength', 'Length').Length = length
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = adapter_color
        self.mount_bolt = bolt_8_32
        self.mount_dz = -obj.Baseplate.OpticsDz.Value if hasattr(obj, 'Baseplate') else -2

        # Periscope-style mount for axial alignment
        _add_linked_object(obj, "Periscope Mount", periscope, pos_offset=(0, 0, -height), lower_dz=10, upper_dz=20)

    def execute(self, obj):
        print("Starting ion_injection_port execute")
        # Base housing
        part = _custom_box(dx=obj.Length.Value, dy=obj.Width.Value, dz=obj.Height.Value,
                           x=0, y=0, z=self.mount_dz, dir=(0, 0, 0))
        print("ion_injection_port: Base housing created")
        # Cylindrical ion optic path
        part = part.cut(_custom_cylinder(dia=5, dz=obj.Length.Value,
                                         x=0, y=0, z=self.mount_dz + obj.Height.Value / 2, dir=(1, 0, 0)))
        print("ion_injection_port: Ion optic path cut")
        # Mounting hole
        part = part.cut(_custom_cylinder(dia=self.mount_bolt['clear_dia'], dz=obj.Height.Value,
                                         head_dia=self.mount_bolt['head_dia'], head_dz=self.mount_bolt['head_dz'],
                                         x=0, y=0, z=obj.Height.Value + self.mount_dz))
        print("ion_injection_port: Mounting hole cut")
        obj.Shape = part
        print("ion_injection_port: Shape assigned")

        # Drill part for baseplate
        part = _bounding_box(obj, 2, 2, min_offset=(0, 0, -5))
        for x, y in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            part = part.fuse(_custom_cylinder(dia=self.mount_bolt['tap_dia'], dz=drill_depth,
                                              x=x * (obj.Width.Value / 2 - 2), y=y * (obj.Height.Value / 2 - 2), z=self.mount_dz))
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("ion_injection_port: Drill part completed")

# Placeholder classes for sub-parts (assumed to be defined elsewhere, but included for completeness)
class surface_adapter_wide:
    type = 'Part::FeaturePython'
    def __init__(self, obj, drill=True, mount_hole_dy=20, adapter_height=8, outer_thickness=2):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'MountHoleDistance').MountHoleDistance = mount_hole_dy
        obj.addProperty('App::PropertyLength', 'AdapterHeight').AdapterHeight = adapter_height
        obj.addProperty('App::PropertyLength', 'OuterThickness').OuterThickness = outer_thickness
        obj.addProperty('Part::PropertyPartShape', 'DrillPart')

        obj.ViewObject.ShapeColor = adapter_color
        self.drill_tolerance = 1

    def execute(self, obj):
        print("Starting surface_adapter_wide execute")
        dx = bolt_8_32['head_dia'] + obj.OuterThickness.Value * 2
        dy = dx + obj.MountHoleDistance.Value
        dz = obj.AdapterHeight.Value

        part = _custom_box(dx=dx, dy=dy, dz=dz,
                           x=0, y=0, z=0, dir=(0, 0, -1),
                           fillet=5)
        print("surface_adapter_wide: Base created")
        part = part.cut(_custom_cylinder(dia=bolt_8_32['clear_dia'], dz=dz,
                                         head_dia=bolt_8_32['head_dia'], head_dz=bolt_8_32['head_dz'],
                                         x=0, y=0, z=-dz, dir=(0, 0, 1)))
        print("surface_adapter_wide: Central hole cut")
        for i in [-1, 1]:
            part = part.cut(_custom_cylinder(dia=bolt_8_32['clear_dia'], dz=dz,
                                             head_dia=bolt_8_32['head_dia'], head_dz=bolt_8_32['head_dz'],
                                             x=0, y=i * obj.MountHoleDistance.Value / 2, z=0))
        print("surface_adapter_wide: Mounting holes cut")
        obj.Shape = part
        print("surface_adapter_wide: Shape assigned")

        part = _bounding_box(obj, self.drill_tolerance, 6)
        for i in [-1, 1]:
            part = part.fuse(_custom_cylinder(dia=bolt_8_32['tap_dia'], dz=drill_depth,
                                              x=0, y=i * obj.MountHoleDistance.Value / 2, z=0))
        part.Placement = obj.Placement
        obj.DrillPart = part
        print("surface_adapter_wide: Drill part completed")

class periscope:
    type = 'Part::FeaturePython'
    def __init__(self, obj, drill=True, lower_dz=1.5 * inch, upper_dz=3 * inch, invert=True, mirror_args=dict()):
        obj.Proxy = self
        ViewProvider(obj.ViewObject)

        obj.addProperty('App::PropertyBool', 'Drill').Drill = drill
        obj.addProperty('App::PropertyLength', 'LowerHeight').LowerHeight = lower_dz
        obj.addProperty('App::PropertyLength', 'UpperHeight').UpperHeight = upper_dz
        obj.addProperty('App::PropertyBool', 'Invert').Invert = invert

        obj.ViewObject.ShapeColor = adapter_color
        self.z_off = 0

    def execute(self, obj):
        print("Starting periscope execute")
        width = 2 * inch
        fillet = 15
        part = _custom_box(dx=70, dy=width, dz=obj.UpperHeight.Value + 20,
                           x=0, y=0, z=0)
        print("periscope: Base created")
        for i in [-1, 1]:
            part = part.cut(_custom_box(dx=fillet * 2 + 4, dy=width, dz=obj.UpperHeight.Value + 20,
                                        x=i * (35 + fillet), y=0, z=20, fillet=15,
                                        dir=(-i, 0, 1), fillet_dir=(0, 1, 0)))
            for y in [-inch / 2, inch / 2]:
                part = part.cut(_custom_cylinder(dia=bolt_14_20['clear_dia'] + 0.5, dz=inch + 5,
                                                 head_dia=bolt_14_20['head_dia'] + 0.5, head_dz=10,
                                                 x=i * inch, y=y, z=25, dir=(0, 0, -1)))
        print("periscope: Cuts and holes created")
        part.translate(App.Vector(0, (-1) ** obj.Invert * (width / 2 + inch / 2), self.z_off))
        part = part.fuse(part)
        obj.Shape = part
        print("periscope: Shape assigned")