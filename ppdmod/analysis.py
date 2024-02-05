from datetime import datetime
from typing import Optional, Any, Dict, List
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS

from .component import Component
from .options import OPTIONS


def save_fits(dim: int, pixel_size: u.mas,
              distance: u.pc,
              components: List[Component],
              component_labels: List[str],
              wavelength: Optional[u.um] = None,
              opacities: List[np.ndarray] = None,
              savefits: Optional[Path] = None,
              object_name: Optional[str] = None,
              nwalkers: Optional[int] = None,
              nsteps: Optional[int] = None,
              ncores: Optional[int] = None) -> None:
    """Saves a (.fits)-file of the model with all the information on the
    parameter space."""
    pixel_size = u.Quantity(pixel_size, u.mas)
    wavelength = u.Quantity(wavelength, u.um) if wavelength is not None\
        else OPTIONS.fit.wavelengths
    distance = u.Quantity(distance, u.pc)

    image = np.empty((wavelength.size, dim, dim))*u.Jy
    for component in components:
        image += component.calculate_image(dim, pixel_size, wavelength)
    breakpoint()

    tables = []
    for index, component in enumerate(components):
        table_header = fits.Header()

        table_header["COMP"] = component.name
        table_header["GRIDTYPE"] = (OPTIONS.model.gridtype,
                                    "The type of the model grid")

        data = {"wavelength": wavelength}
        if component.name != "Star":
            radius = component.calculate_internal_grid(dim)

            data["radius"] = [radius]*wavelength.size
            data["temperature"] = [component.calculate_temperature(radius)]\
                * wavelength.size
            data["surface_density"] = [component.calculate_surface_density(radius)]\
                * wavelength.size

            data["flux"] = component.calculate_flux(wavelength)
            data["emissivity"] = component.calculate_emissivity(radius, wavelength)
            data["brightness"] = component.calculate_brightness(radius, wavelength)

        for wavelength in wavelength:
            for parameter in component.params.values():
                if parameter.wavelength is None:
                    name = parameter.shortname.upper()
                    if name not in table_header:
                        description = f"[{parameter.unit}] {parameter.description}"
                        table_header[name] = (parameter().value, description)
                else:
                    if parameter.name not in data:
                        data[parameter.name] = [parameter(wavelength).value]
                    else:
                        data[parameter.name].append(parameter(wavelength).value)

        table = fits.BinTableHDU(
                Table(data=data),
                name="_".join(component_labels[index].split(" ")).upper(),
                header=table_header)
        tables.append(table)

    data = None
    for table in tables:
        if table.header["COMP"] == "Star":
            continue
        if data is None:
            data = {col.name: table.data[col.name] for col in table.columns}
            continue
        for column in table.columns:
            # TODO: Make calculation work for total flux
            if column.name in ["wavelength", "kappa_abs", "kappa_cont", "flux"]:
                continue
            if column.name == "radius":
                filler = np.tile(
                        np.linspace(data[column.name][0][-1], table.data[column.name][0][0], dim),
                        (table.data[column.name].shape[0], 1))
            else:
                filler = np.zeros(data[column.name].shape)
            data[column.name] = np.hstack((data[column.name],
                                           filler, table.data[column.name]))
    table = fits.BinTableHDU(Table(data=data), name="FULL_DISK")
    tables.append(table)

    if opacities is not None:
        data = {"wavelength": opacities[0].wavelength}
        for opacity in opacities:
            data[opacity.shortname] = opacity()
        tables.append(fits.BinTableHDU(Table(data=data), name="OPACITIES"))

    wcs = WCS(naxis=3)
    wcs.wcs.crpix = (*np.array(images.shape[:2]) // 2, len(wavelength))
    wcs.wcs.cdelt = ([pixel_size.value, pixel_size.value, -1.0])
    wcs.wcs.crval = (0.0, 0.0, 1.0)
    wcs.wcs.ctype = ("RA---AIR", "DEC--AIR", "WAVELENGTHS")
    wcs.wcs.cunit = ("mas", "mas", "um")
    wcs.wcs.pc = np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]])
    header = wcs.to_header()

    header["NSTEP"] = (nsteps, "Number of steps for the fitting")
    header["NWALK"] = (nwalkers, "Numbers of walkers for the fitting")
    header["NCORE"] = (ncores, "Numbers of cores for the fitting")
    header["OBJECT"] = (object_name, "Name of the object")
    header["DATE"] = (f"{datetime.now()}", "Creation date")

    hdu = fits.HDUList([fits.PrimaryHDU(images, header=header), *tables])
    hdu.writeto(savefits, overwrite=True)
