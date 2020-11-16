"""
spinal_units.py
The units used in the motor control model.
"""
from draculab import unit_types, synapse_types, syn_reqs  # names of models and requirements
from units.units import unit, sigmoidal
import numpy as np


#00000000000000000000000000000000000000000000000000000000000000000000000
#000000000 CLASSES INCORPORATING REQUIREMENT UPDATE FUNCTIONS 0000000000
#00000000000000000000000000000000000000000000000000000000000000000000000

class rga_reqs():
    """ A class with the update functions for requirements in rga synapses. """
    def __init__(self, params):
        """ This constructor adds required syn_needs values. 

            The constructor receives the parameters dictionary of the unit's
            creator, but only considers these entries: 
            'inp_deriv_ports' : A list with the numbers of the ports where all
                                inp_deriv_mp methods will calculate their 
                                derivatives. Defaults to a list with all ports.
            'del_inp_ports' : A list with the numbers of the ports where 
                              del_inp_mp, and del_inp_avg_mp will obtain their
                              inputs. Defaults to all ports.
            'xd_inp_deriv_p' : List with the number of the ports where
                               xtra_del_inp_deriv_mp and
                               xtra_del_inp_deriv_mp_sc_sum will work.
                               Defaults to all ports.
        """
        #self.syn_needs.update([syn_reqs.lpf_slow_sc_inp_sum])

        # inp_deriv_ports works by indicating the add_ methods to restrict the
        # entries in pre_list_del_mp and pre_list_mp.
        if 'inp_deriv_ports' in params:
            self.inp_deriv_ports = params['inp_deriv_ports']
        # del_inp_ports works by indicating the add_del_inp_mp method to
        # restrict the entries in dim_act_del.
        if 'del_inp_ports' in params:
            self.del_inp_ports = params['del_inp_ports']
        # xd_inp_deriv works by indicating the add_xtra_del_inp_deriv_mp method
        # to restrict the entries in ??? 
        if 'xd_inp_deriv_p' in params:
            self.xd_inp_deriv_p = params['xd_inp_deriv_p']

    def upd_inp_deriv_mp(self, time):
        """ Update the list with input derivatives for each port.  """
        u = self.net.units
        self.inp_deriv_mp = [[u[uid[idx]].get_lpf_fast(dely[idx]) -
                              u[uid[idx]].get_lpf_mid(dely[idx]) 
                              for idx in range(len(uid))]
                              for uid, dely in self.pre_list_del_mp]

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
 
    def upd_xtra_del_inp_deriv_mp(self, time):
        """ Update the list with extra delayed input derivatives for each port. """
        u = self.net.units
        self.xtra_del_inp_deriv_mp = [
            [u[uid[idx]].get_lpf_fast(self.xtra_inp_del + dely[idx]) - 
             u[uid[idx]].get_lpf_mid(self.xtra_inp_del + dely[idx]) 
             for idx in range(len(uid))] for uid, dely in self.pre_uid_del_mp]

    def upd_xtra_del_inp_deriv_mp_sc_sum(self,time):
        """ Update list with scaled sums of extra delayed input derivatives. """
        #self.xtra_del_inp_deriv_mp_sc_sum = [sum([w*ddiff for w,ddiff in
        #    zip(w_list, ddiff_list)]) for w_list, ddiff_list in
        #    zip(self.mp_weights, self.xtra_del_inp_deriv_mp)]
        self.xtra_del_inp_deriv_mp_sc_sum = [sum([w_l[idx]*ddiff_l[idx] 
                    for idx in range(len(ddiff_l))]) for w_l,ddiff_l in 
                    zip(self.mp_weights, self.xtra_del_inp_deriv_mp)]

    def upd_del_avg_inp_deriv_mp(self, time):
        """ Update the list with delayed averages of input derivatives for each port. """
        self.del_avg_inp_deriv_mp = [np.mean(l) if len(l) > 0 else 0.
                                     for l in self.del_inp_deriv_mp]

    def upd_integ_decay_act(self, time):
        """ Update the slow-decaying integral of the activity. """
        self.integ_decay_act += self.min_delay * (self.act_buff[-1] - 
                                self.integ_decay * self.integ_decay_act)

    def upd_double_del_inp_deriv_mp(self, time):
        """ Update two input derivatives with two delays for each port. """
        u = self.net.units
        self.double_del_inp_deriv_mp[0] = [[u[uid].get_lpf_fast(self.custom_del_diff) - 
                                u[uid].get_lpf_mid(self.custom_del_diff) 
                                for uid in lst] for lst in self.pre_list_mp]
        self.double_del_inp_deriv_mp[1] = [[u[uid].get_lpf_fast(self.custom_inp_del2) - 
                        u[uid].get_lpf_mid(self.custom_inp_del2) 
                        for uid in lst] for lst in self.pre_list_mp]
 
    def upd_double_del_avg_inp_deriv_mp(self, time):
        """ Update averages of input derivatives with two delays for each port. """
        self.double_del_avg_inp_deriv_mp[0] = [np.mean(l) if len(l) > 0 else 0.
                                    for l in self.double_del_inp_deriv_mp[0]]
        self.double_del_avg_inp_deriv_mp[1] = [np.mean(l) if len(l) > 0 else 0.
                                    for l in self.double_del_inp_deriv_mp[1]]

    def upd_slow_inp_deriv_mp(self, time):
        """ Update the list with slow input derivatives for each port.  """
        u = self.net.units
        self.slow_inp_deriv_mp = [[u[uid[idx]].get_lpf_mid(dely[idx]) -
                                   u[uid[idx]].get_lpf_slow(dely[idx]) 
                                   for idx in range(len(uid))]
                                   for uid, dely in self.pre_list_del_mp]

    def upd_avg_slow_inp_deriv_mp(self, time):
        """ Update the list with average slow input derivatives per port. """
        self.avg_slow_inp_deriv_mp = [np.mean(l) if len(l) > 0 else 0.
                                 for l in self.slow_inp_deriv_mp]

    def upd_inp_avg_mp(self, time):
        """ Update the averages of the inputs for each port. """
        self.inp_avg_mp = [r*p_inps.sum() for p_inps,r in 
                           zip(self.mp_inputs, self.inp_recip_mp)]

    def upd_del_inp_mp(self, time):
        """ Update the arrays with delayed inputs for each port. """
        self.del_inp_mp = [[a[0](time-a[1]) for a in l] 
                           for l in self.dim_act_del] # if len(l)>0]

    def upd_del_inp_avg_mp(self, time):
        """ Update the average of delayed inputs for each port. """
        self.del_inp_avg_mp = [r*sum(l) for r,l in
                               zip(self.avg_fact_mp, self.del_inp_mp)]

    def upd_sc_inp_sum_deriv_mp(self, time):
        """ Update the derivatives for the scaled sum of inputs at each port."""
        self.sc_inp_sum_deriv_mp = [sum([w*diff for w,diff in 
                zip(w_list, diff_list)]) for w_list, diff_list in 
                zip(self.mp_weights, self.inp_deriv_mp)]

    def upd_idel_ip_ip_mp(self, time):
        """ Update the dot product of delayed and derived inputs per port."""
        self.idel_ip_ip_mp = [sum([ldi[i]*lip[i] for i in range(len(ldi))])
                   for ldi, lip in zip(self.del_inp_mp, self.inp_deriv_mp)]

    def upd_dni_ip_ip_mp(self, time):
        """ Update dot product of delayed-normalized and diff'd inputs per port."""
        self.dni_ip_ip_mp = [
            sum([(ldi[i]-iavg)*lip[i] for i in range(len(ldi))]) 
            for ldi, lip, iavg in 
                zip(self.del_inp_mp, self.inp_deriv_mp, self.del_inp_avg_mp)]

    def upd_i_ip_ip_mp(self, time):
        """ Update the inner product of input with its derivative per port."""
        self.i_ip_ip_mp = [ sum([inp[j]*dinp[j] for j in range(len(inp))]) if dinp
                else 0. for inp, dinp in zip(self.mp_inputs, self.inp_deriv_mp) ]

    def upd_ni_ip_ip_mp(self, time):
        """ Update dot product of normalized input with its derivative per port."""
        self.ni_ip_ip_mp = [ sum([(inp[j]-avg)*dinp[j] for j in range(len(inp))])
                if dinp else 0. for inp, dinp, avg in 
                zip(self.mp_inputs, self.inp_deriv_mp, self.inp_avg_mp) ]

class lpf_sc_inp_sum_mp_reqs():
    """ Class with the update functions for the X_lpf_sc_inp_sum_mp_reqs. """
    def __init__(self, params):
        """ Class constructor. 

            Receives the params dictionray of the unit's creator.
        """
        self.syn_needs.update([syn_reqs.mp_inputs, syn_reqs.mp_weights,
                              syn_reqs.sc_inp_sum_mp])

    def upd_lpf_fast_sc_inp_sum_mp(self, time):
        """ Update a list with fast LPF'd scaled sums of inputs at each port. """
        # updated to use mp_inputs, mp_weights
        #sums = [(w*i).sum() for i,w in zip(self.mp_inputs, self.mp_weights)]
        # same update rule from other upd_lpf_X methods, put in a list comprehension
        self.lpf_fast_sc_inp_sum_mp = [self.sc_inp_sum_mp[i] + 
                                      (self.lpf_fast_sc_inp_sum_mp[i] - 
                                       self.sc_inp_sum_mp[i])
                                       * self.fast_prop for i in range(self.n_ports)]

    def upd_lpf_mid_sc_inp_sum_mp(self, time):
        """ Update a list with medium LPF'd scaled sums of inputs at each port. """
        # untouched copy from gated_out_norm_am_sig
        #sums = [(w*i).sum() for i,w in zip(self.mp_inputs, self.mp_weights)]
        # same update rule from other upd_lpf_X methods, put in a list comprehension
        self.lpf_mid_sc_inp_sum_mp = [self.sc_inp_sum_mp[i] + 
                                     (self.lpf_mid_sc_inp_sum_mp[i] - 
                                      self.sc_inp_sum_mp[i])
                                      * self.mid_prop for i in range(self.n_ports)]

    def upd_lpf_slow_sc_inp_sum_mp(self, time):
        """ Update a list with slow LPF'd scaled sums of inputs at each port. """
        #sums = [(w*i).sum() for i,w in zip(self.mp_inputs, self.mp_weights)]
        #sums = [(w*i).sum() for i,w in zip(self.get_mp_inputs(time),
        #                                   self.get_mp_weights(time))]
        # same update rule from other upd_lpf_X methods, put in a list comprehension
        self.lpf_slow_sc_inp_sum_mp = [self.sc_inp_sum_mp[i] + 
                                      (self.lpf_slow_sc_inp_sum_mp[i] - 
                                       self.sc_inp_sum_mp[i])
                                       * self.slow_prop for i in range(self.n_ports)]

    def upd_sc_inp_sum_diff_mp(self, time):
        """ Update the derivatives for the scaled sum of inputs at each port."""
        self.sc_inp_sum_diff_mp = [lpf_fast - lpf_mid for lpf_fast, lpf_mid in
                  zip(self.lpf_fast_sc_inp_sum_mp, self.lpf_mid_sc_inp_sum_mp)]



class acc_sda_reqs():
    """ The acc_(mid|slow) and slow_decay_adapt update functions. """
    def __init__(self, params):
        """ Class constructor. 

            Receives the params dictionray of the unit's creator.
            It considers these entries:
            'acc_slow_port' : port number of the acc_slow reset input.
            'acc_mid_port' : port number of the acc_mid reset input.
            'sda_port' : reset port for the slow_decay_adaptation.
        """
        self.syn_needs.update([syn_reqs.mp_inputs, syn_reqs.mp_weights,
                              syn_reqs.sc_inp_sum_mp])
        if 'acc_slow_port' in params:
            self.acc_slow_port = params['acc_slow_port']
        if 'acc_mid_port' in params:
            self.acc_mid_port = params['acc_mid_port']
        if 'sda_port' in params:
            self.sda_port = params['sda_port']

    def upd_acc_slow(self, time):
        """ Update the slow speed accumulator. """
        if self.sc_inp_sum_mp[self.acc_slow_port] > 0.5 and self.acc_slow > 0.5:
        #if ( (self.get_mp_inputs(time)[2]*self.get_mp_weights(time)[2]).sum()
        #     > 0.5 and self.acc_slow > 0.5 ):
             self.acc_slow = 0.
        else: 
            self.acc_slow = 1. - (1.-self.acc_slow)*self.slow_prop

    def upd_acc_mid(self, time):
        """ Update the medium speed accumulator. """
        if self.sc_inp_sum_mp[self.acc_mid_port] > 0.5 and self.acc_mid > 0.5:
        #if ( (self.get_mp_inputs(time)[2]*self.get_mp_weights(time)[2]).sum()
        #     > 0.5 and self.acc_mid > 0.5 ):
             self.acc_mid = 0.
        else: 
            self.acc_mid = 1. - (1.-self.acc_mid)*self.mid_prop

    def upd_slow_decay_adapt(self, time):
        """ Update method for the slow-decaying adaptation. """
        if (self.sc_inp_sum_mp[self.sda_port] > 0.8 and 
            self.slow_decay_adapt < 0.2):
        #if ((self.get_mp_inputs(time)[3]*self.get_mp_weights(time)[3]).sum()
        #    > 0.8 and self.slow_decay_adapt < 0.2):
            #self.slow_decay_adapt = self.lpf_slow
            self.slow_decay_adapt = self.lpf_slow * self.lpf_slow
            # to produce increase in low-activity units
            #self.slow_decay_adapt = self.lpf_slow - 0.3
        else:
            self.slow_decay_adapt *= self.slow_prop



#00000000000000000000000000000000000000000000000000000000000000000000000
#0000000000               UNIT IMPLEMENTATIONS                0000000000
#00000000000000000000000000000000000000000000000000000000000000000000000

class am_pm_oscillator(unit, rga_reqs):
    """
    An oscillator with amplitude and phase modulated by inputs.

    The outuput of the unit is the sum of a constant part and a sinusoidal part.
    Both of their amplitudes are modulated by the sum of the inputs at port 0.
    The phase of the sinusoidal part is modulated by the relative phase of the 
    inputs at port 1 through a method chosen by the user. 

    The model uses 4-dimensional dynamics, so its state at a given time is a 
    4-element array. The first element corresponds to the unit's activity, which
    comes from the sum of the constant part and the oscillating part. The second
    element corresponds to the constant part of the output. The third element
    corresponds to the phase of the oscillating part. The fourth element is a
    variable that follows the scaled sum of the inputs at port 0; this is used in
    order to obtain the derivative of those inputs without the need of two low-pass
    filters and new requirements. 

    The equations of the model currently look like this:
    tau_u * u'   = u*(1-u)*[c' + (c-u) + <Is>'*sin(th) + <Is>th'cos(th)]
    tau_c * c'   = [Is + Im*c] * (1-c)
    tau_t * th'  = w + F(u_1, ..., u_n, U)
    tau_s * <Is>'= tanh(Is - <Is>)
    ACTUALLY, I'M IN THE MIDDLE OF MODIFICATIONS

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
                                  The delay is in units of min_delay steps. 
                OPTIONAL PARAMETERS
                'n_ports' : number of input ports. Must equal 2. Defaults to 2.
                'mu' : mean of white noise when using noisy integration
                'sigma' : standard deviation of noise when using noisy integration
                'inp_del_steps' : integer with the delay to be used by the
                                del_inp_mp requirement, overriding
                                custom_inp_del.
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
        self.syn_needs.update([syn_reqs.mp_inputs, syn_reqs.mp_weights,
                               syn_reqs.lpf_slow_mp_inp_sum])
        if params['F'] == 'zero':
            self.f = lambda x : 0.
        elif params['F'] == 'input_sum':
            self.f = self.input_sum_f
            self.syn_needs.update([syn_reqs.lpf_slow, syn_reqs.mp_inputs, 
                                   syn_reqs.lpf_slow_mp_inp_sum])
            rga_reqs.__init__(self, params)
        elif params['F'] == 'kuramoto':
            self.f = self.kuramoto_f
        else:
            raise ValueError('Wrong specification of the interaction function F')
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        if 'inp_del_steps' in params:
            self.inp_del_steps = params['inp_del_steps']
        if 'mu' in params:
            self.mu = params['mu']
        if 'sigma' in params:
            self.sigma = params['sigma']
        # latency is the time delay in the phase shift of a first-order LPF
        # with a sinusoidal input of angular frequency omega
        #self.latency = np.arctan(self.tau_c*self.omega)/self.omega
        self.mudt = self.mu * self.time_bit # used by flat updaters
        self.mudt_vec = np.zeros(self.dim)
        self.mudt_vec[0] = self.mudt
        self.sqrdt = np.sqrt(self.time_bit) # used by flat updater
        self.needs_mp_inp_sum = True # dt_fun uses mp_inp_sum
        rga_reqs.__init__(self, params)

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
        #Dc = y[1]*(1. - y[1])*(I[0] + I[1]) / self.tau_c
        #Dc = max(y[1],1e-3)*max(1. - y[1],1e-3)*(I[0] + I[1]) / self.tau_c
        # The Dc version below is when I[0] is always positive
        Dc = (I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        #Dc = y[1] * (I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        #slow_I0 = self.lpf_slow_mp_inp_sum[0]
        #Dc = ( I[0]*(1. - y[1]) + (I[1] - slow_I0)*y[1] ) / self.tau_c
        #Dc = ( I[0]*(1. - y[1]) - slow_I0*y[1] ) / self.tau_c
        Dth = (self.omega + self.f(I)) / self.tau_t
        #DI0 = np.tanh(I[0] - y[3]) / self.tau_s # default implementation
        #DI0 = np.tanh(I[0]+I[1] - y[3]) / self.tau_s # Add both inputs
        DI = (np.tanh(I[0]+I[1]) - y[3]) / self.tau_s
        #DI0 = (sum(self.get_mp_inputs(t)[0]) - y[3]) / self.tau_s
        #DIs = self.D_factor * (I[0] - y[3])
        #Du = (Dc + I[0]*Dth*np.cos(y[2]) + DI0*np.sin(y[2])) / self.tau_u
        #ex = np.exp(-y[3]*np.sin(y[2]))
        #prime = 0.2*ex/(1.+ex)
        #Du = ((1.-y[0]) * (y[0]-.01) * (y[1]*Dc + (y[1] - y[0]) + 
        Du = ((1.-y[0]) * (y[0]-.01) * (Dc + (y[1] - y[0]) + 
               #prime*(y[3]*Dth*np.cos(y[2]) + DI0*np.sin(y[2])))) / self.tau_u
               y[3]*Dth*np.cos(y[2]) + DI0*np.sin(y[2]))) / self.tau_u
        return np.array([Du, Dc, Dth, DI0])

    def H(self, t):
        """ The Heaviside step function. """
        return 1. if t > 0. else 0.

    def dt_fun(self, y, s):
        """ the derivatives function when the network is flat.
:
            y : list or Numpy array with the 4-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
              y[2] : th -- phase of the oscillation,
              y[3] : I0 -- LPF'd sum of port 0 inputs.
            s : index to inp_sum for current time point
        Returns:
            4-element numpy array with state variable derivatives.
        """
        t = self.times[s - self.min_buff_size]
        # get the input sum at each port
        I = [ port_sum[s] for port_sum in self.mp_inp_sum ]
        # Obtain the derivatives
        #Dc = max(y[1],1e-3)*max(1. - y[1],1e-3)*(I[0] + I[1]) / self.tau_c
        # The Dc version below is when I[0] is always positive
        Dc = (I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        #Dc = y[1] * (I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        Dth = (self.omega + self.f(I)) / self.tau_t
        #DI0 = np.tanh(I[0] - y[3]) / self.tau_s # default implementation
        DI0 = np.tanh(I[0]+I[1] - y[3]) / self.tau_s # Add both inputs
        #DI = (np.tanh(I[0]+I[1]) - y[3]) / self.tau_s
        #Dc += DI0 #/self.tau_c
        #Dc = self.H(self.net.sim_time-600.)*y[1]*(1. - y[1])*(I[0] + I[1]) / self.tau_c
        Du = ((1.-y[0]) * (y[0]-.01) * (Dc + (y[1] - y[0]) + 
               y[3]*Dth*np.cos(y[2]) + DI0*np.sin(y[2]))) / self.tau_u
        return np.array([Du, Dc, Dth, DI0])

    def input_sum_f(self, I):
        """ Interaction function based on port 1 input sum. """
        # TODO: I changed the sign here, should revert later
        #       Also, the factors here are not normalized.
        return -np.sin(2.*np.pi*(self.lpf_slow_mp_inp_sum[1] - self.lpf_slow))

    def kuramoto_f(self, I):
        """ Interaction function inspired by the Kuramoto model. """
        raise NotImplementedError('kuramoto_f not yet implemented')

    """
    def upd_lpf_slow_mp_inp_sum(self, time):
        #Update the list with slow LPF'd scaled sums of inputs at individual ports.
        # Don't remember why I made a separate implementation here, so I commented
        # this out
        
        #assert time >= self.last_time, ['Unit ' + str(self.ID) + 
        #                                ' lpf_slow_mp_inp_sum updated backwards in time']
        inputs = self.mp_inputs    # updated because mp_inputs is a requirement variable
        weights = self.get_mp_weights(time)
        dots = [ np.dot(i, w) for i, w in zip(inputs, weights) ]
        # same update rule from other upd_lpf_X methods above, put in a list comprehension
        self.lpf_slow_mp_inp_sum = [dots[i] + (self.lpf_slow_mp_inp_sum[i] - dots[i]) * 
                                   np.exp( (self.last_time-time)/self.tau_slow ) 
                                   for i in range(self.n_ports)]
    """
    
    def upd_lpf_mid_mp_raw_inp_sum(self, time):
        """ Update the list with medium LPF'd sums of inputs at individual ports. """
        sums = [sum(inps) for inps in self.mp_inputs]
        self.lpf_mid_mp_raw_inp_sum = [sums[i] + (self.lpf_mid_mp_raw_inp_sum[i] - sums[i])
                                       * self.mid_prop for i in range(self.n_ports)]


class am_oscillator(unit, rga_reqs):
    """
    An oscillator with amplitude modulated by inputs.

    The outuput of the unit is the sum of a constant part and a sinusoidal part.
    Both of their amplitudes are modulated by the sum of the inputs at port 0.

    The model uses 3-dimensional dynamics, so its state at a given time is a 
    3-element array. The first element corresponds to the unit's activity, which
    comes from the sum of the constant part and the oscillating part. The second
    element corresponds to the constant part of the output. The third element
    is a bounded LPF'd scaled sum of inputs.

    For the sake of RGA synapses two ports are assumed, with port 0 being
    the "error" port. Using a different number of ports causes a warning.
    
    The equations of the model currently look like this:
    tau_u * u'   = u*(1-u)*[c' + (c-u) + <I>'*sin(wt) + <I>wcos(wt)]
    tau_c * c'   = I  * c * (1-c)
    tau_s * <I>'= tanh(I - <I>)

    where: 
        u = units's activity,
        c = constant part of the unit's activity,
        <I> = low-pass filtered scaled input,
        I = scaled sum of inputs from both ports, 
        w = intrinsic frequency of the oscillation, 
    """

    def __init__(self, ID, params, network):
        """ The unit constructor.

        Args:
            ID, params, network: same as in the parent's constructor.
            In addition, params should have the following entries.
                REQUIRED PARAMETERS
                'tau_u' : Time constant for the unit's activity.
                'tau_c' : Time constant for non-oscillatory dynamics.
                'tau_s' : Time constant for the input low-pass filter.
                          A small value is recommended, so the derivative
                          of the LPF'd signal is similar to the derivative
                          of the original signal.
                'omega' : intrinsic oscillation angular frequency. 
                'multidim' : the Boolean literal 'True'. This is used to indicate
                             net.create that the 'init_val' parameter may be a single
                             initial value even if it is a list.
                Using rga synapses brings an extra required parameter:
                'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. 
                OPTIONAL PARAMETERS
                'mu' : mean of white noise when using noisy integration
                'sigma' : standard deviation of noise when using noisy integration
                'inp_del_steps' : integer with the delay to be used by the
                                del_inp_mp requirement, overriding
                                custom_inp_del.
        Raises:
            ValueError

        """
        params['multidim'] = True
        if len(params['init_val']) != 3:
            raise ValueError("Initial values for the am_oscillator must " +
                             "consist of a 3-element array.")
        if 'n_ports' in params:
            if params['n_ports'] != 2:
                from warnings import warn
                warn("am_oscillator uses two input ports with rga synapses.",
                 UserWarning)
                #raise ValueError("am_oscillator units use two input ports.")

        else:
            params['n_ports'] = 2
        unit.__init__(self, ID, params, network) # parent's constructor
        rga_reqs.__init__(self, params)
        self.tau_u = params['tau_u']
        self.tau_c = params['tau_c']
        self.tau_s = params['tau_s']
        self.omega = params['omega']
        #self.syn_needs.update([syn_reqs.mp_inputs, syn_reqs.mp_weights,
        #                       syn_reqs.lpf_slow_mp_inp_sum])
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        if 'inp_del_steps' in params:
            self.inp_del_steps = params['inp_del_steps']
        if 'mu' in params:
            self.mu = params['mu']
        if 'sigma' in params:
            self.sigma = params['sigma']
        # latency is the time delay in the phase shift of a first-order LPF
        # with a sinusoidal input of angular frequency omega
        #self.latency = np.arctan(self.tau_c*self.omega)/self.omega
        self.mudt = self.mu * self.time_bit # used by flat updaters
        self.mudt_vec = np.zeros(self.dim)
        self.mudt_vec[0] = self.mudt
        self.sqrdt = np.sqrt(self.time_bit) # used by flat updater
        self.needs_mp_inp_sum = True # dt_fun uses mp_inp_sum

    def derivatives(self, y, t):
        """ Implements the equations of the am_oscillator.

        Args:
            y : list or Numpy array with the 3-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
              y[2] : I -- LPF'd sum of inputs.
            t : time when the derivative is evaluated.
        Returns:
            3-element numpy array with state variable derivatives.
        """
        # get the input sum at each port
        I = [ np.dot(i, w) for i, w in 
              zip(self.get_mp_inputs(t), self.get_mp_weights(t)) ]
        # Obtain the derivatives
        #Dc = (I[0]+I[1]) * y[1] * (1. - y[1]) / self.tau_c
        #Dc = (I[0]+I[1]) * (-y[1] - .5) * (1. - y[1]) / self.tau_c
        #Dc = (I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        Dc = y[1]*(I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        #DI = np.tanh(I - y[2]) / self.tau_s
        #DI = np.tanh(I[0]+I[1] - y[2]) / self.tau_s
        #DI = (np.tanh(I[0]+I[1]) - y[2]) / self.tau_s
        #Is = I[0] + I[1]
        #DI = (Is + 1.)*(1. - Is)/self.tau_s
        DI = (np.tanh(I[0]+I[1]) - y[2]) / self.tau_s
        th = self.omega*t
        #Du = ((1.-y[0]) * (y[0]-.01) * (Dc + (y[1] - y[0]) + 
        Du = ((1.-y[0]) * (y[0]-.01) * ( y[1] - y[0] + 
               y[2]*self.omega*np.cos(th) + DI*np.sin(th))) / self.tau_u
        return np.array([Du, Dc, DI])

    def dt_fun(self, y, s):
        """ the derivatives function when the network is flat.
:
            y : list or Numpy array with the 3-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
              y[2] : I -- LPF'd sum of inputs.
            s : index to inp_sum for current time point
        Returns:
            3-element numpy array with state variable derivatives.
        """
        t = self.times[s - self.min_buff_size]
        # get the input sum at each port
        #I = sum(self.mp_inp_sum[:,s])
        I = [ port_sum[s] for port_sum in self.mp_inp_sum ]
        # Obtain the derivatives
        #Dc = (I[0]+I[1]) * (-y[1] -.5) * (1. - y[1]) / self.tau_c
        #Dc = (I[0]+I[1]) * y[1] * (1. - y[1]) / self.tau_c
        #Dc = (I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        Dc = y[1]*(I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        #DI = np.tanh(I - y[2]) / self.tau_s
        #DI = np.tanh(I[0]+I[1] - y[2]) / self.tau_s
        DI = 0. #(np.tanh(I[0]+I[1]) - y[2]) / self.tau_s
        #DI = (1./(1.+np.exp(-0.5*(I[0] + I[1])))-y[2])/self.tau_s
        th = self.omega*t
        #Du = ((1.-y[0]) * (y[0]-.01) * (Dc + (y[1] - y[0]) + 
        #Du = ((1.-y[0]) * (y[0]-.01) * ( y[1] - y[0] + 
        #       y[2]*self.omega*np.cos(th) + DI*np.sin(th))) / self.tau_u
        # experimental 2D dynamics:
        Is = I[0] #+ I[1]
        Du = (y[1] - y[0] + np.tanh(Is) * np.sin(th)) / self.tau_u
        return np.array([Du, Dc, DI])


class am_oscillator2D(unit, rga_reqs):
    """
    Amplitude-modulated oscillator with two state variables.

    The outuput of the unit is the sum of a constant part and a sinusoidal part.
    Both of their amplitudes are modulated by the sum of the inputs at port 0.

    The model uses 2-dimensional dynamics, so its state at a given time is a 
    2-element array. The first element corresponds to the unit's activity, which
    comes from the sum of the constant part and the oscillating part. The second
    element corresponds to the constant part of the output.

    For the sake of RGA synapses at least two ports are used. Port 0 is assumed
    to be the "error" port, whereas port 1 is the "lateral" port. Additionally,
    if n_ports=3, then port 2 is the "global error" port, to be used by rga_ge
    synapses.
    
    The equations of the model currently look like this:
    u'   = (c - u + A*tanh(I)*sin(th) / tau_u
    c'   = c * (I0 + I1*c)*(1-c) / tau_c

    where: 
        u = units's activity,
        c = constant part of the unit's activity,
        I0 = scaled input sum at port 0,
        I1 = scaled input sum at port 1,
        I = I0+I1,
        th = t*omega (phase of oscillation),
        A = amplitude of the oscillations.
    """

    def __init__(self, ID, params, network):
        """ The unit constructor.

        Args:
            ID, params, network: same as in the parent's constructor.
            In addition, params should have the following entries.
                REQUIRED PARAMETERS
                'tau_u' : Time constant for the unit's activity.
                'tau_c' : Time constant for non-oscillatory dynamics.
                'omega' : intrinsic oscillation angular frequency. 
                'multidim' : the Boolean literal 'True'. This is used to indicate
                             net.create that the 'init_val' parameter may be a single
                             initial value even if it is a list.
                Using rga synapses brings an extra required parameter:
                'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. 
                OPTIONAL PARAMETERS
                A = amplitude of the oscillations. Default is 1.
                Using rga_ge synapses requires to set n_ports = 3:
                'n_ports' : number of input ports. Default is 2.
                'mu' : mean of white noise when using noisy integration
                'sigma' : standard deviation of noise when using noisy integration
                'inp_del_steps' : integer with the delay to be used by the
                                del_inp_mp requirement, overriding
                                custom_inp_del.
        Raises:
            ValueError

        """
        params['multidim'] = True
        if len(params['init_val']) != 2:
            raise ValueError("Initial values for the am_oscillator2D must " +
                             "consist of a 2-element array.")
        if 'n_ports' in params:
            if params['n_ports'] != 2 and params['n_ports'] != 3:
                raise ValueError("am_oscillator2D uses 2 or 3 input ports.")
        else:
            params['n_ports'] = 2
        unit.__init__(self, ID, params, network) # parent's constructor
        rga_reqs.__init__(self, params)
        self.tau_u = params['tau_u']
        self.tau_c = params['tau_c']
        self.omega = params['omega']
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        if 'inp_del_steps' in params:
            self.inp_del_steps = params['inp_del_steps']
        if 'A' in params: self.A = params['A']
        else: self.A = 1.
        if 'mu' in params:
            self.mu = params['mu']
        if 'sigma' in params:
            self.sigma = params['sigma']
        # latency is the time delay in the phase shift of a first-order LPF
        # with a sinusoidal input of angular frequency omega
        self.latency = np.arctan(self.tau_c*self.omega)/self.omega
        self.mudt = self.mu * self.time_bit # used by flat updaters
        self.mudt_vec = np.zeros(self.dim)
        self.mudt_vec[0] = self.mudt
        self.sqrdt = np.sqrt(self.time_bit) # used by flat updater
        self.needs_mp_inp_sum = True # dt_fun uses mp_inp_sum

    def derivatives(self, y, t):
        """ Implements the equations of the am_oscillator.

        Args:
            y : list or Numpy array with the 2-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
            t : time when the derivative is evaluated.
        Returns:
            2-element numpy array with state variable derivatives.
        """
        # get the input sum at each port
        I = [ np.dot(i, w) for i, w in 
              zip(self.get_mp_inputs(t), self.get_mp_weights(t)) ]
        # Obtain the derivatives
        Dc = y[1]*(I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        th = self.omega*t
        #Du = (y[1] - y[0] + 
        #      self.A * np.tanh(I[0]+I[1]) * np.sin(th)) / self.tau_u
        Du = (y[1] - y[0] + 
              self.A * np.tanh(I[0]) * np.sin(th)) / self.tau_u
        return np.array([Du, Dc])

    def dt_fun(self, y, s):
        """ The derivatives function when the network is flat.

            y : list or Numpy array with the 3-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
            s : index to inp_sum for current time point
        Returns:
            3-element numpy array with state variable derivatives.
        """
        t = self.times[s - self.min_buff_size]
        # get the input sum at each port
        #I = sum(self.mp_inp_sum[:,s])
        I = [ port_sum[s] for port_sum in self.mp_inp_sum ]
        # Obtain the derivatives
        Dc = y[1]*(I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        th = self.omega*t
        #Du = (y[1] - y[0] + 
        #      self.A * np.tanh(I[0]+I[1])*np.sin(th)) / self.tau_u
        Du = (y[1] - y[0] + 
              self.A * np.tanh(I[0])*np.sin(th)) / self.tau_u
        return np.array([Du, Dc])


class out_norm_sig(sigmoidal):
    """ The sigmoidal unit with one extra attribute.

        The attribute is called des_out_w_abs_sum. This is needed by the 
        out_norm_factor requirement. 
        
        Units from this class are sigmoidals that can normalize the sum
        of their outgoing weights using out_norm_factor. This requirement should 
        be added by synapses that have the pre_out_norm_factor requirement.
    """

    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
            Raises:
                AssertionError.
        """
        sigmoidal.__init__(self, ID, params, network)
        self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        #self.syn_needs.update([syn_reqs.out_norm_factor])


class out_norm_am_sig(sigmoidal, lpf_sc_inp_sum_mp_reqs):
    """ A sigmoidal whose amplitude is modulated by inputs at port 1.

        The output of the unit is the sigmoidal function applied to the
        scaled sum of port 0 inputs, times the scaled sum of port 1 inputs.

        This model also includes the 'des_out_w_abs_sum' attribute, so the
        synapses that have this as their presynaptic unit can have the
        'out_norm_factor' requirement for presynaptic weight normalization.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
            Raises:
                AssertionError.
        """
        if 'n_ports' in params and params['n_ports'] != 2:
            raise AssertionError('out_norm_am_sig units must have n_ports=2')
        else:
            params['n_ports'] = 2
        sigmoidal.__init__(self, ID, params, network)
        self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        self.needs_mp_inp_sum = True # in case we flatten
        self.syn_needs.update([syn_reqs.mp_inputs, syn_reqs.mp_weights,
                               syn_reqs.sc_inp_sum_mp])
        lpf_sc_inp_sum_mp_reqs.__init__(self, params)
      
    def derivatives(self, y, t):
        """ Return the derivative of the activity at time t. """
        I = [(w*i).sum() for w, i in zip(self.get_mp_weights(t), 
                                         self.get_mp_inputs(t))]
        return ( I[1]*self.f(I[0]) - y[0] ) * self.rtau

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        return ( self.mp_inp_sum[1][s]*self.f(self.mp_inp_sum[0][s]) - y ) * self.rtau


class gated_out_norm_sig(sigmoidal, lpf_sc_inp_sum_mp_reqs, acc_sda_reqs):
    """ A sigmoidal with modulated plasticity and output normaliztion.

        The output of the unit is the sigmoidal function applied to the
        scaled sum of port 0 inputs, plus a `p1_inp` factor times the scaled sum
        of port 1 inputs.
        Inputs at port 2 reset the acc_slow variable, which is used by the 
        gated_corr_inh synapses in order to modulate plasticity.

        This model also includes the 'des_out_w_abs_sum' attribute, so the
        synapses that have this as their presynaptic unit can have the
        'out_norm_factor' requirement for presynaptic weight normalization.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
                    'tau_slow' : slow LPF time constant.
                    OPTIONAL PARAMETERS
                    'p1_inp' : The scaled sum of port 0 inputs is multiplied by
                               this parameter before becoming being added to the
                               arguments of the sigmoidal. Default 0.
                    'out_norm_type' : a synapse type's integer value. If included,
                                 the sum of absolute weights for outgoing
                                 connections will only consider synapses of
                                 that type. For example, you may set it as:
                                 {...,
                                 'out_norm_type' : synapse_types.gated_rga_diff.value}
            Raises:
                AssertionError.
        """
        if 'n_ports' in params and params['n_ports'] != 3:
            raise AssertionError('gated_out_norm_am_sig units must have n_ports=3')
        else:
            params['n_ports'] = 3
        sigmoidal.__init__(self, ID, params, network)
        self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        if 'out_norm_type' in params:
            self.out_norm_type = params['out_norm_type']
        self.syn_needs.update([syn_reqs.acc_slow, syn_reqs.mp_inputs, 
                               syn_reqs.mp_weights])
        self.needs_mp_inp_sum = True # in case we flatten
        lpf_sc_inp_sum_mp_reqs.__init__(self, params)
        params['acc_slow_port'] = 2 # so inputs at port 2 reset acc_slow
        acc_sda_reqs.__init__(self, params)
        if 'p1_inp' in params:
            self.p1_inp = params['p1_inp']
        else:
            self.p1_inp = 0.
      
    def derivatives(self, y, t):
        """ Return the derivative of the activity at time t. """
        I = [(w*i).sum() for w, i in zip(self.get_mp_weights(t), 
                                         self.get_mp_inputs(t))]
        return ( self.f(I[0] + self.p1_inp*I[1]) - y[0] ) * self.rtau

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        return ( self.f(self.mp_inp_sum[0][s] + 
                 self.p1_inp*self.mp_inp_sum[1][s]) - y ) * self.rtau


class gated_out_norm_am_sig(sigmoidal, lpf_sc_inp_sum_mp_reqs, acc_sda_reqs):
    """ A sigmoidal with modulated amplitude and plasticity.

        The output of the unit is the sigmoidal function applied to the
        scaled sum of port 0 inputs, times the scaled sum of port 1 inputs.
        Inputs at port 2 reset the acc_slow variable, which is used by the 
        gated_corr_inh synapses in order to modulate plasticity.

        Optionally, the scaled sum of port 1 inputs can also appear in the
        argument to the sigmoidal function. This is controlled by the p1_inp
        parameter.

        This model also includes the 'des_out_w_abs_sum' attribute, so the
        synapses that have this as their presynaptic unit can have the
        'out_norm_factor' requirement for presynaptic weight normalization.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
                    'tau_slow' : slow LPF time constant.
                    OPTIONAL PARAMETERS
                    'p1_inp' : The scaled sum of port 0 inputs is multiplied by
                               this parameter before becoming being added to the
                               arguments of the sigmoidal. Default 0.
                    'out_norm_type' : a synapse type's integer value. If included,
                                 the sum of absolute weights for outgoing
                                 connections will only consider synapses of
                                 that type. For example, you may set it as:
                                 {...,
                                 'out_norm_type' : synapse_types.gated_rga_diff.value}
            Raises:
                AssertionError.
        """
        if 'n_ports' in params and params['n_ports'] != 3:
            raise AssertionError('gated_out_norm_am_sig units must have n_ports=3')
        else:
            params['n_ports'] = 3
        sigmoidal.__init__(self, ID, params, network)
        self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        if 'out_norm_type' in params:
            self.out_norm_type = params['out_norm_type']
        self.syn_needs.update([syn_reqs.acc_slow, syn_reqs.mp_inputs, 
                               syn_reqs.mp_weights])
        self.needs_mp_inp_sum = True # in case we flatten
        lpf_sc_inp_sum_mp_reqs.__init__(self, params)
        params['acc_slow_port'] = 2 # so inputs at port 2 reset acc_slow
        acc_sda_reqs.__init__(self, params)
        if 'p1_inp' in params:
            self.p1_inp = params['p1_inp']
        else:
            self.p1_inp = 0.
      
    def derivatives(self, y, t):
        """ Return the derivative of the activity at time t. """
        I = [(w*i).sum() for w, i in zip(self.get_mp_weights(t), 
                                         self.get_mp_inputs(t))]
        return ( I[1]*self.f(I[0] + self.p1_inp*I[1]) - y[0] ) * self.rtau

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        return ( self.mp_inp_sum[1][s] * self.f(self.mp_inp_sum[0][s] +
                 self.p1_inp*self.mp_inp_sum[1][s]) - y ) * self.rtau


class am_pulse(unit, rga_reqs):
    """
    Integrator with amplitude-modulated periodic pulses.

    The outuput of the unit is the sum of a constant part and a pulsating part.
    The constant part is a soft-bounded integral of the inputs. The pulsating
    emits a pulse whose amplitude is modulated by the sum of the inputs at port
    0.

    The model uses 2-dimensional dynamics, so its state at a given time is a 
    2-element array. The first element corresponds to the unit's activity, which
    comes from the sum of the constant part and the oscillating part. The second
    element corresponds to the constant part of the output.

    For the sake of RGA synapses at least two ports are used. Port 0 is assumed
    to be the "error" port, whereas port 1 is the "lateral" port. Additionally,
    if n_ports=3, then port 2 is the "global error" port, to be used by rga_ge
    synapses. If n_ports=4, then port 3 is the reset signal for the acc_slow
    attribute (used for gated synapses).
    
    The equations of the model currently look like this:
    u'   = (c + A*|tanh(I0+I1)|*sig - u) / tau_u
    c'   = c * (I0 + I1*c)*(1-c) / tau_c

    where: 
        u = units's activity,
        c = constant part of the unit's activity,
        I0 = scaled input sum at port 0,
        I1 = scaled input sum at port 1,
        A = amplitude of the oscillations.
        omega = angular frequency of the pulses
        sig = 1/(1+exp(-b*(cos(omega*t)-thr)))
        b = slope of the sigmoidal
        thr = threshold of the sigmoidal
    """

    def __init__(self, ID, params, network):
        """ The unit constructor.

        Args:
            ID, params, network: same as in the parent's constructor.
            In addition, params should have the following entries.
                REQUIRED PARAMETERS
                'tau_u' : Time constant for the unit's activity.
                'tau_c' : Time constant for non-oscillatory dynamics.
                'omega' : Angular frequency of the pulses.
                Using rga synapses brings an extra required parameter:
                'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. 
                OPTIONAL PARAMETERS
                A = amplitude of the pulses . Default is 1.
                Using rga_ge synapses requires to set n_ports = 3:
                'n_ports' : number of input ports. Default is 2.
                'mu' : mean of white noise when using noisy integration
                'sigma' : standard deviation of noise when using noisy integration
                'multidim' : the Boolean literal 'True'. This is used to indicate
                             net.create that the 'init_val' parameter may be a single
                             initial value even if it is a list.
                'b' : slope of the sigmoidal used for the pulse. Default is 10.
                'thr' : threshold for the sigmoidal. Default is 0.6 .
                'inp_del_steps' : integer with the delay to be used by the
                                del_inp_mp requirement, overriding
                                custom_inp_del.
        Raises:
            ValueError

        """
        params['multidim'] = True
        if len(params['init_val']) != 2:
            raise ValueError("Initial values for the am_pulse model must " +
                             "consist of a 2-element array.")
        if 'n_ports' in params:
            if params['n_ports'] < 2 or params['n_ports'] > 4:
                raise ValueError("am_pulse units use two to four input ports.")
        else:
            params['n_ports'] = 2
        unit.__init__(self, ID, params, network) # parent's constructor
        self.tau_u = params['tau_u']
        self.tau_c = params['tau_c']
        self.omega = params['omega']
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        if 'inp_del_steps' in params:
            self.inp_del_steps = params['inp_del_steps']
        if 'A' in params: self.A = params['A']
        else: self.A = 1.
        if 'mu' in params:
            self.mu = params['mu']
        if 'sigma' in params:
            self.sigma = params['sigma']
        if 'b' in params: self.b = params['b']
        else: self.b = 10.
        if 'thr' in params: self.thr = params['thr']
        else: self.thr = .6
        # latency is the time delay in the phase shift of a first-order LPF
        # with a sinusoidal input of angular frequency omega
        #self.latency = np.arctan(self.tau_c*self.omega)/self.omega
        self.mudt = self.mu * self.time_bit # used by flat updaters
        self.mudt_vec = np.zeros(self.dim)
        self.mudt_vec[0] = self.mudt
        self.sqrdt = np.sqrt(self.time_bit) # used by flat updater
        self.needs_mp_inp_sum = True # dt_fun uses mp_inp_sum
        # calculate derivatives for all ports?
        # TODO: adjust to final form of rga rule
        #params['inp_deriv_ports'] = [0, 1, 2] 
        #params['del_inp_ports'] = [0, 1, 2] 
        rga_reqs.__init__(self, params)

    def derivatives(self, y, t):
        """ Implements the equations of the am_pulse model.

        Args:
            y : list or Numpy array with the 2-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
            t : time when the derivative is evaluated.
        Returns:
            2-element numpy array with state variable derivatives.
        """
        # get the input sum at each port
        I = [ np.dot(i, w) for i, w in 
              zip(self.get_mp_inputs(t), self.get_mp_weights(t)) ]
        # Obtain the derivatives
        Dc = y[1]*(I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        th = self.omega*t
        sig = 1./(1. + np.exp(-self.b*(np.cos(th) - self.thr)))
        #Du = (y[1] - y[0] + np.tanh(I[0]+I[1]) * (
        #      self.A * self.omega * self.b * sig * (1.-sig) * np.sin(th)) /
        #      self.tau_u )
        #Du = (y[1] + self.A * abs(np.tanh(I[0]+I[1])) * sig - y[0]) / self.tau_u
        Du = (y[1] + self.A * abs(np.tanh(I[0])) * sig - y[0]) / self.tau_u
        return np.array([Du, Dc])

    def dt_fun(self, y, s):
        """ The derivatives function when the network is flat.

            y : list or Numpy array with the 2-element state vector:
              y[0] : u  -- unit's activity,
              y[1] : c  -- constant part of the input,
            s : index to inp_sum for current time point
        Returns:
            2-element numpy array with state variable derivatives.
        """
        t = self.times[s - self.min_buff_size]
        # get the input sum at each port
        I = [ port_sum[s] for port_sum in self.mp_inp_sum ]
        # Obtain the derivatives
        Dc = y[1]*(I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        #Dc = (I[0] + I[1]*y[1]) * (1. - y[1]) / self.tau_c
        th = self.omega*t
        sig = 1./(1. + np.exp(-self.b*(np.cos(th) - self.thr)))
        #Du = (y[1] - y[0] + np.tanh(I[0]+I[1]) * (
        #      self.A * self.omega * self.b * sig * (1.-sig) * np.sin(th)) 
        #      / self.tau_u )
        #Du = (y[1] + self.A * abs(np.tanh(I[0]+I[1])) * sig - y[0]) / self.tau_u
        Du = (y[1] + self.A * abs(np.tanh(I[0])) * sig - y[0]) / self.tau_u
        return np.array([Du, Dc])


class logarithmic(unit):
    """ A unit with a logarithminc activation function. 
    
        The output is zero if the scaled sum of inputs is smaller than a given
        threshold 'thresh'. Otherwise, the activation approaches
        log(1 + (I - thresh)) with time constant 'tau'.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'thresh' : Threshold of the activation function.
                    'tau' : Time constant of the update dynamics.
            Raises:
                AssertionError.
        """
        unit.__init__(self, ID, params, network)
        self.thresh = params['thresh']
        self.tau = params['tau']

    def derivatives(self, y, t):
        """ Return the derivative of the activity y at time t. """
        return (np.log( 1. + max(0., self.get_input_sum(t)-self.thresh)) 
                - y[0]) / self.tau

    def dt_fun(self, y, s):
        """ The derivatives function for flat networks. """
        return (np.log( 1. + max(0., self.inp_sum[s]-self.thresh))
                - y) / self.tau

    def upd_sc_inp_sum_diff_mp(self, time):
        """ Update the derivatives for the scaled sum of inputs at each port."""
        # TODO: there is replication of computations when the requirements
        # obtain the input sums
        self.sc_inp_sum_diff_mp = [lpf_fast - lpf_mid for lpf_fast, lpf_mid in
                  zip(self.lpf_fast_sc_inp_sum_mp, self.lpf_mid_sc_inp_sum_mp)]


class rga_sig(sigmoidal, rga_reqs):
    """ A sigmoidal unit that can receive rga synapses.

        This means it has the extra custom_inp_del attribute, as well as
        implementations of all required requirement update functions.
        Moreover, it is a multiport unit.

        Another addition is that this unit has an integral component. This means
        that the input is integrated (actually, low-pass filtered with the
        tau_slow time constant), and the output comes from the sigmoidal 
        function applied to the scaled input sum plus the integral component.

        The des_out_w_abs_sum parameter is included in case the
        pre_out_norm_factor requirement is used.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'tau_slow' : Slow LPF time constant.
                    'integ_amp' : amplitude multiplier of the integral
                                    component.
                    Using rga synapses brings an extra required parameter:
                    'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. 

                OPTIONAL PARAMETERS
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
                                          Default is 1.
            Raises:
                AssertionError.
        """
        if 'n_ports' in params and params['n_ports'] != 2:
            raise AssertionError('rga_sig units must have n_ports=2')
        else:
            params['n_ports'] = 2
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        else:
            raise AssertionError('rga_sig units need a custom_inp_del parameter')
        sigmoidal.__init__(self, ID, params, network)
        if 'des_out_w_abs_sum' in params:
            self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        else:
            self.des_out_w_abs_sum = 1.
        self.integ_amp = params['integ_amp']
        rga_reqs.__init__(self, params) # add requirements and update functions 
        self.needs_mp_inp_sum = False # the sigmoidal uses self.inp_sum
        self.syn_needs.update([syn_reqs.lpf_slow_sc_inp_sum_mp]) 

    def derivatives(self, y, t):
        """ Return the derivative of the activity at time t. """
        inp = self.get_input_sum(t) + self.integ_amp * self.lpf_slow_sc_inp_sum
        return ( self.f(inp) - y[0] ) * self.rtau

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        inp = self.inp_sum[s] + self.integ_amp * self.lpf_slow_sc_inp_sum
        return ( self.f(inp) - y ) * self.rtau


class act(unit, lpf_sc_inp_sum_mp_reqs):
    """ Action clock unit from the cortex wiki.

        In the context of the spinal model, they are meant to receive input
        from the SPF layer at port 0, increasing their value from 0 to 1, going
        slower when F is close to P, and faster when the SPF signals are larger.
        The equations are in the "detecting layer distances" tiddler.

        When their value gets close enough to 1, their target unit will trigger
        an oscillatory/exploratory phase.

        When the scaled sum of inputs at port 1 is larger than a threshold,  the
        unit will reset its value to 0, and will remain at 0 until the port 1 
        inputs decrease below 0.5 .
        
        This unit has the lpf_slow_sc_inp_sum_mp requirement, which requires the
        tau_slow parameter.
    """
    def __init__(self, ID, params, network):
        """
        The unit constructor.

        Args:
            ID, params, network: same as in the 'unit' class.
            In addition, params should have the following entries.
                REQUIRED PARAMETERS
                tau_u : time constant for the activation growth.
                gamma : multiplier to the "sigmoidal distance" Y.
                g : slope of the sigmoidal that produces Y.
                theta : threshold of the sigmoidal that produces Y.
                tau_slow : slow LPF time constant.
                y_min : value of Y below which increase of activity stops.
                OPTIONAL PARAMETERS
                rst_thr : threshold for port 1 input to cause a reset.
                          Default is 0.5 .
        """
        if 'n_ports' in params and params['n_ports'] != 2:
            raise AssertionError('act units must have n_ports=2')
        else:
            params['n_ports'] = 2
        unit.__init__(self, ID, params, network)
        self.syn_needs.update([syn_reqs.lpf_slow_sc_inp_sum_mp, 
                               syn_reqs.mp_inputs, syn_reqs.mp_weights])
        self.tau_u = params['tau_u']
        self.g = params['g']
        self.theta = params['theta']
        self.gamma = params['gamma']
        self.tau_slow = params['tau_slow']
        self.y_min = params['y_min']
        if "rst_thr" in params: self.rst_thr = params['rst_thr']
        else: self.rst_thr = 0.5
        self.needs_mp_inp_sum = True  # don't want port 1 inputs in the sum
        # the next line provides the lpf_slow_sc_inp_sum_mp requirement
        lpf_sc_inp_sum_mp_reqs.__init__(self, params)

    def derivatives(self, y, t):
        """ Return the derivative of the activation at the given time. """
        I1 = (self.get_mp_inputs(t)[1]*self.get_mp_weights(t)[1]).sum()
        if I1 < self.rst_thr:
            I0 = (self.get_mp_inputs(t)[0]*self.get_mp_weights(t)[0]).sum()
            I0_lpf = self.lpf_slow_sc_inp_sum_mp[0]
            Y = 1. / (1. + np.exp(-self.g*(I0 - self.theta)))
            Y_lpf = 1. / (1. + np.exp(-self.g*(I0_lpf - self.theta)))
            dY = Y - Y_lpf
            Y_dist = Y-self.y_min  #max(Y - self.y_min, 0.)
            if Y_dist < 0.:
                du = y[0]*Y_dist 
            else:
                du = Y_dist*(1. - y + self.gamma*dY) / self.tau_u
        else:
            du = -20.*y[0] # rushing towards 0
        return du

    def dt_fun(self, y, s):
        """ Return the derivative of the activation in a flat network. """
        I1 = self.mp_inp_sum[1][s]
        if I1 < self.rst_thr:
            I0 = self.mp_inp_sum[0][s]
            I0_lpf = self.lpf_slow_sc_inp_sum_mp[0]
            Y = 1. / (1. + np.exp(-self.g*(I0 - self.theta)))
            Y_lpf = 1. / (1. + np.exp(-self.g*(I0_lpf - self.theta)))
            dY = Y - Y_lpf
            Y_dist = Y-self.y_min # max(Y - self.y_min, 0.)
            if Y_dist < 0.:
                du = y*Y_dist 
            else:
                du = Y_dist*(1. - y + self.gamma*dY) / self.tau_u
        else:
            du = -40.*y # rushing towards 0
        return du


class gated_rga_sig(sigmoidal, rga_reqs, acc_sda_reqs):
    """ A sigmoidal unit that can receive gated_rga synapses.

        This means it has the extra custom_inp_del attribute, as well as
        implementations of all required requirement update functions.
        Moreover, it is a multiport unit, with 3 ports.

        Another addition is that this unit has an integral component. This means
        that the input is integrated (actually, low-pass filtered with the
        tau_slow time constant), and the output comes from the sigmoidal 
        function applied to the scaled input sum plus the integral component.

        The difference with the rga_sig model is that this class includes the
        acc_mid attribute, which is required by the gated_rga synapse class.
        Moreover, this model has 3 ports instead of 2. Ports 0 and 1 are for the
        "error" and "lateral" inputs, although this distinction is only done by
        the synapses. Port 2 is for the signal that resets the acc_mid
        accumulator. When the scaled sum of inputs at port 2 is larger than 0.5,
        acc_mid is set to 0.

        The des_out_w_abs_sum parameter is included in case the
        pre_out_norm_factor requirement is used.

        The presynaptic units should have the lpf_fast and lpf_mid requirements,
        since these will be added by the gated_rga synapse.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'tau_slow' : Slow LPF time constant.
                    'tau_mid' : Medium LPF time constant.
                    'integ_amp' : amplitude multiplier of the integral
                                    component.
                    Using rga synapses brings an extra required parameter:
                    'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. 

                OPTIONAL PARAMETERS
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
                                          Default is 1.
            Raises:
                AssertionError.
        """
        if 'n_ports' in params and params['n_ports'] != 3:
            raise AssertionError('gated_rga_sig units must have n_ports=3')
        else:
            params['n_ports'] = 3
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        else:
            raise AssertionError('gated_rga_sig units need a custom_inp_del parameter')
        sigmoidal.__init__(self, ID, params, network)
        params['inp_deriv_ports'] = [0, 1] # ports for inp_deriv_mp
        rga_reqs.__init__(self, params)
        if 'des_out_w_abs_sum' in params:
            self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        else:
            self.des_out_w_abs_sum = 1.
        self.integ_amp = params['integ_amp']
        self.syn_needs.update([syn_reqs.lpf_slow_sc_inp_sum, syn_reqs.acc_slow])
        params['acc_slow_port'] = 2 # so inputs at port 2 reset acc_slow
        acc_sda_reqs.__init__(self, params)
        self.needs_mp_inp_sum = True # to avoid adding the reset signal

    def derivatives(self, y, t):
        """ Return the derivative of the activity at time t. """
        sums = [(w*i).sum() for i,w in zip(self.get_mp_inputs(t),
                                           self.get_mp_weights(t))]
        inp = sums[0] + sums[1] + self.integ_amp * self.lpf_slow_sc_inp_sum
        return ( self.f(inp) - y[0] ) * self.rtau

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        inp = self.mp_inp_sum[0][s] + self.mp_inp_sum[1][s] + \
              self.integ_amp * self.lpf_slow_sc_inp_sum
        return ( self.f(inp) - y ) * self.rtau


class gated_rga_adapt_sig(sigmoidal, rga_reqs, acc_sda_reqs):
    """ A sigmoidal unit that can use gated_rga synapses and gated adaptation.

        The difference with the gated_rga_sig model is that this model has 4
        ports instead of 3. When the inputs at port 3 surpass a threshold the
        unit experiences adaptation, which means that its slow-lpf'd activity
        will be used to decrease its current activation. This is achieved
        through the slow_decay_adapt requirement.

        Like the other rga models it has the extra custom_inp_del attribute, 
        as well as implementations of all required requirement update 
        functions.

        Like gated_rga_sig this unit has an integral component. This means
        that the input is integrated (actually, low-pass filtered with the
        tau_slow time constant), and the output comes from the sigmoidal 
        function applied to the scaled input sum plus the integral component.

        Ports 0 and 1 are for the "error" and "lateral" inputs, although this
        distinction is only done by the synapses. Port 2 is for the signal that
        resets the acc_slow accumulator. When the scaled sum of inputs at port 2
        is larger than 0.5, acc_slow is set to 0.

        The des_out_w_abs_sum parameter is included in case the
        pre_out_norm_factor requirement is used.

        The presynaptic units should have the lpf_fast and lpf_mid requirements,
        since these will be added by the gated_rga synapse.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'tau_slow' : Slow LPF time constant.
                    'tau_mid' : Medium LPF time constant.
                    'integ_amp' : amplitude multiplier of the integral
                                    component.
                    Using rga synapses brings an extra required parameter:
                    'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. 

                OPTIONAL PARAMETERS
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
                                          Default is 1.
                    'adapt_amp' : amplitude of adapation. Default is 1.
            Raises:
                AssertionError.
        """
        if 'n_ports' in params and params['n_ports'] != 4:
            raise AssertionError('gated_rga_adapt_sig units must have n_ports=4')
        else:
            params['n_ports'] = 4
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        else:
            raise AssertionError('gated_rga_adapt_sig units need a ' +
                                'custom_inp_del parameter')
        sigmoidal.__init__(self, ID, params, network)
        if 'des_out_w_abs_sum' in params:
            self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        else:
            self.des_out_w_abs_sum = 1.
        if 'adapt_amp' in params:
            self.adapt_amp = params['adapt_amp']
        else:
            self.adapt_amp = 1.
        self.integ_amp = params['integ_amp']
        self.syn_needs.update([syn_reqs.lpf_slow_sc_inp_sum_mp, syn_reqs.acc_slow,
                               syn_reqs.mp_weights, syn_reqs.mp_inputs,
                               syn_reqs.lpf_slow, syn_reqs.slow_decay_adapt])
        params['inp_deriv_ports'] = [0, 1] # ports for inp_deriv_mp
        rga_reqs.__init__(self, params)
        params['acc_slow_port'] = 2 # so inputs at port 2 reset acc_slow
        params['sda_port'] = 3
        acc_sda_reqs.__init__(self, params)
        self.needs_mp_inp_sum = True # to avoid adding the reset signal

    def derivatives(self, y, t):
        """ Return the derivative of the activity at time t. """
        sums = [(w*i).sum() for i,w in zip(self.get_mp_inputs(t),
                                           self.get_mp_weights(t))]
        inp = (sums[0] + sums[1] 
               + self.integ_amp * self.lpf_slow_sc_inp_sum[0]
               - self.adapt_amp * self.slow_decay_adapt)
        return ( self.f(inp) - y[0] ) * self.rtau

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        inp = (self.mp_inp_sum[0][s] + self.mp_inp_sum[1][s]
               + self.integ_amp * self.lpf_slow_sc_inp_sum_mp[0]
               - self.adapt_amp * self.slow_decay_adapt)
        return ( self.f(inp) - y ) * self.rtau


class gated_rga_inpsel_adapt_sig(sigmoidal, rga_reqs, lpf_sc_inp_sum_mp_reqs,
                                 acc_sda_reqs):
    """ Sigmoidal with gated rga, inp_sel synapses and gated adaptation.

        Unlike gated_rga_adapt_sig this model has 5 ports instead of 4. 
        The scaled sum of inputs at port 0 constitutes the error signal for 
        both the gated_rga and gated_input_selection synapses. Inputs at port 1
        are the "lateral" inputs for the gated_rga synapses. Inputs at port 2
        are the "afferent" inputs for the gated_input_selection synapse. 
        The output of the unit is the sigmoidal function applied to the scaled
        sum of inputs at ports 0, 1, and 2, plus an integral component, minus
        an adaptation component.

        The scaled sum of inputs at port 3 is for the signal that resets the 
        acc_slow accumulator, used to gate both rga and input selection synapses.
        When the scaled sum of inputs at port 3 is larger than 0.5, acc_slow is
        set to 0.
         
        When the input at port 4 surpasses a threshold the unit experiences
        adaptation, which means that its slow-lpf'd activity will be used to 
        decrease its current activation. This is achieved through the 
        slow_decay_adapt requirement.

        Like the other rga models it has the extra custom_inp_del attribute, 
        as well as implementations of all required requirement update 
        functions.

        Like gated_rga_sig this unit has an integral component. This means
        that the input is integrated using the integ_decay_act requirement,
        and the output comes from the sigmoidal function applied to the scaled
        input sum plus a term proportional to the integral component.

        The des_out_w_abs_sum parameter is included in case the
        pre_out_norm_factor requirement is used.

        The presynaptic units should have the lpf_fast and lpf_mid requirements,
        since these will be added by the gated_rga synapse.

        This unit has the required parameters to use euler_maru integration if
        this is specified in the parameters.
    """
    def __init__(self, ID, params, network):
        """ The unit constructor.

            Args:
                ID, params, network: same as in the 'unit' class.
                In addition, params should have the following entries.
                    REQUIRED PARAMETERS
                    'slope' : Slope of the sigmoidal function.
                    'thresh' : Threshold of the sigmoidal function.
                    'tau' : Time constant of the update dynamics.
                    'tau_slow' : Slow LPF time constant.
                    'tau_mid' : Medium LPF time constant.
                    'integ_amp' : amplitude multiplier of the integral
                                    component.
                    'integ_decay' : change rate of the integral component.
                    Using rga synapses brings an extra required parameter:
                    'custom_inp_del' : an integer indicating the delay that the rga
                                  learning rule uses for the lateral port inputs. 
                                  The delay is in units of min_delay steps. 
                    Using rga_diff synapses brings two extra required parameters:
                    'custom_inp_del' : the shortest of the two delays.
                    'custom_inp_del2': the longest of the two delays.
                    When custom_inp_del2 is not in the params dictionary no
                    exception is thrown, but instead it is assumed that
                    rga_diff synapses are not used, and the custom_del_diff
                    attribute will not be generated.
                    Using slide_rga_diff synapses, in addition to the two delay
                    values, requires maximum and minimum delay modifiers:
                    'del_mod_max': maximum delay modifier.
                    'del_mod_min': minimum delay modifier.
                    The two delay modifiers are expressed as number of time
                    steps, as is the case for the custom delays.
                OPTIONAL PARAMETERS
                    'des_out_w_abs_sum' : desired sum of absolute weight values
                                          for the outgoing connections.
                                          Default is 1.
                    'out_norm_type' : a synapse type's integer value. If included,
                                 the sum of absolute weights for outgoing
                                 connections will only consider synapses of
                                 that type. For example, you may set it as:
                                 {...,
                                 'out_norm_type' : synapse_types.gated_rga_diff.value}
                    'adapt_amp' : amplitude of adapation. Default is 1.
                    'mu' : noise bias in for euler_maru integration.
                    'sigma' : standard deviation for euler_maru integration.
            Raises:
                AssertionError.
        """
        if 'n_ports' in params and params['n_ports'] != 5:
            raise AssertionError('gated_rga_inpsel_adapt_sig units must have n_ports=5')
        else:
            params['n_ports'] = 5
        if 'custom_inp_del' in params:
            self.custom_inp_del = params['custom_inp_del']
        else:
            raise AssertionError('gated_rga_inpsel_adapt_sig units need a ' +
                                 'custom_inp_del parameter')
        if 'custom_inp_del2' in params:
            if params['custom_inp_del2'] > params['custom_inp_del']:
                self.custom_inp_del2 = params['custom_inp_del2']
                self.custom_del_diff = self.custom_inp_del2-self.custom_inp_del
            else:
                raise ValueError('custom_inp_del2 must be larger than ' +
                                 'custom_inp_del')

        sigmoidal.__init__(self, ID, params, network)

        if 'del_mod_max' in params or 'del_mod_min' in params:
            if params['del_mod_max'] < params['del_mod_min']:
                raise ValueError('del_mod_max cannot be smaller than del_mod_min')
            self.del_mod_max = params['del_mod_max']
            self.del_mod_min = params['del_mod_min']
            if self.delay < (self.custom_inp_del2 + self.del_mod_max)*self.min_delay:
                raise ValueError('The delay in a gated_slide_rga_diff unit is ' +
                                 'smaller than custom_inp_del2 + del_mod_max')
            if 1 > (self.custom_inp_del + self.del_mod_min):
                raise ValueError('custom_inp_del + del_mod_min is too small')
        if 'des_out_w_abs_sum' in params:
            self.des_out_w_abs_sum = params['des_out_w_abs_sum']
        else:
            self.des_out_w_abs_sum = 1.
        if 'adapt_amp' in params:
            self.adapt_amp = params['adapt_amp']
        else:
            self.adapt_amp = 1.
        if 'out_norm_type' in params:
            self.out_norm_type = params['out_norm_type']
        self.integ_amp = params['integ_amp']
        self.integ_decay = params['integ_decay']
        self.syn_needs.update([syn_reqs.integ_decay_act, syn_reqs.acc_slow,
                               syn_reqs.lpf_slow, syn_reqs.slow_decay_adapt,
                               syn_reqs.mp_inputs, syn_reqs.mp_weights,
                               syn_reqs.sc_inp_sum_mp])
                               # syn_reqs.lpf_slow_mp_inp_sum
        params['inp_deriv_ports'] = [0, 1] # ports for inp_deriv_mp
        rga_reqs.__init__(self, params)
        lpf_sc_inp_sum_mp_reqs.__init__(self, params)
        self.needs_mp_inp_sum = True # to avoid adding signals from ports 3,4
        params['acc_slow_port'] = 3 # so inputs at port 3 reset acc_slow
        params['sda_port'] = 4
        acc_sda_reqs.__init__(self, params)
        if 'mu' in params and 'sigma' in params: 
            self.mu = params['mu']
            self.sigma = params['sigma']
            self.mudt = self.mu * self.time_bit # used by flat updater
            self.sqrdt = np.sqrt(self.time_bit) # used by flat updater


    def derivatives(self, y, t):
        """ Return the derivative of the activity at time t. """
        sums = [(w*i).sum() for i,w in zip(self.get_mp_inputs(t),
                                           self.get_mp_weights(t))]
        inp = (sums[0] + sums[1] + sums[2]
               #+ self.integ_amp * self.lpf_slow_mp_inp_sum[0]
               + self.integ_amp * self.integ_decay_act
               - self.adapt_amp * self.slow_decay_adapt)
        return ( self.f(inp) - y[0] ) * self.rtau

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        inp = (self.mp_inp_sum[0][s] + self.mp_inp_sum[1][s] + self.mp_inp_sum[2][s]
               #+ self.integ_amp * self.lpf_slow_mp_inp_sum[0]
               + self.integ_amp * self.integ_decay_act
               - self.adapt_amp * self.slow_decay_adapt)
        return ( self.f(inp) - y ) * self.rtau



from units.units import linear

class inpsel_linear(linear):
    """ The linear unit with mp_weights and mp_inputs requirements. """
    def __init__(self, ID, params, network):
        linear.__init__(self, ID, params, network)
        self.syn_needs.update([syn_reqs.mp_weights, syn_reqs.mp_inputs,
                               syn_reqs.acc_slow])

    def upd_lpf_fast_sc_inp_sum_mp(self, time):
        """ Update a list with fast LPF'd scaled sums of inputs at each port. """
        # updated to use mp_inputs, mp_weights
        sums = [(w*i).sum() for i,w in zip(self.mp_inputs, self.mp_weights)]
        # same update rule from other upd_lpf_X methods, put in a list comprehension
        self.lpf_fast_sc_inp_sum_mp = [sums[i] + (self.lpf_fast_sc_inp_sum_mp[i] - sums[i])
                                       * self.fast_prop for i in range(self.n_ports)]

    def upd_lpf_mid_sc_inp_sum_mp(self, time):
        """ Update a list with medium LPF'd scaled sums of inputs at each port. """
        # untouched copy from gated_out_norm_am_sig
        sums = [(w*i).sum() for i,w in zip(self.mp_inputs, self.mp_weights)]
        # same update rule from other upd_lpf_X methods, put in a list comprehension
        self.lpf_mid_sc_inp_sum_mp = [sums[i] + (self.lpf_mid_sc_inp_sum_mp[i] - sums[i])
                                       * self.mid_prop for i in range(self.n_ports)]

    def upd_acc_slow(self, time):
        """ Update the slow speed accumulator. """
        # modified to reset from port 3
        if ( (self.get_mp_inputs(time)[2]*self.get_mp_weights(time)[2]).sum()
             > 0.5 and self.acc_slow > 0.5 ):
             self.acc_slow = 0.
        else: 
            self.acc_slow = 1. - (1.-self.acc_slow)*self.slow_prop


class chwr_linear(unit):
    """ A linear unit with centered half-wave rectification.

        This means that the output of the unit is the positive part of the
        input minus its mean value minus a threshold. The mean value comes
        from slow low-pass filtering. In other words, the output approaches:
        max( I - <I> - thr, 0.)

        A negative threshold can be used in order to set an output activity
        when the input is at its mean value.
    """
    def __init__(self, ID, params, network):
        """ The class constructor. 

        Args:
            ID, params, network: same as the unit class.
            
            OPTIONAL PARAMETERS
            thresh : input threshold. Default is 0.
    """
        unit.__init__(self, ID, params, network)
        if 'thresh' in params: self.thresh = params['thresh']
        else: self.thresh = 0.
        self.syn_needs.update([syn_reqs.lpf_slow_sc_inp_sum])

    def derivatives(self, y, t):
        """ Returns the firing rate derivative at time t, given rate y.

        Args:
            y : array-like with one single element.
            t : a float.
        """
        return max(self.get_input_sum(t) -
                   self.lpf_slow_sc_inp_sum -
                   self.thresh, 0.) - y[0]

    def dt_fun(self, y, s):
        """ The derivatives function for flat networks. """
        return max(self.inp_sum[s] - 
                   self.lpf_slow_sc_inp_sum - 
                   self.thresh, 0.) - y
        

class inpsel_linear2(unit, acc_sda_reqs, rga_reqs): 
    """ A multiport linear unit that only sums inputs from ports 0 and 1.

        The current implementation only allows positive values (half-wave
        rectification).

        Port 0 is meant to receive error inputs, which should be the main
        drivers of the activity. Port 1 receives lateral inhibition. Port 2 is
        for the ascending motor command inputs. Port 3 is for resetting the slow
        accumulator (acc_slow), used to pause plasticity.
        Inputs from ports 2 and 3 are not used to produce activation in the unit.

        This is meant to be used in the intermediate layer of an input
        selection mechanism, as described in the "A generalization of RGA, and
        Fourier components" note, used in the test2p5.ipynb notebook.

        This model also includes the mp_inputs and mp_weights requirements.
    """
    def __init__(self, ID, params, network):
        """ The class constructor.

        Args:
            ID, params, network: same as the linear class.
            REQUIRED PARAMETERS
            'tau' : time constant of the dynamics.
            'xtra_inp_del' : extra delay in the port 2 (ascending) inputs.
            OPTIONAL PARAMETERS
            use_acc_slow : Whether to include the acc_slow requirement. Default
                           is 'False'.
        """
        self.tau = params['tau']  # the time constant of the dynamics
        if 'n_ports' in params and params['n_ports'] != 4:
            raise AssertionError('inpsel_linear2 units must have n_ports=4')
        else:
            params['n_ports'] = 4
        # TODO: its probably possible to inplement this withouth xtra delays.
        self.xtra_inp_del = params['xtra_inp_del']
        unit.__init__(self, ID, params, network)
        self.syn_needs.update([syn_reqs.acc_slow,
                               syn_reqs.mp_inputs, 
                               syn_reqs.mp_weights ])
                               #syn_reqs.sc_inp_sum_mp]) # so synapses don't call?
        self.needs_mp_inp_sum = True # in case we flatten
        params['acc_slow_port'] = 3 # so inputs at port 3 reset acc_slow
        acc_sda_reqs.__init__(self, params)
        # The following is for the xtra_del_inp_deriv_mp requirement used by the
        # gated_diff_inp_corr synapse.
        params['xd_inp_deriv_p'] = [2] 
        rga_reqs.__init__(self, params)
       
    def derivatives(self, y, t):
        """ Derivatives of the state variables at the given time. 
        
            Args: 
                y : a 1-element array or list with the current firing rate.
                t: time when the derivative is evaluated.
        """
        I = sum([(w*i).sum() for i,w in zip(self.get_mp_inputs(t)[:2],
                                            self.get_mp_weights(t)[:2])])
        return (I - y[0]) / self.tau #if y[0]>0 else 0.01

    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        I = self.mp_inp_sum[0][s] + self.mp_inp_sum[1][s] 
        return (I - y) / self.tau #if y > 0 else 0.01


class bell_shaped_1D(unit):
    """ A unit that responds maximally to a given value of the input sum.
    
        The constructor is given a 'center' parameter. The output y of the unit
        will evolve with dynamics:
        
        tau y' = exp(-b(I - center)^2) - y,
        
        where 'b' is a parameter for the sharpness of the tuning, and 'I' is the
        scaled input sum.
    """
    def __init__(self, ID, params, network):
        """ The class constructor.

            Args:
                ID, params, network: same as the unit class.
                REQUIRED PARAMETERS
                'tau' : time constant of the dynamics.
                'center' : input value causing maximum activation.
                'b' : sharpness parameter.
        """
        unit.__init__(self, ID, params, network)
        self.tau = params['tau']  # the time constant of the dynamics
        self.rtau = 1./self.tau
        self.center = params['center']
        self.b = params['b']

    def derivatives(self, y, t):
        """ Derivative of y at time t for bell_shaped_1D.

            Args:
                y : a 1-element array or list with the current firing rate.
                t: time when the derivative is evaluated.
        """
        diff = self.get_input_sum(t) - self.center
        return self.rtau * (np.exp(-self.b*diff*diff) - y[0])
            
    def dt_fun(self, y, s):
        """ The derivatives function used when the network is flat. """
        diff = self.inp_sum[s] - self.center
        return self.rtau * (np.exp(-self.b*diff*diff) - y)


class td_unit(unit):
    """ A unit used to implement a value function with the TD rule. 
    
        This unit is meant to receive a reward at port 1, and state inputs at
        port 0. The state inputs should use the TD_synapse, and the reward a
        static synapse. 
    """
    def __init__(self, ID, params, network):
        """ The class constructor.

            Args:
                ID, params, network: same as the unit class.
                REQUIRED PARAMETERS
                'tau' : time constant of the dynamics.
                'delta' : time delay for updates (in seconds)

        """




