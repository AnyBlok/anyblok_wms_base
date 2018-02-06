from anyblok import Declarations
from anyblok.column import Decimal
from anyblok.relationship import Many2One

from anyblok_wms_base.exceptions import (
    OperationGoodsError,
    OperationMissingGoodsError,
    OperationQuantityError,
    OperationMissingQuantityError,
)

Mixin = Declarations.Mixin


@Declarations.register(Mixin)
class WmsSingleGoodsOperation:
    """Mixin for operations that apply to a single record of Goods."""

    goods = Many2One(model='Model.Wms.Goods', nullable=False)
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        if goods is None:
            raise OperationMissingGoodsError(
                cls,
                "The 'goods' keyword argument must be passed to the create() "
                "method")

        return [goods.reason]

    @classmethod
    def check_create_conditions(cls, state, goods=None, quantity=None,
                                **kwargs):
        if goods is None:
            raise OperationMissingGoodsError(
                "The 'goods' keyword argument must be passed to the create() "
                "method")

        if quantity is None:
            raise OperationMissingQuantityError(
                cls,
                "The 'quantity keyword argument must be passed to "
                "the create() method")
        if state == 'done' and goods.state != 'present':
            raise OperationGoodsError(
                cls,
                "Can't create a Move in state 'done' for goods "
                "{goods} because of their state {goods.state}",
                goods=goods)

        if quantity > goods.quantity:
            raise OperationQuantityError(
                cls,
                "Can't move a greater quantity ({quantity}) than held in "
                "goods {goods} (which have quantity={goods.quantity})",
                quantity=quantity,
                goods=goods)

    def check_execute_conditions(self):
        goods = self.goods
        if self.quantity > goods.quantity:
            raise OperationQuantityError(
                self,
                "Can't split {op.qty} from goods {goods} "
                "(which have quantity={goods.quantity}), "
                "although it's been successfully planned in operation {op}",
                op=self, goods=self.goods)

        if goods.state != 'present':
            raise OperationGoodsError(
                self,
                "Can't execute for goods {goods} "
                "because their state {state} is not 'present'",
                goods=goods,
                state=goods.state)
