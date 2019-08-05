For downstream developers and deployers
=======================================

.. _install:

Installation
~~~~~~~~~~~~

Database
--------

.. warning:: AnyBlok WMS / Base supports PostgreSQL only.

It is strongly recommended to install the `btree_gist
<https://www.postgresql.org/docs/11/btree-gist.html>`_ PostgreSQL
extension::

  CREATE EXTENSION btree_gist;

This requires PostgreSQL administration privileges. If you want it to
be automatically available in databases created automatically by
unprivileged ``anyblok_createdb`` processes, you can install it in appropriate
database template, for instance ``template1``, the default one meant
to be customized by the local DBA.

.. warning:: If ``btree_gist`` is not available, your database will not benefit
             from the strongest integrity constraints, nor the fastest
             indexing solutions.

.. _arch:

Architecture
~~~~~~~~~~~~

A typical application would be made of several different services,
each one with very different concurrency features and requirements.

The smallest applications, those with almost no concurrency (single
user or almost…) can get by without these separations, but it's
otherwise expected to be essential from medium-sized deployments on.

In the present page, "service" is to be understood in a very wide
sense. From separate processes being executed on the same OS to
physically different servers or appliances, through various
virtualization options…

.. _arch_reserver:

Reserver
--------

In all but the largest installations, this background service is
supposed to run in-order, without concurrency.

Its task is to translate :ref:`Reservation Requests <resa_request>` into actual
:ref:`Reservations <resa_reservation>`: it takes the Requests in
order, looks for matching :ref:`physobj_model` (whose availability may
lie in the future) and reserves them, with the effect that only those
transactions acting on behalf of the Reservation will be allowed to
issue :ref:`Operations <operation>` about them.

The relatively simple task is supposed to (and must) be accomplished
really fast, and that's why it's acceptable for a reserver to be
single-threaded (whatever that means in the deployment context).

That being said, larger installations can make use of custom query
filtering to dispatch logically independent Requests onto several queues
and process them in parallel.

.. _arch_planner:

Planner
-------
The duty of this service is to issue the :ref:`Operations
<operation>` that express the very purposes of the system.

The planner is where most of the business logic of a concrete
application takes place. One by one, it claims exclusivity over
those :ref:`Reservation Requests <resa_request>` that are fully
reserved, reads their purposes and translates that into action upon
the reserved :ref:`physobj_model`.

While it is related to Reservations, its way of proceeding is in sharp
contrast with :ref:`arch_reserver`:

* Planners are mostly made of custom business logic, while Reservers
  are usually very generic
* Planners can and should be heavily multithreaded: it is actually
  one of the goals of the reservation system to single out and solve
  contention so that more complex.

.. _arch_general_worker:

General Worker
--------------
While they can be further specialized, the general workers take care
of all communications of the application.

* with operators, through HTTP requests issued by their terminals,
  from full management interfaces to barcode flashers ;
* with other business applications, typically through some enterprise
  bus.

In particular, the general workers will issue
:ref:`Reservation Requests <resa_request>` in response to external
events, such as a sale that should translate as an outbound shipment,
but they can also sometimes perform :ref:`Reservations
<resa_reservation>` directly if needed.

.. _avatars_containers_contents:

Avatars and containers vs the 'contents' Property
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At first sight, it may seem that we have in Anyblok / Wms two
different ways to encode that something contains something else: the
``location`` field of :ref:`Avatars <physobj_avatar>`, pointing to  containers,
on one hand, and the ``contents`` :ref:`Property <physobj_properties>`
on the other hand. In truth, these two are fairly different, and this
section's purpose is to explain how, to help developers choose the
right one for their case.

Let's begin by recalling that the ``contents`` Property is used
primarily in :ref:`Unpack Operations
<op_unpack>`, where it encodes the variable part of the expected
outcomes. Conversely, :ref:`Assembly Operations <op_assembly>` are able to
fill this Property, paving the way for a subsequent Unpack.

Here are the differences:

- Comprehensiveness:
   the ``contents`` Property does not necessarily encode all the
   contents of some Physical Object, only what is not a direct
   consequence of its :ref:`Type <physobj_type>`.
- Transparency:
   Physical Objects that are described in a ``contents`` Property
   don't actually exist in the system. At most they can have future
   Avatars if an Unpack is planned or past Avatars if ``contents`` is the
   result of some Assembly.
   They won't be counted correctly by quantity queries, nor
   will it be directly possible to perform Operations on them, e.g,
   Moves, obviously, but also Observations, Disparitions:
   one must first at least plan an Unpack – which affects the whole
   pack, and in many cases would be followed by a converse Assembly.
- Accuracy:
   The ``contents`` Property is actually more a promise of what will be
   found if an Unpack is performed than anything else.
- Evolution:
   Like all Properties, ``contents`` cannot have different values
   according to some considered date and time.




