Abstract classes
================

.. py:module:: anyblok_wms_base.bloks.wms_core.operation

Fundamental Models
~~~~~~~~~~~~~~~~~~

Model.Wms.Operation
-------------------
.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.base.Operation

   .. raw:: html

      <h4>Fields and their semantics</h4>

   .. autoattribute:: id
   .. autoattribute:: type
   .. autoattribute:: state
   .. autoattribute:: inputs
   .. autoattribute:: outcomes
   .. autoattribute:: follows
   .. autoattribute:: followers
   .. autoattribute:: dt_execution
   .. autoattribute:: dt_start

   .. raw:: html

      <h4>Main API</h4>

   These are the methods end applications and downstream libraries are
   supposed to use.

   .. automethod:: create
   .. automethod:: execute
   .. automethod:: cancel
   .. automethod:: plan_revert
   .. automethod:: obliviate

   .. raw:: html

      <h4>Mandatory API of subclasses</h4>


   These are the methods the concrete Operation subclasses must implement.

   .. note:: we provide helper Mixins to help reduce boilerplate and
             duplication.

   .. automethod:: after_insert
   .. automethod:: execute_planned
   .. automethod:: plan_revert_single

   .. raw:: html

      <h4>Optional API of subclasses</h4>


   These methods have a default implementation in the base class, and
   are meant for the concrete Operation subclasses to override them if needed.

   .. automethod:: is_reversible
   .. automethod:: check_create_conditions
   .. automethod:: check_execute_conditions
   .. automethod:: cancel_single
   .. automethod:: obliviate_single
   .. automethod:: before_insert

Model.Wms.Operation.HistoryInput
--------------------------------

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.base.HistoryInput


   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: operation
   .. autoattribute:: goods
   .. autoattribute:: latest_previous_op
   .. autoattribute:: orig_dt_until


Helper Mixin classes
~~~~~~~~~~~~~~~~~~~~

These implement a subset of the mandatory API for subclasses of
:class:`Operation <.base.Operation>`.

They tend to have long names because Anyblok does not have namespaces
for Mixins.

Being Mixins, they can themselves be overridden in concrete
applications, but this is not recommended except for quick bug fixing.


Mixin.WmsSingleInputOperation: working on a single Goods record
---------------------------------------------------------------

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.single_input.WmsSingleInputOperation


   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: inputs_number
   .. autoattribute:: input

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Overrides of the base class.</h4>

   .. automethod:: create


Mixin.WmsSplitterOperation: splitting, then working on a single Goods Record
----------------------------------------------------------------------------

.. note:: will maybe be moved to another Blok or even Python project
          (see also :ref:`improvement_no_quantities`)

This one inherits from :class:`WmsSingleGoodsOperation <anyblok_wmss_base.bloks.wms_core.operation.on_goods.WmsSingleGoodsOperation>`

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.splitter.WmsSplitterOperation

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: partial
   .. autoattribute:: quantity

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Mandatory API for inheritors</h4>

   .. automethod:: execute_planned_after_split

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Implemented subset of the operation subclass API</h4>

   (we list only those methods that override the base classes).

   .. automethod:: before_insert
   .. automethod:: check_execute_conditions
   .. automethod:: execute_planned

