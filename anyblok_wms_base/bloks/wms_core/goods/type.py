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
from anyblok.column import Integer
from anyblok_postgres.column import Jsonb


register = Declarations.register
Model = Declarations.Model


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
    <anyblok_wms_base.bloks.wms_core.operation.base.Operation>` will treat
    the represented Goods.

    .. seealso:: :class:`Unpack
                 <anyblok_wms_base.bloks.wms_core.operation.unpack.Unpack>`
                 for a complex example.

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

    def __str__(self):
        return "(id={self.id}, code={self.code!r})".format(self=self)

    def __repr__(self):
        return "Wms.Goods.Type" + str(self)

    def get_behaviour(self, name, default=None):
        """Get the value of the behaviour with given name.

        This method is the preferred way to access a given behaviour.
        It performs all the needed resolutions and defaultings.
        In particular, it takes care of the case where :attr:`behaviours` is
        ``None`` as a whole.
        """
        behaviours = self.behaviours
        if behaviours is None:
            return default
        return behaviours.get(name, default)
