from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import Customer, WaterType, Cart, CartItem, Order, OrderItem, User as CoreUser

User = get_user_model()

class ModelTestDataSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create Users
        cls.client_user = User.objects.create_user(
            username='testclient', 
            email='client@example.com', 
            password='password123', 
            role=CoreUser.Role.CLIENT
        )
        cls.other_client_user = User.objects.create_user(
            username='otherclient',
            email='otherclient@example.com',
            password='password123',
            role=CoreUser.Role.CLIENT
        )

        # Create Customer profiles
        cls.customer = Customer.objects.create(
            user=cls.client_user, 
            address='123 Test St, Testville', 
            phone='555-1234'
        )
        cls.other_customer = Customer.objects.create(
            user=cls.other_client_user,
            address='456 Other St, Othertown',
            phone='555-5678'
        )

        # Create WaterTypes
        cls.water_type1 = WaterType.objects.create(
            name='Spring Water', 
            description='Refreshing spring water.', 
            price_per_unit=Decimal('10.00')
        )
        cls.water_type2 = WaterType.objects.create(
            name='Mineral Water', 
            description='Rich in minerals.', 
            price_per_unit=Decimal('15.00')
        )
        
        # Create a Cart for the main test client
        cls.cart = Cart.objects.create(user=cls.client_user)


class CartModelTests(ModelTestDataSetup):
    def test_cart_creation(self):
        self.assertIsNotNone(self.cart.id)
        self.assertEqual(self.cart.user, self.client_user)
        self.assertIsNotNone(self.cart.created_at)
        self.assertIsNotNone(self.cart.updated_at)

    def test_cart_str(self):
        self.assertEqual(str(self.cart), f"Cart for {self.client_user.username}")

class CartItemModelTests(ModelTestDataSetup):
    def test_cart_item_creation(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            water_type=self.water_type1,
            quantity=2
        )
        self.assertIsNotNone(cart_item.id)
        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.water_type, self.water_type1)
        self.assertEqual(cart_item.quantity, 2)

    def test_cart_item_str(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            water_type=self.water_type1,
            quantity=3
        )
        expected_str = f"3 of {self.water_type1.name} in cart for {self.cart.user.username}"
        self.assertEqual(str(cart_item), expected_str)

    def test_cart_item_default_quantity(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            water_type=self.water_type1
            # quantity field uses default=1
        )
        self.assertEqual(cart_item.quantity, 1)


class OrderModelTests(ModelTestDataSetup):
    def test_order_creation(self):
        order = Order.objects.create(
            customer=self.customer,
            delivery_address='123 Test St, Testville',
            total_price=Decimal('0.00') # Default or to be calculated
        )
        self.assertIsNotNone(order.id)
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.total_price, Decimal('0.00'))
        self.assertEqual(order.status, 'pending') # Default status
        self.assertIsNotNone(order.order_date)

    def test_order_str(self):
        order = Order.objects.create(
            customer=self.customer,
            delivery_address='123 Test St, Testville',
            total_price=Decimal('50.00')
        )
        expected_str = f"Order #{order.id} by {self.customer.user.username}"
        self.assertEqual(str(order), expected_str)

class OrderItemModelTests(ModelTestDataSetup):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.order = Order.objects.create(
            customer=cls.customer,
            delivery_address='123 Test St, Testville',
            total_price=Decimal('0.00')
        )

    def test_order_item_creation(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            water_type=self.water_type1,
            quantity=3,
            price_at_purchase=self.water_type1.price_per_unit
        )
        self.assertIsNotNone(order_item.id)
        self.assertEqual(order_item.order, self.order)
        self.assertEqual(order_item.water_type, self.water_type1)
        self.assertEqual(order_item.quantity, 3)
        self.assertEqual(order_item.price_at_purchase, self.water_type1.price_per_unit)

    def test_order_item_str(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            water_type=self.water_type1,
            quantity=2,
            price_at_purchase=self.water_type1.price_per_unit
        )
        expected_str = f"2 of {self.water_type1.name} for Order #{self.order.id}"
        self.assertEqual(str(order_item), expected_str)

    def test_get_total_item_price(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            water_type=self.water_type1,
            quantity=3,
            price_at_purchase=Decimal('10.00')
        )
        self.assertEqual(order_item.get_total_item_price(), Decimal('30.00'))

        order_item_2 = OrderItem.objects.create(
            order=self.order,
            water_type=self.water_type2,
            quantity=1,
            price_at_purchase=Decimal('15.00')
        )
        self.assertEqual(order_item_2.get_total_item_price(), Decimal('15.00'))


class CartViewTests(ModelTestDataSetup):
    def setUp(self):
        self.client = Client()
        # Login the main test client for most tests
        self.client.login(username=self.client_user.username, password='password123')
        # Ensure cart exists and is empty for the logged-in user before each test
        self.cart, _ = Cart.objects.get_or_create(user=self.client_user)
        self.cart.items.all().delete()

    def test_view_cart_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('view_cart'))
        self.assertEqual(response.status_code, 302) # Should redirect to login
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_view_empty_cart(self):
        response = self.client.get(reverse('view_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your cart is empty.")
        self.assertContains(response, "Total Cart Price:")
        self.assertContains(response, "₹0.00") # Check total price is zero

    def test_view_cart_with_items(self):
        item1 = CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=2) # 2 * 10 = 20
        item2 = CartItem.objects.create(cart=self.cart, water_type=self.water_type2, quantity=1) # 1 * 15 = 15
        
        response = self.client.get(reverse('view_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.water_type1.name)
        self.assertContains(response, self.water_type2.name)
        self.assertContains(response, f"value=\"{item1.quantity}\"")
        self.assertContains(response, f"value=\"{item2.quantity}\"")
        # Check for item total (2 * 10.00 = 20.00)
        self.assertContains(response, "₹20.00") 
        # Check for item total (1 * 15.00 = 15.00)
        self.assertContains(response, "₹15.00")
        # Check for overall total price
        self.assertContains(response, "Total Cart Price:")
        self.assertContains(response, "₹35.00") 

    def test_add_to_cart_new_item(self):
        response = self.client.post(reverse('add_to_cart', args=[self.water_type1.id]), {'quantity': 2})
        self.assertEqual(response.status_code, 302) # Redirects to view_cart
        self.assertRedirects(response, reverse('view_cart'))
        
        self.assertEqual(self.cart.items.count(), 1)
        item = self.cart.items.first()
        self.assertEqual(item.water_type, self.water_type1)
        self.assertEqual(item.quantity, 2)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"{self.water_type1.name} added to your cart.")

    def test_add_to_cart_existing_item(self):
        CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=1)
        response = self.client.post(reverse('add_to_cart', args=[self.water_type1.id]), {'quantity': 3})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('view_cart'))
        
        self.assertEqual(self.cart.items.count(), 1)
        item = self.cart.items.first()
        self.assertEqual(item.water_type, self.water_type1)
        self.assertEqual(item.quantity, 4) # 1 (existing) + 3 (added) = 4
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"Updated quantity for {self.water_type1.name} in your cart.")

    def test_add_to_cart_invalid_quantity(self):
        response = self.client.post(reverse('add_to_cart', args=[self.water_type1.id]), {'quantity': 'abc'})
        self.assertEqual(response.status_code, 302) # Should redirect back
        self.assertEqual(self.cart.items.count(), 0) # No item added
        messages = list(response.context['messages'])
        self.assertTrue(any("Invalid quantity" in str(msg) for msg in messages))

        response = self.client.post(reverse('add_to_cart', args=[self.water_type1.id]), {'quantity': '0'})
        self.assertEqual(response.status_code, 302) # Should redirect back
        self.assertEqual(self.cart.items.count(), 0) # No item added
        messages = list(response.context['messages'])
        self.assertTrue(any("Quantity must be a positive integer" in str(msg) for msg in messages))

    def test_add_to_cart_invalid_water_type_id(self):
        invalid_id = 9999
        response = self.client.post(reverse('add_to_cart', args=[invalid_id]), {'quantity': 1})
        self.assertEqual(response.status_code, 404) # Not Found
        self.assertEqual(self.cart.items.count(), 0)

    def test_update_cart_item_quantity(self):
        item = CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=2)
        response = self.client.post(reverse('update_cart_item', args=[item.id]), {'quantity': 5})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('view_cart'))
        
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"Quantity for {self.water_type1.name} updated.")

    def test_update_cart_item_invalid_quantity(self):
        item = CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=2)
        response = self.client.post(reverse('update_cart_item', args=[item.id]), {'quantity': '0'})
        self.assertEqual(response.status_code, 302) # Redirects
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2) # Quantity should not change
        messages = list(response.context['messages'])
        self.assertTrue(any("Quantity must be at least 1" in str(msg) for msg in messages))

    def test_update_cart_item_not_users_cart(self):
        # Create item in another user's cart
        other_cart = Cart.objects.create(user=self.other_client_user)
        other_item = CartItem.objects.create(cart=other_cart, water_type=self.water_type1, quantity=1)
        
        response = self.client.post(reverse('update_cart_item', args=[other_item.id]), {'quantity': 3})
        self.assertEqual(response.status_code, 404) # Item not found for this user
        other_item.refresh_from_db()
        self.assertEqual(other_item.quantity, 1) # Quantity should not change

    def test_remove_from_cart(self):
        item = CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=1)
        self.assertEqual(self.cart.items.count(), 1)
        
        response = self.client.post(reverse('remove_from_cart', args=[item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('view_cart'))
        
        self.assertEqual(self.cart.items.count(), 0)
        self.assertFalse(CartItem.objects.filter(id=item.id).exists()) # Item deleted
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"{self.water_type1.name} removed from your cart.")

    def test_remove_from_cart_item_not_users(self):
        other_cart = Cart.objects.create(user=self.other_client_user)
        other_item = CartItem.objects.create(cart=other_cart, water_type=self.water_type1, quantity=1)

        response = self.client.post(reverse('remove_from_cart', args=[other_item.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(id=other_item.id).exists()) # Item not deleted

class PlaceOrderViewTests(ModelTestDataSetup):
    def setUp(self):
        self.client = Client()
        self.client.login(username=self.client_user.username, password='password123')
        self.cart, _ = Cart.objects.get_or_create(user=self.client_user)
        self.cart.items.all().delete() # Clear cart

    def test_place_order_get_empty_cart(self):
        response = self.client.get(reverse('place_order'))
        self.assertEqual(response.status_code, 302) # Redirects to view_cart
        self.assertRedirects(response, reverse('view_cart'))
        messages_list = list(response.context['messages'])
        self.assertTrue(any("Your cart is empty" in str(msg) for msg in messages_list))


    def test_place_order_get_with_items(self):
        CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=1)
        response = self.client.get(reverse('place_order'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Checkout")
        self.assertContains(response, self.water_type1.name)
        self.assertContains(response, "Delivery Address")
        self.assertContains(response, self.customer.address) # Pre-filled address

    def test_place_order_post_successful(self):
        CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=2) # 2 * 10 = 20
        CartItem.objects.create(cart=self.cart, water_type=self.water_type2, quantity=1) # 1 * 15 = 15
        
        initial_order_count = Order.objects.count()
        initial_order_item_count = OrderItem.objects.count()

        post_data = {
            'delivery_address': 'New Address, Test City',
            'phone': '555-9999',
            'latitude': '12.3456',
            'longitude': '78.9101'
        }
        response = self.client.post(reverse('place_order'), post_data)
        
        self.assertEqual(Order.objects.count(), initial_order_count + 1)
        self.assertEqual(OrderItem.objects.count(), initial_order_item_count + 2)
        
        new_order = Order.objects.latest('order_date')
        self.assertEqual(response.status_code, 302) # Redirects to order_confirmation
        self.assertRedirects(response, reverse('order_confirmation', args=[new_order.id]))
        
        self.assertEqual(new_order.customer, self.customer)
        self.assertEqual(new_order.delivery_address, post_data['delivery_address'])
        self.assertEqual(str(new_order.latitude), post_data['latitude'])
        self.assertEqual(str(new_order.longitude), post_data['longitude'])
        self.assertEqual(new_order.items.count(), 2)
        
        # Check total price
        expected_total_price = (self.water_type1.price_per_unit * 2) + (self.water_type2.price_per_unit * 1)
        self.assertEqual(new_order.total_price, expected_total_price)

        # Check OrderItems
        oi1 = new_order.items.get(water_type=self.water_type1)
        oi2 = new_order.items.get(water_type=self.water_type2)
        self.assertEqual(oi1.quantity, 2)
        self.assertEqual(oi1.price_at_purchase, self.water_type1.price_per_unit)
        self.assertEqual(oi2.quantity, 1)
        self.assertEqual(oi2.price_at_purchase, self.water_type2.price_per_unit)

        # Check cart is cleared
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.items.count(), 0)

        messages = list(response.context['messages'])
        self.assertTrue(any("Your order has been placed successfully!" in str(m) for m in messages))

        # Check customer address and phone are updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.address, post_data['delivery_address'])
        self.assertEqual(self.customer.phone, post_data['phone'])


    def test_place_order_post_empty_cart(self):
        response = self.client.post(reverse('place_order'), {'delivery_address': 'Some Address'})
        self.assertEqual(response.status_code, 302) # Redirects to view_cart
        self.assertRedirects(response, reverse('view_cart'))
        messages = list(response.context['messages'])
        self.assertTrue(any("Your cart is empty" in str(m) for m in messages))

    def test_place_order_post_missing_address(self):
        CartItem.objects.create(cart=self.cart, water_type=self.water_type1, quantity=1)
        response = self.client.post(reverse('place_order'), {'delivery_address': ''}) # Empty address
        self.assertEqual(response.status_code, 200) # Stays on place_order page
        self.assertContains(response, "Delivery address is required.") # Error message
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0) # No order created
```

I have written tests for:
- **Models**: `Cart`, `CartItem`, `Order`, `OrderItem` (creation, string representation, specific methods/defaults).
- **Views**:
    - Authentication for `view_cart`.
    - `view_cart`: Empty and with items.
    - `add_to_cart`: New item, existing item, invalid quantity, invalid water type.
    - `update_cart_item`: Valid update, invalid quantity, item not belonging to user.
    - `remove_from_cart`: Valid removal, item not belonging to user.
    - `place_order`:
        - GET: Empty cart (redirect), with items (displays page).
        - POST: Successful order (checks Order, OrderItems, total price, cart clearing, customer info update, redirection).
        - POST: Empty cart (redirect).
        - POST: Missing address (shows error, stays on page).

I've used `setUpTestData` for shared data and `setUp` for client login and cart clearing per test method where applicable.
The tests cover core logic and common scenarios as requested.
I will now submit the task.
