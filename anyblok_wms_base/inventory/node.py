# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import orm

from anyblok import Declarations
from anyblok.column import Integer
from anyblok.column import Text
from anyblok.column import Selection
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb

register = Declarations.register
Wms = Declarations.Model.Wms


@register(Wms.Inventory)
class Node:
    """Representation of the inventory of a subtree of containment hierarchy.

    For each Inventory, there's a tree of Inventory Nodes, each Node
    having one-to-many relationships to:

    - :class:`Inventory Lines <Line>` that together with its descendants',
      form the whole assessment of the contents of the Node's
      :attr:`location`
    - :class:`Inventory Actions <Action>` that encode the primary Operations
      that have to be executed to reconcile the database with the assessment.

    Each Node has a :attr:`location` under which the `locations <location>` of
    its children should be directly placed, but that doesn't mean each
    container visited by the inventory process has to be represented by a
    Node: instead, for each Inventory, the
    :attr:`locations <location>` of its leaf Nodes would ideally balance
    the amount of assessment work that can be done by one person in a
    continuous manner while keeping the size of the tree reasonible.

    Applications may want to override this Model to add user fields,
    representing who's in charge of a given node. The user would then either
    optionally take care of splitting (issuing children) the Node and perform
    assesments that are not covered by children Nodes.

    This whole structure is designed so that assessment work can be
    distributed and reconciliation can be performed in parallel.
    """
    STATES = (
        ('draft', 'wms_inventory_state_draft'),
        ('full', 'wms_inventory_state_full'),
        ('computed', 'wms_inventory_state_computed'),
        ('reconciled', 'wms_inventory_state_reconciled'),
    )

    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    state = Selection(selections=STATES,
                      nullable=False,
                      default='draft',
                      )
    """Node lifecycle

    - draft:
        the Node has been created, could still be split, but its
        :class:`lines <Line>` don't represent the full contents yet.
    - assessment:
        (TODO not there yet, do we need it?) assessment work
        has started.
    - full:
        all Physical Objects relevant to the Inventory that are below
        :attr:`location` are accounted for in the :class:`lines <Line>` of
        its Nodes or of its descendants. This implies in particular that
        none of the children Nodes is in prior states.
    - computed:
        all :class:`Actions <Action>` to reconcile the database with the
        assessment have been issued. It is still possible to simplify them
        (that would typically be the :attr:`parent`'s responsibility)
    - reconciled:
        all relevant Operations have been issued.
    """

    inventory = Many2One(model=Wms.Inventory,
                         index=True,
                         nullable=False)
    """The Inventory for which this Node has been created"""

    parent = Many2One(model='Model.Wms.Inventory.Node',
                      index=True)
    location = Many2One(model=Wms.PhysObj, nullable=False)

    @property
    def is_leaf(self):
        """(:class:`bool`): ``True`` if and only if the Node has no children.
        """
        return self.query().filter_by(parent=self).count() == 0

    def split(self):
        """Create a child Node for each container in :attr:`location`."""
        PhysObj = self.registry.Wms.PhysObj
        Avatar = PhysObj.Avatar
        ContainerType = orm.aliased(
            PhysObj.Type.query_behaviour('container', as_cte=True),
            name='container_type')
        subloc_query = (PhysObj.query()
                        .join(Avatar.obj)
                        .join(ContainerType,
                              ContainerType.c.id == PhysObj.type_id)
                        .filter(Avatar.state == 'present'))
        return [self.insert(inventory=self.inventory,
                            parent=self,
                            location=container)
                for container in subloc_query.all()]


@register(Wms.Inventory)
class Line:
    """Represent an assessment for a :class:`Node <Node>` instance."""
    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""
    node = Many2One(model=Wms.Inventory.Node,
                    one2many='lines',
                    nullable=False)
    location = Many2One(model=Wms.PhysObj)
    type = Many2One(model=Wms.PhysObj.Type)
    code = Text()
    properties = Jsonb()
    quantity = Integer()


@register(Wms.Inventory)
class Action:
    """Represent a reconciliation Action for a :class:`Node <Node>` instance.

    TODO data design
    """
    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""
    node = Many2One(model=Wms.Inventory.Node,
                    one2many='actions',
                    nullable=False)
