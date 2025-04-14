from django.urls import path
from . import views

urlpatterns = [
    # Common pages
    path('', views.home, name='home'),
    path('water-type/<int:pk>/', views.water_type_detail, name='water_type_detail'),
    path('guest-order/', views.create_guest_order, name='create_guest_order'),
    
    # Role router
    path('dashboard/', views.role_router, name='role_router'),
    
    # Authentication URLs
    path('signup/client/', views.client_signup, name='client_signup'),
    path('signup/driver/', views.driver_signup, name='driver_signup'),
    
    # Client URLs
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
    path('client/order/<int:water_type_id>/', views.place_order, name='place_order'),
    path('client/order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('client/my-orders/', views.my_orders, name='my_orders'),
    
    # Driver URLs
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/accept-delivery/<int:order_id>/', views.accept_delivery, name='accept_delivery'),
    path('driver/complete-delivery/<int:delivery_id>/', views.complete_delivery, name='complete_delivery'),
    path('driver/delivery-history/', views.driver_delivery_history, name='driver_delivery_history'),
    
    # Owner URLs
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/manage-orders/', views.manage_orders, name='manage_orders'),
    path('owner/update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('owner/manage-inventory/', views.manage_inventory, name='manage_inventory'),
    path('owner/add-water-type/', views.add_water_type, name='add_water_type'),
    path('owner/edit-water-type/<int:water_type_id>/', views.edit_water_type, name='edit_water_type'),
    path('owner/manage-drivers/', views.manage_drivers, name='manage_drivers'),
    path('owner/manage-clients/', views.manage_clients, name='manage_clients'),
]