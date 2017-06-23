''' 
network.py
The network class used in the sirasi simulator.
'''

from sirasi import unit_types, synapse_types, syn_reqs  # names of models and requirements
from units import *
from synapses import *
import numpy as np
import random # to create random connections

''' This class has the tools to build a network.
    First, you create an instance of 'network'; 
    second, you use the create() method to add units;
    third, you use set_function() for source units, which provide inputs;
    fourth, you use the connect() method to connect the units, 
    finally you use the run() method to run a simulation.
'''
class network():
    def __init__(self, params):
        self.sim_time = 0.0  # current simulation time [ms]
        self.n_units = 0     # current number of units in the network
        self.units = []      # list with all the unit objects
        # The next 3 lists implement the connectivity of the network
        self.delays = [] # delays[i][j] is the delay of the j-th connection to unit i in [ms]
        self.act = []    # act[i][j] is the function from which unit i obtains its j-th input
        self.syns = []   # syns[i][j] is the synapse object for the j-th connection to unit i
        self.min_delay = params['min_delay'] # minimum transmission delay [ms]
        self.min_buff_size = params['min_buff_size']  # number of values stored during a minimum delay period
        
    def create(self, n, params):
        # create 'n' units of type 'params['type']' and parameters from 'params'
        # If you want one of the parameters to have particular values for each unit, you can have a list
        # (or numpy array) of length 'n' in the corresponding 'params' entry
        assert (type(n) == int) and (n > 0), 'Number of units must be a positive integer'
        assert self.sim_time == 0., 'Units are being created when the simulation time is not zero'

        # Any entry in 'params' other than 'coordinates' and 'type' 
        # should either be a scalar, a list of length 'n', or a numpy array of length 'n'
        listed = [] # the entries in 'params' specified with a list
        for par in params:
            if par != 'coordinates' and par != 'type':
                if (type(params[par]) is list) or (type(params[par]) is np.ndarray):
                    if len(params[par]) == n:
                        listed.append(par)
                    else:
                        raise ValueError('Found parameter list of incorrect size during unit creation')
                elif (type(params[par]) != float) and (type(params[par]) != int):
                    raise TypeError('Found a parameter of the wrong type during unit creation')
                    
        params_copy = params.copy() # The 'params' dictionary that a unit receives in its constructor
                                    # should only contain scalar values. params_copy won't have lists
        # Creating the units
        unit_list = list(range(self.n_units, self.n_units + n))
        if params['type'] == unit_types.source:
            default_fun = lambda x: None  # source units start with a null function
            for ID in unit_list:
                for par in listed:
                    params_copy[par] = params[par][ID-self.n_units]
                self.units.append(source(ID, params_copy, default_fun, self))
        elif params['type'] == unit_types.sigmoidal:
            for ID in unit_list:
                for par in listed:
                    params_copy[par] = params[par][ID-self.n_units]
                self.units.append(sigmoidal(ID, params_copy, self))
        elif params['type'] == unit_types.linear:
            for ID in unit_list:
                for par in listed:
                    params_copy[par] = params[par][ID-self.n_units]
                self.units.append(linear(ID, params_copy, self))
        else:
            raise NotImplementedError('Attempting to create a unit with an unknown model type.')
        
        self.n_units += n
        # putting n new slots in the delays, act, and syns lists
        self.delays += [[] for i in range(n)]
        self.act += [[] for i in range(n)]
        self.syns += [[] for i in range(n)]
        # note:  [[]]*n causes all empty lists to be the same object 
        return unit_list
    
    def connect(self, from_list, to_list, conn_spec, syn_spec):
        # connect the units in the 'from_list' to the units in the 'to_list' using the
        # connection specifications in the 'conn_spec' dictionary, and the
        # synapse specfications in the 'syn_spec' dictionary
        # The current version always allows multapses
        
        # A quick test first
        if (np.amax(from_list + to_list) > self.n_units-1) or (np.amin(from_list + to_list) < 0):
            raise ValueError('Attempting to connect units with an ID out of range')
       
        # Let's find out the synapse type
        if syn_spec['type'] == synapse_types.static:
            syn_class = static_synapse
        elif syn_spec['type'] == synapse_types.oja:
            syn_class = oja_synapse
        elif syn_spec['type'] == synapse_types.antihebb:
            syn_class = anti_hebbian_synapse
        else:
            raise ValueError('Attempting connect with an unknown synapse type')
        
        # The units connected depend on the connectivity rule in conn_spec
        # We'll specify  connectivity by creating a list of 2-tuples with all the
        # pairs of units to connect
        connections = []  # the list with all the connection pairs as (source,target)
        if conn_spec['rule'] == 'fixed_outdegree':  #<----------------------
            for u in from_list:
                if conn_spec['allow_autapses']:
                    targets = random.sample(to_list, conn_spec['outdegree'])
                else:
                    to_copy = to_list.copy()
                    while u in to_copy:
                        to_copy.remove(u)
                    targets = random.sample(to_copy, conn_spec['outdegree'])
                connections += [(u,y) for y in targets]
        elif conn_spec['rule'] == 'fixed_indegree':   #<----------------------
            for u in to_list:
                if conn_spec['allow_autapses']:
                    sources = random.sample(from_list, conn_spec['indegree'])
                else:
                    from_copy = from_list.copy()
                    while u in from_copy:
                        from_copy.remove(u)
                    sources = random.sample(from_copy, conn_spec['indegree'])
                connections += [(x,u) for x in sources]
        elif conn_spec['rule'] == 'all_to_all':    #<----------------------
            targets = to_list
            sources = from_list
            if conn_spec['allow_autapses']:
                connections = [(x,y) for x in sources for y in targets]
            else:
                connections = [(x,y) for x in sources for y in targets if x != y]
        elif conn_spec['rule'] == 'one_to_one':   #<----------------------
            if len(to_list) != len(from_list):
                raise ValueError('one_to_one connectivity requires equal number of sources and targets')
            connections = list(zip(from_list, to_list))
            if conn_spec['allow_autapses'] == False:
                connections = [(x,y) for x,y in connections if x != y]
        else:
            raise ValueError('Attempting connect with an unknown rule')
            
        n_conns = len(connections)  # number of connections we'll make

        # Initialize the weights. We'll create a list that 'weights' that
        # has a weight for each entry in 'connections'
        if type(syn_spec['init_w']) is dict: 
            w_dict = syn_spec['init_w']
            if w_dict['distribution'] == 'uniform':  #<----------------------
                weights = np.random.uniform(w_dict['low'], w_dict['high'], n_conns)
            else:
                raise NotImplementedError('Initializing weights with an unknown distribution')
        elif type(syn_spec['init_w']) is float or type(syn_spec['init_w']) is int:
            weights = [float(syn_spec['init_w'])] * n_conns
        else:
            raise TypeError('The value given to the initial weight is of the wrong type')

        # Initialize the delays. We'll create a list 'delayz' that
        # has a delay value for each entry in 'connections'
        if type(conn_spec['delay']) is dict: 
            d_dict = conn_spec['delay']
            if d_dict['distribution'] == 'uniform':  #<----------------------
                # delays must be multiples of the minimum delay
                low_int = max(1, round(d_dict['low']/self.min_delay))
                high_int = max(1, round(d_dict['high']/self.min_delay)) + 1 #+1, so randint can choose it
                delayz = np.random.randint(low_int, high_int,  n_conns)
                delayz = self.min_delay * delayz
            else:
                raise NotImplementedError('Initializing delays with an unknown distribution')
        elif type(conn_spec['delay']) is float or type(conn_spec['delay']) is int:
            delayz = [float(conn_spec['delay'])] * n_conns
        else:
            raise TypeError('The value given to the delay is of the wrong type')


        # To specify connectivity, you need to update 3 lists: delays, act, and syns
        # Using 'connections', 'weights', and 'delayz' this is straightforward
        for idx, (source,target) in enumerate(connections):
            # specify that 'target' neuron has the 'source' input
            self.act[target].append(self.units[source].get_act)
            # add a new synapse object for our connection
            syn_params = syn_spec # a copy of syn_spec just for this connection
            syn_params['preID'] = source
            syn_params['postID'] = target
            syn_params['init_w'] = weights[idx]
            self.syns[target].append(syn_class(syn_params, self))
            # specify the delay of the connection
            self.delays[target].append( delayz[idx] )
            if self.units[source].delay <= delayz[idx]: # this is the longest delay for this source
                self.units[source].delay = delayz[idx]+self.min_delay
                # added self.min_delay because the ODE solver may ask for values a bit out of range
                self.units[source].init_buffers()

        # After connecting, run init_pre_syn_update for all the units connected 
        connected = [x for x,y in connections] + [y for x,y in connections]
        for u in set(connected):
            self.units[u].init_pre_syn_update()

    
    def run(self, total_time):
        # A basic runner.
        # It takes steps of 'min_delay' length, in which the units and synapses 
        # use their own methods to advance their state variables.
        Nsteps = int(total_time/self.min_delay)
        storage = [np.zeros(Nsteps) for i in range(self.n_units)]
        times = np.zeros(Nsteps) + self.sim_time
        
        for step in range(Nsteps):
            times[step] = self.sim_time
            
            # store current state
            for unit in range(self.n_units):
                storage[unit][step] = self.units[unit].get_act(self.sim_time)
                
            # update units
            for unit in range(self.n_units):
                self.units[unit].update(self.sim_time)

            self.sim_time += self.min_delay

        return times, storage        

