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

Quickly said, the :class:`Location
<anyblok_wms_base.bloks.wms_core.location.Location>` Model represents
where the Goods are. It provides methods to sum up Goods quantities.

Locations form a hierarchical structure (a forest, to be pedantic):
each location has a single optional "parent".

.. note:: we may still decide to get rid of the hiearchical
          structure, to replace it with a simpler and more efficient one.

``wms-core`` does not provide coordinates for Locations, therefore
they can be fixed (warehouses, alleys, shelves) or moving (boats,
trucks, trolleys or even carrying boxes), or even represent some
logical grouping (see also :ref:`improvement_location_name`).

.. _operation:

Operation
~~~~~~~~~
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.base.Operation>`
          for more details.

In Anyblok / WMS Base, what happens to the Goods is represented by the
core concept of Operation. This start with creating Operations, such
as :ref:`op_arrival` and ends with removing Operations, such as
:ref:`op_departure`.

In principle, end applications should act upon Goods through
Operations only.

Operations are polymorphic Models, which means that as Python classes,
they inherit from the base :class:`Operation
<anyblok_wms_base.bloks.wms_core.operation.base.Operation>` class,
while they are persisted as two tables in the database: ``wms_operation``
for the common data and a specific one, such as ``wms_operation_arrival``.

Most Operations take Goods as inputs, but some don't (creation
Operations). Conversely, most Operations have resulting Goods, which
for the time being are called « outcomes » in the code.

Operations are linked together in logical order, forming a `Directed
Acyclic Graph (DAG)
<https://en.wikipedia.org/wiki/Directed_acyclic_graph>`_ that,
together with the links between Operations and Goods, record
all operational history, even for planned operations (we may therefore
jokingly speak of "history of the future").

Thanks to this data structure, Operations can be cancelled, reverted
and more (see :ref:`op_cancel_revert_obliviate`.

.. _op_states:

Lifecycle of operations
-----------------------
Operations start their lifecycle with the :meth:`create()
<anyblok_wms_base.bloks.wms_core.operation.base.Operation.create>`
classmethod, which calls ``insert()`` internally. The initial value of
state *must* be passed to :meth:`create()
<anyblok_wms_base.bloks.wms_core.operation.base.Operation.create>`

.. warning:: downstream libraries and applications should never call
             ``insert()`` nor update the :attr:`state
             <anyblok_wms_base.bloks.wms_core.operation.base.Operation.state>`
             field directly, except for bug reproduction and
             automated testing scenarios.

Here are the detailed semantics of Operation states, and their
interactions with :meth:`create()
<anyblok_wms_base.bloks.wms_core.operation.base.Operation.create>`
and :meth:`execute()
<anyblok_wms_base.bloks.wms_core.operation.base.Operation.create>`

- ``planned``:
       this means that the operation is considered for the future. Upon
       creation in this state, the system will already create the necessary
       objects (in particular Goods and other Operation records), with
       appropriate states so that the whole system view is consistent for the
       present time as well as future times.

       Planned Operations can be either :meth:`executed
       <anyblok_wms_base.bloks.wms_core.operation.base.Operation.execute>`
       or :ref:`cancelled <op_cancel_revert_obliviate>`.

- ``started``:
       .. note:: this value is already defined but it is for now
                 totally ignored in the implementation. This part is
                 therefore made only of design notes.

       In reality, operations are never atomic, and often cannot be
       cancelled any more once started.

       In this state, outcomes of the operation are not already
       there, but the operation cannot be cancelled. The Goods being the
       object of the operation should be completely locked to represent that
       they are actually not available any more.

       It would be probably too expensive to systematically use this state,
       therefore, it should be used only if the real life operation takes
       a really long time to conclude.

       Examples:

       + longer distance moves. If this is really frequent, you can also
         consider splitting them in two steps, e.g, moving to a location
         representing some kind of vehicle (even if it is a cart),
         then moving from the vehicle to the final location. This can be
         more consistent and explicit than having thousands Goods, still
         attached to their original locations, but hard lock to represent
         that they aren't there any more.
       + unpacking or manufacturing operations. Here also, you can reduce
         the usage by representing unpacking or manufacturing areas as
         :ref:`Locations <location>` and moving the Goods to them.
         A planner for deliveries could then simply ignore Goods from
         these locations if their presence there are due to Moves
         instead of Unpacks or Assemblies.

- ``done``:
     The :meth:`execute()
     <anyblok_wms_base.bloks.wms_core.operation.base.Operation.execute>`
     method brings a planned Operation in this state, provided the
     needed conditions are met.

     Also, Operations can be created already in their ``done``
     state, usually after the real-life fact happened or
     simultaneously (for a good enough definition of simultaneity),
     provided the needed conditions are met.

     In this case, the consequences are enforced by the :meth:`create()
     <anyblok_wms_base.bloks.wms_core.operation.base.Operation.create>`
     method directly.

     .. note:: Typically, creating directly in the ``done`` state is much less
               expensive that creating in the ``planned`` state, followed by a
               call to :meth:`execute()
               <anyblok_wms_base.bloks.wms_core.operation.base.Operation.execute>`


.. _op_cancel_revert_obliviate:

History leveraging
------------------

The base Operation model provides a few recursive facilities based on
the operational history and working on it.

Planned operations can be cancelled, this is provided by the
:meth:`cancel()
<anyblok_wms_base.bloks.wms_core.operation.base.Operation.cancel>`
method. Canceling an Operation removes it, its outcomes *and all the
dependent operations* from the future history.

Operations that have already been done may be reverted: the
:meth:`plan_revert()
<anyblok_wms_base.bloks.wms_core.operation.base.Operation.plan_revert>`
will issue a bunch of new planned Operations to bring back the Goods
as they were before execution (and planning). These new Operations
will take place in real life, and as such, will take time, can go
wrong etc. Some Operations are always reversible, some never are, and
for some, it depends on conditions.

It is possible to completely forget about an Operation, to express
that *it never happened in reality*, despite what the data says.
This is again a recursion over the dependents, and is provided by the
:meth:`obliviate()
<anyblok_wms_base.bloks.wms_core.operation.base.Operation.obliviate>` method

More sophisticated history manipulation primitives are being currently
thought of, see :ref:`improvement_operation_superseding`.

.. _op_arrival:

Arrival
-------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.arrival.Arrival>`
          for more details.

Arrivals represent the physical arrival of Goods that were not
previously tracked in the application in some :ref:`location`.

This does not encompass all "creations" of Goods, but only those that
come in real life from the outside. They would typically be grouped in
a concept of Incoming Shipment, but that is left to applications.

Arrivals initialise the properties of their outcomes. Therefore, they
carry detailed information about the expected goods, and this can be
used in validation scenarios.

Arrivals are irreversible.

.. _op_departure:

Departure
---------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.departure.Departure>`
          for more details.

Departure represent Goods physically leaving the system.

Like Arrivals, don't mean to encompass all "removals" of Goods, but only
that leave the facilities represented in the system. They would
typically be grouped in a concept of Outgoing Shipment, but that is
left to applications.

Departures are irreversible.

.. _op_move:

Move
----
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.move.Move>`
          for more details.

Moves represent Goods being carried over from one :ref:`location` to
another, with no change of properties. They are always reversible.

.. _op_unpack:

Unpack
------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.bloks.wms_core.operation.unpack.Unpack>`
          for more details.

Unpacks replace some Goods (packs) with their contents. They are entirely
specified as behaviours Type of the packs, and in their properties.
The properties of the packs can be partially or fully carried over to
the outcomes of the Unpack.

The outcomes can be entirely fixed, entirely dependent on the specific
packs being considered or a bit of both. See the documentation of
:meth:`this method
<anyblok_wms_base.bloks.wms_core.operation.unpack.Unpack.get_outcome_specs>`
for a full discussion.

Since Unpacks are destructive operations, they are currently irreversible,
but will be conditionally reversible once we have the converse Pack
(or the more gener Assembly) Operation, maybe consuming some other
Goods for packaging (cardboard, pallet wood). Again, this will be
defined in behaviours.

.. _op_split_aggregate:

Split and Aggregate
-------------------
.. note:: This is an overview, see the code documentation for
          :class:`Split
          <anyblok_wms_base.bloks.wms_core.operation.split.Split>` and
          :class:`Aggregate
          <anyblok_wms_base.bloks.wms_core.operation.aggregate.Aggregate>`
          for more details.

A Split replaces one record of Goods with two identical ones, keeping
the overall total quantity.

According to behaviours on the Goods Type, they are *formal* (have no
counterpart in reality) or *physical*. In the latter case, they can be
reversible or not, again according to behaviours.

Aggregates are the converse of Splits.

.. note:: see :ref:`improvement_no_quantities`

