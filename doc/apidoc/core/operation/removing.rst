Removing Operations
~~~~~~~~~~~~~~~~~~~
These operations take some :ref:`Avatars <physobj_avatar>` as inputs,
and have no outcomes.

Of course, since Anyblok / Wms Base keeps the full history,
technically, the incoming Avatars are not removed from the database.
Rather, their :attr:`state
<anyblok_wms_base.core.goods.goods.state>` field
is being set to ``past`` during execution.

Model.Wms.Operation.Departure
-----------------------------

.. show-inheritance is useles, as it displays the assembled class
   (within the anyblok.mixin virtual namespace), that can't be linked

.. autoclass:: anyblok_wms_base.core.operation.departure.Departure
   :members:
   :undoc-members:

Model.Wms.Operation.Disparition
-------------------------------

.. autoclass:: anyblok_wms_base.core.operation.disparition.Disparition

   .. raw:: html

      <h3>Fields and their semantics</h3>

   .. autoattribute:: id

   .. raw:: html

      <h3>Mandatory methods of Operation subclasses</h3>

   .. automethod:: check_create_conditions
   .. automethod:: after_insert

