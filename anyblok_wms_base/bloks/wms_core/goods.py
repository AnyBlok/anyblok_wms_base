# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok import Declarations
from anyblok.column import String
from anyblok.column import Selection
from anyblok.column import Integer
from anyblok.column import Decimal
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb

from anyblok_wms_base.constants import GOODS_STATES

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Goods:
    """Main data type to represent physical objects managed by the system.

    This represents a certain amount (``quantity``) of indistinguishable goods,
    for all the intents and purposes the WMS is used for.

    - properties:
          Besides its main columns meant to represent handling by the Wms Base
          modules, this model has a flexible model of data, that can be
          handled through the :meth:`get_property` and :meth:`set_property`
          methods.

          As far as ``wms_core`` is concerned, properties can be anything,
          yet downstream applications and libraries can decide whether to
          describe them in the database schema or not.

          Technically, this data is deported into the :class:`Properties`
          Model (see there on how to add additional properties). The properties
          column value can be None, so that we don't pollute the database with
          empty lines of Property records, although this is subject to change
          in the future.
    - state:
          see :mod:`constants`
    - reason:
          this records the Operation that is responsible for the current
          values of the Goods record, including its state
    - quantity:
          this has been defined as Decimal to cover a broad scope of
          applications. However, for performance reasons, applications are
          free to overload this column with other numeric types (i.e.,
          supporting transparently all the usual operations with the same
          syntax, both in Python and SQL).
          Examples :

          + applications not caring about fractional quantities
            might want to overload this column with an Integer column for
            extra performance (if that really makes a difference).

          + applications having to deal with fractional quantities not well
            behaved in decimal notation (e.g., thirds of cherry pies)
            may want to switch to a rational number type, such as ``mpq``
            type on the PostgreSQL side), although it's probably a better idea
            if there's an obvious common denominator to just use integers
            (following on the example, simply have goods types representing
            those thirds of pies alongside those representing the whole pies,
            and represent the first cutting of a slice as an
            unpacking operation)

    TODO: add indexes and constraints
    """
    type = Many2One(model='Model.Wms.Goods.Type', nullable=False)
    id = Integer(label="Identifier", primary_key=True)
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint
    code = String(label="Identifying code")  # TODO index
    # TODO consider switch to Enum
    state = Selection(label="State of existence",
                      selections=GOODS_STATES,
                      )
    properties = Many2One(label="Properties",
                          model='Model.Wms.Goods.Properties')
    location = Many2One(model=Model.Wms.Location, nullable=False)
    reason = Many2One(label="The operation that is the reason why "
                      "these goods are here",
                      model=Model.Wms.Operation, nullable=False)

    def get_property(self, k):
        """Property getter.

        API: same as a ``get()`` on a dict.

        Actually I'd prefer to simply implement the dict API, but we can't
        direcly inherit from UserDict yet. This is good enough to provide
        the abstraction needed for current internal wms_core calls.
        """
        if self.properties is None:
            return None

        return self.properties.get(k)

    def set_property(self, k, v):
        """Property setter.

        See remarks on :meth:`get_property`1
        """
        if self.properties is None:
            self.properties = self.registry.Wms.Goods.Properties(
                flexible=dict())
        return self.properties.set(k, v)


@register(Model.Wms.Goods)
class Type:
    """Types of Goods.

    Applications or downstream libraries may want to tie them (typically as a
    Many2One relationship) to a broader notion of "product", but we
    don't assume one in the ``anyblok_wms``.

    You may think of these types of goods as encoding all the informations
    expected of "products" for logistics purposes. This can be both more
    and less than a general purpose "product" might convey.

    For instance, if the overall environment has a notion of a ham product,
    you should consider whole hams,
    5-slice vaccuum packs, crates and pallets of the latter to be all different
    Goods Types, with potential packing/unpacking Operations.
    On the other hand, there's usually no point attaching pictures on
    Goods Types.
    """
    id = Integer(label="Identifier", primary_key=True)
    label = String(label=u"Label")
    behaviours = Jsonb(label="Behaviours in operations")


@register(Model.Wms.Goods)
class Properties:
    """Properties of goods.

    This is kept in a separate model/table for the following reasons:

    - properties are typically seldom written, whereas the columns directly
      present on Goods are often written, and we want these latter writes
      to be as fast as possible
    - in some cases, it can useful to share properties across items, either
      because some sets of properties are in real life indeed identical for
      large counts of items lines, or to take 'future' items into account.

    The ``flexible`` JSONB column is expected to be a mapping, whose key/values
    ``anyblok_wms_core`` will consider to be property names and values.
    Namely, all property operations defined in the core will handle the
    properties by name, and be indifferent of the values.


    Applications are welcomed to overload this model to add new columns rather
    than storing their meaningful information in the ``flexible`` JSONB column,
    if it has added value for performance or programmming tightness reasons,
    but must in that case take care that all operations are modified to
    handle the new columns properly. We'll try and provide helping mechanisms
    in the core to that effect, but that's vaporware for the time being.
    """
    id = Integer(label="Identifier", primary_key=True)
    flexible = Jsonb(label="Flexible properties")

    def get(self, k):
        # TODO non-flexible props (direct columns)
        return self.flexible.get(k)

    def set(self, k, v):
        # TODO non-flexible props (direct columns)
        self.flexible[k] = v
