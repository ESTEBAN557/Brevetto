from rest_framework.routers import DefaultRouter

from apps.core.views import ClientViewSet, ContractViewSet, DocumentTypeViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("contracts", ContractViewSet, basename="contract")
router.register("document-types", DocumentTypeViewSet, basename="document-type")

urlpatterns = router.urls
