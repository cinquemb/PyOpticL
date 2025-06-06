from PyOpticL import layout, optomech
from datetime import datetime
import numpy as np
import Part
import FreeCAD as App

## Calculating the littrow angle for the ECDL (for tracking purposes)
wavelength = 422e-6  # wavelength in mm
grating_pitch_d = 1/3600  # Lines per mm
littrow_angle = np.arcsin(wavelength / (2 * grating_pitch_d)) * 180 / np.pi
label = "               " + str(wavelength * 1e6) + "nm"

# Define the dimensions of the baseplate
base_dx = 6 * layout.inch 
base_dy = 4 * layout.inch 
base_dz = layout.inch
gap = layout.inch / 4

# Define the position from where the beam will enter into the baseplate
input_x = 0 * layout.inch 
input_y = 0.5 * layout.inch
input_y = base_dy - input_y

# Adding mount holes to bolt the baseplate to the optical table
mount_holes = [[3, 0], [0, 2], [0, 4], [4, 2]]

class ECDL_isolator_baseplate:
    type = "Part::FeaturePython"

    def __init__(self, obj, x=0, y=0, angle=0, mirror=optomech.mirror_mount_km05):
        self.x = x
        self.y = y
        self.angle = angle
        self.mirror = mirror
        obj.Proxy = self
        self.baseplate_obj = None
        # Ensure Shape property exists
        if not hasattr(obj, "Shape"):
            obj.addProperty("Part::PropertyPartShape", "Shape", "Base", "Shape of the object")

    def execute(self, obj):
        # Create the baseplate
        baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=self.x, y=self.y, angle=self.angle,
                                     gap=gap, mount_holes=[(1, 1), (5, 3), (0, 3), (4, 3), (4, 2)],
                                     y_offset=9, label=label)
        
        # Store the FreeCAD object created by baseplate
        self.baseplate_obj = App.ActiveDocument.getObject(baseplate.active_baseplate)
        
        # Adding the beam to baseplate
        beam = baseplate.add_beam_path(x=input_x, y=input_y, angle=layout.cardinal['right'])

        # Adding the first mirror
        baseplate.place_element_along_beam("Input_Mirror_1", optomech.circular_mirror, beam,
                                           beam_index=0b1, distance=1 * layout.inch, angle=layout.turn['right-down'],
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=True))
        
        # Adding second mirror to ensure enough degrees of freedom
        baseplate.place_element_along_beam("Input_Mirror_2", optomech.circular_mirror, beam,
                                           beam_index=0b1, distance=2 * layout.inch, angle=layout.turn['down-right'],
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=True))
        
        # Adding the cylindrical lens pair to make the beam more circular 
        baseplate.place_element_along_beam("Lens 1", optomech.cylindrical_lens, beam,
                                           beam_index=0b1, x=2.5 * layout.inch, angle=layout.cardinal['right'],
                                           thickness=4, width=20, height=22, slots=True)
        baseplate.place_element_along_beam("Lens 2", optomech.cylindrical_lens, beam,
                                           beam_index=0b1, distance=35, angle=layout.cardinal['left'],  
                                           thickness=5.1, width=15, height=17, slots=True)
        
        # Adding the isolator to prevent unwanted feedback
        baseplate.place_element_along_beam("Optical_Isolator", optomech.isolator_405, beam,
                                           beam_index=0b1, distance=40, angle=layout.cardinal['left'])
        
        # Collect shapes: baseplate + all placed elements
        shapes = []
        if hasattr(self.baseplate_obj, "Shape"):
            shapes.append(self.baseplate_obj.Shape)
        for child in self.baseplate_obj.ChildObjects:
            if hasattr(child, "Shape"):
                shapes.append(child.Shape)
        for doc_obj in App.ActiveDocument.Objects:
            if hasattr(doc_obj, "Baseplate") and doc_obj.Baseplate == self.baseplate_obj and hasattr(doc_obj, "Shape"):
                shapes.append(doc_obj.Shape)

        # Create a compound shape
        if shapes:
            if not hasattr(obj, "Shape"):
                obj.addProperty("Part::PropertyPartShape", "Shape", "Base", "Shape of the object")
            obj.Shape = Part.makeCompound(shapes)
        else:
            # Fallback: create a basic box
            if not hasattr(obj, "Shape"):
                obj.addProperty("Part::PropertyPartShape", "Shape", "Base", "Shape of the object")
            obj.Shape = Part.makeBox(base_dx, base_dy, base_dz)

if __name__ == "__main__":
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "ECDL_Isolator_Baseplate")
    ECDL_isolator_baseplate(obj)
    App.ActiveDocument.recompute()
    layout.redraw()