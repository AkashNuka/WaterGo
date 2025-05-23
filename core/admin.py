from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Customer, WaterType, Order, OrderItem, Delivery, Driver, Cart, CartItem

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
    list_filter = ('created_at',)

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'vehicle_info', 'phone', 'created_at')
    search_fields = ('user__username', 'user__email', 'license_number', 'phone')
    list_filter = ('created_at',)

@admin.register(WaterType)
class WaterTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_unit')
    search_fields = ('name',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1 # Number of empty forms to display
    readonly_fields = ('price_at_purchase',) # Price at purchase shouldn't be changed here

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total_price', 'status', 'order_date')
    list_filter = ('status', 'order_date')
    search_fields = ('customer__user__username', 'customer__user__email',)
    readonly_fields = ('total_price',) # total_price is calculated
    inlines = [OrderItemInline]

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'water_type', 'quantity', 'price_at_purchase')
    search_fields = ('order__id', 'water_type__name')

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('order', 'driver', 'delivered_at')
    list_filter = ('delivered_at',)
    search_fields = ('order__id', 'driver__user__username')

# Register the custom user model
admin.site.register(User, CustomUserAdmin)
