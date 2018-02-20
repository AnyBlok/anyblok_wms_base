.. This file is a part of the AnyBlok / WMS Base project
..
..    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
..
.. This Source Code Form is subject to the terms of the Mozilla Public License,
.. v. 2.0. If a copy of the MPL was not distributed with this file,You can
.. obtain one at http://mozilla.org/MPL/2.0/.

.. _core_concepts:

Core concepts
=============

All of these are implemented as Anyblok Models and are provided by
:ref:`blok_wms_core`.

Goods, their Types and Properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Goods represent the physical objects the system is meant to manage.

.. _goods_goods:

Goods
-----

.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.goods.Goods>` for more details.

Records of Goods have a certain :ref:`Type <goods_type>`, a
:ref:`Location <location>`, and can be in three states: ``past``,
``present`` and ``future``.

They have :ref:`flexible properties <goods_properties>`, which are meant
to represent the variability among Goods of given Type (e.g, serial
numbers, expiry dates). Downstream libraries and applications can
implement their business logic on them safely, as their values have no
meaning for ``wms-core``. How :ref:`operations <operation>` handle
properties is configurable if needed.

For the time being, records of goods also have quantities that
represent either a physical measure, or a number of physical items that are
completely identical (including properties), but see
:ref:`improvement_no_quantities`.

.. _goods_type:

Goods Type
-----------

While the end application may have a concept of Product, this is very
hard to define in general without being almost tautological.
In truth, it depends on the concrete needs of the application. While
one would expect some characteristocs of physical items to be the same to say
that they are the same product, another one would consider different ones.

In WMS Base, we focus on represent the physical handling of the goods,
and to that effect, rather than assuming there is a notion of product
around, we speak of Goods Types, and that's actually why we adopted
the Goods terminology : we felt it to be more neutral and less prone
to clash with the terminology in use in other components of the end
application.

That being said, if the end application uses a concept of Product, it's
natural to link it with Goods Types, but it won't necessarily be a
one-to-one relationship, especially since Goods Types typically will include
information about packaging.

For instance, if the application has a Product for ham, in the WMS,
one should consider whole hams,
5-slice vaccuum packs, crates and pallets of the latter to be all different
Goods Types, related by Operations such as packing,
unpacking. Maybe all of them are also listed as Products in a Sale
Order module, maybe not.

If the application considers service products (such as consulting,
extensions of warranty, etc.) besides products representing physical
goods, those services would simply have no Goods Type counterparts.

In WMS Base, Goods Types have a ``behaviours`` flexible field that's
used notably to encode the needed information for :ref:`Operations
<operation>`. A typical example of this is the :ref:`op_unpack`
Operation, whose outcomes are fully described as the ``unpack``
behaviour of the Goods Type to be unpacked.

Behaviours are meant to be extended by downstream libraries and
applications. For instance, a library for quality control and
verification of Goods would probably add behaviours to describe the
expectations on each Goods Type.

.. _goods_properties:

Goods Properties
----------------
.. note:: see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.goods.Goods>` for technical
          details. Notably, properties have to be handled through a
          dedicated API.

While it's necessary to categorize the Goods as we've done with Goods
Types, there is some variability to represent for Goods of the same
Type. After all, they are different concrete objects.

One of the first goal of Goods Properties is to provide the means to
implement the wished traceability features : serial numbers,
production batches of the Goods or of their critical parts…

As usual, WMS Base doesn't impose anything on property values.
Some :ref:`Operations <operation>`, such as :ref:`op_move`, won't
touch properties at all, while some other, such as :ref:`op_unpack`
will manipulate them, according to behaviours on the :ref:`goods_type`.

There's a fine line between what should be encoded as Properties, and
what should be deduced from the :ref:`goods_type`. For an example of
this, imagine that the application cares about the weight of the
Goods: in many cases, that depends only on the Goods Type, but in some
other it might actually be different among Goods of the same Type.

The Properties model can be enriched to make true Anyblok fields out
of some properties (typically ending up as columns in the database),
which can improve querying capabilities, and make for an easier and
safer programming experience.

.. _location:

Location
~~~~~~~~
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.location.Location>`
          for more details.

TODO

.. note:: see :ref:`improvement_location_name`


.. _operation:

Operation
~~~~~~~~~
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.base.Operation>`
          for more details.

TODO

create and execute
------------------

TODO

.. _op_cancel_revert_obliviate:

cancel, revert and obliviate
----------------------------
TODO

.. _op_arrival:

Arrival
-------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.arrival.Arrival>`
          for more details.

TODO

.. _op_departure:

Departure
---------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.departure.Departure>`
          for more details.

TODO

.. _op_move:

Move
----
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.move.Move>`
          for more details.

TODO

.. _op_unpack:

Unpack
------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.unpack.Unpack>`
          for more details.

TODO

.. _op_split_aggregate:

Split and Aggregate
-------------------
.. note:: This is an overview, see the code documentation for
          :class:`Split
          <anyblok_wms_base.bloks.wms_core.operation.split.Split>` and
          :class:`Aggregate
          <anyblok_wms_base.bloks.wms_core.operation.aggregate.Aggregate>`
          for more details.

TODO

.. note:: see :ref:`improvement_no_quantities`

