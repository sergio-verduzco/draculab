"""
spinal_units.py
The units used in the motor control model.
"""
from draculab import unit_types, synapse_types, syn_reqs  # names of models and requirements
from units.units import unit
import numpy as np

class am_pm_oscillator(unit):
    """
    An oscillator with amplitude and phase modulated by inputs.

    The outuput of the unit is the sum of a constant part and a sinusoidal part.
    Both of their amplitudes are modulated by the sum of the inputs at port 0.
    The phase of the sinusoidal part is modulated by the relative phase of the inputs
    at port 1 through a method chosen by the user. 

    The model uses 4-dimensional dynamics, so it's state at a given time is a 
    4-element array. The first element corresponds to the unit's activity, which
    comes from the sum of the constant part and the oscillating part. The second
    element corresponds to the constant part of the output. The third element
    corresponds to the phase of the oscillating part. The fourth element is a
    variable that follows the scaled sum of the inputs at port 0; this is used in
    order to obtain the derivative of those inputs without the need of two low-pass
    filters and new requirements. 

    The equations of the model look like this:
    tau_u * u'   = c' + Is*th'*cos(th) + <Is>'*sin(th)
    tau_c * c'   = Is*(1-c) + Im*c
    tau_t * th'  = w + F(u_1, ..., u_n, U)
    tau_s * <Is>'= Is - <Is>

    where: 
        u = units's activity,
        c = constant part of the unit's activity,
        th = phase of the oscillation,
        <Is> = low-pass filtered Is,
        Is = scaled sum of inputs at port 0,
        Im = scaled sum of INHIBITORY inputs at port 1,
        w = intrinsic frequency of the oscillation times tau_t,
        F = interaction function,
        n = number of inputs at port 1,
        u_j = j-th input at port 1, 
        U = unit's output normalized by its medium LPF'd value.

    There are several choices for the interaction function:
    1) input_sum:
        F = alpha*sin(Ic(t) - U(t)), where Ic is the scaled sum of inputs (each
        multiplied by its synaptic weight), normalized by its slow LPF'd value.
    2) kuramoto:
        F = (1/max(n,1))*sum_j K_j*[f(u_j, u) - f(u, u_j)], where
            K_j = weight of j-th connection at port 1,
            f(a,b) = a*sqrt(1-b**2)
        This aims to reproduce the original Kuramoto model, despite the phases
        not being communicated, but deduced from the received activities.
        It may require normalization of individual inputs (e.g. removing their 
        temporal average and dividing by that average), so it is not implemented.
    3) zero
        F = 0
    """

    def __init__(self, ID, params, network):
        """ The unit constructor.

        Args:
            ID, params, network: same as in the parent's constructor.
            In addition, params should have the following entries.
                REQUIRED PARAMETERS
                'tau_u' : Time constant for the unit's activity.
                'tau_c' : Time constant for non-oscillatory dynamics.
                'tau_t' : Time constant for oscillatory dynamics.
                'tau_s' : Time constant for the port 0 low-pass filter.
                          A small value is recommended, so the derivative
                          of the LPF'd signal is similar to the derivative
                          of the original signal.
                'omega' : intrinsic oscillation angular frequency times tau_t.
                'multidim' : the Boolean literal 'True'. This is used to indicate
                             net.create that the 'init_val' parameter may be a single
                             initial value even if it is a list.
                'F' : a string specifying which interaction function to use.
                      Options: 'zero', 'kuramoto', 'input_sum'.
                      The 'input_sum' option requires an extra parameter: 
                      'alpha' : strength of phase interactions
                If 'input_sum' is the interaction function we also require:
                'tau_slow' : time constant for the slow low-pass filter.
                Using rga synapses brings an extra required parameter:
                'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. It is 
                                  recommended to use the 'post_delay' value of the 
                                  rga synapses. 
                OPTIONAL PARAMETERS
                'n_ports' : number of input ports. Must equal 2. Defaults to 2.
        Raises:
            ValueError

        """
        params['multidim'] = True
        if len(params['init_val']) != 4:
            raise ValueError("Initial values for the am_pm_oscillator must " +
                             "consist of a 4-element array.")
        if 'n_ports' in params:
            if params['n_ports'] != 2:
                raise ValueError("am_pm_oscillator units require 2 input ports.")
        else:
            params['n_ports'] = 2
        unit.__init__(self, ID, params, network) # parent's constructor
        self.tau_u = params['tau_u']
        self.tau_c = params['tau_c']
        self.tau_t = params['tau_t']
        self.tau_s = params['tau_s']
        self.omega = params['omega']
        # you need these by default depending on the Dc update rule
        self.syn_needs.update([syn_reqs.mp_inputs, syn_reqs.lpf_slow_mp_inp_sum])
        if params['F'] == 'zero':
            self.f = lambda x : 0.
        elif params['F'] == 'input_sum':
            self.f = self.input_sum_f
            self.syn_needs.update([syn_reqs.lpf_slow, syn_reqs.mp_inputs, 
                                   syn_reqs.lpf_slow_mp_inp_sum])
        elif params['F'] == 'kuramoto':
            self.f = self.kuramoto_f
        else:
            raise ValueError('Wrong specification of the interaction function F')
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        #self.D_factor = np.exp(self.net.min_delay / self.tau_s) / (3.*self.tau_s)

    def derivatives(self, y, t):
        """ Implements the equations of the am_mp_oscillator.

        Args:
            y : list or Numpy array with the 4-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
              y[2] : th -- phase of the oscillation,
              y[3] : I0 -- LPF'd sum of port 0 inputs.
            t : time when the derivative is evaluated.
        Returns:
            4-element numpy array with state variable derivatives.
        """
        # get the input sum at each port
        I = [ np.dot(i, w) for i, w in 
              zip(self.get_mp_inputs(t), self.get_mp_weights(t)) ]
        # Obtain the derivatives
        Dc = (I[0] * (1. - y[1]) + I[1]*y[1]) / self.tau_c
        slow_I0 = self.lpf_slow_mp_inp_sum[0]
        #Dc = ( I[0]*(1. - y[1]) + (I[1] - slow_I0)*y[1] ) / self.tau_c
        #Dc = ( I[0]*(1. - y[1]) - slow_I0*y[1] ) / self.tau_c
        Dth = (self.omega + self.f(I)) / self.tau_t
        DI0 = (I[0] - y[3]) / self.tau_s
        #DI0 = (sum(self.get_mp_inputs(t)[0]) - y[3]) / self.tau_s
        #DIs = self.D_factor * (I[0] - y[3])
        #Du = (Dc + I[0]*Dth*np.cos(y[2]) + DI0*np.sin(y[2])) / self.tau_u
        ex = np.exp(-y[3]*np.sin(y[2]))
        prime = 0.5*ex/(1.+ex)
        Du = ((1.-y[0]) * y[0] * (Dc + (y[1] - y[0]) + 
               prime*(y[3]*Dth*np.cos(y[2]) + DI0*np.sin(y[2])))) / self.tau_u
        return np.array([Du, Dc, Dth, DI0])

    def input_sum_f(self, I):
        """ Interaction function based on port 1 input sum. """
        # TODO: I changed the sign here
        return -np.sin(2.*np.pi*self.lpf_slow_mp_inp_sum[1] - self.lpf_slow)
        

    def kuramoto_f(self, I):
        """ Interaction function inspired by the Kuramoto model. """
        raise NotImplementedError('kuramoto_f not yet implemented')

    def upd_lpf_slow_mp_inp_sum(self, time):
        """ Update the list with slow LPF'd scaled sums of inputs at individual ports.
        """
        assert time >= self.last_time, ['Unit ' + str(self.ID) + 
                                        ' lpf_slow_mp_inp_sum updated backwards in time']
        inputs = self.mp_inputs    # updated because mp_inputs is a requirement variable
        weights = self.get_mp_weights(time)
        dots = [ np.dot(i, w) for i, w in zip(inputs, weights) ]
        # same update rule from other upd_lpf_X methods above, put in a list comprehension
        self.lpf_slow_mp_inp_sum = [dots[i] + (self.lpf_slow_mp_inp_sum[i] - dots[i]) * 
                                   np.exp( (self.last_time-time)/self.tau_slow ) 
                                   for i in range(self.n_ports)]

    def upd_lpf_mid_mp_raw_inp_sum(self, time):
        """ Update the list with medium LPF'd sums of inputs at individual ports. """
        sums = [sum(inps) for inps in self.mp_inputs]
        # same update rule from other upd_lpf_X methods above, put in a list comprehension
        self.lpf_mid_mp_raw_inp_sum = [sums[i] + (self.lpf_mid_mp_raw_inp_sum[i] - sums[i])
                                       * self.mid_prop for i in range(self.n_ports)]

    def upd_inp_deriv_mp(self, time):
        """ Update the list with input derivatives for each port.  """
        u = self.net.units
        self.inp_deriv_mp = [[u[uid[idx]].get_lpf_fast(dely[idx]) -
                              u[uid[idx]].get_lpf_mid(dely[idx]) 
                              for idx in range(len(uid))]
                              for uid, dely in self.pre_list_del_mp]
        #self.inp_deriv_mp = [[u[uid].get_lpf_fast(dely) - u[uid].get_lpf_mid(dely) 
        #                      for uid, dely in uid_dely] 
        #                      for uid_dely in self.pre_list_del_mp]

    def upd_avg_inp_deriv_mp(self, time):
        """ Update the list with the average of input derivatives for each port. """
        self.avg_inp_deriv_mp = [np.mean(l) if len(l) > 0 else 0.
                                 for l in self.inp_deriv_mp]
        
    def upd_del_inp_deriv_mp(self, time):
        """ Update the list with custom delayed input derivatives for each port. """
        u = self.net.units
        self.del_inp_deriv_mp = [[u[uid].get_lpf_fast(self.custom_inp_del) - 
                                  u[uid].get_lpf_mid(self.custom_inp_del) 
                                  for uid in lst] for lst in self.pre_list_mp]

    def upd_del_avg_inp_deriv_mp(self, time):
        """ Update the list with delayed averages of input derivatives for each port. """
        self.del_avg_inp_deriv_mp = [np.mean(l) if len(l) > 0 else 0.
                                     for l in self.del_inp_deriv_mp]
 

class am_pm_oscillator_exp(unit):
    """
    An oscillator with amplitude and phase modulated by inputs.

    The outuput of the unit is the sum of a constant part and a sinusoidal part.
    Both of their amplitudes are modulated by the sum of the inputs at port 0.
    The phase of the sinusoidal part is modulated by the relative phase of the inputs
    at port 1 through a method chosen by the user. 

    The model uses 5-dimensional dynamics, so it's state at a given time is a 
    5-element array. The first element corresponds to the unit's activity, which
    comes from the sum of the constant part and the oscillating part. The second
    element corresponds to the constant part of the output. The third element
    is a LPFd version of the second element. The fourth element
    corresponds to the phase of the oscillating part. The fifth element is a
    variable that follows the scaled sum of the inputs at port 0; this is used in
    order to obtain the derivative of those inputs without the need of two low-pass
    filters and new requirements. 

    The equations of the model look like this:
    tau_u * u'   = c' + Is*th'*cos(th) + <Is>'*sin(th)
    tau_c * c'   = (1-c)*c*cp*ip
    tau_slow * cs' = c - cs
    tau_t * th'  = w + F(u_1, ..., u_n, U)
    tau_s * <Is>'= Is - <Is>

    where: 
        u = units's activity,
        c = constant part of the unit's activity,
        th = phase of the oscillation,
        <Is> = low-pass filtered Is,
        Is = scaled sum of inputs at port 0,
        cp = "slow" derivative of c (lpf_mid - lpf_slow)
        ip = "slow" derivative f Is (lpf_mid - lpf_slow)
        Im = scaled sum of inputs at port 1,
        w = intrinsic frequency of the oscillation times tau_t,
        F = interaction function,
        n = number of inputs at port 1,
        u_j = j-th input at port 1, 
        U = unit's output normalized by its medium LPF'd value.

    There are several choices for the interaction function:
    1) input_sum:
        F = alpha*sin(Ic(t) - U(t)), where Ic is the scaled sum of inputs (each
        multiplied by its synaptic weight), normalized by its slow LPF'd value.
    2) kuramoto:
        F = (1/max(n,1))*sum_j K_j*[f(u_j, u) - f(u, u_j)], where
            K_j = weight of j-th connection at port 1,
            f(a,b) = a*sqrt(1-b**2)
        This aims to reproduce the original Kuramoto model, despite the phases
        not being communicated, but deduced from the received activities.
        It may require normalization of individual inputs (e.g. removing their 
        temporal average and dividing by that average), so it is not implemented.
    3) zero
        F = 0
    """

    def __init__(self, ID, params, network):
        """ The unit constructor.

        Args:
            ID, params, network: same as in the parent's constructor.
            In addition, params should have the following entries.
                REQUIRED PARAMETERS
                'tau_u' : Time constant for the unit's activity.
                'tau_c' : Time constant for non-oscillatory dynamics.
                'tau_t' : Time constant for oscillatory dynamics.
                'tau_s' : Time constant for the port 0 low-pass filter.
                          A small value is recommended, so the derivative
                          of the LPF'd signal is similar to the derivative
                          of the original signal.
                'tau_slow' : time constant for the slow low-pass filter.
                'omega' : intrinsic oscillation angular frequency times tau_t.
                'multidim' : the Boolean literal 'True'. This is used to indicate
                             net.create that the 'init_val' parameter may be a single
                             initial value even if it is a list.
                'F' : a string specifying which interaction function to use.
                      Options: 'zero', 'kuramoto', 'input_sum'.
                      The 'input_sum' option requires an extra parameter: 
                      'alpha' : strength of phase interactions
                Using rga synapses brings an extra required parameter:
                'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. It is 
                                  recommended to use the 'post_delay' value of the 
                                  rga synapses. 
                OPTIONAL PARAMETERS
                'n_ports' : number of input ports. Must equal 2. Defaults to 2.
        Raises:
            ValueError

        """
        params['multidim'] = True
        if len(params['init_val']) != 5:
            raise ValueError("Initial values for the am_pm_oscillator must " +
                             "consist of a 5-element array.")
        if 'n_ports' in params:
            if params['n_ports'] != 2:
                raise ValueError("am_pm_oscillator units require 2 input ports.")
        else:
            params['n_ports'] = 2
        unit.__init__(self, ID, params, network) # parent's constructor
        self.tau_u = params['tau_u']
        self.tau_c = params['tau_c']
        self.tau_t = params['tau_t']
        self.tau_s = params['tau_s']
        self.omega = params['omega']
        # you need these by default depending on the Dc update rule
        self.syn_needs.update([syn_reqs.mp_inputs, syn_reqs.lpf_slow_mp_inp_sum,
                               syn_reqs.lpf_mid_mp_raw_inp_sum])
        if params['F'] == 'zero':
            self.f = lambda x : 0.
        elif params['F'] == 'input_sum':
            self.f = self.input_sum_f
            self.syn_needs.update([syn_reqs.lpf_slow, syn_reqs.mp_inputs, 
                                   syn_reqs.lpf_slow_mp_inp_sum])
        elif params['F'] == 'kuramoto':
            self.f = self.kuramoto_f
        else:
            raise ValueError('Wrong specification of the interaction function F')
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        self.n_inps = [max(len(l),0.001) for l in self.port_idx] 


    def derivatives(self, y, t):
        """ Implements the equations of the am_mp_oscillator.

        Args:
            y : list or Numpy array with the 4-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
              y[2] : cp -- LFP'd version of c
              y[3] : th -- phase of the oscillation,
              y[4] : I0 -- LPF'd sum of port 0 inputs.
            t : time when the derivative is evaluated.
        Returns:
            5-element numpy array with state variable derivatives.
        """
        # get the input sum at each port
        I = [ np.dot(i, w) for i, w in 
              zip(self.get_mp_inputs(t), self.get_mp_weights(t)) ]
        # Obtain the derivatives
        Dcs = (y[1] - y[2]) / self.tau_slow
        slow_I0 = self.lpf_slow_mp_inp_sum[0]
        """
        Dc = (I[0] * (1. - y[1]) + I[1]*y[1]) / self.tau_c
        Dc = ( I[0]*(1. - y[1]) + (I[1] - slow_I0)*y[1] ) / self.tau_c
        Dc =  (y[1]+0.1)*(1. - y[1])*(
               Dcs*(y[4] - slow_I0) + I[1]) / self.tau_c
        Dc = -(y[1]+0.1)*(1. - y[1])*(
             (self.lpf_mid - (self.lpf_mid_mp_raw_inp_sum[1]/self.n_inps[1]))*
             (y[4] - slow_I0)) / self.tau_c

        xp = self.del_avg_inp_deriv_mp[1]
        up = (self.get_lpf_fast(self.custom_inp_del) -
              self.get_lpf_mid(self.custom_inp_del))
        sp = self.avg_inp_deriv_mp[0]
        Dc = (y[1]+0.1)*(1. - y[1])*(up - xp)*sp / self.tau_c
        #Dc = ((y[1]+0.1)*(1. - y[1])*(up - xp)*
        #      (y[4] - slow_I0))/ self.tau_c
        xp = self.del_avg_inp_deriv_mp[1]
        up = (self.get_lpf_fast(self.custom_inp_del) -
              self.get_lpf_mid(self.custom_inp_del))
        sp = self.avg_inp_deriv_mp[0]
        Dc = (y[1]+0.1)*(1. - y[1])*(up - xp)*(sp - 0.1*(y[2]-0.1)*
              slow_I0 + I[1]*y[1]) / self.tau_c
        """

        Dth = (self.omega + self.f(I)) / self.tau_t
        DI0 = (I[0] - y[4]) / self.tau_s
        Dc = (y[4] - slow_I0) / self.tau_c
        #DI0 = (sum(self.get_mp_inputs(t)[0]) - y[3]) / self.tau_s
        #Du = (Dc + I[0]*Dth*np.cos(y[2]) + DI0*np.sin(y[2])) / self.tau_u
        Du = ((1. - y[0]) * y[0] * 
              (Dc + y[4]*Dth*np.cos(y[3]) + DI0*np.sin(y[3]))) / self.tau_u
        return np.array([Du, Dc, Dcs, Dth, DI0])

    def input_sum_f(self, I):
        """ Interaction function based on port 1 input sum. """
        return np.sin(2.*np.pi*self.lpf_slow_mp_inp_sum[1] - self.lpf_slow)
        

    def kuramoto_f(self, I):
        """ Interaction function inspired by the Kuramoto model. """
        raise NotImplementedError('kuramoto_f not yet implemented')

    def upd_lpf_slow_mp_inp_sum(self, time):
        """ Update the list with slow LPF'd scaled sums of inputs at individual ports.
        """
        assert time >= self.last_time, ['Unit ' + str(self.ID) + 
                                        ' lpf_slow_mp_inp_sum updated backwards in time']
        inputs = self.mp_inputs    # updated because mp_inputs is a requirement variable
        weights = self.get_mp_weights(time)
        dots = [ np.dot(i, w) for i, w in zip(inputs, weights) ]
        # same update rule from other upd_lpf_X methods above, put in a list comprehension
        self.lpf_slow_mp_inp_sum = [dots[i] + (self.lpf_slow_mp_inp_sum[i] - dots[i]) * 
                                   np.exp( (self.last_time-time)/self.tau_slow ) 
                                   for i in range(self.n_ports)]

    def upd_lpf_mid_mp_raw_inp_sum(self, time):
        """ Update the list with medium LPF'd sums of inputs at individual ports. """
        sums = [sum(inps) for inps in self.mp_inputs]
        # same update rule from other upd_lpf_X methods above, put in a list comprehension
        self.lpf_mid_mp_raw_inp_sum = [sums[i] + (self.lpf_mid_mp_raw_inp_sum[i] - sums[i])
                                       * self.mid_prop for i in range(self.n_ports)]

    def upd_inp_deriv_mp(self, time):
        """ Update the list with input derivatives for each port.  """
        u = self.net.units
        self.inp_deriv_mp = [[u[uid[idx]].get_lpf_fast(dely[idx]) -
                              u[uid[idx]].get_lpf_mid(dely[idx]) 
                              for idx in range(len(uid))]
                              for uid, dely in self.pre_list_del_mp]
        #self.inp_deriv_mp = [[u[uid].get_lpf_fast(dely) - u[uid].get_lpf_mid(dely) 
        #                      for uid, dely in uid_dely] 
        #                      for uid_dely in self.pre_list_del_mp]

    def upd_avg_inp_deriv_mp(self, time):
        """ Update the list with the average of input derivatives for each port. """
        self.avg_inp_deriv_mp = [np.mean(l) if len(l) > 0 else 0.
                                 for l in self.inp_deriv_mp]
        
    def upd_del_inp_deriv_mp(self, time):
        """ Update the list with custom delayed input derivatives for each port. """
        u = self.net.units
        self.del_inp_deriv_mp = [[u[uid].get_lpf_fast(self.custom_inp_del) - 
                                  u[uid].get_lpf_mid(self.custom_inp_del) 
                                  for uid in lst] for lst in self.pre_list_mp]

    def upd_del_avg_inp_deriv_mp(self, time):
        """ Update the list with delayed averages of input derivatives for each port. """
        self.del_avg_inp_deriv_mp = [np.mean(l) if len(l) > 0 else 0.
                                     for l in self.del_inp_deriv_mp]
 


class test_oscillator(unit):
    """ 
    A model used to test the frameowork for multidimensional units.

    The model consists of the equations for a sinusoidal:
    y' = w*x
    x' = -w*y
    with y being the unit's output, and w the frequency of oscillation. w is the
    reciprocal of the unit's time constant tau.
    Inputs are currently ignored.
    """

    def __init__(self, ID, params, network):
        """ The unit's constructor.

        Args:
            ID, params, network, same as in unit.__init__, butthe 'init_val' parameter
            needs to be a 1D array with two elements, corresponding to the initial values
            of y and x.
            In addition, params should have the following entries.
            REQUIRED PARAMETERS
            'tau' : Time constant of the update dynamics. Also, reciprocal of the 
                    oscillator's frequency.

        """
        params['multidim'] = True
        unit.__init__(self, ID, params, network)
        self.tau = params['tau']
        self.w = 1/self.tau

    def derivatives(self, y, t):
        """ Implements the ODE of the oscillator.

        Args:
            y : 1D, 2-element array with the values of the state variables.
            t : time when the derivative is evaluated (not used).
        Returns:
            numpy array with [w*y[1], -w*y[0]]
        """
        return np.array([self.w*y[1], -self.w*y[0]])

    def dt_fun(self, y, s):
        """ The derivatives function used for flat networks. 
        
        Args:
            y : 1D, 2-element array with the values of the state variables.
            s: index to the inp_sum array (not used).
        Returns:
            Numpy array with 2 elements.
            
        """
        return np.array([self.w*y[1], -self.w*y[0]])



