# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import CheckConstraint

from anyblok import Declarations
from anyblok.column import Decimal

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Goods:
    """Override to add the :attr:`quantity` field.
    """

    quantity = Decimal(label="Quantity", default=1)
    """Quantity

    Depending on the Goods Type, this represents in reality some physical
    measure (length of wire, weight of wheat) for Goods stored and handled
    in bulk, or a number of identical items, if goods are kept as individual
    pieces.

    There is no corresponding idea of a unit of measure for bulk Goods,
    as we believe it to be enough to represent it in the Goods Type already
    (which would be, e.g, respectively a meter of wire, a ton of wheat). Note
    that bulk Goods can be the result of some :class:`Unpack
    <.operation.Unpack>`, with the packaged version
    being itself handled as an individual piece (imagine spindles of 100m for
    the wire example) and further packable (pallets, containers…)

    .. note:: the ``quantity`` field may vanish from ``wms-core`` in the
              future, see :ref:`improvement_no_quantities`

    This field has been defined as Decimal to cover a broad scope of
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
      (following on the example, simply have Goods Types representing
      those thirds of pies alongside those representing the whole pies,
      and represent the first cutting of a slice as an
      Unpack)
    """

    @classmethod
    def define_table_args(cls):
        return super(Goods, cls).define_table_args() + (
            CheckConstraint('quantity > 0', name='positive_qty'),
        )

    def __str__(self):
        return ("(id={self.id}, type={self.type}, "
                "quantity={self.quantity})").format(self=self)

    def __repr__(self):
        return ("Wms.Goods(id={self.id}, type={self.type!r}, "
                "quantity={self.quantity!r})".format(self=self))
