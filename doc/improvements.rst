.. This file is a part of the AnyBlok / WMS Base project
..
..    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
..
.. This Source Code Form is subject to the terms of the Mozilla Public License,
.. v. 2.0. If a copy of the MPL was not distributed with this file,You can
.. obtain one at http://mozilla.org/MPL/2.0/.

New features and design improvements
====================================

This page collects several stated problems and candidate solutions.
This is a place for discussion and reflection :ref:`that will probably take
a different form in the future <improvement_improvements>`.

The technical detail should not be the main focus in this page,
although proposed solutions have to take them into account.

Current ideas
~~~~~~~~~~~~~

.. _improvement_inventory:

Inventory support
-----------------

Currently, the core provides special Operations, such as
:ref:`op_apparition` to represent the effect of inventory processes,
yet AnyBlok / Wms Base doesn't include a representation of
inventories, that should in turn be the major source of these
Operations.

Depending on the needs, there are several possible ways to proceed
with inventories, but they usually amount to record what is actually present
in the relevant locations, compare that with the database and issue
corrections.

We should provide some support for that process, but it would be in a
new optional Blok, in order not to block applications that would need
to proceed in a very different way.

.. _improvement_indeterminate_avatars:

Allow Avatars with indeterminate time range
-------------------------------------------

It's been a design requirement from the beginning that Avatars of a
given physical object don't overlap, but it's hard to enforce and
gives rise to Avatars whose lifespan is too fictive, meaning that it's not
a prediction made by applicative code or the end user, but just
minimal garbage so that the Avatars don't overlap. It goes as far as
having many Avatars with a zero length lifespan.

An issue not adressed yet is the one of execution of chains of planned
Operations (`#8 on Github
<https://github.com/AnyBlok/anyblok_wms_base/issues/8>`_).
Namely, once the first Operation gets executed, it sets
the real dates and times on its outcomes. No effort is
currently made to adjust downstream Avatars to avoid their overlaping
with the ones now being present, and that happens in case the actual
time of execution is later than planned (almost always the case
with the default value of the planned time of execution).
It could be solved by propagating any positive
shift, but that defeats one of our core goals: that execution of
planned Operations should be really fast.

It would be better to use ``None`` as a marker for totally unkwnown
times of execution and datetimes of ``future`` Avatars. Besides to be
more understandable than having weird values in the database, it would
lift the burden of propagating a shift in the most common use case
where there was simply no planned date of execution (we should enforce that
any downstream Avatar of an indeterminate one should be, too),
but this gives rise to a new set of problems:

- semantically, ``dt_until == None`` currently means the end of times.
  If we use instead to to just say
  that we don't know, we need something else to mark that an
  Avatar is terminal in the current state of planification. Maybe
  that it's not the input of any Operation is good enough, maybe we'd
  have to mark it explicitely with a boolean for efficiency reasons,
  maybe we'd end up chaining Avatars directly.
- in ``future`` quantity queries, we'd need to avoid counting Avatars of a
  given physical object twice, and we'd prefer the results to stay additive
  with respect to the hierarchy of location/containers, ie, if location
  A contains exactly two sublocations B and C::

     quantity(location=A, …) = quantity(location=B, …) + quantity(location=C…)

  Otherwise, it could lead to subtle bugs in applicative code that
  would implicitely take that additivity for granted, or mere
  confusion and distrust of end users that'd browse the stock levels.

  Here we should be really careful to treat (and test!) all corner
  cases, such as when
  ``dt_until`` is None but ``dt_from`` isn't and is earlier than the
  required datetime etc.

- would we have Avatars with both ``dt_from`` and ``dt_until`` being
  ``None`` or would we rather propagate ``dt_from`` to take into
  account that, at  least, we known that execution will happen no
  matter what after a certain date ? If both can be ``None`` we'd have
  some weird effects: a planned Arrival with
  a given date, followed by a Move would lead to the outcome of the
  Move been counted in ``future`` quantity queries before the planned
  time of the Arrival, so we better prevent that to happen. On the other hand,
  does this not repeat the problem with shifting the whole chain at
  execution of the first Operation ? Perhaps this would be less
  problematic, as the double countings due to overlapping Avatars
  would still be solved ? After all, the ``future`` quantity queries that
  are the most important are the ones at infinity (not affected by this),
  and we could mitigate with an asynchronous shifting (at least we
  wouldn't have double countings in the meanwhile).

Finally, if we could go as far as to allow overlapping Avatars, we
could imagine to support simultaneous concurrent scenarios in
planification, and maybe implementations of
:ref:`improvement_operation_superseding` in a way that'd be akin to the
obsolescence markers of Mercurial, but that's probably too far fetched.

Implementation based on date/time ranges
++++++++++++++++++++++++++++++++++++++++

.. note:: August 2019 addendum, part of migration to date/time ranges

.Here's a plan that should work, using the replacement of
``dt_from`` and ``dt_until`` by a range
(:py:attr:`timespan <anyblok_wms_base.core.physobj.main.Avatar.timespan>`) and
the :py:data:`infinity <anyblok_wms_base.dbapi.DATE_TIME_INFINITY>` value:

- timespan ``None``: undetermined non terminal Avatar
- timespan ``[infinity, infinity]``: undetermined
  terminal Avatar (still appears in future quantity queries
  at infinity). The ``[infinity, None)`` value would probably also
  work and provide easier compatibility (the test for terminality
  would be that the the timespan upper bound is ``None``, same as it
  is now for semi-determinate Avatars).
- all these indetermined Avatars would be produced by Operations whose
  ``dt_execution`` is "indeterminate", i.e., ``None`` or maybe infinity,
  provied that infinity becomes the default value in ``create()``.
  In particular, we'd stop initializing ``dt_execution``
  from the inputs' ``dt_from`` by default.
- upon execution of an Operation with previously indeterminate
  ``dt_execution``, we'd simply make its outcomes
  semi-determinate: ``[dt_execution, None)``
  (maybe ``[dt_execution, infinity]``, depending on the choice made
  for terminal indeterminate Avatar above). Nothing would have to be
  propagated, since all
  descendent Avatars of an indeterminate one would be indeterminate.
- data migration: nothing to be done, assuming migration to timespans
  would have already been done. The upcoming
  timespan support already deals with all corner cases
  (notably related to empty timespans). Existing
  Operations jsut wouldn't get the performance boost and the robustness of
  the new, simpler scheme. Some cleanups could be decided and
  implemented later, when most ``future`` Avatars of production
  database created before this change would be at least ``present``.

.. _improvement_federation:

Federation of Anyblok WMS instances
-----------------------------------
In a big system, especially with several sites for Goods handling
(warehouses, retail stores),
the detail of operations occurring at some given premises is usually
of no interest for the big picture.

For example, we could have a central system taking care of sales and
purchases, and keeping track of rough stock levels for these purposes.

Such a system would certainly not be interested by the detailed
organization of locations inside the different warehouses, nor with
the many operations that occur as part of the reception, keep in
stock, then delivery process and in fact, it would burden it.
On the other hand, it's best if handling sites don't suffer
the network latency to an offsite system.

The central system could instead have a simplified view of the
logistics, representing each handling site as a single Location, maybe
using :ref:`Goods lines with quantities <improvement_no_quantities>`
whereas a handling site would not, and intercommunication would
happen over the bus or REST APIs that are :ref:`planned anyway for
Anyblok WMS <blok_wms_bus>`.

If well done, that can also play some kind of sharding role, but there
are intrinsic limits as to how much simplified the view of the central
system can be, even combined with
:ref:`improvement_operation_superseding` to transmit only simplified
operations.

.. note:: about the central system example

          For mass scalability, keeping an exact track of stock
          levels is irrealistic anyway: the logistics system is too
          big and has too much processing to do to ask it for realtime
          reports.

          At a certain scale, its reports would timeout or fall out of sync
          because of, actually, general failure under the stress they
          generate. All the federation system can achieve in that case
          is pushing back the point of failure.

          Besides, if one managed 100 orders per minute, how useful is it to
          track them by the unit to tell customers if they are
          available ?

Obviously, many different scenarios can be achieved with well-thought
federation, including mesh-like moving of Goods across sites, as
needed if one has several production sites and several retail stores.

Communication with other systems also fall in this category.

.. _improvement_improvements:

Documentation is not a proper place for collective thought
----------------------------------------------------------

Well, yeah, this page should be superseded. How ?

* simply Github issues ?
* RFC/PEP-like subdirectory to PR suggestions onto ?
  Maybe that's too formal, but keeping somehow in the docs allows to
  cross-reference, like we did already in :ref:`goal_stubborn_reality`


Implemented
~~~~~~~~~~~

.. _improvement_operation_superseding:

Superseding of planned operations
---------------------------------
.. versionadded:: 0.9.0

                  *we now have enough planning alteration primitives to
                  support the use case detailed here, but we don't
                  have the most general form of Operations graph
                  manipulation suggested near the end of this section.*

We should provide the means to declare that a chain of operations
actually replaces (and maybe completes) some given (chain of?) planned
operations.

It's a general good practice for applications to try and not predict
the future too precisely, because of the "stubbornness of reality" but
it can lead to dilemmas.

A concrete example
++++++++++++++++++

Here's a concrete case, which I stumbled onto
two days ago for one of the prime applications to be built on Anyblok
WMS / Base.

The context:

* after the goods have been ordered from the suppliers, there is
  no way to predict the form the actual delivery will take: it can be
  one or several parcels, each one enclosing several boxes, themselves
  holding one or more of the expected Goods (which are individual
  units btw). None of this is predictable, and the actual contents can
  diverge both from the order and from what the Delivery Order says.

* The individual goods have individual stickers with barcodes
  that would positively identify the
  Goods Type and at least some of the expected Goods Properties. The
  operators will flash these barcodes as part of the verification
  process. These barcodes are supposed to be always telling the truth.

In general, I would advise against representing those incoming parcels
and the intermediate boxes if possible, but :

* The incoming parcels are moved away to an unpacking area as soon as
  they arrive, and actual verification of the contents occur later in
  the unpacking area, possibly by different persons.

* Actually there's even a complication
  that we won't address right away in this "thought of improvement":
  there might be only a single Delivery Order attached to several
  parcels, therefore we don't even have a theory of what each single one is
  supposed do contain.

My customer tells me out of other experiences that this is all fairly
common in many businesses, and I'm inclined to believe him about that.

Note, at this point, WMS Base does not include anything for
verification of unpacks and arrivals, nor any reservation or
planning system (that would issue chains of planned Operations), but
we have to take into account that end applications will need and have some.

Currently, here is how we can attempt to represent this use case with
what the core provides us (none of these is satisfactory):

1. Under-representation scenario

   * Don't represent anything of the incoming parcels or the
     intermediate boxes. After issuing
     the Purchase Order, just plan an
     Arrival for the expected goods, at the unpacking location.
     Make no further attempt to predict
     what form it will take place, just link it with the Purchase Order
     (that linking wouldn't be part of wms-core, but it would be
     implemented in the end application)
   * In particular, don't represent the unpacking of the parcels
   * This is enough for the reservations and plannings of downstream
     Operations to occur.
   * Upon actual unpacking of the parcel(s) of the delivery, compare
     with the expected contenst stored on the Arrival, amend the
     outcomes and maybe alert about the Purchase Order, create an
     arrival for the expected missing Goods etc.

   Drawback: we have a WMS system that doesn't track some
   items that are physically carried over in the warehouse! What
   happens, e.g, if one of the parcels has to be temporarily kept in another
   location than the normal unpacking area due to some unforeseen
   condition ?

2. Over-representation scenario

   Let's not even speak about the intermediate boxes.

   * Have a Goods Type for the parcel, and assume that most of
     the times we'll get just one parcel (does it smell bad?)…
   * After issuing the Purchase Order, plan an Arrival for the parcel,
     with properties that list the expected goods, also linked to the
     Purchase Order. Plan also a Move to
     the unpacking area, and an Unpack
   * Upon delivery, compare the Delivery Order with the expected
     Arrival, amend the Arrival (single) outcome as part of the verification
     process if there's a discrepancy (alert about the Purchase Order,
     create relicate Arrival) and execute the Arrival
   * Execute the Move, then the Unpack, and the final verification as
     part of the Unpack, comparing the properties of the parcel (which
     list the theory of what it holds) with the reality and amend the
     Unpack outcomes.

   Drawbacks:

   * if there are several parcels, we need to cancel the whole
     chain. But that also means cancelling everything that's
     downstream (think Assembly operations, a bunch of Moves, a final
     Departure).
   * Even relying on the planner to be smart enough to reconstruct
     everything, we'll have to make it synchronous or to notify the
     busy and impatient human operator once it's run.
   * This will break the reservation logic that we are also
     supposed to have in the application, creating great complexity
     upon the reservation system to maintain ordering and the
     scheduler (or simply make reservation pointless)

3. No crystal ball scenario

   * Don't plan anything upon Purchase Order
   * Proceed as in scenario 2 upon delivery, creating the needed
     Arrivals and Unpacks on the fly

   This has the obvious merit of being simple, and may be suitable for
   protoyping, while better alternative are developed.

   Drawbacks:

   * Those of scenario 1
   * We can't plan anything about those future Goods that arise from
     planned Arrivals.
   * In particular, we can't have reservation for these future Goods, which
     has consequences on the reservation system: it will have to consider the
     globality of all needs at each iteration, and order them by precedence
     each time there are new Goods instead of performing a reservation
     each time a new need arises. In practice it's more of a consequence on
     the count of unsatisfyable reservations, since it's not acceptable
     to drop reservation attempts that can't be resolved right away;
     therefore it's more a scalability issue than a code logic issue,
     to be considered together with the need for reservations to be fast.

The proposal is that we could merge scenarios 1 and 2 if we'd allow
to substitute a planned operation with a chain of operations.

* Start over as in scenario 1, just declaring an
  expected Arrival (``id=1``) in the unpacking area, linked with the
  Purchase Order
* All reserving and planning downstream of the Arrival can occur
  normally ; they will refer the the outcomes of the Arrival, which
  are Goods in 'future' state in the unpacking area.
* Upon actual delivery, say of three parcels (each with a list of its
  contents), the system would issue three Arrivals (id=``2,3,4``) with
  ``contents`` storing the theoretical contents, and
  link them to the Purchase Order
* The system would recognize that this Purchase Order is already
  linked to the first planned Arrival (``id=1``), and it would
  start planning the Moves (``id=5,6,7``) of the parcels to the unpacking
  area, as well as their Unpack operations (``id=8,9,10``)
* Finally, the system would call the new wms-core API to
  replace or "satisfy" Arrival (``id=1``) with the chain made of ids 2
  through 10, since the contents are identical. The core would arrange
  for the unpack outcomes (still unplanned, but that doesn't matter)
  to actually be the already existing incomes of the downstream
  operations, which don't need to be cancelled. Reservations don't
  have to be updated due to the Arrivals being different than ``id=1``.
* Moves are executed, in any order and at any pace
* Unpacks are executed and contents verified.
  Their outcomes are corrected according to reality, and backtraced to the
  Arrivals (and hence the Purchase Order) in cases of discrepancies,
  same as they would have been if the Arrival with ``id=1`` had been
  executed directly.

This proposal doesn't say anything about which commits or savepoints
are issued to the database and their logical orderings: these can be
considered implementation details at this point, all that matters at
this functional level is that the outcomes of the final Unpacks
with ``id=8,9,10``

* are not themselves visible in future stock levels together
  with outcomes of the original Arrival (``id=1``)
* don't get themselves reserved right away for other purposes.

As already noted, this does not take into account the fact that we'd
probably get a single delivery order for those three parcels,
but that can be addressed separately by introducing a multi-unpack
operation (details of that don't belong here).

Back to the general discussion
++++++++++++++++++++++++++++++
I'm pretty much convinced that the ability to refine a
prediction with another one (possibly partly done, it doesn't matter)
would be a great feature, and a strong step towards coping with the
stubbornness of reality.

Actually, about any planning would benefit from such a core
feature. The motto for downstream developers would then be: "plan the
minimum, refine it later to adjust to reality".

Question: do other WMS have such future history rewrite capabilities?

I'm not sure how far it should go in the general form. Mathematically,
it would be about replacing any subgraph of the history DAG by another one
which has the same incomes and outcomes, for a suitable definition of
"same".

Maybe it's simpler to implement it in full generality rather than some
special cases like the example above, in which the subgraph has a
single root with no incomes, that happens to be also root in the whole DAG.

.. _improvement_goods_location:

Droping Locations altogether in favor of Goods
----------------------------------------------

.. versionadded:: 0.8.0

In some cases, one wants to put the goods into some containing object,
dsand then perhaps move that containing object. The use cases I have
currently are cables in a plastic box and audio devices in a flight
case. Let's use the first one as example.

Currently, if one considers the box as a Location, this leaves the
cables it holds accessible to perform operations on them : perhaps
move them out of the box, test them and mark them as working or not,
etc. But, it does not represent the very convenient thing that can
happen in the physical reality: close the lid, move the whole at once
into a truck.

On the other hand, one can choose to represent the box as a Goods record, and
load them via an Assembly operation. Then its ``contents`` property
will have the Goods that are stored in the box, but each time one
wants to use or test a cable, one has to perform an Unpack and an
Assembly again. One would have to ignore that the Unpack will produce
avatar
for all the cables in the Location where the box sits, hence much confusion:
in reality, the cables are still in the box, not aside of it.
Moreover, unless special effort is done to avoid that, each
pack/unpack cycle would lead to change of ids, meaning that the system
considers that the box has changed enough to be a new box.
On top of that, the contents are not visible in quantity queries…

Add the issues mentioned in :ref:`improvement_location_name` on top of
that, and it's clear we have a design problem to solve.

In real life, the plastic box is both an object that can be tossed
into a truck and that can hold other objects, so why should we do
thing differently in an application meant to represent physical
objects ?

We could :

* remove the Location model
* make the ``location`` field of Avatars point towards a Goods record
* maybe add a flag in :ref:`physobj_behaviours` to indicate that some Goods can
  contain other ones.
* think of the interplay of this with the ``contents`` propery
  (variable part of :ref:`op_unpack`) and with packing/unpacking in
  general.
* accept the idea that in our system, even a warehouse, not to speak
  of the universe, is as much an object as a spoon is, and it is, in
  fact, a very big and unmovable object.

Assuming this doesn't introduce unsolvable problems, this would
also take care of all the issues of :ref:`improvement_location_name`:

* instead of the obscure ``parent`` of the existing hierarchy, we have
  the standard Avatar ``location`` field to indicate that some
  location is inside another: it's now very clear
  that it's about the position in space of the location, instead of
  maybe some logical grouping.
* we wouldn't have the terminology problem that the name might suggest that the
  position in space is fixed any more
* we'd gain immediately that Locations, being Goods are now typed. The
  Type itself can hold interesting information like dimensions etc.

This would leave us mostly with two concepts: Goods (physical objects)
and Operations, which is probably intellectually satisfying, but we'd
have a new problem: "Goods" now would sound
too specific and would have to be replaced by a more general name
(Item ? Object ? PhysObj ?)

.. _improvement_location_name:

"Location" terminology is misleading
------------------------------------

.. versionadded:: 0.8.0 (actually made obsolete by
                  :ref:`improvement_goods_location`)

Our concept of :ref:`Location <location>` does not imply that it is
actually a fixed place. Locations can actually be moving ones (a van,
a ship, a trolley or even a carrying box if needed).

I've heard that some proprietary WMS system makes use of the word
"support" for the same purposes. It sounds a bit obscure to my taste,
though. What alternatives would we have ?

Similarly, the hierarchy of locations does not mean that they are
actually inside each other. It's rather some kind of logical grouping,
useful to aggregate stock levels, or to confine some Goods to a group
of Locations once they are reserved.

.. _improvement_goods_type_hierarchy:

Goods Type hierarchy and behaviour inheritance
----------------------------------------------

.. versionadded:: 0.7.0

Some applications will have many of :ref:`Goods Types <physobj_type>`,
which will be often mere variations of each other, for example clothes
of different sizes.

It is therefore natural to group them in one way or another, both for
direct consideration by applicative code, and to allow mutualisation
of configuration within WMS Base.

Namely, we could make the :ref:`physobj_type` Model hierarchical, by
means of a ``parent`` field. This would bring the following
possibilities:

* Behaviour inheritance:
    If a :ref:`behaviour <physobj_behaviours>` is not found on a given
    Goods Type, then it would be looked up recursively on its parent,
    meaning that direct access to the ``behaviours`` field in applicative code
    should be prohibited, in favour of the :meth:`get_behaviour()
    <anyblok_wms_base.core.physobj.type.Type.get_behaviour>` method,
    that would take care of the inheritance.

    We could also allow *merging* of behaviours: a Goods Type could
    for instance inherit the ``unpack`` behaviour from its parent,
    changing only the ``required_properties`` key/value pair. Nested
    mapping merging is rather simple. Merging lists would be more
    complicated to specify.
* Generic reference:
    In some cases, it'd be interesting to specify an intermediate node
    in the :ref:`physobj_type` hierarchy rather than the most precise
    one. This could be useful for instance in Assembly Operations.
* (needs more thinking) Specialization:
    Help resolve the hard choices between :ref:`physobj_type` and
    :ref:`physobj_properties` by providing a way to convert the Type of
    some Goods to a more precise one according to its Properties.

    The interesting thing is that this could be done without any
    change in the ``id`` of the Goods, which is how we decided to
    represent that the physical object itelf is unchanged: only our way
    to consider has actually changed.

    This has the drawback that a given Goods record could be
    represented in several ways, and that is definitely not sane. Some
    logic, such as quantity queries, could be aware of it at a high
    complexity price. Perhaps the good way to do it would be to make
    it transparent:

    + define some Property to encode the specialization of a Goods
      Type relative to its parent.
    + have the :meth:`set_property()
      <anyblok_wms_base.core.physobj.main.PhysObj.set_property>` method
      set the proper Goods Type automatically on changes of that
      Property. *(Not done for 0.7.0)*
    + have the :meth:`get_property()
      <anyblok_wms_base.core.physobj.main.PhysObj.get_property>` method
      return the proper value for that Property, inferred from the
      actual Goods Type. *(This is actually a consequence of the Type
      Properties, also done for 0.7.0)*

    This transparency would also simplify configuration of Assembly
    Operations when faced with generic types: no need for even more
    complex configuration to decide on the final Goods Type, just
    treat it like any other Property.

    Also, it would help refactoring applications that would start by
    considering a parameter to be a simple Property, and later on
    recognize that they need to represent it as a full Goods Type.



.. _improvement_stock_levels:

Location hierarchical structure and stock levels
------------------------------------------------

.. note:: replaced by simple location type filterings in version 0.8.0

.. versionadded:: 0.7.0

Counting (or summing) the goods quantities is expensive within an
arborescent structure, even if done with PostgreSQL recursive queries.

And actually, it's often a bad idea to rely on the arborescence for
that. Imagine a system with two warehouses: it's tempting to have a
location for each warehouse, that would be the ancestor of all
locations within the warehouse. Now do we really like to count all
items in there, including locations for temporary storage of damaged
goods before actually destroying them ?

In fact, measuring stock levels is often done for a purpose (like
deciding whether we can sell), and, assuming we want an exact count,
it should not rely on the Location hierarchy, but rather on the
Location's purpose (e.g., storage before shipping to customers) or not
on Locations at all.

Therefore we should introduce a simple tag system for stock levels
grouping in Location. Getting back to the crucial example of counting
sellable goods, it should also take any notion of reservation into
account anyway (it's truer than counting short term previsions).

We can keep the arborescent structure,
claiming this time that it really expresses physical inclusion of
Locations (can be useful for other purposes than stock levels, such as
confinement of reserved Goods). It could be acceptable that *by
default*, these tags are copied to the sub-Locations upon creation, but
nothing more.

We should rename the ``parent`` field as ``part_of`` or ``inside`` to
insist on that.


.. _improvement_no_quantities:

Quantity will often be a useless complexity
-------------------------------------------

.. versionadded:: 0.7.0

.. note:: at the time of this writing, :ref:`physobj_model` had the
          ``quantity`` field that is now carried by
          :ref:`wms-quantity <physobj_quantity>`.

In the current state of the project, :ref:`physobj_model` records have a
``quantity`` field. There are several hints that this shouldn't be a part
of the core, but should be moved to a distinct blok. Let's call it
``wms-aggregated-goods`` for the time being.

1. we settled on ``Decimal`` (Python) / ``numeric`` (PostgreSQL) to
   account for use cases resorting to physical measurements (lengths of
   wire, tons of sand). Of course that's overridable, but it's an
   example of the core taking decisions it should not
2. this creates a non trivial complexity for most operations, that
   have to maybe split Goods records.
3. in most logistics applications, only packaged Goods are actually
   been handled anyway, therefore they are merely equivalent to
   *units* (reels of 100m of wiring, bags of 50kg sand, etc.).

   The obvious and only benefits of this ``quantity`` field in these use cases
   are that we can represent many identical such units with a single
   line in the database.

   But these benefits are severely impaired by the need to perform and
   record many Splits, unless it's so much common to handle several of
   them together *and not as some kinds of bigger packs*, such as
   pallets or containers that it counterbalances the overhead of all
   those Splits.

   Thery are also impaired by traceability requirements, for instance
   if the related properties have consequent variability. In the extreme
   case, if we track serial numbers for all goods, then we'll end up
   with each Goods record having ``quantity=1``.

   In many use cases, including the most prominent one at the inception of WMS
   Base, several identical goods almost never get shipped to final
   customers, so it's guaranteed that the overwhelming majority of
   these lines of Goods with quantities greater that 1 would be
   split down to quantity 1, and even if we'd defined the Unpacks
   outcomes to have single Goods lines with quantity equal to 1, it
   would still not be the worth carrying around the code that decides
   whether to split or not.

On the other hand, putting aside the current code for
quantities and :ref:`the related operations <op_split_aggregate>`
would probably create a rift in the implementations.

Namely, ``wms-aggregated-goods`` would have to override much of
``wms-core`` and I fear that it'd become under-used, which would
either impair its compatibility with downstream libraries and
applications, or become a needless development burden on these latter ones.


.. _improvement_avatars:

Goods Avatars
-------------

.. versionadded:: 0.6.0

.. note:: at the time of this writing, :ref:`PhysObj <physobj_model>`
          was called "Goods", there was a separate Model for
          locations, and Goods bore
          all the fields that are now in :ref:`Avatars <physobj_avatar>`

Due to the planning and historical features we want, in our system,
the physical goods will give rise to many different records of
Goods
as non destructive operations, typically :ref:`Moves <op_move>`
currently create new records, and obsolete the ones they got as input.

This is a problem to design a reservation system, which should clearly
not reserve some Goods in some precise state at some time in
some place, but only be attached to the mostly immutable part of their
data.

For an example of the latter requirement, consider a T-shirt been
reserved in advance for some end delivery, before it has even arrived
in the warehouse. Imagine some planner has decided to put it in
location AB/X/234 before packing it with other goods of the same
delivery and shipping them to the final customer. Now, deciding at the
last minute to put it in the adjacent AB/X/235 should not void the
reservation. It should require at most :ref:`partial replanning
<improvement_operation_superseding>`. Even if the end location is
the planned one, but the Goods record isn't the same one,
the system should not have to update its reservations to match it:
that's an obvious source of conflicts, it's bad for performance, it
contradicts many of our :ref:`design_goals` and, frankly speaking,
it's absurd: everybody would agree it's « the same T-shirt ».

Simply arranging for :ref:`op_move` to create a new record in the
``past`` state, changing just location, times and state on the moved
one  wouldn't be a solution, as it would require the even
heavier update of all past history. And having :ref:`op_move` mutate all the
:ref:`physobj_model` in place as we intended before realizing we could
provide :ref:`op_cancel_revert_obliviate` is not doable because of planning…

So, the proposal is to introduce a new Model, *Goods Avatar*, that would
bear the (very) mutable part of the current Goods.
This is what :ref:`Operations <operation>` would manipulate and reference.

Now the Goods Model would express the otherwise not so
much well-defined idea of a physical object that stays "the same".
We should even provide transforming :ref:`Operations <operation>` to
resolve the question whether some given change (like engraving a
personalised message on a watch) means it becomes a different object
or not, as it's after all only a matter of perception that we can't
decide in WMS Base.

The future :ref:`reservation system(s) <blok_wms_reservation>` would then
lock and/or refer to this skimmed down in the Goods
Model. In end applications, concrete
schedulers/planners would also refer to them, and look for *Avatars* to
create their planned :ref:`Operations <operation>`.

This also probably means that the purposes of the separate
:ref:`physobj_properties` Model would boild down to deduplication (probably
still very much useful).

All of this is made utterly complicated by the :ref:`issue of
quantities <improvement_no_quantities>`, that's why this proposal
mostly doesn't speak of them, assuming that other problem is solved.
