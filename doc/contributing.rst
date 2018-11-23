.. This file is a part of the AnyBlok / WMS Base project
..
..    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
..
.. This Source Code Form is subject to the terms of the Mozilla Public License,
.. v. 2.0. If a copy of the MPL was not distributed with this file,You can
.. obtain one at http://mozilla.org/MPL/2.0/.

.. _contributing:

Contribution guidelines
=======================

Version control and workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The project is available on GitHub at
https://github.com/AnyBlok/anyblok_wms_base.

As far as workflow is concerned, we're using standard
GitHub pull requests and issues, and that's it!

If you're submitting a bugfix, we'd appreciate if you could also fill
in an issue, because it's more visible to other users.

If you want to know if we'd be interested in some improvements, just
fill an issue.

Technical policy
~~~~~~~~~~~~~~~~

Licensing and credits
---------------------

Please add the standard MPL 2.0 header on any new files you'd
contribute.

Don't forget to add yourself to the :doc:`credits` page! (unless you
don't want to).

Code style
----------

We're using `flake8 <https://pypi.org/project/flake8/>`_ with its
default settings. This is enforced by the Travis CI system that runs
on pull requests.

To check by yourself::

  pip install flake8
  flake8 anyblok_wms_base

We also recommend using the flake8 Git pre-commit hook.


Tests coverage
--------------

Global coverage
+++++++++++++++
The global tests coverage has been at 100% for almost all the history
of the project, it's checked by the continuous integration, and it
must stay this way.

Don't worry, we'll help you getting your pull request to that level.

Of course, It doesn't prove that all
important situations are really tested, but we see it the other way
around: a line uncovered is certainly not tested! In any case, full
tests coverage allows us to very quickly pinpoint problems during
refactorings.

self-coverage of subpackages
++++++++++++++++++++++++++++

The self-coverage of some Python packages of this project have also
been at 100% for a fair amount of time, and it's been really great for
refactorings.

This means that :ref:`running the
tests of some Blok or subpackage <contributing_test_partial>` gives
100% coverage of that package.

Ideally, we'd like it to stay that way, but it's not readily enforced
by the current continuous integration systems.

This is currently true for

* all provided :doc:`Bloks <components>`
* main subpackages of the ``wms-core`` and ``wms-quantity`` Bloks:

  + :ref:`pkg_physobj`
  + :ref:`pkg_operation`
  + :ref:`pkg_quantity_operation`

.. note:: There's a special case for the forthcoming ``wms-inventory``
          Blok. Since it has functionality that depends on whether
          ``wms-reservation`` is installed or not, full coverage can only be
          achieved by runnig the tests twice, one without ``wms-reservation``
          and one with it. Of course :ref:`run_all_tests.py
          <contributing_run_all_tests>` does precisely this.

          We expect more similar cases to appear in the future.


Launching the tests
~~~~~~~~~~~~~~~~~~~

Common requirements
-------------------

* make sure you have a local PostgreSQL server running, with the standard
  command-line interface (``psql``), accepting requests on UNIX
  Socket Domain (this is the default in most installations)
* make sure that your current system user has a corresponding
  PostgreSQL role under peer authentication. This is typically ensured
  by something like::

    sudo -u postgres createuser -dSR `whoami`

* you'll need a virtual environment::

    python3 -m venv /path/to/virtualenv
    source /path/to/virtualenv/bin/activate

* it's necessary to install AnyBlok / Wms Base in the virtualenv, so
  that its Bloks are registered. From your Git clone, just do::

    pip install -e .

.. _contributing_run_all_tests:

Launching all the tests
-----------------------
To run all the tests (it takes about one or two minutes depending on
your development rig) from your Git clone::

  ./run_all_tests.py

The tests run on a dedicated database that is created afresh each time.

.. _contributing_test_partial:

Launching only tests for a Blok, or a Blok sub package
------------------------------------------------------

Just do, e.g::

  ./test_partial.py wms-core

or for just a subpackage::

  ./test_partial.py wms-core --subpkg physobj

for more options::

    ./test_partial.py --help

The script ends with a coverage report and instructions on how to
rerun more precise tests::

  $ ./test_partial.py wms-core --subpkg physobj
  (...)
  Name                                        Stmts   Miss  Cover
  ---------------------------------------------------------------
  anyblok_wms_base/core/physobj/__init__.py       7      0   100%
  anyblok_wms_base/core/physobj/main.py         241      0   100%
  anyblok_wms_base/core/physobj/type.py          99      0   100%
  ---------------------------------------------------------------
  TOTAL                                         347      0   100%
  ----------------------------------------------------------------------
  Ran 38 tests in 3.200s

  OK

  For HTML coverage report, open file:///tmp/COVER-anyblok_wms_base.core.physobj/index.html

  To run again with different options, maybe incompatible with the Nose plugin, or a precise test, do something based on:
      anyblok_nose --db-driver-name postgresql --db-name test_awb_anyblok_wms_base.core.physobj -- anyblok_wms_base.core.physobj

