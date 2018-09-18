# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok import Declarations
from anyblok_wms_base.exceptions import OperationPhysObjReserved

register = Declarations.register
Wms = Declarations.Model.Wms


@register(Wms)
class Operation:

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                inputs=None, **kwargs):
        """Refuse to work on reserved PhysObj unless reservation agrees.
        """
        super(Operation, cls).check_create_conditions(
            state, dt_execution, inputs=inputs, **kwargs)
        if not inputs:
            return

        Reservation = cls.registry.Wms.Reservation
        Avatar = cls.registry.Wms.PhysObj.Avatar
        # TODO report that we can't join() on m2o directly, have to
        # use (guess) their primary keys
        for resa in Reservation.query().join(
                Avatar, Avatar.obj_id == Reservation.physobj_id).filter(
                    Avatar.id.in_(av.id for av in inputs)).all():
            if not resa.is_transaction_allowed(
                    cls, state, dt_execution,
                    inputs=inputs, **kwargs):
                raise OperationPhysObjReserved(
                    cls,
                    "Cannot create for {goods} because their PhysObj are "
                    "reserved {reservation!r}, which does not not agree.",
                    goods=resa.goods,
                    reservation=resa)
