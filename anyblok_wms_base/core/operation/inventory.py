# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Mixins for Operations that take exactly on PhysObj record as input.
"""

from anyblok import Declarations
from anyblok_wms_base.exceptions import (
    OperationForbiddenState
    )

Mixin = Declarations.Mixin


@Declarations.register(Mixin)
class WmsInventoryOperation:
    """Mixin for Inventory Operations.

    Inventory Operations have some common features / traits, such as not
    supporting the ``planned`` state.

    Also, this Mixin allows dependent Bloks to add more functionality to all
    of them in one shot.
    """

    @classmethod
    def check_create_conditions(cls, state, dt_execution, **kwargs):
        """Forbid creation with wrong states.

        :raises: :class:`OperationForbiddenState
                 <anyblok_wms_base.exceptions.OperationForbiddenState>`
                 if state is not ``'done'``
        """
        if state != 'done':
            raise OperationForbiddenState(
                cls, "Inventory Operations can exist only "
                "in the 'done' state", forbidden=state)
        super().check_create_conditions(state, dt_execution, **kwargs)
