For downstream developers and deployers
=======================================

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
order, looks for matching :ref:`goods_goods` (whose availability may
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
the reserved :ref:`goods_goods`.

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
