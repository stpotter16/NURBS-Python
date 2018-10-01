"""
.. module:: BSpline
    :platform: Unix, Windows
    :synopsis: Provides data storage and evaluation functionality for B-spline curves and surfaces

.. moduleauthor:: Onur Rauf Bingol <orbingol@gmail.com>

"""

import warnings
import pickle
from . import Abstract
from . import utilities
from . import helpers
from . import evaluators
from . import operations
from . import tessellate


class Curve(Abstract.Curve):
    """ Data storage and evaluation class for n-variate B-Spline (non-rational) curves.

    Notes:
        * Please see the :py:class:`.Abstract.Curve()` documentation for details.
        * This class sets the *FindSpan* implementation to Linear Search by default.
    """

    def __init__(self, **kwargs):
        super(Curve, self).__init__(**kwargs)
        # self._name = "B-Spline Curve"
        self._span_func = kwargs.get('find_span_func', helpers.find_span_linear)
        self._evaluator = evaluators.CurveEvaluator(find_span_func=self._span_func)

    @property
    def ctrlpts(self):
        """ Control points.

        :getter: Gets the control points
        :setter: Sets the control points
        :type: list
        """
        ret_list = []
        for pt in self._control_points:
            ret_list.append(tuple(pt))
        return tuple(ret_list)

    @ctrlpts.setter
    def ctrlpts(self, value):
        self.set_ctrlpts(value)

    @property
    def knotvector(self):
        """ Knot vector.

        :getter: Gets the knot vector
        :setter: Sets the knot vector
        :type: list
        """
        return tuple(self._knot_vector)

    @knotvector.setter
    def knotvector(self, value):
        # Call parent property setter
        super(Curve, self.__class__).knotvector.fset(self, value)

        # Normalize knot vector
        self._knot_vector = utilities.normalize_knot_vector(self._knot_vector, decimals=self._precision)

    def save(self, file_name):
        """  Saves the curve as a pickled file.

        :param file_name: name of the file to be saved
        :type file_name: str
        :raises IOError: an error occurred writing the file
        """
        # Create a dictionary from the curve data
        expdata = {'rational': self._rational,
                   'degree': self._degree,
                   'knotvector': self._knot_vector,
                   'ctrlpts': self._control_points,
                   'dimension': self._dimension}

        save_pickle(expdata, file_name)

    def load(self, file_name):
        """ Loads the curve from a pickled file.

        :param file_name: name of the file to be loaded
        :type file_name: str
        :raises IOError: an error occurred reading the file
        """
        impdata = read_pickle(file_name)

        if self._rational != impdata['rational']:
            raise TypeError("Curve types are not compatible (NURBS-BSpline mismatch)")

        # Clean control points and evaluated points
        self.reset(ctrlpts=True, evalpts=True)

        # Set the curve data
        self._degree = impdata['degree']
        self._knot_vector = impdata['knotvector']
        self._dimension = impdata['dimension']
        self._control_points = impdata['ctrlpts']

    def curvept(self, u):
        """ Evaluates the curve at the given parameter.

        :param u: parameter
        :type u: float
        :return: evaluated curve point
        :rtype: list
        """
        return self.evaluate_single(u)

    def evaluate(self, **kwargs):
        """ Evaluates the curve.

        **The evaluated curve points are stored in :py:attr:`~evalpts` property.**

        Keyword arguments:
            * ``start``: start parameter
            * ``stop``: stop parameter

        The ``start`` and ``stop`` parameters allow evaluation of a curve segment in the range *[start, stop]*, i.e.
        the curve will also be evaluated at the ``stop`` parameter value.

        The following examples illustrate the usage of the keyword arguments.

        .. code-block:: python

            # Start evaluating from u=0.2 to u=1.0
            curve.evaluate(start=0.2)

            # Start evaluating from u=0.0 to u=0.7
            curve.evaluate(stop=0.7)

            # Start evaluating from u=0.1 to u=0.5
            curve.evaluate(start=0.1, stop=0.5)

            # Get the evaluated points
            curve_points = curve.evalpts

        """
        # Call parent method
        super(Curve, self).evaluate(**kwargs)

        # Find evaluation start and stop parameter values
        start = kwargs.get('start', self.knotvector[self.degree])
        stop = kwargs.get('stop', self.knotvector[-(self.degree+1)])

        # Check if the input parameters are in the range
        utilities.check_uv(start)
        utilities.check_uv(stop)

        # Clean up the curve points
        self.reset(evalpts=True)

        # Evaluate
        cpts = self._evaluator.evaluate(start_u=start, stop_u=stop,
                                        degree=self.degree,
                                        knotvector=self.knotvector,
                                        ctrlpts=self._control_points,
                                        sample_size=self.sample_size,
                                        dimension=self._dimension,
                                        precision=self._precision)

        self._curve_points = cpts

    def evaluate_single(self, u):
        """ Evaluates the curve at the given parameter.

        :param u: parameter
        :type u: float
        :return: evaluated surface point at the given parameter
        :rtype: list
        """
        # Call parent method
        super(Curve, self).evaluate_single(u)

        # Check u parameters are correct
        utilities.check_uv(u)

        # Evaluate
        return self._evaluator.evaluate_single(knot=u,
                                               degree=self.degree,
                                               knotvector=self.knotvector,
                                               ctrlpts=self._control_points,
                                               dimension=self._dimension)

    def evaluate_list(self, u_list):
        """ Evaluates the curve for an input range of parameters.

        :param u_list: list of parameters
        :type u_list: list, tuple
        :return: evaluated surface points at the input parameters
        :rtype: tuple
        """
        # Call parent method
        super(Curve, self).evaluate_list(u_list)

        # Tolerance value
        tol = 10e-8

        # Evaluate (u,v) list
        res = []
        for u in u_list:
            if 0.0 + tol < u < 1.0 - tol:
                res.append(self.evaluate_single(u))
        return tuple(res)

    # Evaluates the curve derivative
    def derivatives(self, u, order=0, **kwargs):
        """ Evaluates n-th order curve derivatives at the given parameter value.

        :param u: parameter value
        :type u: float
        :param order: derivative order
        :type order: int
        :return: a list containing up to {order}-th derivative of the curve
        :rtype: list
        """
        # Call parent method
        super(Curve, self).derivatives(u=u, order=order, **kwargs)

        # Evaluate and return the derivative at knot u
        return self._evaluator.derivatives_single(knot=u,
                                                  deriv_order=order,
                                                  degree=self.degree,
                                                  knotvector=self.knotvector,
                                                  ctrlpts=self._control_points,
                                                  dimension=self._dimension)

    # Knot insertion
    def insert_knot(self, u, r=1, check_r=True):
        """ Inserts the given knot and updates the control points array and the knot vector.

        :param u: knot to be inserted
        :type u: float
        :param r: number of knot insertions
        :type r: int
        :param check_r: enables/disables number of knot insertions check
        :type check_r: bool
        """
        # Check all parameters are set before the curve evaluation
        self._check_variables()

        # Check u parameters are correct
        utilities.check_uv(u)

        # Check if the number of knot insertions requested is valid
        if not isinstance(r, int) or r < 0:
            raise ValueError('Number of insertions (r) must be a positive integer value')

        s = helpers.find_multiplicity(u, self.knotvector)

        # Check if it is possible add that many number of knots
        if check_r and r > self._degree - s:
            raise ValueError("Cannot insert " + str(r) + " number of knots")

        UQ, Q = self._evaluator.insert_knot(knot=u,
                                            r=r,
                                            s=s,
                                            degree=self.degree,
                                            knotvector=self.knotvector,
                                            ctrlpts=self._control_points,
                                            dimension=self._dimension)

        # Update class variables
        self._knot_vector = UQ
        self._control_points = Q

        # Evaluate curve again if it has already been evaluated before knot insertion
        if check_r and self._curve_points:
            self.evaluate()

    def tangent(self, param, **kwargs):
        """ Evaluates the tangent vector of the curve at the given parametric position(s).

        The ``param`` argument can be

        * a float value for evaluation at a single parametric position
        * a list of float values for evaluation at the multiple parametric positions

        The return value will be in the order of the input parametric position list.

        This method accepts the following keyword arguments:

        * ``normalize``: normalizes the output vector. Default value is *True*.

        :param param: parametric position(s) where the evaluation will be executed
        :type param: float, list or tuple
        :return: an array containing "point" and "vector" pairs
        :rtype: tuple
        """
        return operations.tangent(self, param, **kwargs)

    def normal(self, parpos, **kwargs):
        """ Evaluates the normal vector of the curve at the given parametric position(s).

        The ``param`` argument can be

        * a float value for evaluation at a single parametric position
        * a list of float values for evaluation at the multiple parametric positions

        The return value will be in the order of the input parametric position list.

        This method accepts the following keyword arguments:

        * ``normalize``: normalizes the output vector. Default value is *True*.

        :param parpos: parametric position(s) where the evaluation will be executed
        :type parpos: float, list or tuple
        :return: an array containing "point" and "vector" pairs
        :rtype: tuple
        """
        return operations.normal(self, parpos, **kwargs)

    def binormal(self, parpos, **kwargs):
        """ Evaluates the binormal vector of the curve at the given parametric position(s).

        The ``param`` argument can be

        * a float value for evaluation at a single parametric position
        * a list of float values for evaluation at the multiple parametric positions

        The return value will be in the order of the input parametric position list.

        This method accepts the following keyword arguments:

        * ``normalize``: normalizes the output vector. Default value is *True*.

        :param parpos: parametric position(s) where the evaluation will be executed
        :type parpos: float, list or tuple
        :return: an array containing "point" and "vector" pairs
        :rtype: tuple
        """
        return operations.binormal(self, parpos, **kwargs)


class Surface(Abstract.Surface):
    """ Data storage and evaluation class for B-Spline (non-rational) surfaces.

    Notes:
        * Please see the :py:class:`.Abstract.Surface()` documentation for details.
        * This class sets the *FindSpan* implementation to Linear Search by default.
    """

    def __init__(self, **kwargs):
        super(Surface, self).__init__(**kwargs)
        # self._name = "B-Spline Surface"
        self._span_func = kwargs.get('find_span_func', helpers.find_span_linear)
        self._evaluator = evaluators.SurfaceEvaluator(find_span_func=self._span_func)
        self._tsl_component = tessellate.TriangularTessellate()

    @property
    def ctrlpts(self):
        """ 1-dimensional array of control points.

        .. note::

            The v index varies first. That is, a row of v control points for the first u value is found first.
            Then, the row of v control points for the next u value.

        :getter: Gets the control points
        :setter: Sets the control points
        :type: list
        """
        ret_list = []
        for pt in self._control_points:
            ret_list.append(tuple(pt))
        return tuple(ret_list)

    @ctrlpts.setter
    def ctrlpts(self, value):
        if self._control_points_size_u <= 0 and self._control_points_size_v <= 0:
            raise ValueError("Please set size of the control points in u and v directions")

        # Use set_ctrlpts directly
        self.set_ctrlpts(value, self._control_points_size_u, self._control_points_size_v)

    @property
    def ctrlpts2d(self):
        """ 2-dimensional array of control points.

        The getter returns a tuple of 2D control points (weighted control points + weights if NURBS) in *[u][v]* format.
        The rows of the returned tuple correspond to v-direction and the columns correspond to u-direction.

        The following example can be used to traverse 2D control points:

        .. code-block:: python

            # Create a BSpline surface
            surf_bs = BSpline.Surface()

            # Do degree, control points and knot vector assignments here

            # Each u includes a row of v values
            for u in surf_bs.ctrlpts2d:
                # Each row contains the coordinates of the control points
                for v in u:
                    print(str(v))  # will be something like (1.0, 2.0, 3.0)

            # Create a NURBS surface
            surf_nb = NURBS.Surface()

            # Do degree, weighted control points and knot vector assignments here

            # Each u includes a row of v values
            for u in surf_nb.ctrlpts2d:
                # Each row contains the coordinates of the weighted control points
                for v in u:
                    print(str(v))  # will be something like (0.5, 1.0, 1.5, 0.5)


        When using **NURBS.Surface** class, the output of :py:attr:`~ctrlpts2d` property could be confusing since,
        :py:attr:`~ctrlpts` always returns the unweighted control points, i.e. :py:attr:`~ctrlpts` property returns 3D
        control points all divided by the weights and you can use :py:attr:`~weights` property to access the weights
        vector, but :py:attr:`~ctrlpts2d` returns the weighted ones plus weights as the last element.
        This difference is intentionally added for compatibility and interoperability purposes.

        To explain this situation in a simple way;

        * If you need the weighted control points directly, use :py:attr:`~ctrlpts2d`
        * If you need the control points and the weights separately, use :py:attr:`~ctrlpts` and :py:attr:`~weights`

        .. note::

            Please note that the setter doesn't check for inconsistencies and using the setter is not recommended.
            Instead of the setter property, please use :func:`.set_ctrlpts()` function.

        :getter: Gets the control points as a 2-dimensional array in [u][v] format
        :setter: Sets the control points as a 2-dimensional array in [u][v] format
        :type: list
        """
        ret_list = []
        for u in range(0, self._control_points_size_u):
            ret_list_v = []
            for v in range(0, self._control_points_size_v):
                ret_list_v.append(tuple(self._control_points2D[u][v]))
            ret_list.append(tuple(ret_list_v))
        return tuple(ret_list)

    @ctrlpts2d.setter
    def ctrlpts2d(self, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("The input must be a list or tuple")

        # Clean up the surface and control points
        self.reset(evalpts=True, ctrlpts=True)

        # Assume that the user has prepared the lists correctly
        self._control_points_size_u = len(value)
        self._control_points_size_v = len(value[0])

        # Estimate dimension by checking the size of the first element
        self._dimension = len(value[0][0])

        # Make sure that all numbers are float type
        ctrlpts2d = [[[] for _ in range(0, self._control_points_size_v)]
                     for _ in range(0, self._control_points_size_u)]
        for u in range(0, self._control_points_size_u):
            for v in range(0, self._control_points_size_v):
                ctrlpts2d[u][v] = [float(coord) for coord in value[u][v]]

        # Set 2D control points
        self._control_points2D = ctrlpts2d

        # Set 1D control points
        for u in self._control_points2D:
            for v in u:
                self._control_points.append(v)

    @property
    def knotvector_u(self):
        """ Knot vector for u-direction.

        :getter: Gets the knot vector for u-direction
        :setter: Sets the knot vector for u-direction
        :type: list
        """
        return tuple(self._knot_vector_u)

    @knotvector_u.setter
    def knotvector_u(self, value):
        # Call parent property setter
        super(Surface, self.__class__).knotvector_u.fset(self, value)

        # Normalize knot vector
        self._knot_vector_u = utilities.normalize_knot_vector(self._knot_vector_u, decimals=self._precision)

    @property
    def knotvector_v(self):
        """ Knot vector for v-direction.

        :getter: Gets the knot vector for v-direction
        :setter: Sets the knot vector for v-direction
        :type: list
        """
        return tuple(self._knot_vector_v)

    @knotvector_v.setter
    def knotvector_v(self, value):
        # Call parent property setter
        super(Surface, self.__class__).knotvector_v.fset(self, value)

        # Normalize knot vector
        self._knot_vector_v = utilities.normalize_knot_vector(self._knot_vector_v, decimals=self._precision)

    def save(self, file_name):
        """ Saves the surface as a pickled file.

        :param file_name: name of the file to be saved
        :type file_name: str
        :raises IOError: an error occurred writing the file
        """
        # Create a dictionary from the surface data
        expdata = {'rational': self._rational,
                   'degree_u': self._degree_u,
                   'degree_v': self._degree_v,
                   'knotvector_u': self._knot_vector_u,
                   'knotvector_v': self._knot_vector_v,
                   'ctrlpts_size_u': self._control_points_size_u,
                   'ctrlpts_size_v': self._control_points_size_v,
                   'ctrlpts': self._control_points,
                   'dimension': self._dimension}

        save_pickle(expdata, file_name)

    def load(self, file_name):
        """ Loads the surface from a pickled file.

        :param file_name: name of the file to be loaded
        :type file_name: str
        :raises IOError: an error occurred reading the file
        """
        impdata = read_pickle(file_name)

        # Check if we have loaded the correct type of surface
        if self._rational != impdata['rational']:
            raise TypeError("Surface types are not compatible (NURBS-BSpline mismatch)")

        # Clean control points and evaluated points
        self.reset(ctrlpts=True, evalpts=True)

        # Set the surface data
        self._degree_u = impdata['degree_u']
        self._degree_v = impdata['degree_v']
        self._knot_vector_u = impdata['knotvector_u']
        self._knot_vector_v = impdata['knotvector_v']
        self._control_points_size_u = impdata['ctrlpts_size_u']
        self._control_points_size_v = impdata['ctrlpts_size_v']
        self._dimension = impdata['dimension']
        self._control_points = impdata['ctrlpts']

    def transpose(self):
        """ Transposes the surface by swapping u- and v-directions. """
        # Transpose existing data
        degree_u_new = self._degree_v
        degree_v_new = self._degree_u
        kv_u_new = self._knot_vector_v
        kv_v_new = self._knot_vector_u
        ctrlpts2d_new = []
        for v in range(0, self._control_points_size_v):
            ctrlpts_u = []
            for u in range(0, self._control_points_size_u):
                temp = self._control_points2D[u][v]
                ctrlpts_u.append(temp)
            ctrlpts2d_new.append(ctrlpts_u)
        ctrlpts_new_size_u = self._control_points_size_v
        ctrlpts_new_size_v = self._control_points_size_u

        ctrlpts_new = []
        for v in range(0, ctrlpts_new_size_v):
            for u in range(0, ctrlpts_new_size_u):
                ctrlpts_new.append(ctrlpts2d_new[u][v])

        # Clean up the surface points
        self.reset(evalpts=True)

        # Save transposed data
        self._degree_u = degree_u_new
        self._degree_v = degree_v_new
        self._knot_vector_u = kv_u_new
        self._knot_vector_v = kv_v_new
        self._control_points = ctrlpts_new
        self._control_points_size_u = ctrlpts_new_size_u
        self._control_points_size_v = ctrlpts_new_size_v
        self._control_points2D = ctrlpts2d_new

    def surfpt(self, u, v):
        """ Evaluates the surface at the given (u,v) parameter pair.

        :param u: parameter on the u-direction
        :type u: float
        :param v: parameter on the v-direction
        :type v: float
        :return: evaluated surface point at the given parameter pair
        :rtype: list
        """
        return self.evaluate_single([u, v])

    def evaluate(self, **kwargs):
        """ Evaluates the surface.

        **The evaluated surface points are stored in :py:attr:`~evalpts` property.**

        Keyword arguments:
            * ``start_u``: start parameter on the u-direction
            * ``stop_u``: stop parameter on the u-direction
            * ``start_v``: start parameter on the v-direction
            * ``stop_v``: stop parameter on the v-direction

        The ``start_u``, ``start_v`` and ``stop_u`` and ``stop_v`` parameters allow evaluation of a surface segment
        in the range  *[start_u, stop_u][start_v, stop_v]* i.e. the surface will also be evaluated at the ``stop_u``
        and ``stop_v`` parameter values.

        The following examples illustrate the usage of the keyword arguments.

        .. code-block:: python

            # Start evaluating in range u=[0, 0.7] and v=[0.1, 1]
            surf.evaluate(stop_u=0.7, start_v=0.1)

            # Start evaluating in range u=[0, 1] and v=[0.1, 0.3]
            surf.evaluate(start_v=0.1, stop_v=0.3)

            # Get the evaluated points
            surface_points = surf.evalpts

        """
        # Call parent method
        super(Surface, self).evaluate(**kwargs)

        # Find evaluation start and stop parameter values
        start_u = kwargs.get('start_u', self.knotvector_u[self.degree_u])
        stop_u = kwargs.get('stop_u', self.knotvector_u[-(self.degree_u+1)])
        start_v = kwargs.get('start_v', self.knotvector_v[self.degree_v])
        stop_v = kwargs.get('stop_v', self.knotvector_v[-(self.degree_v+1)])

        # Check if all the input parameters are in the range
        utilities.check_uv(start_u, stop_u)
        utilities.check_uv(start_v, stop_v)

        # Clean up the surface points
        self.reset(evalpts=True)

        # Evaluate
        spts = self._evaluator.evaluate(start_u=start_u, stop_u=stop_u, start_v=start_v, stop_v=stop_v,
                                        degree_u=self.degree_u, degree_v=self.degree_v,
                                        knotvector_u=self.knotvector_u, knotvector_v=self.knotvector_v,
                                        ctrlpts_size_u=self.ctrlpts_size_u, ctrlpts_size_v=self.ctrlpts_size_v,
                                        ctrlpts=self._control_points2D,
                                        sample_size=self.sample_size,
                                        dimension=self._dimension,
                                        precision=self._precision)

        self._surface_points = spts

    def evaluate_single(self, uv):
        """ Evaluates the surface at the given (u,v) parameter pair.

        :param uv: parameter pair (u, v)
        :type uv: list, tuple
        :return: evaluated surface point at the given parameter pair
        :rtype: list
        """
        # Call parent method
        super(Surface, self).evaluate_single(uv)

        # Check u and v parameters are correct
        utilities.check_uv(uv[0], uv[1])

        # Evaluate the surface
        spt = self._evaluator.evaluate_single(knot_u=uv[0], knot_v=uv[1],
                                              degree_u=self.degree_u, degree_v=self.degree_v,
                                              knotvector_u=self.knotvector_u, knotvector_v=self.knotvector_v,
                                              ctrlpts_size_u=self.ctrlpts_size_u, ctrlpts_size_v=self.ctrlpts_size_v,
                                              ctrlpts=self._control_points2D,
                                              dimension=self._dimension)

        return spt

    def evaluate_list(self, uv_list):
        """ Evaluates the surface for a given list of (u,v) parameters.

        :param uv_list: list of parameter pairs (u, v)
        :type uv_list: list, tuple
        :return: evaluated surface point at the input parameter pairs
        :rtype: tuple
        """
        # Call parent method
        super(Surface, self).evaluate_list(uv_list)

        # Tolerance value
        tol = 10e-8

        # Evaluate (u,v) list
        res = []
        for uv in uv_list:
            if 0.0 + tol < uv[0] < 1.0 - tol and 0.0 + tol < uv[1] < 1.0 - tol:
                res.append(self.evaluate_single(uv))
        return tuple(res)

    # Evaluates n-th order surface derivatives at the given (u,v) parameter
    def derivatives(self, u, v, order=0, **kwargs):
        """ Evaluates n-th order surface derivatives at the given (u, v) parameter pair.

        * SKL[0][0] will be the surface point itself
        * SKL[0][1] will be the 1st derivative w.r.t. v
        * SKL[2][1] will be the 2nd derivative w.r.t. u and 1st derivative w.r.t. v

        :param u: parameter on the u-direction
        :type u: float
        :param v: parameter on the v-direction
        :type v: float
        :param order: derivative order
        :type order: integer
        :return: A list SKL, where SKL[k][l] is the derivative of the surface S(u,v) w.r.t. u k times and v l times
        :rtype: list
        """
        # Call parent method
        super(Surface, self).derivatives(u=u, v=v, order=order, **kwargs)

        # Evaluate and return the derivatives
        return self._evaluator.derivatives_single(knot_u=u, knot_v=v, deriv_order=order,
                                                  degree_u=self.degree_u, degree_v=self.degree_v,
                                                  knotvector_u=self.knotvector_u, knotvector_v=self.knotvector_v,
                                                  ctrlpts_size_u=self.ctrlpts_size_u,
                                                  ctrlpts_size_v=self.ctrlpts_size_v,
                                                  ctrlpts=self._control_points2D,
                                                  dimension=self._dimension)

    # Insert knot 'r' times at the given (u, v) parametric coordinates
    def insert_knot(self, u=None, v=None, ru=1, rv=1, check_r=True):
        """ Inserts the knot in single dimension, with only u or v input, or multi-dimensions, with a (u,v) pair input.

        :param u: Knot to be inserted on the u-direction
        :type u: float
        :param v: Knot to be inserted on the v-direction
        :type v: float
        :param ru: Number of knot insertions on the u-direction
        :type ru: int
        :param rv: Number of knot insertions on the v-direction
        :type rv: int
        :param check_r: enables/disables number of knot insertions check
        :type check_r: bool
        """
        can_insert_knot = True

        # Check all parameters are set before the curve evaluation
        self._check_variables()

        # Check if the parameter values are correctly defined
        if u or v:
            utilities.check_uv(u, v)

        if not isinstance(ru, int) or ru < 0:
            raise ValueError("Number of insertions on the u-direction must be a positive integer")

        if not isinstance(rv, int) or rv < 0:
            raise ValueError("Number of insertions on the v-direction must be a positive integer")

        # Algorithm A5.3
        if u:
            s_u = helpers.find_multiplicity(u, self.knotvector_u)

            # Check if it is possible add that many number of knots
            if check_r and ru > self.degree_u - s_u:
                warnings.warn("Cannot insert " + str(ru) + " knots on the u-direction")
                can_insert_knot = False

            if can_insert_knot:
                UQ, Q = self._evaluator.insert_knot_u(knot=u, r=ru, s=s_u, degree=self.degree_u,
                                                      knotvector=self.knotvector_u,
                                                      ctrlpts_size_u=self.ctrlpts_size_u,
                                                      ctrlpts_size_v=self.ctrlpts_size_v,
                                                      ctrlpts=self._control_points2D)

                # Update class variables after knot insertion
                self._knot_vector_u = UQ
                self._control_points2D = Q
                self._control_points_size_u += ru
                # Update 1D control points
                self._control_points[:] = []
                for dir_u in self._control_points2D:
                    for dir_v in dir_u:
                        self._control_points.append(dir_v)

        if v:
            s_v = helpers.find_multiplicity(v, self.knotvector_v)

            # Check if it is possible add that many number of knots
            if check_r and rv > self.degree_v - s_v:
                warnings.warn("Cannot insert " + str(rv) + " knots on the v-direction")
                can_insert_knot = False

            if can_insert_knot:
                VQ, Q = self._evaluator.insert_knot_v(knot=v, r=rv, s=s_v, degree=self.degree_v,
                                                      knotvector=self.knotvector_v,
                                                      ctrlpts_size_u=self.ctrlpts_size_u,
                                                      ctrlpts_size_v=self.ctrlpts_size_v,
                                                      ctrlpts=self._control_points2D)

                # Update class variables after knot insertion
                self._knot_vector_v = VQ
                self._control_points2D = Q
                self._control_points_size_v += rv
                # Update 1D control points
                self._control_points[:] = []
                for dir_u in self._control_points2D:
                    for dir_v in dir_u:
                        self._control_points.append(dir_v)

        # Evaluate surface again if it has already been evaluated before knot insertion
        if check_r and self._surface_points:
            self.evaluate()

    def tangent(self, parpos, **kwargs):
        """ Evaluates the tangent vectors of the surface at the given parametric position(s).

        The ``param`` argument can be

        * a float value for evaluation at a single parametric position
        * a list of float values for evaluation at the multiple parametric positions

        The parametric positions should be a pair of (u,v) values. The return value will be in the order of the input
        parametric position list.

        This method accepts the following keyword arguments:

        * ``normalize``: normalizes the output vector. Default value is *True*.

        :param parpos: parametric position(s) where the evaluation will be executed
        :type parpos: list or tuple
        :return: an array containing "point" and "vector"s on u- and v-directions, respectively
        :rtype: tuple
        """
        return operations.tangent(self, parpos, **kwargs)

    def normal(self, parpos, **kwargs):
        """ Evaluates the normal vector of the surface at the given parametric position(s).

        The ``param`` argument can be

        * a float value for evaluation at a single parametric position
        * a list of float values for evaluation at the multiple parametric positions

        The parametric positions should be a pair of (u,v) values. The return value will be in the order of the input
        parametric position list.

        This method accepts the following keyword arguments:

        * ``normalize``: normalizes the output vector. Default value is *True*.

        :param parpos: parametric position(s) where the evaluation will be executed
        :type parpos: list or tuple
        :return: an array containing "point" and "vector" pairs
        :rtype: tuple
        """
        return operations.normal(self, parpos, **kwargs)


def save_pickle(data_dict, file_name):
    """ Saves the contents of the data dictionary as a pickled file.

    Helper function for curve and surface ``save`` method.

    :param data_dict: data dictionary
    :type data_dict: dict
    :param file_name: name of the file to be saved
    :type file_name: str
    :raises IOError: an error occurred writing the file
    """
    # Try opening the file for writing
    try:
        with open(file_name, 'wb') as fp:
            # Pickle the data dictionary
            pickle.dump(data_dict, fp)
    except IOError as e:
        print("An error occurred. {}".format(e.args[-1]))
        raise e
    except Exception:
        raise


def read_pickle(file_name):
    """ Reads a data dictionary from a pickled file.

    Helper function for curve and surface ``load`` method.

    :param file_name: name of the file to be loaded
    :type file_name: str
    :return: data dictionary
    :rtype: dict
    :raises IOError: an error occurred reading the file
    """
    # Try opening the file for reading
    try:
        with open(file_name, 'rb') as fp:
            # Read and return the pickled file
            impdata = pickle.load(fp)
            return impdata
    except IOError as e:
        print("An error occurred. {}".format(e.args[-1]))
        raise e
    except Exception:
        raise
