#!/usr/bin/env python3
# vim:fileencoding=utf-8
"""
unit_tests.py
A suite of unit tests for draculab.
"""

from draculab import *
import re  # regular expressions module, for the load_data function
import matplotlib.pyplot as plt   # more plotting tools
import numpy as np
import time
import unittest
from scipy.interpolate import interp1d


def load_data(filename):
    """
    Receives the name of a datafile saved in XPP's .dat format, 
    and returns numpy arrays with the data from the columns
    The format is simply putting in each line the values of time and state
    variables separated by spaces. Time is the first column.
    """
    # Counting the lines and columns in order to allocate the numpy arrays
    file_obj = open(filename, 'r')
    nlines = sum(1 for line in file_obj)
    file_obj.seek(0) # resetting the file object's position
    n_columns = len(re.split(' .', file_obj.readline()))
    # XPP puts an extra space at the end of the line, so I used ' .' instead of ' '
    # We'll store everything in one tuple of numpy arrays, one per column
    values = tuple(np.zeros(nlines) for i in range(n_columns))
    file_obj.seek(0) # resetting the file object's position
    for idx, line in enumerate(file_obj):
        listed = re.split(' ', re.split(' $', line)[0]) # the first split removes 
                                                        # the trailing space
        for jdx, value in enumerate(listed):  
            values[jdx][idx] = float(value) 
    file_obj.close()
    return values


def align_points(times, data_times, data_points):
    """ Returns the data_points interpolated at the points in 'times'. """
    data_fun = interp1d(data_times, data_points)
    return np.array([data_fun(t) for t in times])


class test_comparison_1(unittest.TestCase):
    """ An automated version of the first comparison in test2.ipynb . """

    @classmethod
    def setUpClass(self):
        self.tolerance = 0.0025 # test will fail if error larger than this
        # The .dat files should be in the same directory
        self.xpp_dat = load_data('./sim1oderun.dat')
        self.matlab_dat = load_data('./sim1matrun.txt')

    def setUp(self):
        self.net = self.create_test_network_1()

    def create_test_network_1(self, integ='odeint'):
        """ Returns a network that should produce the test data. 
        
            integ a string specifying the integrator to use.
        """
        ######### 1) Create a network
        net_params = {'min_delay' : 0.2, 'min_buff_size' : 50 } 
        n1 = network(net_params)
        ######### 2) Put some units in the network
        # default parameters for the units
        pars = { 'coordinates' : np.zeros(3),
                'delay' : 1., 'init_val' : 0.5, 'tau_fast' : 1.,
                'slope' : 1., 'thresh' : 0.0, 'tau' : 0.02,
                'mu' : 0., 'sigma' : 0., 'lambda' : 1.,
                'type' : unit_types.source, 'function' : lambda x : None } 
        inputs = n1.create(2,pars) # creating two input sources
        # setting the input functions
        n1.units[inputs[0]].set_function(lambda t: 0.5*t)
        n1.units[inputs[1]].set_function(lambda t: -4.*np.sin(t))
        pars['integ_meth'] = integ
        # setting units for noisy integrators
        if integ in ['euler_maru', 'exp_euler']:
            pars['type'] = unit_types.noisy_sigmoidal
        else:
            pars['type'] = unit_types.sigmoidal
        sig_units = n1.create(2,pars) # creating two sigmoidal units
        if integ == 'euler_maru': # we have to force this if lambda!=0
            for unit in [n1.units[uid] for uid in sig_units]:
                unit.update = unit.euler_maru_update
        ######### 3) Connect the units in the network
        conn_spec = {'rule' : 'all_to_all', 'delay' : 1.,
                    'allow_autapses' : False } 
        syn_pars = {'init_w' : 1., 'lrate' : 0.0, 
                    'type' : synapse_types.oja} 
        n1.connect([inputs[0]], [sig_units[0]], conn_spec, syn_pars)
        conn_spec['delay'] = 2.
        n1.connect([inputs[1]], [sig_units[0]], conn_spec, syn_pars)
        conn_spec['delay'] = 5.
        n1.connect([sig_units[0]], [sig_units[1]], conn_spec, syn_pars)
        conn_spec['delay'] = 6.
        n1.connect([sig_units[1]], [sig_units[0]], conn_spec, syn_pars)
        ######## 4) Return
        return n1

    def max_diff_1(self, dracu, xpp, matlab):
        """ Obtain the maximum difference in the dracu time series. """
        # interpolate the XPP and Matlab data so it is at
        # the same time points as the draculab data
        xpp_points1 = align_points(dracu[0], xpp[0], xpp[1])
        matlab_points1 = align_points(dracu[0], matlab[0], matlab[1])
        xpp_points2 = align_points(dracu[0], xpp[0], xpp[2])
        matlab_points2 = align_points(dracu[0], matlab[0], matlab[2])
        
        max_diff_xpp1 = max(np.abs(xpp_points1 - dracu[1][2]))
        max_diff_xpp2 = max(np.abs(xpp_points2 - dracu[1][3]))
        max_diff_matlab1 = max(np.abs(matlab_points1 - dracu[1][2]))
        max_diff_matlab2 = max(np.abs(matlab_points2 - dracu[1][3]))
        return max(max_diff_xpp1, max_diff_xpp2, max_diff_matlab1, max_diff_matlab2)

    def test_network_1(self):
        """ Test if draculab, XPP and Matlab agree for network 1. """
        sim_dat = self.net.run(20.)
        max_diff = self.max_diff_1(sim_dat, self.xpp_dat, self.matlab_dat)
        self.assertTrue(max_diff < self.tolerance) 

    def test_network_1_flat(self):
        """ Test if flat draculab, XPP and Matlab agree for network 1. """
        sim_dat = self.net.flat_run(20.)
        max_diff = self.max_diff_1(sim_dat, self.xpp_dat, self.matlab_dat)
        self.assertTrue(max_diff < self.tolerance) 

    def test_network_1_all_integrators(self):
        """ Same test, different integrators. """
        integ_list = ['odeint', 'solve_ivp', 'euler', 'euler_maru', 'exp_euler']
        for integ in integ_list:
            net = self.create_test_network_1(integ)
            sim_dat = net.run(20.)
            max_diff = self.max_diff_1(sim_dat, self.xpp_dat, self.matlab_dat)
            self.assertTrue(max_diff < self.tolerance, 
                            msg = integ + ' integrator failed') 

    def test_network_1_all_integrators_flat(self):
        """ Same test, different integrators. """
        # currently the flat network does not support 'odeint' or 'solve_ivp'.
        # moreover, this is not configured to force 'euler_maru' for flat networks
        integ_list = ['euler', 'euler_maru', 'exp_euler']
        for integ in integ_list:
            net = self.create_test_network_1(integ)
            sim_dat = net.flat_run(20.)
            max_diff = self.max_diff_1(sim_dat, self.xpp_dat, self.matlab_dat)
            self.assertTrue(max_diff < self.tolerance, 
                            msg = integ + ' integrator failed') 

class test_comparison_2(unittest.TestCase):
    """ An automatic version of the second comparison in test2.ipynb. """

    @classmethod
    def setUpClass(self):
        self.tolerance = 0.01 # test will fail if difference is larger than this
        # The .dat files should be in the same directory
        self.xpp_data = load_data('./sim3oderun5.dat')  # ran in XPP with lrate = 0.5

    def create_test_network_2(self, custom_fi=False):
        """ Creates a draculab network equivalent of the one in sim3.ode . 
        
            When running XPP, set nUmerics -> Dt to 0.01 .

            custom_fi == True causes the network to use custom_fi units,
            as in test 2a of test2.ipynb.
        """
        ######### 1) Create a network
        net_params = {'min_delay' : 0.1, 'min_buff_size' : 5, 'rtol' : 1e-4, 'atol' : 1e-4 } # parameter dictionary for the network
        n2 = network(net_params)
        ######### 2) Put some units in the network
        # default parameters for the units
        pars = { 'init_val' : 0.5, 'tau_fast' : 1.,
                'slope' : 1., 'thresh' : 0.0, 'tau' : 0.02,
                'type' : unit_types.source, 'function' : lambda x : None } 
        inputs = n2.create(5,pars) # creating five input sources
        # setting the input functions
        n2.units[inputs[0]].set_function(lambda t: 0.5*np.sin(t))
        n2.units[inputs[1]].set_function(lambda t: -0.5*np.sin(2*t))
        n2.units[inputs[2]].set_function(lambda t: 0.5*np.sin(3*t))
        n2.units[inputs[3]].set_function(lambda t: -0.5*np.sin(t))
        n2.units[inputs[4]].set_function(lambda t: 2.0*np.sin(t))
        if custom_fi:
            sig_f = lambda x: 1. / (1. + np.exp( -1.*(x - 0.0) ))
            pars['type'] = unit_types.custom_fi
            pars['tau'] = 0.02
            pars['function'] = sig_f
        else:
            pars['type'] = unit_types.sigmoidal
        sig_units = n2.create(5,pars) # creating sigmoidal units
        ######### 3) Connect the units in the network
        conn_spec = {'rule' : 'all_to_all', 'delay' : 1.,
                    'allow_autapses' : False} # connection specification dictionary
        syn_pars = {'init_w' : 1., 'lrate' : 0.5, 
                    'type' : synapse_types.static} # synapse parameters dictionary
        # In the XPP code, projections to unit X have a delay X
        # and synapses from unit X have a weight 2*0.X,
        for idx_to, unit_to in enumerate(sig_units):
            conn_spec['delay'] = float(idx_to+1)
            n2.connect([inputs[idx_to]], [unit_to], conn_spec, syn_pars)
            if idx_to == 4: # the last unit has oja synapses in connections from sigmoidals
                syn_pars['type'] = synapse_types.oja
            for idx_from, unit_from in enumerate(sig_units):
                if unit_from != unit_to:
                    syn_pars['init_w'] = 0.2*(idx_from+1)
                    n2.connect([unit_from], [unit_to], conn_spec, syn_pars)
        ######### 4) Return
        return n2

    def max_diff_2(self, dracu, xpp):
        """ Obtain the maximum difference in the dracu time series. """
        xpp_points = [ [] for _ in range(5) ]
        for i in range(5):
            xpp_points[i] = align_points(dracu[0], xpp[0], xpp[i+1])
        return max( [max(np.abs( x - d )) for x,d in zip(dracu[1][5:10], xpp_points)] )

    def test_network_2(self):
        """ Compare the output of sim3.ode with the draculab equivalent. """
        ####### Test the regular run
        net = self.create_test_network_2()
        sim_dat = net.run(10.)
        max_diff = self.max_diff_2(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance)

    def test_network_2_flat(self):
        """ Compare the output of sim3.ode with the flat draculab equivalent. """
        ####### Test the flat run
        net = self.create_test_network_2()
        sim_dat = net.flat_run(10.)
        max_diff = self.max_diff_2(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance)

    def test_network_2_custom(self):
        """ Compare the output of sim3.ode with the draculab equivalent. """
        ####### Test the regular run with custom_fi units
        net = self.create_test_network_2(custom_fi=True)
        sim_dat = net.run(10.)
        max_diff = self.max_diff_2(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance)

    def test_network_2_custom_flat(self):
        """ Compare the output of sim3.ode with the flat draculab equivalent. """
        ####### Test the flat run with custom_fi units
        net = self.create_test_network_2(custom_fi=True)
        sim_dat = net.flat_run(10.)
        max_diff = self.max_diff_2(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance)


class test_comparison_3(unittest.TestCase):
    """ The comparison with sim4a.ode in test2.ipynb. """

    @classmethod
    def setUpClass(self):
        self.tolerance = 0.06 # test will fail if difference is larger than this
        self.noisy_tol = 0.5 # when noise is added
        # The .dat files should be in the same directory
        self.xpp_data = load_data('./sim4aoderun.dat')  

    def create_test_network_3(self, noisy=False, sigma=0.):
        """ Creates a draculab network equivalent of the one in sim4a.ode . """
        ######### 1) Create a network
        net_params = {'min_delay' : .5, 'min_buff_size' : 50 } # parameter dictionary for the network
        n3 = network(net_params)
        ######### 2) Put some units in the network
        # default parameters for the units
        pars = { 'coordinates' : [np.array([0.,1.])]*5, 
                'lambda': 1., 'mu':0., 'sigma':sigma,
                'delay' : 2., 'init_val' : 0.5,
                'slope' : 1., 'thresh' : 0.0, 'tau' : 0.02,
                'type' : unit_types.source, 'function' : lambda x: None} 
        inputs = n3.create(5,pars) # creating five input sources
        # setting the input functions
        n3.units[inputs[0]].set_function(lambda t: np.sin(t))
        n3.units[inputs[1]].set_function(lambda t: np.sin(2*t))
        n3.units[inputs[2]].set_function(lambda t: np.sin(3*t))
        n3.units[inputs[3]].set_function(lambda t: np.sin(4*t))
        n3.units[inputs[4]].set_function(lambda t: np.sin(5*t))
        if noisy:
            pars['type'] = unit_types.noisy_linear
        else:
            pars['type'] = unit_types.linear
        sig_units = n3.create(5,pars) # creating units
        ######### 3) Connect the units in the network
        conn_spec = {'rule' : 'all_to_all', 'delay' : {'distribution' : 'uniform', 'low' : 1., 'high' : 1.},
                    'allow_autapses' : False } # connection specification dictionary
        syn_pars = {'init_w' : 0.5, 'lrate' : 0.0, 
                    'type' : synapse_types.static} # synapse parameters dictionary
        # In the XPP code, projections from inputs have delay 1 and weight 1,
        # whereas projections from sigmoidals have delay 2 and weight 0.3
        for inp_unit, sig_unit in zip(inputs,sig_units):
            n3.connect([inp_unit], [sig_unit], conn_spec, syn_pars)
        conn_spec['delay'] = 2.
        syn_pars['init_w'] = 0.3
        n3.connect(sig_units, sig_units, conn_spec, syn_pars)
        ######### 4) Return
        return n3

    def max_diff_3(self, dracu, xpp):
        """ Obtain the maximum difference in the dracu time series. """
        xpp_points = [ [] for _ in range(5) ]
        for i in range(5):
            xpp_points[i] = align_points(dracu[0], xpp[0], xpp[i+1])
        return max( [max(np.abs( x - d )) for x,d in zip(dracu[1][5:10], xpp_points)] )

    def test_network_3(self):
        """ Compare the output of sim4a.ode with the draculab equivalent. """
        net = self.create_test_network_3()
        sim_dat = net.run(10.)
        max_diff = self.max_diff_3(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance)

    def test_network_3_flat(self):
        """ Compare the output of sim4a.ode with the flat draculab equivalent. """
        net = self.create_test_network_3()
        sim_dat = net.flat_run(10.)
        max_diff = self.max_diff_3(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance)

    def test_network_3_exp_euler(self):
        """ Compare the output of sim4a.ode, now using noisy_linear units . """
        net = self.create_test_network_3(noisy=True)
        sim_dat = net.run(10.)
        max_diff = self.max_diff_3(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance,
                        msg='exp_euler test failed with max_diff='+str(max_diff))

    def test_network_3_exp_euler_flat(self):
        """ Compare the output of sim4a.ode, now using noisy_linear units and flat. """
        net = self.create_test_network_3(noisy=True)
        sim_dat = net.flat_run(10.)
        max_diff = self.max_diff_3(sim_dat,self.xpp_data)
        self.assertTrue(max_diff < self.tolerance)

    def test_network_3_exp_euler_noisy(self):
        """ Compare the output of sim4a.ode, with actual noise in the unit. """ 
        net = self.create_test_network_3(noisy=True, sigma=0.5)
        sim_dat = net.run(10.)
        max_diff = self.max_diff_3(sim_dat,self.xpp_data)
        self.assertTrue(max_diff > self.tolerance and max_diff < self.noisy_tol,
                        msg = 'noisy exp_euler had max_diff'+str(max_diff))

    def test_network_3_exp_euler_noisy_flat(self):
        """ Compare the output of sim4a.ode, with actual noise in the unit. """ 
        net = self.create_test_network_3(noisy=True, sigma=0.5)
        sim_dat = net.flat_run(10.)
        max_diff = self.max_diff_3(sim_dat,self.xpp_data)
        self.assertTrue(max_diff > self.tolerance and max_diff < self.noisy_tol)


class eigenvalue_test(unittest.TestCase):
    """ Test 4 synapse types that extract the leading eigenvalue. """

    @classmethod
    def setUpClass(self):
        self.min_cos = 0.8 # test will fail if cosine is smaller than this
        ####### SETTING THE INPUT FUNCTIONS
        ### You are going to present 4 input patterns that randomly switch over time.
        ### Imagine the 9 inputs arranged in a grid, like a tic-tac-toe board, numbered
        ### from left to right and from top to bottom:
        ### 1 2 3
        ### 4 5 6
        ### 7 8 9
        ### You'll have input patterns
        ### 0 X 0   0 0 0   X 0 X   0 X 0
        ### 0 X 0   X X X   0 0 0   X 0 X
        ### 0 X 0   0 0 0   X 0 X   0 X 0
        ### The input is always a normalized linear combination of one or two of these 
        ### patterns. Pattern pat1 is presented alone for t_pat time units, and then
        ### there is a transition period during which pat1 becomes pat2 by presenting
        ### at time t an input 
        ### c*(t_pat+t_trans - t)*pat1 + c*(t - tpat)*pat2
        ### where c = 1/t_trans, and t_trans is the duration of the transition period. 
        ### At time t_pat+t_trans, pat2 is presented by itself for t_pat time units.
        ### 
        # here are the patterns as arrays
        self.patterns = [np.zeros(9) for i in range(4)]
        self.patterns[0] = np.array([0., 1., 0., 0., 1., 0., 0., 1., 0.])/3.
        self.patterns[1] = np.array([0., 0., 0., 1., 1., 1., 0., 0., 0.])/3.
        self.patterns[2] = np.array([1., 0., 1., 0., 0., 0., 1., 0., 1.])/4.
        self.patterns[3] = np.array([0., 1., 0., 1., 0., 1., 0., 1., 0.])/4.
        ####### THE LEADING EIGENVECTOR
        # The code that obtains this is in test3,4,5.ipynb
        self.max_evector = [0.0000, 0.4316, 0.0000, 0.4316, 0.5048, 
                            0.4316, 0.0000, 0.4316, 0.0000]

    def make_fun1(self, idx, cur_pat):
        """ This creates a constant function with value: patterns[cur_pat][idx]
            thus avoiding a scoping problem that is sometimes hard to see:
            https://eev.ee/blog/2011/04/24/gotcha-python-scoping-closures/
        """
        fun = lambda t : self.patterns[cur_pat][idx]
        return fun
    
    def make_fun2(self, idx, last_t, cur_pat, next_pat, t_trans):
        """ Creates a function for the pattern transition. """
        fun = lambda t : self.c * ( (t_trans - (t-last_t))*self.patterns[cur_pat][idx] +
                            (t-last_t)*self.patterns[next_pat][idx] )
        return fun

    def create_network(self, syn_type=synapse_types.oja):
        """ Creates a network for a test. """
        ######### 1) Create a network
        net_params = {'min_delay' : 0.05, 'min_buff_size' : 5 } 
        n1 = network(net_params)
        ######### 2) Put some units in the network
        # default parameters for the units
        pars = { 'function' : lambda x : None,
                'delay' : 1., 'init_val' : 0.5, 'tau_fast' : 1.,
                'slope' : 1., 'thresh' : 0.0, 'tau' : 0.02,
                'type' : unit_types.source } 
        self.inputs = n1.create(9,pars) # creating nine input sources
        pars['type'] = unit_types.linear
        self.unit = n1.create(1,pars) # creating one linear unit
        ######### 3) Connect the units in the network
        conn_spec = {'rule' : 'all_to_all', 'delay' : 1.,
                    'allow_autapses' : False} 
        syn_pars = {'init_w' : {'distribution':'uniform', 'low':0.1, 'high':0.5}, 
                    'lrate' : 0.02, 'type' : syn_type} 
        n1.connect(self.inputs, self.unit, conn_spec, syn_pars)
        ######## 4) Return
        self.net = n1

    def run_net(self, n_pres=80, t_pat=10., t_trans=4.):
        """ Simulate 'n_pres' pattern presentations.

        Each pattern is presented for t_pat time unts, and transitions
        between patterns last t_trans time units.
        """
        self.c = 1/t_trans # auxiliary variable
        cur_pat = np.random.randint(4)  # pattern currently presented
        next_pat = np.random.randint(4) # next pattern to be presented
        last_t = 0.

        for pres in range(n_pres):
        # For each cycle you'll set the input functions and simulate, once with
        # a single pattern, # once with a mix of patterns, as described above
            # first, we present a single pattern
            for u in range(9):
                self.net.units[self.inputs[u]].set_function( self.make_fun1(u, cur_pat) )
            sim_dat = self.net.flat_run(t_pat)  # simulating
            last_t = self.net.sim_time # simulation time after last pattern presentation
            # now one pattern turns into the next
            for u in range(9):
                self.net.units[self.inputs[u]].set_function(self.make_fun2(u, last_t, cur_pat, next_pat, t_trans))
            sim_dat = self.net.flat_run(t_trans) # simulating
            # choose the pattern you'll present next
            cur_pat = next_pat
            next_pat = np.random.randint(4)
            
    def test_oja_synapse(self):
        self.create_network(syn_type=synapse_types.oja) # initializes self.net
        self.run_net()
        weights = np.array(self.net.units[self.unit[0]].get_weights(self.net.sim_time))
        cos = sum(self.max_evector*weights) / (np.linalg.norm(self.max_evector)*np.linalg.norm(weights))
        self.assertTrue(self.min_cos < cos, 
                        msg='Oja synapse failed with cosine: '+str(cos))


if __name__=='__main__':
    unittest.main()
