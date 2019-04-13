"""
requirements.py
This file contains functions to initialize all synaptic requirements used
in draculab units. For some requirements there are also classes that contain
initialization and updating methods.
"""

from draculab import unit_types, synapse_types, syn_reqs
from units import *
import numpy as np


def add_lpf_fast(unit):
    """ Adds 'lpf_fast', a low-pass filtered version of the unit's activity.

        The name lpf_fast indicates that the time constant of the low-pass filter,
        whose name is 'tau_fast', should be relatively fast. In practice this is
        arbitrary.
        The user needs to set the value of 'tau_fast' in the parameter dictionary 
        that initializes the unit.

        This method is meant to be called from init_pre_syn_update whenever the
        'lpf_fast' requirement is found. This method only takes care of the 
        initialization of the variables used for the lpf_fast requirement. Updating
        the value is done by unit.upd_lpf_fast, added to unit.functions by
        init_pre_syn_update. The buffer is re-initialized after each connection
        in unit.init_bufers .
    """
    if not hasattr(unit,'tau_fast'): 
        raise NameError( 'Synaptic plasticity requires unit parameter tau_fast, not yet set' )
    setattr(unit, 'lpf_fast', unit.init_val)
    setattr(unit, 'lpf_fast_buff', np.array( [unit.init_val]*unit.steps, dtype=unit.bf_type) )


def add_lpf_mid(unit):
    """ See 'add_lpf_fast' above. """
    if not hasattr(unit,'tau_mid'): 
        raise NameError( 'The tau_mid requirement needs the parameter tau_mid, not yet set' )
    setattr(unit, 'lpf_mid', unit.init_val)
    setattr(unit, 'lpf_mid_buff', np.array( [unit.init_val]*unit.steps, dtype=unit.bf_type) )


def add_lpf_slow(unit):
    """ See 'add_lpf_fast' above. """
    if not hasattr(unit,'tau_slow'): 
        raise NameError( 'The tau_slow requirement needs the parameter tau_slow, not yet set' )
    setattr(unit, 'lpf_slow', unit.init_val)
    setattr(unit, 'lpf_slow_buff', np.array( [unit.init_val]*unit.steps, dtype=unit.bf_type) )


def add_sq_lpf_slow(unit):
    """ Adds a low pass filtered version of the squared activity.
        
        As the name implies, the filter uses the "slow" time constant 'tau_slow'.
        The purpose of this is to have a mean value of the square of the activity,
        as used in some versions of the BCM learning rule. Accordingly, this 
        requirement is used by the bcm_synapse class.
    """
    if not hasattr(unit,'tau_slow'): 
        raise NameError( 'sq_lpf_slow requires unit parameter tau_slow, not yet set' )
    setattr(unit, 'sq_lpf_slow', unit.init_val)


def add_inp_vector(unit):
    """ Add a numpy array with the unit's inputs at the start of the simulation step.

        The inputs are not multiplied by synaptic weights, and come with their 
        appropriate delays.

        This input vector is used by other synaptic requirements, namely lpf_mid_inp_sum,
        balance, and exp_scale. In this last requirement, it is used to obtain the 'mu'
        factor used by the exp_scale rule.
    """
    setattr(unit, 'inp_vector', np.tile(unit.init_val, len(unit.net.syns[unit.ID])))


def add_mp_inputs(unit):
    """ Add a list with all the inputs, in the format of get_mp_inputs method. 

        In fact, the list is updated using the get_mp_inputs method. Some requirements
        like mp_balance and lpf_slow_mp_inp_sum use the output of get_mp_inputs, and
        the mp_inputs requirement saves computations by ensuring that get_mp_inputs
        only gets called once per simulation step.

        Quoting the docstring of unit.get_mp_inputs:
        "This method is for units where multiport = True, and that have a port_idx attribute.
        The i-th element of the returned list is a numpy array containing the raw (not multiplied
        by the synaptic weight) inputs at port i. The inputs include transmision delays."
    """
    if not hasattr(unit,'port_idx'): 
        raise NameError( 'the mp_inputs requirement is for multiport units with a port_idx list' )
    val = [] 
    for prt_lst in unit.port_idx:
        val.append(np.array([unit.init_val for _ in range(len(prt_lst))]))
    setattr(unit, 'mp_inputs', val)


def add_inp_avg_hsn(unit):
    """ Add an average of the inputs arriving at hebbsnorm synapses.

        In other words, the sum of fast-LPF'd hebbsnorm inputs divided by the the number
        of hebbsnorm inputs.

        Since we are using the lpf_fast signals, all the presynaptic units with hebbsnorm
        synapses need to have the lpf_fast requirement. 

        This initialization code calculates the 'snorm_list_dels' list used in
        upd_in_avg_hsn, and also the number of hebbsnorm synapses.
    """
    snorm_list = []  # a list with all the presynaptic units
                     # providing hebbsnorm synapses
    snorm_dels = []  # a list with the delay steps for each connection from snorm_list
    for syn in unit.net.syns[unit.ID]:
        if syn.type is synapse_types.hebbsnorm:
            if not syn_reqs.lpf_fast in unit.net.units[syn.preID].syn_needs:
                raise AssertionError('inp_avg_hsn needs lpf_fast on presynaptic units')
            snorm_list.append(unit.net.units[syn.preID])
            snorm_dels.append(syn.delay_steps)
    n_hebbsnorm = len(snorm_list) # number of hebbsnorm synapses received
    snorm_list_dels = list(zip(snorm_list, snorm_dels)) # both lists zipped
    setattr(unit, 'inp_avg_hsn', 0.2)  # arbitrary initialization of the average input
    setattr(unit, 'n_hebbsnorm', n_hebbsnorm)
    setattr(unit, 'snorm_list_dels', snorm_list_dels)


def add_pos_inp_avg_hsn(unit):
    """ Add an average of the inputs arriving at hebbsnorm synapses with positive weights.

        More precisely, the sum of fast-LPF'd hebbsnorm inputs divided by the the number
        of hebbsnorm inputs, but only considering inputs with positive synapses.

        Since we are using the lpf_fast signals, all the presynaptic units with hebbsnorm
        synapses need to have the lpf_fast requirement. 

        In addition to creating the 'pos_inp_avg_hsn' variable, this initialization code
        obtains four lists: n_vec, snorm_syns, snorm_units, snorm_delys.
        snorm_syns : a list with the all the hebbsnorm synapses
        snorm_units : a list with the presynaptic units for each entry in snorm_syns
        snorm_delys : a list with the delays for each connection of snorm_syns
        n_vec : n_vec[i]=1 if the i-th connection of snorm_syns has positive weight,
                and n_vec[i]=0 otherwise. The 'n' vector from Pg.290 of Dayan&Abbott.
    """
    snorm_units = []  # a list with all the presynaptic units
                      # providing hebbsnorm synapses
    snorm_syns = []  # a list with the synapses for the list above
    snorm_delys = []  # a list with the delay steps for these synapses
    for syn in unit.net.syns[unit.ID]:
        if syn.type is synapse_types.hebbsnorm:
            if not syn_reqs.lpf_fast in unit.net.units[syn.preID].syn_needs:
                raise AssertionError('pos_inp_avg_hsn needs lpf_fast on presynaptic units')
            snorm_syns.append(syn)
            snorm_units.append(unit.net.units[syn.preID])
            snorm_delys.append(syn.delay_steps)
    setattr(unit, 'pos_inp_avg_hsn', .2) # arbitrary initialization
    setattr(unit, 'snorm_syns', snorm_syns)
    setattr(unit, 'snorm_units', snorm_units)
    setattr(unit, 'snorm_delys', snorm_delys)
    setattr(unit, 'n_vec', np.ones(len(snorm_units)))


def add_err_diff(unit):
    """ Adds the approximate derivative of the error signal.

        The err_diff requirement is used by the input_correlation_synapse (inp_corr).

        The err_idx_dels list (see below) is also initialized.
    """
    err_idx = [] # a list with the indexes of the units that provide errors
    pred_idx = [] # a list with the indexes of the units that provide predictors 
    err_dels = [] # a list with the delays for each unit in err_idx
    err_diff = 0. # approximation of error derivative, updated by upd_err_diff
    for syn in unit.net.syns[unit.ID]:
        if syn.type is synapse_types.inp_corr:
            if syn.input_type == 'error':
                err_idx.append(syn.preID)
                err_dels.append(syn.delay_steps)
            elif syn.input_type == 'pred': 
                pred_idx.append(syn.preID) # not currently using this list
            else:
                raise ValueError('Incorrect input_type ' + str(syn.input_type) + ' found in synapse')
    err_idx_dels = list(zip(err_idx, err_dels)) # both lists zipped
    setattr(unit, 'err_diff', err_diff)
    setattr(unit, 'err_idx_dels', err_idx_dels)


def add_sc_inp_sum_sqhsn(unit):
    """ Adds the scaled input sum of fast LPF'd inputs from sq_hebbsnorm synapses. """
    sq_snorm_units = [] # a list with all the presynaptic neurons providing
                        # sq_hebbsnorm synapses
    sq_snorm_syns = []  # a list with all the sq_hebbsnorm synapses
    sq_snorm_dels = []  # a list with the delay steps for the sq_hebbsnorm synapses
    for syn in unit.net.syns[unit.ID]:
        if syn.type is synapse_types.sq_hebbsnorm:
            sq_snorm_syns.append(syn)
            sq_snorm_units.append(unit.net.units[syn.preID])
            sq_snorm_dels.append(syn.delay_steps)
    u_d_syn = list(zip(sq_snorm_units, sq_snorm_dels, sq_snorm_syns)) # all lists zipped
    setattr(unit, 'sc_inp_sum_sqhsn', 0.2)  # an arbitrary initialization 
    setattr(unit, 'u_d_syn', u_d_syn) 


def add_diff_avg(unit):
    """ Adds the average of derivatives for inputs with diff_hebb_subsnorm synapses."""
    dsnorm_list = [] # list with all presynaptic units providing
                     # diff_hebb_subsnorm synapses
    dsnorm_dels = [] # list with delay steps for each connection in dsnorm_list
    for syn in unit.net.syns[unit.ID]:
        if syn.type is synapse_types.diff_hebbsnorm:
            dsnorm_list.append(unit.net.units[syn.preID])
            dsnorm_dels.append(syn.delay_steps)
    n_dhebbsnorm = len(dsnorm_list) # number of diff_hebbsnorm synapses received
    dsnorm_list_dels = list(zip(dsnorm_list, dsnorm_dels)) # both lists zipped
    setattr(unit, 'diff_avg', 0.2)  # arbitrary initialization
    setattr(unit, 'n_dhebbsnorm', n_dhebbsnorm)
    setattr(unit, 'dsnorm_list_dels', dsnorm_list_dels)


def add_lpf_mid_inp_sum(unit):
    """ Adds the low-pass filtered sum of inputs.

        This requirement is used by the exp_rate_dist_synapse model.

        As the name suggests, the sum of inputs is filtered with the tau_mid time
        constant. The inputs include transmission delays, but are not multiplied
        by the synaptic weights. The sum of inputs comes from the inp_vector
        requirement.

        The lpf_mid_inp_sum keeps a buffer with past values. It is re-initialized
        by unit.init_buffers.
    """
    if not hasattr(unit,'tau_mid'): 
        raise NameError( 'Synaptic plasticity requires unit parameter tau_mid, not yet set' )
    if not syn_reqs.inp_vector in unit.syn_needs:
        raise AssertionError('lpf_mid_inp_sum requires the inp_vector requirement to be set')
    setattr(unit, 'lpf_mid_inp_sum', unit.init_val) # arbitrary initialization
    setattr(unit, 'lpf_mid_inp_sum_buff', 
            np.array( [unit.init_val]*unit.steps, dtype=unit.bf_type))


def add_lpf_slow_mp_inp_sum(unit):
    """ Adds a slow LPF'd scaled sum of inputs for each input port.

        lpf_slow_mp_inp_sum will be a list whose i-th element will be the sum of all
        the inputs at the i-th port, low-pass filtered with the 'tau_slow' time
        constant. The mp_inputs requirement is used for this.

        The lpf_slow_mp_inp_sum requirement is used by units of the 
        "double_sigma_normal" type in order to normalize their inputs according to
        the average of their sum.
    """
    if not hasattr(unit,'tau_slow'): 
        raise NameError( 'Requirement lpf_slow_mp_inp_sum requires parameter tau_slow, not yet set' )
    if not syn_reqs.mp_inputs in unit.syn_needs:
        raise AssertionError('lpf_slow_mp_inp_sum requires the mp_inputs requirement')
    setattr(unit, 'lpf_slow_mp_inp_sum', [ 0.4 for _ in range(unit.n_ports) ])


def add_balance(unit):
    """ Adds two numbers called  below, and above.

        below = fraction of inputs with rate lower than the unit.
        above = fraction of inputs with rate higher than the unit.

        Those numbers are useful to produce a given firing rate distribtuion by the
        various trdc and ssrdc models.
    """
    if not syn_reqs.inp_vector in unit.syn_needs:
        raise AssertionError('balance requirement has the inp_vector requirement as a prerequisite')
    setattr(unit, 'below', 0.5)
    setattr(unit, 'above', 0.5)


def add_balance_mp(unit):
    """ Updates two numbers called  below, and above. Used in multiport units.

        below = fraction of inputs with rate lower than the unit.
        above = fraction of inputs with rate higher than the unit.

        Those numbers are useful to produce a given firing rate distribtuion among
        the population of units that connect to the 'rdc_port'.

        This is the same as upd_balance, but ports other than the rdc_port are ignored.
    """
    if not syn_reqs.mp_inputs in unit.syn_needs:
        raise AssertionError('balance_mp requirement has the mp_inputs requirement as a prerequisite')
    setattr(unit, 'below', 0.5)
    setattr(unit, 'above', 0.5)


def add_exp_scale(unit):
    """ Adds the 'scale_facs' list, which specifies a scale factor for each weight.

        The scale factors are calculated so that the network acquires an exponential
        distribution of firing rates.
    """
    if not syn_reqs.balance in unit.syn_needs:
        raise AssertionError('exp_scale requires the balance requirement to be set')
    if not syn_reqs.lpf_fast in unit.syn_needs:
        raise AssertionError('exp_scale requires the lpf_fast requirement to be set')
    scale_facs= np.tile(1., len(unit.net.syns[unit.ID])) # array with scale factors
    # exc_idx = numpy array with index of all excitatory units in the input vector 
    exc_idx = [ idx for idx,syn in enumerate(unit.net.syns[unit.ID]) if syn.w >= 0]
    # ensure the integer data type; otherwise you can't index numpy arrays
    exc_idx = np.array(exc_idx, dtype='uint32')
    # inh_idx = numpy array with index of all inhibitory units 
    inh_idx = [idx for idx,syn in enumerate(unit.net.syns[unit.ID]) if syn.w < 0]
    inh_idx = np.array(inh_idx, dtype='uint32')
    setattr(unit, 'exc_idx', exc_idx)
    setattr(unit, 'inh_idx', inh_idx)
    setattr(unit, 'scale_facs', scale_facs)


def add_exp_scale_mp(unit):
    """ Adds the synaptic scaling factors used in multiport ssrdc units.

        The algorithm is the same as upd_exp_scale, but only the inputs at the rdc_port
        are considered.
    """
    if not syn_reqs.balance_mp in unit.syn_needs:
        raise AssertionError('exp_scale_mp requires the balance_mp requirement to be set')
    if not syn_reqs.lpf_fast in unit.syn_needs:
        raise AssertionError('exp_scale_mp requires the lpf_fast requirement to be set')
    scale_facs_rdc = np.tile(1., len(unit.port_idx[unit.rdc_port])) # array with scale factors
    # exc_idx_rdc = numpy array with index of all excitatory units at rdc port
    exc_idx_rdc = [ idx for idx,syn in enumerate([unit.net.syns[unit.ID][i] 
                         for i in unit.port_idx[unit.rdc_port]]) if syn.w >= 0 ]
    # ensure the integer data type; otherwise you can't index numpy arrays
    exc_idx_rdc = np.array(exc_idx_rdc, dtype='uint32')
    setattr(unit, 'exc_idx_rdc', exc_idx_rdc)
    setattr(unit, 'scale_facs_rdc', scale_facs_rdc)


def add_slide_thresh(unit):
    """ Adds a 'sliding threshold' for single-port trdc sigmoidal units.
    
        The sliding threshold is meant to produce an exponential distribution of firing
        rates in a population of units. The first unit type to use trdc (Threshold-based
        Rate Distribution Control) was exp_dist_sig_thr, which uses this requirement.

        Since the requirement adjusts the 'thresh' attribute already present in
        sigmoidal models, this initialization code adds no variables.
    """
    if (not syn_reqs.balance in unit.syn_needs) and (not syn_reqs.balance_mp in unit.syn_needs):
        raise AssertionError('slide_thresh requires the balance(_mp) requirement to be set')


def add_slide_thresh_shrp(unit):
    """ Adds a sliding threshold that falls back to a default value when signalled.

        The sliding threshold is meant to produce an exponential distribution of firing
        rates in a population of units. Units using this requirement will have a
        'sharpen_port', and when its signal is smaller than 0.5 the trdc will cease,
        and the threshold will revert to a fixed value.

        The units that use this requirement are those derived from the trdc_sharp_base
        class.
    """
    if not syn_reqs.balance_mp in unit.syn_needs:
        raise AssertionError('slide_thresh_shrp requires the balance_mp requirement to be set')
    if not unit.multiport:
        raise AssertionError('The slide_thresh_shrp is for multiport units only')


def add_slide_thr_hr(unit):
    """ Adds a sliding threshold that aims to produce a harmonic pattern of firing rates.

        See the sliding_threshold_harmonic_rate_sigmoidal unit type for the
        meaning of this.
    """
    if not syn_reqs.mp_inputs in unit.syn_needs:
        raise AssertionError('slide_thr_hr requires the mp_inputs requirement to be set')
    if not unit.multiport:
        raise AssertionError('The slide_thr_hr requirment is for multiport units only')


def add_syn_scale_hr(unit):
    """ Adds factors to scale the synaptic weights, producing 'harmonic rates'.

        Too see what this means see the synaptic_scaling_harmonic_rate_sigmoidal
        unit type.
    """
    if not syn_reqs.mp_inputs in unit.syn_needs:
        raise AssertionError('syn_scale_hr requires the mp_inputs requirement to be set')
    if not unit.multiport:
        raise AssertionError('The syn_scale_hr requirment is for multiport units only')
    if not syn_reqs.lpf_fast in unit.syn_needs:
        raise AssertionError('syn_scale_hr requires the lpf_fast requirement to be set')
    # exc_idx_hr = numpy array with index of all excitatory units at hr port
    exc_idx_hr = [ idx for idx,syn in enumerate([unit.net.syns[unit.ID][i] 
                         for i in unit.port_idx[unit.hr_port]]) if syn.w >= 0 ]
    # ensure the integer data type; otherwise you can't index numpy arrays
    exc_idx_hr = np.array(exc_idx_hr, dtype='uint32')
    #scale_facs = np.tile(1., len(unit.net.syns[unit.ID])) # array with scale factors
    scale_facs_hr = np.tile(1., len(unit.port_idx[unit.hr_port])) # array with scale factors
    setattr(unit, 'exc_idx_hr', exc_idx_hr)
    setattr(unit, 'scale_facs_hr', scale_facs_hr)


def add_exp_scale_shrp(unit):
    """ Adds the scaling factors used in ssrdc_sharp units not using sort_rdc.

        This requirement is found in units that inherit from the ssrdc_sharp_base class.
    """
    if not syn_reqs.balance_mp in unit.syn_needs:
        raise AssertionError('exp_scale_shrp requires the balance_mp requirement to be set')
    if not unit.multiport:
        raise AssertionError('The exp_scale_shrp requirement is for multiport units only')
    if not syn_reqs.lpf_fast in unit.syn_needs:
        raise AssertionError('exp_scale_shrp requires the lpf_fast requirement to be set')
    scale_facs_rdc = np.tile(1., len(unit.port_idx[unit.rdc_port])) # array with scale factors
    # exc_idx_rdc = numpy array with index of all excitatory units at rdc port
    exc_idx_rdc = [ idx for idx,syn in enumerate([unit.net.syns[unit.ID][i] 
                         for i in unit.port_idx[unit.rdc_port]]) if syn.w >= 0 ]
    # ensure the integer data type; otherwise you can't index numpy arrays
    exc_idx_rdc = np.array(exc_idx_rdc, dtype='uint32')
    rdc_exc_ones = np.tile(1., len(exc_idx_rdc))
    setattr(unit, 'exc_idx_rdc', exc_idx_rdc)
    setattr(unit, 'rdc_exc_ones', rdc_exc_ones)
    setattr(unit, 'scale_facs_rdc', scale_facs_rdc)


def add_exp_scale_sort_mp(unit):
    """ Adds the scaling factors used in the sig_ssrdc unit when sort_rdc==True.  """
    if not unit.multiport:
        raise AssertionError('The exp_scale_sort_mp requirement is for multiport units only')
    scale_facs_rdc = np.tile(1., len(unit.port_idx[unit.rdc_port])) # array with scale factors
    # exc_idx_rdc = numpy array with index of all excitatory units at rdc port
    exc_idx_rdc = [ idx for idx,syn in enumerate([unit.net.syns[unit.ID][i] 
                         for i in unit.port_idx[unit.rdc_port]]) if syn.w >= 0 ]
    autapse = False
    autapse_idx = len(exc_idx_rdc) - 1
    for idx, syn in enumerate([unit.net.syns[unit.ID][eir] for eir in exc_idx_rdc]):
        if syn.preID == unit.ID: # if there is an excitatory autapse at the rdc port
            autapse_idx = idx
            autapse = True
            break
    # Gotta produce the array of ideal rates given the truncated exponential distribution
    if autapse:
        N = len(exc_idx_rdc)
    else:
        N = len(exc_idx_rdc) + 1 # an extra point for the fake autapse
    points = [ (k + 0.5) / (N + 1.) for k in range(N) ]
    ideal_rates = np.array([-(1./unit.c) * np.log(1.-(1.-np.exp(-unit.c))*pt) for pt in points])
    setattr(unit, 'scale_facs_rdc', scale_facs_rdc) 
    setattr(unit, 'exc_idx_rdc', exc_idx_rdc) 
    setattr(unit, 'autapse', autapse) 
    setattr(unit, 'autapse_idx', autapse_idx) 
    setattr(unit, 'ideal_rates', ideal_rates) 


def add_exp_scale_sort_shrp(unit):
    """ Adds the scaling factors used in ssrdc_sharp units where sort_rdc==False.  
    
        This requirement is found in units that inherit from the ssrdc_sharp_base class.
        This initialization function is identical to add_exp_scale_sort_mp
    """
    if not unit.multiport:
        raise AssertionError('The exp_scale_sort_mp requirement is for multiport units only')
    scale_facs_rdc = np.tile(1., len(unit.port_idx[unit.rdc_port])) # array with scale factors
    # exc_idx_rdc = numpy array with index of all excitatory units at rdc port
    exc_idx_rdc = [ idx for idx,syn in enumerate([unit.net.syns[unit.ID][i] 
                         for i in unit.port_idx[unit.rdc_port]]) if syn.w >= 0 ]
    autapse = False
    autapse_idx = len(exc_idx_rdc) - 1
    for idx, syn in enumerate([unit.net.syns[unit.ID][eir] for eir in exc_idx_rdc]):
        if syn.preID == unit.ID: # if there is an excitatory autapse at the rdc port
            autapse_idx = idx
            autapse = True
            break
    # Gotta produce the array of ideal rates given the truncated exponential distribution
    if autapse:
        N = len(exc_idx_rdc)
    else:
        N = len(exc_idx_rdc) + 1 # an extra point for the fake autapse
    points = [ (k + 0.5) / (N + 1.) for k in range(N) ]
    ideal_rates = np.array([-(1./unit.c) * np.log(1.-(1.-np.exp(-unit.c))*pt) for pt in points])
    setattr(unit, 'scale_facs_rdc', scale_facs_rdc) 
    setattr(unit, 'exc_idx_rdc', exc_idx_rdc) 
    setattr(unit, 'autapse', autapse) 
    setattr(unit, 'autapse_idx', autapse_idx) 
    setattr(unit, 'ideal_rates', ideal_rates) 


def add_error(unit):
    """ Adds the error value used by delta_linear units. """
    if not syn_reqs.mp_inputs in unit.syn_needs:
        raise AssertionError('The error requirement needs the mp_inputs requirement.')
    setattr(unit, 'error', 0.)
    setattr(unit, 'learning', 0.)


def add_inp_l2(unit):
    """ Adds the L2-norm of the vector with all inputs at port 0. 
    
        This requirement is used by delta_linear units to normalize their inputs.
    """
    if not syn_reqs.mp_inputs in unit.syn_needs:
        raise AssertionError('The inp_l2 requirement needs the mp_inputs requirement.')
    setattr(unit, 'inp_l2', 1.)


def add_norm_factor(unit):
    """ Adds the normalization factor for inhibitory and excitatory inputs on the model cell."""

    n_inh = 0 # count of inhibitory synapses 
    n_exc = 0 # count of excitatory synapses 
    for syn in unit.net.syns[unit.ID]:
        if syn.w < 0:
            n_inh += 1
        else:
            n_exc += 1

    if n_inh == 0:
        n_inh = 1
    if n_exc == 0:
        n_exc = 1
           
    setattr(unit, 's_inh', -unit.HYP/n_inh)
    setattr(unit, 's_exc', (1.+unit.OD)/n_exc)


#-------------------------------------------------------------------------------------
# Use of the following classes has been deprecated because they slow down execution
#-------------------------------------------------------------------------------------

class requirement():
    """ The parent class of requirement classes.  """
    
    def __init__(self, unit):
        """ The class constructor.

            Args:
                unio : a reference to the unit where the requirement is used.

        """
        self.val = None

    def update(self, time):
        pass

    def get(self):
        return self.val


class lpf_fast(requirement):
    """ Maintains a low-pass filtered version of the unit's activity.

        The name lpf_fast indicates that the time constant of the low-pass filter,
        whose name is 'tau_fast', should be relatively fast. In practice this is
        arbitrary.
        The user needs to set the value of 'tau_fast' in the parameter dictionary 
        that initializes the unit.

        An instance of this class is meant to be created by init_pre_syn_update 
        whenever the unit has the 'lpf_fast' requiremnt. In this case, the update
        method of this class will be included in the unit's 'functions' list, and 
        called at each simulation step by pre_syn_update.

        Additionally, when the unit has the 'lpf_fast' requirement, the init_buff
        method will be invoked by the unit's init_buffers method.
    """
    def __init__(self, unit):
        """ The class' constructor.
            Args:
                unit : the unit containing the requirement.
        """
        if not hasattr(unit,'tau_fast'): 
            raise NameError( 'Synaptic plasticity requires unit parameter tau_fast, not yet set' )
        self.val = unit.init_val
        self.unit = unit
        self.init_buff()
 
    def update(self, time):
        """ Update the lpf_fast variable. """
        #assert time >= self.unit.last_time, ['Unit ' + str(self.ID) + 
        #                                ' lpf_fast updated backwards in time']
        cur_act = self.unit.get_act(time)
        # This updating rule comes from analytically solving 
        # lpf_x' = ( x - lpf_x ) / tau
        # and assuming x didn't change much between self.last_time and time.
        # It seems more accurate than an Euler step lpf_x = lpf_x + (dt/tau)*(x - lpf_x)
        self.val = cur_act + ( (self.val - cur_act) * 
                                   np.exp( (self.unit.last_time-time)/self.unit.tau_fast ) )
        # update the buffer
        self.lpf_fast_buff = np.roll(self.lpf_fast_buff, -1)
        self.lpf_fast_buff[-1] = self.val

    def init_buff(self):
        """ Initialize the buffer with past values of lpf_fast. """
        self.lpf_fast_buff = np.array( [self.unit.init_val]*self.unit.steps, dtype=self.unit.bf_type)

    def get(self, steps):
        """ Get the fast low-pass filtered activity, as it was 'steps' simulation steps before. """
        return self.lpf_fast_buff[-1-steps]


class lpf_mid(requirement):
    """ Maintains a low-pass filtered version of the unit's activity.

        The name lpf_mid indicates that the time constant of the low-pass filter,
        whose name is 'tau_mid', should have an intermediate value. In practice 
        this is arbitrary.
        The user needs to set the value of 'tau_mid' in the parameter dictionary 
        that initializes the unit.

        An instance of this class is meant to be created by init_pre_syn_update 
        whenever the unit has the 'lpf_mid' requiremnt. In this case, the update
        method of this class will be included in the unit's 'functions' list, and 
        called at each simulation step by pre_syn_update.

        Additionally, when the unit has the 'lpf_mid' requirement, the init_buff
        method will be invoked by the unit's init_buffers method.
    """
    def __init__(self, unit):
        """ The class' constructor.
            Args:
                unit : the unit containing the requirement.
        """
        if not hasattr(unit,'tau_mid'): 
            raise NameError( 'Synaptic plasticity requires unit parameter tau_mid, not yet set' )
        self.val = unit.init_val
        self.unit = unit
        self.init_buff()
 
    def update(self, time):
        """ Update the lpf_fast variable. """
        #assert time >= self.unit.last_time, ['Unit ' + str(self.ID) + 
        #                                ' lpf_fast updated backwards in time']
        cur_act = self.unit.get_act(time)
        # This updating rule comes from analytically solving 
        # lpf_x' = ( x - lpf_x ) / tau
        # and assuming x didn't change much between self.last_time and time.
        # It seems more accurate than an Euler step lpf_x = lpf_x + (dt/tau)*(x - lpf_x)
        self.val = cur_act + ( (self.val - cur_act) * 
                                   np.exp( (self.unit.last_time-time)/self.unit.tau_mid ) )
        # update the buffer
        self.lpf_mid_buff = np.roll(self.lpf_mid_buff, -1)
        self.lpf_mid_buff[-1] = self.val

    def init_buff(self):
        """ Initialize the buffer with past values of lpf_fast. """
        self.lpf_mid_buff = np.array( [self.unit.init_val]*self.unit.steps, dtype=self.unit.bf_type)

    def get(self, steps):
        """ Get the fast low-pass filtered activity, as it was 'steps' simulation steps before. """
        return self.lpf_mid_buff[-1-steps]


class lpf_slow(requirement):
    """ Maintains a low-pass filtered version of the unit's activity.

        The name lpf_slow indicates that the time constant of the low-pass filter,
        whose name is 'tau_slow', should have a relatively large value. In practice 
        this is arbitrary.
        The user needs to set the value of 'tau_slow' in the parameter dictionary 
        that initializes the unit.

        An instance of this class is meant to be created by init_pre_syn_update 
        whenever the unit has the 'lpf_slow' requiremnt. In this case, the update
        method of this class will be included in the unit's 'functions' list, and 
        called at each simulation step by pre_syn_update.

        Additionally, when the unit has the 'lpf_slow' requirement, the init_buff
        method will be invoked by the unit's init_buffers method.
    """
    def __init__(self, unit):
        """ The class' constructor.
            Args:
                unit : the unit containing the requirement.
        """
        if not hasattr(unit,'tau_slow'): 
            raise NameError( 'Synaptic plasticity requires unit parameter tau_slow, not yet set' )
        self.val = unit.init_val
        self.unit = unit
        self.init_buff()
 
    def update(self, time):
        """ Update the lpf_fast variable. """
        #assert time >= self.unit.last_time, ['Unit ' + str(self.ID) + 
        #                                ' lpf_fast updated backwards in time']
        cur_act = self.unit.get_act(time)
        # This updating rule comes from analytically solving 
        # lpf_x' = ( x - lpf_x ) / tau
        # and assuming x didn't change much between self.last_time and time.
        # It seems more accurate than an Euler step lpf_x = lpf_x + (dt/tau)*(x - lpf_x)
        self.val = cur_act + ( (self.val - cur_act) * 
                                   np.exp( (self.unit.last_time-time)/self.unit.tau_slow ) )
        # update the buffer
        self.lpf_slow_buff = np.roll(self.lpf_slow_buff, -1)
        self.lpf_slow_buff[-1] = self.val

    def init_buff(self):
        """ Initialize the buffer with past values of lpf_fast. """
        self.lpf_slow_buff = np.array( [self.unit.init_val]*self.unit.steps, dtype=self.unit.bf_type)

    def get(self, steps):
        """ Get the fast low-pass filtered activity, as it was 'steps' simulation steps before. """
        return self.lpf_slow_buff[-1-steps]


class lpf(requirement):
    """ A low pass filter with a given time constant. """
    def __init__(self, unit):
        self.tau = unit.lpf_tau
        self.val = unit.init_val
        self.unit = unit
        self.init_buff()
 
    def update(self, time):
        """ Update the lpf_fast variable. """
        #assert time >= self.unit.last_time, ['Unit ' + str(self.ID) + 
        #                                ' lpf_fast updated backwards in time']
        cur_act = self.unit.get_act(time)
        # This updating rule comes from analytically solving 
        # lpf_x' = ( x - lpf_x ) / tau
        # and assuming x didn't change much between self.last_time and time.
        # It seems more accurate than an Euler step lpf_x = lpf_x + (dt/tau)*(x - lpf_x)
        self.val = cur_act + ( (self.val - cur_act) * 
                                   np.exp( (self.unit.last_time-time)/self.tau ) )
        # update the buffer
        self.buff = np.roll(self.buff, -1)
        self.buff[-1] = self.val

    def init_buff(self):
        """ Initialize the buffer with past values. """
        self.buff = np.array( [self.unit.init_val]*self.unit.steps, dtype=self.unit.bf_type)

    def get(self, steps):
        """ Get the fast low-pass filtered activity, as it was 'steps' simulation steps before. """
        return self.lpf_fast_buff[-1-steps]


class sq_lpf_slow(requirement):
    """ A low pass filtered version of the squared activity.
        
        As the name implies, the filter uses the "slow" time constant 'tau_slow'.
        The purpose of this is to have a mean value of the square of the activity,
        as used in some versions of the BCM learning rule. Accordingly, this 
        requirement is used byt the bcm_synapse class.
    """
    def __init__(self, unit):
        if not hasattr(unit,'tau_slow'): 
            raise NameError( 'sq_lpf_slow requires unit parameter tau_slow, not yet set' )
        self.tau = unit.tau_slow
        self.val = unit.init_val
        self.unit = unit

    def update(self,time):
        """ Update the sq_lpf_slow variable. """
        #assert time >= self.unit.last_time, ['Unit ' + str(self.unit.ID) + 
        #                                ' sq_lpf_slow updated backwards in time']
        cur_sq_act = self.unit.get_act(time)**2.  
        # This updating rule comes from analytically solving 
        # lpf_x' = ( x - lpf_x ) / tau
        # and assuming x didn't change much between self.last_time and time.
        # It seems more accurate than an Euler step lpf_x = lpf_x + (dt/tau)*(x - lpf_x)
        self.val = cur_sq_act + ( (self.val - cur_sq_act) * 
                                  np.exp( (self.unit.last_time-time)/self.tau ) )

class inp_vector(requirement):
    """ A numpy array with the unit's inputs at the start of the current simulation step.

        The inputs are not multiplied by synaptic weights, and come with their 
        appropriate delays.

        This input vector is used by other synaptic requirements, namely lpf_mid_inp_sum,
        balance, and exp_scale. In this last requirement, it is used to obtain the 'mu'
        factor used by the rule.
    """
    def __init__(self, unit):
        self.unit = unit
        self.val = np.tile(unit.init_val, len(unit.net.syns[unit.ID]))
        self.uid = unit.ID

    def update(self, time):
        self.val = np.array([ fun(time - dely) for dely,fun in 
                   zip(self.unit.net.delays[self.uid], self.unit.net.act[self.uid]) ])


class mp_inputs(requirement):
    """ Maintains a list with all the inputs, in the format of get_mp_inputs method. 

        In fact, the list is updated using the get_mp_inputs method. Some requirements
        like mp_balance and lpf_slow_mp_inp_sum use the output of get_mp_inputs, and
        the mp_inputs requirement saves computations by ensuring that get_mp_inputs
        only gets called once per simulation step.

        Repeating the docsting of unit.get_mp_inputs:
        This method is for units where multiport = True, and that have a port_idx attribute.
        The i-th element of the returned list is a numpy array containing the raw (not multiplied
        by the synaptic weight) inputs at port i. The inputs include transmision delays.
    """
    def __init__(self, unit):
        if not hasattr(unit,'port_idx'): 
            raise NameError( 'the mp_inputs requirement is for multiport units with a port_idx list' )
        self.val = [] 
        for prt_lst in unit.port_idx:
            self.val.append(np.array([unit.init_val for _ in range(len(prt_lst))]))
        self.unit = unit

    def update(self, time):
        self.val = self.unit.get_mp_inputs(time)
        

class inp_avg_hsn(requirement):
    """ Provides an average of the inputs arriving at hebbsnorm synapses.

        More precisely, the sum of fast-LPF'd hebbsnorm inputs divided by the the number
        of hebbsnorm inputs.

        Since we are using the lpf_fast signals, all the presynaptic units with hebbsnorm
        synapses need to have the lpf_fast requirement. 
    """
    def __init__(self, unit):  
        self.snorm_list = []  # a list with all the presynaptic units
                              # providing hebbsnorm synapses
        self.snorm_dels = []  # a list with the delay steps for each connection from snorm_list
        for syn in unit.net.syns[unit.ID]:
            if syn.type is synapse_types.hebbsnorm:
                if not syn_reqs.lpf_fast in unit.net.units[syn.preID].syn_needs:
                    raise AssertionError('inp_avg_hsn needs lpf_fast on presynaptic units')
                self.snorm_list.append(unit.net.units[syn.preID])
                self.snorm_dels.append(syn.delay_steps)
        self.n_hebbsnorm = len(self.snorm_list) # number of hebbsnorm synapses received
        self.val = 0.2  # an arbitrary initialization of the average input value
        self.snorm_list_dels = list(zip(self.snorm_list, self.snorm_dels)) # both lists zipped

    def update(self, time):
        self.val = sum([u.get_lpf_fast(s) for u,s in self.snorm_list_dels]) / self.n_hebbsnorm


class pos_inp_avg_hsn(requirement):
    """ Provides an average of the inputs arriving at hebbsnorm synapses with positive weights.

        More precisely, the sum of fast-LPF'd hebbsnorm inputs divided by the the number
        of hebbsnorm inputs, but only considering inputs with positive synapses.

        Since we are using the lpf_fast signals, all the presynaptic units with hebbsnorm
        synapses need to have the lpf_fast requirement. 
    """
    def __init__(self, unit):  
        self.snorm_units = []  # a list with all the presynaptic units
                               # providing hebbsnorm synapses
        self.snorm_syns = []  # a list with the synapses for the list above
        self.snorm_delys = []  # a list with the delay steps for these synapses
        for syn in unit.net.syns[unit.ID]:
            if syn.type is synapse_types.hebbsnorm:
                if not syn_reqs.lpf_fast in unit.net.units[syn.preID].syn_needs:
                    raise AssertionError('pos_inp_avg_hsn needs lpf_fast on presynaptic units')
                self.snorm_syns.append(syn)
                self.snorm_units.append(unit.net.units[syn.preID])
                self.snorm_delys.append(syn.delay_steps)
        self.val = 0.2  # an arbitrary initialization of the average input value
        self.n_vec = np.ones(len(self.snorm_units)) # the 'n' vector from Pg.290 of Dayan&Abbott

    def update(self, time):
        # first, update the n vector from Eq. 8.14, pg. 290 in Dayan & Abbott
        self.n_vec = [ 1. if syn.w>0. else 0. for syn in self.snorm_syns ]
        
        self.val = sum([n*(u.get_lpf_fast(s)) for n,u,s in 
                                zip(self.n_vec, self.snorm_units, self.snorm_delys)]) / sum(self.n_vec)


