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

There are three classes of concepts in :ref:`blok_wms_core`:
:ref:`Goods <goods>`, :ref:`operation` and :ref:`location`.

.. _goods:

Goods and related concepts
~~~~~~~~~~~~~~~~~~~~~~~~~~

Goods represent the physical objects the system is meant to manage.

.. _goods_goods:

Goods
-----
.. versionchanged:: 0.7.0

.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.goods.goods.Goods>` for more
          details, notably for the API of properties.

Records of Goods represent the physicality of the goods, they have a
certain :ref:`Type <goods_type>` and :ref:`flexible properties
<goods_properties>`, whose purpose is to carry useful information
about the Goods, including in particular the variability
among Goods of a given Type (e.g, serial numbers, expiry dates).

The journey of the Goods through the system is represented by their
successive :ref:`Avatars <goods_avatar>`.

Ideally, if the goods change enough in reality that they should be
considered a different object, this should be represented by a new Goods record.
From ``wms-core``'s perspective, there is no definitive answer
whether an object "stays the same" for all the data changes that can
occur about it, not even to speak of reality.
This subjective question is partly left to end
applications, and the Goods record itself serves as the encoding of that.

.. seealso:: :ref:`the original thoughts on Avatars <improvement_avatars>`
             for a discussion predating the current form of the Goods
             record, with examples.

Except for a few predefined cases, Properties form an open ground for
downstream librairies and applications to base some business logic on, as their
values have no meaning for ``wms-core``.
While some :ref:`Operations <operation>` do manipulate
properties, they don't care about their semantics, and do so in a
configurable way, according to the :ref:`goods_type` behaviours.
For a very simple example, see :ref:`op_arrival`, for a less trivial
one, see :ref:`op_unpack`.

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

Goods Types form a hierarchical structure, by means of the ``parent``
field, which gives the end application and its users the means to
group them, and also has a functional impact (see :ref:`goods_behaviours`)

Goods Type have a ``properties`` flexible field. Reading the property
values is done through a dedicated API, which implements defaulting to
the ``parent``, if there's one.

See the section about :ref:`Goods Properties <goods_properties>` for
a full description of Properties, including the interplay between Type
and Goods Properties.


.. _goods_behaviours:

Behaviours
++++++++++

In WMS Base, Goods Types have a ``behaviours`` flexible field that's
used notably to encode the needed information for :ref:`Operations
<operation>`. A typical example of this is the :ref:`op_unpack`
Operation, whose outcomes are fully described as the ``unpack``
behaviour of the Goods Type to be unpacked.

Behaviours are meant to be extended by downstream libraries and
applications. For instance, a library for quality control and
verification of Goods would probably add behaviours to describe the
expectations on each Goods Type.

Behaviours can be any JSON serializable value, and they are themselves
often :class:`dicts <dict>`.

If a given Type has a parent, then its behaviours are merged
recursively with its parent.
This allows to set common parameter values for a whole family of
Types.

For instance, to have different :ref:`Assemblies
<op_assembly>` on some Types, each setting a serial number
:ref:`Property <goods_properties>`
by means of a shared sequence, one may specify the serial :ref:`Property
<goods_properties>` in the ``assembly`` behaviour of some
common ancestor Type.

.. _goods_properties:

Goods Properties
----------------
.. note:: see :class:`the code documentation
          <anyblok_wms_base.core.goods.goods.Goods>` for technical
          details. Notably, properties have to be handled through a
          dedicated API.

Goods Properties allow to store and retrieve information about the
Goods. A given Property can come from the Goods record itself, or be
inherited from its Type: it won't make any difference for applicative code.

While it's necessary to categorize the Goods as we've done with Goods
Types, there is some variability to represent for Goods of the same
Type. After all, they are different concrete objects.

One of the first goal of Goods Properties is to provide the means to
implement the wished traceability features : serial numbers,
production batches of the Goods or of their critical parts…

As usual, WMS Base doesn't impose anything on property values.
Some :ref:`Operations <operation>`, such as :ref:`op_move`, won't
touch properties at all, while some others, such as :ref:`op_unpack`
will manipulate them, according to behaviours on the :ref:`goods_type`.

There's a fine line between what should be encoded as Properties, and
what should be *deduced* from the :ref:`goods_type`. For an example of
this, imagine that the application cares about the weight of the
Goods: in many cases, that depends only on the Goods Type, but in some
other it might actually be different among Goods of the same Type.

In order to accomodate both cases in the same application, and also to
bring uniformity between different characteristics of the Goods, and
therefore how applicative code handles them, Goods Properties are
automatically merged with the Type properties. To follow on the weight
example, the code that takes care of an actual shipping doesn't have
to worry whether a ``weight`` Property is carried by the Goods or if
it has to implement special logic based on the knowledge of some
Types: it's enough to define a ``weight`` on the Types for which it's
fixed, and simply read it from the Goods record in all cases.

The Properties stored on the Goods records form a Model of
their own, which can be enriched to make true Anyblok fields out
of some properties (typically ending up as columns in the database).
This can improve querying capabilities, and make for an easier and
safer programming experience.

.. _goods_avatar:

Goods Avatar
------------
.. versionadded:: 0.6.0

An Avatar represents the idea that some Goods are, should be or were
somewhere in a certain state (``past``, ``present`` or ``future``) in
a certain date and time range.

.. note:: the state is actually totally independent from the times,
          and has more to do with advancement of :ref:`Operations
          <operation>` than the current clock time.

They also bear a reference to the latest :ref:`operation` that
affected them, which is the main entry point to operational history
from the perspective of Goods.

:ref:`Operations <operation>` take primarily Avatars as their inputs,
and spawn new ones, but can also affect the underlying :ref:`Goods
<goods_goods>`.

Here's a concrete example: a planned :ref:`op_move` inputs an Avatar in the
``present`` state, and produces a new one at the wished
:ref:`location` in the ``future`` state. Upon execution, the input's
state is changed to ``past``, while the outcome's state is changed to
``present``. These two Avatars share the same :ref:`Goods
<goods_goods>` record, to account for the fact that the physical goods
haven't changed (in this case, ``wms-core`` can decide of this for itself).

On the other hand, a reservation system needs to work on :ref:`Goods
<goods_goods>`, rather than Avatars, whose instances are
too volatile.

.. seealso:: :ref:`the original thoughts on Avatars
             <improvement_avatars>`, for more on the intended
             purposes, especially with reservation systems in mind,
             and :class:`the code documentation
             <anyblok_wms_base.core.goods.goods.Avatar>` for a
             detailed description of their fields, with full semantics.

.. _location:

Location
~~~~~~~~
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.location.Location>`
          for more details.

Quickly said, the :class:`Location
<anyblok_wms_base.core.location.Location>` Model represents
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
          <anyblok_wms_base.core.operation.base.Operation>`
          for more details.

In Anyblok / WMS Base, what happens to the Goods is represented by the
core concept of Operation. This start with creating Operations, such
as :ref:`op_arrival` and ends with removing Operations, such as
:ref:`op_departure`.

In principle, end applications should act upon Goods through
Operations only.

Operations are polymorphic Models, which means that as Python classes,
they inherit from the base :class:`Operation
<anyblok_wms_base.core.operation.base.Operation>` class,
while they are persisted as two tables in the database: ``wms_operation``
for the common data and a specific one, such as ``wms_operation_arrival``.

In general, Operations take :ref:`Goods Avatars <goods_avatar>` as inputs,
but that can be an empty set for some (creation Operations, such as
:ref:`op_arrival`), and many Operations work just on one :ref:`Avatar
<goods_avatar>`.
Conversely, most Operations have resulting :ref:`Avatars <goods_avatar>`, which
for the time being are called their *outcomes*.

.. note:: That Operations see :ref:`goods_goods` through their
          :ref:`Avatars <goods_avatar>` doesn't imply they have no
          effect on the underlying :ref:`goods_goods`.
          In fact, all :ref:`goods_goods` handling should occur
          through Operations.

Operations are linked together in logical order, forming a `Directed
Acyclic Graph (DAG)
<https://en.wikipedia.org/wiki/Directed_acyclic_graph>`_ that,
together with the links between Operations and Goods, records
all operational history, even for planned operations (we may therefore
jokingly speak of "history of the future").

Thanks to this data structure, Operations can be cancelled, reverted
and more (see :ref:`op_cancel_revert_obliviate`).

.. _op_states:

Lifecycle of operations
-----------------------
Operations start their lifecycle with the :meth:`create()
<anyblok_wms_base.core.operation.base.Operation.create>`
classmethod, which calls ``insert()`` internally. The initial value of
state *must* be passed to :meth:`create()
<anyblok_wms_base.core.operation.base.Operation.create>`

.. warning:: downstream libraries and applications should never call
             ``insert()`` nor update the :attr:`state
             <anyblok_wms_base.core.operation.base.Operation.state>`
             field directly, except for bug reproduction and
             automated testing scenarios.

Here are the detailed semantics of Operation states, and their
interactions with :meth:`create()
<anyblok_wms_base.core.operation.base.Operation.create>`
and :meth:`execute()
<anyblok_wms_base.core.operation.base.Operation.create>`

- ``planned``:
       this means that the operation is considered for the future. Upon
       creation in this state, the system will already create the necessary
       objects (in particular Goods and other Operation records), with
       appropriate states so that the whole system view is consistent for the
       present time as well as future times.

       For this reason, it is necessary to provide a value for the
       :attr:`date and time of execution
       <anyblok_wms_base.core.operation.base.Operation.dt_execution>`,
       even if it is a very wrong estimate.

       Planned Operations can be either :meth:`executed
       <anyblok_wms_base.core.operation.base.Operation.execute>`
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
         more consistent and explicit than having thousands of Goods,
         whose ``present`` Avatars are still
         attached to their original locations, but hard locked to represent
         that they aren't there any more.
       + unpacking or manufacturing operations. Here also, you can reduce
         the usage by representing unpacking or manufacturing areas as
         :ref:`Locations <location>` and moving the Goods to them.
         A planner for deliveries could then simply ignore Goods from
         these locations if their presence there are due to Moves
         instead of Unpacks or Assemblies.

- ``done``:
     The :meth:`execute()
     <anyblok_wms_base.core.operation.base.Operation.execute>`
     method brings a planned Operation in this state, provided the
     needed conditions are met.

     Also, Operations can be created already in their ``done``
     state, usually after the real-life fact happened or
     simultaneously (for a good enough definition of simultaneity),
     provided the needed conditions are met.

     In this case, the consequences are enforced by the :meth:`create()
     <anyblok_wms_base.core.operation.base.Operation.create>`
     method directly.

     .. note:: Typically, creating directly in the ``done`` state is much less
               expensive that creating in the ``planned`` state, followed by a
               call to :meth:`execute()
               <anyblok_wms_base.core.operation.base.Operation.execute>`


.. _op_cancel_revert_obliviate:

History leveraging
------------------

The base Operation model provides a few recursive facilities based on
the operational history and working on it.

Planned operations can be cancelled, this is provided by the
:meth:`cancel()
<anyblok_wms_base.core.operation.base.Operation.cancel>`
method. Canceling an Operation removes it, its outcomes *and all the
dependent operations* from the future history.

Operations that have already been done may be reverted: the
:meth:`plan_revert()
<anyblok_wms_base.core.operation.base.Operation.plan_revert>`
will issue a bunch of new planned Operations to bring back the Goods
as they were before execution (and planning). These new Operations
will take place in real life, and as such, will take time, can go
wrong etc. Some Operations are always reversible, some never are, and
for some, it depends on conditions.

It is possible to completely forget about an Operation, to express
that *it never happened in reality*, despite what the data says.
This is again a recursion over the dependents, and is provided by the
:meth:`obliviate()
<anyblok_wms_base.core.operation.base.Operation.obliviate>` method

More sophisticated history manipulation primitives are being currently
thought of, see :ref:`improvement_operation_superseding`.

.. _op_arrival:

Arrival
-------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.arrival.Arrival>`
          for more details.

Arrivals represent the physical arrival of goods that were not
previously tracked in the application, in some :ref:`location`.

This does not encompass all "creations" of Goods records with Avatars,
but only those that come in real life from the outside. They would
typically be grouped in a concept of Incoming Shipment, but that is
left to applications.

Arrivals initialise the properties of their outcomes. Therefore, they
carry detailed information about the expected goods, and this can be
used in validation scenarios.

Arrivals are irreversible in the sense of :ref:`op_cancel_revert_obliviate`.

.. _op_departure:

Departure
---------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.departure.Departure>`
          for more details.

Departure represent goods physically leaving the system.

Like Arrivals, don't mean to encompass all "removals" of Goods, but only
that leave the facilities represented in the system. They would
typically be grouped in a concept of Outgoing Shipment, but that is
left to applications.

Departures are irreversible in the sense of :ref:`op_cancel_revert_obliviate`.

.. _op_move:

Move
----
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.move.Move>`
          for more details.

Moves represent goods being carried over from one :ref:`location` to
another, with no change of properties. They are always reversible in
the sense of :ref:`op_cancel_revert_obliviate`.

.. _op_unpack:

Unpack
------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.unpack.Unpack>`
          for more details.

Unpacks replace some Goods (packs) with their contents.
The :ref:`Properties <goods_properties>` of the packs can be partially
or fully carried over to the outcomes of the Unpack.

The outcomes of an Unpack and its handling of properties are entirely
specified by the ``unpack`` behaviour of the :ref:`Type <goods_type>`
of the packs, and in the packs properties. They can be entirely fixed
by the behaviour, be entirely dependent on the specific
packs being considered or a bit of both. See the documentation of
:meth:`this method
<anyblok_wms_base.core.operation.unpack.Unpack.get_outcome_specs>`
for a full discussion with concrete use cases.

Unpacks can be reverted by an :ref:`op_assembly` of the proper name
(by default, ``'pack'``), provided that no extra input Goods are to be
consumed by the Assembly.

This means that either

* the wrapping is not been tracked in the system
* the wrapping is tracked, is among the outcomes of the Unpack and can
  be reused.

.. _op_assembly:

Assembly
--------

.. versionadded:: 0.7.0

.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.assembly.Assembly>`
          for more details, and especially :attr:`specification
          <anyblok_wms_base.core.operation.assembly.Assembly.specification>`

Packing and simple manufacturing needs are covered by the Assembly
Operations : several inputs are consumed to produce a single outcome.
More general manufacturing cases fall out of the scope of
the ``wms-core`` Blok.

Assemblies have an outcome :ref:`goods_type`, and a name, so that a given
:ref:`Type <goods_type>` can be assembled in different ways.

As an edge case, Assemblies can have a single input,
how weird that may sound, and are, in fact, the preferred way to alter
some :ref:`Goods <goods_goods>`
record to produce *a new one* with new or different
:ref:`Properties <goods_properties>`,
whether the :ref:`Type <goods_type>` has changed or
not. Use case: one may wish to consider that cutting the edges of a
piece of timber makes it different enough that it must be considered a
new :ref:`Goods <goods_goods>` record.

Assemblies are governed by a flexible :attr:`specification
<anyblok_wms_base.core.operation.assembly.Assembly.specification>`,
which is built from the ``assembly`` behaviour of the
outcome :ref:`Type <goods_type>` and from their optional
:attr:`parameters
<anyblok_wms_base.core.operation.assembly.Assembly.parameters>` field.
This specification includes:

- how to build :ref:`Properties <goods_properties>` on
  the outcome, depending on the :ref:`state <op_states>` been reached.
  For example, it is possible to use a Model.System.Sequence to build
  up a serial number once the Assembly reaches the ``started`` state.
  It's also possible to forward :ref:`Properties <goods_properties>`
  from one or several inputs to the outcome.

- expected inputs, with various required :ref:`Properties
  <goods_properties>` depending on the :ref:`state <op_states>` been
  reached. Variable inputs are also supported (must be
  explicitely turned on).

  These inputs rules are useful for checking
  purposes and to perform selective forwarding of :ref:`Properties
  <goods_properties>` to the outcome. The result been stored in the
  :attr:`match
  <anyblok_wms_base.core.operation.assembly.Assembly.match>` field,
  it can be used as a support for end user display and machine control
  if needed.

- special rules for the contents Property which is used by
  :ref:`op_unpack` to describe the variable part of the :ref:`Goods
  <goods_goods>`.

Assemblies have also programmatic hooks for applications to implement more
complex cases (at the time of this writing, only for the build of outcome
:ref:`Properties <goods_properties>`).

Assemblies can be reverted by :ref:`Unpacks <op_unpack>`, if the outcome
:ref:`Type <goods_type>` supports them. If appropriate, it's possible
to tune the Assembly so that a later
:ref:`op_unpack` reuses the input :ref:`Goods
<goods_goods>`, to underline that they are actually unchanged.
