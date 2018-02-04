# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.blok import Blok


class GoodsBatchRef(Blok):
    """Adds an SQL column to Goods properties for testing purposes
    """
    version = '0.0.1'
    author = "Georges Racinet"
    required = ['wms-core']

    @classmethod
    def import_declaration_module(cls):
        from . import goods_batch_ref  # noqa
