from PyOpticL import layout, optomech
from datetime import datetime
import Part
import FreeCAD as App

class doublepass_f50:
    type = "Part::FeaturePython"

    def __init__(self, obj, x=0, y=0, angle=0, mirror=optomech.mirror_mount_k05s2, x_split=False, thumbscrews=True):
        self.x = x
        self.y = y
        self.angle = angle
        self.mirror = mirror
        self.x_split = x_split
        self.thumbscrews = thumbscrews
        obj.Proxy = self
        self.baseplate_obj = None
        # Ensure Shape property exists
        if not hasattr(obj, "Shape"):
            obj.addProperty("Part::PropertyPartShape", "Shape", "Base", "Shape of the object")

    def execute(self, obj):
        # Adding name and date to keep track of the updates
        name = "Doublepass"
        date_time = datetime.now().strftime("%m/%d/%Y")
        label = ""  # name + " " + date_time

        # Dimensions of the baseplate 
        base_dx = 9.5 * layout.inch
        base_dy = 5 * layout.inch
        base_dz = layout.inch
        gap = layout.inch / 8

        input_x = 6.5 * layout.inch  # Grid-aligned position

        mount_holes = [(0, 0), (8, 3)]
        extra_mount_holes = [(2, 0), (1, 2), (4, 0), (4, 4), (6, 2)]

        # Define the baseplate
        baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=self.x, y=self.y, angle=self.angle,
                                     gap=gap, mount_holes=mount_holes + extra_mount_holes,
                                     name=name, label=label, x_splits=[0 * layout.inch] * self.x_split)
        
        # Store the FreeCAD object created by baseplate
        self.baseplate_obj = App.ActiveDocument.getObject(baseplate.active_baseplate)
        
        # Adding the beam to the baseplate
        beam = baseplate.add_beam_path(input_x, gap, layout.cardinal['up'])

        # Adding input fiberport to send the beam into the baseplate
        baseplate.place_element("Input Fiberport", optomech.fiberport_mount_hca3, x=165.10, y=2.6,
                                angle=layout.cardinal['up'])
        
        # Adding two mirrors to give the beam enough degrees of freedom
        baseplate.place_element_along_beam("Input Mirror 1", optomech.circular_mirror, beam,
                                           beam_index=0b1, distance=17, angle=layout.turn['up-right'],
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=self.thumbscrews))
        
        baseplate.place_element_along_beam("Input Mirror 2", optomech.circular_mirror, beam,
                                           beam_index=0b1, distance=layout.inch, angle=layout.turn['right-up'],
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=self.thumbscrews))
        
        # Adding a waveplate to control the polarization
        baseplate.place_element_along_beam("Half waveplate", optomech.waveplate, beam,
                                           beam_index=0b1, distance=55, angle=layout.cardinal['up'],
                                           mount_type=optomech.rotation_stage_rsp05)
        
        # Adding beam splitter to divide the beam
        baseplate.place_element_along_beam("Beam Splitter", optomech.cube_splitter, beam,
                                           beam_index=0b1, distance=28, angle=layout.cardinal['up'],
                                           mount_type=optomech.skate_mount)
        
        # Adding AOM
        baseplate.place_element_along_beam("AOM", optomech.isomet_1205c_on_km100pm, beam,
                                           beam_index=0b11, distance=55, angle=layout.cardinal['left'],
                                           forward_direction=-1, backward_direction=1)
        
        # Adding lens to make collimated beam
        lens = baseplate.place_element_along_beam("Lens f50mm AB coat", optomech.circular_lens, beam,
                                                  beam_index=0b110, distance=50, angle=layout.cardinal['right'],
                                                  focal_length=50, part_number='LA1213-AB', mount_type=optomech.lens_holder_l05g)
        
        # Adding quarter waveplate to control the polarization
        baseplate.place_element_along_beam("Quarter waveplate", optomech.waveplate, beam,
                                           beam_index=0b110, distance=24, angle=layout.cardinal['left'],
                                           mount_type=optomech.rotation_stage_rsp05)
        
        # Adding iris to select the right order of beam
        baseplate.place_element_along_beam("Iris", optomech.pinhole_ida12, beam,
                                           beam_index=0b111, distance=17.5, angle=layout.cardinal['right'],
                                           pre_refs=2, adapter_args=dict(drill_offset=-2))
        
        # Adding another mirror to send the beam back into the AOM
        baseplate.place_element_relative("Retro Mirror", optomech.circular_mirror, lens,
                                         x_off=-50, angle=layout.cardinal['right'],
                                         mount_type=self.mirror, mount_args=dict(thumbscrews=self.thumbscrews))
        
        # Adding output mirrors to send the beam to the fiberport
        baseplate.place_element_along_beam("Output Mirror 1", optomech.circular_mirror, beam,
                                           beam_index=0b11110, distance=30, angle=layout.turn['right-down'],
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=self.thumbscrews))
        
        baseplate.place_element_along_beam("Output Mirror 2", optomech.circular_mirror, beam,
                                           beam_index=0b11110, distance=39.3, angle=layout.turn['down-left'], 
                                           mount_type=self.mirror, mount_args=dict(thumbscrews=self.thumbscrews))
        
        # Adding half waveplate to control the polarization
        baseplate.place_element_along_beam("Half waveplate Out", optomech.waveplate, beam,
                                           beam_index=0b11110, distance=110, angle=layout.cardinal['left'],
                                           mount_type=optomech.rotation_stage_rsp05)
        
        # Adding iris
        baseplate.place_element_along_beam("Iris Out", optomech.pinhole_ida12, beam,
                                           beam_index=0b11110, distance=30, angle=layout.cardinal['right'])
        
        # Fiberport to fiber the beam
        baseplate.place_element_along_beam("Output Fiberport", optomech.fiberport_mount_hca3, beam,
                                           beam_index=0b11110, x=gap - 1, angle=layout.cardinal['right'])
        
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

# doublepass_f100 remains a function for now since it's not used in laser_cooling_subsystem
def doublepass_f100(x=0, y=0, angle=0, mirror=optomech.mirror_mount_km05, x_split=False, thumbscrews=True):
    name = "Doublepass"
    date_time = datetime.now().strftime("%m/%d/%Y")
    label = name + " " + date_time

    base_dx = 13.5 * layout.inch
    base_dy = 5 * layout.inch
    base_dz = layout.inch
    gap = layout.inch / 8

    input_x = 10.5 * layout.inch

    mount_holes = [(0, 0), (8, 3)]
    extra_mount_holes = [(2, 0), (1, 2), (4, 0), (6, 2)]

    baseplate = layout.baseplate(base_dx, base_dy, base_dz, x=x, y=y, angle=angle,
                                 gap=gap, mount_holes=mount_holes + extra_mount_holes,
                                 name=name, label=label, x_splits=[4 * layout.inch] * x_split)
    
    beam = baseplate.add_beam_path(input_x, gap, layout.cardinal['up'])
    
    baseplate.place_element("Input Fiberport", optomech.fiberport_mount_hca3, x=266.7, y=2.6,
                            angle=layout.cardinal['up'])
    
    baseplate.place_element_along_beam("Input Mirror 1", optomech.circular_mirror, beam,
                                       beam_index=0b1, distance=18, angle=layout.turn['up-right'],
                                       mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    baseplate.place_element_along_beam("Input Mirror 2", optomech.circular_mirror, beam,
                                       beam_index=0b1, distance=layout.inch, angle=layout.turn['right-up'],
                                       mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    baseplate.place_element_along_beam("Half waveplate", optomech.waveplate, beam,
                                       beam_index=0b1, distance=54, angle=layout.cardinal['up'],
                                       mount_type=optomech.rotation_stage_rsp05)
    
    baseplate.place_element_along_beam("Beam Splitter", optomech.cube_splitter, beam,
                                       beam_index=0b1, distance=28, angle=layout.cardinal['up'],
                                       mount_type=optomech.skate_mount)
    
    baseplate.place_element_along_beam("AOM", optomech.isomet_1205c_on_km100pm, beam,
                                       beam_index=0b11, distance=60, angle=layout.cardinal['left'],
                                       forward_direction=-1, backward_direction=1)
    
    lens = baseplate.place_element_along_beam("Lens f100mm AB coat", optomech.circular_lens, beam,
                                              beam_index=0b110, distance=100, angle=layout.cardinal['right'],
                                              focal_length=100, part_number='LA1213-AB', mount_type=optomech.lens_holder_l05g)
    
    baseplate.place_element_along_beam("Quarter waveplate", optomech.waveplate, beam,
                                       beam_index=0b110, distance=40, angle=layout.cardinal['left'],
                                       mount_type=optomech.rotation_stage_rsp05)
    
    baseplate.place_element_along_beam("Iris", optomech.pinhole_ida12, beam,
                                       beam_index=0b111, distance=46, angle=layout.cardinal['right'],
                                       pre_refs=2, adapter_args=dict(drill_offset=-2))
    
    baseplate.place_element_relative("Retro Mirror", optomech.circular_mirror, lens,
                                     x_off=-100, angle=layout.cardinal['right'],
                                     mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))

    baseplate.place_element_along_beam("Output Mirror 1", optomech.circular_mirror, beam,
                                       beam_index=0b11110, distance=30, angle=layout.turn['right-down'],
                                       mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    baseplate.place_element_along_beam("Output Mirror 2", optomech.circular_mirror, beam,
                                       beam_index=0b11110, distance=39.3, angle=layout.turn['down-left'],  
                                       mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    baseplate.place_element_along_beam("Half waveplate Out", optomech.waveplate, beam,
                                       beam_index=0b11110, distance=110, angle=layout.cardinal['left'],
                                       mount_type=optomech.rotation_stage_rsp05)
    
    baseplate.place_element_along_beam("Iris", optomech.pinhole_ida12, beam,
                                       beam_index=0b11110, distance=42, angle=layout.cardinal['right'])  

    baseplate.place_element_along_beam("Output Fiberport", optomech.fiberport_mount_hca3, beam,
                                       beam_index=0b11110, x=gap, angle=layout.cardinal['right'])

if __name__ == "__main__":
    doc = App.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "Doublepass_f50")
    doublepass_f50(obj)
    App.ActiveDocument.recompute()
    layout.redraw()