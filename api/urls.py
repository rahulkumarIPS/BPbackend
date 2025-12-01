from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # Auth endpoint
    path('login/', obtain_auth_token, name='api_token_auth'),
    
    # Public endpoints
    path('sites/search/', views.search_sites, name='search_sites'),
    path('price/calculate/', views.calculate_price, name='calculate_price'),
    path('book/', views.book_create, name='book_create'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    
    # Admin endpoints
    path('admin/sites/create/', views.create_site, name='create_site'),
    path('admin/sites/list/', views.list_sites, name='list_sites'),
    path('admin/pricing/create/', views.create_pricing, name='create_pricing'),
    path('admin/charges/create/', views.create_optional_charge, name='create_optional_charge'),
]
