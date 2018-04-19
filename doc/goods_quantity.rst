.. _goods_quantity:

Quantities on Goods records
===========================

The optional ``wms-quantity`` Blok adds a ``quantity`` field on the
``Wms.Goods`` model, and brings the corresponding logic.

With the ``quantity`` field, Gods record represents a certain amount
of goods that are otherwise indistinguishable, for all the intents and
purposes the WMS is used for.


.. seealso:: The :ref:`original thoughts <improvement_no_quantities>`
             that led to the separation of the ``quantity`` field from
             ``wms-core``.

Use cases
~~~~~~~~~

Goods handled in bulk
---------------------

The ``quantity`` field is necessary for goods handled in bulk, since
the quantity in reality is variable.

We don't use a notion of unit of measure, as we feel it to be too much
a source of complication with few benefits. Therefore, the unit of
measure is morally part of the Goods Type, which will represent for instance
"Bulk sand, in metric tons".

Goods handled as units
----------------------

For goods that are to be handled as *units* (e.g, a bottle of milk, a
50kg bag of sand…), the obvious and only benefits of this ``quantity`` field in these use cases
are that we can represent many identical such units with a single
line in the database.

But these benefits are severely impaired by the need to perform and
record many Splits, unless it's so much common to handle several of
them together *and not as some kinds of bigger packs*, such as
pallets or containers that it counterbalances the overhead of all
those Splits.

The database lightneding can also be impaired by traceability
requirements. For instance,
if they induce a great variability in related properties.
In the extreme case, if we track serial numbers for all goods, then
we'll end up with each Goods record having ``quantity=1``.

Goods with and without quantities
---------------------------------
If the application tracks but one bulk Goods Type, it becomes
necessary to install ``wms-quantity``, however many other Goods Type
there are.

This is not an issue, as Goods record with ``quantity=1``, when
handled through Operations having also ``quantity=1`` will behave as
if the quantity field wasn't there in the first place.

Applicative code written without the ``quantity`` field should not require
a rewrite, since it defaults to ``1``, for the ``Goods`` record
as well as for the :ref:`splitter operations <splitter_ops>`.

Operations and quantity
~~~~~~~~~~~~~~~~~~~~~~~
The ``wms-quantity`` blok introduces the Split and Aggregate
Operations, it also makes enhances some Operations with a ``quantity``
field and automatic Splits.

.. _op_split_aggregate:

Split and Aggregate
-------------------
.. note:: This is an overview, see the code documentation for
          :class:`Split
          <anyblok_wms_base.bloks.wms_quantity.operation.split.Split>` and
          :class:`Aggregate
          <anyblok_wms_base.bloks.wms_quantity.operation.aggregate.Aggregate>`
          for more details.

A Split replaces one record of Goods with two identical ones, keeping
the overall total quantity.

According to behaviours on the Goods Type, they are *formal* (have no
counterpart in reality) or *physical*. In the latter case, they can be
reversible or not, again according to behaviours.

Aggregates are the converse of Splits, and both are always reversible
in the sense of :ref:`op_cancel_revert_obliviate`.

.. _splitter_ops:

Splitter operations
-------------------

``wms-quantity`` overrides some Operations by making them inherit from
the ``WmsSplitterOperation`` Mixin. This enhances them with a
``quantity`` field and automatically inserts a Split if and only if
that quantity is less than the Goods record's.

As of this writing, the affected operations are:

* :ref:`Move <op_move>`
* :ref:`Unpack <op_unpack>`
* :ref:`Departure <op_departure>`

Operations defined in downstream libraries or end applications can
also inherit the mixin and behave in the same way.

Drawbacks
~~~~~~~~~

* More complexity, so ``wms-quantity`` shouldn't be installed if not
  really needed.

* Goods with quantities break the intent for the Goods record to
  represent the "physical continuity" of the goods, since Splits
  create new Goods records, even though the goods themselves haven't
  changed in reality.

* Somewhat related with the previous point is that ``wms-quantity`` is
  at this stage mostly incompatible with
  ``wms-reservation``, for which it is really convenient to reserve
  whole lines. The obvious solution to this would be to introduce Splits
  before reserving, but don't play well with the efficiency goals of
  :ref:`reserver services <arch_reserver>`, and can be a major source
  of database contention.
