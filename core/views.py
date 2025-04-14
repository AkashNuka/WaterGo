from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.db.models import Count, Sum, Q
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from .models import WaterType, Order, Customer, User, Driver, Delivery, GuestOrder
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

def home(request):
    water_types = WaterType.objects.all()
    return render(request, 'core/home.html', {'water_types': water_types})

def water_type_detail(request, pk):
    water_type = get_object_or_404(WaterType, pk=pk)
    return render(request, 'core/water_type_detail.html', {'water_type': water_type})

@login_required
def role_router(request):
    """Routes users to their appropriate dashboard based on their role"""
    user = request.user
    
    if user.is_client():
        return redirect('client_dashboard')
    elif user.is_driver():
        return redirect('driver_dashboard')
    elif user.is_owner():
        return redirect('owner_dashboard')
    else:
        # Fallback for admin or undefined roles
        return redirect('home')

# CLIENT VIEWS

@login_required
def client_dashboard(request):
    """Dashboard for clients showing their orders and water options"""
    if not request.user.is_client():
        return HttpResponseForbidden("Access denied")
    
    try:
        customer = Customer.objects.get(user=request.user)
        orders = Order.objects.filter(customer=customer).order_by('-order_date')
        recent_orders = orders[:3]  # Get 3 most recent orders
        pending_orders = orders.filter(status__in=['pending', 'confirmed', 'in_transit']).count()
    except Customer.DoesNotExist:
        recent_orders = []
        pending_orders = 0
        
    water_types = WaterType.objects.all()
    
    context = {
        'customer': customer if 'customer' in locals() else None,
        'recent_orders': recent_orders,
        'pending_orders': pending_orders,
        'water_types': water_types
    }
    
    return render(request, 'core/client_dashboard.html', context)

@login_required
def place_order(request, water_type_id):
    if not request.user.is_client():
        return HttpResponseForbidden("Access denied")
        
    water_type = get_object_or_404(WaterType, pk=water_type_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        delivery_address = request.POST.get('delivery_address', '')
        
        # Get or create customer profile for the user
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={
                'address': delivery_address,
                'phone': request.POST.get('phone', '')
            }
        )
        
        # Create the order
        order = Order.objects.create(
            customer=customer,
            water_type=water_type,
            quantity=quantity,
            delivery_address=delivery_address,
            total_price=water_type.price_per_unit * quantity
        )
        
        messages.success(request, "Your order has been placed successfully!")
        return redirect('order_confirmation', order_id=order.id)
    
    return render(request, 'core/place_order.html', {'water_type': water_type})

@login_required
def order_confirmation(request, order_id):
    if not request.user.is_client():
        return HttpResponseForbidden("Access denied")
        
    order = get_object_or_404(Order, pk=order_id, customer__user=request.user)
    return render(request, 'core/order_confirmation.html', {'order': order})

@login_required
def my_orders(request):
    if not request.user.is_client():
        return HttpResponseForbidden("Access denied")
        
    try:
        customer = Customer.objects.get(user=request.user)
        orders = Order.objects.filter(customer=customer).order_by('-order_date')
    except Customer.DoesNotExist:
        orders = []
    
    return render(request, 'core/my_orders.html', {'orders': orders})

# DRIVER VIEWS

@login_required
def driver_dashboard(request):
    """Dashboard for drivers showing assigned deliveries and statistics"""
    if not request.user.is_driver():
        return HttpResponseForbidden("Access denied")
    
    try:
        driver = Driver.objects.get(user=request.user)
        
        # Get active deliveries (in transit)
        active_deliveries = Delivery.objects.filter(
            driver=driver, 
            order__status='in_transit'
        ).select_related('order')
        
        # Get deliveries completed today
        today = timezone.now().date()
        completed_today = Delivery.objects.filter(
            driver=driver,
            delivered_at__date=today
        ).count()
        
        # Get pending orders that need a driver
        available_orders = Order.objects.filter(status='confirmed')
        
    except Driver.DoesNotExist:
        active_deliveries = []
        completed_today = 0
        available_orders = []
    
    context = {
        'driver': driver if 'driver' in locals() else None,
        'active_deliveries': active_deliveries,
        'completed_today': completed_today,
        'available_orders': available_orders
    }
    
    return render(request, 'core/driver_dashboard.html', context)

@login_required
def accept_delivery(request, order_id):
    """Allow driver to accept a delivery assignment"""
    if not request.user.is_driver():
        return HttpResponseForbidden("Access denied")
    
    order = get_object_or_404(Order, pk=order_id, status='confirmed')
    driver = get_object_or_404(Driver, user=request.user)
    
    # Create or update delivery
    delivery, created = Delivery.objects.get_or_create(
        order=order,
        defaults={
            'driver': driver,
            'started_at': timezone.now()
        }
    )
    
    if not created:
        delivery.driver = driver
        delivery.started_at = timezone.now()
        delivery.save()
    
    # Update order status
    order.status = 'in_transit'
    order.save()
    
    messages.success(request, f"You've accepted the delivery for order #{order.id}")
    return redirect('driver_dashboard')

@login_required
def complete_delivery(request, delivery_id):
    """Mark a delivery as complete"""
    if not request.user.is_driver():
        return HttpResponseForbidden("Access denied")
    
    delivery = get_object_or_404(
        Delivery, 
        pk=delivery_id, 
        driver__user=request.user,
        order__status='in_transit'
    )
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        
        # Update delivery
        delivery.notes = notes
        delivery.delivered_at = timezone.now()
        delivery.save()
        
        # Update order status
        delivery.order.status = 'delivered'
        delivery.order.delivery_date = timezone.now()
        delivery.order.save()
        
        messages.success(request, f"Delivery for order #{delivery.order.id} marked as complete")
        return redirect('driver_dashboard')
    
    return render(request, 'core/complete_delivery.html', {'delivery': delivery})

@login_required
def driver_delivery_history(request):
    """Show driver's delivery history"""
    if not request.user.is_driver():
        return HttpResponseForbidden("Access denied")
    
    driver = get_object_or_404(Driver, user=request.user)
    deliveries = Delivery.objects.filter(driver=driver).order_by('-delivered_at')
    
    return render(request, 'core/driver_delivery_history.html', {'deliveries': deliveries})

# OWNER VIEWS

@login_required
def owner_dashboard(request):
    """Dashboard for business owner with enhanced analytics"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    # Basic statistics
    total_customers = Customer.objects.count()
    total_orders = Order.objects.count()
    total_guest_orders = GuestOrder.objects.count()
    
    # Revenue calculations
    regular_revenue = Order.objects.filter(status='delivered').aggregate(Sum('total_price'))['total_price__sum'] or 0
    guest_revenue = GuestOrder.objects.filter(status='delivered').aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_revenue = regular_revenue + guest_revenue
    
    # Monthly revenue data for charts
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_revenue = []
    monthly_orders = []
    
    for month in range(1, 13):
        # Regular orders revenue
        month_regular_revenue = Order.objects.filter(
            order_date__year=current_year,
            order_date__month=month,
            status='delivered'
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        # Guest orders revenue
        month_guest_revenue = GuestOrder.objects.filter(
            created_at__year=current_year,
            created_at__month=month,
            status='delivered'
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        monthly_revenue.append(month_regular_revenue + month_guest_revenue)
        
        # Order counts
        month_orders = Order.objects.filter(
            order_date__year=current_year,
            order_date__month=month
        ).count()
        month_guest_orders = GuestOrder.objects.filter(
            created_at__year=current_year,
            created_at__month=month
        ).count()
        monthly_orders.append(month_orders + month_guest_orders)
    
    # Recent orders
    recent_orders = Order.objects.all().order_by('-order_date')[:5]
    recent_guest_orders = GuestOrder.objects.all().order_by('-created_at')[:5]
    
    # Orders by status with percentages
    total_all_orders = total_orders + total_guest_orders
    
    # Regular orders status
    pending_orders = Order.objects.filter(status='pending').count()
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    in_transit_orders = Order.objects.filter(status='in_transit').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    # Guest orders status
    pending_guest_orders = GuestOrder.objects.filter(status='pending').count()
    confirmed_guest_orders = GuestOrder.objects.filter(status='confirmed').count()
    in_transit_guest_orders = GuestOrder.objects.filter(status='in_transit').count()
    delivered_guest_orders = GuestOrder.objects.filter(status='delivered').count()
    cancelled_guest_orders = GuestOrder.objects.filter(status='cancelled').count()
    
    # Calculate percentages
    def calculate_percentage(value):
        return round((value / total_all_orders * 100) if total_all_orders > 0 else 0, 1)
    
    order_status_data = {
        'pending': {
            'count': pending_orders + pending_guest_orders,
            'percentage': calculate_percentage(pending_orders + pending_guest_orders)
        },
        'confirmed': {
            'count': confirmed_orders + confirmed_guest_orders,
            'percentage': calculate_percentage(confirmed_orders + confirmed_guest_orders)
        },
        'in_transit': {
            'count': in_transit_orders + in_transit_guest_orders,
            'percentage': calculate_percentage(in_transit_orders + in_transit_guest_orders)
        },
        'delivered': {
            'count': delivered_orders + delivered_guest_orders,
            'percentage': calculate_percentage(delivered_orders + delivered_guest_orders)
        },
        'cancelled': {
            'count': cancelled_orders + cancelled_guest_orders,
            'percentage': calculate_percentage(cancelled_orders + cancelled_guest_orders)
        }
    }
    
    # Water type popularity with percentages
    water_types = WaterType.objects.all()
    water_type_data = []
    total_water_orders = Order.objects.count()
    
    for water_type in water_types:
        orders_count = Order.objects.filter(water_type=water_type).count()
        percentage = round((orders_count / total_water_orders * 100) if total_water_orders > 0 else 0, 1)
        water_type_data.append({
            'name': water_type.name,
            'count': orders_count,
            'percentage': percentage
        })
    
    # Growth metrics
    last_month = timezone.now() - timezone.timedelta(days=30)
    
    # Customer growth
    new_customers_month = Customer.objects.filter(created_at__gte=last_month).count()
    customer_growth = round((new_customers_month / total_customers * 100) if total_customers > 0 else 0, 1)
    
    # Revenue growth
    last_month_order_revenue = Order.objects.filter(order_date__gte=last_month, status='delivered').aggregate(Sum('total_price'))['total_price__sum'] or 0
    last_month_guest_revenue = GuestOrder.objects.filter(created_at__gte=last_month, status='delivered').aggregate(Sum('total_price'))['total_price__sum'] or 0
    last_month_revenue = last_month_order_revenue + last_month_guest_revenue
    
    prev_month_order_revenue = Order.objects.filter(
        order_date__lt=last_month,
        order_date__gte=last_month - timezone.timedelta(days=30),
        status='delivered'
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    prev_month_guest_revenue = GuestOrder.objects.filter(
        created_at__lt=last_month,
        created_at__gte=last_month - timezone.timedelta(days=30),
        status='delivered'
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    previous_month_revenue = prev_month_order_revenue + prev_month_guest_revenue
    
    revenue_growth = round(((last_month_revenue - previous_month_revenue) / previous_month_revenue * 100) if previous_month_revenue > 0 else 0, 1)
    
    context = {
        'total_customers': total_customers,
        'total_orders': total_all_orders,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'monthly_orders': monthly_orders,
        'recent_orders': recent_orders,
        'recent_guest_orders': recent_guest_orders,
        'order_status_data': order_status_data,
        'water_type_data': water_type_data,
        'customer_growth': customer_growth,
        'revenue_growth': revenue_growth,
        'regular_revenue': regular_revenue,
        'guest_revenue': guest_revenue,
        'current_month': current_month,
        'current_year': current_year
    }
    
    return render(request, 'core/owner_dashboard.html', context)

@login_required
def manage_drivers(request):
    """Allow owner to manage drivers"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    drivers = Driver.objects.all().select_related('user')
    
    return render(request, 'core/manage_drivers.html', {
        'drivers': drivers
    })

@login_required
def manage_clients(request):
    """Allow owner to manage clients"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    clients = Customer.objects.all().select_related('user')
    
    return render(request, 'core/manage_clients.html', {
        'clients': clients
    })

@login_required
def manage_orders(request):
    """Allow owner to manage all orders"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    status_filter = request.GET.get('status', '')
    
    if status_filter and status_filter != 'all':
        orders = Order.objects.filter(status=status_filter).order_by('-order_date')
    else:
        orders = Order.objects.all().order_by('-order_date')
    
    return render(request, 'core/manage_orders.html', {
        'orders': orders,
        'current_filter': status_filter
    })

@login_required
def update_order_status(request, order_id):
    """Allow owner to update an order's status"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    order = get_object_or_404(Order, pk=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [s[0] for s in Order.STATUS_CHOICES]:
            order.status = new_status
            order.save()
            
            # If confirming an order, prepare it for delivery assignment
            if new_status == 'confirmed' and not hasattr(order, 'delivery'):
                Delivery.objects.create(order=order)
            
            messages.success(request, f"Order #{order.id} status updated to {new_status}")
        else:
            messages.error(request, "Invalid status selected")
            
        return redirect('manage_orders')
    
    return render(request, 'core/update_order_status.html', {'order': order})

@login_required
def manage_inventory(request):
    """Allow owner to manage water types/inventory"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    water_types = WaterType.objects.all()
    
    return render(request, 'core/manage_inventory.html', {'water_types': water_types})

@login_required
def add_water_type(request):
    """Allow owner to add a new water type"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        image_url = request.POST.get('image_url')
        
        WaterType.objects.create(
            name=name,
            description=description,
            price_per_unit=price,
            image_url=image_url
        )
        
        messages.success(request, f"Added new water type: {name}")
        return redirect('manage_inventory')
    
    return render(request, 'core/add_water_type.html')

@login_required
def edit_water_type(request, water_type_id):
    """Allow owner to edit a water type"""
    if not request.user.is_owner():
        return HttpResponseForbidden("Access denied")
    
    water_type = get_object_or_404(WaterType, pk=water_type_id)
    
    if request.method == 'POST':
        water_type.name = request.POST.get('name')
        water_type.description = request.POST.get('description')
        water_type.price_per_unit = request.POST.get('price')
        water_type.image_url = request.POST.get('image_url')
        water_type.save()
        
        messages.success(request, f"Updated water type: {water_type.name}")
        return redirect('manage_inventory')
    
    return render(request, 'core/edit_water_type.html', {'water_type': water_type})

# AUTHENTICATION VIEWS

def client_signup(request):
    """Client registration view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('client_signup')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('client_signup')
        
        # Create user and customer profile
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='CLIENT'
        )
        
        Customer.objects.create(
            user=user,
            address=address,
            phone=phone
        )
        
        # Log the user in
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('client_dashboard')
    
    return render(request, 'core/client_signup.html')

def driver_signup(request):
    """Driver registration view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        license_number = request.POST.get('license_number')
        vehicle_info = request.POST.get('vehicle_info')
        phone = request.POST.get('phone')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('driver_signup')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('driver_signup')
        
        # Create user and driver profile
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='DRIVER'
        )
        
        Driver.objects.create(
            user=user,
            license_number=license_number,
            vehicle_info=vehicle_info,
            phone=phone
        )
        
        # Log the user in
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Driver registration successful!")
            return redirect('driver_dashboard')
    
    return render(request, 'core/driver_signup.html')

def create_guest_order(request):
    """Handle guest water tanker orders"""
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        tanker_count = int(request.POST.get('tanker_count', 1))

        # Create guest order
        guest_order = GuestOrder.objects.create(
            name=name,
            phone=phone,
            address=address,
            tanker_count=tanker_count
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Order created successfully',
            'order_id': guest_order.id
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# API endpoints
@login_required
def get_order_details(request, order_id):
    """API endpoint to get order details"""
    try:
        order = Order.objects.get(pk=order_id, customer__user=request.user)
        data = {
            'id': order.id,
            'water_type': {
                'name': order.water_type.name,
                'price_per_unit': float(order.water_type.price_per_unit)
            },
            'quantity': order.quantity,
            'total_price': float(order.total_price),
            'status': order.status,
            'delivery_address': order.delivery_address,
            'order_date': order.order_date.isoformat(),
            'delivery_date': order.delivery_date.isoformat() if order.delivery_date else None
        }
        return JsonResponse(data)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def cancel_order(request, order_id):
    """API endpoint to cancel an order"""
    try:
        order = Order.objects.get(pk=order_id, customer__user=request.user, status__in=['pending', 'confirmed'])
        order.status = 'cancelled'
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order cancelled successfully'})
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Order not found or cannot be cancelled'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
