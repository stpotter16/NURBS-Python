Tessellation
^^^^^^^^^^^^

The ``tessellate`` module provides tessellation algorithms for surfaces. The following example illustrates the usage
scenario of the tessellation algorithms with surfaces.

.. code-block:: python

    from geomdl import NURBS
    from geomdl import tessellate

    # Create a surface instance
    surf = NURBS.Surface()

    # Set tessellation algorithm (you can use another algorithm)
    surf.tessellator = tessellate.TriangularTessellate()

    # Tessellate surface
    surf.tessellate()

NURBS-Python uses :py:class:`.TriangularTessellate` class for surface tessellation by default.

Abstract Tessellation
=====================

.. autoclass:: geomdl.Abstract.Tessellate
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:

Included Tessellation Options
=============================

The following tessellation classes are included in NURBS-Python.

.. automodule:: geomdl.tessellate
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:
