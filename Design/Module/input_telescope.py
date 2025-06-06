from PyOpticL import layout, optomech
import Part
import FreeCAD as App

# Default dimensions for standalone mode
base_dx = 3 * layout.inch
base_dy = 3 * layout.inch
base_dz = layout.inch
gap = layout.inch / 8
mount_holes = [(0, 0), (0, 2), (2, 0), (2, 2)]

class telescope:
    type = "Part::FeaturePython"

    def __init__(self, obj, baseplate=None, x=0, y=0, angle=0):
        self.baseplate = baseplate
        self.x = x
        self.y = y
        self.angle = angle
        obj.Proxy = self
        # Add serializable properties
        obj.addProperty("App::PropertyLength", "X").X = x
        obj.addProperty("App::PropertyLength", "Y").Y = y
        obj.addProperty("App::PropertyAngle", "Angle").Angle = angle
        if not hasattr(obj, "Shape"):
            obj.addProperty("Part::PropertyPartShape", "Shape", "Base", "Shape of the object")

    def execute(self, obj):
        # Use provided baseplate or create a new one
        if self.baseplate is None:
            baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=obj.X.Value, y=obj.Y.Value, angle=obj.Angle.Value,
                                         gap=gap, mount_holes=mount_holes)
            self.baseplate_obj = App.ActiveDocument.getObject(baseplate.active_baseplate)
            beam_y = 1.5 * layout.inch
        else:
            baseplate = self.baseplate
            self.baseplate_obj = None
            beam_y = obj.Y.Value + 1.5 * layout.inch

        # Add the beam path
        beam = baseplate.add_beam_path(x=obj.X.Value, y=beam_y, angle=layout.cardinal['right'] + obj.Angle.Value)

        offset = (2 * layout.inch - 45) / 2. + 0.5 * layout.inch

        # Add lenses
        baseplate.place_element_along_beam("Lens 1", optomech.circular_lens, beam,
                                           beam_index=0b1, distance=offset, angle=180,
                                           mount_type=optomech.lens_holder_l05g)
        baseplate.place_element_along_beam("Lens 2", optomech.circular_lens, beam,
                                           beam_index=0b1, distance=45.0, angle=0,
                                           mount_type=optomech.lens_holder_l05g)

        # Collect shapes for this component only
        shapes = []
        for doc_obj in App.ActiveDocument.Objects:
            if hasattr(doc_obj, "BeamPath") and doc_obj.BeamPath == beam and hasattr(doc_obj, "Shape"):
                shapes.append(doc_obj.Shape)

        if shapes:
            obj.Shape = Part.makeCompound(shapes)
        else:
            obj.Shape = Part.makeBox(1, 1, 1)

if __name__ == "__main__":
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "Telescope")
    telescope(obj)
    App.ActiveDocument.recompute()
    layout.redraw()