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
    OperationError,
    OperationContainerExpected,
    )

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Arrival(Operation):
    """Operation to describe physical arrival of goods in some location.

    Arrivals store data about the expected or arrived physical objects:
    properties, code…
    These are copied over to the corresponding PhysObj records in all
    cases and stay inert after the fact.

    In case the Arrival state is ``planned``,
    these are obviously only unchecked values,
    but in case it is ``done``, the actual meaning can depend
    on the application:

    - maybe the application won't use the ``planned`` state at all, and
      will only create Arrival after checking them,
    - maybe the application will inspect the Arrival properties, compare them
      to reality, update them on the created PhysObj and cancel downstream
      operations if needed, before calling :meth:`execute`.

    TODO maybe provide higher level facilities for validation scenarios.
    """
    TYPE = 'wms_arrival'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    """Primary key."""
    physobj_type = Many2One(model='Model.Wms.PhysObj.Type')
    """Expected :class:`PhysObj Type
    <anyblok_wms_base.core.physobj.Type>`.
    """
    physobj_properties = Jsonb(label="Properties of arrived PhysObj")
    """Expected :class:`Properties
    <anyblok_wms_base.core.physobj.Properties>`.

    They are copied over to the newly created :class:`PhysObj
    <anyblok_wms_base.core.physobj.PhysObj>` as soon as the Arrival
    is planned, and aren't updated by :meth:`execute`. Matching them with
    reality is the concern of separate validation processes, and this
    field can serve for later assessments after the fact.
    """
    physobj_code = Text(label="Code to set on arrived PhysObj")
    """Expected :attr:`PhysObj code
    <anyblok_wms_base.core.physobj.PhysObj.code>`.

    Can be ``None`` in case the arrival process issues the code only
    at the time of actual arrival.
    """
    location = Many2One(model='Model.Wms.PhysObj')
    """Will be the location of the initial Avatar."""

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

    destination_field = 'location'

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
        """Ensure that ``location`` is indeed a container."""
        super(Arrival, cls).check_create_conditions(state, dt_execution,
                                                    **kwargs)
        if location is None or not location.is_container():
            raise OperationContainerExpected(
                cls, "location field value {offender}",
                offender=location)

    def after_insert(self):
        PhysObj = self.registry.Wms.PhysObj
        self_props = self.physobj_properties
        if self_props is None:
            props = None
        else:
            props = PhysObj.Properties.create(**self_props)

        goods = PhysObj.insert(type=self.physobj_type,
                               properties=props,
                               code=self.physobj_code)
        PhysObj.Avatar.insert(
            obj=goods,
            location=self.location,
            outcome_of=self,
            state='present' if self.state == 'done' else 'future',
            dt_from=self.dt_execution,
        )

    def execute_planned(self):
        self.outcomes[0].update(state='present', dt_from=self.dt_execution)

    @classmethod
    def refine_with_trailing_unpack(cls, arrivals, pack_type,
                                    dt_pack_arrival=None,
                                    dt_unpack=None,
                                    pack_properties=None,
                                    pack_code=None):
        """Replace some Arrivals by the Arrival of a pack followed by an Unpack.

        This is useful in cases where it is impossible to predict ahead how
        incoming goods will actually be packed: the arrivals of individual
        items can first be planned, and once more is known about the form
        of delivery, this classmethod can replace some of them with the
        Arrival of a parcel and the subsequent Unpack.

        Together with :meth:`refine_with_trailing_move
        <anyblok_wms_base.core.operation.base.Operation.refine_with_trailing_move>`,
        this can handle the use case detailed in
        :ref:`improvement_operation_superseding`.

        :param arrivals:
            the Arrivals considered to be superseded by the Unpack.
            It is possible that only a subset of them are superseded, and
            conversely that the Unpack has more outcomes than the superseded
            Arrivals. For more details about the matching, see
            :meth:`Unpack.plan_for_outcomes
            <anyblok_wms_base.core.operation.unpack.Unpack.plan_for_outcomes>`
        :param pack_type:
            :attr:`anyblok_wms_base.core.PhysObj.main.PhysObj.type` of the
            expected pack.
        :param pack_properties:
            optional properties of the expected Pack. This optional parameter
            is of great importance in the case of parcels with variable
            contents, since it allows to set the ``contents`` Property.
        :param str pack_code:
            Optional code of the expected Pack.
        :param datetime dt_pack_arrival:
            expected date/time for the Arrival of the pack. If not specified,
            a default one will be computed.
        :param datetime dt_unpack:
            expected date/time for the Unpack Operation. If not specified,
            a default one will be computed.
        """  # noqa (unbreakable meth crosslink)
        for arr in arrivals:
            arr.check_alterable()
        if not arrivals:
            raise OperationError(cls,
                                 "got empty collection of arrivals "
                                 "to refine: {arrivals!r}",
                                 arrivals=arrivals)
        arr_iter = iter(arrivals)
        location = next(arr_iter).location
        if not all(arr.location == location for arr in arr_iter):
            raise OperationError(cls,
                                 "can't rewrite arrivals to different "
                                 "locations, got {nb_locs} different ones in "
                                 "{arrivals}",
                                 nb_locs=len(set(arr.location
                                                 for arr in arrivals)),
                                 arrivals=arrivals)

        Wms = cls.registry.Wms
        Unpack = Wms.Operation.Unpack
        # check that the arrivals happen in the same locations
        if dt_pack_arrival is None:
            # max minimizes the number of date/time shifts to perform
            # upon later execution, min is more optimistic
            dt_pack_arrival = min(arr.dt_execution for arr in arrivals)
        pack_arr = cls.create(location=location,
                              dt_execution=dt_pack_arrival,
                              physobj_type=pack_type,
                              physobj_properties=pack_properties,
                              physobj_code=pack_code,
                              state='planned')

        arrivals_outcomes = {arr.outcomes[0]: arr for arr in arrivals}
        unpack, attached_avatars = Unpack.plan_for_outcomes(
            pack_arr.outcomes,
            arrivals_outcomes.keys(),
            dt_execution=dt_unpack)
        for att in attached_avatars:
            arrivals_outcomes[att].delete()
        return unpack
