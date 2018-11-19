# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from copy import deepcopy
import warnings

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import orm
from sqlalchemy import or_

from anyblok import Declarations
from anyblok.column import Text
from anyblok.column import Selection
from anyblok.column import Integer
from anyblok.column import DateTime
from anyblok.relationship import Many2One
from anyblok.field import Function
from anyblok_postgres.column import Jsonb

from anyblok_wms_base.utils import dict_merge
from anyblok_wms_base.constants import (
    AVATAR_STATES,
    DATE_TIME_INFINITY,
)

_missing = object()
"""A marker to use as default value in get-like functions/methods."""


register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class PhysObj:
    """Main data type to represent physical objects managed by the system.

    The instances of this model are also
    the ultimate representation of the PhysObj "staying the same" or "becoming
    different" under the Operations, which is, ultimately, a subjective
    decision that has to be left to downstream libraires and applications, or
    even end users.

    For instance, everybody agrees that moving something around does not make
    it different. Therefore, the Move Operation uses the same PhysObj record
    in its outcome as in its input.
    On the other hand, changing a property could be considered enough an
    alteration of the physical object to consider it different, or not (think
    of recording some measurement that had not be done earlier.)
    """
    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    type = Many2One(model='Model.Wms.PhysObj.Type', nullable=False, index=True)
    """The :class:`PhysObj Type <.type.Type>`"""

    code = Text(label="Identifying code",
                index=True)
    """Uniquely identifying code.

    This should be about what one is ready to display as a barcode for handling
    the PhysObj. It's also meant to be shared with other applications if needed
    (rather than ids which are only locally unique).
    """

    properties = Many2One(label="Properties",
                          index=True,
                          model='Model.Wms.PhysObj.Properties')
    """Link to :class:`Properties`.

    .. seealso:: :ref:`physobj_properties` for functional aspects.

    .. warning:: don't ever mutate the contents of :attr:`properties` directly,
                 unless what you want is precisely to affect all the PhysObj
                 records that use them directly.

    Besides their :attr:`type` and the fields meant for the Wms Base
    bloks logic, the PhysObj Model bears flexible data,
    called *properties*, that are to be
    manipulated as key/value pairs through the :meth:`get_property` and
    :meth:`set_property` methods.

    As far as ``wms_core`` is concerned, values of properties can be of any
    type, yet downstream applications and libraries can choose to make them
    direct fields of the :class:`Properties` model.

    Properties can be shared among several PhysObj records, for efficiency.
    The :meth:`set_property` implements the necessary Copy-on-Write
    mechanism to avoid unintentionnally modify the properties of many
    PhysObj records.

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
            fmt = "Wms.PhysObj(id={self.id}, type={self.type!r})"
        else:
            # I expect direct assignment onto string litteral to be more
            # efficient than a string manipulation
            fmt = ("Wms.PhysObj(id={self.id}, code={self.code!r}, "
                   "type={self.type!r})")
        return fmt.format(self=self)

    def has_type(self, goods_type):
        """Tell whether ``self`` has the given type.

        :param .type.Type goods_type:
        :return: ``True`` if the :attr:`type` attribute is ``goods_type`` or
                 on of its descendants.

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

        Duplication occurs iff there are other PhysObj with the same
        Properties instance.

        The caller must have already checked that ``self.properties`` is not
        ``None``.
        """
        cls = self.__class__
        existing = self.properties
        if (cls.query(cls.id)
                .filter(cls.properties == existing, cls.id != self.id)
                .limit(1).count()):
            self.properties = existing.duplicate()

    def set_property(self, k, v):
        """Property setter.

        See remarks on :meth:`get_property`.

        This method implements a simple Copy-on-Write mechanism. Namely,
        if the properties are referenced by other PhysObj records, it
        will duplicate them before actually setting the wished value.
        """
        existing_props = self.properties
        if existing_props is None:
            self.properties = self.registry.Wms.PhysObj.Properties(
                flexible=dict())
        elif existing_props.get(k) != v:
            self._maybe_duplicate_props()
        self.properties.set(k, v)

    def update_properties(self, mapping):
        """Update Properties in one shot, similar to :meth:`dict.update`

        :param mapping: a :class:`dict` like object, or an iterable of
                        (key, value) pairs

        This method implements a simple Copy-on-Write mechanism. Namely,
        if the properties are referenced by other PhysObj records, it
        will duplicate them before actually setting the wished value.
        """
        items_meth = getattr(mapping, 'items', None)
        if items_meth is None:
            items = mapping
        else:
            items = mapping.items()

        existing_props = self.properties
        if existing_props is None:
            self.properties = self.registry.Wms.PhysObj.Properties.create(
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

    @classmethod
    def flatten_containers_subquery(cls, top=None,
                                    additional_states=None, at_datetime=None):
        """Return an SQL subquery flattening the containment graph.

        Containing PhysObj can themselves be placed within a container
        through the standard mechanism: by having an Avatar whose location is
        the surrounding container.
        This default implementation issues a recursive CTE (``WITH RECURSIVE``)
        that climbs down along this, returning just the ``id`` column

        This subquery cannot be used directly: it is meant to be used as part
        of a wider query; see :mod:`unit tests
        <anyblok_wms_base.core.physobj.tests.test_containers>`) for nice
        examples with or without joins.

        .. note:: This subquery itself does not restrict its results to
                  actually be containers! Only its use in joins as locations
                  of Avatars will, and that's considered good enough, as
                  filtering on actual containers would be more complicated
                  (resolving behaviour inheritance) and is useless for
                  quantity queries.

                  Applicative code relying on this method for other reasons
                  than quantity counting should therefore add its own ways
                  to restrict to actual containers if needed.

        :param top:
           if specified, the query starts at this Location (inclusive)

        For some applications with a large and complicated containing
        hierarchy, joining on this CTE can become a performance problem.
        Quoting
        `PostgreSQL documentation on CTEs
        <https://www.postgresql.org/docs/10/static/queries-with.html>`_:

          However, the other side of this coin is that the optimizer is less
          able to push restrictions from the parent query down into a WITH
          query than an ordinary subquery.
          The WITH query will generally be evaluated as written,
          without suppression of rows that the parent query might
          discard afterwards.

        If that becomes a problem, it is still possible to override the
        present method: any subquery whose results have the same columns
        can be used by callers instead of the recursive CTE.

        Examples:

        1. one might design a flat Location hierarchy using prefixing on
           :attr:`code` to express inclusion instead of the standard Avatar
           mechanism.
           :attr:`parent`. See :meth:`this test
           <.tests.test_containers.TestContainers.test_override_recursion>`
           for a proof of this concept.
        2. one might make a materialized view out of the present recursive CTE,
           refreshing as soon as needed.
        """
        Avatar = cls.Avatar
        query = cls.registry.session.query
        cte = cls.query(cls.id)
        if top is None:
            cte = (cte.outerjoin(Avatar, Avatar.obj_id == cls.id)
                   .filter(Avatar.location_id.is_(None)))
        else:
            cte = cte.filter_by(id=top.id)

        cte = cte.cte(name="container", recursive=True)
        parent = orm.aliased(cte, name='parent')
        child = orm.aliased(cls, name='child')
        tail = (query(child.id)
                .join(Avatar, Avatar.obj_id == child.id)
                .filter(Avatar.location_id == parent.c.id))

        # taking additional states and datetime query into account
        # TODO, this location part is very redundant with what's done in
        # Wms.quantity() itself for the PhysObj been counted,
        # we should refactor
        if additional_states is None:
            tail = tail.filter(Avatar.state == 'present')
        else:
            tail = tail.filter(
                Avatar.state.in_(('present', ) + tuple(additional_states)))

        if at_datetime is DATE_TIME_INFINITY:
            tail = tail.filter(Avatar.dt_until.is_(None))
        elif at_datetime is not None:
            tail = tail.filter(Avatar.dt_from <= at_datetime,
                               or_(Avatar.dt_until.is_(None),
                                   Avatar.dt_until > at_datetime))
        cte = cte.union_all(tail)
        return cte

    def is_container(self):
        """Tell whether the :attr:`type` is a container one.

        :rtype: bool
        """
        return self.type.is_container()

    def current_avatar(self):
        """The Avatar giving the current position of ``self`` in reality

        :return: the Avatar, or ``None``, in case ``self`` is not yet or
                 no more physically present.
        """
        return self.Avatar.query().filter_by(obj=self, state='present').first()

    def eventual_avatar(self):
        """The Avatar giving the latest foreseeable position of ``self``.

        :return: the Avatar, or ``None``, in case

                 - ``self`` is planned to leave the system.
                 - ``self`` has already left the system (only ``past`` avatars)

        There are more complicated corner cases, but they shouldn't arise in
        real operation and the results are considered to be dependent on the
        implementation of this method, hence not part of any stability
        promises. Simplest example: a single avatar, with ``state='present'``
        and ``dt_until`` not ``None`` (normally a subsequent avatar, in the
        ``planned`` state should explain the bounded time range).
        """
        Avatar = self.Avatar
        return (Avatar.query()
                .filter(Avatar.state.in_(('present', 'future')))
                .filter_by(obj=self, dt_until=None)
                .first())


_empty_dict = {}


@register(Model.Wms.PhysObj)
class Properties:
    """Properties of PhysObj.

    This is kept in a separate Model (and SQL table) to provide sharing
    among several :class:`PhysObj` instances, as they can turn out to be
    identical for a large number of them.

    Use-case: receive a truckload of milk bottles that all have the same
    expiration date, and unpack everything down to the bottles. The expiration
    date would be stored in a single Properties instance, assuming there aren't
    also non-uniform properties to store, of course.

    Applications are welcome to overload this model to add new fields rather
    than storing their meaningful information in the :attr:`flexible` field,
    if it has added value for performance or programmming tightness reasons.
    This has the obvious drawback of defining some properties for all PhysObj,
    regardless of their Types, so it should not be abused.

    This model implements a subset of the :class:`dict` API, treating
    direct fields and top-level keys of :attr:`flexible` uniformely, so
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
        """Support for reading with the [] syntax.

        :raises: KeyError
        """
        if k in self._field_property_names():
            return getattr(self, k)
        if self.flexible is None:
            raise KeyError(k)
        return self.flexible[k]

    def get(self, k, *default):
        """Similar to :meth:`dict.get`."""
        if len(default) > 1:
            return _empty_dict.get(k, *default)

        try:
            return self[k]
        except KeyError:
            if default:
                return default[0]
            return None

    def __setitem__(self, k, v):
        """Support for writing with the [] notation."""
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
        """Support for deleting with the [] notation.

        :raises: KeyError if ``k`` is missing
        """
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
        """Similar to :meth:`dict.pop`."""
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


def deprecation_warn_goods():
        warnings.warn("The 'goods' attribute of Model.Wms.PhysObj.Avatar is "
                      "deprecated, please rename to 'obj' before "
                      "version 1.0 of Anyblok / WMS Base",
                      DeprecationWarning,
                      stacklevel=2)


@register(Model.Wms.PhysObj)
class Avatar:
    """PhysObj Avatar.

    See in :ref:`Core Concepts <physobj_avatar>` for a functional description.
    """

    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    obj = Many2One(model=Model.Wms.PhysObj,
                   index=True,
                   nullable=False)
    """The PhysObj of which this is an Avatar."""

    state = Selection(label="State of existence",
                      selections=AVATAR_STATES,
                      nullable=False,
                      index=True)
    """State of existence in the premises.

    see :mod:`anyblok_wms_base.constants`.

    This may become an ENUM once Anyblok supports them.
    """

    location = Many2One(model=Model.Wms.PhysObj,
                        nullable=False,
                        index=True)
    """Where the PhysObj are/will be/were.

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
      counting several :ref:`physobj_avatar` of the same physical goods
      while :meth:`peeking at quantities in the future
      <anyblok_wms_base.core.location.Location.quantity>`.
      If the end application does serious time prediction, it can use it
      freely.

    In all cases, this doesn't mean that the very same PhysObj aren't present
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

    outcome_of = Many2One(index=True,
                          model=Model.Wms.Operation, nullable=False)
    """The Operation that created this Avatar.
    """

    goods = Function(fget='_goods_get',
                     fset='_goods_set',
                     fexpr='_goods_expr')
    """Compatibility wrapper.

    Before the merge of Goods and Locations as PhysObj, :attr:`obj` was
    ``goods``.

    This does not extend to compatibility of the former low level ``goods_id``
    column.
    """

    def _goods_get(self):
        deprecation_warn_goods()
        return self.obj

    def _goods_set(self, value):
        deprecation_warn_goods()
        self.obj = value

    @classmethod
    def _goods_expr(cls):
        deprecation_warn_goods()
        return cls.obj

    def __str__(self):
        return ("(id={self.id}, obj={self.obj}, state={self.state!r}, "
                "location={self.location}, "
                "dt_range=[{self.dt_from}, "
                "{self.dt_until}])".format(self=self))

    def __repr__(self):
        return ("Wms.PhysObj.Avatar(id={self.id}, "
                "obj={self.obj!r}, state={self.state!r}, "
                "location={self.location!r}, "
                "dt_range=[{self.dt_from!r}, {self.dt_until!r}])").format(
                    self=self)

    def get_property(self, k, default=None):
        return self.obj.get_property(k, default=default)
