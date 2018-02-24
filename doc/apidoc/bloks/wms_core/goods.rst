wms_core.goods
==============
.. py:module:: anyblok_wms_base.bloks.wms_core.goods

Model.Wms.Goods
~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.bloks.wms_core.goods.Goods

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: type
   .. autoattribute:: properties
   .. autoattribute:: location
   .. autoattribute:: state
   .. autoattribute:: reason
   .. autoattribute:: quantity
   .. autoattribute:: dt_from
   .. autoattribute:: dt_until

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: get_property
   .. automethod:: set_property


Model.Wms.Goods.Type
~~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.bloks.wms_core.goods.Type

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: code
   .. autoattribute:: behaviours

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: get_behaviour
   .. automethod:: are_split_aggregate_physical
   .. automethod:: is_split_reversible
   .. automethod:: is_aggregate_reversible


Model.Wms.Goods.Properties
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.bloks.wms_core.goods.Properties

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: flexible

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: create
   .. automethod:: duplicate
   .. automethod:: get
   .. automethod:: set
