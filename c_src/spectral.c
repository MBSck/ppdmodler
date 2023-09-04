#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "spectral.h"


const double c = 2.99792458e+10;  // cm/s
const double c2 = 8.98755179e+20; // cm²/s²
const double h = 6.62607015e-27;  // erg s
const double kb = 1.380649e-16;   // erg/K
const double bb_to_jy = 1.0e+23;  // Jy


double *linspace(
    float start, float stop, long long dim, double factor) {
  double step = (stop - start)/dim;
  double *linear_grid = malloc(dim*sizeof(double));
  for ( long long i = 0; i < dim; ++i ) {
    linear_grid[i] = (start + i * step) * factor;
  }
  return linear_grid;
}

double *meshgrid(double *linear_grid, long long dim, int axis) {
  double *mesh = malloc(dim*dim*sizeof(double));
  double temp = 0.0;
  for ( long long i = 0; i < dim; ++i ) {
      for ( long long j = 0; j < dim; ++j ) {
        if (axis == 0) {
          temp = linear_grid[i];
        } else {
          temp = linear_grid[j];
        }
        mesh[i*dim+j] = temp;
      }
    }
  return mesh;
}

struct Grid grid(
    long long dim, float pixel_size, float pa, float elong, int elliptic) {
  struct Grid grid;
  double *x = linspace(-0.5, 0.5, dim, dim*pixel_size);
  grid.xx = meshgrid(x, dim, 1);
  grid.yy = meshgrid(x, dim, 0);

  free(x);

  if (elliptic) {
    for ( long long i = 0; i < dim*dim; ++i) {
      grid.xx[i] = grid.xx[i]*cos(pa)-grid.yy[i]*sin(pa);
      grid.yy[i] = (grid.xx[i]*sin(pa)+grid.yy[i]*cos(pa))/elong;
    }
  }
  return grid;
}


double *radius(double *xx, double *yy, long long dim) {
  double *radius = malloc(dim*dim*sizeof(double));
  for ( long long i = 0; i < dim*dim; ++i ) {
    radius[i] = sqrt(pow(xx[i], 2) + pow(yy[i], 2));
  }
  return radius;
}


double *const_temperature(
    double *radius, float stellar_radius, float stellar_temperature, long long dim) {
  double *const_temperature = malloc(dim*dim*sizeof(double));
  for ( long long i = 0; i < dim*dim; ++i ) {
    const_temperature[i] = stellar_temperature*sqrt(stellar_radius/(2.0*radius[i]));
  }
  return const_temperature;
}

double *temperature_power_law(
    double *radius, float inner_temp, float inner_radius, float q, long long dim) {
  double *temperature_power_law = malloc(dim*dim*sizeof(double));
  for ( long long i = 0; i < dim*dim; ++i ) {
    temperature_power_law[i] = inner_temp*pow(radius[i]/inner_radius, -q);
  }
  return temperature_power_law;
}

double *surface_density_profile(
    double *radius, float inner_radius,
    float inner_sigma, float p, long long dim) {
  double *sigma_profile = malloc(dim*dim*sizeof(double));
  for ( long long i = 0; i < dim*dim; ++i ) {
    sigma_profile[i]= inner_sigma*pow(radius[i]/inner_radius, -p);
  }
  return sigma_profile;
}


double *azimuthal_modulation(
    double *xx, double *yy, double a, double phi, long long dim) {
  double *modulation = malloc(dim*dim*sizeof(double));
  for ( long long i = 0; i < dim*dim; ++i ) {
    modulation[i] = a*cos(atan2(yy[i], xx[i])-phi);
  }
  return modulation;
}


double *optical_thickness(
    double *surface_density_profile, float opacity, long long dim) {
  double *optical_thickness = malloc(dim*dim*sizeof(double));
  for ( long long i = 0; i < dim*dim; ++i ) {
    optical_thickness[i] = 1.0-exp(-surface_density_profile[i]*opacity);
  }
  return optical_thickness;
}

double bb(double temperature, double wavelength) {
  double nu = c/wavelength;   // Hz
  return (2.0*h*pow(nu, 3)/c2)*(1.0/(exp(h*nu/(kb*temperature))-1.0));
}


double *intensity(
    double *temperature_profile, double wavelength, double pixel_size, long long dim) {
  double *intensity = malloc(dim*dim*sizeof(double));
  for ( long long i = 0; i < dim*dim; ++i ) {
      intensity[i] = bb(temperature_profile[i], wavelength)*pow(pixel_size, 2)*bb_to_jy;
  }
  return intensity;
}


int main() {
  return 0;
}
