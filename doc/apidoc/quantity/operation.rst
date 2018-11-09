quantity.operation
==================

Model.Wms.Operation.Split
~~~~~~~~~~~~~~~~~~~~~~~~~

This Operation Model inherits from :class:`Mixin.WmsSingleInput
<anyblok_wms_base.core.operation.single_input.WmsSingleInputOperation>`

.. py:currentmodule:: anyblok_wms_base.quantity.operation.split

.. autoclass:: anyblok_wms_base.quantity.operation.split.Split

   .. autoattribute:: TYPE

   .. raw:: html

      <h3>Specific members</h3>

   .. autoattribute:: wished_outcome

   .. raw:: html

      <h3>Optional methods of Operation subclasses</h3>

   .. automethod:: is_reversible

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>


   .. automethod:: after_insert
   .. automethod:: execute_planned
   .. automethod:: plan_revert_single


Model.Wms.Operation.Aggregate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. py:currentmodule:: anyblok_wms_base.quantity.operation.aggregate

.. autoclass:: anyblok_wms_base.quantity.operation.aggregate.Aggregate

   .. raw:: html

      <h3>Specific members</h3>

   .. autoattribute:: UNIFORM_PHYSOBJ_FIELDS
   .. automethod:: field_is_equal

   .. raw:: html

      <h3>Optional methods of Operation subclasses</h3>

   .. automethod:: is_reversible
   .. automethod:: check_create_conditions

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: after_insert
   .. automethod:: execute_planned
   .. TODO   .. automethod:: plan_revert_single

Splitter Mixins: splitting Physical Objects if needed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:module:: anyblok_wms_base.quantity.operation.splitter

.. autoclass:: anyblok_wms_base.quantity.operation.splitter.WmsSplitterOperation

   .. raw:: html

      <h3 class="section">Fields and their semantics</h3>

   .. autoattribute:: partial
   .. autoattribute:: quantity

   .. raw:: html

      <h3 class="section">
          Implemented subset of the operation subclass API
      </h3>

   (we list only those methods that override the base classes).

   .. automethod:: before_insert
   .. automethod:: check_execute_conditions
   .. automethod:: execute_planned

.. autoclass:: anyblok_wms_base.quantity.operation.splitter.WmsSplitterSingleInputOperation

Model.Wms.Operation.Move
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: anyblok_wms_base.quantity.operation.move.Move

   .. raw:: html

      <h3 class="section">
          Implemented subset of the operation subclass API
      </h3>

   .. raw:: html

      <h3 class="section">Methods</h3>

   .. automethod:: revert_extra_fields


Model.Wms.Operation.Unpack
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. py:module:: anyblok_wms_base.bloks

.. autoclass:: anyblok_wms_base.quantity.operation.unpack.Unpack

   .. raw:: html

      <h3 class="section">
          Implemented subset of the operation subclass API
      </h3>

   .. raw:: html

      <h3 class="section">Methods</h3>

   .. automethod:: create_unpacked_goods

Model.Wms.Operation.Departure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: anyblok_wms_base.quantity.operation.splitter.Departure

