# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Various constants used throughout WMS applications.

Enumeration of Selection columns
--------------------------------

This module defines several constants for use in Selection columns
definitions. In this fundational library, we actually don't care about the
labels, since we have no specified user interaction.

However, the Selection column type forces us to define some, that's why we
settled for labels than can themselves be used stably and without ambiguity
as keys for a display system (with i18n in mind), such as
``wms_op_type_pack``.

"""

GOODS_STATES = dict(past="wms_goods_states_past",
                    present="wms_goods_states_present",
                    future="wms_goods_states_future"
                    )
"""This is the enumeration of possible values of the ``state`` column of
the :class:`Wms.Goods <anyblok_wms_base.bloks.wms_core.goods.Goods>` Model.

- ``present``:
        means that the represented goods are (supposed to be) actually
        physically present as described by the record.
- ``past``:
        means that the represented goods are (supposed to be) not anymore
        physically present as described by the record. This is used rather
        than destroying the records so that archived operations can still
        reference them
- ``future``:
        means that the represented goods are planned to be as described in the
        record. This is used for various planning purposes, with the expected
        benefit of quick validation of operations if they are planned in
        advance

"""
OPERATION_STATES = dict(planned="wms_op_states_planned",
                        started="wms_op_states_started",
                        done="wms_wms_op_states_done",
                        )
"""This is the enumeration of possible values of the ``state`` field of
the :class:`Wms.Operation
<anyblok_wms_base.bloks.wms_core.operation.base.Operation>` Model and its
subclasses.

See :ref:`op_states` for a full discussion of these values.
"""

OPERATION_TYPES = dict(wms_move="wms_op_types_move",
                       wms_split="wms_op_types_split",
                       wms_aggregate="wms_op_types_aggregate",
                       wms_unpack="wms_op_types_unpack",
                       wms_pack="wms_op_types_pack",
                       wms_arrival="wms_op_types_arrival",
                       wms_departure="wms_op_types_departure",
                       )
"""The keys of this :class:`dict` are used for the polymorphism of
the :class:`Wms.Operation
<anyblok_wms_base.bloks.wms_core.operation.base.Operation>` Model.

As these keys
supposed to be unique among all polymorphic cases in the whole application,
they are prefixed with ``wms_``.
"""

SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR = 'split_aggregate_physical'
