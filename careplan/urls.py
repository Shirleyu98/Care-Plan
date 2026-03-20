from django.urls import path
from careplan import views

urlpatterns = [
    path("", views.order_form, name="order_form"),
    path("result/<int:order_id>/", views.order_result, name="order_result"),
]