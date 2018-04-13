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
from anyblok.column import DateTime
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

    Forgetting quantities for a while, the instances of this model are also
    the ultimate representation of the Goods "staying the same" or "becoming
    different" under the Operations, which is, ultimately, a subjective
    decision that has to be left to downstream libraires and applications, or
    even end users.

    For instance, everybody agrees that moving something around does not make
    it different. Therefore, the Move Operation uses the same Goods record
    in its outcome as in its input.
    On the other hand, changing a property could be considered enough an
    alteration of the physical object to consider it different, or not (think
    of recording some measurement that had not be done earlier.)
    """
    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    type = Many2One(model='Model.Wms.Goods.Type', nullable=False, index=True)
    """The :class:`Goods Type <.Type>`"""

    code = String(label="Identifying code",
                  index=True)
    """Uniquely identifying code.

    This should be about what one is ready to display as a barcode for handling
    the Goods. It's also meant to be shared with other applications if needed
    (rather than ids which are only locally unique).
    """

    properties = Many2One(label="Properties",
                          index=True,
                          model='Model.Wms.Goods.Properties')
    """Link to :class:`Properties`.

    .. seealso:: :ref:`goods_properties` for functional aspects.

    .. warning:: don't ever mutate the contents of :attr:`properties` directly,
                 unless what you want is precisely to affect all the Goods
                 records that use them directly.

    Besides their :attr:`type` and the fields meant for the Wms Base
    bloks logic, the Goods Model bears flexible data,
    called *properties*, that are to be
    manipulated as key/value pairs through the :meth:`get_property` and
    :meth:`set_property` methods.

    As far as ``wms_core`` is concerned, values of properties can be of any
    type, yet downstream applications and libraries can choose to make them
    direct fields of the :class:`Properties` model.

    Properties can be shared among several Goods records, for efficiency.
    The :meth:`set_property` implements the necessary Copy-on-Write
    mechanism to avoid unintentionnally modify the properties of many
    Goods records.

    Technically, this data is deported into the :class:`Properties`
    Model (see there on how to add additional properties). The properties
    column value can be None, so that we don't pollute the database with
    empty lines of Property records, although this is subject to change
    in the future.
    """

    def __str__(self):
        return "(id={self.id}, type={self.type})".format(self=self)

    def __repr__(self):
        return "Wms.Goods(id={self.id}, type={self.type!r})".format(self=self)

    def get_property(self, k, default=None):
        """Property getter, works like :meth:`dict.get`.

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

    For a full functional discussion, see :ref:`goods_type`.
    """
    id = Integer(label="Identifier", primary_key=True)
    """Primary key"""

    code = String(label=u"Identifying code", index=True)
    """Uniquely identifying code.

    As a convenience, and for sharing with other applications.
    """

    label = String(label=u"Label")

    behaviours = Jsonb(label="Behaviours in operations")
    """
    Goods Types specify with this flexible field how various :class:`Operations
    <.operation.base.Operation>` will treat the represented Goods.

    .. seealso:: :class:`Unpack <.operation.unpack.Unpack>` for a complex
                 example.

    The value is a key/value mapping.

    This field is also open for downstream libraries and applications to
    make use of it to define some of their specific logic, but care must be
    taken not to conflict with the keys used by ``wms-core`` and other bloks
    (TODO introduce namespacing, then ? at least make a list available by
    using constants from an autodocumented module)

    As a special case, the behaviours specify whether
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

    This is kept in a separate Model (and SQL table) to provide sharing
    among several :class:`Goods` instances, as they can turn out to be
    identical for a large number of them.

    Use-case: receive a truckload of milk bottles that all have the same
    expiration date, and unpack everything down to the bottles. The expiration
    date would be stored in a single Properties instance, assuming there aren't
    also non-uniform properties to store, of course.

    Applications are welcome to overload this model to add new fields rather
    than storing their meaningful information in the :attr:`flexible` field,
    if it has added value for performance or programmming tightness reasons.
    This has the obvious drawback of defining some properties for all Goods,
    regardless of their Types, so it should not be abused.

    On :class:`Goods`, the :meth:`get_property <Goods.get_property>` /
    :meth:`set_property <Goods.set_property>` API will treat
    direct fields and top-level keys of :attr:`flexible` uniformely,
    that, as long as all pieces of code use only this API to handle properties,
    flexible keys can be replaced with proper fields transparently at any time
    in the development of downstream applications and libraries
    (assuming of course that any existing data is properly migrated to the new
    schema).
    """
    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    flexible = Jsonb(label="Flexible properties")
    """Flexible properties.

    The value is expected to be a mapping, and all property handling
    operations defined in the ``wms-core`` will handle the properties by key,
    while being indifferent of the values.

    .. note:: the core also makes use of a few special properties, such as
              ``unpack_outcomes``. TODO make a list, in the form of
              constants in a module
    """

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
        direct fields or in the :attr:`flexible` field.

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


@register(Model.Wms.Goods)
class Avatar:
    """Goods Avatar.

    See in :ref:`Core Concepts <goods_avatar>` for a functional description.
    """

    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    goods = Many2One(model=Model.Wms.Goods,
                     index=True,
                     nullable=False)
    """The Goods of which this is an Avatar."""

    state = Selection(label="State of existence",
                      selections=GOODS_STATES,
                      nullable=False,
                      index=True)
    """State of existence in the premises.

    see :mod:`anyblok_wms_base.constants`.

    This may become an ENUM once Anyblok supports them.
    """

    location = Many2One(model=Model.Wms.Location,
                        nullable=False,
                        index=True)
    """Where the Goods are/will be/were.

    See :class:`.location.Location` for a discussion of what this should
    actually mean.
    """

    dt_from = DateTime(label="Exist (or will) from this date & time",
                       nullable=False)
    """Date and time from which the Avatar is meaningful, inclusively.

    Functionally, even though the default in creating Operations will be
    to use the current date and time, this is not to be confused with the
    time of creation in the database, which we don't care much about.

    The actual meaning really depends on the value of the :attr:`state`
    field:

    + In the ``past`` and ``present`` states, this is supposed to be
      a faithful representation of reality.

    + In the ``future`` state, this is completely theoretical, and
      ``wms-core`` doesn't do much about it, besides using it to avoid
      counting several :ref:`goods_avatar` of the same physical goods
      while :meth:`peeking at quantities in the future
      <anyblok_wms_base.bloks.wms_core.location.Location.quantity>`.
      If the end application does serious time prediction, it can use it
      freely.

    In all cases, this doesn't mean that the very same Goods aren't present
    at an earlier time with the same state, location, etc. That earlier time
    range would simply be another Avatar (use case: moving back and forth).
    """

    dt_until = DateTime(label="Exist (or will) until this date & time")
    """Date and time until which the Avatar record is meaningful, exclusively.

    Like :attr:`dt_from`, the meaning varies according to the value of
    :attr:`state`:

    + In the ``past`` state, this is supposed to be a faithful
      representation of reality: apart from the special case of formal
      :ref:`Splits and Aggregates <op_split_aggregate>`, the goods
      really left this location at these date and time.

    + In the ``present`` and ``future`` states, this is purely
      theoretical, and the same remarks as for the :attr:`dt_from` field
      apply readily.

    In all cases, this doesn't mean that the very same goods aren't present
    at an later time with the same state, location, etc. That later time
    range would simply be another Avatar (use case: moving back and forth).
    """

    reason = Many2One(label="The operation that is the direct cause "
                      "for the values",
                      index=True,
                      model=Model.Wms.Operation, nullable=False)
    """Entry point to operational history.

    This records the Operation that is responsible for the current
    Avatar, including its :attr:`state`. In practice, it is
    simply the latest :class:`Operation <.operation.base.Operation>` that
    affected these goods.

    It should renamed as ``outcome_of`` or ``latest_operation`` in some
    future.

    .. note:: As a special case, planned Operations do change :attr:`dt_until`
              on the Avatars they work on without setting themselves as
              :attr:`reason`.

              No setting themselves as :attr:`reason` helps to distinguish
              their inputs from their outcomes and is in line
              with :attr:`dt_until` being theoretical in that case anyway.
    """

    def __str__(self):
        return ("(id={self.id}, goods={self.goods}, state={self.state!r}, "
                "location={self.location}, "
                "dt_range=[{self.dt_from}, {self.dt_until})".format(self=self))

    def __repr__(self):
        return ("Wms.Goods.Avatar(id={self.id}, "
                "goods={self.goods!r}, state={self.state!r}, "
                "location={self.location!r}, "
                "dt_range=[{self.dt_from!r}, {self.dt_until!r})").format(
                    self=self)

    def get_property(self, k, default=None):
        return self.goods.get_property(k, default=default)

    @property
    def type(self):
        """Mostly to ease the separation of Avatars from Goods."""
        return self.goods.type

    @property
    def code(self):
        """Mostly to ease the separation of Avatars from Goods."""
        return self.goods.code

    @property
    def quantity(self):
        """Mostly to ease the separation of Avatars from Goods."""
        return self.goods.quantity
