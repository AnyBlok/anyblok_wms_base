# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import orm
from sqlalchemy import or_
from sqlalchemy import and_

from anyblok import Declarations
from anyblok.column import Integer
from anyblok.column import Text
from anyblok.column import Selection
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb

register = Declarations.register
Wms = Declarations.Model.Wms


@register(Wms.Inventory)
class Action:
    """Represent a reconciliation Action for a :class:`Node <Node>` instance.
    """
    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""
    node = Many2One(model=Wms.Inventory.Node,
                    one2many='actions',
                    nullable=False)

    OPERATIONS = (
        ('app', 'wms_inventory_action_app'),
        ('disp', 'wms_inventory_action_disp'),
        ('telep', 'wms_inventory_action_telep'),
    )

    type = Selection(selections=OPERATIONS, nullable=False)

    location = Many2One(model=Wms.PhysObj, nullable=False)
    destination = Many2One(model=Wms.PhysObj)
    """Optional destination container.

    This is useful if :attr:`type` is ``telep`` only.
    """
    physobj_type = Many2One(model=Wms.PhysObj.Type, nullable=False)
    physobj_code = Text()
    physobj_properties = Jsonb()
    quantity = Integer(nullable=False)

    def __repr__(self):
        fmt = ("Wms.Inventory.Action(type={self.type!r}, "
               "node={self.node!r}, location_code={self.location.code!r}, ")
        if self.type == 'telep':
            fmt += "destination_code={self.destination.code!r}, "
        fmt += ("quantity={self.quantity}, "
                "physobj_type_code={self.physobj_type.code!r}, "
                "physobj_code={self.physobj_code!r}, "
                "physobj_properties={self.physobj_properties!r})")
        return fmt.format(self=self)

    __str__ = __repr__

    @classmethod
    def simplify(cls, node):
        App = orm.aliased(cls, name='app')
        Disp = orm.aliased(cls, name='disp')
        # TODO, compare properties
        matching = (cls.registry.query(App, Disp)
                    .filter(App.node == node,
                            App.type == 'app',
                            Disp.node == node,
                            Disp.type == 'disp',
                            Disp.physobj_type_id == App.physobj_type_id,
                            or_(Disp.physobj_code == App.physobj_code,
                                and_(Disp.physobj_code.is_(None),
                                     App.physobj_code.is_(None))))
                    .all())

        for app, disp in matching:
            if app.type == 'telep' or disp.type == 'telep':
                # one is already rewritten
                continue
            diff_qty = app.quantity - disp.quantity
            dest = app.location
            if diff_qty >= 0:
                disp.update(type='telep', destination=dest)
                if diff_qty:
                    app.quantity = diff_qty
                else:
                    app.delete()
            else:
                app.update(type='telep',
                           location=disp.location,
                           destination=dest)
                disp.quantity = -diff_qty

    def apply(self):
        """Issue Inventory Operations for the current Action.

        :return: tuple of the newly created Operations
        """
        Operation = self.registry.Wms.Operation
        op_fields = dict(state='done', inventory=self.node.inventory)
        if self.type == 'app':
            return (
                Operation.Apparition.create(
                    physobj_type=self.physobj_type,
                    physobj_code=self.physobj_code,
                    physobj_properties=self.physobj_properties,
                    quantity=self.quantity,
                    location=self.location,
                    **op_fields),
                )

        # only Operations with (single) input remain
        avatars = self.choose_affected()
        if self.type == 'disp':
            Op = Operation.Disparition
        else:
            Op = Operation.Teleportation
            op_fields['new_location'] = self.destination

        return tuple(Op.create(input=av, **op_fields) for av in avatars)

    def choose_affected(self):
        """Choose Physical Objects to be taken for Disparition/Teleportation.

        if :attr:`physobj_code` is ``None``, we match only Physical Objects
        whose ``code`` is also ``None``. That's because the code should
        come directly from existing PhysObj records (that weren't reflected
        in Inventory Lines).

        Same remark would go for Properties, but:
        TODO implement Properties
        TODO take Reservation into account
        TODO adapt to wms-quantity
        """
        PhysObj = self.registry.Wms.PhysObj
        Avatar = PhysObj.Avatar
        avatars = (Avatar.query()
                   .filter_by(location=self.location,
                              state='present')
                   .join(PhysObj, Avatar.obj_id == PhysObj.id)
                   .filter(PhysObj.type == self.physobj_type,
                           PhysObj.code == self.physobj_code)
                   .limit(self.quantity)
                   .all()
                   )
        # TODO precise exc
        if len(avatars) != self.quantity:
            raise ValueError("Couldn't find enough Avatars (only %d over %d) "
                             "to choose from in application of %r" % (
                                 len(avatars), self.quantity, self))
        return avatars
