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
from anyblok_postgres.column import Jsonb
from .exceptions import (NodeStateError,
                         )

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

    TODO structural Properties to use throughout the whole hierarchy
    for  Physical Object identification

    This tree is designed for distribution of the assessment and reconciliation
    work, but it's possible to compute all reconciliations and apply them on
    an Inventory for testing purposes as follows (assuming that all related
    :class:`Nodes <.node.Node>` are in the ``full`` state)::

        inventory.root.recurse_compute_push_actions()
        inventory.reconcile_all()
    """

    id = Integer(label="Identifier", primary_key=True)
    """Primary key."""

    excluded_types = Jsonb()
    """List of Physobj.Type codes to be excluded.

    This is not the smartest way of excluding stuff, but it's good enough
    for time being.
    The primary use-case is to exclude some/most of the container types
    from inventories, which could also be done by excluding all container types
    with a recursive query involving behaviours, but that's a performance hit
    for something that can be done by simply excluding a few types.
    """

    considered_types = Jsonb()
    """List of ``Physobj.Type`` codes to be considered.

    Similarly to :attr:`excluded_types`, this is good enough and can be
    later be improved by adding a flag to make it recursive.
    """

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

    def reconcile_all(self):
        """Convenience method to apply all Actions linked to this Inventory.

        This is a straightforward yet non scalable implementation of
        the final reconciliation (see below). Don't use it on large
        installations.

        To run it, it is required that the :attr:`root` Node has reached
        the ``pushed`` state.

        :raises: NodeStateError if :attr:`root` Node is not ready.

        This method does everything in one shot, therefore leading to huge
        database transactions on full inventories of large installations.

        For large inventories, a more progressive way of doing is required,
        perhaps Node per Node plus batching for each Node.
        Nodes wouldn't have to be taken
        in order, but care must be taken while updating their state
        to 'reconciled' in out of order executions with several batches per
        Node.
        """
        root = self.root
        if root.state != 'pushed':
            raise NodeStateError(root, "This root {node} has not "
                                 "reached the 'pushed' state "
                                 "(currently at {state!r})")
        Node = self.Node
        Action = self.Action
        for action in (Action.query()
                       .join(Node, Node.id == Action.node_id)
                       .filter(Node.inventory == self)
                       .all()):
            action.apply()

        (Node.query()
         .filter_by(inventory=self)
         .update(dict(state='reconciled'), synchronize_session='fetch'))
