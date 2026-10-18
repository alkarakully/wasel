from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Device


class DeviceSerializer(serializers.Serializer):
    fid = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=Device.Platform.choices)
    app = serializers.ChoiceField(choices=Device.App.choices)


class DeviceView(APIView):
    """
    POST /api/devices/ {fid, platform, app}: this phone wants pushes.
    DELETE /api/devices/ {fid}: stop (on logout).

    `fid` is the app's Firebase Installation ID. It belongs to one phone, so
    registering it moves it to the signed-in user if someone else used that
    phone before.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        Device.objects.update_or_create(
            fid=data["fid"], defaults={"user": request.user, "platform": data["platform"], "app": data["app"]}
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        Device.objects.filter(user=request.user, fid=request.data.get("fid", "")).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
