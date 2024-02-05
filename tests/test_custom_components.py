from pathlib import Path
from typing import Dict

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import pytest

from ppdmod.component import Component
from ppdmod.custom_components import Star, GreyBody, assemble_components
from ppdmod.data import ReadoutFits
from ppdmod.options import STANDARD_PARAMETERS
from ppdmod.parameter import Parameter
from ppdmod.utils import load_data, linearly_combine_data, qval_to_opacity


DIMENSION = [2**power for power in range(9, 13)]


@pytest.fixture
def wavelength() -> u.m:
    """A wavelenght grid."""
    return [12.5]*u.um


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
def star_parameters() -> Dict[str, float]:
    """The star's parameters"""
    return {"dim": 512, "dist": 145, "eff_temp": 7800, "eff_radius": 1.8}


@pytest.fixture
def temp_gradient_parameters() -> Dict[str, float]:
    """The temperature gradient's parameters."""
    return {"rin": 0.5, "q": 0.5, 
            "inner_temp": 1500, "inner_sigma": 2000,
            "pixel_size": 0.1, "p": 0.5}


@pytest.fixture
def star(star_parameters: Dict[str, float]) -> Star:
    """Initializes a star component."""
    return Star(**star_parameters)


def test_get_component() -> Component:
    ...


def test_star_init(star: Star) -> None:
    """Tests the star's initialization."""
    assert "dist" in star.params
    assert "eff_temp" in star.params
    assert "eff_radius" in star.params


def test_star_stellar_radius_angular(star: Star) -> None:
    """Tests the stellar radius conversion to angular radius."""
    assert star.stellar_radius_angular.unit == u.mas


# TODO: include test for stellar flux with input file as well.
# TODO: Make this for multiple wavelengths
@pytest.mark.parametrize("wl, dim",
                         [(wl, dim) for dim in DIMENSION
                          for wl in [8, 9, 10, 11]*u.um])
def test_star_image(star: Star, dim: int, wl: u.um,
                    wavelength: u.um) -> None:
    """Tests the star's image calculation."""
    image = star.calculate_image(dim, 0.1*u.mas, wavelength)

    star_dir = Path("fluxes/star")
    if not star_dir.exists():
        star_dir.mkdir()

    centre = dim//2

    plt.imshow(image.value[0])
    plt.xlim(centre-20, centre+20)
    plt.ylim(centre-20, centre+20)
    plt.savefig(star_dir / f"dim{dim}_wl{wl.value}_star_image.pdf")
    plt.close()

    assert len(image[image != 0]) == 4
    assert image.shape == (1, dim, dim)
    assert image.unit == u.Jy
    assert np.max(image.value) < 0.1


def test_star_visibility_function(star: Star,
                                  wavelength: u.um) -> None:
    """Tests the star's complex visibility function calculation."""
    complex_visibility = star._visibility_function(512, 0.1*u.mas, wavelength)
    assert complex_visibility.shape == tuple(star.params["dim"]() for _ in range(2))


def test_assemble_components() -> None:
    """Tests the model's assemble_model method."""
    param_names = ["rin", "p", "a", "phi",
                   "cont_weight", "pa", "elong"]
    values = [1.5, 0.5, 0.3, 33, 0.2, 45, 1.6]
    limits = [[0, 20], [0, 1], [0, 1],
              [0, 360], [0, 1], [0, 360], [1, 50]]
    params = {name: Parameter(**STANDARD_PARAMETERS[name])
              for name in param_names}
    for value, limit, param in zip(values, limits, params.values()):
        param.set(*limit)
        param.value = value
    shared_params = {"p": params["p"]}
    del params["p"]

    components_and_params = [["Star", params],
                             ["GreyBody", params]]
    components = assemble_components(components_and_params, shared_params)
    assert isinstance(components[0], Star)
    assert isinstance(components[1], GreyBody)
    assert all(param not in components[0].params
               for param in param_names if param not in ["pa", "elong"])
    assert all(param in components[1].params for param in param_names)
    assert all(components[1].params[name].value == value
               for name, value in zip(["pa", "elong"], values[-2:]))
    assert all(components[1].params[name].value == value
               for name, value in zip(param_names, values))
    assert all([components[0].params[name].min,
                components[0].params[name].max] == limit
               for name, limit in zip(["pa", "elong"], limits[-2:]))
    assert all([components[1].params[name].min,
                components[1].params[name].max] == limit
               for name, limit in zip(param_names, limits))
