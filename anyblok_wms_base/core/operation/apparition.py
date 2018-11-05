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
from anyblok.column import Text
from anyblok.field import Function
from anyblok_postgres.column import Jsonb
from anyblok.relationship import Many2One
from .deprecation import deprecation_warn_goods_col
from anyblok_wms_base.exceptions import (
    OperationForbiddenState,
    OperationContainerExpected,
)

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Apparition(Operation):
    """Inventory Operation to record unexpected physical objects.

    This is similar to Arrival, but has a distinct functional meaning.
    Apparitions can exist only in the ``done`` :ref:`state <op_states>`.

    Another difference with Arrivals is that Apparitions have a
    :attr:`quantity` field.
    """
    TYPE = 'wms_apparition'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    """Primary key."""
    physobj_type = Many2One(model='Model.Wms.PhysObj.Type')
    """Observed :class:`PhysObj Type
    <anyblok_wms_base.core.physobj.Type>`.
    """
    quantity = Integer()
    """The number of identical PhysObj that have appeared.

    Here, identical means "same type, code and properties"
    """
    physobj_properties = Jsonb()
    """Observed :class:`Properties
    <anyblok_wms_base.core.physobj.Properties>`.

    They are copied over to the newly created :class:`PhysObj
    <anyblok_wms_base.core.physobj.PhysObj>`. Then the Properties can evolve on
    the PhysObj, while this Apparition field will keep the exact values
    that were observed during inventory.
    """
    physobj_code = Text()
    """Observed :attr:`PhysObj code
    <anyblok_wms_base.core.physobj.PhysObj.code>`.
    """
    location = Many2One(model='Model.Wms.PhysObj')
    """Location of appeared PhysObj.

    This will be the location of the initial Avatars.
    """

    goods_type = Function(fget='_goods_type_get',
                          fset='_goods_type_set',
                          fexpr='_goods_type_expr')
    """Compatibility wrapper.

    Before version 0.9.0, :attr:`physobj_type` was ``goods_type``.

    This does not extend to compatibility of the former low level
    ``goods_type_id`` column.
    """

    goods_properties = Function(fget='_goods_properties_get',
                                fset='_goods_properties_set',
                                fexpr='_goods_properties_expr')
    """Compatibility wrapper.

    Before version 0.9.0, :attr:`physobj_properties` was ``goods_properties``.
    """

    goods_code = Function(fget='_goods_code_get',
                          fset='_goods_code_set',
                          fexpr='_goods_code_expr')
    """Compatibility wrapper.

    Before version 0.9.0, :attr:`physobj_code` was ``goods_code``.
    """

    inputs_number = 0
    """This Operation is a purely creative one."""

    def specific_repr(self):
        return ("physobj_type={self.physobj_type!r}, "
                "location={self.location!r}").format(self=self)

    def _goods_col_get(self, suffix):
        deprecation_warn_goods_col(self, suffix)
        return getattr(self, 'physobj_' + suffix)

    def _goods_col_set(self, suffix, value):
        deprecation_warn_goods_col(self, suffix)
        setattr(self, 'physobj_' + suffix, value)

    @classmethod
    def _goods_col_expr(cls, suffix):
        deprecation_warn_goods_col(cls, suffix)
        return getattr(cls, 'physobj_' + suffix)

    def _goods_type_get(self):
        return self._goods_col_get('type')

    def _goods_type_set(self, value):
        self._goods_col_set('type', value)

    @classmethod
    def _goods_type_expr(cls):
        return cls._goods_col_expr('type')

    def _goods_properties_get(self):
        return self._goods_col_get('properties')

    def _goods_properties_set(self, value):
        self._goods_col_set('properties', value)

    @classmethod
    def _goods_properties_expr(cls):
        return cls._goods_col_expr('properties')

    def _goods_code_get(self):
        return self._goods_col_get('code')

    def _goods_code_set(self, value):
        self._goods_col_set('code', value)

    @classmethod
    def _goods_code_expr(cls):
        return cls._goods_col_expr('code')

    @classmethod
    def check_create_conditions(cls, state, dt_execution, location=None,
                                **kwargs):
        """Forbid creation with wrong states, check location is a container.

        :raises: :class:`OperationForbiddenState
                 <anyblok_wms_base.exceptions.OperationForbiddenState>`
                 if state is not ``'done'``

                 :class:`OperationContainerExpected
                 <anyblok_wms_base.exceptions.OperationContainerExpected>`
                 if location is not a container.
        """
        if state != 'done':
            raise OperationForbiddenState(
                cls, "Apparition can exist only in the 'done' state",
                forbidden=state)
        if location is None or not location.is_container():
            raise OperationContainerExpected(
                cls, "location field value {offender}",
                offender=location)

        super(Apparition, cls).check_create_conditions(
            state, dt_execution, **kwargs)

    def after_insert(self):
        """Create the PhysObj and their Avatars.

        In the ``wms-core`` implementation, the :attr:`quantity` field
        gives rise to as many PhysObj records.
        """
        PhysObj = self.registry.Wms.PhysObj
        self_props = self.physobj_properties
        if self_props is None:
            props = None
        else:
            props = PhysObj.Properties.create(**self_props)

        for _ in range(self.quantity):
            PhysObj.Avatar.insert(
                obj=PhysObj.insert(
                    type=self.physobj_type,
                    properties=props,
                    code=self.physobj_code),
                location=self.location,
                outcome_of=self,
                state='present',
                dt_from=self.dt_execution)
