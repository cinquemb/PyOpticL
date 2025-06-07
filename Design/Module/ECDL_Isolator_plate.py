from PyOpticL import layout, optomech
from datetime import datetime
import numpy as np
import Part
import FreeCAD as App

# Define default dimensions for standalone mode
base_dx = 6 * layout.inch
base_dy = 4 * layout.inch
base_dz = layout.inch
gap = layout.inch / 4
input_x = 0 * layout.inch
input_y = 0.5 * layout.inch
mount_holes = [[3, 0], [0, 2], [0, 4], [4, 2]]

# Calculating the littrow angle (for tracking purposes)
wavelength = 422e-6  # wavelength in mm
grating_pitch_d = 1/3600  # Lines per mm
littrow_angle = np.arcsin(wavelength / (2 * grating_pitch_d)) * 180 / np.pi
label = "               " + str(wavelength * 1e6) + "nm"

class ECDL_isolator_baseplate:
    type = "Part::FeaturePython"

    def __init__(self, obj, baseplate=None, x=0, y=0, angle=0, mirror=optomech.mirror_mount_km05):
        self.baseplate = baseplate  # Store reference, but don’t serialize it directly
        self.x = x
        self.y = y
        self.angle = angle
        self.mirror = mirror
        obj.Proxy = self
        if not hasattr(obj, "Shape"):
            obj.addProperty("Part::PropertyPartShape", "Shape", "Base", "Shape of the object")
        # Add serializable properties
        obj.addProperty("App::PropertyLength", "X").X = x
        obj.addProperty("App::PropertyLength", "Y").Y = y
        obj.addProperty("App::PropertyAngle", "Angle").Angle = angle

    def execute(self, obj):
        if self.baseplate is None:
            baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=self.x, y=self.y, angle=self.angle,
                                         gap=gap, mount_holes=[(1, 1), (5, 3), (0, 3), (4, 3), (4, 2)],
                                         y_offset=9, label=label)
            self.baseplate_obj = App.ActiveDocument.getObject(baseplate.active_baseplate)
            adjusted_input_y = base_dy - input_y
        else:
            baseplate = self.baseplate
            self.baseplate_obj = None
            adjusted_input_y = self.y + input_y

        beam = baseplate.add_beam_path(x=self.x + input_x, y=adjusted_input_y, angle=layout.cardinal['right'] + self.angle)

        baseplate.place_element_along_beam("Input_Mirror_1", optomech.circular_mirror, beam,
                                           beam_index=0b1, distance=1 * layout.inch, angle=layout.turn['right-down'],
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=True))
        baseplate.place_element_along_beam("Input_Mirror_2", optomech.circular_mirror, beam,
                                           beam_index=0b1, distance=2 * layout.inch, angle=layout.turn['down-right'],
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=True))
        baseplate.place_element_along_beam("Lens 1", optomech.cylindrical_lens, beam,
                                           beam_index=0b1, x=self.x + 2.5 * layout.inch, angle=layout.cardinal['right'],
                                           thickness=4, width=20, height=22, slots=True)
        baseplate.place_element_along_beam("Lens 2", optomech.cylindrical_lens, beam,
                                           beam_index=0b1, distance=35, angle=layout.cardinal['left'],
                                           thickness=5.1, width=15, height=17, slots=True)
        baseplate.place_element_along_beam("Optical_Isolator", optomech.isolator_405, beam,
                                           beam_index=0b1, distance=40, angle=layout.cardinal['left'])

        shapes = []
        for doc_obj in App.ActiveDocument.Objects:
            if hasattr(doc_obj, "BeamPath") and doc_obj.BeamPath == beam and hasattr(doc_obj, "Shape"):
                shapes.append(doc_obj.Shape)

        if shapes:
            obj.Shape = Part.makeCompound(shapes)
        else:
            obj.Shape = Part.makeBox(1, 1, 1)

    def __getstate__(self):
        """Return the state to be serialized, based on existing properties."""
        # Serialize only the instance attributes that are serializable
        state = {
            'x': self.x,
            'y': self.y,
            'angle': self.angle,
            'mirror_type': self.mirror.__class__.__name__  # Serialize mirror as its class name
        }
        return state

    def __setstate__(self, state):
        """Restore the state from serialized data."""
        self.x = state.get('x', 0)
        self.y = state.get('y', 0)
        self.angle = state.get('angle', 0)
        # Restore mirror based on class name (assuming optomech is available)
        mirror_type = state.get('mirror_type', 'mirror_mount_km05')
        if hasattr(optomech, mirror_type):
            self.mirror = getattr(optomech, mirror_type)
        else:
            self.mirror = optomech.mirror_mount_km05  # Default fallback
        # baseplate is regenerated in execute, so no need to restore it here
        self.baseplate = None

if __name__ == "__main__":
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "ECDL_Isolator_Baseplate")
    ECDL_isolator_baseplate(obj)
    App.ActiveDocument.recompute()
    layout.redraw()