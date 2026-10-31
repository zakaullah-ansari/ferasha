from django.urls import path
from .views import CartViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', CartViewSet, basename='cart')

urlpatterns = router.urls
