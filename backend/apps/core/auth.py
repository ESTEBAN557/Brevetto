"""Login del personal: acepta usuario o correo electrónico (la pantalla de empleados pide "Email")."""

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class StaffTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        identifier = attrs.get(self.username_field, "")
        if "@" in identifier:
            user_model = get_user_model()
            matches = list(user_model.objects.filter(email__iexact=identifier.strip(), is_active=True)[:2])
            if len(matches) == 1:  # correo ambiguo: no se resuelve, falla como credenciales inválidas
                attrs[self.username_field] = matches[0].get_username()
        return super().validate(attrs)


class StaffTokenObtainPairView(TokenObtainPairView):
    serializer_class = StaffTokenObtainPairSerializer
