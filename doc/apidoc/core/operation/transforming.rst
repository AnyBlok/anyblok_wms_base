Handling and transforming Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. py:currentmodule:: anyblok_wms_base.core.operation

Model.Wms.Operation.Move
------------------------

This Operation Model inherits from :class:`Mixin.WmsSingleInput
<anyblok_wms_base.core.operation.single_input.WmsSingleInputOperation>`

.. autoclass:: anyblok_wms_base.core.operation.move.Move

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: destination

   .. raw:: html

      <h3>Specific members</h3>

   .. automethod:: revert_extra_fields

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: after_insert
   .. automethod:: execute_planned
   .. automethod:: is_reversible
   .. automethod:: plan_revert_single

   .. raw:: html

      <h3>Overridden methods of Operation</h3>

   .. automethod:: check_create_conditions

Model.Wms.Operation.Teleportation
---------------------------------

This Operation Model inherits from :class:`Mixin.WmsSingleInput
<anyblok_wms_base.core.operation.single_input.WmsSingleInputOperation>`

.. autoclass:: anyblok_wms_base.core.operation.teleportation.Teleportation

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: new_location

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: check_create_conditions
   .. automethod:: after_insert

   .. raw:: html

      <h3>Overridden methods of Operation</h3>

   .. automethod:: check_create_conditions

Model.Wms.Operation.Observation
-------------------------------
This Operation Model inherits from :class:`Mixin.WmsSingleInput
<anyblok_wms_base.core.operation.single_input.WmsSingleInputOperation>`

.. autoclass:: anyblok_wms_base.core.operation.observation.Observation

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: name
   .. autoattribute:: observed_properties
   .. autoattribute:: required_properties
   .. autoattribute:: previous_properties
   .. autoattribute:: id

   .. raw:: html

      <h3>Overridden methods of Operation</h3>
   .. automethod:: obliviate_single
   .. automethod:: is_reversible
   .. automethod:: plan_revert_single

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: after_insert
   .. automethod:: execute_planned

   .. raw:: html

      <h3>Specific members</h3>

   .. automethod:: apply_properties

Model.Wms.Operation.Unpack
--------------------------
This Operation Model inherits from :class:`Mixin.WmsSingleInput
<anyblok_wms_base.core.operation.single_input.WmsSingleInputOperation>`


.. autoclass:: anyblok_wms_base.core.operation.unpack.Unpack

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id

   .. raw:: html

      <h3>Specific members</h3>

   .. automethod:: get_outcome_specs
   .. automethod:: outcome_props_update
   .. automethod:: create_unpacked_goods
   .. automethod:: plan_for_outcomes

   .. raw:: html

      <h3>Overridden methods of Operation</h3>
   .. automethod:: check_create_conditions
   .. automethod:: cancel_single

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: after_insert
   .. automethod:: execute_planned


Model.Wms.Operation.Assembly
----------------------------

.. py:currentmodule:: anyblok_wms_base.core.operation.assembly

.. autoclass:: anyblok_wms_base.core.operation.assembly.Assembly

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: outcome_type
   .. autoattribute:: name
   .. autoattribute:: parameters
   .. autoattribute:: match

   .. raw:: html

      <h3>Specific members</h3>

   .. autoattribute:: specification
   .. autoattribute:: DEFAULT_FOR_CONTENTS
   .. autoattribute:: SPEC_LIST_MERGE
   .. automethod:: outcome_properties
   .. automethod:: eval_typed_expr
   .. automethod:: specific_outcome_properties
   .. autoattribute:: props_hook_fmt

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: check_create_conditions
   .. automethod:: after_insert
   .. automethod:: execute_planned
