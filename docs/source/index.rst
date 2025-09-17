Quilt
=====

A knit-programming library for modular combination of knitted structures defined by the knitout machine knitting language.

.. image:: https://img.shields.io/github/workflow/status/mhofmann-Khoury/QUILT/CI
   :target: https://github.com/mhofmann-Khoury/QUILT/actions
   :alt: Build Status

.. image:: https://img.shields.io/pypi/v/quilt-knit
   :target: https://pypi.org/project/quilt-knit/
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/quilt-knit
   :target: https://pypi.org/project/quilt-knit/
   :alt: Python Versions

Quick Start
-----------

Installation
~~~~~~~~~~~~

Install from PyPI:

.. code-block:: bash

   pip install quilt-knit

Or install from source:

.. code-block:: bash

   git clone https://github.com/mhofmann-Khoury/QUILT.git
   cd QUILT
   poetry install

Basic Usage
~~~~~~~~~~~

The Quilt library enables you to combine knitted structures (swatches) in two primary ways: **course-wise** (horizontally) and **wale-wise** (vertically).
You can also create complex quilts by combining multiple swatches in grid patterns.

Creating Swatches
^^^^^^^^^^^^^^^^^

First, you'll need to create individual swatches from knitout programs:

.. code-block:: python

   from quilt_knit.swatch.Swatch import Swatch

   # Assuming you have a knitout program loaded
   swatch = Swatch("my_swatch", knitout_program)

Course-wise Merging (Horizontal)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Course-wise merging combines two swatches side by side horizontally:

.. code-block:: python

   from quilt_knit.swatch.course_wise_merging.Course_Wise_Connection import Course_Wise_Connection
   from quilt_knit.swatch.course_wise_merging.Course_Merge_Process import Course_Merge_Process

   # Create two swatches (left and right)
   left_swatch = Swatch("left swatch", left_knitout_program)
   right_swatch = Swatch("right swatch", right_knitout_program)

   # Create a connection between the swatches
   connection = Course_Wise_Connection( left_swatch,  right_swatch,
       first_carriage_pass_on_left=0,      # Optional: specify range
       last_carriage_pass_on_left=None,    # None means all passes
       first_carriage_pass_on_right=0,     # Optional: specify range
       last_carriage_pass_on_right=None    # None means all passes
   )

   # Merge the swatches
   merger = Course_Merge_Process(connection)
   merger.merge_swatches()

   # Compile to DAT file for machine knitting
   merger.compile_to_dat('merged_course_wise')

Wale-wise Merging (Vertical)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Wale-wise merging combines two swatches vertically (bottom to top):

.. code-block:: python

   from quilt_knit.swatch.wale_wise_merging.Wale_Wise_Connection import Wale_Wise_Connection
   from quilt_knit.swatch.wale_wise_merging.Wale_Merge_Process import Wale_Merge_Process

   # Create two swatches (bottom and top)
   bottom_swatch = Swatch("bottom swatch", bottom_knitout_program)
   top_swatch = Swatch("top swatch", top_knitout_program)

   # Create a connection between the swatches
   connection = Wale_Wise_Connection( bottom_swatch, top_swatch,
       bottom_leftmost_needle_position=0,     # Optional: specify needle positions
       bottom_rightmost_needle_position=None, # None means auto-detect
       top_leftmost_needle_position=0,        # Optional: specify needle positions
       top_rightmost_needle_position=None     # None means auto-detect
   )

   # Merge the swatches
   merger = Wale_Merge_Process(connection)
   merger.merge_swatches()

   # Compile to DAT file
   merger.compile_to_dat('merged_wale_wise')

Creating Quilts
^^^^^^^^^^^^^^^

A quilt is a collection of swatches connected in a grid-like pattern to form a whole garment when the swatches are merged together.
Swatches can be connected either course-wise or wale-wise but not both.

Simple Quad Quilt (2x2 Grid)
"""""""""""""""""""""""""""""

A quilt arranged from four swatches in a 2x2 grid pattern:

.. code-block:: python

   from quilt_knit.quilt.Quilt import Quilt

   # Create four swatches
   left_bottom = Swatch("left bottom", left_bottom_program)
   right_bottom = Swatch("right bottom", right_bottom_program)
   left_top = Swatch("left top", left_top_program)
   right_top = Swatch("right top", right_top_program)

   # Create quilt and establish connections
   quilt = Quilt()

   # Connect vertically (wale-wise)
   quilt.connect_swatches_wale_wise(left_bottom, left_top)
   quilt.connect_swatches_wale_wise(right_bottom, right_top)

   # Connect horizontally (course-wise)
   quilt.connect_swatches_course_wise(left_bottom, right_bottom)
   quilt.connect_swatches_course_wise(left_top, right_top)

   # Merge the entire quilt
   merged_swatches = quilt.merge_quilt()

   # Compile the result
   for swatch in merged_swatches:
       swatch.compile_to_dat('quad_quilt_output')

Complex Interlocking Quilt
""""""""""""""""""""""""""

An interlock quilt creates a more complex arrangement with a center piece.
Each connection between swatches covers only part of a swatch, demonstrating all possible partial connections.

.. code-block:: python

   # Create five swatches with different dimensions
   left_bottom = Swatch("left bottom", program1)    # Wide rectangle
   right_bottom = Swatch("right bottom", program2)  # Tall rectangle
   center = Swatch("center", program3)              # Square
   left_top = Swatch("left top", program4)          # Tall rectangle
   right_top = Swatch("right top", program5)        # Wide rectangle

   # Remove cast-on boundaries for seamless connection
   center.remove_cast_on_boundary()
   left_top.remove_cast_on_boundary()
   right_top.remove_cast_on_boundary()

   # Create the quilt
   quilt = Quilt()

   # Complex wale-wise connections with specific needle positioning
   # Connect up to the right edge of the thinner top rectangle.
   quilt.connect_swatches_wale_wise( left_bottom, left_top,  bottom_rightmost_needle_position=left_top.max_needle)
   # Connect the remainder of the bottom to the center swatch.
   quilt.connect_swatches_wale_wise( left_bottom, center, bottom_leftmost_needle_position=left_top.max_needle + 1)
   # Connect the remainder center up to the first half of the top right swatch.
   quilt.connect_swatches_wale_wise( center, right_top, top_rightmost_needle_position=center.max_needle)
   # Connect the remainder of the top swatch to the full width of the bottom swatch.
   quilt.connect_swatches_wale_wise( right_bottom, right_top, top_leftmost_needle_position=center.max_needle + 1)

   # Complex course-wise connections with carriage pass splitting
   right_bottom_split = right_bottom.find_carriage_pass_from_course_passes(left_bottom.constructed_height)
   # Connect the left bottom swatch to half the height of the right bottom swatch.
   quilt.connect_swatches_course_wise( left_bottom, right_bottom, last_carriage_pass_on_right=right_bottom_split)

   left_top_split = left_top.find_carriage_pass_from_course_passes(center.constructed_height)
   quilt.connect_swatches_course_wise( left_top, center, last_carriage_pass_on_left=left_top_split)
   quilt.connect_swatches_course_wise( center, right_bottom, first_carriage_pass_on_right=right_bottom_split + 1)
   quilt.connect_swatches_course_wise(  left_top, right_top, first_carriage_pass_on_left=left_top_split + 1 )

   # Merge and compile
   merged_swatches = quilt.merge_quilt()
   for swatch in merged_swatches:
       swatch.compile_to_dat('interlock_quilt_output')

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation

.. TODO: Add Additional Pages for Usage and Examples as appropriate

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/quilt_knit

Support and Community
---------------------

* **GitHub Repository**: https://github.com/mhofmann-Khoury/QUILT
* **Issue Tracker**: https://github.com/mhofmann-Khoury/QUILT/issues
* **PyPI Package**: https://pypi.org/project/quilt-knit/

License
-------

This project is licensed for non-commercial use- see the `LICENSE <https://github.com/mhofmann-Khoury/QUILT/LICENSE.md>`_ file for details.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
