.. _reservation:

Reservation
===========

The purpose of reservations in Anyblok / WMS Base is two-fold:

* functionally, it's about making sure that :ref:`goods_goods` that
  are essential to some purposes stay available for them (as much as
  possible, of course)
* technically, it collapses contention onto a relatively simple
  problem that, once solved, allows the rest of the application to
  work in parallel without much trouble.


.. _resa_request:

Reservation Request
~~~~~~~~~~~~~~~~~~~
This is the cornerstone of the reservation system.

These represent (and link together) what it is needed to reserve, and for
what purpose.

They can be issued freely by all subsystems when new needs arise. It
shouldn't lead to contention problems, as they are simply inserted in
the database, and are mostly inert at that point.

They get enforced as :ref:`Reservations <resa_reservation>`, typically by a
:ref:`arch_reserver` service. From that point on, they represent
limitations on what can be done about the corresponding
:ref:`goods_goods`, and get fed to :ref:`Planners <arch_planner>` as work
specifications.

Reservation Requests are actually made of several Request Items.

.. seealso:: the :class:`code documentation
             <anyblok_wms_base.reservation.request.Request>`.

.. _resa_reservation:

Reservation
~~~~~~~~~~~
A Reservation binds some :ref:`goods_goods` to a Reservation Request Item.

Once thus reserved, new :ref:`Operations <operation>` can't be done or
planned for these :ref:`goods_goods` unless either:

- the current database transaction has claimed ownership of the reservations of
  the corresponding Request (this is meant for :ref:`Planners <arch_planner>`)
- the :ref:`Operation <operation>` is in a restricted list of
  authorized ones (this probably won't be implemented before version
  0.7). The idea is to still allow some :ref:`Operations <operation>`
  (for instance a short range :ref:`Move <op_move>` for rack
  reorganisation shouldn't be prevented if the same :ref:`goods_goods`
  are supposed to leave the system later on.

.. seealso:: the :class:`code documentation
             <anyblok_wms_base.reservation.reservation.Reservation>`.

