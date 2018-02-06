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


class OperationCreateArgFollows(OperationError):
    """Used to forbid direct passing of 'follows' kwarg at creation.

    The purpose is to avoid downstream programmers believe that they can
    control it (of course, they can tamper with follows afterwards, this is
    Python)
    """
    def __init__(self, model_or_record, create_kw):
        OperationError.__init__(
            self, model_or_record,
            "'follows' should not be passed create() keyword arguments, "
            "as it is automatically computed upon "
            "operation creation. Other keyword arguments: {create_kw})",
            create_kw=create_kw)


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
