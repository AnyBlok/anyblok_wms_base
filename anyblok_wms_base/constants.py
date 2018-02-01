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

GOODS_STATES
------------

This is the enumeration of possible values of the ``state`` column of
the ``Wms.Goods`` model.

- ``present``:
        means that the represented goods are (supposed to be) actually
        physically present as described by the record.
- ``past``:
        means that the represented goods are (supposed to be) not anymore
        physically present as described by the record. This is used rather
        than destroying the records so that archived operations can still
        reference them
- ``future`:
        means that the represented goods are planned to be as described in the
        record. This is used for various planning purposes, with the expected
        benefit of quick validation of operations if they are planned in
        advance

OPERATIONS_STATES
-----------------
This is the enumeration of possible values of the ``state`` column of
the ``Wms.Goods`` model and its subclasses.

- ``planned``:
       this means that the operation is considered for the future. Upon
       creation in this state, the system will already create the necessary
       objects (in particular Goods and other Operation records), with
       appropriate states so that the whole system view is consistent for the
       present time as well as future times.
- ``started``:
       In real life, operations are never atomic, and often cannot be
       cancelled any more once started.

       In this state, outcomes of the operation are not already
       there, but the operation cannot be cancelled. The Goods being the
       object of the operation should be completely locked to represent that
       they are actually not available any more.

       It would be probably too expensive to systematically use this state,
       therefore, it should be used only if the real life operation takes
       a really long time to conclude.

       Examples:

          + longer distance moves. If this is really frequent, you can also
            consider splitting them in two steps, e.g, moving to a location
            representing some kind of vehicle (even if it is a cart),
            then moving from the vehicle to the final location. This can be
            more consistent and explicit than having thousands Goods, still
            attached to their original locations, but hard lock to represent
            that they aren't there any more.
          + unpacking or manufacturing operations. Here also, you can reduce
            the usage by representing unpacking of manufacturing areas.
``done``:
     Most operations can be created already in their ``done`` state, usually
     after the real-life fact happened or simultaneously (for a good enough
     definition of simultaneity).

     In this case, the consequences are enforced within the same transaction.
     This state is also the outcome of the ``execute()`` method.

OPERATION_TYPES
---------------

The keys are used for the polymorphism of ``Wms.Operation``. As they are
supposed to be unique among all polymorphic cases in the whole application,
these keys are prefixed with ``wms_``.
"""


GOODS_STATES = dict(past="wms_goods_states_past",
                    present="wms_goods_states_present",
                    future="wms_goods_states_future"
                    )

OPERATION_STATES = dict(planned="wms_op_states_planned",
                        started="wms_op_states_started",
                        done="wms_wms_op_states_done",
                        )

OPERATION_TYPES = dict(wms_move="wms_op_types_move",
                       wms_unpack="wms_op_types_unpack",
                       wms_pack="wms_op_types_pack",
                       wms_arrival="wms_op_types_arrival",
                       wms_departure="wms_op_types_departure",
                       )
