Transforming Operations
~~~~~~~~~~~~~~~~~~~~~~~
.. py:currentmodule:: anyblok_wms_base.bloks.wms_core.operation

ModelWms.Operation.Move
-----------------------
This Operation Model inherits from :class:`WmsSplitter
<.splitter.WmsSplitterOperation>`

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.move.Move
   :members:
   :undoc-members:

Model.Wms.Operation.Unpack
--------------------------
This Operation Model inherits from :class:`WmsSplitter
<.splitter.WmsSplitterOperation>`

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.unpack.Unpack
   :members:
   :undoc-members:

Model.Wms.Operation.Split
-------------------------

This Operation Model inherits from :class:`WmsSingleGoods
<.on_goods.WmsSingleGoodsOperation>`

.. py:currentmodule:: anyblok_wms_base.bloks.wms_core.operation.split

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.split.Split

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
-----------------------------
This Operation Model inherits from :class:`WmsMultipleGoods
<.on_goods.WmsMultipleGoodsOperation>`

.. py:currentmodule:: anyblok_wms_base.bloks.wms_core.operation.aggregate

.. autoclass:: anyblok_wms_base.bloks.wms_core.operation.aggregate.Aggregate

   .. raw:: html

      <h3>Specific members</h3>

   .. autoattribute:: UNIFORM_GOODS_FIELDS
   .. autoattribute:: UNIFORM_AVATAR_FIELDS
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

