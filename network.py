''' 
network.py
The network class used in the sirasi simulator.
'''

from sirasi import unit_types, synapse_types, plant_models, syn_reqs  # names of models and requirements
from units import *
from synapses import *
from plants import *
import numpy as np
import random # to create random connections

class network():
    ''' 
    This class has the tools to build a network.
    First, you create an instance of network(); 
    second, you use the create() method to add units and plants;
    third, you use source.set_function() for source units, which provide inputs;
    fourth, you use the connect() method to connect the units, 
    finally you use the run() method to run a simulation.
    '''

    def __init__(self, params):
        '''
        The constructor receives a 'params' dictionary, which only requires two entries:
        A minimum transmission delay 'min_delay', and
        a minimum buffer size 'min_buff_size'.
        '''
        self.sim_time = 0.0  # current simulation time [ms]
        self.n_units = 0     # current number of units in the network
        self.units = []      # list with all the unit objects
        self.n_plants = 0    # current number of plants in the network
        self.plants = []     # list with all the plant objects
        # The next 3 lists implement the connectivity of the network
        self.delays = [] # delays[i][j] is the delay of the j-th connection to unit i in [ms]
        self.act = []    # act[i][j] is the function from which unit i obtains its j-th input
        self.syns = []   # syns[i][j] is the synapse object for the j-th connection to unit i
        self.min_delay = params['min_delay'] # minimum transmission delay [ms]
        self.min_buff_size = params['min_buff_size']  # number of values stored during a minimum delay period
        

    def create(self, n, params):
        '''
        This method is just a front to find out whether we're creating units or a plant.

        If we're creating units, it will call create_units().
        If we're creating a plant, it will call create_plant().

        Raises:
            TypeError.
        '''
        if hasattr(unit_types, params['type'].name):
            return self.create_units(n,params)
        elif hasattr(plant_models, params['type'].name):
            return self.create_plant(n, params)
        else:
            raise TypeError('Tried to create an object of an unknown type')


    def create_plant(self, n, params):
        '''
        Create a plant with model params['model']. The current implementation only 
        creates one plant per call, so n != 1 will raise an exception.
        The method returns the ID of the created plant.

        Raises:
            NotImplementedError, ValueError.
        '''
        # TODO: finish documentation
        assert self.sim_time == 0., 'A plant is being created when the simulation time is not zero'
        if n != 1:
            raise ValueError('Only one plant can be created on each call to create()')
        plantID = self.n_plants
        try:
            plant_class = params['type'].get_class()
        except NotImplementedError: # raising the same exception with a different message
            raise NotImplementedError('Attempting to create a plant with an unknown model type')

        self.plants.append(plant_class(plantID, params, self))
        '''
        if params['type'] == plant_models.pendulum:
            self.plants.append(pendulum(plantID, params, self))
        elif params['type'] == plant_models.conn_tester:
            self.plants.append(conn_tester(plantID, params, self))
        else:
            raise NotImplementedError('Attempting to create a plant with an unknown model type.')
        '''
        self.n_plants += 1
        return plantID
   

    def create_units(self, n, params):
        '''
        create 'n' units of type 'params['type']' and parameters from 'params'.
        The method returns a list with the ID's of the created units.
        If you want one of the parameters to have different values for each unit, you can have a list
        (or numpy array) of length 'n' in the corresponding 'params' entry
        '''
        # TODO: finish documentation
        assert (type(n) == int) and (n > 0), 'Number of units must be a positive integer'
        assert self.sim_time == 0., 'Units are being created when the simulation time is not zero'

        # Any entry in 'params' other than 'coordinates' and 'type' 
        # should either be a scalar, a list of length 'n', or a numpy array of length 'n'
        # 'coordinates' should be either a list (with 'n' tuples) or a (1|2|3)-tuple
        listed = [] # the entries in 'params' specified with a list
        for par in params:
            if par != 'type':
                if (type(params[par]) is list) or (type(params[par]) is np.ndarray):
                    if len(params[par]) == n:
                        listed.append(par)
                    else:
                        raise ValueError('Found parameter list of incorrect size during unit creation')
                elif (type(params[par]) != float) and (type(params[par]) != int):
                    if not (par == 'coordinates' and type(params[par]) is tuple):
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
        else:
            try: 
                unit_class = params['type'].get_class()
            except NotImplementedError:
                raise NotImplementedError('Attempting to create a unit with an unknown type')

            for ID in unit_list:
                for par in listed:
                    params_copy[par] = params[par][ID-self.n_units]
                self.units.append(unit_class(ID, params_copy, self))

        '''
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
        ''' 
        self.n_units += n
        # putting n new slots in the delays, act, and syns lists
        self.delays += [[] for i in range(n)]
        self.act += [[] for i in range(n)]
        self.syns += [[] for i in range(n)]
        # note:  [[]]*n causes all empty lists to be the same object 
        return unit_list
    
    def connect(self, from_list, to_list, conn_spec, syn_spec):
        '''
        connect the units in the 'from_list' to the units in the 'to_list' using the
        connection specifications in the 'conn_spec' dictionary, and the
        synapse specfications in the 'syn_spec' dictionary.
        The current version always allows multapses.

        from_list: A list with the IDs of the units sending the connections
        to_list: A list the IDs of the units receiving the connections
        conn_spec: A dictionary specifying a connection rule, and delays.
            REQUIRED PARAMETERS
            'rule' : a string specifying a rule on how to create the connections. 
                     Currently implemented: 
                     'fixed_outdegree' - an 'outdegree' integer entry must also be in conn_spec,
                     'fixed_indegree', - an 'indegree' integer entry must also be in conn_spec,
                     'one_to_one',
                     'all_to_all'.
            'allow_autapses' : True or False. Can units connect to themselves?
            'delay' : either a dictionary specifying a distribution, or a scalar delay value that
                      will be applied to all connections. Implemented dsitributions:
                      'uniform' - the delay dictionary must also include 'low' and 'high' values.
        syn_spec: A dictionary used to initialize the synapses in the connections.
            REQUIRED PARAMETERS
            'type' : a synapse type from the synapse_types enum.
            'init_w' : Initial weight values. Either a dictionary specifying a distribution, or a
                       scalar value to be applied for all created synapses. Distributions:
                      'uniform' - the delay dictionary must also include 'low' and 'high' values.
            OPTIONAL PARAMETERS
            'inp_ports' : input ports of the connections. Either a single integer, or a list.
                          If using a list, its length must match the number of connections being
                          created, which depends on the conection rule.
                
        Raises:
            ValueError, TypeError, NotImplementedError.
        '''
        
        # A quick test first
        if (np.amax(from_list + to_list) > self.n_units-1) or (np.amin(from_list + to_list) < 0):
            raise ValueError('Attempting to connect units with an ID out of range')

        # Retrieve the synapse class from its type object
        syn_class = syn_spec['type'].get_class()
       
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

        # Initialize the weights. We'll create a list called 'weights' that
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
            raise TypeError('The value given to the initial weights is of the wrong type')

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

        # Initialize the input ports, if specified in the syn_spec dictionary
        if 'inp_ports' in syn_spec:
            if type(syn_spec['inp_ports']) is int:
                portz = [syn_spec['inp_ports']]*n_conns
            elif type(syn_spec['inp_ports']) is list:
                if len(syn_spec['inp_ports']) == n_conns:
                    portz = syn_spec['inp_ports']
                else:
                    raise ValueError('Number of input ports specified does not match number of connections created')
            else:
                raise TypeError('Input ports were specified with the wrong data type')
        else:
            portz = [0]*n_conns

        # To specify connectivity, you need to update 3 lists: delays, act, and syns
        # Using 'connections', 'weights', 'delayz', and 'portz' this is straightforward
        for idx, (source,target) in enumerate(connections):
            # specify that 'target' neuron has the 'source' input
            self.act[target].append(self.units[source].get_act)
            # add a new synapse object for our connection
            syn_params = syn_spec # a copy of syn_spec just for this connection
            syn_params['preID'] = source
            syn_params['postID'] = target
            syn_params['init_w'] = weights[idx]
            syn_params['inp_port'] = portz[idx]
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


    def set_plant_inputs(self, unitIDs, plantID, conn_spec, syn_spec):
        """ Make the activity of some units provide inputs to a plant.

            Args:
                unitIDs: a list with the IDs of the input units
                plantID: ID of the plant that will receive the inputs
                conn_spec: a dictionary with the connection specifications
                    REQUIRED ENTRIES
                    'inp_ports' : A list. The i-th entry determines the input type of
                                  the i-th element in the unitIDs list.
                    'delays' : Delay value for the inputs. A scalar, or a list of length len(unitIDs)
                syn_spec: a dictionary with the synapse specifications.
                    REQUIRED ENTRIES
                    'type' : one of the synapse_types. Currently only 'static' allowed, because the
                             plant does not update the synapse dynamics in its update method.
                    'init_w': initial synaptic weight. A scalar, or a list of length len(unitIDs)

            Raises:
                ValueError, NotImplementedError

        """
        # First check that the IDs are inside the right range
        if (np.amax(unitIDs) >= self.n_units) or (np.amin(unitIDs) < 0):
            raise ValueError('Attempting to connect units with an ID out of range')
        if (plantID >= self.n_plants) or (plantID < 0):
            raise ValueError('Attempting to connect to a plant with an ID out of range')

        # Then connect them to the plant...
        # Have to create a list with the delays (if one is not given in the conn_spec)
        if type(conn_spec['delays']) is float:
            delys = [conn_spec['delays'] for _ in inp_funcs]
        elif (type(conn_spec['delays']) is list) or (type(conn_spec['delays']) is np.ndarray):
            delys = conn_spec['delays']
        else:
            raise ValueError('Invalid value for delays when connecting units to plant')
        # Have to create a list with all the synaptic weights
        if syn_spec['type'] is synapse_types.static: 
            synaps = []
            syn_spec['postID'] = plantID
            if type(syn_spec['init_w']) is float:
                weights = [syn_spec['init_w']]*len(unitIDs)
            elif (type(syn_spec['init_w']) is list) or (type(syn_spec['init_w']) is np.ndarray):
                weights = syn_spec['init_w']
            else:
                raise ValueError('Invalid value for initial weights when connecting units to plant')

            for pre,w in zip(unitIDs,weights):
                syn_spec['preID'] = pre
                syn_spec['init_w'] = w
                synaps.append( static_synapse(syn_spec, self) )
        else:
            raise NotImplementedError('Inputs to plants only use static synapses')

        inp_funcs = [self.units[uid].get_act for uid in unitIDs]
        ports = conn_spec['inp_ports']
        
        # Now just use this auxiliary function in the plant class
        self.plants[plantID].append_inputs(inp_funcs, ports, delys, synaps)

        # You may need to update the delay of some sending units
        for dely, unit in zip(delys, [self.units[id] for id in unitIDs]):
            if dely >= unit.delay: # This is the longest delay for the sending unit
                unit.delay = dely + self.min_delay
                unit.init_buffers()

   
    def set_plant_outputs(self, plantID, unitIDs, conn_spec, syn_spec):
        """ Connect the outputs of a plant to the units in a list.

        Args:
            plantID: ID of the plant sending the outpus.
            unitIDs: a list with the IDs of the units receiving inputs from the plant.
            conn_spec: a dictionary with the connection specifications.
                REQUIRED ENTRIES
                'port_map': a list used to specify which output of the plant goes to which input
                            port in each of the units. There are two options for this, one uses the
                            same output-to-port map for all units, and one specifies it separately
                            for each individual unit. More precisely, the two options are:
                            1) port_map is a list of 2-tuples (a,b), indicating that output 'a' of
                               the plant (the a-th element in the state vector) connects to port 'b'.
                            2) port_map[i] is a list of 2-tuples (a,b), indicating that output 'a' of the 
                               plant is connected to port 'b' for the i-th neuron in the neuronIDs list.
                            For example if unitIDs has two elements:
                                [(0,0),(1,1)] -> output 0 to port 0 and output 1 to port 1 for the 2 units.
                                [ [(0,0),(1,1)], [(0,1)] ] -> Same as above for the first unit,
                                map 0 to 1 for the second unit. 
                'delays' : either a dictionary specifying a distribution, a scalar delay value that
                           will be applied to all connections, or a list of values. 
                           Implemented dsitributions:
                           'uniform' - the delay dictionary must also include 'low' and 'high' values.
            syn_spec: a dictionary with the synapse specifications.
                REQUIRED ENTRIES
                'type' : one of the synapse_types. 
                'init_w': initial synaptic weight. A scalar, or a list of length len(unitIDs)

        Raises:
            ValueError, TypeError.
        """
        # There is some code duplication with connect, when setting weights and delays, 
        # but it's not quite the same.

        # Some utility functions
        # this function gets a list, returns True if all elements are tuples
        T_if_tup = lambda x : (True if (len(x) == 1 and type(x[0]) is tuple) else 
                               (type(x[-1]) is tuple) and T_if_tup(x[:-1]) )
        # this function gets a list, returns True if all elements are lists
        T_if_lis = lambda x : (True if (len(x) == 1 and type(x[0]) is list) else 
                               (type(x[-1]) is list) and T_if_lis(x[:-1]) )
        # this function returns true if its argument is float or int
        foi = lambda x : True if (type(x) is float) or (type(x) is int) else False
        # this function gets a list, returns True if all elements are float or int
        T_if_scal = lambda x : ( True if (len(x) == 1 and foi(x[0])) else 
                                 foi(x[-1])  and T_if_scal(x[:-1]) )

        # First check that the IDs are inside the right range
        if (np.amax(unitIDs) >= self.n_units) or (np.amin(unitIDs) < 0):
            raise ValueError('Attempting to connect units with an ID out of range')
        if (plantID >= self.n_plants) or (plantID < 0):
            raise ValueError('Attempting to connect to a plant with an ID out of range')
       
        # Retrieve the synapse class from its type object
        syn_class = syn_spec['type'].get_class()

        # Now we create a list with all the connections. In this case, each connection is
        # described by a 3-tuple (a,b,c). a=plant's output port. b=ID of receiving unit.
        # c=input port of receiving unit.
        pm = conn_spec['port_map']
        connections = []
        if T_if_tup(pm): # one single list of tuples
            for uid in unitIDs: 
                for tup in pm:
                    connections.append((tup[0], uid, tup[1]))
        elif T_if_lis(pm): # a list of lists of tuples
            if len(pm) == len(unitIDs):
                for uid, lis in zip(unitIDs, pm):
                    if T_if_tup(lis):
                        for tup in lis:
                            connections.append((tup[0], uid, tup[1]))
                    else:
                        raise ValueError('Incorrect port map format for unit ' + str(uid))
            else:
                raise ValueError('Wrong number of entries in port map list')
        else:
            raise TypeError('port map specification should be a list of tuples, or a list of lists of tuples')
            
        n_conns = len(connections)

        # Initialize the weights. We'll create a list called 'weights' that
        # has a weight for each entry in 'connections'
        if type(syn_spec['init_w']) is float or type(syn_spec['init_w']) is int:
            weights = [float(syn_spec['init_w'])] * n_conns
        elif type(syn_spec['init_w']) is list and T_if_scal(syn_spec['init_w']):
            if len(syn_spec['init_w']) == n_conns:
                weights = syn_spec['init_w']
            else:
                raise ValueError('Number of initial weights does not match number of connections being created')
        else:
            raise TypeError('The value given to the initial weights is of the wrong type')

        # Initialize the delays. We'll create a list 'delayz' that
        # has a delay value for each entry in 'connections'
        if type(conn_spec['delays']) is dict: 
            d_dict = conn_spec['delay']
            if d_dict['distribution'] == 'uniform':  #<----------------------
                # delays must be multiples of the minimum delay
                low_int = max(1, round(d_dict['low']/self.min_delay))
                high_int = max(1, round(d_dict['high']/self.min_delay)) + 1 #+1, so randint can choose it
                delayz = np.random.randint(low_int, high_int,  n_conns)
                delayz = self.min_delay * delayz
            else:
                raise NotImplementedError('Initializing delays with an unknown distribution')
        elif type(conn_spec['delays']) is float or type(conn_spec['delays']) is int:
            delayz = [float(conn_spec['delay'])] * n_conns
        elif type(conn_spec['delays']) is list and T_if_scal(conn_spec['delays']):
            if len(conn_spec['delays']) == n_conns:
                delayz = conn_spec['delays']
            else:
                raise ValueError('Number of delays does not match the number of connections being created')
        else:
            raise TypeError('The value given to the delay is of the wrong type')

        # To specify connectivity, you need to update 3 lists: delays, act, and syns
        # Using 'connections', 'weights', and 'delayz', this is straightforward
        for idx, (output, target, port) in enumerate(connections):
            # specify that 'target' neuron has the 'output' input
            if self.units[target].multi_port: # if the unit has support for multiple input ports
                self.act[target].append(self.plants[plantID].get_state_var)
            else:
                self.act[target].append(self.plants[plantID].get_state_var_fun(output))
            # add a new synapse object for our connection
            syn_params = syn_spec # a copy of syn_spec just for this connection
            syn_params['preID'] = plantID
            syn_params['postID'] = target
            syn_params['init_w'] = weights[idx]
            syn_params['inp_port'] = port
            syn_params['plant_out'] = output
            self.syns[target].append(syn_class(syn_params, self))
            # specify the delay of the connection
            self.delays[target].append( delayz[idx] )
            if self.plants[plantID].delay <= delayz[idx]: # this is the longest delay for this source
                # added self.min_delay because the ODE solver may ask for values a bit out of range
                self.plants[plantID].delay = delayz[idx]+self.min_delay
                self.plants[plantID].init_buffers()

        # After connecting, run init_pre_syn_update for all the units connected 
        connected = [y for x,y,z in connections] 
        for u in set(connected):
            self.units[u].init_pre_syn_update()



    def run(self, total_time):
        '''
        Simulate the network for the given time.

        It takes steps of 'min_delay' length, in which the units, synapses 
        and plants use their own methods to advance their state variables.
        The method returns a 3-tuple with numpy arrays containing the simulation
        times when the update functions were called, and the unit activities and 
        plant states corresponding to those times.
        After run(T) is finished, calling run(T) again continues the simulation
        starting at the last state of the previous simulation.
        '''
        Nsteps = int(total_time/self.min_delay)
        unit_stor = [np.zeros(Nsteps) for i in range(self.n_units)]
        plant_stor = [np.zeros((Nsteps,p.dim)) for p in self.plants]
        times = np.zeros(Nsteps) + self.sim_time
        
        for step in range(Nsteps):
            times[step] = self.sim_time
            
            # store current unit activities
            for uid, unit in enumerate(self.units):
                unit_stor[uid][step] = unit.get_act(self.sim_time)
           
            # store current plant state variables 
            for pid, plant in enumerate(self.plants):
                plant_stor[pid][step,:] = plant.get_state(self.sim_time)
                
            # update units
            for unit in self.units:
                unit.update(self.sim_time)

            # update plants
            for plant in self.plants:
                plant.update(self.sim_time)

            self.sim_time += self.min_delay

        return times, unit_stor, plant_stor

