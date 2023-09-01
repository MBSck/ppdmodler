import time
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
import pytest
from astropy.modeling import models

from ppdmod import spectral
from ppdmod import utils
from ppdmod.data import ReadoutFits
from ppdmod.custom_components import NumericalComponent
from ppdmod.parameter import Parameter


RESOLUTION_FILE = Path("resolution.xlsx")
CONST_TEMPERATURE = "Constant Temperature"
TEMPERATURE_POWER = "Temperature Power Law"
AZIMUTHAL_MODULATION = "Azimuthal Modulation"
SURFACE_DENSITY = "Surface Density"
OPTICAL_THICKNESS = "Optical Thickness"
INTENSITY = "Intensity"

utils.make_workbook(
    RESOLUTION_FILE,
    {
        CONST_TEMPERATURE: ["Dimension [px]",
                            "Python Time [s]",
                            "Cython Time [s]",],
        TEMPERATURE_POWER: ["Dimension [px]",
                            "Python Time [s]",
                            "Cython Time [s]",],
        AZIMUTHAL_MODULATION: ["Dimension [px]",
                               "Python Time [s]",
                               "Cython Time [s]",],
        SURFACE_DENSITY: ["Dimension [px]",
                          "Python Time [s]",
                          "Cython Time [s]",],
        OPTICAL_THICKNESS: ["Dimension [px]",
                            "Python Time [s]",
                            "Cython Time [s]",],
        INTENSITY: ["Dimension [px]",
                    "Python Time [s]",
                    "Cython Time [s]",],
    })

DIMENSION = [2**power for power in range(7, 14)]


@pytest.fixture
def stellar_radius() -> u.Rsun:
    """The stellar radius."""
    return 1.8*u.Rsun


@pytest.fixture
def stellar_temperature() -> u.K:
    """The stellar temperature."""
    return 7800*u.K


@pytest.fixture
def distance_star() -> u.pc:
    """The distance to the star."""
    return 150*u.pc


@pytest.fixture
def inner_radius() -> u.mas:
    """The inner radius."""
    return 0.5*u.mas


@pytest.fixture
def inner_temperature() -> u.K:
    """The inner temperature."""
    return 1500*u.K


@pytest.fixture
def q() -> float:
    """The temperature power-law exponent."""
    return 0.5


@pytest.fixture
def inner_sigma() -> u.g/u.cm**2:
    """The inner surface density."""
    return 1e-3*u.g/u.cm**2


@pytest.fixture
def p() -> float:
    """The surface density power-law exponent."""
    return 0.5


@pytest.fixture
def wavelength() -> u.m:
    """A wavelenght."""
    return (13.000458e-6*u.m).to(u.um)


@pytest.fixture
def wavelength_solution() -> u.um:
    """A MATISSE (.fits)-file."""
    file = "hd_142666_2022-04-23T03_05_25:2022-04-23T02_28_06_AQUARIUS_FINAL_TARGET_INT.fits"
    return ReadoutFits(Path("data/fits") / file).wavelength


@pytest.fixture
def qval_file_dir() -> Path:
    """The qval-file directory."""
    return Path("data/qval")


@pytest.fixture
def opacity(qval_file_dir: Path,
            wavelength_solution: u.um) -> None:
    """A parameter containing the opacity."""
    weights = np.array([42.8, 9.7, 43.5, 1.1, 2.3, 0.6])/100
    qval_files = ["Q_Am_Mgolivine_Jae_DHS_f1.0_rv0.1.dat",
                  "Q_Am_Mgolivine_Jae_DHS_f1.0_rv1.5.dat",
                  "Q_Am_Mgpyroxene_Dor_DHS_f1.0_rv1.5.dat",
                  "Q_Fo_Suto_DHS_f1.0_rv0.1.dat",
                  "Q_Fo_Suto_DHS_f1.0_rv1.5.dat",
                  "Q_En_Jaeger_DHS_f1.0_rv1.5.dat"]
    qval_paths = list(map(lambda x: qval_file_dir / x, qval_files))
    opacity = utils.linearly_combine_opacities(
        weights, qval_paths, wavelength_solution)
    return Parameter(name="kappa_abs", value=opacity,
                     wavelength=wavelength_solution,
                     unit=u.cm**2/u.g, free=False,
                     description="Dust mass absorption coefficient")


def calculate_temperature_profile(
        radius: u.mas, distance: u.pc,
        stellar_radius: u.Rsun,
        stellar_temperature: u.K,
        inner_temperature: u.K,
        inner_radius: u.mas,
        q: float,
        const_temperature: bool) -> u.K:
    if const_temperature:
        radius = utils.angular_to_distance(radius, distance)
        return np.sqrt(stellar_radius.to(u.m)/(2*radius))\
            * stellar_temperature
    return inner_temperature*(radius/inner_radius)**(-q)


def calculate_azimuthal_modulation(
        xx: u.mas, yy: u.mas, a: u.one, phi: u.deg) -> None:
    """Calculation of the azimuthal modulation."""
    return a*np.cos(np.arctan2(yy, xx)-phi.to(u.rad))


def calculate_intensity(
        temp_profile: u.K, wavelength: u.um, pixel_size: u.rad) -> np.ndarray:
    """Calculate the intensity."""
    plancks_law = models.BlackBody(temperature=temp_profile)
    spectral_radiance = plancks_law(wavelength.to(u.m)).to(
        u.erg/(u.cm**2*u.Hz*u.s*u.rad**2))
    return (spectral_radiance*(pixel_size.to(u.rad))**2).to(u.Jy)


def calculate_surface_density_profile(
        radius: u.mas, inner_radius: u.mas,
        inner_sigma: u.cm**2/u.g, p: float) -> np.ndarray:
    """Calculates the surface density profile."""
    return inner_sigma*(radius/inner_radius)**(-p)


@pytest.mark.parametrize("dim", DIMENSION)
def test_calculate_const_temperature(
        dim: int, stellar_radius: u.Rsun,
        stellar_temperature: u.K, distance_star: u.pc,
        inner_temperature: u.K, inner_radius: u.mas, q: float) -> None:
    """Test the calculation of the temperature profile."""
    numerical_component = NumericalComponent(dim=dim, pixel_size=0.1)
    xx, yy = numerical_component._calculate_internal_grid()
    radius = np.hypot(xx, yy)
    stellar_radius_angular =\
        utils.distance_to_angular(stellar_radius.to(u.m), distance_star)

    cython_st = time.time()
    cython_temp = spectral.calculate_const_temperature(
        radius.value,
        stellar_radius_angular.value,
        stellar_temperature.value)
    cython_et = time.time()-cython_st

    python_st = time.time()
    python_temp = calculate_temperature_profile(
        radius, distance_star, stellar_radius,
        stellar_temperature, inner_temperature, inner_radius, q, True)
    python_et = time.time()-python_st

    data = {"Dimension [px]": [dim],
            "Python Time [s]": [python_et],
            "Cython Time [s]": [cython_et]}

    if RESOLUTION_FILE.exists():
        df = pd.read_excel(RESOLUTION_FILE, sheet_name=CONST_TEMPERATURE)
        new_df = pd.DataFrame(data)
        df = pd.concat([df, new_df])
    else:
        df = pd.DataFrame(data)
    with pd.ExcelWriter(RESOLUTION_FILE, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=CONST_TEMPERATURE, index=False)

    assert np.allclose(cython_temp, python_temp.value)


@pytest.mark.parametrize("dim", DIMENSION)
def test_calculate_temperature_power_law(
        dim: int, stellar_radius: u.Rsun,
        stellar_temperature: u.K, distance_star: u.pc,
        inner_temperature: u.K, inner_radius: u.mas, q: float) -> None:
    """Test the calculation of the temperature profile."""
    numerical_component = NumericalComponent(dim=dim, pixel_size=0.1)
    xx, yy = numerical_component._calculate_internal_grid()
    radius = np.hypot(xx, yy)

    cython_st = time.time()
    cython_temp = spectral.calculate_temperature_power_law(
        radius.value, inner_temperature.value, inner_radius.value, q)
    cython_et = time.time()-cython_st

    python_st = time.time()
    python_temp = calculate_temperature_profile(
        radius, distance_star, stellar_radius,
        stellar_temperature, inner_temperature, inner_radius, q, False)
    python_et = time.time()-python_st

    data = {"Dimension [px]": [dim],
            "Python Time [s]": [python_et],
            "Cython Time [s]": [cython_et]}

    if RESOLUTION_FILE.exists():
        df = pd.read_excel(RESOLUTION_FILE, sheet_name=TEMPERATURE_POWER)
        new_df = pd.DataFrame(data)
        df = pd.concat([df, new_df])
    else:
        df = pd.DataFrame(data)
    with pd.ExcelWriter(RESOLUTION_FILE, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=TEMPERATURE_POWER, index=False)

    assert np.array_equal(cython_temp, python_temp.value)


@pytest.mark.parametrize("dim", DIMENSION)
def test_calculate_azimuthal_modulation(dim: int) -> None:
    """Test the azimuthal modulation."""
    numerical_component = NumericalComponent(dim=dim, pixel_size=0.1)
    xx, yy = numerical_component._calculate_internal_grid()
    a, phi = 0.5*u.one, 35*u.deg

    cython_st = time.time()
    cython_mod = spectral.calculate_azimuthal_modulation(
        xx.value, yy.value, a.value, phi.to(u.rad).value)
    cython_et = time.time()-cython_st

    python_st = time.time()
    python_mod = calculate_azimuthal_modulation(xx, yy, a, phi)
    python_et = time.time()-python_st

    data = {"Dimension [px]": [dim],
            "Python Time [s]": [python_et],
            "Cython Time [s]": [cython_et]}

    if RESOLUTION_FILE.exists():
        df = pd.read_excel(RESOLUTION_FILE, sheet_name=AZIMUTHAL_MODULATION)
        new_df = pd.DataFrame(data)
        df = pd.concat([df, new_df])
    else:
        df = pd.DataFrame(data)
    with pd.ExcelWriter(RESOLUTION_FILE, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=AZIMUTHAL_MODULATION, index=False)

    assert np.array_equal(cython_mod, python_mod.value)


@pytest.mark.parametrize("dim", DIMENSION)
def test_calculate_surface_density(
        dim: int, inner_sigma: u.cm**2/u.g,
        inner_radius: u.mas, p: float) -> None:
    """Test the calculation of the surface density."""
    numerical_component = NumericalComponent(dim=dim, pixel_size=0.1)
    xx, yy = numerical_component._calculate_internal_grid()
    radius = np.hypot(xx, yy)

    cython_st = time.time()
    cython_surface = spectral.calculate_surface_density_profile(
        radius.value, inner_radius.value, inner_sigma.value, p)
    cython_et = time.time()-cython_st

    python_st = time.time()
    python_surface = calculate_surface_density_profile(
        radius, inner_radius, inner_sigma, p)
    python_et = time.time()-python_st

    data = {"Dimension [px]": [dim],
            "Python Time [s]": [python_et],
            "Cython Time [s]": [cython_et]}

    if RESOLUTION_FILE.exists():
        df = pd.read_excel(RESOLUTION_FILE, sheet_name=SURFACE_DENSITY)
        new_df = pd.DataFrame(data)
        df = pd.concat([df, new_df])
    else:
        df = pd.DataFrame(data)
    with pd.ExcelWriter(RESOLUTION_FILE, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=SURFACE_DENSITY, index=False)

    assert np.allclose(cython_surface, python_surface.value)


@pytest.mark.parametrize("dim", DIMENSION)
def test_calculate_optical_thickness(
        dim: int, inner_sigma: u.g/u.cm**2,
        inner_radius: u.mas, p: float,
        wavelength: u.um, opacity: u.cm**2/u.g) -> None:
    """Test the calculation of the optical thickness."""
    numerical_component = NumericalComponent(dim=dim, pixel_size=0.1)
    xx, yy = numerical_component._calculate_internal_grid()
    radius = np.hypot(xx, yy)
    cython_surface = spectral.calculate_surface_density_profile(
        radius.value, inner_radius.value, inner_sigma.value, p)
    python_surface = calculate_surface_density_profile(
        radius, inner_radius, inner_sigma, p)

    cython_st = time.time()
    cython_optical_thickness = spectral.calculate_optical_thickness(
        cython_surface, opacity(wavelength).value)
    cython_et = time.time()-cython_st

    python_st = time.time()
    python_optical_thickness = 1-np.exp(-python_surface*opacity(wavelength))
    python_et = time.time()-python_st

    data = {"Dimension [px]": [dim],
            "Python Time [s]": [python_et],
            "Cython Time [s]": [cython_et]}

    if RESOLUTION_FILE.exists():
        df = pd.read_excel(RESOLUTION_FILE, sheet_name=OPTICAL_THICKNESS)
        new_df = pd.DataFrame(data)
        df = pd.concat([df, new_df])
    else:
        df = pd.DataFrame(data)
    with pd.ExcelWriter(RESOLUTION_FILE, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=OPTICAL_THICKNESS, index=False)

    assert np.allclose(cython_optical_thickness,
                       python_optical_thickness.value)


@pytest.mark.parametrize("dim", DIMENSION)
def test_calculate_intensity(
        dim: int, stellar_radius: u.Rsun, wavelength: u.um,
        stellar_temperature: u.K, distance_star: u.pc,
        inner_temperature: u.K, inner_radius: u.mas, q: float) -> None:
    """Test the calculation of the intensity."""
    numerical_component = NumericalComponent(dim=dim, pixel_size=0.1)
    xx, yy = numerical_component._calculate_internal_grid()
    radius = np.hypot(xx, yy)
    stellar_radius_angular =\
        utils.distance_to_angular(stellar_radius.to(u.m), distance_star)
    cython_temp = spectral.calculate_const_temperature(
        radius.value,
        stellar_radius_angular.value,
        stellar_temperature.value)
    python_temp = calculate_temperature_profile(
        radius, distance_star, stellar_radius,
        stellar_temperature, inner_temperature, inner_radius, q, True)
    pixel_size = 0.1*u.mas

    cython_st = time.time()
    cython_intensity = spectral.calculate_intensity(
        cython_temp, wavelength.to(u.cm).value,
        pixel_size.to(u.rad).value)
    cython_et = time.time()-cython_st

    python_st = time.time()
    python_intensity = calculate_intensity(python_temp, wavelength, pixel_size)
    python_et = time.time()-python_st

    data = {"Dimension [px]": [dim],
            "Python Time [s]": [python_et],
            "Cython Time [s]": [cython_et]}

    if RESOLUTION_FILE.exists():
        df = pd.read_excel(RESOLUTION_FILE, sheet_name=INTENSITY)
        new_df = pd.DataFrame(data)
        df = pd.concat([df, new_df])
    else:
        df = pd.DataFrame(data)
    with pd.ExcelWriter(RESOLUTION_FILE, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=INTENSITY, index=False)

    assert np.allclose(cython_intensity, python_intensity.value)
