from PyOpticL import layout, optomech
import Part
import FreeCAD as App

# Baseplate constants - Dimensions of the baseplate
base_dx = 3 * layout.inch
base_dy = 3 * layout.inch
base_dz = layout.inch
gap = layout.inch / 8

# Adding the mount holes to bolt the baseplate to the optical table
mount_holes = [(0, 0), (0, 2), (2, 0), (2, 2)]

class telescope:
    type = "Part::FeaturePython"

    def __init__(self, obj, x=0, y=0, angle=0):
        self.x = x
        self.y = y
        self.angle = angle
        obj.Proxy = self
        self.baseplate_obj = None
        # Ensure Shape property exists
        if not hasattr(obj, "Shape"):
            obj.addProperty("Part::PropertyPartShape", "Shape", "Base", "Shape of the object")

    def execute(self, obj):
        # Create the baseplate
        baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=self.x, y=self.y, angle=self.angle,
                                     gap=gap, mount_holes=mount_holes)
        
        # Store the FreeCAD object created by baseplate
        self.baseplate_obj = App.ActiveDocument.getObject(baseplate.active_baseplate)
        
        # Adding the beam to the baseplate
        beam = baseplate.add_beam_path(x=0, y=1.5 * layout.inch, angle=layout.cardinal['right'])

        offset = (2 * layout.inch - 45) / 2. + 0.5 * layout.inch

        # Add two lenses to make a telescope
        baseplate.place_element_along_beam("Lens 1", optomech.circular_lens, beam,
                                           beam_index=0b1, distance=offset, angle=180,
                                           mount_type=optomech.lens_holder_l05g)
        
        baseplate.place_element_along_beam("Lens 2", optomech.circular_lens, beam,
                                           beam_index=0b1, distance=45.0, angle=0,
                                           mount_type=optomech.lens_holder_l05g)
        
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
    obj = doc.addObject("Part::FeaturePython", "Telescope")
    telescope(obj)
    App.ActiveDocument.recompute()
    layout.redraw()