from rest_framework.response import Response
from rest_framework.views import exception_handler


class BusinessError(Exception):
    """
    Biznes qoidasi buzilganda services qatlamidan ko'tariladi.
    Services DRF'ga bog'liq bo'lmasligi uchun alohida klass; API'da 400 bo'lib qaytadi.
    """

    status_code = 400

    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.message = message
        self.extra = extra


def custom_exception_handler(exc, context):
    if isinstance(exc, BusinessError):
        return Response({"detail": exc.message, **exc.extra}, status=exc.status_code)
    return exception_handler(exc, context)
