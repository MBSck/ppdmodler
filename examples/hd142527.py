import os
from datetime import datetime
from typing import List
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import astropy.units as u
import numpy as np

from ppdmod import analysis
from ppdmod import basic_components
from ppdmod import fitting
from ppdmod import utils
from ppdmod.data import set_data, get_all_wavelengths
from ppdmod.parameter import Parameter
from ppdmod.plot import plot_corner, plot_chains
from ppdmod.options import STANDARD_PARAMETERS, OPTIONS



def ptform(theta: List[float]) -> np.ndarray:
    """Transform that constrains the first two parameters to 1 for dynesty."""
    params = fitting.transform_uniform_prior(theta)
    indices = list(map(labels.index, (filter(lambda x: "rin" in x or "rout" in x, labels))))
    for count, index in enumerate(indices):
        if count == len(indices) - 1:
            break
        next_index = indices[count + 1]
        params[next_index] = params[next_index] if params[index] <= params[next_index] else params[index]

    return params


DATA_DIR = Path("../tests/data")
wavelengths = {"hband": [1.6]*u.um,
               "kband": [2.25]*u.um,
               "lband": [3.2]*u.um,
               "mband": [4.7]*u.um,
               "nband": [8., 9., 10., 11.3, 12.5]*u.um}

OPTIONS.model.output = "non-normed"
fits_files = list((DATA_DIR / "fits" / "hd142527").glob("*fits"))
wavelength = np.concatenate((wavelengths["lband"], wavelengths["mband"], wavelengths["nband"]))
# wavelength = wavelengths["lband"]
data = set_data(fits_files, wavelengths=wavelength, fit_data=["flux", "vis"])

all_wavelengths = get_all_wavelengths()
wl_flux, flux = utils.load_data(DATA_DIR / "flux" / "hd142527" / "HD142527_stellar_model.txt")
star_flux = Parameter(**STANDARD_PARAMETERS.f)
star_flux.wavelength, star_flux.value = wl_flux, flux

weights = np.array([73.2, 8.6, 0.6, 14.2, 2.4, 1.0])/100
names = ["pyroxene", "forsterite", "enstatite", "silica"]
# fmaxs = [1.0, 1.0, 1.0, None]
sizes = [[1.5], [0.1], [0.1, 1.5], [0.1, 1.5]]

wl_opacity, opacity = utils.get_opacity(
    DATA_DIR, weights, sizes, names, "boekel")

cont_opacity_file = DATA_DIR / "qval" / "Q_amorph_c_rv0.1.dat"
# cont_opacity_file = DATA_DIR / "qval" / "Q_iron_0.10um_dhs_0.7.dat",
wl_cont, cont_opacity = utils.load_data(cont_opacity_file, load_func=utils.qval_to_opacity)

kappa_abs = Parameter(**STANDARD_PARAMETERS.kappa_abs)
kappa_abs.value, kappa_abs.wavelength = opacity, wl_opacity
kappa_cont = Parameter(**STANDARD_PARAMETERS.kappa_cont)
kappa_cont.value, kappa_cont.wavelength = cont_opacity, wl_cont

dim, distance, eff_temp = 32, 158.51, 6500
eff_radius = utils.compute_stellar_radius(10**1.35, eff_temp).value
OPTIONS.model.constant_params = {
    "dim": dim, "dist": distance,
    "f": star_flux, "kappa_abs": kappa_abs,
    "eff_temp": eff_temp, "eff_radius": eff_radius,
    "kappa_cont": kappa_cont}

x = Parameter(**STANDARD_PARAMETERS.x)
y = Parameter(**STANDARD_PARAMETERS.y)
x.free = y.free = True
# star = {"x": x, "y": y}
star = {}
star_labels = [f"st_{label}" for label in star]

rin = Parameter(**STANDARD_PARAMETERS.rin)
rout = Parameter(**STANDARD_PARAMETERS.rout)
p = Parameter(**STANDARD_PARAMETERS.p)
sigma0 = Parameter(**STANDARD_PARAMETERS.sigma0)
c1 = Parameter(**STANDARD_PARAMETERS.c)
s1 = Parameter(**STANDARD_PARAMETERS.s)
cont_weight = Parameter(**STANDARD_PARAMETERS.cont_weight)

rin.value = 1.
rout.value = 3.
sigma0.value = 1e-3
p.value = 0.5
c1.value = s1.value = 0.5
cont_weight.value = 0.40             # Relative contribution (adds to 1). Mass fractions

rin.set(min=0, max=30)
rout.set(min=0, max=30)
rout.free = True
p.set(min=-10, max=10)
cont_weight.set(min=0, max=1)

# inner_ring = {"rin": rin, "rout": rout, "c1": c1, "s1": s1,
#               "sigma0": sigma0, "p": p}
inner_ring = {"rin": rin, "rout": rout, "p": p, "sigma0": sigma0,
              "cont_weight": cont_weight}
# inner_ring = {}
inner_ring_labels = [f"ir_{label}" for label in inner_ring]

rin = Parameter(**STANDARD_PARAMETERS.rin)
rout = Parameter(**STANDARD_PARAMETERS.rout)
p = Parameter(**STANDARD_PARAMETERS.p)
sigma0 = Parameter(**STANDARD_PARAMETERS.sigma0)
c1 = Parameter(**STANDARD_PARAMETERS.c)
s1 = Parameter(**STANDARD_PARAMETERS.s)
cont_weight = Parameter(**STANDARD_PARAMETERS.cont_weight)

rin.value = 5
rout.value = 10
p.value = 0.5
sigma0.value = 1e-3
c1.value = s1.value = 0.5
cont_weight.value = 0.40             # Relative contribution (adds to 1). Mass fractions

rin.set(min=0, max=30)
rout.set(min=0, max=50)
rout.free = True
p.set(min=-20, max=20)
sigma0.set(min=0, max=1e-1)
cont_weight.set(min=0, max=1)

# outer_ring = {"rin": rin, "c1": c1, "s1": s1, "sigma0": sigma0, "p": p}
# outer_ring = {"rin": rin, "rout": rout, "p": p, "sigma0": sigma0,
#               "cont_weight": cont_weight}
outer_ring = {"rin": rin, "p": p, "sigma0": sigma0,
              "cont_weight": cont_weight}
# outer_ring = {}
outer_ring_labels = [f"or_{label}" for label in outer_ring]

rin.value = 12
p.value = 0.5
sigma0.value = 1e-3
c1.value = s1.value = 0.5
cont_weight.value = 0.40             # Relative contribution (adds to 1). Mass fractions

rin.set(min=0, max=30)
rout.set(min=0, max=50)
rout.free = True
p.set(min=-10, max=10)
sigma0.set(min=0, max=1e-1)
cont_weight.set(min=0, max=1)

last_ring = {"rin": rin, "p": p, "sigma0": sigma0,
              "cont_weight": cont_weight}
# last_ring = {}
last_ring_labels = [f"lr_{label}" for label in last_ring]

q = Parameter(**STANDARD_PARAMETERS.q)
temp0 = Parameter(**STANDARD_PARAMETERS.temp0)
pa = Parameter(**STANDARD_PARAMETERS.pa)
inc = Parameter(**STANDARD_PARAMETERS.inc)

q.value = 0.5
temp0.value = 1500
pa.value = 163
inc.value = 0.5

temp0.set(min=300, max=2000)
pa.set(min=0, max=180)
inc.set(min=0.3, max=0.95)

OPTIONS.model.shared_params = {# "q": q, "temp0": temp0,
                               "pa": pa, "inc": inc}
shared_params_labels = [f"sh_{label}" for label in OPTIONS.model.shared_params]

OPTIONS.model.components_and_params = [
    ["Star", star],
    ["GreyBody", inner_ring],
    ["GreyBody", outer_ring],
    # ["GreyBody", last_ring],
]

# labels = star_labels + inner_ring_labels + outer_ring_labels + last_ring_labels
labels = star_labels + inner_ring_labels + outer_ring_labels
labels += shared_params_labels
component_labels = ["Star", "Inner Ring", "Outer Ring", "Last Ring"]
component_labels = component_labels[:len(OPTIONS.model.components_and_params)]

OPTIONS.fit.method = "dynesty"

model_result_dir = Path("../model_results/")
day_dir = model_result_dir / str(datetime.now().date())
dir_name = f"results_model_{datetime.now().strftime('%H:%M:%S')}"
result_dir = day_dir / dir_name
result_dir.mkdir(parents=True, exist_ok=True)

components = basic_components.assemble_components(
        OPTIONS.model.components_and_params,
        OPTIONS.model.shared_params)
rchi_sq = fitting.compute_observable_chi_sq(
        *fitting.compute_observables(components), reduced=True)
print(f"rchi_sq: {rchi_sq}")

analysis.save_fits(
    components, component_labels,
    save_dir=result_dir / "pre_fit_model.fits",
    object_name="HD142527")


if __name__ == "__main__":
    ncores = None
    fit_params_emcee = {"nburnin": 2, "nsteps": 5, "nwalkers": 100}
    fit_params_dynesty = {"nlive_init": 2000, "ptform": ptform}

    if OPTIONS.fit.method == "emcee":
        fit_params = fit_params_emcee
        ncores = fit_params["nwalkers"]//2 if ncores is None else ncores
        fit_params["discard"] = fit_params["nburnin"]
    else:
        ncores = 50 if ncores is None else ncores
        fit_params = fit_params_dynesty

    sampler = fitting.run_fit(**fit_params, ncores=ncores, method="dynamic",
                              save_dir=result_dir, debug=False)

    # TODO: Check if the parameters are the same as the ones from dynesty
    theta, uncertainties = fitting.get_best_fit(
            sampler, **fit_params, method="quantile")

    components_and_params, shared_params = fitting.set_params_from_theta(theta)
    components = basic_components.assemble_components(
            components_and_params, shared_params)
    rchi_sq = fitting.compute_observable_chi_sq(
            *fitting.compute_observables(components), reduced=True)
    print(f"rchi_sq: {rchi_sq}")

    analysis.save_fits(
        components, component_labels,
        fit_hyperparameters=fit_params, ncores=ncores,
        save_dir=result_dir / "post_fit_model.fits",
        object_name="HD142527")

    plot_corner(sampler, labels, **fit_params,
                savefig=result_dir / "corner.pdf")
    plot_chains(sampler, labels, **fit_params,
                savefig=result_dir / "chains.pdf")
