from rest_framework.response import Response


class APIResponse:
    @staticmethod
    def success(data=None, message="Success", status=200):
        return Response(
            {
                "success": True,
                "status_code": status,
                "message": message,
                "data": data,
                "errors": None,
            },
            status=status,
        )

    @staticmethod
    def error(message, status=400, errors=None):
        return Response(
            {
                "success": False,
                "status_code": status,
                "message": message,
                "data": None,
                "errors": errors,
            },
            status=status,
        )
