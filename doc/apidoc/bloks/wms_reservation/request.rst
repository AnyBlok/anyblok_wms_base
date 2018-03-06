wms_reservation.request
=======================

.. py:module:: anyblok_wms_base.bloks.wms_reservation.request

Model.Wms.Reservation.Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: anyblok_wms_base.bloks.wms_reservation.request.Request

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: purpose
   .. autoattribute:: reserved
   .. autoattribute:: planned

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: claim_reservations
   .. automethod:: reserve_all
   .. automethod:: reserve

   .. raw:: html

      <h3>Exceptions</h3>

   .. autoattribute:: ReservationsLocked

   .. raw:: html

      <h3>Internal methods</h3>

   .. automethod:: is_txn_reservations_owner
   .. automethod:: lock_unreserved

Model.Wms.Reservation.RequestItem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: anyblok_wms_base.bloks.wms_reservation.request.RequestItem


   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: request
   .. autoattribute:: goods_type
   .. autoattribute:: quantity
   .. autoattribute:: properties

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: lookup
   .. automethod:: reserve

