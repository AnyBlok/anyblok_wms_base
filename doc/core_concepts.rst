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

There are two classes of concepts in :ref:`blok_wms_core`:
:ref:`Physical Objects <physobj>` and :ref:`operation`.

.. note::

   .. versionadded:: 0.8.0

   In Anyblok / WMS, there is no separate concept of location, i.e, a
   Model that would represent where the goods are, were or
   will be. Rather, racks, shelves, carts and even warehouses are just
   special cases of :ref:`physical objects <physobj_model>`.
   See :ref:`location` for more details.

.. _physobj:

Physical Objects and related concepts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _physobj_model:

The PhysObj Model: Physical Objects
-----------------------------------
.. versionchanged:: 0.7.0

.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.physobj.main.PhysObj>` for more
          details, notably for the API of properties.

The ``Wms.PhysObj`` model represents all physical objects that are
meaningful to the system: those being stored and handled (often
thought of as goods), as well as those meant to contain other objects
(even fixed locations such as warehouses).

Records of PhysObj have a certain :ref:`Type <physobj_type>` and
:ref:`flexible properties <physobj_properties>`, whose purpose is to
carry additional information, including in particular the variability
among physical objects of a given Type (e.g, serial numbers, expiry dates).

The journey of the physical objects through the system, notably where
they are and when, is represented
by their successive :ref:`Avatars <physobj_avatar>`.

Ideally, if some object changes enough in reality that it should be
considered to be a different one, this should be represented by a new
PhysObj record.
From ``wms-core``'s perspective, there is no definitive answer
whether a physical object "stays the same" for all the data changes that can
occur about it, not even to speak of reality.
This subjective question is partly left to end
applications, and the PhysObj record itself serves as the encoding of that.

Except for a few predefined cases, Properties form an open ground for
downstream librairies and applications to base some business logic on, as their
values have no meaning for ``wms-core``.
While some :ref:`Operations <operation>` do manipulate
Properties, they usually don't care about their semantics, and they do so in a
configurable way, according to the :ref:`physobj_type` behaviours.
For a very simple example, see :ref:`op_arrival`, for a less trivial
one, see :ref:`op_unpack`.

In ``wms-core``, the PhysObj Model is meant to represent single objects,
and therefore doesn't have a ``quantity`` field that could be used to
represent either a physical measure for goods kept in bulk (tons of
sand, meters of wire) or numbers of physical items that would be
completely identical. These use-cases are
supported in WMS Base by the :ref:`blok_wms_quantity` optional blok.


.. _physobj_type:

Physical Object Types
---------------------

While the end application may have a concept of Product, this is very
hard to define in general without being almost tautological.
In truth, it depends on the concrete needs of the application. While
one would expect some characteriscs of physical items to be the same to say
that they are the same product, another application would consider
different ones.

In WMS Base, we focus on represent the physical handling of the goods,
and to that effect, rather than assuming there is a notion of product
around, we speak of Physical Object Types (Model ``Wms.PhysObj.Type``), a
terminogy that we hope to be neutral
enough not to clash with the terminology in use in other components of the end
application.

That being said, if the end application uses a concept of Product, it's
natural to link it with Physical Object Types, but it won't necessarily be a
one-to-one relationship, especially since Physical Object Types
typically will include information about packaging and handling.

For instance, if the application has a Product for ham, in the WMS,
one should consider whole hams,
5-slice vaccuum packs, crates and pallets of the latter to be all different
Types, related by Operations such as packing,
unpacking. Maybe all of them are also listed as Products in a Sale
Order module, maybe not.

If the application considers service products (such as consulting,
extensions of warranty, etc.) besides products representing physical
goods, those services would simply have no Physical Object Type counterparts.

Physical Object Types form a hierarchical structure, by means of the ``parent``
field, which gives the end application and its users the means to
group them, and also has a functional impact (see :ref:`physobj_behaviours`)

Physical Object Types have a ``properties`` flexible field. Reading
the property values is done through a dedicated API, which implements
defaulting to the ``parent``, if there's one.

.. seealso:: The section about :ref:`Physical Object Properties
             <physobj_properties>` which explains the interplay between Type
             and Object Properties.

.. _physobj_behaviours:

Behaviours
++++++++++

In WMS Base, PhysObj Types have a ``behaviours`` flexible field that's
used notably to encode the needed information for :ref:`Operations
<operation>`. A typical example of this is the :ref:`op_unpack`
Operation, whose outcomes are fully described as the ``unpack``
behaviour of the PhysObj Type to be unpacked.

Behaviours are meant to be extended by downstream libraries and
applications. For instance, a library for quality control and
verification of goods would probably add behaviours to describe the
expectations on each PhysObj Type.

Behaviours can be any JSON serializable value, and they are themselves
often :class:`dicts <dict>`.

If a given Type has a parent, then its behaviours are merged
recursively with its parent.
This allows to set common parameter values for a whole family of
Types.

For instance, to have different :ref:`Assemblies
<op_assembly>` on some Types, each setting a serial number
:ref:`Property <physobj_properties>`
by means of a shared sequence, one may specify the serial :ref:`Property
<physobj_properties>` in the ``assembly`` behaviour of some
common ancestor Type.

.. _physobj_properties:

Properties
----------
.. note:: see :class:`the code documentation
          <anyblok_wms_base.core.physobj.main.PhysObj>` for technical
          details. Notably, Properties have to be handled through a
          dedicated API.

Properties of Physical Objects allow to store and retrieve information
about them. A given Property can come from the Physical Object
Properties record itself or be
inherited from its Type: it won't make any difference for applicative code.

While it's necessary to categorize the Physical Objects as we've done
with Types, there is some variability to represent among those of a
given Type. After all, they are different concrete objects.

One of the first goal of such Properties is to provide the means to
implement the wished traceability features : serial numbers,
production batches of the Physical Objects or of their critical parts…

As usual, WMS Base doesn't impose anything on property values.
Some :ref:`Operations <operation>`, such as :ref:`op_move`, won't
touch properties at all, while some others, such as :ref:`op_unpack`
will manipulate them, according to behaviours on the :ref:`physobj_type`.

There's a fine line between what should be encoded as Properties, and
what should be *deduced* from the :ref:`physobj_type`. For an example of
this, imagine that the application cares about the weight of the
Physical Objects: in many cases, that depends only on the PhysObj
Type, but in some other it might actually be different among objects of
the same Type.

In order to accomodate both cases in the same application, and also to
bring uniformity between different characteristics of the Physical
Objects, and therefore how applicative code handles them, PhysObj
Properties are automatically merged with Type properties. To
follow on the weight
example, the code that takes care of an actual shipping doesn't have
to worry whether a ``weight`` Property is carried by the PhysObj record or if
it has to implement special logic based on the knowledge of some
Types: it's enough to define a ``weight`` on the Types for which it's
fixed, and simply read it with the proper API from the PhysObj
record in all cases.

The Properties stored on the PhysObj records form a Model of
their own: ``Wms.PhysObj.Properties``), which can be enriched to
make true Anyblok fields out of some properties (typically ending up
as columns in the database).
This can improve querying capabilities, and make for an easier and
safer programming experience.

.. _physobj_avatar:

Avatars
-------
.. versionadded:: 0.6.0

.. versionadded:: 0.9.0 *clarification that Avatars are history
                  anchors, hence more than location, state and time bearers*

An Avatar (model
:class:`Wms.PhysObj.Avatar <anyblok_wms_base.core.physobj.main.Avatar>`)
represents a step in the
evolution of some Physical Object through the system. In particular, it
encompasses the idea that the Physical Object is, should be or was
somewhere in a certain state (``past``, ``present`` or ``future``) in
a certain time range.

.. note:: the state is actually totally independent from the times,
          and has more to do with advancement of :ref:`Operations
          <operation>` than the current clock time.

:ref:`Operations <operation>` take Avatars as their *inputs*,
and spawn new ones, that we call their *outcomes*. Even an Operation
that doesn't affect locations nor time ranges has to outcome
new Avatars, disjoint from its inputs.

.. note:: That :ref:`Operations <operation>` work on Avatars doesn't
          prevent them to affect the underlying :ref:`PhysObj
          <physobj_model>` records.

Here's a concrete example: a planned :ref:`op_move` inputs an Avatar in the
``present`` state, and produces a new one at the wished
:ref:`location` in the ``future`` state. Upon execution, the input's
state is changed to ``past``, while the outcome's state is changed to
``present``. These two Avatars share the same :ref:`PhysObj
<physobj_model>` record, to account for the fact that the physical object
hasn't changed (in this case, ``wms-core`` can decide of this for itself).

.. seealso:: :ref:`the original thoughts on Avatars
             <improvement_avatars>`, for more on the intended
             purposes, especially with reservation systems in mind,
             and :class:`the code documentation
             <anyblok_wms_base.core.physobj.main.Avatar>` for a
             detailed description of their fields, with full semantics.

.. _location:

Containers and locations
~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.8.0

Of course, in any stocks and logistics application, the question where
the goods are is a central and crucial one.
In Wms Base, that is fulfilled by saying that :ref:`Physical
Objects <physobj>` can themselves contain other ones.

In other words, what one would think of as a location
is nothing but a special case of Physical Object. We call them
informally *containers*, because "location" without more context may
be understood as something necessarily fixed, or even as coordinates.

In many cases, containers will indeed be fixed
(warehouses, alleys, shelves),
yet moving containers (boats, trucks, trolleys or even carrying boxes)
are also interesting cases.

Technically, containers are characterized by the fact that their
:ref:`Types <physobj_type>` has the ``container`` behaviour. This
behaviour can be itself refined by applications, for instance to
specify what exactly a given container can hold.

Like any other Physical Object, containers can have :ref:`Avatars
<physobj_avatar>`, meaning that they can themselves be inside a bigger
container (at some point in time). Anyblok / Wms Base provides
:meth:`quantity queries <anyblok_wms_base.core.wms.Wms.quantity>`
that are able to recurse through this, optionally at a given point in time.

.. warning:: topmost containers must be created by the
             dedicated :meth:`helper method
             <anyblok_wms_base.core.wms.Wms.create_root_container>`.

             Other containers can be created at their own locations
             by Operations such as :ref:`op_arrival` or
             :ref:`op_apparition`, like any Physical Objects.

The fact that there is no strong distinction between goods and their
containers may seem surprising for some developers, but it has lots of
interesting benefits:

- containers can be moved in a way that the system is able to track
  and take into account, e.g, in the quantity queries, whereas with a
  separate model, we'd probably have a ``parent`` field, of which any change
  of value would impact all times, present, future and even past.
- containers are automatically typed and have properties, which can be
  used to encode various functional aspects.
- containers can be received (after all, warehouse hardware is also
  purchased and delivered), shipped as a whole, broken, disappear, etc.

.. seealso:: :ref:`the original thoughts that led to the disppearance
             of the Location model <improvement_goods_location>`.

.. seealso:: :ref:`avatars_containers_contents`

.. _operation:

Operation
~~~~~~~~~
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.base.Operation>`
          for more details.

In Anyblok / WMS Base, what happens to the Physical Objects is
represented by the core concept of Operation. This start with creating
Operations, such
as :ref:`op_arrival` and ends with removing Operations, such as
:ref:`op_departure`.

In principle, end applications should act upon Physical Objects through
Operations only.

Operations are polymorphic Models, which means that as Python classes,
they inherit from the base :class:`Operation
<anyblok_wms_base.core.operation.base.Operation>` class,
while they are persisted as two tables in the database: ``wms_operation``
for the common data and a specific one, such as ``wms_operation_arrival``.

In general, Operations take :ref:`Avatars <physobj_avatar>` as *inputs*,
but that can be an empty set for some (creation Operations, such as
:ref:`op_arrival`), and many Operations work just on one :ref:`Avatar
<physobj_avatar>`.
Conversely, most Operations have resulting :ref:`Avatars
<physobj_avatar>`, which we call their *outcomes*.

.. note:: That Operations see Physical Objects through their
          :ref:`Avatars <physobj_avatar>` doesn't imply they have no
          effect on the underlying :ref:`PhysObj <physobj_model>`
          records, quite the contrary.
          In fact, most of :ref:`PhysObj <physobj_model>` modifications
          should occur through Operations.

Operations are linked together in logical order, forming a `Directed
Acyclic Graph (DAG)
<https://en.wikipedia.org/wiki/Directed_acyclic_graph>`_ that,
together with the links between Operations and Avatars, records
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
       objects (in particular, Avatars and other Operation records), with
       appropriate states so that the whole system view is consistent for the
       present time as well as future times.

       Planned Operations can be either :meth:`executed
       <anyblok_wms_base.core.operation.base.Operation.execute>`
       or :ref:`cancelled <op_cancel_revert_obliviate>`.

- ``started``:
       .. note:: this value is already defined but it is for now
                 totally ignored in the implementation. This part can be
                 therefore considered to be design notes.

       In reality, operations are never atomic, and often cannot be
       cancelled any more once started.

       In this state, outcomes of the operation are not already
       there, but the operation cannot be cancelled. The Physical
       Objects and their Avatars being acted upon should be locked to
       represent that they are actually not available any more.

       It would be probably too expensive to systematically use this state,
       therefore, it should be used only if the real life operation takes
       a really long time to conclude.

       Examples:

       + longer distance moves. If this is really frequent, you can also
         consider splitting them in two steps, e.g, moving to a location
         representing some kind of vehicle (even if it is a cart),
         then moving from the vehicle to the final location. This can be
         more consistent and explicit than having thousands of
         Physical Objects, whose ``present`` Avatars are still
         attached to their original locations, but hard locked to represent
         that they aren't there any more.
       + unpacking or manufacturing operations. Here also, you can reduce
         the usage by representing unpacking or manufacturing areas as
         :ref:`locations <location>` and moving the relevant Physical
         Objects to them.
         A reserver for deliveries could then simply ignore what's
         inside these locations if their presence there are due to Moves
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

     .. note:: Typically, creating directly in the ``done`` state is less
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
will issue a bunch of new planned Operations to bring back the
Physical Objects and their Avatars
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

Arrivals represent the physical arrival of something that wasn't
previously tracked in the application, in some :ref:`location`.

This does not encompass all "creations" of Physical Objects with Avatars,
but only those that come in real life from the outside. They would
typically be grouped in a concept of Incoming Shipment, but that is
left to applications.

Arrivals initialise the properties of their outcomes. Therefore, they
carry detailed information about the expected objects, and this can be
used in validation scenarios.

Arrivals are irreversible in the sense of :ref:`op_cancel_revert_obliviate`.

.. _op_departure:

Departure
---------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.departure.Departure>`
          for more details.

Departure represent Physical Objects leaving the system.

Like Arrivals, don't mean to encompass all "removals" of Physical
Objects, but only those that leave the facilities represented in the
system.

They would
typically be grouped in a concept of Outgoing Shipment, but that is
left to applications.

Departures are irreversible in the sense of :ref:`op_cancel_revert_obliviate`.

.. _op_apparition:

Apparition
----------
.. versionadded:: 0.8.0

.. note:: see :class:`the code documentation
          <anyblok_wms_base.core.operation.apparition.Apparition>`
          for more details.

Apparitions are similar to Arrivals in that they create previously
untracked :ref:`Physical Objects <physobj_model>`, but they are meant
to be used in
inventory assessments: they represent the fact that some
:ref:`Physical Objects <physobj_model>` have been discovered, with no
known explanation.

In concrete applications, Apparitions would typically be optionally
tied to some higher level Inventory Model that would be backing some user
interface while grouping and maybe creating them. Anyblok / Wms Base 0.8
does not provide such Inventories, but there are :ref:`plans
to include them in a new optional Blok <improvement_inventory>`.

Apparitions are always in the ``done`` :ref:`state <op_states>`, as
other states don't make sense in their case. In other words, only
direct creations in the ``done`` :ref:`state <op_states>` are allowed.

Apparitions are irreversible in the sense of :ref:`op_cancel_revert_obliviate`.

.. _op_disparition:

Disparition
-----------
.. versionadded:: 0.8.0

.. note:: see :class:`the code documentation
          <anyblok_wms_base.core.operation.disparition.Disparition>`
          for more details.

Disparitions are inventory Operations that record that the goods are
missing, for no known reason. In other words, they are to
:ref:`Departures <op_departure>` what :ref:`Apparitions
<op_apparition>` are to :ref:`Arrivals <op_arrival>`:

- they cannot be planned nor started; only direct creations in the
  ``done`` :ref:`state <op_states>` are allowed.
- they are irreversible.
- they should be tied in applications to higher level Inventory objects.

Same as for :ref:`op_departure`, the effect of a Disparition is not
to erase the :ref:`physobj_model`,
but only to put the given :ref:`Avatar <physobj_avatar>` in the ``past`` state.

.. _op_move:

Move
----
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.move.Move>`
          for more details.

Moves represent goods being carried over from one :ref:`place <location>` to
another, with no other change. They are always reversible in
the sense of :ref:`op_cancel_revert_obliviate`.

.. _op_teleportation:

Teleportation
-------------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.teleportation.Teleportation>`
          for more details.

Teleportations are inventory Operations that record that the goods are
not missing, but changed places, for no known reason.
In other words, they are to
:ref:`Moves <op_move>` what :ref:`Apparitions
<op_apparition>` are to :ref:`Arrivals <op_arrival>`:

- they cannot be planned nor started; only direct creations in the
  ``done`` :ref:`state <op_states>` are allowed.
- they are irreversible.
- they should be tied in applications to higher level Inventory objects.

Apart from that, their have the same effect as :ref:`Moves <op_move>`.


.. _op_unpack:

Unpack
------
.. note:: This is an overview, see :class:`the code documentation
          <anyblok_wms_base.core.operation.unpack.Unpack>`
          for more details.

Unpacks replace some Physical Objects (let's call them "packs") with
their contents.
The :ref:`Properties <physobj_properties>` of the packs can be partially
or fully carried over to the outcomes of the Unpack.

The outcomes of an Unpack and its handling of properties are entirely
specified by the ``unpack`` behaviour of the :ref:`Type <physobj_type>`
of the packs, and in the packs properties. They can be entirely fixed
by the behaviour, be entirely dependent on the specific
packs being considered or a bit of both. See the documentation of
:meth:`this method
<anyblok_wms_base.core.operation.unpack.Unpack.get_outcome_specs>`
for a full discussion with concrete use cases.

Unpacks can be reverted by an :ref:`op_assembly` of the proper name
(by default, ``'pack'``), provided that no extra input Physical Objects
are to be consumed by the Assembly, in other words that either:

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

Assemblies have an outcome :ref:`Type <physobj_type>`, and a name, so
that a given :ref:`Type <physobj_type>` can be assembled in different ways.

As an edge case, Assemblies can have a single input,
how weird that may sound, and are, in fact, the preferred way to alter
some :ref:`PhysObj <physobj_model>`
record to produce *a new one* with new or different
:ref:`Properties <physobj_properties>`,
whether the :ref:`Type <physobj_type>` has changed or
not. Use case: one may wish to consider that cutting the edges of a
piece of timber makes it different enough that it must be considered a
new :ref:`PhysObj <physobj_model>` record.

Assemblies are governed by a flexible :attr:`specification
<anyblok_wms_base.core.operation.assembly.Assembly.specification>`,
which is built from the ``assembly`` behaviour of the
outcome :ref:`Type <physobj_type>` and from their optional
:attr:`parameters
<anyblok_wms_base.core.operation.assembly.Assembly.parameters>` field.
This specification includes:

- how to build :ref:`Properties <physobj_properties>` on
  the outcome, depending on the :ref:`state <op_states>` been reached.
  For example, it is possible to use a Model.System.Sequence to build
  up a serial number once the Assembly reaches the ``started`` state.
  It's also possible to forward :ref:`Properties <physobj_properties>`
  from one or several inputs to the outcome.

- expected inputs, with various required :ref:`Properties
  <physobj_properties>` depending on the :ref:`state <op_states>` been
  reached. Variable inputs are also supported (must be
  explicitely turned on).

  These inputs rules are useful for checking
  purposes and to perform selective forwarding of :ref:`Properties
  <physobj_properties>` to the outcome. The result been stored in the
  :attr:`match
  <anyblok_wms_base.core.operation.assembly.Assembly.match>` field,
  it can be used as a support for end user display and machine control
  if needed.

- special rules for the contents Property which is used by
  :ref:`op_unpack` to describe the variable part of its outcomes.

Assemblies have also programmatic hooks for applications to implement more
complex cases (at the time of this writing, only for the build of outcome
:ref:`Properties <physobj_properties>`).

Assemblies can be reverted by :ref:`Unpacks <op_unpack>`, if the outcome
:ref:`Type <physobj_type>` supports them. If appropriate, it's possible
to tune the Assembly so that a later
:ref:`op_unpack` reuses the input :ref:`PhysObj
<physobj_model>` records, to underline that they are actually unchanged.
