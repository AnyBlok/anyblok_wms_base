.. This file is a part of the AnyBlok / WMS Base project
..
..    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
..
.. This Source Code Form is subject to the terms of the Mozilla Public License,
.. v. 2.0. If a copy of the MPL was not distributed with this file,You can
.. obtain one at http://mozilla.org/MPL/2.0/.

.. _design_goals:

Design Goals
============

This page presents what we are striving to achieve, and explains some
design decisions.

It also summarizes some of the features of Anyblok
WMS Base, to put them in perspective of the relevant goals.

To be clear, we are not claiming we reached these goals, nor that
we'll reach them without some serious change on the ways we are
designing and implementing Anyblok / WMS Base, as the project
is still in its infancy.

.. _goal_tightness:

Tightness and genericity
------------------------
The scope of Anyblok / WMS Base is limited by design. Although Anyblok
applications enjoy powerful override capabilities, these should not be
abused.

If we'd assume and provide too much in WMS Base components, the
inevitable overrides from downstream applications and libraries would
end up in an explosion of interdependencies, and intractable
code, such as we've often witnessed in overiddable systems whose core
components did too much.

Ideally, one should be able to create applications
without overriding anything besides what is explicitely designed to be
overridden.

The goal of Anyblok / Wms Base is therefore to focus on a set of
fundamental :ref:`core_concepts`, in hope of doing them really well,
while giving downstream applications or libraries the *means* to
implement their detailed behaviours.

To help with this, Anyblok / Wms Base is actually itself split into
several :ref:`components` ("Bloks" in Anyblok speech), of which only
``wms-core`` is mandatory.
For instance, the reservation system that ships with AnyBlok / Wms
Base takes the form of the separate ``wms-reservation`` Blok. Even some
further developments meant for ``wms-core`` may be first provided as
separate Bloks.

So, in particular, you won't find any user interface within Anyblok /
WMS Base. Actually we don't want to even assume that the end
application has a notion of user. Similarly, we don't want to assume
that the application is actually about selling, buying or making
goods, even if, obviously, most will be. Finally, WMS Base does not
intend to provide a concept of picking, at least not in ``wms-core``.

This statement does not imply that we, as a team, won't provide in the
future some fully integrated library or application that would handle some
frequent use cases. If that happens (and we surely hope it
will, actually !) it'll just have to be a different Python project.

This does not mean either that we don't have concrete use cases in
mind, nor ideas on how an application is supposed to use WMS Base features
in practice. Actually, we do, and they are based on actual experience
in the field. You'll find mentions of use cases with concrete examples
all over this documentation, and you are welcome to help us designing
the system by submitting more of them.

.. _goal_traceability:

Full traceability
-----------------

Modern handling of wares requires great traceability capabilities. One
often needs to identify faulty lots for product recalls, track down
products by serial number, not even to speak of expiry of perishables
and accounting.

One also needs to understand what has gone wrong in the face of
software bugs or human errors.

Anybox WMS Base provides different set of features for these purposes:

* :ref:`flexible properties <physobj_properties>` allow to represent
  what can be variable amond Physical Objects of a given Type
* full historical data about operations
* ability to query Physical Objects in the past and in the
  (theoretical) future

.. _goal_flexibility:

Flexibility
-----------

This is the counterpart of :ref:`goal_tightness`: it would not make
any sense to focus on a core set of features without providing the
means to expand on them.

Besides the inherent flexibility of Anyblok (that one won't ever
become tired of recalling), WMS Base should provide the downstream application
developers the ways to represent what they need with no overrides, and
to forward the needed flexibility to functional administrators of the system.

To that effect, we currently have :

* :ref:`physobj_properties`, already mentioned in
  :ref:`goal_traceability`
* Behaviours in operations: the fine details of what operations should
  do of some given :ref:`physobj_type` are customisable by this means.

  This is true. for instance, of :ref:`op_unpack`, whose outcomes are
  entirely defined in those behaviours. This is also how the core decides if
  :ref:`op_split_aggregate` are reversible.
* The as-of-now theoretical possibility for downstream libraries and
  applications to define custom Operations.

.. _goal_stubborn_reality:

Taking real life into account
-----------------------------

As an obvious fact, Stock and Logistics applications can but
*represent* what happens in the real world. This implies that they
should be rich enough to encompass events of the real world, such as
the accidental destruction of some physical objects.

This also implies that care must be taken to define what the data
should actually mean. We're trying to be very explicit about that, but it's
all about intents, as it also depends on the usage the concrete application
will make of that library. For a concrete example, see the meaning of the
data about Physical Objects that :ref:`op_arrival` operation carries.

Logistics systems also try and predict or planify the future, yet
reality can be really stubborn.

End users hate nothing more than computer systems that
fail to comply to reality once it diverges from their idealised views
about it. Operative engineers themselves tend not to be happy if they
have to fix manually dozens of lines in SQL databases to bring a
Warehouse Management System back in sync with reality, at great risk
of breaking everything.

Also, sometimes, because of bugs in the system or of its users,
changes will be recorded that have no real-life counterpart. These
should be easy to correct.

That's why Anyblok WMS :ref:`operations <operation>` have had
:ref:`op_cancel_revert_obliviate` from before the first experimental release.

We also have :ref:`plans to help avoid
over-representing the future <improvement_operation_superseding>`.

That being said, this part of the design goals is a difficult one, and
moreso for downstream applications and user interfaces. We'll do our best.

.. _goal_scalability_performance:

Scalability and performance
---------------------------

As for scalability, our initial goal is to maintain a rate of up to
5000 deliveries per day on a basic sales workflow, after doing one
million of them, on commodity hardware, without resorting to archival,
and with a few tenth of thousands of :ref:`stock locations <location>`.

These are, after all, modest goals. If you need more scalability, you
can consider :ref:`improvement_federation`, but that's frankly
speaking merely vaporware at this point.

.. note:: the :ref:`traceability goal <goal_traceability>` implies that
          the database will grow a lot, since it'll have to keep a full
          operational history for that million deliveries. Archiving
          will inevitably become necessary, but it'd be useful to keep a
          whole fiscal year on hand, and have only more demanding
          applications perform specialized archiving strategies, such
          as table partioning or partial replication for BI and
          accounting needs…

These goals are obviously very vague, since actual workflows will vary
vastly, and such will their computing costs. Early results are
promising though, but they are over simplified at this stage of
developement, and there's not much point investing too much in
performance analysis in early development cycles.
We intend to publish some example use-cases that will
double up as benchmarks, though.

The performance design should be oriented towards reactivity for human
operators. A 1 second delay after flashing a QR code is barely
tolerable, therefore the target reactivity should be 0.1s for common
operations, under the above mentioned load. Time will tell if that was
a realistic goal.

To achieve that, most of the heavy work should be accomplished by
background processing (reservation, scheduling, that is issueing
planned operations and their outcomes) leaving only
fast confirmations to human operators. Obviously, a lot depends on
downstream components, but the examples should demonstrate a way of
doing it.


Quality
-------
This is an obvious benefit of having focused goals: we can afford
greater efforts towards quality in the scope of WMS Base than we would
for a complete system.

So, for instance, it is fully unit tested, and abides to PEP8 coding
standards, and that is checked by continuous integration systems
(Travis CI at the time of this writing).

Despite what everybody would say, end applications are often plagued
with the dire need of getting stuff in production as soon as possible,
maybe bypassing procedures in case of emergencies, and it requires a
great amount of will and freedom for the developers to sanitize it
after the fact.

Thanks to the flexibility of Anyblok, downstream developers are free to
override anything from WMS Base, be it for quick workarounds or
features. This means that within WMS Base, we have no need to rush
for anything we'd missed, bug or feature, even if it's crucial for one
application that we happen to maintain ourselves.

In the case of features that end developers feel should be
part of WMS Base, they can be upstreamed later through pull requests,
discussed, maybe become new optional bloks if not fit for the provided
ones. In the meanwhile, WMS Base quality won't be affected.

PS: nobody's perfect, and we certainly aren't. If you feel that
quality is lacking, and especially if you have proposals, feel free to
tell us about it.
