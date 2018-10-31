Creating Operations
~~~~~~~~~~~~~~~~~~~
These Operations have no inputs, and have one or several outcomes.

Model.Wms.Operation.Arrival
---------------------------
.. autoclass:: anyblok_wms_base.core.operation.arrival.Arrival

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: goods_type
   .. autoattribute:: goods_code
   .. autoattribute:: goods_properties

   .. raw:: html

      <h3>Specific attributes</h3>

   .. autoattribute:: inputs_number

   .. raw:: html

      <h3>Specific methods</h3>

   .. automethod:: refine_with_trailing_unpack

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: after_insert
   .. automethod:: execute_planned

   .. raw:: html

      <h3>Overridden methods of Operation</h3>

   .. automethod:: check_create_conditions

Model.Wms.Operation.Apparition
------------------------------
.. autoclass:: anyblok_wms_base.core.operation.apparition.Apparition

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id
   .. autoattribute:: quantity
   .. autoattribute:: location
   .. autoattribute:: goods_type
   .. autoattribute:: goods_code
   .. autoattribute:: goods_properties

   .. raw:: html

      <h3>Specific members</h3>

   .. autoattribute:: inputs_number

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: check_create_conditions
   .. automethod:: after_insert

   .. raw:: html

      <h3>Overridden methods of Operation</h3>

   .. automethod:: check_create_conditions
