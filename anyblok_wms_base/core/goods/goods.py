# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from copy import deepcopy
from sqlalchemy.orm.attributes import flag_modified

from anyblok import Declarations
from anyblok.column import Text
from anyblok.column import Selection
from anyblok.column import Integer
from anyblok.column import DateTime
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb

from anyblok_wms_base.utils import dict_merge
from anyblok_wms_base.constants import (
    GOODS_STATES,
)

_missing = object()
"""A marker to use as default value in get-like functions/methods."""


register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Goods:
    """Main data type to represent physical objects managed by the system.

    The instances of this model are also
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
    """The :class:`Goods Type <.type.Type>`"""

    code = Text(label="Identifying code",
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
        if self.code is None:
            fmt = "(id={self.id}, type={self.type})"
        else:
            # I expect direct assignment onto string litteral to be more
            # efficient than a string manipulation
            fmt = "(id={self.id}, code={self.code}, type={self.type})"
        return fmt.format(self=self)

    def __repr__(self):
        if self.code is None:
            fmt = "Wms.Goods(id={self.id}, type={self.type!r})"
        else:
            # I expect direct assignment onto string litteral to be more
            # efficient than a string manipulation
            fmt = ("Wms.Goods(id={self.id}, code={self.code!r}, "
                   "type={self.type!r})")
        return fmt.format(self=self)

    def has_type(self, goods_type):
        """Tell whether ``self`` has the given type.

        :param .type.Type goods_type:
        :return: ``True`` if the :attr:`type` attribute is ``goods_type``

        :rtype bool:
        """
        return self.type.is_sub_type(goods_type)

    def get_property(self, k, default=None):
        """Property getter, works like :meth:`dict.get`.

        Actually I'd prefer to simply implement the dict API, but we can't
        direcly inherit from UserDict yet. This is good enough to provide
        the abstraction needed for current internal wms_core calls.
        """
        props = self.properties
        val = _missing if props is None else props.get(k, _missing)
        if val is _missing:
            return self.type.get_property(k, default=default)
        return val

    def merged_properties(self):
        """Return all Properties, merged with the Type properties.

        :rtype: dict

        To retrieve just one Property, prefer :meth:`get_property`, which
        is meant to be more efficient.
        """
        props = self.properties
        type_props = self.type.merged_properties()
        if props is None:
            return type_props

        return dict_merge(props.as_dict(), type_props)

    def _maybe_duplicate_props(self):
        """Internal method to duplicate Properties

        Duplication occurs iff there are other Goods with the same
        Properties instance.

        The caller must have already checked that ``self.properties`` is not
        ``None``.
        """
        cls = self.__class__
        existing = self.properties
        if cls.query(cls.id).filter(
                cls.properties == existing,
                cls.id != self.id).limit(1).count():
            self.properties = existing.duplicate()

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
            self._maybe_duplicate_props()
        self.properties.set(k, v)

    def update_properties(self, mapping):
        """Update Properties in one shot, similar to :meth:`dict.update`

        :param mapping: a :class:`dict` like object, or an iterable of
                        (key, value) pairs
        This method implements a simple Copy-on-Write mechanism. Namely,
        if the properties are referenced by other Goods records, it
        will duplicate them before actually setting the wished value.
        """
        items_meth = getattr(mapping, 'items', None)
        if items_meth is None:
            items = mapping
        else:
            items = mapping.items()

        existing_props = self.properties
        if existing_props is None:
            self.properties = self.registry.Wms.Goods.Properties.create(
                **{k: v for k, v in items})
            return

        actual_upd = []
        for k, v in items:
            if existing_props.get(k, _missing) != v:
                actual_upd.append((k, v))
        if not actual_upd:
            return

        self._maybe_duplicate_props()
        self.properties.update(actual_upd)

    def has_property(self, name):
        """Check if a Property with given name is present."""
        props = self.properties
        if props is not None and name in props:
            return True
        return self.type.has_property(name)

    def has_properties(self, names):
        """Check in one shot if Properties with given names are present."""
        if not names:
            return True
        props = self.properties
        if props is None:
            return self.type.has_properties(names)
        return self.type.has_properties(n for n in names if n not in props)

    def has_property_values(self, mapping):
        """Check that all key/value pairs of mapping are in properties."""
        if not mapping:
            return True
        props = self.properties
        if props is None:
            return self.type.has_property_values(mapping)

        return all(self.get_property(k, default=_missing) == v
                   for k, v in mapping.items())


_empty_dict = {}


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
              ``contents``. TODO make a list, in the form of
              constants in a module
    """

    @classmethod
    def _field_property_names(cls):
        """Iterable over the names of properties that are fields."""
        return (f for f in cls._fields_description()
                if f not in ('id', 'flexible'))

    def as_dict(self):
        """Return the properties as a ``dict``.

        This is not to be confused with the generic :meth:`to_dict` method of
        all Models. The present method abstracts over the :attr:`flexible`
        field and the regular ones. It also strips :attr:`id` and doesn't
        attempt to follow relationships.
        """
        res = {k: getattr(self, k) for k in self._field_property_names()}
        flex = self.flexible
        if flex is not None:
            res.update((k, deepcopy(v)) for k, v in flex.items())
        return res

    def __getitem__(self, k):
        if k in self._field_property_names():
            return getattr(self, k)
        if self.flexible is None:
            raise KeyError(k)
        return self.flexible[k]

    def get(self, k, *default):
        if len(default) > 1:
            return _empty_dict.get(k, *default)

        try:
            return self[k]
        except KeyError:
            if default:
                return default[0]
            return None

    def __setitem__(self, k, v):
        if k in ('id', 'flexible'):
            raise ValueError("The key %r is reserved, and can't be used "
                             "as a property name" % k)
        if k in self.fields_description():
            setattr(self, k, v)
        else:
            if self.flexible is None:
                self.flexible = {k: v}
            else:
                self.flexible[k] = v
            flag_modified(self, '__anyblok_field_flexible')

    set = __setitem__  # backwards compatibility

    def __delitem__(self, k):
        if k in ('id', 'flexible'):
            raise ValueError("The key %r is reserved, can't be used "
                             "as a property name and hence can't "
                             "be deleted " % k)
        if k in self._field_property_names():
            raise ValueError("Can't delete field backed property %r" % k)

        if self.flexible is None:
            raise KeyError(k)

        del self.flexible[k]
        flag_modified(self, '__anyblok_field_flexible')

    def pop(self, k, *default):
        if k in ('id', 'flexible'):
            raise ValueError("The key %r is reserved, can't be used "
                             "as a property name and hence can't "
                             "be deleted " % k)
        if k in self._field_property_names():
            raise ValueError("Can't delete field backed property %r" % k)

        if self.flexible is None:
            return _empty_dict.pop(k, *default)

        res = self.flexible.pop(k, *default)
        flag_modified(self, '__anyblok_field_flexible')
        return res

    def duplicate(self):
        """Insert a copy of ``self`` and return its id."""
        fields = {k: getattr(self, k)
                  for k in self._field_property_names()
                  }
        return self.insert(flexible=deepcopy(self.flexible), **fields)

    @classmethod
    def create(cls, **props):
        """Direct creation.

        The caller doesn't have to care about which properties get stored as
        direct fields or in the :attr:`flexible` field.

        This method is a better alternative than
        insertion followed by calls to :meth:`set`, because it guarantees that
        only one SQL INSERT will be issued.

        If no ``props`` are given, then nothing is created and ``None``
        gets returned, thus avoiding a needless row in the database.
        This may seem trivial, but it spares a test for callers that would
        pass a ``dict``, using the ``**`` syntax, which could turn out to
        be empty.
        """
        if not props:
            return

        fields = set(cls._field_property_names())
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

    def update(self, *args, **kwargs):
        """Similar to :meth:`dict.update`

        This current implementation doesn't attempt to be smarter that setting
        the values one after the other, which means in particular going
        through all the checks for each key. A future implementation might try
        and be more efficient.
        """
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % (
                len(args)))
        iters = [kwargs.items()]
        if args:
            positional = args[0]
            if isinstance(positional, dict):
                iters.append(positional.items())
            else:
                iters.append(positional)
        for it in iters:
            for k, v in it:
                self[k] = v

    def __contains__(self, k):
        """Support for the 'in' operator.

        Field properties are always present. Since one could say that
        the database uses ``None`` to mark absence, it could be relevant
        to return False if the value is ``None`` (TODO STABILIZATION).
        """
        if k in self._field_property_names():
            return True
        flex = self.flexible
        if flex is None:
            return False
        return k in flex


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

    location = Many2One(model=Model.Wms.Goods,
                        nullable=False,
                        index=True)
    """Where the Goods are/will be/were.

    See :class:`Location <anyblok_wms_base.core.location.Location>`
    for a discussion of what this should actually mean.
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
      <anyblok_wms_base.core.location.Location.quantity>`.
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
                "dt_range=[{self.dt_from}, "
                "{self.dt_until}])".format(self=self))

    def __repr__(self):
        return ("Wms.Goods.Avatar(id={self.id}, "
                "goods={self.goods!r}, state={self.state!r}, "
                "location={self.location!r}, "
                "dt_range=[{self.dt_from!r}, {self.dt_until!r}])").format(
                    self=self)

    def get_property(self, k, default=None):
        return self.goods.get_property(k, default=default)
