Abstract classes
================

.. py:module:: anyblok_wms_base.bloks.wms_core.operation

Model.Wms.Operation
~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.base.Operation

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: type
   .. autoattribute:: state
   .. autoattribute:: follows
   .. autoattribute:: dt_execution
   .. autoattribute:: dt_start

   .. raw:: html

      <h3>Main API</h3>

   These are the methods end applications and downstream libraries are
   supposed to use.

   .. automethod:: create
   .. automethod:: execute
   .. automethod:: cancel
   .. automethod:: plan_revert
   .. automethod:: obliviate

   .. raw:: html

      <h3>Mandatory API of subclasses</h3>


   These are the methods the concrete Operation subclasses must implement.

   .. note:: we provide helper Mixins to help reduce boilerplate and
             duplication.

   .. automethod:: check_create_conditions
   .. automethod:: find_parent_operations
   .. automethod:: after_insert
   .. automethod:: check_execute_conditions
   .. automethod:: execute_planned
   .. automethod:: cancel_single
   .. automethod:: plan_revert_single
   .. automethod:: obliviate_single

   .. raw:: html

      <h3>Optional API of subclasses</h3>


   These methods have a default implementation in the base class, and
   are meant for the concrete Operation subclasses to override them if needed.

   .. automethod:: is_reversible

Helper Mixin classes
~~~~~~~~~~~~~~~~~~~~

These implement a subset of the mandatory API for subclasses of
:class:`Operation <.base.Operation>`.

They tend to have long names because Anyblok does not have namespaces
for Mixins.

Being Mixins, they can themselves be overridden in concrete
applications, but this is not recommended except for quick bug fixing.


Mixin.WmsSingleGoodsOperation: working on a single Goods record
---------------------------------------------------------------

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.on_goods.WmsSingleGoodsOperation


   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: goods
   .. autoattribute:: quantity
   .. autoattribute:: orig_goods_dt_until

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Implemented subset of the operation subclass API</h4>

   .. automethod:: find_parent_operations
   .. automethod:: check_create_conditions
   .. automethod:: check_execute_conditions


Mixin.WmsMultipleGoodsOperation: working on several Goods records
-----------------------------------------------------------------

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.on_goods.WmsMultipleGoodsOperation

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: goods

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Specific methods</h4>

   .. automethod:: iter_goods_original_reasons
   .. automethod:: reset_goods_original_reasons

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Implemented subset of the operation subclass API</h4>

   .. automethod:: find_parent_operations
   .. automethod:: check_create_conditions
   .. automethod:: check_execute_conditions

Mixin.WmsSingleGoodsSplitterOperation: splitting, then working on a Goods Record
--------------------------------------------------------------------------------

.. note:: will maybe be moved to another Blok or even Python project
          (see also :ref:`improvement_no_quantities`)

This one inherits from :class:`WmsSingleGoodsOperation <anyblok_wmss_base.bloks.wms_core.operation.on_goods.WmsSingleGoodsOperation>`

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.splitter.WmsSingleGoodsSplitterOperation

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: partial

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Mandatory API for inheritors</h4>

   .. automethod:: execute_planned_after_split

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Implemented subset of the operation subclass API</h4>

   (we list only those methods that override the base classes).

   .. automethod:: create
   .. automethod:: check_execute_conditions
   .. automethod:: execute_planned

