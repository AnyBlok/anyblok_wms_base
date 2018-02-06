class OperationError(ValueError):

    def __init__(self, model_or_record, fmt, **kwargs):
        self.fmt = fmt
        self.model_name = model_or_record.__registry_name__
        self.kwargs = kwargs

    def __repr__(self):
        formatted_kwargs = ', '.join(
            '%s=%r' % (k, v) for k, v in self.kwargs.items())
        return self.__class__.__name__ + '(%s, %r, %s)' % (
            self.model_name, self.fmt, formatted_kwargs)

    def __str__(self):
        return self.model_name + ': ' + self.fmt.format(**self.kwargs)


class OperationGoodsError(OperationError):
    """Used for operations that take Goods records as input.

    Note that creation operations do not belong to that category.
    """


class OperationMissingGoodsError(OperationGoodsError):
    """Used if the Goods the operation is about are required yet not passed."""


class OperationQuantityError(OperationGoodsError):
    """Used if an operation has an issue with some quantity."""


class OperationMissingQuantityError(OperationGoodsError):
    """Used if the operation requires some quantity that's not passed."""
