from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import RouteRequestSerializer
from .services import RoutePlanningError, plan_route


class RouteBurstThrottle(AnonRateThrottle):
    rate = "30/min"


class RoutePlanView(APIView):
    """
    Plan a USA driving route with cost-optimal fuel stops.

    Accepts JSON body or query params: start, finish.
    """

    throttle_classes = [RouteBurstThrottle]
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request: Request) -> Response:
        return self._handle(request.data)

    def get(self, request: Request) -> Response:
        return self._handle(request.query_params)

    def _handle(self, data) -> Response:
        serializer = RouteRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data["start"]
        finish = serializer.validated_data["finish"]

        try:
            payload = plan_route(start, finish)
        except RoutePlanningError as exc:
            return Response({"detail": str(exc)}, status=exc.status)

        return Response(payload, status=status.HTTP_200_OK)
