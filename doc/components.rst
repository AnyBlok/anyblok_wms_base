.. _components:

Components
==========

Anyblok / Wms Base provides several components, what Anyblok calls
"Bloks". This means that you have to install them in the database,
update them etc.

.. _blok_wms_core:

wms-core
--------

As the name suggests, this Blok provides the :ref:`core_concepts` of
Anyblok / Wms.

.. seealso:: :mod:`the code documentation  <anyblok_wms_base.bloks.wms_core>`.


.. _blok_wms_reservation:

wms-reservation
---------------

This Blok provides facilities to reserve :ref:`goods_goods`.

Reservations bind :ref:`goods_goods` to some purpose
(typically a final delivery, or a manufacturing action), that
typically gets fulfilled through a *chain* of operations.

.. seealso:: :ref:`the overwiew of reservation concepts,
             <reservation>` and :mod:`the
             code documentation  <anyblok_wms_base.bloks.wms_reservation>`.


.. _blok_wms_quantity:

wms-quantity
------------

This Blok adds a ``quantity`` field on the :ref:`Wms.Goods
<goods_goods>` model, to represent goods handled in bulk or several
identical items in one record.

.. seealso:: :doc:`goods_quantity`

.. _blok_wms_rest_api:

wms-rest-api
------------
.. warning:: development not even started

This Blok will integrate Anyblok / WMS Base with `Anyblok / Pyramid
<https://anyblok-pyramid.readthedocs.io>`_ to provide a RESTful HTTP
API.

.. _blok_wms_bus:

wms-bus
-------
.. warning:: development not even started

This Blok will integrate Anyblok / WMS Base with `Anyblok / Bus
<https://anyblok-bus.readthedocs.io>`_ to provide intercommunication
with other applications.
