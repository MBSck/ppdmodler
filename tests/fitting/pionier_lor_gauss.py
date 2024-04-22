import os
from typing import List
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import astropy.units as u
import numpy as np
from ppdmod import data
from ppdmod import plot
from ppdmod.basic_components import assemble_components
from ppdmod.fitting import compute_observable_chi_sq, compute_observables, \
    set_params_from_theta, lnprior, run_fit, get_best_fit, transform_uniform_prior
from ppdmod.parameter import Parameter
from ppdmod.options import STANDARD_PARAMETERS, OPTIONS
from ppdmod.utils import compute_photometric_slope


def ptform(theta: List[float]) -> np.ndarray:
    """Transform that constrains the first two parameters to 1 for dynesty."""
    params = transform_uniform_prior(theta)
    params[1] = params[1]*(1-params[0])
    return params


def lnprob(theta: np.ndarray) -> float:
    """Takes theta vector and the x, y and the yerr of the theta.
    Returns a number corresponding to how good of a fit the model is to your
    data for a given set of parameters, weighted by the data points.

    This is the analytical 1D implementation.

    Constraints the parameters to 1 for emcee.

    Parameters
    ----------
    theta: np.ndarray
        The parameters that ought to be fitted.

    Returns
    -------
    float
        The log of the probability.
    """
    parameters, shared_params = set_params_from_theta(theta)
    if parameters[0][1]["fs"] + parameters[0][1]["fc"] > 1:
        return -np.inf

    if OPTIONS.fit.method == "emcee":
        if np.isinf(lnprior(parameters, shared_params)):
            return -np.inf

    components = assemble_components(parameters, shared_params)
    return compute_observable_chi_sq(*compute_observables(components))


DATA_DIR = Path("../data/pionier/nChannels3")
OPTIONS.model.output = "non-physical"
fits_files = list((DATA_DIR).glob("*fits"))
data.set_data(fits_files, wavelengths="all", fit_data=["vis2"])

pa = Parameter(**STANDARD_PARAMETERS.pa)
pa.value = 162
pa.free = True

inc = Parameter(**STANDARD_PARAMETERS.inc)
inc.value = 0.5
inc.free = True

fc = Parameter(**STANDARD_PARAMETERS.fr)
fc.value = 0.54
fc.free = True

fs = Parameter(**STANDARD_PARAMETERS.fr)
fs.value = 0.44
fs.free = True

wavelength = data.get_all_wavelengths()
ks = Parameter(**STANDARD_PARAMETERS.exp)
ks.value = compute_photometric_slope(wavelength, 7500*u.K)
ks.wavelength = wavelength
ks.free = False

kc = Parameter(**STANDARD_PARAMETERS.exp)
kc.value = -3.64
kc.set(min=-20, max=20)

fwhm = Parameter(**STANDARD_PARAMETERS.fwhm)
fwhm.value = 2.14
fwhm.set(min=0.1, max=32)

flor = Parameter(**STANDARD_PARAMETERS.fr)
flor.value = 0.41
flor.free = True

params = {"fs": fs, "fc": fc, "flor": flor,
          "fwhm": fwhm, "kc": kc, "inc": inc, "pa": pa}
labels = [label for label in params]

OPTIONS.model.constant_params = {"wl0": 1.68, "ks": ks}
OPTIONS.model.components_and_params = [["StarHaloGaussLor", params]]
OPTIONS.fit.method = "dynesty"

result_dir = Path("results/pionier")
result_dir.mkdir(exist_ok=True, parents=True)
model_name = "starHaloGaussLor"

components = assemble_components(
        OPTIONS.model.components_and_params,
        OPTIONS.model.shared_params)

rchi_sq = compute_observable_chi_sq(
        *compute_observables(components), reduced=True)
print(f"rchi_sq: {rchi_sq}")

plot.plot_overview(savefig=result_dir / f"{model_name}_data_overview.pdf")
plot.plot_fit(components[0].inc(), components[0].pa(), components=components,
              savefig=result_dir / f"{model_name}_pre_fit_results.pdf")

if __name__ == "__main__":
    ncores = None
    fit_params_emcee = {"nburnin": 2000, "nsteps": 8000, "nwalkers": 100,
                        "lnprob": lnprob}
    fit_params_dynesty = {"nlive": 1500, "sample": "rwalk", "bound": "multi",
                          "ptform": ptform}

    if OPTIONS.fit.method == "emcee":
        fit_params = fit_params_emcee
        ncores = fit_params["nwalkers"]//2 if ncores is None else ncores
        fit_params["discard"] = fit_params["nburnin"]
    else:
        ncores = 50 if ncores is None else ncores
        fit_params = fit_params_dynesty

    sampler = run_fit(**fit_params, ncores=ncores,
                      save_dir=result_dir, debug=False)

    theta, uncertainties = get_best_fit(
            sampler, **fit_params, method="quantile")

    components_and_params, shared_params = set_params_from_theta(theta)
    components = assemble_components(components_and_params, shared_params)
    rchi_sq = compute_observable_chi_sq(
            *compute_observables(components), reduced=True)
    print(f"rchi_sq: {rchi_sq}")

    plot.plot_chains(sampler, labels, **fit_params,
                     savefig=result_dir / f"{model_name}_chains.pdf")
    plot.plot_corner(sampler, labels, **fit_params,
                     savefig=result_dir / f"{model_name}_corner.pdf")
    plot.plot_fit(components[0].inc(), components[0].pa(), components=components,
                  savefig=result_dir / f"{model_name}_fit_results.pdf")
