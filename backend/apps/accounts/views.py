from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AuthorProfile, StaffInvitation
from apps.common.permissions import HasEditorialPrivilege, IsOrganizationMember

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "display_name",
            "first_name",
            "last_name",
            "avatar_url",
            "locale",
            "timezone",
            "bio",
            "preferences",
            "last_seen_at",
        ]
        read_only_fields = ["id", "email", "last_seen_at"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=4, write_only=True)
    display_name = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            display_name=validated_data.get("display_name", ""),
        )


class StaffInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffInvitation
        fields = [
            "id",
            "organization",
            "email",
            "role",
            "publications",
            "invited_by",
            "status",
            "expires_at",
            "accepted_at",
            "message",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "invited_by",
            "status",
            "expires_at",
            "accepted_at",
            "created_at",
        ]


class AuthorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorProfile
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if User.objects.filter(email__iexact=ser.validated_data["email"]).exists():
            return Response({"detail": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)
        user = ser.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request.user.touch_last_seen()
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class StaffInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = StaffInvitationSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember, HasEditorialPrivilege]
    required_privilege = "users.manage"
    queryset = StaffInvitation.objects.select_related("role", "invited_by")

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if not org else StaffInvitation.objects.none()

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            invited_by=self.request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[])
    def accept(self, request):
        token = request.data.get("token")
        invitation = StaffInvitation.objects.filter(token=token).first()
        if not invitation or not invitation.is_valid:
            return Response({"detail": "Invalid invitation"}, status=status.HTTP_400_BAD_REQUEST)
        email = request.data.get("email", invitation.email)
        password = request.data.get("password")
        user = User.objects.filter(email__iexact=email).first()
        if user:
            if not password:
                return Response(
                    {"detail": "password required for new users"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = User.objects.create_user(
                email=email,
                password=password,
                display_name=request.data.get("display_name", ""),
            )
        membership = invitation.accept(user)
        return Response(
            {
                "membership_id": str(membership.id),
                "organization_id": str(invitation.organization_id),
            }
        )


class AuthorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = AuthorProfileSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = AuthorProfile.objects.none()
    lookup_field = "slug"
    search_fields = ["display_name", "email", "job_title"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else AuthorProfile.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)
