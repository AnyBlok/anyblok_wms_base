core.goods
==========
.. py:module:: anyblok_wms_base.core.goods.goods

Model.Wms.PhysObj
~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.core.goods.goods.PhysObj

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: type
   .. autoattribute:: properties

   .. raw:: html

      <h3>Type methods</h3>

   .. automethod:: has_type

   .. raw:: html

      <h3>Property methods</h3>

   .. automethod:: get_property
   .. automethod:: merged_properties
   .. automethod:: has_property
   .. automethod:: has_properties
   .. automethod:: has_property_values
   .. automethod:: set_property
   .. automethod:: update_properties

   .. raw:: html

      <h3>Containers methods</h3>

   .. automethod:: flatten_containers_subquery

Model.Wms.PhysObj.Type
~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.core.goods.type.Type

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: code
   .. autoattribute:: behaviours

   .. raw:: html

      <h3>Methods</h3>

   .. automethod:: get_behaviour


Model.Wms.PhysObj.Properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

Model.Wms.PhysObj.Avatar
~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: anyblok_wms_base.core.goods.goods.Avatar

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: location
   .. autoattribute:: state
   .. autoattribute:: reason
   .. autoattribute:: dt_from
   .. autoattribute:: dt_until
