# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy.orm.attributes import flag_modified

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
    type = Many2One(model='Model.Wms.Goods.Type', nullable=False, index=True)
    id = Integer(label="Identifier", primary_key=True)
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint
    code = String(label="Identifying code",
                  index=True)
    # TODO consider switch to Enum
    state = Selection(label="State of existence",
                      # TODO nullable=False
                      selections=GOODS_STATES,
                      index=True,
                      )
    properties = Many2One(label="Properties",
                          index=True,
                          model='Model.Wms.Goods.Properties')
    location = Many2One(model=Model.Wms.Location,
                        nullable=False,
                        index=True)
    reason = Many2One(label="The operation that is the reason why "
                      "these goods are here",
                      index=True,
                      model=Model.Wms.Operation, nullable=False)

    def __str__(self):
        return ("(id={self.id}, state={self.state!r}, "
                "type={self.type})".format(self=self))

    def __repr__(self):
        return ("Wms.Goods(id={self.id}, state={self.state!r}, "
                "type={self.type!r})".format(self=self))

    def get_property(self, k, default=None):
        """Property getter.

        API: same as a ``get()`` on a dict.

        Actually I'd prefer to simply implement the dict API, but we can't
        direcly inherit from UserDict yet. This is good enough to provide
        the abstraction needed for current internal wms_core calls.
        """
        if self.properties is None:
            return default

        return self.properties.get(k, default)

    def set_property(self, k, v):
        """Property setter.

        See remarks on :meth:`get_property`
        """
        existing_props = self.properties
        if existing_props is None:
            self.properties = self.registry.Wms.Goods.Properties(
                flexible=dict())
        elif existing_props.get(k) != v:
            cls = self.__class__
            if cls.query(cls.id).filter(
                    cls.properties == existing_props,
                    cls.id != self.id).limit(1).count():
                self.properties = existing_props.duplicate()
        self.properties.set(k, v)


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
    code = String(label=u"Identifying code", index=True)
    label = String(label=u"Label")
    behaviours = Jsonb(label="Behaviours in operations")

    def __str__(self):
        return "(id={self.id}, code={self.code!r})".format(self=self)

    def __repr__(self):
        return "Wms.Goods.Type" + str(self)


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
    if it has added value for performance or programmming tightness reasons.

    On :class:`Goods`, the ``get_property``/``set_property`` API will treat
    direct columns and top-level keys of ``flexible`` in the same way, meaning
    that, as long as all pieces of code use only this API to handle properties,
    flexible keys can be replaced with columns transparently at any time
    (assuming of course that any existing data is properly migrated to the new
    schema)
    """
    id = Integer(label="Identifier", primary_key=True)
    flexible = Jsonb(label="Flexible properties")

    def get(self, k, default=None):
        if k in self.loaded_columns:
            return getattr(self, k)
        return self.flexible.get(k, default)

    def set(self, k, v):
        if k in ('id', 'flexible'):
            raise ValueError("The key %k is reserved, and can't be used for "
                             "properties" % k)
        if k in self.fields_description():
            setattr(self, k, v)
        else:
            self.flexible[k] = v
            flag_modified(self, '__anyblok_field_flexible')

    def duplicate(self):
        fields = {k: getattr(self, k)
                  for k in self.fields_description().keys()
                  }
        fields.pop('id')
        return self.insert(**fields)
