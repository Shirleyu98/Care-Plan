from django.urls import path
from careplan import views

urlpatterns = [
    path("", views.order_form, name="order_form"),
    path("result/<int:order_id>/", views.order_result, name="order_result"),

    # Search by name - personal practice
    path("search_by_name/", views.search_orders_by_name, name="search_orders_by_name")
]