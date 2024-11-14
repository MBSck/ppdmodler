import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import List

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import astropy.units as u
import numpy as np

from ppdmod import basic_components
from ppdmod.data import set_data
from ppdmod.fitting import (
    compute_interferometric_chi_sq,
    compute_observables,
    get_best_fit,
    ptform_sequential_radii,
    run_fit,
    set_components_from_theta,
    get_theta,
)
from ppdmod.options import OPTIONS
from ppdmod.parameter import Parameter
from ppdmod.utils import load_data, qval_to_opacity


def ptform(theta: List[float]) -> np.ndarray:
    return ptform_sequential_radii(theta, LABELS)


DATA_DIR = Path(__file__).parent.parent / "data"
wavelengths = {
    "hband": [1.7] * u.um,
    "kband": [2.15] * u.um,
    "lband": np.linspace(3.1, 3.4, 6) * u.um,
    "mband": np.linspace(4.7, 4.9, 4) * u.um,
    "nband": np.linspace(8, 15, 35) * u.um,
}

fits_files = list((DATA_DIR / "fits" / "hd142527").glob("*fits"))
wavelengths = np.concatenate(
    (
        wavelengths["hband"],
        wavelengths["kband"],
        wavelengths["lband"],
        wavelengths["mband"],
        wavelengths["nband"],
    )
)
data = set_data(
    fits_files,
    wavelengths=wavelengths,
    fit_data=["flux", "vis"],
    set_std_err=["mband"],
    weights=[1, 0.07258975120604641],
)

grid, _, value = np.load(DATA_DIR / "flux" / "hd142527" / "HD142527_stellar_model.npy")
flux_star = Parameter(grid=grid, value=value, base="f")

SOURCE_DIR = DATA_DIR / "model_results" / "hd142527"

method = "grf"
grid, value = np.load(SOURCE_DIR / f"silicate_{method}_opacities.npy")
kappa_abs = Parameter(grid=value, value=value, base="kappa_abs")

grid, value = load_data(
    DATA_DIR / "opacities" / "qval" / "Q_amorph_c_rv0.1.dat", load_func=qval_to_opacity
)
kappa_cont = Parameter(grid=grid, value=value, base="kappa_cont")
pa = Parameter(value=352, free=False, base="pa")
inc = Parameter(value=0.915, free=True, base="inc")

constant_params = {
    "dim": 32,
    "dist": 158.51,
    "eff_temp": 6500,
    "eff_radius": 3.46,
    "kappa_abs": kappa_abs,
    "kappa_cont": kappa_cont,
}

with open(SOURCE_DIR / "opacity_temps.pkl", "rb") as save_file:
    temps = pickle.load(save_file)

# NOTE: Set opacity calculated temperatures
# OPTIONS.model.constant_params["weights"] = temps.weights
# OPTIONS.model.constant_params["radii"] = temps.radii
# OPTIONS.model.constant_params["matrix"] = temps.values

rin1 = Parameter(value=0.5, min=0, max=30, base="rin")
rout1 = Parameter(value=1.5, min=0, max=30, free=True, base="rout")
p1 = Parameter(value=0.5, min=-20, max=20, base="p")
sigma01 = Parameter(value=1e-3, min=0, max=1e-1, base="sigma0")
cont_weight1 = Parameter(base="cont_weight")

rin2 = Parameter(value=2, min=0, max=30, base="rin")
rout2 = Parameter(value=4, free=False, base="rout")
p2 = Parameter(value=0.5, min=-30, max=20, base="p")
sigma02 = Parameter(value=1e-3, min=0, max=1e-1, base="sigma0")
cont_weight2 = Parameter(base="cont_weight")

star = basic_components.Star(label="Star", f=flux_star, **constant_params)
inner_ring = basic_components.GreyBody(
    label="Inner Ring",
    rin=rin1,
    rout=rout1,
    p=p1,
    sigma0=sigma01,
    cont_weight=cont_weight1,
    **constant_params,
)

outer_ring = basic_components.GreyBody(
    label="Outer Ring",
    rin=rin2,
    rout=rout2,
    p=p2,
    sigma0=sigma02,
    cont_weight=cont_weight2,
    **constant_params,
)

OPTIONS.model.components = components = [star, inner_ring, outer_ring]
OPTIONS.model.shared_params = shared_params = {"inc": inc}

result_dir = Path("../model_results/") / "disc_fit"
day_dir = result_dir / str(datetime.now().date())
dir_name = f"results_model_{datetime.now().strftime('%H:%M:%S')}"
result_dir = day_dir / dir_name
result_dir.mkdir(parents=True, exist_ok=True)

ndim = get_theta(components, shared_params).size
breakpoint()

rchi_sqs = compute_interferometric_chi_sq(
    *compute_observables(components),
    ndim=ndim,
    method="linear",
    reduced=True,
)
print(f"rchi_sq: {rchi_sqs[0]:.2f}")


if __name__ == "__main__":
    ncores = 50
    fit_params = {"nlive_init": 2000, "ptform": ptform}
    sampler = run_fit(
        **fit_params, ncores=ncores, method="dynamic", save_dir=result_dir, debug=True
    )

    theta, uncertainties = get_best_fit(sampler, **fit_params)
    components_and_params, shared_params = set_components_from_theta(theta)
    components = basic_components.assemble_components(
        components_and_params, shared_params
    )

    np.save(result_dir / "theta.npy", theta)
    np.save(result_dir / "uncertainties.npy", uncertainties)
    with open(result_dir / "components.pkl", "wb") as file:
        pickle.dump(components, file)

    rchi_sqs = compute_interferometric_chi_sq(
        *compute_observables(components),
        ndim=theta.size,
        method="linear",
        reduced=True,
    )
    print(f"Total reduced chi_sq: {rchi_sqs[0]:.2f}")
