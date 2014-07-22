'''
@class Wakefields
@author Hannes Bartosik & Kevin Li & Giovanni Rumolo & Michael Schenk
@date March 2014
@Class for creation and management of wakefields from impedance sources
@copyright CERN
'''
from __future__ import division

from abc import ABCMeta, abstractmethod
import numpy as np
from scipy.constants import c, e
from scipy.constants import physical_constants


sin = np.sin
cos = np.cos


class WakeSources(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def wake_functions(self):
        pass


def BB_Resonator_Circular(R_shunt, frequency, Q, slices):
    return BB_Resonator_transverse(R_shunt, frequency, Q,
                                   Yokoya_X1=1, Yokoya_Y1=1, Yokoya_X2=0, Yokoya_Y2=0, Yokoya_ZZ=0)


def BB_Resonator_ParallelPlates(R_shunt, frequency, Q, slices):
    return BB_Resonator_transverse(R_shunt, frequency, Q,
                                   Yokoya_X1=np.pi**2/24, Yokoya_Y1=np.pi**2/12,
                                   Yokoya_X2=-np.pi**2/24, Yokoya_Y2=np.pi**2/24, Yokoya_ZZ=0)


class Resonator(WakeSources):

    def __init__(self, R_shunt, frequency, Q,
                 Yokoya_X1=1, Yokoya_Y1=1, Yokoya_X2=0, Yokoya_Y2=0, Yokoya_ZZ=0):

        assert(len(R_shunt) == len(frequency) == len(Q))

        self.R_shunt = R_shunt
        self.frequency = frequency
        self.Q = Q
        # self.R_shunt = np.array([R_shunt]).flatten()
        # self.frequency = np.array([frequency]).flatten()
        # self.Q = np.array([Q]).flatten()

        self.Yokoya_X1 = Yokoya_X1
        self.Yokoya_Y1 = Yokoya_Y1
        self.Yokoya_X2 = Yokoya_X2
        self.Yokoya_Y2 = Yokoya_Y2
        self.Yokoya_ZZ = Yokoya_ZZ

    def wake_functions(self):

        wake_dict = {}

        if self.Yokoya_X1:
            wake_dict['dipole_xx'] = self.Yokoya_X1 * self.function_total(self.function_transverse)
        if self.Yokoya_Y1:
            wake_dict['dipole_yy'] = self.Yokoya_Y1 * self.function_total(self.function_transverse)
        if self.Yokoya_X2:
            wake_dict['quadrupole_x'] = self.Yokoya_X2 * self.function_total(self.function_transverse)
        if self.Yokoya_Y2:
            wake_dict['quadrupole_y'] = self.Yokoya_Y2 * self.function_total(self.function_transverse)
        if self.Yokoya_ZZ:
            wake_dict['longitudinal'] = self.Yokoya_ZZ * self.function_total(self.function_longitudinal)

        return wake_dict

    def function_transverse(self, R_shunt, frequency, Q):

        # Taken from Alex Chao's resonator model (2.82)
        omega = 2 * np.pi * self.frequency
        alpha = omega / (2 * self.Q)
        omegabar = np.sqrt(np.abs(omega**2 - alpha**2))

        # Taken from definition in HEADTAIL
        def wake(beta, z):

            t = z.clip(max=0) / (beta*c)
            if self.Q > 0.5:
                y =  self.R_shunt * omega**2 / (self.Q*omegabar) * np.exp(alpha*t) * sin(omegabar*t)
            elif self.Q == 0.5:
                y =  self.R_shunt * omega**2 / self.Q * np.exp(alpha*t) * t
            else:
                y =  self.R_shunt * omega**2 / (self.Q*omegabar) * np.exp(alpha*t) * np.sinh(omegabar*t)
            return y

        return wake

    def function_longitudinal(self, R_shunt, frequency, Q):

        # Taken from Alex Chao's resonator model (2.82)
        omega = 2 * np.pi * frequency
        alpha = omega / (2 * Q)
        omegabar = np.sqrt(np.abs(omega ** 2 - alpha ** 2))

        def wake(beta, z):

            t = z.clip(max=0) / (beta*c)
            if Q > 0.5:
                y =  - (np.sign(z)-1) * R_shunt * alpha * np.exp(alpha*t) * (cos(omegabar*t)
                                                                            + alpha/omegabar * sin(omegabar*t))
            elif Q == 0.5:
                y =  - (np.sign(z)-1) * R_shunt * alpha * np.exp(alpha*t) * (1. + alpha*t)
            elif Q < 0.5:
                y =  - (np.sign(z)-1) * R_shunt * alpha * np.exp(alpha*t) * (np.cosh(omegabar*t)
                                                                            + alpha/omegabar * np.sinh(omegabar*t))
            return y

        return wake

    def function_total(self, function_single):
        return reduce(lambda x, y: x + y,
                      [self.function_single(self.R_shunt[i], self.frequency[i], self.Q[i]) for i in np.arange(len(self.Q))])

    def memo(self, fn):
        cache = {}
        def call(*args):
            if args not in cache:
                cache[args] = fn(*args)

            return cache[args]

        return call

    def dipole_wake_x_memo(self, bunch, z):
        wake_partial = partial(self.wake_transverse, bunch)
        wake_transverse = self.memo(wake_partial)
        z_shape = z.shape
        W = np.array(map(wake_transverse, z.flatten())).reshape(z_shape)
        return self.Yokoya_X1 * W#wake_transverse(bunch, z)


def Resistive_wall_Circular(pipe_radius, length_resistive_wall, conductivity=5.4e17, dz_min=1e-4):
    return Resistive_wall_transverse(pipe_radius, length_resistive_wall, conductivity, dz_min,
                                     Yokoya_X1=1, Yokoya_Y1=1, Yokoya_X2=0, Yokoya_Y2=0, Yokoya_ZZ=0)


def Resistive_wall_ParallelPlates(pipe_radius, length_resistive_wall, conductivity=5.4e17, dz_min=1e-4):
    return BB_Resonator_transverse(pipe_radius, length_resistive_wall, conductivity, dz_min,
                                   Yokoya_X1=np.pi**2/24, Yokoya_Y1=np.pi**2/12,
                                   Yokoya_X2=-np.pi**2/24, Yokoya_Y2=np.pi**2/24, Yokoya_ZZ=0)


class ResistiveWall(WakeSources):

    def __init__(self, pipe_radius, resistive_wall_length, conductivity=5.4e17, dz_min= 1e-4,
                 Yokoya_X1=1, Yokoya_Y1=1, Yokoya_X2=0, Yokoya_Y2=0):

        self.pipe_radius = np.array([pipe_radius]).flatten()
        self.resistive_wall_length = resistive_wall_length
        self.conductivity = conductivity
        self.dz_min = dz_min

        self.Yokoya_X1 = Yokoya_X1
        self.Yokoya_Y1 = Yokoya_Y1
        self.Yokoya_X2 = Yokoya_X2
        self.Yokoya_Y2 = Yokoya_Y2

    def wake_functions(self):

        wake_dict = {}

        if self.Yokoya_X1:
            wake_dict['dipole_x'] = self.Yokoya_X1 * self.function_transverse
        if self.Yokoya_Y1:
            wake_dict['dipole_y'] = self.Yokoya_Y1 * self.function_transverse
        if self.Yokoya_X2:
            wake_dict['quadrupole_x'] = self.Yokoya_X2 * self.function_transverse
        if self.Yokoya_Y2:
            wake_dict['quadrupole_y'] = self.Yokoya_Y2 * self.function_transverse

        return wake_dict

    def function_transverse(self, bunch, z):

        Z0 = physical_constants['characteristic impedance of vacuum'][0]
        lambda_s = 1. / (Z0*self.conductivity)
        mu_r = 1

        wake = (np.sign(z + np.abs(self.dz_min)) - 1) / 2 * bunch.beta * c
             * Z0 * self.length_resistive_wall / np.pi / self.pipe_radius ** 3
             * np.sqrt(-lambda_s * mu_r / np.pi / z.clip(max=-abs(self.dz_min)))

        return wake


class Wake_table(Wakefields):

    def __init__(self, wake_file, keys):

        Wakefields.__init__(self, slices)
        table = np.loadtxt(wake_file, delimiter="\t")
        self.wake_table = dict(zip(keys, np.array(zip(*table))))
        self.unit_conversion()

    def unit_conversion(self):
        transverse_wakefield_keys   = ['dipolar_x', 'dipolar_y', 'quadrupolar_x', 'quadrupolar_y']
        longitudinal_wakefield_keys = ['longitudinal']
        self.wake_field_keys = []
        print 'Converting wake table to correct units ... '
        self.wake_table['time'] *= 1e-9 # unit convention [ns]
        print '\t converted time from [ns] to [s]'
        for wake in transverse_wakefield_keys:
            try:
                self.wake_table[wake] *= - 1.e15 # unit convention [V/pC/mm] and sign convention !!
                print '\t converted "' + wake + '" wake from [V/pC/mm] to [V/C/m] and inverted sign'
                self.wake_field_keys += [wake]
            except:
                print '\t "' + wake + '" wake not provided'
        for wake in longitudinal_wakefield_keys:
            try:
                self.wake_table[wake] *= - 1.e12 # unit convention [V/pC] and sign convention !!
                print '\t converted "' + wake + '" wake from [V/pC] to [V/C]'
                self.wake_field_keys += [wake]
            except:
                print '\t "' + wake + '" wake not provided'

    #~ @profile
    def wake_transverse(self, key, bunch, z):
        time = np.array(self.wake_table['time'])
        wake = np.array(self.wake_table[key])
        # insert zeros at origin if wake functions at (or below) zero not provided
        if time[0] > 0:
            time = np.append(0, time)
            wake = np.append(0, wake)
        # insert zero value of wake field if provided wake begins with a finite value
        if wake[0] != 0:
            wake = np.append(0, wake)
            time = np.append(time[0] - np.diff(time[1], time[0]), time)
        return np.interp(- z / c / bunch.beta, time, wake, left=0, right=0)


    def dipole_wake_x(self, bunch, z):
        if 'dipolar_x' in self.wake_field_keys: return self.wake_transverse('dipolar_x', bunch, z)
        return 0

    def dipole_wake_y(self, bunch, z):
        if 'dipolar_y' in self.wake_field_keys: return self.wake_transverse('dipolar_y', bunch, z)
        return 0

    def quadrupole_wake_x(self, bunch, z):
        if 'quadrupolar_x' in self.wake_field_keys: return self.wake_transverse('quadrupolar_x', bunch, z)
        return 0

    def quadrupole_wake_y(self, bunch, z):
        if 'quadrupolar_y' in self.wake_field_keys: return self.wake_transverse('quadrupolar_y', bunch, z)
        return 0

    def wake_longitudinal(self, bunch, z):
        time = np.array(self.wake_table['time'])
        wake = np.array(self.wake_table['longitudinal'])
        wake_interpolated = np.interp(- z / c / bunch.beta, time, wake, left=0, right=0)
        if time[0] < 0:
            return wake_interpolated
        elif time[0] == 0:
            # beam loading theorem: half value of wake at z=0;
            return (np.sign(-z) + 1) / 2 * wake_interpolated

    def track(self, bunch):
        if not self.slices:
            self.slices = bunch.slices

        # bunch.compute_statistics()
        self.slices.update_slices(bunch)
        self.slices.compute_statistics(bunch)

        if ('dipolar_x' or 'quadrupolar_x') in self.wake_field_keys:
            wakefield_kicks_x = self.transverse_wakefield_kicks('x')
            wakefield_kicks_x(bunch)
        if ('dipolar_y' or 'quadrupolar_y') in self.wake_field_keys:
            wakefield_kicks_y = self.transverse_wakefield_kicks('y')
            wakefield_kicks_y(bunch)
        if 'longitudinal' in self.wake_field_keys:
            self.longitudinal_wakefield_kicks(bunch)