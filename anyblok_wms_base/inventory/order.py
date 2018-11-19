# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok import Declarations
from anyblok.column import Integer

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Inventory:
    """This model represents the decision of making an Inventory.

    It expresses a global specification for the inventory process to be made
    as well as human level additional information.

    Applicative code is welcomed and actually supposed to override this to
    add more columns as needed (dates, creator, reason, comments...)

    Instances of :class:`Wms.Inventory <Inventory>` are linked to a tree
    of processing :class:`Nodes <anyblok_wms_base.inventory.node.Node>`,
    which is reachable with the convenience :attr:`root` attribute.

    # TODO structural Properties to use throughout the whole hierarchy
    # for  Physical Object identification
    # TODO PhysObj.Type to exclude (typically containers)
    """

    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    @property
    def root(self):
        """Root Node of the Inventory."""
        return (self.registry.Wms.Inventory.Node.query()
                .filter_by(inventory=self, parent=None)
                .one())

    @classmethod
    def create(cls, location, **fields):
        """Insert a new Inventory together with its root Node.

        :return: the new Inventory
        """
        Node = cls.registry.Wms.Inventory.Node
        inventory = cls.insert(**fields)
        Node.insert(inventory=inventory, location=location)
        return inventory
