CloudCity
=========

This is a layer on top of cloudformation to assist with bringing together
multiple cloudformation stacks that depend on each other.

It's similar to the ideas in `cumulous <https://github.com/cotdsa/cumulus>`_.

Note:: This is far from working!! And time is a commodity I don't have much of :(

Installation
------------

Use pip!:

.. code-block:: bash

    pip install cloudcity

Or if you're developing it:

.. code-block:: bash

    pip install -e .
    pip install -e ".[tests]"

Tests
-----

Run the helpful script:

.. code-block:: bash

    ./test.sh

