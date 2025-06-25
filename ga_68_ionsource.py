import FreeCAD as App
import Part
import math

# Create a new document
doc = App.newDocument("Ga68_IonSource_3D_Enclosure_With_IonTrap")

# Function to create a box
def create_box(x, y, z, length, width, height, name, color=(0.6,0.8,1.0), transparency=85):
    box = Part.makeBox(length, width, height, App.Vector(x, y, z))
    box_obj = doc.addObject("Part::Feature", name)
    box_obj.Shape = box
    box_obj.ViewObject.ShapeColor = color
    box_obj.ViewObject.Transparency = transparency
    return box_obj

# Function to create a cylinder
def create_cylinder(x, y, z, radius, height, name, color=(0.8,0.8,0.8), transparency=30):
    cylinder = Part.makeCylinder(radius, height, App.Vector(x, y, z), App.Vector(0, 0, 1))
    cylinder_obj = doc.addObject("Part::Feature", name)
    cylinder_obj.Shape = cylinder
    cylinder_obj.ViewObject.ShapeColor = color
    cylinder_obj.ViewObject.Transparency = transparency
    return cylinder_obj

# Function to create laser viewport assembly
def create_laser_viewport(x, y, z, direction, length, diameter, window_thickness, name_prefix):
    """
    Creates UHV-compatible laser viewport with mounting flange and optical window
    - direction: beam direction vector (normalized)
    - length: total assembly length
    - diameter: flange diameter
    - window_thickness: optical window thickness
    """
    # Normalize direction vector
    dir_vec = App.Vector(*direction).normalize()
    
    # Create mounting flange (CF40 style)
    flange = Part.makeCylinder(diameter/2, 5, App.Vector(x, y, z), dir_vec)
    flange_obj = doc.addObject("Part::Feature", f"{name_prefix}_Flange")
    flange_obj.Shape = flange
    flange_obj.ViewObject.ShapeColor = (0.5, 0.5, 0.5)  # stainless steel
    flange_obj.ViewObject.Transparency = 0
    
    # Create optical window (sapphire)
    window_pos = App.Vector(x, y, z) + dir_vec * (length - window_thickness)
    window = Part.makeCylinder(diameter/2 - 1, window_thickness, window_pos, dir_vec)
    window_obj = doc.addObject("Part::Feature", f"{name_prefix}_Window")
    window_obj.Shape = window
    window_obj.ViewObject.ShapeColor = (0.8, 0.9, 1.0)  # sapphire blue tint
    window_obj.ViewObject.Transparency = 80
    
    return flange_obj, window_obj

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

# ===== MAIN GEOMETRY PARAMETERS =====
pellet_chamber_width = 40
pellet_chamber_depth = 20
pellet_chamber_height = 30

plate_thickness = 1.5
visual_liquid_thickness = 1.0
plate_length = 440
plate_width = 440
guide_length = 200
guide_width = 30
guide_height = 10
ion_trap_rod_radius = 1.5
ion_trap_rod_length = 40
clearance = 5

# ===== PELLET CHAMBER ENCLOSURE =====
#'''
pellet_enclosure = create_box(
    -clearance,
    -clearance,
    -clearance,
    pellet_chamber_width + 2*clearance,
    pellet_chamber_width + 2*clearance,
    pellet_chamber_depth + 2*clearance,
    "PelletEnclosure"
)
#'''
'''
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
'''
print(f"enclosure_length0: {pellet_chamber_width + 2*clearance}, enclosure_width0: {pellet_chamber_width + 2*clearance}, enclosure_height0: {pellet_chamber_depth + 2*clearance}")

# ===== GLASS PLATE SANDWICH ENCLOSURE =====
glass_enclosure = create_box(
    pellet_chamber_width + 10 - clearance,
    -clearance,
    0,
    plate_length + 2*clearance,
    plate_width + 2*clearance,
    plate_thickness*2 + visual_liquid_thickness + clearance,
    "GlassPlateEnclosure"
)
print(f"enclosure_length1: {plate_length + 2*clearance}, enclosure_width1: {plate_width + 2*clearance}, enclosure_height1: {plate_thickness*2 + visual_liquid_thickness + clearance}")

# ===== ION TRAP & GUIDE ENCLOSURE =====
guide_start_x = pellet_chamber_width + 10 + plate_length
trap_center_x = guide_start_x + guide_length + 20
trap_center_y = plate_width/2  # Define if missing
trap_center_z = plate_thickness + visual_liquid_thickness/2 + 10
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
    "IonTrapEnclosure"
)
print(f"enclosure_length2: {ion_guide_and_trap_length}, enclosure_width2: {ion_guide_and_trap_width}, enclosure_height2: {ion_guide_and_trap_height}")

# ===== ION OPTICS =====
# Bottom glass plate
bottom_glass = create_box(
    pellet_chamber_width + 10,
    0,
    0,
    plate_length,
    plate_width,
    plate_thickness,
    "BottomGlassPlate",
    color=(0.9,0.9,0.9),
    transparency=50
)

# Liquid gallium layer
liquid_ga = create_box(
    pellet_chamber_width + 10,
    0,
    plate_thickness,
    plate_length,
    plate_width,
    visual_liquid_thickness,
    "LiquidGallium",
    color=(0.8,0.8,0.8),
    transparency=40
)

# Top glass plate
top_glass = create_box(
    pellet_chamber_width + 10,
    0,
    plate_thickness + visual_liquid_thickness,
    plate_length,
    plate_width,
    plate_thickness,
    "TopGlassPlate",
    color=(0.9,0.9,0.9),
    transparency=50
)


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

# First extraction electrode (30% along plate)
extraction_electrode1 = create_box(
    pellet_chamber_width + 10 + plate_length * 0.3,
    plate_width/2 - 15,
    plate_thickness + visual_liquid_thickness + 1,
    5,
    30,
    5,
    "ExtractionElectrode1",
    color=(0.2,0.2,0.8),
    transparency=20
)

# Second extraction electrode (70% along plate)
extraction_electrode2 = create_box(
    pellet_chamber_width + 10 + plate_length * 0.7,
    plate_width/2 - 15,
    plate_thickness + visual_liquid_thickness + 1,
    5,
    30,
    5,
    "ExtractionElectrode2",
    color=(0.2,0.2,0.8),
    transparency=20
)

# Ion guide plates (4 plates)
guide_start_x = pellet_chamber_width + 10 + plate_length
for i in range(4):
    y_pos = plate_width/2 - guide_width/2 + (i * guide_width/3)
    ion_guide_plate = create_box(
        guide_start_x,
        y_pos,
        plate_thickness + visual_liquid_thickness/2 - guide_height/2,
        guide_length,
        2,
        guide_height,
        f"IonGuidePlate_{i+1}",
        color=(0.7,0.1,0.1),
        transparency=30
    )

# Ion trap rods (4 rods)
rod_angles = [0, 90, 180, 270]
for i, angle in enumerate(rod_angles):
    rad_angle = math.radians(angle)
    rod_x = trap_center_x
    rod_y = trap_center_y + 5 * math.cos(rad_angle)
    rod_z = trap_center_z + 5 * math.sin(rad_angle)
    
    rod = Part.makeCylinder(
        ion_trap_rod_radius,
        ion_trap_rod_length,
        App.Vector(rod_x - ion_trap_rod_length/2, rod_y, rod_z),
        App.Vector(1, 0, 0)
    )
    rod_obj = doc.addObject("Part::Feature", f"IonTrapRod_{i+1}")
    rod_obj.Shape = rod
    rod_obj.ViewObject.ShapeColor = (0.1,0.7,0.1)
    rod_obj.ViewObject.Transparency = 10

# ===== VACUUM SYSTEM ENHANCEMENTS =====
# Laser viewport for liquid gallium ionization (213nm beam)
ionization_viewport_x = pellet_chamber_width + 10 + plate_length/2
ionization_viewport_y = plate_width/2
ionization_viewport_z = plate_thickness*2 + visual_liquid_thickness + 10
create_laser_viewport(
    ionization_viewport_x,
    ionization_viewport_y,
    ionization_viewport_z,
    (0, 0, -1),  # Downward beam direction
    25,            # Viewport length
    30,            # Flange diameter
    3,             # Window thickness
    "IonizationLaser"
)

# Laser viewport for ion trap cooling (369nm beam)
cooling_viewport_x = trap_center_x
cooling_viewport_y = ion_guide_and_trap_start_y - 5
cooling_viewport_z = trap_center_z
create_laser_viewport(
    cooling_viewport_x,
    cooling_viewport_y,
    cooling_viewport_z,
    (0, 1, 0),    # Inward beam direction
    30,            # Viewport length
    25,            # Flange diameter
    2,             # Window thickness
    "CoolingLaser"
)

# Turbo-molecular pump port
pump_port_x = ion_guide_and_trap_start_x + ion_guide_and_trap_length - 15
pump_port_y = ion_guide_and_trap_start_y + ion_guide_and_trap_width/2
pump_port_z = ion_guide_and_trap_start_z + ion_guide_and_trap_height - 5
create_cylinder(
    pump_port_x,
    pump_port_y,
    pump_port_z,
    20,            # Port radius
    15,            # Port height
    "TurboPumpPort",
    color=(0.3,0.3,0.3)
)

# Electrical feedthroughs (4x for trap electrodes)
for i in range(4):
    feedthrough_x = ion_guide_and_trap_start_x + 15 + i*30
    feedthrough_y = ion_guide_and_trap_start_y + ion_guide_and_trap_width - 5
    feedthrough_z = ion_guide_and_trap_start_z + ion_guide_and_trap_height - 5
    create_cylinder(
        feedthrough_x,
        feedthrough_y,
        feedthrough_z,
        5,          # Feedthrough radius
        10,         # Feedthrough height
        f"ElectrodeFeedthrough_{i+1}",
        color=(0.2,0.2,0.2)
    )

# Pressure gauge port
gauge_port_x = ion_guide_and_trap_start_x + ion_guide_and_trap_length/2
gauge_port_y = ion_guide_and_trap_start_y - 5
gauge_port_z = ion_guide_and_trap_start_z + ion_guide_and_trap_height - 10
create_cylinder(
    gauge_port_x,
    gauge_port_y,
    gauge_port_z,
    8,             # Gauge radius
    12,            # Gauge height
    "IonGaugePort",
    color=(0.4,0.1,0.1)
)

# ===== FINAL VIEW SETUP =====
doc.recompute()
print("3D schematic with full ion extraction, guiding electrodes, and storage ion trap created. View set to top-down orthographic.")
