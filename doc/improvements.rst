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

.. _improvement_location_name:

"Location" terminology is misleading
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

.. _improvement_operation_superseding:

Superseding of planned operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We should provide the means to declare that a chain of operations
actually replaces (and maybe completes) some given (chain of?) planned
operations.

It's a general good practice for applications to try and not predict
the future too precisely, because of the "stubbornness of reality" but
it can lead to dilemmas.

A concrete example
------------------

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
     what form it will take place, but linki it with the Purchase Order
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
     busy and impatient operator once it's run.
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
  ``unpack_outcomes`` storing the theoretical contents, and
  link them to the Purchase Order
* The system would recognize that this Purchase Order is already
  linked to the first planned Arrival (id=``1``), and it would
  start planning the Moves (id=``4,5,6``) of the parcels to the unpacking
  area, as well as their Unpack operations (id=``7,8,9``)
* Finally, the system would call the new wms-core API to
  replace or "satisfy" Arrival (id=1) with the chain made of ids 2
  through 9, since the contents are identical. The core would arrange
  for the unpack outcomes (still unplanned, but that doesn't matter)
  to actually be the already existing incomes of the downstream
  operations, which don't need to be cancelled. Reservations don't
  have to be updated due to the Arrivals being different than ``id=1``.
* Moves are executed, in any order and at any pace
* Unpacks are executed and contents verified.
  Their outcomes are corrected according to reality, and backtraced to the
  Arrivals (and hence the Purchase Order) in cases of discrepancies,
  same as they would have been if the Arrival with (``id=1``) had been
  executed directly.

This proposal doesn't say anything about which commits or savepoints
are issued to the database and their logical orderings: these can be
considered implementation details at this point, all that matters at
this functional level is that the outcomes of the final Unpacks
with (``id=7,8,9``)

* are not themselves visible in future stock levels besides the
  outcomes of the original Arrival (id=1) is superseded
* don't get themselves reserved right away for other purposes.

As already noted, this does not take into account the fact that we'd
probably get a single delivery order, but that can be addressed
separately by introducing a multi-unpack operation (details of that
don't belong here).

Back to the general discussion
------------------------------
I'm pretty much convinced that the ability to refine a
prediction with another one (possibly partly done, it doesn't matter)
would be a great feature, and a strong step towards coping with the
stubbornness of reality.

Actually, about any planning would benefit from such a core
feature. The motto for downstream developers would then be: "plan the
minimum, you can rewrite it later".

Question: do other WMS have such future history rewrite capabilities?

I'm not sure how far it should go in the general form. Mathematically,
it would be about replacing any subgraph of the history DAG by another one
which has the same incomes and outcomes. Maybe it's simpler to
implement it in full generality rather than some special cases like
the example above (which has a single root that happens to be also
root in the whole DAG, which no incomes).


.. _improvement_no_quantities:

Quantity will often be a useless complexity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the current state of the project, :ref:`goods_goods` records have a
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

   In many use cases, including the most prominent one at the inception of WMS
   Base, several identical goods almost never get shipped to final
   customers, so it's guaranteed that the overwhelming majority of
   these lines of Goods with quantities greater that 1 would be
   split down to quantity 1, and even if we'd defined the Unpacks
   oucomes to have single Goods lines with quantity equal to 1, it
   would still not be the worth carrying around the code that decides
   whether to split or not.

On the other hand, putting aside the current code for
quantities and :ref:`the related operations <op_split_aggregate>`
would probably create a rift in the implementations.

Namely, ``wms-aggregated-goods`` would have to override much of
``wms-core`` and I fear that it'd become under-used, which would
either impair its compatibility with downstream libraries and
applications, or become a needless development burden on these latter.

.. _improvement_federation:

Federation of Anyblok WMS instances
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Well, yeah, this page should be superseded. How ?

* simply Github issues ?
* RFC/PEP-like subdirectory to PR suggestions onto ?
  Maybe that's too formal, but keeping somehow in the docs allows to
  cross-reference, like we did already in :ref:`goal_stubborn_reality`

