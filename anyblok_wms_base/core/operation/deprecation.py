# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import warnings


def deprecation_warn_goods_col(op, suffix):
    """Generic deprecation warning for goods_* columns of various Operations.
    """
    warnings.warn(
        "The 'goods_{suffix}' attribute of {op} is "
        "deprecated, please rename to 'physobj_{suffix}' before "
        "version 1.0 of Anyblok / WMS Base".format(op=op.__registry_name__,
                                                   suffix=suffix),
        DeprecationWarning,
        stacklevel=2)
