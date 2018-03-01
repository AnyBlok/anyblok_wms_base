Roadmap
=======

This is not a promise, rather an expression of intent… This will get
updated along the way.

0.6
~~~
* Unification of the relationship between Goods and Operations,
  together with the operational history
* :ref:`Avatars <improvement_avatars>`
* work begins on :ref:`blok_wms_reservation`
* doc: architecture suggestions (reserver, planner)

0.7
~~~
* First release pushed on PyPI and advertised a bit
* Detangling of the :ref:`issues with quantities
  <improvement_no_quantities>` (new blok, new Python distribution or not)
* Decisions about Location and stock levels:
  :ref:`improvement_location_name` and :ref:`improvement_stock_levels`
* new Operations: Pack / Assembly (decision whether it's the same
  thing or not)
* work begins on :ref:`blok_wms_bus` and/or :ref:`blok_wms_rest_api`

0.8
~~~
* (simple cases of) :ref:`improvement_operation_superseding` ?
* official examples (should be in different Python distribution)
* new Operations for inventories: Appearance, Disappearance, Teleportation

0.9
~~~
* First use in production ever (under our direct control)
* Data schema stability (meaning that changes come with appropriate
  migration tools)

1.0.0
~~~~~
* API stability: abiding to `Semantic versioning rules <https://semver.org/>`_
* Some performance tuning
