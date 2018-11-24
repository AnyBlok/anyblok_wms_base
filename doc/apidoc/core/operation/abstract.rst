Abstract classes
================

.. py:module:: anyblok_wms_base.core.operation

Fundamental Models
~~~~~~~~~~~~~~~~~~

Model.Wms.Operation
-------------------
.. autoclass:: anyblok_wms_base.core.operation.base.Operation

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
   .. automethod:: alter_destination

   .. raw:: html

      <h4>Mandatory API of subclasses</h4>


   These are the methods the concrete Operation subclasses must implement.

   .. note:: we provide helper Mixins to help reduce boilerplate and
             duplication.

   .. automethod:: after_insert
   .. automethod:: execute_planned
   .. automethod:: plan_revert_single
   .. automethod:: input_location_altered

   .. raw:: html

      <h4>Optional API of subclasses</h4>

   These methods have a default implementation in the base class, and
   are meant for the concrete Operation subclasses to override them if needed.

   .. autoattribute:: destination_field
   .. automethod:: is_reversible
   .. automethod:: check_create_conditions
   .. automethod:: check_execute_conditions
   .. automethod:: cancel_single
   .. automethod:: obliviate_single
   .. automethod:: before_insert

Model.Wms.Operation.HistoryInput
--------------------------------

.. autoclass:: anyblok_wms_base.core.operation.base.HistoryInput


   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: operation
   .. autoattribute:: avatar
   .. autoattribute:: orig_dt_until


Helper Mixin classes
~~~~~~~~~~~~~~~~~~~~

These implement a subset of the mandatory API for subclasses of
:class:`Operation <.base.Operation>`.

They tend to have long names because Anyblok does not have namespaces
for Mixins.

Being Mixins, they can themselves be overridden in concrete
applications, but this is not recommended except for quick bug fixing.


Mixin.WmsSingleInputOperation: working on a single input
--------------------------------------------------------

.. autoclass:: anyblok_wms_base.core.operation.single_input.WmsSingleInputOperation


   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: inputs_number
   .. autoattribute:: input

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Overrides of the base class.</h4>

   .. automethod:: create

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Specific methods.</h4>

   .. automethod:: refine_with_leading_move

Mixin.WmsSingleOutcomeOperation: producing only one outcome
-----------------------------------------------------------

.. autoclass:: anyblok_wms_base.core.operation.single_outcome.WmsSingleOutcomeOperation


   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Fields and their semantics</h4>

   .. autoattribute:: outcome

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Specific methods.</h4>

   .. automethod:: refine_with_trailing_move

Mixin.WmsInPlaceOperation: staying in the same location or container
--------------------------------------------------------------------

.. autoclass:: anyblok_wms_base.core.operation.in_place.WmsInPlaceOperation

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Specific methods.</h4>

   .. automethod:: unique_inputs_location

   .. raw:: html

      <h4 class="section" style="font-size: 160%">
            Overrides of the base class.</h4>

   .. automethod:: check_create_conditions
   .. automethod:: input_location_altered
