.. This file is a part of the AnyBlok / WMS Base project
..
..    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
..
.. This Source Code Form is subject to the terms of the Mozilla Public License,
.. v. 2.0. If a copy of the MPL was not distributed with this file,You can
.. obtain one at http://mozilla.org/MPL/2.0/.

Release history
===============

0.7.0 (unreleased)
~~~~~~~~~~~~~~~~~~
* Moved the quantity field of Goods from wms-core to the new
  optional wms-quantity Blok.

  Applications that need this field (mostly for
  goods kept in bulk) will have to install
  wms-quantity. wms-reservation still ignores the quantity field
  completely, i.e, no partial reservation is possible.
* Location tags and recursive stock computations (now a transversal
  method on the Wms model).
* Goods Type hierarchy and merging of behaviours
* Properties on Goods types and defaulting rules from the Goods and
  across the hierarchy
* new Operation: Assembly, for manufacturing processes with exactly
  one outcome

0.6.0
~~~~~
* Published on PyPY
* Implemented Avatars
* Uniformisation of the relationship between Operations and Goods
  (Avatars)
* wms-reservation: initial implementation (with architectural
  notes in documentation)
* some factorisation of concrete Operation methods into the base
  class, leading to much simpler implementations.

0.5
~~~
* First tag, not released to PyPI.
* Operations behave consistently; in particular stock levels at a
  given Location are consistent for all Goods states at any date and time.
* Initial Operations: Arrival, Departure, Move, Unpack, Split, Aggregate
