import pytest
import random
import numpy as np
import astropy.units as u

from astropy.io import fits
from collections import namedtuple

from ppdmod.functionality.data_prep import ReadoutFits, DataHandler


################################### Fixtures #############################################

@pytest.fixture
def example_fits_file_path():
    return "../data/test.fits"

@pytest.fixture
def header_names_tuple():
    Data = namedtuple("Data", ["header", "data", "error", "station"])
    vis = Data("oi_vis", "visamp", "visamperr", "sta_index")
    vis2 = Data("oi_vis2", "vis2amp", "vis2amperr", "sta_index")
    t3phi = Data("oi_t3phi", "t3phi", "t3phierr", "sta_index")
    flux = Data("oi_flux", "fluxdata", "fluxerr", None)
    wavelength = Data("oi_wavelength", "eff_wave", None, None)
    Header = namedtuple("Header", ["vis", "vis2", "cphase", "flux", "wavelength"])
    return Header(vis, vis2, t3phi, flux, wavelength)

@pytest.fixture
def mock_vis_data():
    mock_vis = np.random.rand(6, 121)*u.dimensionless_unscaled
    mock_viserr = np.arange(6, 121)*0.2*u.dimensionless_unscaled
    return mock_vis, mock_viserr

@pytest.fixture
def example_fits_files_lists(example_fits_file_path):
    two_fits_files = [example_fits_file_path]*2
    three_fits_files = [example_fits_file_path]*3
    return two_fits_files, three_fits_files

@pytest.fixture
def example_polychromatic_vis4wl_dataset():
    visdata_first_wl_ind = [2.7, 2.5, 2.2, 2.0, 1.8, 1.6]*u.Jy
    visdata_second_wl_ind = [2.5, 2.3, 2.0, 1.8, 1.6, 1.4]*u.Jy
    visdata_third_wl_ind = [2.3, 2.1, 1.8, 1.6, 1.4, 1.2]*u.Jy
    mock_visdata = u.Quantity([visdata_first_wl_ind, visdata_second_wl_ind,
                               visdata_third_wl_ind])
    mock_visdata = np.concatenate((mock_visdata, mock_visdata)).reshape(2, 3, 6)
    return u.Quantity(mock_visdata)

@pytest.fixture
def wl_ind_mock_data():
    wl_ind = [[random.randint(0, 120)]]
    wl_indices = [[random.randint(0, 120) for _ in range(5)]]
    wl_poly_indices = np.array([np.random.randint(0, 120)\
                                for _ in range(6)]).reshape(2, 3)
    len_wl_indices = len(wl_indices)
    shape_wl_poly_indices = wl_poly_indices.shape[0]
    return wl_ind, wl_indices, wl_poly_indices.tolist(),\
        len_wl_indices, shape_wl_poly_indices

@pytest.fixture
def selected_wavelengths():
    return [8.5], [8.5, 10.0], [8.5]*random.randint(1, 10)

################################ ReadoutFits - TESTS #####################################

# TODO: Implement this test
def test_get_info():
    ...

# TODO: Implement this test
def test_get_header():
    ...

def test_get_data(example_fits_file_path, header_names_tuple):
    """Tests if all MATISSE values can be fetched from the (.fits)-file"""
    readout = ReadoutFits(example_fits_file_path)
    output =  readout.get_data(header_names_tuple.vis.header,
            header_names_tuple.vis.data, header_names_tuple.vis.error,
            header_names_tuple.vis.station)

    data, error, sta_index = output

    with fits.open(example_fits_file_path) as hdul:
        data_fits = hdul[header_names_tuple.vis.header].data[header_names_tuple.vis.data]
        error_fits = hdul[header_names_tuple.vis.header].data[header_names_tuple.vis.error]
        sta_index_fits = hdul[header_names_tuple.vis.header]\
                .data[header_names_tuple.vis.station]

    assert len(output) == 3
    assert isinstance(data, np.ndarray)
    assert isinstance(error, np.ndarray)
    assert isinstance(sta_index, np.ndarray)
    assert np.all(data == data_fits)
    assert np.all(error == error_fits)
    assert np.all(sta_index == sta_index_fits)

def test_get_wavelength_indicies(example_fits_file_path):
    # TODO: Make this test better if (.fits)-file is in L-band -> Automatically read band
    wavelength_selection_single = [8.5]
    wavelength_selection_multiple = [8.5, 10.0]
    readout = ReadoutFits(example_fits_file_path)
    wl_ind_no_window = readout.get_wavelength_indices(wavelength_selection_single, [0.0])
    wl_ind_small_window = readout.get_wavelength_indices(wavelength_selection_single,
                                                         [0.1])

    wl_ind_normal_window = readout.get_wavelength_indices(wavelength_selection_single,
                                                         [0.2])
    wl_ind_multi_no_win = readout.get_wavelength_indices(wavelength_selection_multiple,
                                                         [0.0])

    wl_ind_multi_s_win = readout.get_wavelength_indices(wavelength_selection_multiple,
                                                        [0.1])
    wl_ind_multi_n_win = readout.get_wavelength_indices(wavelength_selection_multiple,
                                                        [0.2])
    # TODO: Add here L-band check
    assert not wl_ind_no_window[0] == True
    assert len(wl_ind_small_window[0]) == 1
    assert len(wl_ind_normal_window[0]) == 3
    assert not wl_ind_multi_no_win[0] == True
    assert len(wl_ind_multi_s_win[0]) == 1
    assert len(wl_ind_multi_n_win[0]) == 3
    assert not wl_ind_multi_no_win[1] == True
    assert len(wl_ind_multi_s_win[1]) == 3
    assert len(wl_ind_multi_n_win[1]) == 5

def test_get_data_for_wavelength(example_fits_file_path, wl_ind_mock_data):
    readout = ReadoutFits(example_fits_file_path)
    wl_ind, wl_indices, wl_poly_indices,\
        len_wl_indices, len_wl_poly_indices = wl_ind_mock_data
    visdata = readout.get_visibilities()
    vis4wl_singular, viserr4wl_singular = readout.get_data_for_wavelength(visdata, wl_ind)
    vis4wl, viserr4wl = readout.get_data_for_wavelength(visdata, wl_indices)
    vis4wl_poly, viserr4wl_poly = readout.get_data_for_wavelength(visdata, wl_poly_indices)
    assert isinstance(vis4wl_singular.value, np.ndarray)
    assert isinstance(viserr4wl_singular.value, np.ndarray)
    assert isinstance(vis4wl.value, np.ndarray)
    assert isinstance(viserr4wl.value, np.ndarray)
    assert isinstance(vis4wl_poly.value, np.ndarray)
    assert isinstance(viserr4wl_poly.value, np.ndarray)
    assert vis4wl_singular.shape == (1, 6)
    assert viserr4wl_singular.shape == (1, 6)
    assert vis4wl.shape == (len_wl_indices, 6)
    assert viserr4wl.shape == (len_wl_indices, 6)
    assert vis4wl_poly.shape == (len_wl_poly_indices, 6)
    assert viserr4wl_poly.shape == (len_wl_poly_indices, 6)
    assert vis4wl_singular.unit == u.Jy
    assert viserr4wl_singular.unit == u.Jy
    assert vis4wl.unit == u.Jy
    assert viserr4wl.unit == u.Jy

def test_average_polychromatic_data(example_fits_file_path,
                                    example_polychromatic_vis4wl_dataset):
    readout = ReadoutFits(example_fits_file_path)
    averaged = readout.average_polychromatic_data(example_polychromatic_vis4wl_dataset)
    assert averaged.shape == (2, 6)
    assert averaged[0].shape == (6, )

def test_get_telescope_information(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    station_names, station_indicies,\
            station_indicies4baselines,\
            station_indicies4triangles = readout.get_telescope_information()
    assert isinstance(station_names, np.ndarray)
    assert isinstance(station_names[0], str)
    assert isinstance(station_indicies.value, np.ndarray)
    assert isinstance(station_indicies4baselines.value, np.ndarray)
    assert isinstance(station_indicies4triangles.value, np.ndarray)
    assert station_indicies.unit == u.dimensionless_unscaled

# TODO: Implement this test
def test_get_split_uvcoords():
    ...

# TODO: Implement this test
def test_get_uvcoords():
    ...

# TODO: Implement this test
def test_get_closure_phases_uvcoords():
    ...

def test_get_baselines(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    baselines = readout.get_baselines()
    assert isinstance(baselines.value, np.ndarray)
    assert baselines.unit == u.m

def test_get_visibilities(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    vis, viserr = readout.get_visibilities()
    assert isinstance(vis.value, np.ndarray)
    assert isinstance(viserr.value, np.ndarray)
    assert isinstance(vis.value[0], np.ndarray)
    assert isinstance(vis.value[0][0], float)
    assert isinstance(viserr.value[0], np.ndarray)
    assert isinstance(viserr.value[0][0], float)
    assert vis.shape == (6, 121)
    assert viserr.shape == (6, 121)

    if np.max(vis.value) >= 1.:
        assert vis.unit == u.Jy
        assert viserr.unit == u.Jy
    else:
        assert vis.unit == u.dimensionless_unscaled
        assert viserr.unit == u.dimensionless_unscaled

def test_get_visibilities_squared(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    vis2, vis2err = readout.get_visibilities_squared()
    assert isinstance(vis2.value, np.ndarray)
    assert isinstance(vis2err.value, np.ndarray)
    assert isinstance(vis2.value[0], np.ndarray)
    assert isinstance(vis2.value[0][0], float)
    assert isinstance(vis2err.value[0], np.ndarray)
    assert isinstance(vis2err.value[0][0], float)
    assert vis2.shape == (6, 121)
    assert vis2err.shape == (6, 121)
    assert vis2.unit == u.dimensionless_unscaled
    assert vis2err.unit == u.dimensionless_unscaled

def test_get_closure_phases(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    cphases, cphaseserr = readout.get_closure_phases()
    assert isinstance(cphases.value, np.ndarray)
    assert isinstance(cphaseserr.value, np.ndarray)
    assert isinstance(cphases.value[0], np.ndarray)
    assert isinstance(cphases.value[0][0], float)
    assert isinstance(cphaseserr.value[0], np.ndarray)
    assert isinstance(cphaseserr.value[0][0], float)
    assert cphases.shape == (4, 121)
    assert cphaseserr.shape == (4, 121)
    assert cphases.unit == u.deg
    assert cphaseserr.unit == u.deg

def test_get_flux(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    flux, fluxerr = readout.get_flux()
    assert isinstance(flux.value, np.ndarray)
    assert isinstance(fluxerr.value, np.ndarray)
    assert flux.shape == (1, 121)
    assert fluxerr.shape == (1, 121)
    assert flux.unit== u.Jy
    assert fluxerr.unit== u.Jy

def test_get_wavelength_solution(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    wavelength_solution = readout.get_wavelength_solution()
    assert isinstance(wavelength_solution.value, np.ndarray)
    assert wavelength_solution.unit == u.um

def test_get_visibilities4wavelength(example_fits_file_path, wl_ind_mock_data):
    readout = ReadoutFits(example_fits_file_path)
    wl_ind, wl_indices, wl_poly_indices,\
        len_wl_indices, len_wl_poly_indices = wl_ind_mock_data
    vis4wl_singular, viserr4wl_singular = readout.get_visibilities4wavelength(wl_ind)
    vis4wl, viserr4wl = readout.get_visibilities4wavelength(wl_indices)
    vis4wl_poly, viserr4wl_poly = readout.get_visibilities4wavelength(wl_poly_indices)
    assert isinstance(vis4wl_singular.value, np.ndarray)
    assert isinstance(viserr4wl_singular.value, np.ndarray)
    assert isinstance(vis4wl.value, np.ndarray)
    assert isinstance(viserr4wl.value, np.ndarray)
    assert isinstance(vis4wl_poly.value, np.ndarray)
    assert isinstance(viserr4wl_poly.value, np.ndarray)
    assert vis4wl_singular.shape == (1, 6)
    assert viserr4wl_singular.shape == (1, 6)
    assert vis4wl.shape == (len_wl_indices, 6)
    assert viserr4wl.shape == (len_wl_indices, 6)
    assert vis4wl_poly.shape == (len_wl_poly_indices, 6)
    assert viserr4wl_poly.shape == (len_wl_poly_indices, 6)

    if np.max(vis4wl_singular.value) >= 1.:
        assert vis4wl_singular.unit == u.Jy
        assert viserr4wl_singular.unit == u.Jy
        assert vis4wl.unit == u.Jy
        assert viserr4wl.unit == u.Jy
        assert vis4wl_poly.unit == u.Jy
        assert viserr4wl_poly.unit == u.Jy
    else:
        assert vis4wl_singular.unit == u.dimensionless_unscaled
        assert viserr4wl_singular.unit == u.dimensionless_unscaled
        assert vis4wl.unit == u.dimensionless_unscaled
        assert viserr4wl.unit == u.dimensionless_unscaled
        assert vis4wl_poly.unit == u.dimensionless_unscaled
        assert viserr4wl_poly.unit == u.dimensionless_unscaled

def test_get_visibilities24wavelength(example_fits_file_path, wl_ind_mock_data):
    readout = ReadoutFits(example_fits_file_path)
    wl_ind, wl_indices, wl_poly_indices,\
        len_wl_indices, len_wl_poly_indices = wl_ind_mock_data
    vis24wl_singular,\
        vis2err4wl_singular = readout.get_visibilities_squared4wavelength(wl_ind)
    vis24wl,\
        vis2err4wl = readout.get_visibilities_squared4wavelength(wl_indices)
    vis24wl_poly,\
        vis2err4wl_poly = readout.get_visibilities_squared4wavelength(wl_poly_indices)
    assert isinstance(vis24wl_singular.value, np.ndarray)
    assert isinstance(vis2err4wl_singular.value, np.ndarray)
    assert isinstance(vis24wl.value, np.ndarray)
    assert isinstance(vis2err4wl.value, np.ndarray)
    assert vis24wl_singular.shape == (1, 6)
    assert vis2err4wl_singular.shape == (1, 6)
    assert vis24wl.shape == (len_wl_indices, 6)
    assert vis2err4wl.shape == (len_wl_indices, 6)
    assert vis24wl_poly.shape == (len_wl_poly_indices, 6)
    assert vis2err4wl_poly.shape == (len_wl_poly_indices, 6)
    assert vis24wl_singular.unit == u.dimensionless_unscaled
    assert vis2err4wl_singular.unit == u.dimensionless_unscaled
    assert vis24wl.unit == u.dimensionless_unscaled
    assert vis2err4wl.unit == u.dimensionless_unscaled
    assert vis24wl_poly.unit == u.dimensionless_unscaled
    assert vis2err4wl_poly.unit == u.dimensionless_unscaled

def test_get_closure_phases4wavelength(example_fits_file_path, wl_ind_mock_data):
    readout = ReadoutFits(example_fits_file_path)
    wl_ind, wl_indices, wl_poly_indices,\
        len_wl_indices, len_wl_poly_indices = wl_ind_mock_data
    cphases4wl_singular,\
            cphaseserr4wl_singular = readout.get_closure_phases4wavelength(wl_ind)
    cphases4wl, cphaseserr4wl = readout.get_closure_phases4wavelength(wl_indices)
    cphases4wl_poly,\
        cphaseserr4wl_poly = readout.get_closure_phases4wavelength(wl_poly_indices)
    assert isinstance(cphases4wl_singular.value, np.ndarray)
    assert isinstance(cphaseserr4wl_singular.value, np.ndarray)
    assert isinstance(cphases4wl.value, np.ndarray)
    assert isinstance(cphaseserr4wl.value, np.ndarray)
    assert isinstance(cphases4wl_poly.value, np.ndarray)
    assert isinstance(cphaseserr4wl_poly.value, np.ndarray)
    assert cphases4wl_singular.shape == (1, 4)
    assert cphaseserr4wl_singular.shape == (1, 4)
    assert cphases4wl.shape == (len_wl_indices, 4)
    assert cphaseserr4wl.shape == (len_wl_indices, 4)
    assert cphases4wl_poly.shape == (len_wl_poly_indices, 4)
    assert cphaseserr4wl_poly.shape == (len_wl_poly_indices, 4)
    assert cphases4wl_singular.unit == u.deg
    assert cphaseserr4wl_singular.unit == u.deg
    assert cphases4wl.unit == u.deg
    assert cphaseserr4wl.unit == u.deg
    assert cphases4wl_poly.unit == u.deg
    assert cphaseserr4wl_poly.unit == u.deg

def test_get_flux4wavlength(example_fits_file_path, wl_ind_mock_data):
    readout = ReadoutFits(example_fits_file_path)
    wl_ind, wl_indices, wl_poly_indices,\
        len_wl_indices, len_wl_poly_indices = wl_ind_mock_data
    flux4wl_singular, fluxerr4wl_singular = readout.get_flux4wavelength(wl_ind)
    flux4wl, fluxerr4wl = readout.get_flux4wavelength(wl_indices)
    flux4wl_poly, fluxerr4wl_poly = readout.get_flux4wavelength(wl_poly_indices)
    assert isinstance(flux4wl_singular.value, np.ndarray)
    assert isinstance(fluxerr4wl_singular.value, np.ndarray)
    assert isinstance(flux4wl.value, np.ndarray)
    assert isinstance(fluxerr4wl.value, np.ndarray)
    assert isinstance(flux4wl_poly.value, np.ndarray)
    assert isinstance(fluxerr4wl_poly.value, np.ndarray)
    assert flux4wl_singular.value.shape == (1, 1)
    assert fluxerr4wl_singular.value.shape == (1, 1)
    assert flux4wl.value.shape == (len_wl_indices, 1)
    assert fluxerr4wl.value.shape == (len_wl_indices, 1)
    assert flux4wl_poly.value.shape == (len_wl_poly_indices, 1)
    assert fluxerr4wl_poly.value.shape == (len_wl_poly_indices, 1)
    assert flux4wl_singular.unit == u.Jy
    assert fluxerr4wl_singular.unit == u.Jy
    assert flux4wl.unit == u.Jy
    assert fluxerr4wl.unit == u.Jy
    assert flux4wl_poly.unit == u.Jy
    assert fluxerr4wl_poly.unit == u.Jy

def test_telescope_information_from_different_header(example_fits_file_path):
    readout = ReadoutFits(example_fits_file_path)
    station_names, station_indices,\
            station_indices4baselines,\
            station_indices4triangles = readout.get_telescope_information()
    station_indices_from_visibilities = readout.get_data("oi_vis", "sta_index")[0]
    station_indices_from_visibilities_squared = readout.\
            get_data("oi_vis2", "sta_index")[0]

    assert np.all(station_indices_from_visibilities ==\
            station_indices_from_visibilities_squared)


################################ DataDandler - TESTS #####################################

def test_data_handler_init(example_fits_files_lists, selected_wavelengths):
    selected_wl_solo, selected_wl, _ = selected_wavelengths
    two_fits_files, three_fits_files = example_fits_files_lists
    # Note: This also tests the initalisation with one or more wavelengths
    data_handler_two = DataHandler(two_fits_files, selected_wl_solo)
    data_handler_three = DataHandler(three_fits_files, selected_wl)
    assert len(data_handler_two.readout_files) == 2
    assert len(data_handler_three.readout_files) == 3

def test_get_data_type_function(example_fits_files_lists, selected_wavelengths):
    selected_wl_solo, selected_wl, _ = selected_wavelengths
    two_fits_files, _ = example_fits_files_lists
    data_handler = DataHandler(two_fits_files, selected_wl)
    readout = data_handler.readout_files[0]
    assert readout.get_visibilities4wavelength ==\
        data_handler._get_data_type_function(readout, "vis")
    assert readout.get_visibilities_squared4wavelength ==\
        data_handler._get_data_type_function(readout, "vis2")
    assert readout.get_closure_phases4wavelength ==\
        data_handler._get_data_type_function(readout, "cphases")
    assert readout.get_flux4wavelength ==\
        data_handler._get_data_type_function(readout, "flux")

def test_iterate_over_data_arrays(example_fits_files_lists, selected_wavelengths):
    selected_wl_solo, selected_wl, selected_wl_multi = selected_wavelengths
    two_fits_files, three_fits_files = example_fits_files_lists
    len_selected_wl, len_selected_wl_multi = len(selected_wl), len(selected_wl_multi)
    # Note: This also tests the initalisation with one or more wavelengths
    data_handler_two_solo = DataHandler(two_fits_files, selected_wl_solo)
    data_handler_two = DataHandler(two_fits_files, selected_wl)
    data_handler_two_multi = DataHandler(two_fits_files, selected_wl_multi)

    visdata_solo = data_handler_two_solo.readout_files[0].\
        get_visibilities4wavelength(data_handler_two_solo.wl_ind)
    visdata = data_handler_two.readout_files[0].\
        get_visibilities4wavelength(data_handler_two.wl_ind)
    visdata_multi = data_handler_two_multi.readout_files[0].\
        get_visibilities4wavelength(data_handler_two_multi.wl_ind)
    merged_data_vis_solo = data_handler_two_solo.\
        _iterate_over_data_arrays(visdata_solo, visdata_solo.copy())
    merged_data_vis = data_handler_two._iterate_over_data_arrays(visdata, visdata.copy())
    merged_data_vis_multi = data_handler_two_multi.\
        _iterate_over_data_arrays(visdata_multi, visdata_multi.copy())

    cphasesdata_solo = data_handler_two_solo.readout_files[0].\
        get_closure_phases4wavelength(data_handler_two_solo.wl_ind)
    cphasesdata = data_handler_two.readout_files[0].\
        get_closure_phases4wavelength(data_handler_two.wl_ind)
    cphasesdata_multi = data_handler_two_multi.readout_files[0].\
        get_closure_phases4wavelength(data_handler_two_multi.wl_ind)
    merged_data_cphases_solo = data_handler_two_solo.\
        _iterate_over_data_arrays(cphasesdata_solo, cphasesdata_solo.copy())
    merged_data_cphases = data_handler_two.\
        _iterate_over_data_arrays(cphasesdata, cphasesdata.copy())
    merged_data_cphases_multi = data_handler_two_multi.\
        _iterate_over_data_arrays(cphasesdata_multi, cphasesdata_multi.copy())

    fluxdata_solo = data_handler_two_solo.readout_files[0].\
        get_flux4wavelength(data_handler_two_solo.wl_ind)
    fluxdata = data_handler_two.readout_files[0].\
        get_flux4wavelength(data_handler_two.wl_ind)
    fluxdata_multi = data_handler_two_multi.readout_files[0].\
        get_flux4wavelength(data_handler_two_multi.wl_ind)
    merged_data_fluxdata_solo = data_handler_two_solo.\
        _iterate_over_data_arrays(fluxdata_solo, fluxdata_solo.copy())
    merged_data_fluxdata = data_handler_two.\
        _iterate_over_data_arrays(fluxdata, fluxdata.copy())
    merged_data_fluxdata_multi = data_handler_two_multi.\
        _iterate_over_data_arrays(fluxdata_multi, fluxdata_multi.copy())

    assert merged_data_vis_solo[0].shape == (1, 12)
    assert merged_data_vis_solo[1].shape == (1, 12)
    assert merged_data_vis[0].shape == (len_selected_wl, 12)
    assert merged_data_vis[1].shape == (len_selected_wl, 12)
    assert merged_data_vis_multi[0].shape == (len_selected_wl_multi, 12)
    assert merged_data_vis_multi[1].shape == (len_selected_wl_multi, 12)

    assert merged_data_cphases_solo[0].shape == (1, 8)
    assert merged_data_cphases_solo[1].shape == (1, 8)
    assert merged_data_cphases[0].shape == (len_selected_wl, 8)
    assert merged_data_cphases[1].shape == (len_selected_wl, 8)
    assert merged_data_cphases_multi[0].shape == (len_selected_wl_multi, 8)
    assert merged_data_cphases_multi[1].shape == (len_selected_wl_multi, 8)

    assert merged_data_fluxdata_solo[0].shape == (1, 2)
    assert merged_data_fluxdata_solo[1].shape == (1, 2)
    assert merged_data_fluxdata[0].shape == (len_selected_wl, 2)
    assert merged_data_fluxdata[1].shape == (len_selected_wl, 2)
    assert merged_data_fluxdata_multi[0].shape == (len_selected_wl_multi, 2)
    assert merged_data_fluxdata_multi[1].shape == (len_selected_wl_multi, 2)

def test_merge_data(example_fits_files_lists, selected_wavelengths):
    selected_wl_solo, selected_wl, selected_wl_multi = selected_wavelengths
    two_fits_files, three_fits_files = example_fits_files_lists
    data_handler_two_solo = DataHandler(two_fits_files, selected_wl_solo)
    data_handler_two = DataHandler(three_fits_files, selected_wl)
    data_handler_three_solo = DataHandler(three_fits_files, selected_wl_solo)
    data_handler_three = DataHandler(three_fits_files, selected_wl)
    assert data_handler_two_solo.merge_data("vis")[0].shape == (2, 12)
