Installation
============


Requirements
------------

* Python 3.11 or higher
* pip or Poetry package manager

Install from PyPI
-----------------

The easiest way to install the package is from PyPI:

.. code-block:: bash

   pip install quilt-knit

Or using Poetry:

.. code-block:: bash

   poetry add quilt-knit

Install from Source
-------------------

To install the latest development version from source:

.. code-block:: bash

   git clone https://github.com/mhofmann-Khoury/QUILT.git
   cd your-repo
   pip install -e .

Or with Poetry:

.. code-block:: bash

   git clone https://github.com/mhofmann-Khoury/QUILT.git
   cd your-repo
   poetry install

Development Installation
------------------------

For development and contributing:

.. code-block:: bash

   git clone https://github.com/mhofmann-Khoury/QUILT.git
   cd your-repo
   poetry install --with dev,docs

This installs the package with all development dependencies including testing and documentation tools.
