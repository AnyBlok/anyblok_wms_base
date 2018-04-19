# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Move:
    """Override to use quantity where needed."""

    def revert_extra_fields(self):
        """Take quantity into account for reversal.

        See also this method's documentation :meth:`in the base class
        <anyblok_wms_base.bloks.wms_core.operation.move.Move.revert_extra_fields>`.
        """
        return dict(quantity=self.quantity)
