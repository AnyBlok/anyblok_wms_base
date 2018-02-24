# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import CheckConstraint

from anyblok import Declarations
from anyblok.column import String
from anyblok.column import Selection
from anyblok.column import Integer
from anyblok.column import DateTime
from anyblok.column import Decimal
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb

from anyblok_wms_base.constants import (
    GOODS_STATES,
    SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR
)


register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Goods:
    """Main data type to represent physical objects managed by the system.

    This represents a certain amount (:attr:`quantity`) of indistinguishable
    goods, for all the intents and purposes the WMS is used for.

    Fields semantics:

    .. note:: the ``quantity`` field may vanish from ``wms-core`` in the
              future, see :ref:`improvement_no_quantities`

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

          The :meth:`set_property` takes implements the necessary Copy-on-Write
          mechanism to avoid unintentionnally modify the properties of many
          Goods records.
    - state:
          see :mod:`anyblok_wms_base.constants`
    - reason:
          this records the Operation that is responsible for the current
          values of the Goods record, including its state. In practice it is
          simply the latest Operation that did anything to these Goods.
    - dt_from:
          This represents the starting date and time
          of presence of the goods at this location (TODO really make this
          Move story uniform and accept the price in volumetry), but the
          meaning really depends on the value of the ``state`` field:

          + In the ``past`` and ``present`` states, this is supposed to be
            a faithful representation of reality.

          + In the ``future`` state, this is completely theoretical, and
            ``wms-core`` doesn't do much about it, besides using it to avoid
            counting several :ref:`goods_avatar` of the same physical goods
            while :meth:`peeking at quantities in the future
            <anyblok_wms_base.bloks.wms_core.location.Location.quantity>`.
            If the end application does serious time prediction, it can use it
            freely
    - dt_until:
          This represents the ending date and time
          of presence of the goods at this location (TODO really make this
          Move story uniform and accept the price in volumetry).

          Like ``dt_from``, the meaning vary according to the value of state:

          + In the ``past`` state, this is supposed to be a faithful
            representation of reality: apart from the special case of formal
            :ref:`Splits and Aggregates <op_split_aggregate>`, the goods
            really left this location at these date and time.

          + In the ``present`` and ``future`` states, this is purely
            theoretical, and the same remarks as for the ``dt_from`` field
            apply readily.

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

    """
    type = Many2One(model='Model.Wms.Goods.Type', nullable=False, index=True)
    id = Integer(label="Identifier", primary_key=True)
    quantity = Decimal(label="Quantity")
    code = String(label="Identifying code",
                  index=True)
    # TODO consider switch to Enum
    state = Selection(label="State of existence",
                      selections=GOODS_STATES,
                      nullable=False,
                      index=True)
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

    dt_from = DateTime(label="Exist (or will) from this date & time",
                       nullable=False)
    """DateTime from which the Goods exist with the given location and state.

    Functionally, even though the default in creating Operations will be
    to use the current date and time, this is not to be confused with the
    time of creation in the database, which we don't care much about.

    Timestamps tend to be very precise, but for the sake of completeness,
    let's mention here that is is inclusive.
    """

    dt_until = DateTime(label="Exist (or will) until this date & time")
    """DateTime until which the Goods exist with the given location and state.

    Timestamps tend to be very precise, but for the sake of completeness,
    let's mention here that is is exclusive.
    """

    @classmethod
    def define_table_args(cls):
        return super(Goods, cls).define_table_args() + (
            CheckConstraint('quantity > 0', name='positive_qty'),
        )

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

        See remarks on :meth:`get_property`.

        This method implements a simple Copy-on-Write mechanism. Namely,
        if the properties are referenced by other Goods records, it
        will duplicate them before actually setting the wished value.
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

    Goods Types have a flexible (JSONB) :attr:`behaviours` field, whose main
    purpose is to specify how various Operations will treat the represented
    Goods.

    Notably, the behaviours specify whether
    :class:`Split <.operation.split.Split>` and
    :class:`Aggregate <.operation.aggregate.Aggregate>` Operations are physical
    (represent something happening in reality), and if that's the case if they
    are reversible, using``{"reversible": true}``, defaulting to ``false``,
    in the ``split`` and ``aggregate`` behaviours, respectively.

    We don't want to impose reversibility to be equal for both directions,
    as we don't feel confident it would be true in all use cases (it is indeed
    in the ones presented below).

    Reality of Split and Aggregate and their reversibilitues can be queried
    using :meth:`are_split_aggregate_physical`,
    :meth:`is_split_reversible` and :meth:`is_aggregate_reversible`

    Use cases:

    * if the represented goods come as individual pieces in reality, then all
      quantities are integers, and there's no difference in reality
      between N>1 records of a given Goods Type with quantity=1 having
      identical properties and locations on one hand, and a
      record with quantity=N at the same location with the same properties, on
      the other hand.

      .. note:: This use case is so frequent that we are considering moving
                all notions of quantities together with Split and Aggregate
                Operations out of ``wms-core`` in a separate Blok.

                See :ref:`improvement_no_quantities` for more on this.

    * if the represented goods are meters of wiring, then Splits are physical,
      they mean cutting the wires, but Aggregates probably can't happen
      in reality, and therefore Splits are irreversible.
    * if the represented goods are kilograms of sand, kept in bulk,
      then Splits mean in reality shoveling some out of, while Aggregates mean
      shoveling some in (associated with Move operations, obviously).
      Both operations are certainly reversible in reality.

    """
    id = Integer(label="Identifier", primary_key=True)
    code = String(label=u"Identifying code", index=True)
    label = String(label=u"Label")
    behaviours = Jsonb(label="Behaviours in operations")

    def __str__(self):
        return "(id={self.id}, code={self.code!r})".format(self=self)

    def __repr__(self):
        return "Wms.Goods.Type" + str(self)

    def get_behaviour(self, key, default=None):
        """Get the value of the behaviour with given key.

        This is shortcut to avoid testing over and over if :attr:`behaviours`
        is ``None``.
        """
        behaviours = self.behaviours
        if behaviours is None:
            return default
        return behaviours.get(key, default)

    def are_split_aggregate_physical(self):
        """Tell if Split and Aggregate operations are physical.

        By default, these operations are considered to be purely formal,
        but a behaviour can be set to specify otherwise. This has impact
        at least on reversibility.

        Downstream libraries and applications should use
        :const:`SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR` as this behaviour name.

        :returns bool: the answer.
        """
        return self.get_behaviour(SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR, False)

    def _is_op_reversible(self, op_beh):
        """Common impl for question about reversibility of some operations.

        :param op_beh: name of the behaviour for the given operation
        """
        if not self.are_split_aggregate_physical():
            return True
        split = self.get_behaviour(op_beh)
        if split is None:
            return False
        return split.get('reversible', False)

    def is_split_reversible(self):
        """Tell whether :class:`Split <.operation.split.Split>` can be reverted
        for this Goods Type.

        By default, the Split Operation is considered to be formal,
        hence the result is ``True``. Otherwise, that depends on the
        ``reversible`` flag in the ``split`` behaviour.

        :returns bool: the answer.
        """
        return self._is_op_reversible('split')

    def is_aggregate_reversible(self):
        """Tell whether :class:`Aggregate <.operation.aggregate.Aggregate>`
        can be reverted for this Goods Type.

        By default, Aggregate is considered to be formal, hence the result is
        ``True``. Otherwise, that depends on the ``reversible`` flag in the
        ``aggregate`` behaviour.

        :returns bool: the answer.
        """
        return self._is_op_reversible('aggregate')


@register(Model.Wms.Goods)
class Properties:
    """Properties of Goods.

    This is kept in a separate Model and table for the following reasons:

    - properties are typically seldom written, whereas the columns directly
      present on Goods are often written, and we want these latter writes
      to be as fast as possible
    - in some cases, it can useful to share properties across items, either
      because some sets of properties are in real life indeed identical for
      large counts of items lines, or to take 'future' items into account.

    The :attr:`flexible` field is expected to be a mapping, whose key/values
    ``wms_core`` will consider to be property names and values.
    Namely, all property operations defined in the core will handle the
    properties by name, and be indifferent of the values.

    Applications are welcome to overload this model to add new fields rather
    than storing their meaningful information in the ``flexible`` JSONB field,
    if it has added value for performance or programmming tightness reasons.
    This has the obvious drawback of defining some properties for all Goods,
    regardless of their Types, so it should not be abused.

    On :class:`Goods`, the ``get_property``/``set_property`` API will treat
    direct fields and top-level keys of ``flexible`` in the same way, meaning
    that, as long as all pieces of code use only this API to handle properties,
    flexible keys can be replaced with fields transparently at any time
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
        """Insert a copy of ``self`` and return its id."""
        fields = {k: getattr(self, k)
                  for k in self.fields_description().keys()
                  }
        fields.pop('id')
        return self.insert(**fields)

    @classmethod
    def create(cls, **props):
        """Direct creation.

        The caller doesn't have to care about which properties get stored as
        columns or in the :attr:`flexible` field.

        This method is a better alternative than
        insertion followed by calls to :meth:`set`, because it guarantees that
        only one SQL INSERT will be issued.
        """
        fields = cls.fields_description()
        columns = {}
        flexible = {}
        forbidden = ('id', 'flexible')
        for k, v in props.items():
            if k in forbidden:
                raise ValueError(
                    "The key %r is reserved, and can't be used as "
                    "a property key" % k)
            if k in fields:
                columns[k] = v
            else:
                flexible[k] = v
        return cls.insert(flexible=flexible, **columns)
