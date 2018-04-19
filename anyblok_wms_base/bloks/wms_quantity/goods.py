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

from anyblok_wms_base.constants import (
    SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR
)

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
    that bulk Goods can be the result of some :ref:`op_unpack`, with the
    packaged version
    being itself handled as an individual piece (imagine spindles of 100m for
    the wire example) and further packable (pallets, containers…)

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


@register(Model.Wms.Goods)
class Type:
    """Override to have behavorial tests for Split/Aggregate.

    As a special case, the behaviours specify whether
    :class:`Split <.operation.split.Split>` and
    :class:`Aggregate <.operation.aggregate.Aggregate>` Operations are physical
    (represent something happening in reality), and if that's the case if they
    are reversible, using ``{"reversible": true}``, defaulting to ``false``,
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

    * if the represented goods are meters of wiring, then Splits are physical,
      they mean cutting the wires, but Aggregates probably can't happen
      in reality, and therefore Splits are irreversible.
    * if the represented goods are kilograms of sand, kept in bulk,
      then Splits mean in reality shoveling some out of, while Aggregates mean
      shoveling some in (associated with Move operations, obviously).
      Both operations are certainly reversible in reality.
    """

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
