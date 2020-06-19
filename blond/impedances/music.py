
# Copyright 2014-2017 CERN. This software is distributed under the
# terms of the GNU General Public Licence version 3 (GPL Version 3),
# copied verbatim in the file LICENCE.md.
# In applying this licence, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization or
# submit itself to any jurisdiction.
# Project website: http://blond.web.cern.ch/

'''
:Authors: **Danilo Quartullo, Konstantinos Iliakis**
'''

from __future__ import division
from builtins import range, object
import numpy as np
from scipy.constants import e
import ctypes
from ..utils import bmath as bm


class Music(object):

    r"""
    Implementation of the MuSiC algorithm in C++ to calculate the exact induced 
    voltage generated by resonant modes in time domain without using slices, 
    cost = O(n). The corresponding methods in Python are kept for reference.
    The method track_classic, which calculates in time domain the
    exact voltage with the O(n^2) algorithm used in the usual voltage 
    definition, is kept just for reference. 

    Parameters
    ----------
    Beam : object
        Beam object.
    resonator : float list
        List of the resonator parameters: 
        [shunt impedance [:math:`\Omega`], angular resonant frequency [rad/s], 
        quality factor [1]].
    n_macroparticles : int
        Number of macro-particles [1].
    n_particles : float
        Beam intensity [1].
    t_rev : float
        Revolution period [s]

    Attributes
    ----------
    beam : object
        Beam object.
    R_S : float
        shunt impedance [:math:`\Omega`]
    omega_R : float
        angular resonant frequency [rad/s]
    Q : float
        quality factor [1]
    n_macroparticles : int
        Number of macro-particles [1].
    n_particles : float
        Beam intensity [1].
    alpha : float
        Definition dependent on previously defined attributes.
    omega_bar : float
        Definition dependent on previously defined attributes.
    const : float
        Definition dependent on previously defined attributes.
    induced_voltage : float array
        Output induced voltage [V] (multiplied by -1 for BLonD conventions)
    coeff1 : float
        Definition dependent on previously defined attributes.
    coeff2 : float
        Definition dependent on previously defined attributes.
    coeff3 : float
        Definition dependent on previously defined attributes.
    coeff4 : float
        Definition dependent on previously defined attributes.
    input_first_component : float
        First component of vertical array in MuSiC algorithm
    input_second_component : float
        Second component of vertical array in MuSiC algorithm
    t_rev : float
        Revolution period [s]
    last_dt: float
        Last longitudinal coordinate of the beam [s]
    array_parameters : float array
        Array gathering four attributes already defined to be used in the C++
        algorithm.

    Notes
    -----
    The energies dE of the particles in the beam object are updated after the 
    induced voltage calculation.

    See Also
    --------
    The MuSiC algorithm is described in:
    M. Migliorati, L. Palumbo, 'Multibunch and multiparticle simulation code 
    with an alternative approach to wakefield effects', Phys. Rev. ST Accel. 
    Beams 18, 2015.

    """

    def __init__(self, Beam, resonator, n_macroparticles, n_particles, t_rev):

        self.beam = Beam
        self.R_S = resonator[0]
        self.omega_R = resonator[1]
        self.Q = resonator[2]
        self.n_macroparticles = n_macroparticles
        self.n_particles = n_particles
        self.alpha = self.omega_R / (2*self.Q)
        self.omega_bar = np.sqrt(self.omega_R ** 2 - self.alpha ** 2)
        self.const = -e*self.R_S*self.omega_R * \
            self.n_particles/(self.n_macroparticles*self.Q)
        self.induced_voltage = np.zeros(len(self.beam.dt))
        self.induced_voltage[0] = self.const/2
        self.coeff1 = -self.alpha/self.omega_bar
        self.coeff2 = -self.R_S*self.omega_R/(self.Q*self.omega_bar)
        self.coeff3 = self.omega_R*self.Q/(self.R_S*self.omega_bar)
        self.coeff4 = self.alpha/self.omega_bar
        self.input_first_component = 1
        self.input_second_component = 0
        self.t_rev = t_rev
        self.last_dt = self.beam.dt[-1]
        self.array_parameters = np.array([self.input_first_component,
                                          self.input_second_component, self.t_rev, self.last_dt])

    def track_cpp(self):
        r"""
        Voltage in time domain (single-turn) using MuSiC (C++ code).
        Note: this method should also be called at turn number 1 when
        multi-turn voltage computations are needed.

        Examples
        --------
        >>> import impedances.music as musClass
        >>> from setup_cpp import libblond
        >>>  
        >>> music_cpp = musClass.Music(my_beam, [R_S, 2*np.pi*frequency_R, Q], 
        >>>                               n_macroparticles, n_particles, t_rev)
        >>> music_cpp.track_cpp()

        """
        bm.music_track(self.beam.dt, self.beam.dE, self.induced_voltage,
                       self.array_parameters, self.alpha, self.omega_bar,
                       self.const, self.coeff1, self.coeff2, self.coeff3,
                       self.coeff4)

    def track_cpp_multi_turn(self):
        r"""
        Voltage in time domain (multi-turn) using MuSiC (C++ code).
        Note: this method should be called from turn number 2 onwards when
        multi-turn voltage computations are needed..

        Examples
        --------
        >>> import impedances.music as musClass
        >>> from setup_cpp import libblond
        >>>
        >>> music_cpp = musClass.Music(my_beam, [R_S, 2*np.pi*frequency_R, Q],
        >>>                               n_macroparticles, n_particles, t_rev)
        >>> music_cpp.track_cpp()
        >>> for i in range(2, n_turns):
        >>>     music_cpp.track_cpp_multi_turn()

        """
        bm.music_track_multiturn(self.beam.dt, self.beam.dE, self.induced_voltage,
                                 self.array_parameters, self.alpha, self.omega_bar,
                                 self.const, self.coeff1, self.coeff2, self.coeff3,
                                 self.coeff4)

    def track_py(self):
        r"""
        Voltage in time domain (single-turn) using MuSiC (Python code).
        Note: this method should also be called at turn number 1 when
        multi-turn voltage computations are needed.

        Examples
        --------
        >>> import impedances.music as musClass
        >>>  
        >>> music_cpp = musClass.Music(my_beam, [R_S, 2*np.pi*frequency_R, Q], 
        >>>                               n_macroparticles, n_particles, t_rev)
        >>> music_cpp.track_py()

        """

        indices_sorted = np.argsort(self.beam.dt)
        self.beam.dt = self.beam.dt[indices_sorted]
        self.beam.dE = self.beam.dE[indices_sorted]
        self.beam.dE[0] += self.induced_voltage[0]
        self.input_first_component = 1
        self.input_second_component = 0

        for i in range(len(self.beam.dt)-1):

            time_difference = self.beam.dt[i+1]-self.beam.dt[i]

            exp_term = np.exp(-self.alpha * time_difference)
            cos_term = np.cos(self.omega_bar * time_difference)
            sin_term = np.sin(self.omega_bar * time_difference)

            product_first_component = exp_term * \
                ((cos_term+self.coeff1*sin_term)*self.input_first_component
                 + self.coeff2*sin_term*self.input_second_component)
            product_second_component = exp_term * \
                (self.coeff3*sin_term*self.input_first_component
                 + (cos_term+self.coeff4*sin_term)*self.input_second_component)

            self.induced_voltage[i+1] = self.const * \
                (0.5+product_first_component)
            self.beam.dE[i+1] += self.induced_voltage[i+1]

            self.input_first_component = product_first_component+1.0
            self.input_second_component = product_second_component

        self.last_dt = self.beam.dt[-1]

    def track_py_multi_turn(self):
        r"""
        Voltage in time domain (multi-turn) using MuSiC (Python code).
        Note: this method should be called from turn number 2 onwards when
        multi-turn voltage computations are needed..

        Examples
        --------
        >>> import impedances.music as musClass
        >>>  
        >>> music_cpp = musClass.Music(my_beam, [R_S, 2*np.pi*frequency_R, Q], 
        >>>                               n_macroparticles, n_particles, t_rev)
        >>> music_cpp.track_py()
        >>> for i in range(2, n_turns):
        >>>     music_cpp.track_py_multi_turn()

        """

        indices_sorted = np.argsort(self.beam.dt)
        self.beam.dt = self.beam.dt[indices_sorted]
        self.beam.dE = self.beam.dE[indices_sorted]
        time_difference_0 = self.beam.dt[0] + self.t_rev - self.last_dt
        exp_term = np.exp(-self.alpha * time_difference_0)
        cos_term = np.cos(self.omega_bar * time_difference_0)
        sin_term = np.sin(self.omega_bar * time_difference_0)
        product_first_component = exp_term * \
            ((cos_term+self.coeff1*sin_term)*self.input_first_component
             + self.coeff2*sin_term*self.input_second_component)
        product_second_component = exp_term * \
            (self.coeff3*sin_term*self.input_first_component
             + (cos_term+self.coeff4*sin_term)*self.input_second_component)
        self.induced_voltage[0] = self.const * \
            (0.5+product_first_component)
        self.beam.dE[0] += self.induced_voltage[0]
        self.input_first_component = product_first_component+1.0
        self.input_second_component = product_second_component

        for i in range(len(self.beam.dt)-1):

            time_difference = self.beam.dt[i+1]-self.beam.dt[i]

            exp_term = np.exp(-self.alpha * time_difference)
            cos_term = np.cos(self.omega_bar * time_difference)
            sin_term = np.sin(self.omega_bar * time_difference)

            product_first_component = exp_term * \
                ((cos_term+self.coeff1*sin_term)*self.input_first_component
                 + self.coeff2*sin_term*self.input_second_component)
            product_second_component = exp_term * \
                (self.coeff3*sin_term*self.input_first_component
                 + (cos_term+self.coeff4*sin_term)*self.input_second_component)

            self.induced_voltage[i+1] = self.const * \
                (0.5+product_first_component)
            self.beam.dE[i+1] += self.induced_voltage[i+1]

            self.input_first_component = product_first_component+1.0
            self.input_second_component = product_second_component

        self.last_dt = self.beam.dt[-1]

    def track_classic(self):
        r"""
        Voltage in time domain using the basic definition (Python code)

        """

        indices_sorted = np.argsort(self.beam.dt)
        self.beam.dt = self.beam.dt[indices_sorted]
        self.beam.dE = self.beam.dE[indices_sorted]
        self.beam.dE[0] += self.induced_voltage[0]
        self.induced_voltage[1:] = 0

        for i in range(len(self.beam.dt)-1):

            for j in range(i+1):

                time_difference = self.beam.dt[i+1]-self.beam.dt[j]
                exp_term = np.exp(-self.alpha * time_difference)
                cos_term = np.cos(self.omega_bar * time_difference)
                sin_term = np.sin(self.omega_bar * time_difference)
                self.induced_voltage[i+1] += \
                    exp_term*(cos_term+self.coeff1*sin_term)

            self.induced_voltage[i+1] = \
                self.const*(0.5+self.induced_voltage[i+1])
            self.beam.dE[i+1] += self.induced_voltage[i+1]