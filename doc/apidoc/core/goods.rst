core.goods
==========
.. py:module:: anyblok_wms_base.core.goods.goods

Model.Wms.Goods
~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.core.goods.goods.Goods

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: type
   .. autoattribute:: properties

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: get_property
   .. automethod:: set_property


Model.Wms.Goods.Type
~~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.core.goods.type.Type

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: code
   .. autoattribute:: behaviours

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: is_sub_type
   .. automethod:: query_subtypes
   .. automethod:: get_behaviour
   .. automethod:: query_behaviour



Model.Wms.Goods.Properties
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.core.goods.goods.Properties

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

Model.Wms.Goods.Avatar
~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.core.goods.goods.Avatar

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: location
   .. autoattribute:: state
   .. autoattribute:: reason
   .. autoattribute:: dt_from
   .. autoattribute:: dt_until
