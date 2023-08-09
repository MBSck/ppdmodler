OPTIONS = {}

# NOTE: Data.
OPTIONS["data.readouts"] = []
OPTIONS["data.total_flux"] = []
OPTIONS["data.total_flux_error"] = []
OPTIONS["data.correlated_flux"] = []
OPTIONS["data.correlated_flux_error"] = []
OPTIONS["data.closure_phase"] = []
OPTIONS["data.closure_phase_error"] = []

# NOTE: Model. The output can either be 'surface_brightness' or ' jansky_px'
OPTIONS["model.output"] = "jansky_px"
OPTIONS["model.params"] = {}
OPTIONS["model.constant_params"] = {}

# NOTE: Fourier transform.
# TODO: Set these values to 0?
OPTIONS["fourier.padding"] = None
OPTIONS["fourier.binning"] = None
OPTIONS["fourier.backend"] = "numpy"

# NOTE: Spectrum.
OPTIONS["spectrum.coefficients"] = {
    "low": [0.10600484,  0.01502548,  0.00294806, -0.00021434],
    "high": [-8.02282965e-05,  3.83260266e-03, 7.60090459e-05, -4.30753848e-07]
}
OPTIONS["spectrum.binning"] = {"low": 7,
                               "high": 7}

# NOTE: Fitting.
OPTIONS["fit.data"] = ["flux", "vis", "t3phi"]
OPTIONS["fit.wavelengths"] = None
OPTIONS["fit.chi2.weight.total_flux"] = 1
OPTIONS["fit.chi2.weight.corr_flux"] = 1
OPTIONS["fit.chi2.weight.cphase"] = 1
