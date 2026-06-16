from django.db import models
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver


from vendor.models import Vendor
from userauths.models import User, Profile

from shortuuid.django_fields import ShortUUIDField


# Create your models here.

class Category(models.Model):
    title = models.CharField(max_length=100)
    image = models.FileField(upload_to="category", default="category.jpg", null=True, blank=True)
    active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "Category"
        ordering = ['title']


class Product(models.Model):
    STATUS = (
        ("draft","Draft"),
        ("disabled","Disabled"),
        ("in_review","In Review"),
        ("published","Published"),
    )
    title = models.CharField(max_length=100)
    image = models.FileField(upload_to="products", default="product.jpg", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    old_price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    shipping_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    stock_qty = models.PositiveIntegerField(default=1)
    in_stock = models.BooleanField(default=True)
    status = models.CharField(max_length=100, choices=STATUS, default="published")
    featured = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, null=True, blank=True)  # Changed to DecimalField
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    pid = ShortUUIDField(unique=True, length=10, alphabet="abcdefghijklmnopqrstwxyz")
    slug = models.SlugField(null=True, blank=True, unique=True)  # Added unique=True
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    def orders(self):
        return CartOrderItem.objects.filter(product=self).count()
    
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.old_price and self.old_price > self.price:
            discount = ((self.old_price - self.price) / self.old_price) * 100
            return int(discount)
        return 0
    
    def product_rating(self):
        """Calculate average rating - safe for unsaved instances"""
        if self.pk:  # Only query if product is saved
            product_rating = Review.objects.filter(product=self).aggregate(avg_rating=models.Avg("rating"))
            return product_rating['avg_rating'] or 0.00
        return 0.00

    def rating_count(self):
        if self.pk:
            return Review.objects.filter(product=self).count()  
        return 0
    
    def gallery(self):
        if self.pk:
            return Gallery.objects.filter(product=self)
        return Gallery.objects.none()
    
    def specification(self):
        if self.pk:
            return Specification.objects.filter(product=self)
        return Specification.objects.none()
    
    def size(self):
        if self.pk:
            return Size.objects.filter(product=self)
        return Size.objects.none()
    
    def color(self):
        if self.pk:
            return Color.objects.filter(product=self)
        return Color.objects.none()
    
    def save(self, *args, **kwargs):
        # Generate slug if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Only update rating if product already exists in database
        if self.pk:
            self.rating = self.product_rating()
        
        super(Product, self).save(*args, **kwargs)
    
class Gallery(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # Changed to CASCADE and allow blank
    image = models.FileField(upload_to="products", default="product.jpg", null=True, blank=True)
    active = models.BooleanField(default=True)
    g_id = ShortUUIDField(unique=True, length=10, alphabet="abcdefg12345")

    def __str__(self):
        if self.product:
            return self.product.title
        return f"Gallery {self.g_id}"
    
    class Meta:
        verbose_name_plural = "Product Image"

class Specification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # Changed to CASCADE
    title = models.CharField(max_length=1000, null=True, blank=True)
    content = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return self.title if self.title else "Specification"
    
class Size(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # Changed to CASCADE
    name = models.CharField(max_length=1000, null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)

    def __str__(self):
        return self.name if self.name else "Size"
    
class Color(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # Changed to CASCADE
    name = models.CharField(max_length=1000, null=True, blank=True)
    color_code = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return self.name if self.name else "Color"
    


class Cart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    qty = models.PositiveIntegerField(default=0)
    price = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    sub_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    shipping_amount = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    country = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    cart_id = models.CharField(max_length=1000, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cart_id} - {self.product.title}"
    

class CartOrder(models.Model):
    PAYMENT_STATUS = (
        ("paid","Paid"),
        ("pending","Pending"),
        ("processing","Processing"),
        ("cancelled","Cancelled"),
    )

    ORDER_STATUS = (
        ("Pending","Pending"),
        ("Fullfilled","Fullfilled"),
        ("Cancelled","Cancelled"),
    )
    vendor = models.ManyToManyField(Vendor, blank=True)
    buyer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sub_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    shipping_amount = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)

    payment_status = models.CharField(choices=PAYMENT_STATUS, max_length=100, default="pending")
    order_status = models.CharField(choices=ORDER_STATUS, max_length=100, default="pending")
    # Copun 
    initial_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    saved = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    # Bio Data
    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    mobile = models.CharField(max_length=100, null=True, blank=True)
    # Shipping Address 
    address = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    stripe_session_id = models.CharField(max_length=1000, null=True, blank=True)

    oid = ShortUUIDField(unique=True, length=10, max_length=25, alphabet="abcdefg12345")
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.oid
    
    def orderitem(self):
        return CartOrderItem.objects.filter(order=self)
    

class CartOrderItem(models.Model):
    order = models.ForeignKey(CartOrder, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=0)
    price = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    sub_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    shipping_amount = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    service_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    tax_fee = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    country = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=100, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)

    # Coupon
    coupon = models.ManyToManyField("store.Coupon", blank=True)
    initial_total = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    saved = models.DecimalField(default=0.00, max_digits=12, decimal_places=2)
    oid = ShortUUIDField(unique=True, length=10, max_length=25, alphabet="abcdefg12345")
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.oid
    

class ProductFeq(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    email = models.EmailField(null=True, blank=True)
    question = models.CharField(max_length=1000)
    answer = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.question
    
    class Meta:
        verbose_name_plural = "Product FAQs"

class Review(models.Model):
    RATTING = (
        (1,"1 Star"),
        (2,"2 Star"),
        (3,"3 Star"),
        (4,"4 Star"),
        (5,"5 Star"),

    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    review = models.TextField()
    reply = models.CharField(null=True, blank=True, max_length=1000)
    rating = models.IntegerField(default=None, choices=RATTING)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    
    def __str__(self):
        return self.product.title
    
    class Meta:
        verbose_name_plural = "Rating & Reviews"

    def profile(self):
        return Profile.objects.get(user=self.user)
    
@receiver(post_save, sender=Review)
def update_product_rating(sender, instance, **kwargs):
    if instance.product:
        instance.product.save()



class Wshlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product.title
    

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(CartOrder, on_delete=models.SET_NULL, null=True, blank=True)
    order_item = models.ForeignKey(CartOrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    seen = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.order:
            return self.order.oid
        else:
            f"Notification - {self.pk}"

class Coupon(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    user_by = models.ManyToManyField(User, blank=True) 
    code = models.CharField(max_length=1000)
    discount = models.IntegerField(default=1)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code
    


class Tax(models.Model):
    country = models.CharField(max_length=100)
    rate = models.IntegerField(default=5, help_text="Number added here are in pecentage e.g 5%")
    active = models.BooleanField(default=True)
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.country
    
    class Meta:
        verbose_name_plural = "Taxes"
        ordering = ['country']

# models.py - Add this to your store/models.py

class Banner(models.Model):
    """Banner model for home page and other sections"""
    
    POSITION_CHOICES = (
        ('home', 'Home Page'),
        ('shop', 'Shop Page'),
        ('product', 'Product Page'),
        ('sidebar', 'Sidebar'),
    )
    
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Images
    image = models.ImageField(upload_to='banners/', help_text="Main banner image")
    mobile_image = models.ImageField(upload_to='banners/mobile/', blank=True, null=True, help_text="Mobile version")
    
    # Links and buttons
    button_text = models.CharField(max_length=50, default='Shop Now')
    button_link = models.CharField(max_length=500, default='/store/shop/')
    button_color = models.CharField(
        max_length=20, 
        choices=(
            ('primary', 'Primary'),
            ('danger', 'Danger'),
            ('success', 'Success'),
            ('warning', 'Warning'),
            ('info', 'Info'),
            ('dark', 'Dark'),
        ),
        default='primary'
    )
    
    # Display settings
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='home')
    order = models.IntegerField(default=0, help_text="Order to display banners")
    
    # Status
    active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'
    
    def __str__(self):
        return self.title
    
    def get_image_url(self):
        if self.image:
            return self.image.url
        return '/static/images/default-banner.jpg'
    


class Newsletter(models.Model):
    """Newsletter subscription model"""
    email = models.EmailField(unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Newsletter Subscriber'
        verbose_name_plural = 'Newsletter Subscribers'
    
    def __str__(self):
        return self.email
    


