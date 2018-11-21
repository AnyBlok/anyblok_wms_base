inventory: the wms-inventory Blok
=================================

This package provides the :ref:`blok_wms_inventory` Blok.

.. py:module:: anyblok_wms_base.inventory


Model.Wms.Inventory
-------------------

.. autoclass:: anyblok_wms_base.inventory.order.Inventory

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: root

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: create
   .. automethod:: reconcile_all

Model.Wms.Inventory.Node
------------------------

.. autoclass:: anyblok_wms_base.inventory.node.Node

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: state
   .. autoattribute:: inventory
   .. autoattribute:: parent
   .. autoattribute:: location
   .. autoattribute:: is_leaf

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: split
   .. automethod:: compute_actions
   .. automethod:: clear_actions
   .. automethod:: compute_push_actions
   .. automethod:: recurse_compute_push_actions

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

.. autoclass:: anyblok_wms_base.inventory.action.Action

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: node
   .. autoattribute:: OPERATIONS
   .. autoattribute:: quantity
   .. autoattribute:: location
   .. autoattribute:: destination
   .. autoattribute:: physobj_type
   .. autoattribute:: physobj_code
   .. autoattribute:: physobj_properties

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: simplify
   .. automethod:: apply
   .. automethod:: choose_affected
