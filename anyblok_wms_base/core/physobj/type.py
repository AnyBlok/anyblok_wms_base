# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from sqlalchemy import orm

from anyblok import Declarations
from anyblok.column import Text
from anyblok.column import Integer
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb
from anyblok_wms_base.utils import dict_merge

_missing = object()
"""A marker to use as default value in get-like functions/methods."""


register = Declarations.register
Model = Declarations.Model


@register(Model.Wms.PhysObj)
class Type:
    """Types of PhysObj.

    For a full functional discussion, see :ref:`physobj_type`.
    """
    id = Integer(label="Identifier", primary_key=True)
    """Primary key"""

    code = Text(label=u"Identifying code", index=True,
                unique=True, nullable=False)
    """Uniquely identifying code.

    As a convenience, and for sharing with other applications.
    """

    label = Text(label=u"Label")

    behaviours = Jsonb()
    """
    Flexible field to encode how represented objects interact with the system.

    Notably, PhysObj Types specify with this flexible field how various
    :class:`Operations <anyblok_wms_base.core.operation.base.Operation>`
    will treat the represented physical object.

    .. seealso:: :class:`Unpack
                 <anyblok_wms_base.core.operation.unpack.Unpack>`
                 for a complex example.

    But behaviours are in no means in one to one correspondence with Operation
    classes, nor do they need to be related to Operations. Any useful
    information that depends on the Type only is admissible to encode as a
    behaviour.

    The value is a key/value mapping (behaviour name/value).

    .. warning:: direct read access to a behaviour is to be
                 avoided in favour of :meth:`get_behaviour`
                 (see :ref:`improvement_goods_type_hierarchy`).

    This field is also open for downstream libraries and applications to
    make use of it to define some of their specific logic, but care must be
    taken not to conflict with the keys used by ``wms-core`` and other bloks
    (TODO introduce namespacing, then ? at least make a list available by
    using constants from an autodocumented module)
    """

    properties = Jsonb(label="Properties")
    """PhysObj Types also have flexible properties.

    These are usually read from the PhysObj themselves (where they act as
    default values if not defined on the PhysObj), and are useful with
    generic Types, i.e., those that have children. Operations that handle
    Properties can do interesting things by using properties that actually
    come from Type information.
    """

    parent = Many2One(model='Model.Wms.PhysObj.Type')
    """This field expresses the hierarchy of PhysObj Types."""

    def __str__(self):
        return "(id={self.id}, code={self.code!r})".format(self=self)

    def __repr__(self):
        return "Wms.PhysObj.Type" + str(self)

    # TODO PERF cache ?
    def get_behaviour(self, name, default=None):
        """Get the value of the behaviour with given name.

        This method is the preferred way to access a given behaviour.
        It resolves the wished behaviour by looking it up within the
        :attr:`behaviours` :class:`dict`, and recursively on its parent.

        It also takes care of corner cases, such as when :attr:`behaviours` is
        ``None`` as a whole.
        """
        behaviours = self.behaviours
        parent = self.parent

        if parent is None:
            parent_beh = _missing
        else:
            parent_beh = self.parent.get_behaviour(name, default=_missing)

        if behaviours is None:
            beh = _missing
        else:
            beh = behaviours.get(name, _missing)

        if beh is _missing:
            if parent_beh is _missing:
                return default
            return parent_beh
        if parent_beh is _missing:
            return beh
        return dict_merge(beh, parent_beh)

    def is_sub_type(self, gt):
        """True if ``self``  is a sub type of ``gt``, inclusively.

        TODO PERF the current implementation recurses over ancestors.
        A subsequent implementation could add caching and/or recursive SQL
        queries.
        """
        if self == gt:
            return True
        parent = self.parent
        if parent is None:
            return False
        return parent.is_sub_type(gt)

    @classmethod
    def query_add_subtypes(cls, base, as_cte=False):
        """Make a recursive SQL query out of a base query.

        The base query is used as starting point of the iteration performed
        by the database, which itself simply adds descendents.

        :param base: Query object on ``cls``, with only one column: ``id``
        :param bool as_cte: if ``True``, instead of a directly usable query,
                            a CTE (WITH statement) is returned, that the
                            called may in turn use as they wish
        """
        session = cls.registry.session
        cte = base.cte(name='subtypes', recursive=True)
        parent = orm.aliased(cte, name='subtypes_parent')
        child = orm.aliased(cls, name='subtypes_child')
        cte = cte.union_all(
            session.query(child.id).filter(child.parent_id == parent.c.id))
        if as_cte:
            return cte
        # TODO strangely enough, I can't see to have SQLAlchemy issuing
        # a working IN clause on the CTE (it would repeat the CTE contents and
        # use that), so let's do with a JOIN for the time being
        return cls.query().join(cte, cte.c.id == cls.id)

    @classmethod
    def query_subtypes(cls, ancestors, as_cte=False):
        """Return a recursive SQL query for Type hierarchy.

        :param ancestors: the Type to start with (inclusive)

        The resulting query or CTE matches all Types that are descendents
        (inclusive) of those in ``ancestors``.
        """
        return cls.query_add_subtypes(
            cls.query(cls.id).filter(cls.id.in_(a.id for a in ancestors)),
            as_cte=as_cte)

    def get_property(self, k, default=None):
        """Read a property value recursively.

        If the current Type does not have the wished property key, but has a
        parent, then the lookup continues on the parent.
        """
        props = self.properties
        val = _missing if props is None else props.get(k, _missing)
        if val is _missing:
            parent = self.parent
            if parent is None:
                return default
            return parent.get_property(k, default=default)
        return val

    @classmethod
    def query_behaviour(cls, behaviour, as_cte=False):
        """Return a recursive SQL query for behaviour presence.

        :param behaviour: Types having this behaviour will be returned.
                           The value of the behaviours don't matter.
        :param bool as_cte: if ``True``, instead of a directly usable query,
                            a CTE (WITH statement) is returned, that the
                            called may in turn use as they wish

        The resulting query or CTE matches all Types that are descendents
        (inclusive) of those in ``ancestors``.
        """
        # TODO factorize with query_subtypes
        # this is simply those that have the behaviour plus their descendents
        # i.e., only the non-recursive part differs
        return cls.query_add_subtypes(
            cls.query(cls.id)
            .filter(
                cls.behaviours.has_key(  # noqa: pep8 thinks it's dict API
                behaviour)),
            as_cte=as_cte)

    def is_container(self):
        return self.get_behaviour('container') is not None

    def query_container(self):
        """Return a query for container Types.

        For the time being, this is just a wrapper around
        :meth:`query_behaviour`, but container identification might change
        in the future.
        """

    def merged_properties(self):
        """Return this Type properties, merged with its parent."""
        parent = self.parent
        properties = self.properties
        if parent is None:
            return properties if properties is not None else {}
        return dict_merge(properties, parent.merged_properties())

    def has_property_values(self, mapping):
        return all(self.get_property(k, default=_missing) == v
                   for k, v in mapping.items())

    def has_property(self, name):
        if self.properties is not None and name in self.properties:
            return True
        parent = self.parent
        if parent is not None:
            return parent.has_property(name)
        return False

    def has_properties(self, wanted_props):
        if not wanted_props:
            return True

        properties = self.properties
        if properties is None:
            missing = wanted_props
        else:
            missing = (p for p in wanted_props if p not in properties)

        parent = self.parent
        if parent is None:
            for x in missing:  # could be a generator, a list etc.
                return False
            return True
        return parent.has_properties(missing)
