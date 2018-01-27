# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Various constants used throughout WMS applications.

ITEMS_STATES
------------

This is for the ``state`` column of the ``Wms.Items`` model

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
"""


ITEMS_STATES = ('past', 'present', 'future')
