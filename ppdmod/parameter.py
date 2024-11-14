from dataclasses import dataclass
from typing import Any, Union

import astropy.units as u
import numpy as np
from numpy.typing import ArrayLike

from .options import STANDARD_PARAMETERS
from .utils import smooth_interpolation


# TODO: Write template functionality
@dataclass()
class Parameter:
    """Defines a parameter."""

    name: str | None = None
    value: Any | None = None
    unit: u.Quantity | None = None
    shortname: str | None = None
    free: bool | None = None
    description: str | None = None
    min: float | None = None
    max: float | None = None
    dtype: type | None = None
    grid: np.ndarray | None = None
    smooth: bool | None = None
    base: str | None = None

    def __setattr__(self, key: str, value: Any):
        """Sets an attribute."""
        if key != "unit":
            if isinstance(value, u.Quantity):
                value = value.value
        super().__setattr__(key, value)

    def __post_init__(self):
        """Post initialisation actions."""
        self.value = self._set_to_numpy_array(self.value)
        self.grid = self._set_to_numpy_array(self.grid)
        self._process_base(self.base)

    def _process_base(self, base: str | None) -> None:
        """Process the template attribute."""
        if base is None:
            return

        for key, value in getattr(STANDARD_PARAMETERS, base).items():
            if getattr(self, key) is None:
                setattr(self, key, value)

        if self.smooth is None:
            self.smooth = False

        if self.free is None:
            self.free = False

    def __call__(self, points: u.Quantity | None = None) -> np.ndarray:
        """Gets the value for the parameter or the corresponding
        values for some points."""
        if points is None or self.grid is None:
            value = self.value
        else:
            if self.smooth:
                value = smooth_interpolation(points.value, self.grid, self.value)
            else:
                value = np.interp(points.value, self.grid, self.value)

        return u.Quantity(value, unit=self.unit, dtype=self.dtype)

    def __str__(self):
        message = (
            f"Parameter: {self.name} has the value "
            f"{np.round(self.value, 2)} and "
            f"is {'free' if self.free else 'fixed'}"
        )
        if self.max is not None:
            message += f" with its limits being {self.min:.1f}-{self.max:.1f}"
        return message

    def _set_to_numpy_array(
        self, array: ArrayLike | None = None, retain_value: bool = False
    ) -> Union[Any, np.ndarray]:
        """Converts a value to a numpy array."""
        if array is None:
            return

        if isinstance(array, u.Quantity) and retain_value:
            return array

        if not isinstance(array, np.ndarray):
            if isinstance(array, (tuple, list)):
                return np.array(array)

        return array

    # TODO: One can make this modular, maybe cool for oimodeler?
    def set(self, min: float | None = None, max: float | None = None) -> None:
        """Sets the limits of the parameters."""
        self.min, self.max = min, max
