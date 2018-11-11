inventory: the wms-inventory Blok
=================================

This package provides the :ref:`blok_wms_inventory` Blok.

.. py:module:: anyblok_wms_base.inventory


Model.Wms.Inventory.Order
-------------------------

.. autoclass:: anyblok_wms_base.inventory.order.Order

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: root

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: create

Model.Wms.Inventory.Node
------------------------

.. autoclass:: anyblok_wms_base.inventory.node.Node

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: state
   .. autoattribute:: order
   .. autoattribute:: parent
   .. autoattribute:: location

Model.Wms.Inventory.Line
------------------------

.. autoclass:: anyblok_wms_base.inventory.node.Line

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: node
   .. autoattribute:: location
   .. autoattribute:: type
   .. autoattribute:: code
   .. autoattribute:: properties
   .. autoattribute:: quantity


Model.Wms.Inventory.Action
--------------------------

.. autoclass:: anyblok_wms_base.inventory.node.Action

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: node
