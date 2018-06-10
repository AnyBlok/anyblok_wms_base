# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.


def import_declarations(reload=None):
    from . import goods
    from . import type as gtype

    # even with 'import as', there is masking of the builtin
    # (at least on Python 3.5). Let's remove it if it's there
    # to avoid leaving a trap here
    globals().pop('type', None)

    if reload is not None:
        reload(goods)
        reload(gtype)
