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
from anyblok.relationship import Many2Many

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Operation:
    """A stock operation.

    The Operation model encodes the common part of all precise operations,
    which themselves have dedicated models. This implemented through the
    polymorphic features of SQLAlchemy and AnyBlok.

    The main purpose of this separation is to simplify auditing purposes: the
    Goods model can bear a ``reason`` column, operations can be linked whatever
    their types are.

    Downstream applications and libraries can add columns on the present model
    to satisfy their auditing needs (some notion of "user" or "operator" comes
    to mind).

    More column semantics:
    - id: is equal to the id of the concrete operations model
    - state: see mod:`constants`
    - comment: free field to store details of how it went, or motivation
               for the operation (downstream libraries implementing scheduling
               should better use columns rather than this field).
    - follows:
        the operations that are the direct reasons
        for the presence of Goods the present one is about.
        This is a Many2Many relationship because there might be
        several Goods involved in the operation, but for each of them,
        it'll be exactly one operation, namely the latest before
        the present one. In other words, operations history is a directed
        acyclic graph, whose edges are encoded by this Many2Many.

        This field can be empty in case of initial operations.

        Examples:

             + a move of a bottle of milk that follows the unpacking
               of a 6-pack, which itself follows a move from somewhere
               else
             + a parcel packing operation that follows exactly one move
               to the shipping area for each Goods to be packed.
               They themselves would follow more operations.
             + an Arrival typically doesn't follow anything (but might be due
               to some kind of purchase order).

    """
    id = Integer(label="Identifier, shared with specific tables",
                 primary_key=True)
    type = String(label="Operation Type", nullable=False)  # TODO enum ?
    state = String(label="State", nullable=False)  # TODO enum ?
    comment = String(label="Comment")
    follows = Many2Many(model='Model.Wms.Operation',
                        m2m_remote_columns='parent_id',
                        m2m_local_columns='child_id',
                        join_table='wms_operation_history',
                        label="Immediate preceding operations",
                        )

    @classmethod
    def define_mapper_args(cls):
        mapper_args = super(Operation, cls).define_mapper_args()
        if cls.__registry_name__ == 'Model.Wms.Operation':
            mapper_args.update({
                'polymorphic_identity': 'operation',
                'polymorphic_on': cls.type,
            })
        else:
            mapper_args.update({
                'polymorphic_identity': cls.TYPE,
            })

        return mapper_args
