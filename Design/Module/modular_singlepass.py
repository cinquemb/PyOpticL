## The baseplate works as a singlepass. The beam passes through the AOM once and sweep/change the frequency.
# Latest update: 10/25/24 Nishat
from PyOpticL import layout, optomech
from datetime import datetime

# Adding name and date to keep a track of the updates
name = "singlepass"
date_time = datetime.now().strftime("%m/%d/%Y")
label = name + " " + date_time

def singlepass(baseplate, x=0, y=0, angle=270, mirror=optomech.mirror_mount_km05, x_split=False, thumbscrews=True, add_box=False):
    D1 = 1 * layout.inch
    D2 = 0
    # Dimension of the baseplate (used for positioning, not creation)
    base_dx = 8.25 * layout.inch  # 8.25
    base_dy = 4.5 * layout.inch   # 4.6
    base_dz = layout.inch
    gap = layout.inch / 4
    mh = [(3, 0.5), (3, 1.5), (2, 1.5)]
    input_x = 2.75 * layout.inch   # 2.75
    if add_box:
        base_dx = base_dx + 1 * layout.inch
        base_dy = base_dy + 1.5 * layout.inch
        input_x = 3.05 * layout.inch
        D1 = 1.85 * layout.inch
        D2 = 0.7 * layout.inch
        mh = [(2, 4.5), (8, 3.5), (3, 0.5), (3, 1.5), (2, 1.5), (8, 2.5)]

    # Adding the beam to the existing baseplate
    beam = baseplate.add_beam_path(x + base_dx - input_x, y, layout.cardinal['up'])
    
    # Adding two mirrors to give the beam enough degree of freedom. Mirror 1
    baseplate.place_element_along_beam("Input Mirror 1", optomech.circular_mirror, beam,
                                      beam_index=0b1, distance=D1, angle=layout.turn['up-right'],
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Mirror 2
    baseplate.place_element_along_beam("Input Mirror 2", optomech.circular_mirror, beam,
                                      beam_index=0b1, distance=1 * layout.inch, angle=layout.turn['right-up'],
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Adding a waveplate to control the polarization
    baseplate.place_element_along_beam("Half waveplate", optomech.waveplate, beam,
                                      beam_index=0b1, distance=25, angle=layout.cardinal['up'],
                                      mount_type=optomech.rotation_stage_rsp05)
    
    # Adding beam splitter to divide the beam
    baseplate.place_element_along_beam("Beam Splitter", optomech.cube_splitter, beam,
                                      beam_index=0b1, distance=30, angle=layout.cardinal['left'],
                                      mount_type=optomech.skate_mount, invert=True)
    
    # Adding lens pair to make collimated beam. Lens 1
    lens = baseplate.place_element_along_beam("Lens f100mm AB coat", optomech.circular_lens, beam,
                                             beam_index=0b11, distance=25, angle=layout.cardinal['left'],
                                             focal_length=45, part_number='LA1213-AB', mount_type=optomech.lens_holder_l05g)
    
    # Adding AOM
    aom = baseplate.place_element_along_beam("AOM", optomech.isomet_1205c_on_km100pm, beam,
                                            beam_index=0b11, distance=50, angle=layout.cardinal['left'],
                                            forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    if add_box:
        baseplate.add_beam_path(x + 110, y + 130, layout.cardinal['up'], color=(0.0, 0.0, 0.0))  # open window for RF port
    
    # Lens 2
    lens = baseplate.place_element_along_beam("Lens f100mm AB coat", optomech.circular_lens, beam,
                                             beam_index=0b111, distance=50, angle=layout.cardinal['left'] + aom.DiffractionAngle.Value,
                                             focal_length=50, part_number='LA1213-AB', mount_type=optomech.lens_holder_l05g)
    
    # Adding output mirror to send the beam to the fiberport. Mirror 1
    baseplate.place_element_along_beam("Output Mirror 1", optomech.circular_mirror, beam,
                                      beam_index=0b111, distance=15, angle=layout.turn['left-down'] + aom.DiffractionAngle.Value,
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Adding iris to select the right order of beam
    z_ = 10  # distance of iris and half waveplate
    x_ = 25  # distance of output mirror and iris
    baseplate.place_element_along_beam("Iris", optomech.pinhole_ida12, beam,
                                      beam_index=0b111, distance=4 + x_ - z_, angle=layout.cardinal['up'])
    
    # Adding half waveplate to control the polarization
    baseplate.place_element_along_beam("Half waveplate", optomech.waveplate, beam,
                                      beam_index=0b111, distance=4 + z_, angle=layout.cardinal['up'],
                                      mount_type=optomech.rotation_stage_rsp05)

    # Mirror 2 
    baseplate.place_element_along_beam("Output Mirror 2", optomech.circular_mirror, beam,
                                      beam_index=0b111, distance=46.5 - x_, angle=layout.turn['down-left'] + aom.DiffractionAngle.Value / 2,
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Fiberport to fiber the beam
    baseplate.place_element_along_beam("Fiberport", optomech.fiberport_mount_hca3, beam,
                                      beam_index=0b111, distance=19 + D2, angle=layout.cardinal['right'])

    # Cover for the baseplate
    if add_box:
        baseplate.add_cover(dz=50)

def singlepass_mirrored(baseplate, x=0, y=0, angle=270, mirror=optomech.mirror_mount_km05, x_split=False, thumbscrews=True, add_box=False):
    D1 = 1 * layout.inch
    D2 = 0
    # Dimension of the baseplate (used for positioning, not creation)
    base_dx = 8.25 * layout.inch  # 8.25
    base_dy = 4.5 * layout.inch   # 4.6
    base_dz = layout.inch
    gap = layout.inch / 4
    mh = [(3, 3.5), (3, 1.5), (2, 0.5)]
    input_x = 2.75 * layout.inch   # 2.75
    if add_box:
        base_dx = base_dx + 1 * layout.inch
        base_dy = base_dy + 1.5 * layout.inch
        input_x = 3.05 * layout.inch
        D1 = 1.85 * layout.inch
        D2 = 0.7 * layout.inch
        mh = [(3, 4.5), (8, 3.5), (3, 3.5), (3, 1.5), (2, 0.5), (8, 2.5)]

    # Adding the beam to the existing baseplate
    beam = baseplate.add_beam_path(x + base_dx - input_x, y + base_dy - gap - 5, layout.cardinal['down'])
    
    # Adding two mirrors to give the beam enough degree of freedom. Mirror 1
    baseplate.place_element_along_beam("Input Mirror 1", optomech.circular_mirror, beam,
                                      beam_index=0b1, distance=D1, angle=layout.turn['up-right'] + 90,
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Mirror 2
    baseplate.place_element_along_beam("Input Mirror 2", optomech.circular_mirror, beam,
                                      beam_index=0b1, distance=1 * layout.inch, angle=layout.turn['right-up'] + 90,
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Adding a waveplate to control the polarization
    baseplate.place_element_along_beam("Half waveplate", optomech.waveplate, beam,
                                      beam_index=0b1, distance=25, angle=layout.cardinal['up'],
                                      mount_type=optomech.rotation_stage_rsp05)
    
    # Adding beam splitter to divide the beam
    baseplate.place_element_along_beam("Beam Splitter", optomech.cube_splitter, beam,
                                      beam_index=0b1, distance=30, angle=layout.cardinal['left'],
                                      mount_type=optomech.skate_mount, invert=False)
    
    # Adding lens pair to make collimated beam. Lens 1
    lens = baseplate.place_element_along_beam("Lens f100mm AB coat", optomech.circular_lens, beam,
                                             beam_index=0b11, distance=25, angle=layout.cardinal['left'],
                                             focal_length=45, part_number='LA1213-AB', mount_type=optomech.lens_holder_l05g)
    
    # Adding AOM
    aom = baseplate.place_element_along_beam("AOM", optomech.isomet_1205c_on_km100pm, beam,
                                            beam_index=0b11, distance=20, angle=layout.cardinal['right'],
                                            forward_direction=-1, backward_direction=1, diffraction_angle=0.01)
    if add_box:
        baseplate.add_beam_path(x + 136, y, layout.cardinal['up'], color=(0.0, 0.0, 0.0))  # open window for RF port
    
    # Lens 2
    lens = baseplate.place_element_along_beam("Lens f100mm AB coat", optomech.circular_lens, beam,
                                             beam_index=0b111, distance=80, angle=layout.cardinal['left'] + aom.DiffractionAngle.Value,
                                             focal_length=50, part_number='LA1213-AB', mount_type=optomech.lens_holder_l05g)
    
    # Adding output mirror to send the beam to the fiberport. Mirror 1
    baseplate.place_element_along_beam("Output Mirror 1", optomech.circular_mirror, beam,
                                      beam_index=0b111, distance=15, angle=90 + layout.turn['left-down'] + aom.DiffractionAngle.Value,
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Adding iris to select the right order of beam
    z_ = 10  # distance of iris and half waveplate
    x_ = 25  # distance of output mirror and iris
    baseplate.place_element_along_beam("Iris", optomech.pinhole_ida12, beam,
                                      beam_index=0b111, distance=4 + x_ - z_, angle=layout.cardinal['up'])
    
    # Adding half waveplate to control the polarization
    baseplate.place_element_along_beam("Half waveplate", optomech.waveplate, beam,
                                      beam_index=0b111, distance=4 + z_, angle=layout.cardinal['up'],
                                      mount_type=optomech.rotation_stage_rsp05)

    # Mirror 2 
    baseplate.place_element_along_beam("Output Mirror 2", optomech.circular_mirror, beam,
                                      beam_index=0b111, distance=46.5 - x_, angle=90 + layout.turn['down-left'] + aom.DiffractionAngle.Value / 2,
                                      mount_type=mirror, mount_args=dict(thumbscrews=thumbscrews))
    
    # Fiberport to fiber the beam
    baseplate.place_element_along_beam("Fiberport", optomech.fiberport_mount_hca3, beam,
                                      beam_index=0b111, distance=19 + D2, angle=layout.cardinal['right'])

    # Cover for the baseplate
    if add_box:
        baseplate.add_cover(dz=50)

if __name__ == "__main__":
    baseplate = layout.baseplate(10 * layout.inch, 10 * layout.inch, layout.inch)
    singlepass_mirrored(baseplate, x=5, add_box=False)
    layout.redraw()