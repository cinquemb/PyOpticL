import FreeCAD as App
import FreeCADGui as Gui
import Part
from math import cos, sin, pi

doc = App.newDocument("Ga68_IonSource_3D_Enclosure_With_IonTrap")

# Updated Parameters (mm)
plate_length = 430  # 43 cm
plate_width = 430   # 43 cm
plate_thickness = 1
liquid_layer_thickness = 0.0001  # 100 nm (exaggerated visually below)
visual_liquid_thickness = liquid_layer_thickness#0.1  # for visibility in CAD
pellet_chamber_width = 40
pellet_chamber_height = 30
pellet_chamber_depth = 20
heater_trace_width = 1
heater_trace_thickness = 0.05
electrode_width = 2
electrode_thickness = 0.1
ion_trap_rod_radius = 2.5
ion_trap_rod_length = 60
ion_trap_rod_spacing = 10  # center-to-center spacing between rods
ion_trap_width = 30
ion_trap_height = 50
ion_trap_depth = 40
enclosure_thickness = 2

def create_box(x, y, z, length, width, height, name, color=None, transparency=0):
    box = Part.makeBox(length, width, height, App.Vector(x, y, z))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    if color:
        obj.ViewObject.ShapeColor = color
    obj.ViewObject.Transparency = transparency
    return obj

def create_cylinder(x, y, z, radius, height, name, color=None, transparency=0):
    cyl = Part.makeCylinder(radius, height, App.Vector(x, y, z))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = cyl
    if color:
        obj.ViewObject.ShapeColor = color
    obj.ViewObject.Transparency = transparency
    return obj

def create_valve(x, y, z, diameter, length, gate_thickness, actuator_height, name_prefix):
    # Valve body (cylinder)
    #valve_body = Part.makeCylinder(diameter/2, length, App.Vector(x, y - diameter/2, z))
    #valve_body_obj = doc.addObject("Part::Feature", f"{name_prefix}_Body")
    #valve_body_obj.Shape = valve_body
    #alve_body_obj.ViewObject.ShapeColor = (0.5, 0.5, 0.5)
    #valve_body_obj.ViewObject.Transparency = 20

    # Valve gate (block inside valve body)
    gate = Part.makeBox(gate_thickness, diameter, diameter, App.Vector(x + length/2 - gate_thickness/2, y - diameter/2, z))
    gate_obj = doc.addObject("Part::Feature", f"{name_prefix}_Gate")
    gate_obj.Shape = gate
    gate_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
    gate_obj.ViewObject.Transparency = 0

    # Actuator housing (box on top)
    actuator = Part.makeBox(diameter*0.6, diameter*0.6, actuator_height, App.Vector(x + length/2 - diameter*0.3, y - diameter*0.3, z + diameter))
    actuator_obj = doc.addObject("Part::Feature", f"{name_prefix}_Actuator")
    actuator_obj.Shape = actuator
    actuator_obj.ViewObject.ShapeColor = (0.2, 0.2, 0.8)
    actuator_obj.ViewObject.Transparency = 30

    return gate_obj, actuator_obj


# Pellet Chamber
pellet_chamber = create_box(0, plate_width + 10, plate_thickness + visual_liquid_thickness + plate_thickness,
                            pellet_chamber_width, pellet_chamber_height, pellet_chamber_depth, "PelletChamber",
                            color=(0.8,0.3,0.3), transparency=0)

# Drain Channel connecting Pellet Chamber to Bottom Glass Plate
drain_channel = create_box(pellet_chamber_width, plate_width + 10 + pellet_chamber_height/2 - 2,
                          plate_thickness + visual_liquid_thickness + plate_thickness,
                          10, 4, 4, "DrainChannel", color=(0.6,0.6,0.6), transparency=0)

# Bottom Glass Plate
bottom_plate = create_box(pellet_chamber_width + 10, 0, 0,
                          plate_length, plate_width, plate_thickness, "BottomGlassPlate",
                          color=(0.7,0.7,0.9), transparency=0)

# Heater traces on bottom plate (3 thin boxes)
for i in range(3):
    y = 10 + i*150  # scaled spacing for larger plate
    heater = create_box(pellet_chamber_width + 15, y, plate_thickness,
                        plate_length - 10, heater_trace_width, heater_trace_thickness,
                        f"HeaterTrace_{i+1}", color=(1.0,0.5,0.0), transparency=0)

# Liquid Ga Layer (thin box between glass plates)
liquid_layer = create_box(pellet_chamber_width + 10, 0, plate_thickness,
                          plate_length, plate_width, visual_liquid_thickness, "LiquidGaLayer",
                          color=(0.9,0.9,0.3), transparency=70)  # semi-transparent yellow

# Top Glass Plate
top_plate = create_box(pellet_chamber_width + 10, 0, plate_thickness + visual_liquid_thickness,
                       plate_length, plate_width, plate_thickness, "TopGlassPlate",
                       color=(0.7,0.7,0.9), transparency=30)  # semi-transparent glass

# Valve parameters
valve_diameter = 40  # mm, typical vacuum flange size
valve_length = 20    # mm, valve body length
gate_thickness = 3   # mm, thickness of valve shutter
actuator_height = 30 # mm, actuator housing height

# Position valve just after glass plates, before electrodes
valve_x = pellet_chamber_width + 10 + plate_length + 2  # small gap after glass plates
valve_y = plate_width / 2  # center in Y
valve_z = plate_thickness + visual_liquid_thickness / 2  # aligned with liquid layer height

valve_gate, valve_actuator = create_valve(valve_x, valve_y, valve_z,
                                                     valve_diameter, valve_length,
                                                     gate_thickness, actuator_height,
                                                     "GlassToElectrodeValve")


# Ion Extraction Electrodes (2 thin vertical plates near liquid layer)
electrode_x1 = pellet_chamber_width + 10 + plate_length * 0.3
electrode_x2 = pellet_chamber_width + 10 + plate_length * 0.7
for idx, x in enumerate([electrode_x1, electrode_x2], 1):
    electrode = create_box(x, 0, plate_thickness,
                          electrode_width, plate_width, electrode_thickness,
                          f"IonExtractionElectrode_{idx}", color=(0.8,0.8,0.8), transparency=0)

# Additional Ion Guiding Electrodes (forming electrostatic lenses/path to storage trap)
# We'll create 4 parallel plates forming a simple ion guide channel from extraction to trap

guide_start_x = pellet_chamber_width + 10 + plate_length + 5
guide_length = 50
guide_width = 20
guide_height = 10
guide_plate_thickness = 0.5

# Two side plates (left and right)
left_plate = create_box(guide_start_x, (plate_width/2) - guide_width/2, plate_thickness + visual_liquid_thickness/2,
                        guide_length, guide_plate_thickness, guide_height,
                        "IonGuide_LeftPlate", color=(0.6,0.6,0.6), transparency=30)

right_plate = create_box(guide_start_x, (plate_width/2) + guide_width/2 - guide_plate_thickness,
                         plate_thickness + visual_liquid_thickness/2,
                         guide_length, guide_plate_thickness, guide_height,
                         "IonGuide_RightPlate", color=(0.6,0.6,0.6), transparency=30)

# Bottom plate
bottom_guide = create_box(guide_start_x, (plate_width/2) - guide_width/2, plate_thickness + visual_liquid_thickness/2,
                          guide_length, guide_width, guide_plate_thickness,
                          "IonGuide_BottomPlate", color=(0.6,0.6,0.6), transparency=30)

# Top plate
top_guide = create_box(guide_start_x, (plate_width/2) - guide_width/2, plate_thickness + visual_liquid_thickness/2 + guide_height - guide_plate_thickness,
                       guide_length, guide_width, guide_plate_thickness,
                       "IonGuide_TopPlate", color=(0.6,0.6,0.6), transparency=30)

# Ion Ejection Path (clear path from guide to trap)
ion_eject_path = create_box(guide_start_x + guide_length, (plate_width/2) - 2,
                           plate_thickness + visual_liquid_thickness/2 + guide_height/2 - 2,
                           ion_trap_width, 4, 4, "IonEjectionPath",
                           color=(0.5,0.5,0.5), transparency=0)

# Storage Ion Trap: Four cylindrical rods arranged in a quadrupole geometry
# Rods length along X axis, spaced in YZ plane

trap_center_x = guide_start_x + guide_length + ion_trap_width/2
trap_center_y = plate_width / 2
trap_center_z = plate_thickness + visual_liquid_thickness/2 + guide_height/2

rod_positions = [
    (trap_center_x, trap_center_y + ion_trap_rod_spacing/2, trap_center_z + ion_trap_rod_spacing/2),
    (trap_center_x, trap_center_y + ion_trap_rod_spacing/2, trap_center_z - ion_trap_rod_spacing/2),
    (trap_center_x, trap_center_y - ion_trap_rod_spacing/2, trap_center_z + ion_trap_rod_spacing/2),
    (trap_center_x, trap_center_y - ion_trap_rod_spacing/2, trap_center_z - ion_trap_rod_spacing/2),
]

for i, (x, y, z) in enumerate(rod_positions, 1):
    # Rods oriented along X-axis (length)
    rod = Part.makeCylinder(ion_trap_rod_radius, ion_trap_rod_length, App.Vector(x - ion_trap_rod_length/2, y, z))
    rod_obj = doc.addObject("Part::Feature", f"IonTrapRod_{i}")
    rod_obj.Shape = rod
    rod_obj.ViewObject.ShapeColor = (0.2, 0.2, 0.7)
    rod_obj.ViewObject.Transparency = 0

# Transparent enclosure around pellet chamber and glass plates
clearance = 5  # mm clearance around parts
glass_clearance = 2  # mm clearance around parts

# Pellet chamber enclosure (tallest)
pellet_enclosure_height = pellet_chamber_depth + plate_thickness*2 + visual_liquid_thickness + clearance
pellet_enclosure = create_box(
    -clearance,
    plate_width + 10 - clearance,
    -clearance,
    pellet_chamber_width + 2*clearance,
    pellet_chamber_height + 2*clearance,
    pellet_enclosure_height,
    "PelletEnclosure",
    color=(0.6,0.8,1.0),
    transparency=85
)

print("enclosure_length0: %s, enclosure_width0: %s, enclosure_height0: %s, " % (pellet_chamber_width + 2*clearance, pellet_chamber_height + 2*clearance, pellet_enclosure_height))


# Glass plate sandwich enclosure (very thin)
glass_enclosure_height = plate_thickness*2 + visual_liquid_thickness + glass_clearance
glass_enclosure = create_box(
    pellet_chamber_width + 10 - glass_clearance,
    -clearance,
    0,
    plate_length + 2*glass_clearance,
    plate_width + 2*glass_clearance,
    glass_enclosure_height,
    "GlassPlateEnclosure",
    color=(0.6,0.8,1.0),
    transparency=85
)
print("enclosure_length1: %s, enclosure_width1: %s, enclosure_height1: %s, " % (plate_length + 2*clearance, plate_width + 2*clearance, glass_enclosure_height))

# Ion trap and ion optics enclosure (medium height)
# Ion trap and ion optics enclosure (covers entire ion guide and trap region)
ion_guide_and_trap_start_x = guide_start_x - clearance
ion_guide_and_trap_end_x = trap_center_x + ion_trap_rod_length/2 + clearance
ion_guide_and_trap_length = ion_guide_and_trap_end_x - ion_guide_and_trap_start_x

ion_guide_and_trap_start_y = (plate_width/2) - (guide_width/2) - clearance
ion_guide_and_trap_end_y = (plate_width/2) + (guide_width/2) + clearance
ion_guide_and_trap_width = ion_guide_and_trap_end_y - ion_guide_and_trap_start_y

ion_guide_and_trap_start_z = plate_thickness + visual_liquid_thickness/2 - clearance
ion_guide_and_trap_end_z = trap_center_z + ion_trap_rod_radius + clearance
ion_guide_and_trap_height = ion_guide_and_trap_end_z - ion_guide_and_trap_start_z

ion_trap_enclosure = create_box(
    ion_guide_and_trap_start_x,
    ion_guide_and_trap_start_y,
    ion_guide_and_trap_start_z,
    ion_guide_and_trap_length,
    ion_guide_and_trap_width,
    ion_guide_and_trap_height,
    "IonTrapEnclosure",
    color=(0.6,0.8,1.0),
    transparency=85
)

print("enclosure_length2: %s, enclosure_width2: %s, enclosure_height2: %s, " % (ion_guide_and_trap_length, ion_guide_and_trap_width, ion_guide_and_trap_height))


# Optional: add small connecting tubes or apertures between these volumes if modeling differential pumping


# Recompute document to update view
doc.recompute()

# Set default view to top-down orthographic
view = Gui.ActiveDocument.ActiveView
view.viewTop()
view.fitAll()

print("3D schematic with full ion extraction, guiding electrodes, and storage ion trap created. View set to top-down orthographic.")
