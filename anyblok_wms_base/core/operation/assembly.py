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
from anyblok_postgres.column import Jsonb
from anyblok.relationship import Many2One

from anyblok_wms_base.exceptions import (OperationInputsError,
                                         AssemblyInputNotMatched,
                                         AssemblyExtraInputs,
                                         AssemblyPropertyConflict,
                                         UnknownExpressionType,
                                         OperationError,
                                         )
from anyblok_wms_base.constants import (DEFAULT_ASSEMBLY_NAME,
                                        CONTENTS_PROPERTY,
                                        )

register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation

_missing = object()
"""A marker to use as default value in get-like functions/methods."""


@register(Operation)
class Assembly(Operation):
    """Assembly/Pack Operation.

    This operation covers simple packing and assembly needs : those for which
    a single outcome is produced from the inputs, which must be in the same
    Location. More general manufacturing cases fall out of the scope of
    the ``wms-core`` Blok.

    The behaviour is specified on the :attr:`outcome's Goods Type
    <outcome_type>`, and amounts to describing the expected inputs,
    and how to build the Properties of the outcome (see
    :meth:`build_outcome_properties`)

    A given Type can be assembled in different ways (TODO use-cases even
    for simple packing), and this gets specified by the :attr:`name` field.

    Besides being the main key for the
    :attr:`Assembly specification <specification>`,
    the :attr:`name` is also used to dispatch hooks for specific logic that
    would be too complicated to describe in configuration (see
    :meth:`specific_build_outcome_properties`).
    """
    TYPE = 'wms_assembly'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))

    outcome_type = Many2One(model='Model.Wms.Goods.Type', nullable=False)
    """The :class:`Goods Type
    <anyblok_wms_base.core.goods.Type>` to produce.
    """

    name = Text(nullable=False, default=DEFAULT_ASSEMBLY_NAME)
    """The name of the assembly, to be looked up in behaviour.

    This field has a default value to accomodate the common case where there's
    only one assembly for the given :attr:`outcome_type`.

    .. note:: the default value is not enforced before flush, this can
              prove out to be really inconvenient for downstream code.
              TODO apply the default value in :meth:`check_create_conditions`
              for convenience ?
    """

    match = Jsonb()
    """Field use to store the result of inputs matching

    Assembly Operations match their actual inputs (set at creation)
    with the ``inputs`` part of :attr:`specification`.
    This field is used to store the
    result, so that it's available for further logic (for instance in
    the :meth:`property setting hooks
    <specific_build_outcome_properties>`).

    This field's value is either ``None`` (before matching) or a list
    of lists: for each of the inputs specification, respecting
    ordering, the list of ids of the matching Avatars.
    """

    def specific_repr(self):
        return ("outcome_type={self.outcome_type!r}, "
                "name={self.name!r}").format(self=self)

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                inputs=None, outcome_type=None, name=None,
                                **kwargs):
        super(Assembly, cls).check_create_conditions(
            state, dt_execution, inputs=inputs,
            **kwargs)
        behaviour = outcome_type.behaviours.get('assembly')
        if behaviour is None:
            raise OperationError(
                cls, "No assembly specified for type {outcome_type!r}",
                outcome_type=outcome_type)
        spec = behaviour.get(name)
        if spec is None:
            raise OperationError(
                cls,
                "No such assembly: {name!r} for type {outcome_type!r}",
                name=name, outcome_type=outcome_type)

        loc = inputs[0].location
        if any(inp.location != loc for inp in inputs[1:]):
            raise OperationInputsError(
                cls,
                "Inputs {inputs} are in different Locations: {locations!r}",
                inputs=inputs,
                # in the passing case, building a set would have been
                # useless overhead
                locations=set(inp.location for inp in inputs))

    def check_extract_input_props(self, avatar, extracted,
                                  input_spec=None,
                                  required_props=None,
                                  required_prop_values=None,
                                  forwarded_props=None):
        """Check and if match, extract for forwarding properties of one input.

        :param avatar: the input to consider
        :param dict extracted: previously done extractions
        :param input_spec: (index, expected) it is redudant with
                           required_props etc, but used only
                           for feedback in exceptions
        :rtype bool:
        :return: ``True`` if the avatar matches the criteria
        :raises: AssemblyPropertyConflict if forwarding properties
                 changes an already set value.

        The required properties and values are checked, and the forwarded
        ones are stored in ``extracted``, after it has been checked that
        they don't change a previous one.
        """
        goods = avatar.goods

        # TODO use global exceptions (and define them !)
        if not goods.has_properties(required_props):
            return False
        if not goods.has_property_values(required_prop_values):
            return False

        for fp in forwarded_props:
            candidate_value = goods.get_property(fp, default=_missing)
            if candidate_value is _missing:
                continue
            try:
                existing = extracted[fp]
            except KeyError:
                extracted[fp] = candidate_value
            else:
                if existing != candidate_value:
                    raise AssemblyPropertyConflict(
                        self, input_spec, fp, existing, candidate_value)

        return True

    def analyse_inputs(self):
        """Compare input Avatars to specification and apply Properties rules.

        This is meant to be called after :meth:`check_create_conditions` has
        performed the checks that don't return anything for further treatment.

        :return: (extra_inputs, forwarded_props), respectively an iterable of
                 inputs that are left once all input specifications are met,
                 and a :class:`dict` of property names and values extracted
                 from the inputs and to be set on the outcome.
        :raises: :class:`anyblok_wms_base.exceptions.AssemblyInputNotMatched`,
                 :class:`anyblok_wms_base.exceptions.AssemblyForbiddenExtraInputs`

        """
        outcome_props = {}
        spec = self.specification
        req_props = spec.get('required_properties', ())
        req_prop_values = spec.get('required_property_values', {})
        fwd_props = spec.get('forward_properties', ())

        for av in self.inputs:
            self.check_extract_input_props(av, outcome_props,
                                           required_props=req_props,
                                           required_prop_values=req_prop_values,
                                           forwarded_props=fwd_props)

        # let' stress that the incoming ordering shouldn't matter
        # from this method's point of view. And indeed, only in tests can
        # it come from the will of a caller. In reality, it'll be due to
        # factors that are random wrt the specification.
        inputs = set(self.inputs)
        match = self.match = []

        GoodsType = self.registry.Wms.Goods.Type
        types_by_code = dict()

        for i, expected in enumerate(spec['inputs']):
            match_item = []
            match.append(match_item)

            req_props = expected.get('required_properties', ())
            req_prop_values = expected.get('required_property_values', {})
            fwd_props = expected.get('forward_properties', ())

            type_code = expected['type']
            gtype = types_by_code.get(type_code)
            if gtype is None:
                gtype = GoodsType.query().filter_by(
                    code=type_code).one()
                types_by_code[type_code] = gtype

            for _ in range(expected['quantity']):
                for candidate in inputs:
                    if not candidate.goods.has_type(gtype):
                        continue
                    if self.check_extract_input_props(
                            candidate, outcome_props,
                            input_spec=(i, expected),
                            required_props=req_props,
                            required_prop_values=req_prop_values,
                            forwarded_props=fwd_props):
                        inputs.discard(candidate)
                        match_item.append(candidate.id)
                        break
                else:
                    raise AssemblyInputNotMatched(self, (expected, i))

        if inputs and not spec.get('allow_extra_inputs'):
            raise AssemblyExtraInputs(self, inputs)
        return inputs, outcome_props

    @property
    def specification(self):
        """The Assembly specification

        The Assembly specification is read from the ``assembly`` part of
        the behaviour field of :attr:`outcome_type`. Namely, it is, within
        that part, the value associated with :attr:`name`.

        Here's an example, for an Assembly whose :attr:`name` is
        ``'soldering'``, also displaying all standard parameters::

          behaviours = {
             …
             'assembly': {
                 'soldering': {
                     'properties': {'built_here': ['const', True]},
                     'properties_at_execution': {
                         'serial': ['sequence', 'SOLDERINGS'],
                     },
                     'inputs': [
                         {'type': 'GT1',
                          'quantity': 1,
                          'forward_properties': ['foo', 'bar'],
                          'required_properties': ['foo'],
                          'required_property_values': {'x': True}
                          },
                         {'type': 'GT2', 'quantity': 2},
                     ],
                     'for_contents': ['all', 'descriptions'],
                     'forward_properties': …
                     'required_properties': …
                     'required_property_values': …
                 }
                 …
              }
          }

        .. note:: Non standard parameters can be specified, for use in
                  :meth:`Specific hooks <specific_build_outcome_properties>`.

        The present Python property performs no checks,
        since it is meant to be accessed only after the protection of
        :meth:`check_create_conditions`.
        """
        return self.outcome_type.behaviours['assembly'][self.name]

    DEFAULT_FOR_CONTENTS = ('extra', 'records')
    """Default value of the ``for_contents`` part of specification.

    See :meth:`build_outcome_properties` for the meaning of the values.
    """

    def build_outcome_properties(self):
        """Method responsible for initial properties on the outcome.

        :rtype: :class:`Model.Wms.Goods.Properties
                <anyblok_wms_base.core.goods.Properties>`
        :raises: :class:`AssemblyInputNotMatched` if one of the
                 :attr:`input specifications <specification>` is not
                 matched by ``self.inputs``,
                 :class:`AssemblyPropertyConflict` in case of conflicting
                 values for the outcome.

        **Property specifications**

        The Assembly :attr:`specification` can have the following
        key/value pairs:

        * ``properties``:
             a dict of Properties to set on the outcome; the values
             are pairs ``(TYPE, EXPRESSION)`` evaluated by passing as
             positional arguments to :meth:`eval_typed_expr`.
        * ``properties_at_execution``:
             similar to ``properties``, but set during Assembly
             execution (or at creation in the ``done`` state).

             use-case: when using ``Model.System.Sequence`` to create
             a serial number,  or if recording the assembly date in
             the outcome properties, one probably prefer to evaluate
             this at execution time.
        * ``forward_properties``:
             a list of properties that will be copied from all inputs to
             the Properties of the outcome.
        * ``required_properties``:
             a list of properties that all inputs must have to be valid,
             whatever the values.
        * ``required_property_values``:
             a :class:`dict` describing required Property key/value pairs on
             all inputs.

        **Per input specification matching and forwarding**

        The last three configuration parameters can be specified
        inside each :class:`dict` that form
        the ``inputs`` list of the :meth:`Assembly specification <spec>`),
        and in that case, the Property requirements are used as matching
        criteria on the inputs. They are applied in order, but remember that
        the ordering of ``self.inputs`` itself is to be considered random.

        In all cases, if a given Property is to be forwarded from several
        inputs to the outcome and its values on these inputs aren't equal,
        :class:`AssemblyPropertyConflict` will be raised.

        **Specific hooks**

        While already powerful, the Property manipulations described above
        are not expected to fit all situations, especially the rule about
        differing values on inputs. On the other hand, trying to accomodate
        all use cases through configuration would lead to insanity.

        Therefore, the core will stick to these still
        relatively simple primitives, but will also provide the means
        to perform custom logic, through :meth:`assembly-specific hooks
        <specific_build_outcome_properties>`

        Namely, :meth:`specific_build_outcome_properties` gets called near
        the end of the process. and the built Properties are built according
        to its result, with higher precedence than any other source of
        properties.


        **The contents Property**

        The outcome also bears the special :data:`contents property
        <anyblok_wms_base.constants.CONTENTS_PROPERTY>` (
        used by :class:`Operation.Unpack
        <anyblok_wms_base.core.operation.unpack.Unpack>`).

        This is controlled by the
        ``for_contents`` part of the assembly specification, which
        itself is a pair, whose first element indicates which inputs to list,
        and the second how to list them. Its default value is
        :attr:`DEFAULT_FOR_CONTENTS`.

        *for_contents: possible values of first element:*

        * ``'all'``:
             all inputs will be listed
        * ``'extra'``:
            only the actual inputs that aren't specified in the
            behaviour will be listed. This is useful in cases where
            the Unpack behaviour already takes the specified ones into
            account. Hence, the variable parts of Assembly and Unpack are
            consistent.

        *for_contents: possible values of second element:*

        * ``'descriptions'``:
            include Goods' Types, those Properties that aren't recoverable by
            an Unpack from the Assembly outcome, together with appropriate
            ``forward_properties`` for those who are (TODO except those that
            come from a global ``forward_properties`` of the assembly)
        * ``'records'``:
            same as ``descriptions``, but also includes the record ids, so
            that an Unpack following the Assembly would not give rise to new
            Goods records, but would reuse the existing ones, hence keep the
            promise that the Goods records are meant to track the "sameness"
            of the physical objects.
        """
        spec = self.specification
        extra, assembled_props = self.analyse_inputs()

        contents = self.build_contents(spec, extra, assembled_props)
        if contents:
            assembled_props[CONTENTS_PROPERTY] = contents

        spec_props = spec.get('properties')
        if spec_props is not None:
            assembled_props.update(self.eval_spec_exprs('properties'))
        direct_exec = self.state == 'done'
        if direct_exec:
            assembled_props.update(
                self.eval_spec_exprs('properties_at_execution'))

        assembled_props.update(self.specific_build_outcome_properties(
            assembled_props, for_exec=direct_exec))
        return self.registry.Wms.Goods.Properties.create(**assembled_props)

    props_hook_fmt = "build_outcome_properties_{name}"

    def specific_build_outcome_properties(self, assembled_props,
                                          for_exec=False):
        """Hook for per-name specific update of Properties on outcome.

        At the time of Operation creation or execution,
        this calls a specific method whose name is derived from the
        :attr:`name` field, :attr:`by this format <props_hook_fmt>`, if that
        method exists.

        Applicative code is meant to override the present Model to provide
        the specific method. The signature to implement is identical to the
        present one:

        :param dict assembled_props:
           a :class:`dict` of already built Properties, or a
           :class:`Properties
           <anyblok_wms_base.core.goods.Properties>` instance.
        :param bool for_exec:
          ``False`` during Operation creation in the ``planned`` state,
          ``True`` during Operation execution or creation in the ``done``
          state.
        :return: the properties to set or update
        :rtype: any iterable that can be passed to :meth:`dict.update`.

        """
        meth = getattr(self, self.props_hook_fmt.format(name=self.name), None)
        if meth is None:
            return ()
        return meth(assembled_props, for_exec=for_exec)

    def build_contents(self, spec, extra, forwarded_props):
        """Construction of the ``contents`` property

        This is part of :meth`build_outcome_properties`
        """
        what, how = spec.get('for_contents', self.DEFAULT_FOR_CONTENTS)
        if what == 'extra':
            for_unpack = extra
        elif what == 'all':
            for_unpack = self.inputs

        contents = []

        # sorting here and later is for tests reproducibility
        for avatar in sorted(for_unpack, key=lambda av: av.id):
            # TODO individual properties aren't supported by Unpack yet
            goods = avatar.goods
            props = goods.properties
            unpack_outcome = dict(
                type=goods.type.code,
                quantity=1,  # TODO hook for wms_quantity
                )
            if props is not None:
                unpack_outcome_fwd = []
                for k, v in props.as_dict().items():
                    if k in forwarded_props:
                        unpack_outcome_fwd.append(k)
                    else:
                        unpack_outcome.setdefault('properties', {})[k] = v
                unpack_outcome_fwd.sort()
                if unpack_outcome_fwd:
                    unpack_outcome['forward_properties'] = unpack_outcome_fwd

            contents.append(unpack_outcome)
            if how == 'records':
                # Adding local goods id so that a forthcoming unpack
                # would produce the very same goods.
                # TODO this *must* be discarded in case of Departures with
                # EDI,  and maybe some other ones. How to do that cleanly and
                # efficiently ?
                unpack_outcome['local_goods_ids'] = [goods.id]

        return contents

    def after_insert(self):
        outcome_state = 'present' if self.state == 'done' else 'future'
        dt_exec = self.dt_execution
        input_upd = dict(dt_until=dt_exec)
        if self.state == 'done':
            input_upd.update(state='past', reason=self)
        # TODO PERF bulk update ?
        for inp in self.inputs:
            inp.update(**input_upd)

        Goods = self.registry.Wms.Goods
        Goods.Avatar.insert(
            goods=Goods.insert(
                type=self.outcome_type,
                properties=self.build_outcome_properties()),
            location=self.inputs[0].location,
            reason=self,
            state=outcome_state,
            dt_from=dt_exec,
            dt_until=None)

    def execute_planned(self):
        """Update states and build execution properties.

        Besides the update of state for inputs and outcomes, that all
        Operations perform, this also performs the final update of
        Properties on the outcome:

        * application of the ``properties_at_execution`` key of the Assembly
          :attr:`specification`
        * application of :meth:`specific_build_outcome_properties`
          with ``for_exec=True``
        """
        # TODO PERF direct update query would probably be faster
        for inp in self.inputs:
            inp.state = 'past'
        outcome = self.outcomes[0]

        outcome.state = 'present'
        goods = outcome.goods
        goods.update_properties(
            self.eval_spec_exprs('properties_at_execution'))
        goods.update_properties(
            self.specific_build_outcome_properties(goods.properties,
                                                   for_exec=True))

    def eval_typed_expr(self, etype, expr):
        """Evaluate a typed expression.

        :param expr: the expression to evaluate
        :param etype: the type or ``expr``.

        *Possible values for etype*

        * ``'const'``:
            ``expr`` is considered to be a constant and gets returned
            directly. Any Python value that is JSON serializable is admissible.
        * ``'sequence'``:
            ``expr`` must be the code of a
            ``Model.System.Sequence`` instance. The return value is
            the formatted value of that sequence, after incrementation.
        """
        if etype == 'const':
            return expr
        elif etype == 'sequence':
            return self.registry.System.Sequence.nextvalBy(code=expr.strip())
        raise UnknownExpressionType(self, etype, expr)

    def eval_spec_exprs(self, spec_key):
        """Read typed expressions from :attr:`specification` and evaluate them.

        :rtype: iterator of (key, value) pairs.
        """
        props = self.specification.get(spec_key)
        if props is None:
            return ()
        return ((k, self.eval_typed_expr(*v)) for k, v in props.items())

    def is_reversible(self):
        """Assembly can be reverted by Unpack.
        """
        return self.outcome_type.get_behaviour("unpack") is not None

    def plan_revert_single(self, dt_execution, follows=()):
        unpack_inputs = [out for op in follows for out in op.outcomes]
        # self.outcomes has actually only those outcomes that aren't inputs
        # of downstream operations
        # TODO maybe change that for API clarity
        unpack_inputs.extend(self.outcomes)
        return self.registry.Wms.Operation.Unpack.create(
            dt_execution=dt_execution,
            inputs=unpack_inputs)
