# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.


class InventoryException(ValueError):
    """Base class for ``wms-inventory`` exceptions."""


class NodeStateError(InventoryException):

    def __init__(self, node, fmt):
        self.node_id = node.id
        self.node_state = node.state
        self.node = node
        self.node_repr = repr(node)
        self.fmt = fmt

    def __str__(self):
        return self.fmt.format(node=self.node_repr,
                               id=self.node_id,
                               state=self.node_state)


class NodeChildrenStateError(InventoryException):

    def __init__(self, node, children, fmt):
        self.node_id = node.id
        self.node = node
        self.node_repr = repr(node)
        self.children = children
        self.children_states = {str(c): c.state for c in children}
        self.fmt = fmt

    def __str__(self):
        return self.fmt.format(node=self.node,
                               id=self.node_id,
                               children=self.children,
                               children_states=self.children_states)


class ActionInputsMissing(InventoryException):

    def __init__(self, action, nb_found, fmt):
        self.action = action
        self.action_repr = repr(action)
        self.nb_found = nb_found
        self.nb_expected = action.quantity
        self.fmt = fmt

    def __str__(self):
        return self.fmt.format(action=self.action_repr,
                               nb_found=self.nb_found,
                               nb_expected=self.nb_expected)
