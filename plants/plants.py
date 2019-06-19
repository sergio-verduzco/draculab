"""
plants.py
This file contains all the physical plant models used in the draculab simulator.
A plant is very similar to a unit, but it has a vector output.
"""

import numpy as np
from scipy.integrate import odeint
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d 
from draculab import plant_models, synapse_types
from numpy import sin, cos # for the double pendulum equations

class plant():
    """ Parent class of all non-unit models that interact with the network.

    Derived classes can implement any system that can be modeled with an ODE.

    Objects of the derived classes are basically the same as draculab's units: 
    they receive inputs and they send outputs to and from draculab's units. 
    Moreover, their inputs and outputs are mediated by the same synapse types 
    used by units. But whereas a unit's output can only be a firing rate,
    models have multidimensional outputs that can correspond to the the state 
    variables of a physical model. 
    
    By putting the appropriate dynamics in the derivatives() function, a 
    physical plant controlled by the network of units can interact with the 
    network using draculab's synapses and delayed connections.

    The added complexity of connecting the plant's multidimensional inputs 
    and outputs is handled by network.set_plant_inputs() and 
    network.set_plant_outputs().
    """

    def __init__(self, ID, params, network):
        """ The class constructor. 

        Args:
            ID: An integer identifying the plant. Set by network.create_plant
            params: parameter dictionary
            REQUIRED PARAMETERS
                'dimension' : dimensionality of the state vector. 
                'type' : an enum identifying the type of plant being instantiated.
                'inp_dim' : input dimensionality; number of qualitatively different input types.
            OPTIONAL PARAMETERS
                'delay' : maximum delay in the outputs sent by the plant. Set by
                          network.set_plant_outputs.

        """
        self.ID = ID # An integer identifying the plant
        self.net = network # the network where the plant lives
        self.inp_dim = params['inp_dim'] # input dimensionality; 
                                       # number of qualitatively different input types.
        self.inputs =  [[] for _ in range(self.inp_dim)]
        # self.inputs is a list of lists, with the get_act functions of the units that 
        # provide inputs to the plant. inputs[i][j] = j-th input of the i-th type.
        self.inp_dels = [[] for _ in range(self.inp_dim)]
        # for each entry in self.inputs, self.inp_dels gives the corresponding delay
        self.inp_syns = [[] for _ in range(self.inp_dim)]
        # for each entry in self.inputs, self.inp_syns has its synapse
        self.type = params['type'] # an enum identifying the type of plant being instantiated
        self.dim = params['dimension'] # dimensionality of the state vector
        # The delay of a plant is the maximum delay among the projections it sends. 
        # Its final value is set by network.set_plant_outputs(), after the plant is created.
        if 'delay' in params: 
            self.delay = params['delay']
            # delay must be a multiple of net.min_delay. Next line checks that.
            assert (self.delay+1e-6)%self.net.min_delay < 2e-6, ['unit' + str(self.ID) + 
                                               ': delay is not a multiple of min_delay']       
        else:  # giving a temporary value
            self.delay = 2. * self.net.min_delay 
        self.rtol = self.net.rtol # local copies of ODE solver tolerances
        self.atol = self.net.atol

        self.init_buffers() # This will create the buffers that store states and times


    def init_buffers(self):
        """ This method nitializes the buffer variables with the current parameters.  

        It is useful because new connections may increase self.delay, and thus
        the size of the buffers.
        """
    
        assert self.net.sim_time == 0., 'Plant buffers were reset when ' + \
                                        'the simulation time is not zero'
        # variables with '*' become redefined for flat networks (see network.flatten)
        min_del = self.net.min_delay  # just to have shorter lines below
        min_buff = self.net.min_buff_size
        self.steps = int(round(self.delay/min_del)) # delay, in units of the minimum delay
        self.offset = (self.steps-1)*min_buff # * an index used in the update
                                              # function of derived classes
        self.buff_width = int(round(self.steps*min_buff)) # * number of state values to store
        # keeping with scipy.integrate.odeint, each row in the buffer will
        # correspond to a state
        if hasattr(self, 'init_state'): # if we have initial values to put in the buffer
            self.buffer = np.array([self.init_state]*self.buff_width) # * initializing buffer
        else:
            self.buffer = np.ndarray(shape=(self.buff_width, self.dim), dtype=float) # *
        self.times = np.linspace(-self.delay, 0., self.buff_width) # * times for 
                                                                   # each buffer row
        self.times_grid = np.linspace(0, min_del, min_buff+1) # used to create values for 'times'


    def get_state(self, time):
        """ Returns an array with the state vector. """
        # TODO: This method uses the very inefficient process of creating a new
        # interpolator for each call. 
        if self.net.flat:
            ax = 1
        else:
            ax = 0
        return interp1d(self.times, self.buffer, kind='linear', axis=ax, bounds_error=False, 
                        copy=False, fill_value="extrapolate", assume_sorted=True)(time)


    def get_state_var(self, t, idx):
        """ Returns the value of the state variable with index 'idx' at time 't'. """
        # Sometimes the ode solver asks about values slightly out of bounds, 
        # so I set this to extrapolate
        if self.net.flat:
            return interp1d(self.times, self.buffer[idx,:], kind='linear', bounds_error=False, 
                            copy=False, fill_value="extrapolate", assume_sorted=True)(t)
        else:
            return interp1d(self.times, self.buffer[:,idx], kind='linear', bounds_error=False,
                            copy=False, fill_value="extrapolate", assume_sorted=True)(t)

    def get_state_var_fun(self, idx):
        """ 
        Returns a function that yields the state variable with index 'idx' at a given time. 
        
        This is used so units can ignore any input port settings while 
        receiving inputs from a plant.
        """
        # The creation of this function is done when the connections from the plant
        # are made with network.set_plant_outputs, and if the network is flattened,
        # network.act will still have the non-flat version of this function. 
        # Thus, if network.act is to remain a valid way to obtain plant inputs even
        # when the network is flat, these functions need to be specified again.
        if self.net.flat:
            return interp1d(self.times, self.buffer[idx,:], kind='linear',
                            bounds_error=False, copy=False, 
                            fill_value="extrapolate", assume_sorted=True)
        else:
            # for this case it seems we need to wrap the interpolator in a lambda
            return lambda t: interp1d(self.times, self.buffer[:,idx], kind='linear',
                                      bounds_error=False, copy=False, 
                                      fill_value="extrapolate", assume_sorted=True)(t)

    def get_input_sum(self, time, port):
        """ Returns the sum of all inputs at a given port, and at a given time.

            For each input arriving at 'port', you'll get its value at the 
            time ('time' - delay), multiply that value by the corresponding
            synaptic weight, and then sum all the scaled values. This sum is
            the returned value, which constitutes the total input provided by 
            all inputs in the given port.
        """
        return sum( [ fun(time - dely)*syn.w for fun,dely,syn in 
                      zip(self.inputs[port], self.inp_dels[port], self.inp_syns[port]) ] )
        
    def update(self, time):
        ''' This function advances the state for net.min_delay time units. '''
        assert (self.times[-1]-time) < 2e-6, 'plant ' + str(self.ID) + \
                ': update time is desynchronized'

        new_times = self.times[-1] + self.times_grid
        self.times = np.roll(self.times, -self.net.min_buff_size)
        self.times[self.offset:] = new_times[1:] 
        
        # odeint also returns the initial condition, so to produce min_buff_size new
        # states we need to provide min_buff_size+1 desired times, starting with the
        # one for the initial condition
        new_buff = odeint(self.derivatives, self.buffer[-1,:], new_times, 
                          rtol=self.rtol, atol=self.atol)
        self.buffer = np.roll(self.buffer, -self.net.min_buff_size, axis=0)
        self.buffer[self.offset:,:] = new_buff[1:,:] 

    def flat_update(self, time):
        """ advances the state for net.min_delay time units when the network is flat. """
        # The flat version of a plants has a buffer that is a view of a slice of 
        # network.acts. A slice of acts with several rows and not all of the columns
        # cannot be contiguous, and therefore you can't create a view of such a slice.
        # Therefore the buffer is a slice of acts with the full number of columns.
        # Moreover, each row in the buffer corresponds to a different state variable,
        # whereas it corresponds to a different time for a regular network.
        # The solve_ivp integrator works with this alignment without the need of 
        # transpositions, so it is the current choice.
        #
        # Unlike units, the current flat implementation of plants still uses its
        # regular get_input_sum function, relying on the get_act functions of its
        # input units. This is not fast, but at least it means that dt_fun and 
        # derivatives only differ in the order of their arguments.
        assert (self.times[self.offset-1]-time) < 2e-6, 'plant ' + str(self.ID) + \
                ': update time is desynchronized'
        # self.times is a view of network.ts
        nts = self.times[self.offset-1:] # times relevant for the update
        solution = solve_ivp(self.dt_fun, (nts[0], nts[-1]), self.buffer[:,-1], 
                             t_eval=nts, rtol=self.rtol, atol=self.atol)
        np.put(self.buffer[:,self.offset:], range(self.net.min_buff_size*self.dim), 
               solution.y[:,1:])

    def dt_fun(self, t, y):
        """ The derivatives function with the arguments switched. 

            The method flat_update above calls this instead of derivatives.
        """
        return self.derivatives(y, t)

    def append_inputs(self, inp_funcs, ports, delays, synaps):
        """ Append inputs with given functions, ports, delays, and synapses.

        An input port is just a list in the 'inputs' list. 
        The 'inputs' list contains 'inp_dim' lists, each one with all the
        functions providing that type of input.
        
        append_inputs is an auxiliary method for network.set_plant_inputs.

        Args:
            inp_funcs: a list with functions that will provide inputs to the plant.
            ports: an integer, or a list with integers, identifying the type 
                   of input that the corresponding entry in inp_funcs will provide. 
            delays: a list with the delays for the inputs in inp_funcs.
            synaps: a list of synapse objects that will scale the inputs in inp_funcs.

        Raises:
            ValueError, NotImplementedError.
        """
        # Handle the case when ports is a single integer
        if type(ports) in [int, np.int_]:
            ports = [ports] * len(inp_funcs)
        # Test the port specification
        test1 = len(inp_funcs) == len(ports)
        test2 = (np.amax(ports) < self.inp_dim) and (np.amin(ports) >= 0)
        type_list = [type(n) in [int, np.int_] for n in ports]
        test3 = sum(type_list) == len(inp_funcs)
        if not(test1 and test2 and test3):
            raise ValueError('Invalid input port specification when adding inputs to plant')

        # Then append the inputs
        for funz, portz in zip(inp_funcs, ports):  # input functions
            self.inputs[portz].append(funz)

        md = self.net.min_delay
        for delz, portz in zip(delays, ports):  # input delays
            if delz >= md: # ensuring delay not smaller than minimum delay
                if (delz+1e-8) % md < 1e-6: # delay a multiple of minimum delay
                    self.inp_dels[portz].append(delz)
                else:
                    raise ValueError('Delay of connection to plant is not ' +
                                     'multiple of min_delay')
            else:
                raise ValueError('Delay of connection to plant smaller than min_delay')

        for synz, portz in zip(synaps, ports):   # input synapses
            if synz.type is synapse_types.static:
                self.inp_syns[portz].append(synz)
            else:
                raise NotImplementedError('Inputs to plants only use static synapses')


class pendulum(plant):
    """ 
    Model of a rigid, homogeneous rod with a 1-dimensional rotational joint at one end.

    The simplest model of an arm is a rigid rod with one end attached to a rotational
    joint with 1 degree of freedom. Like a rigid pendulum, but the gravity vector is
    optional. 
    There is no extra mass at the end of the rod; the center of mass is at length/2 .
    
    On the XY plane the joint is at the origin, the positive X direction
    aligns with zero degrees, and gravity points in the negative Y direction.
    Counterclockwise rotation and torques are positive. Angles are in radians, time is
    in seconds.

    The equation of motion used is: I a = (mgL/2)cos(theta) - mu v + T
    where I=inertia moment about axis of rotation, a=angular acceleration, g=gravity constant,
    L=length of rod, theta=pendulum angle, mu=viscous friction coefficeint, m=mass of rod, 
    v=angular velocity, T=external torque.

    Inputs to the model at port 0 are torques applied at the joint. Other ports are ignored.

    The get_state(time) function returns the two state variables of the model in a numpy 
    array. Angle has index 0, and angular velocity has index 1. The 'time' argument
    should be in the interval [sim_time - del, sim_time], where sim_time is the current
    simulation time (time of last simulation step), and del is the 'delay' value
    of the plant. This method can be configured to provide angles in the 
    [-pi, pi) interval by using the 'bound_angle' parameter.

    Alternatively, the state variables can be retrieved with the get_angle(t) and
    get_ang_vel(t) functions.
    """

    def __init__(self, ID, params, network):
        """ The class constructor, called by network.create_plant .

        Args:
            ID: An integer serving as a unique identifier in the network.
            params: A dictionary with parameters to initialize the model.
                REQUIRED PARAMETERS
                'type' : A model from the plant_models enum.
                'length' : length of the rod [m]
                'mass' : mass of the rod [kg]
                'init_angle' : initial angle of the rod. [rad]
                'init_ang_vel' : initial angular velocity of the rod. [rad/s]
                OPTIONAL PARAMETERS
                'g' : gravitational acceleration constant. [m/s^2] (Default: 9.8)
                'inp_gain' : A gain value that multiplies the inputs. (Default: 1)
                'mu' : A viscous friction coefficient. (Default: 0)
                'bound_angle' : If True, the angle communicated through the output
                                ports is in the interval [-pi, pi). False by default.
            network: the network where the plant instance lives.

        Raises:
            AssertionError.

        """
        # This is the stuff that goes into all model constructors. Adjust accordingly.
        #-------------------------------------------------------------------------------
        #assert params['type'] is plant_models.pendulum, ['Plant ' + str(self.ID) + 
        #                                            ' instantiated with the wrong type']
        params['dimension'] = 2 # notifying dimensionality of model to parent constructor
        params['inp_dim'] = 1 # notifying there is only one type of inputs
        plant.__init__(self, ID, params, network) # calling parent constructor
        # Using model-specific initial values, initialize the state vector.
        self.init_state = np.array([params['init_angle'], params['init_ang_vel']])
        self.buffer = np.array([self.init_state]*self.buff_width) # initializing buffer
        #-------------------------------------------------------------------------------
        # Initialize the parameters specific to this model
        self.length = params['length']  # length of the rod [m]
        self.mass = params['mass']   # mass of the rod [kg]
        # To get the moment of inertia assume a homogeneous rod, so I = m(l^2)/3
        self.I = self.mass * self.length * self.length / 3.
        # The gravitational force per kilogram can be set as a parameter
        if 'g' in params: self.g = params['g']
        else: self.g = 9.8  # [m/s^2]
        # This constant is used to calculate torque from gravity
        self.c = 0.5 * self.mass * self.g * self.length 
        # We may also have an input gain
        if 'inp_gain' in params: self.inp_gain = params['inp_gain']
        else: self.inp_gain = 1.
        # And finally, we have a viscous friction coefficient
        if 'mu' in params: self.mu = params['mu']
        else: self.mu = 0.
        if 'bound_angle' in params and params['bound_angle'] is True:
            self.get_state_var_fun = self.get_state_var_fun_bound
            self.get_state = self.get_state_bound

    def derivatives(self, y, t):
        """ Returns the derivatives of the state variables at a given point in time. 

	Args:
            y[0] = angle [radians]
            y[1] = angular velocity [radians / s]
            t = time at which the derivative is evaluated [s]
        Returns:
            2-element 1D Numpy array with angular velocity and acceleration.
        """
        torque = self.inp_gain * self.get_input_sum(t,0)
        # torque may also come from gravity and friction
        torque -= self.c * np.cos(y[0]) +  self.mu * y[1]
        # angular acceleration = torque / (inertia moment)
        ang_accel = torque / self.I
        return np.array([y[1], ang_accel])

    def get_angle(self,time):
        """ Returns the angle in radians, modulo 2*pi. """
        return self.get_state_var(time,0) % (2.*np.pi)
              
    def get_ang_vel(self,time):
        """ Returns the angular velocity in rads per second. """
        return self.get_state_var(time,1) 
        
    def get_state_var_fun_bound(self, idx):
        """ 
        Overrides plant.get_state_var in order to bound the angle to [-pi,pi).
        
        This method is used optionally depending on the value of 'bound_angle'.
        It slows things down, so it's off by default.
        """
        meth = plant.get_state_var_fun(self, idx)
        if idx == 0:
            return lambda t : (meth(t) + np.pi)%(2.*np.pi) - np.pi
        else:
            return meth

    def get_state_bound(self, time):
        """ Overrides plant.get_state to bound the angle to [-pi, pi). """
        if self.net.flat:
            ax = 1
        else:
            ax = 0
        state = interp1d(self.times, self.buffer, kind='linear', axis=ax,
                         bounds_error=False, copy=False, fill_value="extrapolate", 
                         assume_sorted=True)(time)
        state[0] = (state[0] + np.pi)%(2.*np.pi) - np.pi
        return state


class conn_tester(plant):
    """
    This plant is used to test the network.set_plant_inputs and plant.append_inputs functions.

    Pay no attention to it.
    """
    def __init__(self, ID, params, network):
        """ conn_tester constructor """
        # This is the stuff that goes into all model constructors. 
        #-------------------------------------------------------------------------------
        assert params['type'] is plant_models.conn_tester, ['Plant ' + str(self.ID) + 
                                                    ' instantiated with the wrong type']
        params['dimension'] = 3 # notifying dimensionality of model to parent constructor
        params['inp_dim'] = 3 # notifying number of input ports
        super(conn_tester, self).__init__(ID, params, network) # calling parent constructor

        # Using model-specific initial values, initialize the state vector.
        self.init_state = np.array(params['init_state'])
        self.buffer = np.array([self.init_state]*self.buff_width) # initializing buffer
        #-------------------------------------------------------------------------------

    def derivatives(self, y, t):
        ''' The first two equations, when their input sum is 1, have sin and cos solutions. 
    
        Different ratios of the input amplitudes should bring differernt ratios of the solution 
        amplitudes, and the amplitude of the inputs should change the frequency of the solutions.
        The third equation has an exponential solution, with time constant equal to the input.
        '''
        return np.array([-y[1]*self.get_input_sum(t,0),
                          y[0]*self.get_input_sum(t,1),
                         -y[2]*self.get_input_sum(t,2)])


class point_mass_2D(plant):
    """ A point mass moving in two dimensions, with force exerted by the inputs. 
    
        Inputs may arrive at ports 0 or 1.
        Inputs at port 0 push the mass in the direction of 'vec0' with a force
        equal to the input activity times the synaptic weight times a 'g0' gain
        parameter. 
        Inputs at port 1 push the mass in the direction of 'vec1' with a force
        equal to the input activity times the synaptic weight times a 'g1' gain
        parameter.
        
        Mass is in units of kilograms, distance in meters, force in Newtons,
        time in seconds. Position is specified in Cartesian coordinates.
    """
    def __init__(self, ID, params, network):
        """ The class constructor, called by network.create_plant . 
        
        Args:
            ID: an integer serving as a unique identifier in the network
            network: the network containing the plant
            params: a dictionary with parameters to initialize the model
            REQUIRED PARAMETERS
                type: this should have the plant_models.point_mass_2D value.
                mass: mass in kilograms.
                init_pos: a 2-element array-like with the initial (x,y) position.
                init_vel: a 2-element array-like with the initial (x,y) velocity.
                vec0: 2-element array-like with direction of force for port 0 inputs.
                vec1: 2-element array-like with direction of force for port 1 inputs.
                g0: force in Newtons exerted by an input sum of magnitude 1 at port 0.
                g1: force in Newtons exerted by an input sum of magnitude 1 at port 1.
            Raises:
                AssertionError
        """
        # This is the stuff that goes into all model constructors. Adjust accordingly. 
        #-------------------------------------------------------------------------------
        params['dimension'] = 4  # Dimension passed to the parent constructor
        params['inp_dim'] = 2  # Input dimension passed to the parent constructor
        plant.__init__(self, ID, params, network) # parent constructor
        # Using model-specific initial values, initialize the state vector.
        self.init_state = np.array([params['init_pos'][0], params['init_pos'][1],
                                    params['init_vel'][0], params['init_vel'][1]])
        self.buffer = np.array([self.init_state]*self.buff_width)
        #-------------------------------------------------------------------------------
        # Initialize the parameters specific to this model
        self.mass = params['mass']
        assert self.mass > 0., 'Mass should be a positive scalar value'
        self.vec0 = np.array([params['vec0'][0], params['vec0'][1]])
        self.vec1 = np.array([params['vec1'][0], params['vec1'][1]])
        self.g0 = params['g0']
        self.g1 = params['g1']
    
    def derivatives(self, y, t):
        """ Returns the derivtives of the state variables at time 't'. 
        
        Args:
            y[0]: x-coordinate [meters]
            y[1]: y-coordinate [meters]
            y[2]: x-velocity [meters / second]
            y[3]: y-velocity [meters / second]
            t: time when the derivative is evaluated [seconds]
        Returns:
            4-element Numpy array with [x_vel, y_vel, x_accel, y_accel]
        """
        v0_sum = self.get_input_sum(t, 0)
        v1_sum = self.get_input_sum(t, 1)
        accel = (self.g0*v0_sum*self.vec0 + self.g1*v1_sum*self.vec1) / self.mass
        return np.array([y[2], y[3], accel[0], accel[1]])


class simple_double_pendulum(plant):
    """ 
    Model of a simple double pendulum driven by torques at its two joints.
    
    The simple double pendulum consists of two point masses attached by
    rods with no mass. Derivation of the equations of motion for this model is
    in the ../tests/double_pendulum_validation.ipynb file.

    On the XY plane the shoulder joint is at the origin, the positive X direction
    aligns with zero degrees, and gravity points in the negative Y direction.
    Counterclockwise rotation and torques are positive. Angles are in radians, time is
    in seconds.

    The configuration of the pendulum is described by two angles q1 and q2.
    Let L1 be the line segment going from the shoulder to the elbow, and L2 the line
    segment going from the elbow to the hand. 
    q1 is the angle formed by L1 with the positive x axis. q2 is the angle
    formed by the extension of L1 in the distal direction with the segment L2. 

    Inputs to the model at port 0 are torques applied at the shoulder joint. 
    Inputs at port 1 are torques applied at the elbow joint. Other ports are ignored.
    """
    def __init__(self, ID, params, network):
        """ The class constructor, called by network.create_plant.

        Args:
            ID: An integer serving as a unique identifier in the network.
            params: A dictionary with parameters to initialize the model.
                REQUIRED PARAMETERS
                'type' : A model from the plant_models enum.
                'l1' : length of the rod1 [m]
                'l2' : length of the rod2 [m]
                'mass1' : mass of the point mass at the elbow [kg]
                'mass2' : mass of the point mass at the hand [kg]
                'init_q1 : initial angle of the first joint (shoulder) [rad]
                'init_q2' : initial angle of the second joint (elbow) [rad]
                'init_q1p' : initial angular velocity of the first joint (shoulder) [rad/s]
                'init_q2p' : initial angular velocity of the second joint (elbow) [rad/s]
                OPTIONAL PARAMETERS
                'g' : gravitational acceleration constant. [m/s^2] (Default: 9.81)
                'inp_gain0' : A gain value that multiplies the port 0 inputs. (Default: 1)
                'inp_gain1' : A gain value that multiplies the port 1 inputs. (Default: 1)
                'mu1' : Viscous friction coefficient at shoulder joint. (Default: 0)
                'mu2' : Viscous friction coefficient at elbow joint. (Default: 0)
            network: the network where the plant instance lives.

        Raises:
            AssertionError.

        """
        # This is the stuff that goes into all model constructors. Adjust accordingly.
        #-------------------------------------------------------------------------------
        assert params['type'] is plant_models.simple_double_pendulum, ['Plant ' + str(self.ID) + 
                                                     ' instantiated with the wrong type']
        params['dimension'] = 4 # notifying dimensionality of model to parent constructor
        params['inp_dim'] = 2 # notifying there are two type of inputs
        plant.__init__(self, ID, params, network) # calling parent constructor
        # Using model-specific initial values, initialize the state vector.
        self.init_state = np.array([params['init_q1'], params['init_q1p'],
                                    params['init_q2'], params['init_q2p']])
        self.buffer = np.array([self.init_state]*self.buff_width) # initializing buffer
        #-------------------------------------------------------------------------------
        # Initialize the parameters specific to this model
        self.l1 = params['l1']  # length of the rod1 [m]
        self.l2 = params['l2']  # length of the rod2 [m]
        self.mass1 = params['mass1']   # mass of the rod1 [kg]
        self.mass2 = params['mass2']   # mass of the rod2 [kg]
        if 'g' in params: # gravitational force per kilogram
            self.g = params['g']
        else: 
            self.g = 9.8  # [m/s^2]
        if 'inp_gain0' in params:  # port 0 input gain
            self.inp_gain = params['inp_gain0']
        else:
            self.inp_gain0 = 1.
        if 'inp_gain1' in params:  # port 1 input gain
            self.inp_gain1 = params['inp_gain1']
        else:
            self.inp_gain1 = 1.
        if 'mu1' in params: # shoulder viscous friction coefficient
            self.mu1 = params['mu1'] 
        else:
            self.mu1 = 0.
        if 'mu2' in params: # elbow viscous friction coefficient
            self.mu2 = params['mu2']
        else:
            self.mu2 = 0.

    def derivatives(self, y, t):
        """ Returns the derivatives of the state variables at a given point in time. 

        These equations were copy-pasted from double_pendulum_validation.ipynb .

        Args:
            y : state vector (list-like) ...
                y[0] : angle of shoulder [radians]
                y[1] : angular velocity of shoulder [radians / s]
                y[2] : angle of elbow [radians]
                y[3] : angular velocity of elbow [radians / s]
            t : time at which the derivative is evaluated [s]
        Returns:
            dydt : vector of derivtives (numpy array) ...
                dydt[0] : angular velocity of shoulder [radians / s]
                dydt[1] : angular acceleration of shoulder [radians/s^2]
                dydt[2] : angular velocity of elbow [radians / s]
                dydt[3] : angular acceleration of elbow [radians/s^2]
        """
	# obtaining the input torques
        tau1 = self.inp_gain0 * self.get_input_sum(t,0)
        tau2 = self.inp_gain1 * self.get_input_sum(t,1)
	# setting shorter names for the variables
        q1 = y[0]
        q1p = y[1]
        q2 = y[2]
        q2p = y[3]
        L1 = self.l1
        L2 = self.l2
        m1 = self.mass1
        m2 = self.mass2
        g = self.g
        mu1 = self.mu1
        mu2 = self.mu2
        # equations
        dydt = np.zeros_like(y)
        dydt[0] = q1p
        dydt[1] = (L1**2.*L2*m2*q1p**2.*sin(2.*q2)/2. + L1*L2**2.*m2*q1p**2.*sin(q2) +
                   2.*L1*L2**2.*m2*q1p*q2p*sin(q2) + L1*L2**2.*m2*q2p**2.*sin(q2) -
                   L1*L2*g*m1*cos(q1) - L1*L2*g*m2*cos(q1)/2. +
                   L1*L2*g*m2*cos(q1 + 2.*q2)/2. + L1*mu2*q2p*cos(q2) -
                   L2*mu1*q1p + L2*mu2*q2p + L2*tau1) / (L1**2.*L2*(m1 + m2*sin(q2)**2.))
        dydt[2] = q2p
        dydt[3] = -(m2*(L1*cos(q2) + L2)*(2.*L1*L2**2.*m2*q1p*q2p*sin(q2) + 
                    L1*L2**2.*m2*q2p**2.*sin(q2) - L1*L2*g*m1*cos(q1) - 
                    L1*L2*g*m2*cos(q1) + L1*tau2*cos(q2) - L2**2.*g*m2*cos(q1 + q2) -
                    L2*mu1*q1p + L2*tau1 + L2*tau2) + (L1**2.*m1 + L1**2.*m2 + 
                    2.*L1*L2*m2*cos(q2) + L2**2.*m2)*(L1*L2*m2*q1p**2.*sin(q2) +
                    L2*g*m2*cos(q1 + q2) + mu2*q2p - tau2)) / (
                        L1**2.*L2**2.*m2*(m1 + m2*sin(q2)**2.))
        return dydt
        

class compound_double_pendulum(plant):
    """ 
    Model of a compound double pendulum driven by torques at its two joints.
    
    This compound or physical double pendulum consists of rods of homogeneous
    density along their axis.
    Derivation of the equations of motion for this model is in the 
    ../tests/double_pendulum_validation.ipynb file, on section 2.

    On the XY plane the shoulder joint is at the origin, the positive X direction
    aligns with zero degrees, and gravity points in the negative Y direction.
    Counterclockwise rotation and torques are positive. Angles are in radians, time is
    in seconds.

    The configuration of the pendulum is described by two angles q1 and q2.
    Let L1 be the line segment going from the shoulder to the elbow, and L2 the line
    segment going from the elbow to the hand. 
    q1 is the angle formed by L1 with the positive x axis. q2 is the angle
    formed by the extension of L1 in the distal direction with the segment L2. 

    Inputs to the model at port 0 are torques applied at the shoulder joint. 
    Inputs at port 1 are torques applied at the elbow joint. Other ports are ignored.
    """
    def __init__(self, ID, params, network):
        """ The class constructor, called by network.create_plant .

        Args:
            ID: An integer serving as a unique identifier in the network.
            params: A dictionary with parameters to initialize the model.
                REQUIRED PARAMETERS
                'type' : A model from the plant_models enum.
                'l1' : length of the rod1 [m]
                'l2' : length of the rod2 [m]
                'mass1' : mass of the rod1 [kg]
                'mass2' : mass of the rod2 [kg]
                'init_q1 : initial angle of the first joint (shoulder) [rad]
                'init_q2' : initial angle of the second joint (elbow) [rad]
                'init_q1p' : initial angular velocity of the first joint (shoulder) [rad/s]
                'init_q2p' : initial angular velocity of the second joint (elbow) [rad/s]
                OPTIONAL PARAMETERS
                'g' : gravitational acceleration constant. [m/s^2] (Default: 9.81)
                'inp_gain0' : A gain value that multiplies the port 0 inputs. (Default: 1)
                'inp_gain1' : A gain value that multiplies the port 1 inputs. (Default: 1)
                'mu1' : Viscous friction coefficient at shoulder joint. (Default: 0)
                'mu2' : Viscous friction coefficient at elbow joint. (Default: 0)
            network: the network where the plant instance lives.

        Raises:
            AssertionError.

        """
        # This is the stuff that goes into all model constructors. Adjust accordingly.
        #-------------------------------------------------------------------------------
        assert params['type'] is plant_models.compound_double_pendulum, ['Plant ' +
                                 str(self.ID) + ' instantiated with the wrong type']
        params['dimension'] = 4 # notifying dimensionality of model to parent constructor
        params['inp_dim'] = 2 # notifying there are two type of inputs
        plant.__init__(self, ID, params, network) # calling parent constructor
        # Using model-specific initial values, initialize the state vector.
        self.init_state = np.array([params['init_q1'], params['init_q1p'],
                                    params['init_q2'], params['init_q2p']])
        self.buffer = np.array([self.init_state]*self.buff_width) # initializing buffer
        #-------------------------------------------------------------------------------
        # Initialize the parameters specific to this model
        self.l1 = params['l1']  # length of the rod1 [m]
        self.l2 = params['l2']  # length of the rod2 [m]
        self.mass1 = params['mass1']   # mass of the rod1 [kg]
        self.mass2 = params['mass2']   # mass of the rod2 [kg]
        if 'g' in params: # gravitational force per kilogram
            self.g = params['g']
        else: 
            self.g = 9.81  # [m/s^2]
        if 'inp_gain0' in params:  # port 0 input gain
            self.inp_gain = params['inp_gain0']
        else:
            self.inp_gain0 = 1.
        if 'inp_gain1' in params:  # port 1 input gain
            self.inp_gain1 = params['inp_gain1']
        else:
            self.inp_gain1 = 1.
        if 'mu1' in params: # shoulder viscous friction coefficient
            self.mu1 = params['mu1'] 
        else:
            self.mu1 = 0.
        if 'mu2' in params: # elbow viscous friction coefficient
            self.mu2 = params['mu2']
        else:
            self.mu2 = 0.
        
    def derivatives(self, y, t):
        """ Returns the derivatives of the state variables at a given point in time. 

        These equations were copy-pasted from double_pendulum_validation.ipynb .

        Args:
            y : state vector (list-like) ...
                y[0] : angle of shoulder [radians]
                y[1] : angular velocity of shoulder [radians / s]
                y[2] : angle of elbow [radians]
                y[3] : angular velocity of elbow [radians / s]
            t : time at which the derivative is evaluated [s]
        Returns:
            dydt : vector of derivtives (numpy array) ...
                dydt[0] : angular velocity of shoulder [radians / s]
                dydt[1] : angular acceleration of shoulder [radians/s^2]
                dydt[2] : angular velocity of elbow [radians / s]
                dydt[3] : angular acceleration of elbow [radians/s^2]
        """
	# obtaining the input torques
        tau1 = self.inp_gain0 * self.get_input_sum(t,0)
        tau2 = self.inp_gain1 * self.get_input_sum(t,1)
	# setting shorter names for the variables
        q1 = y[0]
        q1p = y[1]
        q2 = y[2]
        q2p = y[3]
        L1 = self.l1
        L2 = self.l2
        m1 = self.mass1
        m2 = self.mass2
        g = self.g
        mu1 = self.mu1
        mu2 = self.mu2
        # equations
        dydt = np.zeros_like(y)
        dydt[0] = q1p
        dydt[1] = 3.0*(-2.0*L2*(-2.0*L1*L2*m2*q1p*q2p*sin(q2) - L1*L2*m2*q2p**2*sin(q2) +
                       L1*g*m1*cos(q1) + 2.0*L1*g*m2*cos(q1) + L2*g*m2*cos(q1 + q2) +
                       2.0*mu1*q1p - 2.0*tau1) + (3.0*L1*cos(q2) + 2.0*L2) * 
                       (L1*L2*m2*q1p**2*sin(q2) + L2*g*m2*cos(q1 + q2) +
                       2.0*mu2*q2p - 2.0*tau2)) / ( 
                       L1**2*L2*(4.0*m1 + 9.0*m2*sin(q2)**2 + 3.0*m2))
        dydt[2] = q2p
        dydt[3] = 3.0*(L2*m2*(3.0*L1*cos(q2) + 2.0*L2)*(-2.0*L1*L2*m2*q1p*q2p*sin(q2) -
                       L1*L2*m2*q2p**2*sin(q2) + L1*g*m1*cos(q1) + 2.0*L1*g*m2*cos(q1) +
                       L2*g*m2*cos(q1 + q2) + 2.0*mu1*q1p - 2.0*tau1) -
                       2.0*(L1**2*m1 + 3.0*L1**2*m2 + 3.0*L1*L2*m2*cos(q2) + L2**2*m2) *
                       (L1*L2*m2*q1p**2*sin(q2) + L2*g*m2*cos(q1 + q2) + 2.0*mu2*q2p -
                       2.0*tau2)) / (L1**2*L2**2*m2*(4.0*m1 + 9.0*m2*sin(q2)**2 + 3.0*m2))
        return dydt

class spring_muscle():
    """ A very simple muscle model with a linear spring. 
    
        This object is to be used by the planar_arm plant.

        The contraction force of the muscle is proportional to its input, plus
        the force provided by the spring. The spring force is proportional to
        its deviation from a rest length.

        The muscle provides 3 outputs: its length, its contraction velocity, and
        its tension. In order to update its state the muscle uses 5 inputs at
        each simulation step. The first two inputs provide the coordinates of
        the muscle's insertion points, one input provides the contraction-causing
        stimulation, and two inputs modulate the length and contraction velocity
        outputs. See the constructor's docstring for more details.
    """
    def __init__(self, params):
        """ The class constructor.

        Args:
            params: A parameter dictionary with the following entries:
            REQUIRED PARAMETERS
                s: spring constant [N/m]
                g1: contraction input gain [N].
                g2: length afferent modulation gain.
                g3: velocity afferent modulation gain.
                dt: length of simulation steps [s]
                p1: array-like with coordinates of proximal insertion point.
                p2: array-like with coordinates of distal insertion point.
            OPTIONAL PARAMETERS
                tau_fast : time constant for fast low-pass filter [s]
                           Defaults to 0.01 seconds.
                tau_mid : time constant for medium low-pass filter [s]
                          Defaults to 0.1 seconds.
                v_scale : a factor that scales the magnitude of the velocity.
                          Defaults to 5.
                l0: resting length of the muscle as a fraction of the distance
                    between the received p1 and p2 coordinates, which is the
                    default resting length.

        The spring force of the muscle is obtained as:
            F = s*(l - l0,0) + g1*i1
        where F=Force, l=length, and i1=contracting stimulation
        The afferent outputs come from length, velocity, and tension:
            affs[0] = g2*(1+i2)*l/l0, where l0 = resting length in meters.
            affs[1] = g3*(1+i3)*v
            affs[2] = s*max(l - l0,0) + g1*i1
        where v is the contraction velocity, and i2,i3 are inputs.
        These output are supposed to represent the Ia, II, and Ib afferents,
        respectively.
        The contraction velocity is obtained as:
            v = v_scale * (L_fast - L_mid)
        where L_fast=fast LPF length, L_mid=medium LPF length.
        """
        self.s = params['s']
        self.g1 = params['g1']
        self.g2 = params['g2']
        self.g3 = params['g3']
        self.dt = params['dt']
        if 'tau_fast' in params:
            self.tau_fast = params['tau_fast']
        else:
            self.tau_fast = 0.01
        if 'tau_mid' in params:
            self.tau_mid = params['tau_mid']
        else:
            self.tau_mid = 0.1
        if 'v_scale' in params:
            self.v_scale = params['v_scale']
        else:
            self.v_scale = 15.
        p1 = params['p1']
        p2 = params['p2']
        # defining an auxiliary function to obtain the muscle length
        if len(p1) == 2 and len(p2) == 2:
            self.norm = lambda p1,p2: ((p1[0]-p2[0])*(p1[0]-p2[0])+
                                       (p1[1]-p2[1])*(p1[1]-p2[1]))**(1/2)
        elif len(p1) == 3 and len(p2) == 3:
            self.norm = lambda p1,p2: ((p1[0]-p2[0])*(p1[0]-p2[0])+
                                       (p1[1]-p2[1])*(p1[1]-p2[1])+
                                       (p1[2]-p2[2])*(p1[2]-p2[2]))**(1/2)
        else:
            raise ValueError('Insertion points should both be 2 or 3-' +
                             'dimensional arrays')
        self.l = self.norm(p1,p2) # intializing the length
        if 'l0' in params: self.l0 = params['l0']*self.l # rest length
        else: self.l0 = self.l
        self.l_lpf_fast = self.l # initializing fast lpf'd length
        self.l_lpf_mid = self.l # initializing medium lpf'd length
        self.T = self.s*(self.l-self.l0) # initial tension
        self.v = 0. # initial velocity is zero
        self.fast_propagator = np.exp(-self.dt/self.tau_fast) # to update l_lpf_fast
        self.mid_propagator = np.exp(-self.dt/self.tau_mid) # to update l_lpf_mid
        # initialize vector with afferents
        self.affs = np.array([self.g2*self.l, self.g3*self.v, self.T])

    def upd_lpf_l(self):
        """ Update the low-pass filtered lengths. """
        # Using the approach from unit.upd_lpf_fast
        self.l_lpf_fast = self.l + (self.l_lpf_fast - self.l) * self.fast_propagator
        self.l_lpf_mid = self.l + (self.l_lpf_mid - self.l) * self.mid_propagator
    
    def update(self, p1, p2, i1, i2, i3):
        """ Update the length, tension, velocity, afferents, and LPF'd lengths. 
        
        Args:
            p1: array-like with coordinates of proximal insertion point.
            p2: array-like with coordinates of distal insertion point.
            i1: stimulation to contract the muscle.
            i2: stimulation to modulate length afferent.
            i3: stimulation to modulate velocity afferent.
            
        """
        # find the muscle's length
        self.l = self.norm(p1, p2)
        # update the low-pass filtered lengths
        self.l_lpf_fast = self.l + (self.l_lpf_fast-self.l) * self.fast_propagator
        self.l_lpf_mid = self.l + (self.l_lpf_mid-self.l) * self.mid_propagator
        # update the tension
        self.T = self.s * max(self.l-self.l0, 0.) + self.g1*i1
        # update the velocity
        self.v = self.v_scale * (self.l_lpf_fast - self.l_lpf_mid)
        # update afferents vector
        self.affs[0] = self.g2 * (1.+i2) * self.l / self.l0
        self.affs[1] = self.g3 * (1.+i3) * self.v
        self.affs[2] = self.T


class planar_arm(plant):
    """ 
    Model of a planar arm with six muscles.
    
    The planar arm consists of a compound double pendulum together with six
    muscle objects that produce torques on its two joints.

    The inputs to this model are the stimulations to each one of the muscles;
    each muscle can receive 3 types of stimuli, representing 3 different
    sources. The first type of stimulus represents inputs from alpha
    motoneurons, and causes muscle contraction. The other two types represent
    inputs from dynamic and static gamma interneurons, respectively
    representing inputs to the dynamic bag fibers and to the static bag fibers
    and nuclear chain fibers. The effect of the gamma interneuron stimulation
    depends on the muscle model.

    Geometry of the muscle model is specified through 14 2-dimensional
    coordinates. Two coordinates are for the elbow and hand, whereas the
    remaining 12 are for the insertion points of the 6 muscles. The script in
    planar_arm.ipynb permits to visualize the geometric configuration that
    results from particular values of the coordinates, and explains the
    reference position used to specify these coordinates.

    Inputs to the model organize in triplets, with 3 consecutive inputs being
    received by the same muscle:
        port 0: alpha stimulation to muscle 1
        port 1: gamma static stimulation to muscle 1
        port 2: gamma dynamic stimulation to muscle 1
        port 3,4,5: same, for muscle 2
        port 6,7,8: same, for muscle 3
        port 9,10,11: same, for muscle 4
        port 12,13,14: same, for muscle 5
        port 15,16,17: same, for muscle 6
    Outputs from the model consist of the 4-dimensional state of the double
    pendulum, and a 4-dimensional output coming from each one of the muscles.
        port 0: shoulder angle [radians]
        port 1: angular velocity of shoulder [radians / s]
        port 2: angle of elbow [radians]
        port 3: angular velocity of elbow [radians / s]
        port 4: length of muscle 1
        port 5: group Ia afferent output for muscle 1 (see muscle model)
        port 6: group II afferent output for muscle 1
        port 7: group Ib afferent output for muscle 1
        port 8-11: same as ports 4-7, but for muscle 2
        port 12-15: same, for muscle 3
        port 16-19: same, for muscle 4
        port 20-23: same, for muscle 5
        port 24-27: same, for muscle 6

    See planar_arm.ipynb for an example.
    """
    def __init__(self, ID, params, network):
        """ The class constructor, called by network.create.

        See planar_arm.ipynb for a reference on how to specify the arm geometry.
        All length units are in meters.

        Args:
            ID: An integer serving as a unique identifier in the network.
            params: A dictionary with parameters to initialize the model.
                REQUIRED PARAMETERS
                'type' : The enum 'plant_models.planar_arm'.
                'mass1' : mass of the rod1 [kg]
                'mass2' : mass of the rod2 [kg]
                'init_q1 : initial angle of the first joint (shoulder) [rad]
                'init_q2' : initial angle of the second joint (elbow) [rad]
                'init_q1p' : initial angular velocity of the first joint (shoulder) [rad/s]
                'init_q2p' : initial angular velocity of the second joint (elbow) [rad/s]
                OPTIONAL PARAMETERS
                'g' : gravitational acceleration constant. [m/s^2] (Default: 9.81)
                'mu1' : Viscous friction coefficient at shoulder joint. (Default: 0)
                'mu2' : Viscous friction coefficient at elbow joint. (Default: 0)
                i1: proximal insertion point of muscle 1 (2-element array-like).
                i2: distal insertion point of muscle 1 (2-element array-like).
                i3: proximal insertion point of muscle 2 (2-element array-like).
                i4: distal insertion point of muscle 2 (2-element array-like).
                i5: proximal insertion point of muscle 3 (2-element array-like).
                i6: distal insertion point of muscle 3 (2-element array-like).
                i7: proximal insertion point of muscle 4 (2-element array-like).
                i8: distal insertion point of muscle 4 (2-element array-like).
                i9: proximal insertion point of muscle 5 (2-element array-like).
                i10: distal insertion point of muscle 5 (2-element array-like).
                i11: proximal insertion point of muscle 6 (2-element array-like).
                i12: distal insertion point of muscle 6 (2-element array-like).
                c_elbow: coordinates of the elbow in the reference position.
                c_hand: coordinates of the hand in the reference position.
                rest_l: a 6-element array-like with the rest lengths for the 6
                        muscles. The default value is the length of the muscle
                        when the arm is at the reference position (shoulder at 0
                        radians, elbow at pi/2 radians). The units of length
                        used in rest_l are the lengths in the reference
                        position; e.g. the default value of rest_l is an array
                        like [1, 1, 1, 1, 1, 1].
                m_gain: gain for the muscle forces (default 1).
            network: the network where the plant instance lives.

        Raises:
            AssertionError.

        """
        # This is the stuff that goes into all model constructors. Adjust accordingly.
        #-------------------------------------------------------------------------------
        #assert params['type'] is plant_models.planar_arm, ['Plant ' +
        #                         str(self.ID) + ' instantiated with the wrong type']
        params['dimension'] = 28 # notifying dimensionality of model to parent constructor
        params['inp_dim'] = 18 # notifying there are eighteen input ports
        plant.__init__(self, ID, params, network) # calling parent constructor
        # Initialization of the buffer is done below.
        #-------------------------------------------------------------------------------
        # Initialize the double pendulum's parameters
        self.mass1 = params['mass1']   # mass of the rod1 [kg]
        self.mass2 = params['mass2']   # mass of the rod2 [kg]
        if 'g' in params: # gravitational force per kilogram
            self.g = params['g']
        else: 
            self.g = 9.81  # [m/s^2]
        if 'mu1' in params: # shoulder viscous friction coefficient
            self.mu1 = params['mu1'] 
        else:
            self.mu1 = 0.
        if 'mu2' in params: # elbow viscous friction coefficient
            self.mu2 = params['mu2']
        else:
            self.mu2 = 0.
        # Initialize the muscle insertion points
        #~~ biarticular biceps
        if 'p1' in params: self.p1 = params['p1']
        else: self.p1 = (0.,0.04) # proximal insertion point
        if 'p2' in params: self.p2 = params['p2']
        else: self.p2 = (0.29, 0.04) # distal insertion point
        #~~ anterior deltoid, pectoral (muscle 2)
        if 'p3' in params: self.p3 = params['p3']
        else: self.p3 = (0., 0.04)
        if 'p4' in params: self.p4 = params['p4']
        else: self.p4 = (.1, 0.02)
        #~~ posterior deltoid (muscle 3)
        if 'p5' in params: self.p5 = params['p5']
        else: self.p5 = (0., -.04)
        if 'p6' in params: self.p6 = params['p6']
        else: self.p6 = (.1, -0.02)
        #~~ biarticular triceps (muscle 4)
        if 'p7' in params: self.p7 = params['p7']
        else: self.p7 = (0., -0.04)
        if 'p8' in params: self.p8 = params['p8']
        else: self.p8 = (.3, -0.03)
        #~~ brachialis (muscle 5)
        if 'p9' in params: self.p9 = params['p9']
        else: self.p9 = (0.2, 0.02)
        if 'p10' in params: self.p10 = params['p10']
        else: self.p10 = (0.29, 0.04)
        #~~ monoarticular triceps (muscle 6)
        if 'p11' in params: self.p11 = params['p11']
        else: self.p11 = (0.2, -0.02)
        if 'p12' in params: self.p12 = params['p12']
        else: self.p12 = (0.3, -0.03)
        # elbow and hand coordinates
        if 'c_elbow' in params: self.c_elbow = params['c_elbow']
        else: self.c_elbow = (0.3, 0.)
        if 'c_hand' in params: self.c_hand = params['c_hand']
        else: self.c_hand = (0.3, 0.3)
        # some basic tests with the coordinates
        self.ip = [self.p1, self.p2, self.p3, self.p4, self.p5,self.p6,
                  self.p7, self.p8, self.p9, self.p10, self.p11, self.p12]
        assert (self.c_hand[0] == self.c_elbow[0] and 
                self.c_hand[1] > self.c_elbow[1]), ['Hand and'+
                            ' elbow coordinates not in reference position']
        for i in range(6):
            assert self.ip[2*i][0] < self.ip[2*i+1][0], ['Distal insertion ' +
                   'point not right of proximal one for muscle' + str(i+1)]
        for i in [1, 3]:
            assert self.ip[i][1] > 0, ['Insertion point ' + str(i) +
                   ' is expected to have a positive y coordinate']
        for i in [5, 7]:
            assert self.ip[i][1] < 0, ['Insertion point ' + str(i) +
                   ' is expected to have a negative y coordinate']
        # intialize rest lengths
        if 'rest_l' in params:
            self.rest_l = params['rest_l']
        else:
            self.rest_l = np.ones(6)
        if 'm_gain' in params: self.m_gain = params['m_gain']
        else: self.m_gain = 1.
        # extract geometry information from the coordinates
        #~~ arm and forearm lengths
        self.l_arm = self.c_elbow[0]  # length of the upper arm
        self.l_farm = self.c_hand[1] - self.c_elbow[1] # length of forearm
        #~~ insertion point 1
        self.l_i1 = np.sqrt(self.p1[0]**2 + self.p1[1]**2)
        self.a_i1 = np.arctan2(self.p1[1], self.p1[0])
        #~~ insertion point 2
        self.l_i2 = np.sqrt((self.p2[0]-self.c_elbow[0])**2 + self.p2[1]**2)
        self.a_i2 = np.arctan2(self.c_elbow[0]-self.p2[0], self.p2[1])
        #~~ insertion point 3
        self.l_i3 = np.sqrt(self.p3[0]**2 + self.p3[1]**2)
        self.a_i3 = np.arctan2(self.p3[1], self.p3[0])
        #~~ insertion point 4
        self.l_i4 = np.sqrt(self.p4[0]**2 + self.p4[1]**2)
        self.a_i4 = np.arctan2(self.p4[1], self.p4[0])
        #~~ insertion point 5
        self.l_i5 = np.sqrt(self.p5[0]**2 + self.p5[1]**2)
        self.a_i5 = np.arctan2(self.p5[1], self.p5[0])
        #~~ insertion point 6
        self.l_i6 = np.sqrt(self.p6[0]**2 + self.p6[1]**2)
        self.a_i6 = np.arctan2(self.p6[1], self.p6[0])
        #~~ insertion point 7
        self.l_i7 = np.sqrt(self.p7[0]**2 + self.p7[1]**2)
        self.a_i7 = np.arctan2(self.p7[1], self.p7[0])
        #~~ insertion point 8
        self.l_i8 = np.sqrt((self.p8[0]-self.c_elbow[0])**2 + self.p8[1]**2)
        self.a_i8 = np.arctan(abs((self.c_elbow[0]-self.p8[0])/self.p8[1]))
        #~~ insertion point 9
        self.l_i9 = np.sqrt(self.p9[0]**2 + self.p9[1]**2)
        self.a_i9 = np.arctan2(self.p9[1], self.p9[0])
        #~~ insertion point 10
        self.l_i10 = np.sqrt((self.p10[0]-self.c_elbow[0])**2 + self.p10[1]**2)
        self.a_i10 = np.arctan2(self.c_elbow[0]-self.p10[0], self.p10[1])
        #~~ insertion point 11
        self.l_i11 = np.sqrt(self.p11[0]**2 + self.p11[1]**2)
        self.a_i11 = np.arctan2(self.p11[1], self.p11[0])
        #~~ insertion point 12
        self.l_i12 = np.sqrt((self.p12[0]-self.c_elbow[0])**2 + self.p12[1]**2)
        self.a_i12 = np.arctan(abs((self.c_elbow[0]-self.p12[0])/self.p12[1]))
        # set limit rotation angles for shoulder insertion points (see upd_ip)
        self.q1_min = -np.pi/12.
        self.q1_max = np.pi/12.
        # create the muscles
        mus_pars = {'l0': 1., # resting length
                's' : 5., # spring constant
                'g1': self.m_gain,  # contraction input gain
                'g2': 1., # length afferent gain
                'g3': 1., # velocity afferent gain
                'dt': self.net.min_delay, # time step length
                'p1': [], # proximal insertion point
                'p2': [] } # distal insertion point
        self.muscles = []
        for i in range(6):
            mus_pars['l0'] = self.rest_l[i]
            mus_pars['p1'] = self.ip[2*i]
            mus_pars['p2'] = self.ip[2*i+1]
            self.muscles.append(spring_muscle(mus_pars))
        ##  initialize the state vector.
        self.init_state = np.zeros(self.dim)
        # initializing double pendulum state variables
        self.init_state[0:4] = np.array([params['init_q1'], params['init_q1p'],
                                         params['init_q2'], params['init_q2p']])
        self.buffer = np.array([self.init_state]*self.buff_width) 
        # initializing muscle state variables in the buffer
        self.upd_muscle_buff(0.)
        # one variable used in the update method
        self.mbs = self.net.min_buff_size

    def upd_ip(self):
        """ Update the coordinates of all the insertion points (self.ip).

            This method also updates the coordinates of the elbow and the hand.
        """
        # retrieve current angles
        if self.net.flat:
            q1 = self.buffer[0, -1] # shoulder angle
            q2 = self.buffer[2, -1] # elbow angle
        else:
            q1 = self.buffer[-1, 0] 
            q2 = self.buffer[-1, 2] 
        q12 = q1+q2
        q1_clip = max(min(q1, self.q1_max), self.q1_min)
        # update coordinates of the elbow and hand
        self.c_elbow = (self.l_arm*np.cos(q1), self.l_arm*np.sin(q1)) 
        self.c_hand = (self.c_elbow[0] + self.l_farm*np.cos(q12),
                       self.c_elbow[1] + self.l_farm*np.sin(q12))
        #~~ muscle 1
        ip1 = self.p1 # if this point doesn't rotate
        ip2 = (self.c_elbow[0] + self.l_i2*np.cos(q12+self.a_i2),
               self.c_elbow[1] + self.l_i2*np.sin(q12+self.a_i2))
        #~~ muscle 2
        ip3 = self.p3  # if this point doesn't rotate
        ip4 = (self.l_i4*np.cos(q1+self.a_i4), self.l_i4*np.sin(q1+self.a_i4))
        #~~ muscle 3
        ip5 = self.p5 # if this point doesn't rotate
        ip6 = (self.l_i6*np.cos(q1+self.a_i6), self.l_i6*np.sin(q1+self.a_i6))
        #~~ muscle 4
        ip7 = self.p7 # if this point doesn't rotate
        ip8 = (self.c_elbow[0] - self.l_i8*np.cos(q12-self.a_i8),
               self.c_elbow[1] - self.l_i8*np.sin(q12-self.a_i8))
        #~~ muscle 5
        ip9 = (self.l_i9*np.cos(q1+self.a_i9), self.l_i9*np.sin(q1+self.a_i9))
        ip10 = (self.c_elbow[0] + self.l_i10*np.cos(q12+self.a_i10),
                self.c_elbow[1] + self.l_i10*np.sin(q12+self.a_i10))
        #~~ muscle 6
        ip11 = (self.l_i11*np.cos(q1+self.a_i11), self.l_i11*np.sin(q1+self.a_i11))
        ip12 = (self.c_elbow[0] - self.l_i12*np.cos(q12-self.a_i12),
                self.c_elbow[1] - self.l_i12*np.sin(q12-self.a_i12))
        self.ip = [ip1, ip2, ip3, ip4, ip5, ip6, ip7, ip8, ip9, ip10, ip11, ip12]

    def upd_muscle_buff(self, time, flat=False):
        """ Update the buffer entries for the muscle variables. 
        
            'time' is the time for which the muscle inputs will be retrieved.
            Notice that regardless of the value of 'time', the muscle
            insertion points used will be the latest ones.
            
            The 'flat' argument indicates whether the network is flattened,
            which means that the buffer has the indexes reversed.
        """
        self.upd_ip() # update the coordinates of all insertion points
        for idx, musc in enumerate(self.muscles):
            musc.update(self.ip[2*idx], self.ip[2*idx+1],
                        self.get_input_sum(time, 3*idx),
                        self.get_input_sum(time, 3*idx+1),
                        self.get_input_sum(time, 3*idx+2))
            base = 4 * (idx + 1) # auxiliary index variable
            if not flat:
                self.buffer[:, base] = [musc.l] * self.buff_width
                self.buffer[:, base+1] = [musc.affs[0]] * self.buff_width
                self.buffer[:, base+2] = [musc.affs[1]] * self.buff_width
                self.buffer[:, base+3] = [musc.affs[2]] * self.buff_width
            else:
                self.buffer[base, :] = [musc.l] * self.buff_width
                self.buffer[base+1, :] = [musc.affs[0]] * self.buff_width
                self.buffer[base+2, :] = [musc.affs[1]] * self.buff_width
                self.buffer[base+3, :] = [musc.affs[2]] * self.buff_width

    def shoulder_torque(self, i_prox, i_dist, T):
    	""" Obtain the torque produced by a muscle wrt the shoulder joint.
    	
        	Args:
            	i_prox : coordinates of proximal insertion point (tuple)
            	i_dist : coordinates of distal insertion point (tuple)
            	T : muscle tension
        	Returns:
            	float
    	"""
    	v = np.array([i_prox[0] - i_dist[0], i_prox[1] - i_dist[1]])
    	v_norm = (sum(v*v))**(1./2.)
    	F = (T/v_norm) * v
    	tau = i_dist[0] * F[1] - i_dist[1] * F[0]
    	return tau
	
    def elbow_torque(self, i_prox, i_dist, T):
    	""" Obtain the torque produced by a muscle wrt the shoulder joint.
    	
        	Args:
            	i_prox : coordinates of proximal insertion point (tuple)
            	i_dist : coordinates of distal insertion point (tuple)
            	T : muscle tension
        	Returns:
            	float
    	"""
    	v = np.array([i_prox[0] - i_dist[0], i_prox[1] - i_dist[1]])
    	v_norm = (sum(v*v))**(1./2.)
    	F = (T/v_norm) * v
        # notice c_elbow is currently updated by upd_ip()
    	tau = ((i_dist[0]-self.c_elbow[0]) * F[1] - 
               (i_dist[1]-self.c_elbow[1]) * F[0])
    	return tau
        
    def derivatives(self, y, t):
        """ Returns the derivatives of the state variables at a given point in time. 

        Because the muscle model has no differential dynamics, this method only deals
        with the first 4 state variables. This implies that during each integration
        step the muscle tensions are considered to be constant.

        The muscle variables are handled by the custom update methods.
        Inputs to the muscles are appliead in upd_muscle_buffs.
        These equations were copy-pasted from double_pendulum_validation.ipynb .

        Args:
            y : state vector (list-like) ...
                y[0] : angle of shoulder [radians]
                y[1] : angular velocity of shoulder [radians / s]
                y[2] : angle of elbow [radians]
                y[3] : angular velocity of elbow [radians / s]
            t : time at which the derivative is evaluated [s]
        Returns:
            dydt : vector of derivtives (numpy array) ...
                dydt[0] : angular velocity of shoulder [radians / s]
                dydt[1] : angular acceleration of shoulder [radians/s^2]
                dydt[2] : angular velocity of elbow [radians / s]
                dydt[3] : angular acceleration of elbow [radians/s^2]
        """
	# obtaining the muscle torques
        #~~ muscle 1 wrt shouler
        tau1s = self.shoulder_torque(self.ip[0], self.ip[1], self.muscles[0].T)
        #~~ muscle 1 wrt elbow
        tau1e = self.elbow_torque(self.ip[0], self.ip[1], self.muscles[0].T)
	#~~ muscle 2 wrt shoulder
        tau2s = self.shoulder_torque(self.ip[2], self.ip[3], self.muscles[1].T)
	#~~ muscle 3 wrt shoulder
        tau3s = self.shoulder_torque(self.ip[4], self.ip[5], self.muscles[2].T)
	#~~ muscle 4 wrt shoulder
        tau4s = self.shoulder_torque(self.ip[6], self.ip[7], self.muscles[3].T)
	#~~ muscle 4 wrt elbow
        tau4e = self.elbow_torque(self.ip[6], self.ip[7], self.muscles[3].T)
	#~~ muscle 5 wrt elbow
        tau5e = self.elbow_torque(self.ip[8], self.ip[9], self.muscles[4].T)
	#~~ muscle 6 wrt elbow
        tau6e = self.elbow_torque(self.ip[10], self.ip[11], self.muscles[5].T)
        tau1 = tau1s + tau2s + tau3s + tau4s # shoulder torque
        tau2 = tau1e + tau4e + tau5e + tau6e # elbow torque
        ## torques from inputs
        #tau1 = self.get_input_sum(t,0)
        #tau2 = self.get_input_sum(t,1)
	# setting shorter names for the variables
        q1 = y[0]
        q1p = y[1]
        q2 = y[2]
        q2p = y[3]
        L1 = self.l_arm
        L2 = self.l_farm
        m1 = self.mass1
        m2 = self.mass2
        g = self.g
        mu1 = self.mu1
        mu2 = self.mu2
        # equations
        dydt = np.zeros_like(y)
        dydt[0] = q1p
        dydt[1] = 3.0*(-2.0*L2*(-2.0*L1*L2*m2*q1p*q2p*sin(q2) - L1*L2*m2*q2p**2*sin(q2) +
                       L1*g*m1*cos(q1) + 2.0*L1*g*m2*cos(q1) + L2*g*m2*cos(q1 + q2) +
                       2.0*mu1*q1p - 2.0*tau1) + (3.0*L1*cos(q2) + 2.0*L2) * 
                       (L1*L2*m2*q1p**2*sin(q2) + L2*g*m2*cos(q1 + q2) +
                       2.0*mu2*q2p - 2.0*tau2)) / ( 
                       L1**2*L2*(4.0*m1 + 9.0*m2*sin(q2)**2 + 3.0*m2))
        dydt[2] = q2p
        dydt[3] = 3.0*(L2*m2*(3.0*L1*cos(q2) + 2.0*L2)*(-2.0*L1*L2*m2*q1p*q2p*sin(q2) -
                       L1*L2*m2*q2p**2*sin(q2) + L1*g*m1*cos(q1) + 2.0*L1*g*m2*cos(q1) +
                       L2*g*m2*cos(q1 + q2) + 2.0*mu1*q1p - 2.0*tau1) -
                       2.0*(L1**2*m1 + 3.0*L1**2*m2 + 3.0*L1*L2*m2*cos(q2) + L2**2*m2) *
                       (L1*L2*m2*q1p**2*sin(q2) + L2*g*m2*cos(q1 + q2) + 2.0*mu2*q2p -
                       2.0*tau2)) / (L1**2*L2**2*m2*(4.0*m1 + 9.0*m2*sin(q2)**2 + 3.0*m2))
        return dydt

           
    def update(self, time):
        ''' This function advances the state for net.min_delay time units. 
        
            Since the planar arm has 28 variables, 4 of which are handled by the ODE
            integrator, it is necessary to customize this method so the right values
            are entered into the buffer.
        '''
        # updating the double pendulum state variables
        new_times = self.times[-1] + self.times_grid
        self.times += self.net.min_delay
        self.buffer[:self.offset,:] = self.buffer[self.mbs:,:]
        self.buffer[self.offset:,0:4] = odeint(self.derivatives, self.buffer[-1,0:4],
                                    new_times, rtol=self.rtol, atol=self.atol)[1:,:]
        # updating the muscles
        self.upd_muscle_buff(time)

    def flat_update(self, time):
        """ advances the state for net.min_delay time units when the network is flat. """
        # self.times is a view of network.ts
        nts = self.times[self.offset-1:] # times relevant for the update
        solution = solve_ivp(self.dt_fun, (nts[0], nts[-1]), self.buffer[0:4,-1], 
                             t_eval=nts, rtol=self.rtol, atol=self.atol)
        np.put(self.buffer[0:4,self.offset:], range(self.net.min_buff_size*4), 
               solution.y[:,1:])
        # updating the muscles
        self.upd_muscle_buff(time, flat=True)


            

