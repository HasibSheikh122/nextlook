from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Product, Gallery, Specification, Size, Color,
    Cart, CartOrder, CartOrderItem, ProductFeq, Review, Notification, Coupon, Tax
)

class GalleryInline(admin.TabularInline):
    model = Gallery
    extra = 1
    fields = ['image', 'active']

class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 1
    fields = ['title', 'content']

class SizeInline(admin.TabularInline):
    model = Size
    extra = 1
    fields = ['name', 'price']

class ColorInline(admin.TabularInline):
    model = Color
    extra = 1
    fields = ['name', 'color_code']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'active', 'slug']
    list_filter = ['active']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['active']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'vendor', 'price','old_price', 'stock_qty', 'in_stock', 'status', 'featured', 'views', 'rating']
    list_filter = ['status', 'featured', 'in_stock', 'category', 'vendor', 'date']
    search_fields = ['title', 'description', 'pid', 'vendor__user__email']
    list_editable = ['price','old_price', 'stock_qty', 'in_stock', 'status', 'featured']
    readonly_fields = ['pid', 'views', 'rating', 'display_image']
    prepopulated_fields = {'slug': ('title',)}
    
    inlines = [GalleryInline, SpecificationInline, SizeInline, ColorInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'image', 'display_image', 'description', 'category', 'vendor')
        }),
        ('Pricing', {
            'fields': ('price', 'old_price', 'shipping_amount')
        }),
        ('Inventory', {
            'fields': ('stock_qty', 'in_stock')
        }),
        ('Status', {
            'fields': ('status', 'featured')
        }),
        ('Metrics', {
            'fields': ('pid', 'views', 'rating'),
            'classes': ('collapse',)
        }),
    )
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return "No Image"
    display_image.short_description = 'Preview'

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'active']
    list_filter = ['active', 'product']
    search_fields = ['product__title']
    list_editable = ['active']

@admin.register(Specification)
class SpecificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'product', 'content']
    search_fields = ['title', 'product__title']

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'price']
    search_fields = ['name', 'product__title']

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'color_display', 'color_code']
    search_fields = ['name', 'product__title']
    
    def color_display(self, obj):
        return format_html('<div style="width: 30px; height: 30px; background-color: {}; border-radius: 5px;"></div>', obj.color_code)
    color_display.short_description = 'Color'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['cart_id', 'product', 'user', 'qty', 'price', 'total', 'date']
    list_filter = ['date', 'country']
    search_fields = ['cart_id', 'product__title', 'user__email']
    readonly_fields = ['cart_id', 'date']

@admin.register(CartOrder)
class CartOrderAdmin(admin.ModelAdmin):
    list_display = ['oid', 'buyer', 'total', 'payment_status', 'order_status', 'date']
    list_filter = ['payment_status', 'order_status', 'date']
    search_fields = ['oid', 'buyer__email', 'full_name', 'email']
    readonly_fields = ['oid', 'date']
    list_editable = ['payment_status', 'order_status']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('oid', 'buyer', 'vendor')
        }),
        ('Payment', {
            'fields': ('payment_status', 'order_status', 'stripe_session_id')
        }),
        ('Amount Details', {
            'fields': ('sub_total', 'shipping_amount', 'tax_fee', 'service_fee', 'total', 'initial_total', 'saved')
        }),
        ('Shipping Information', {
            'fields': ('full_name', 'email', 'mobile', 'address', 'city', 'state', 'country')
        }),
        ('Timestamps', {
            'fields': ('date',),
            'classes': ('collapse',)
        }),
    )

@admin.register(CartOrderItem)
class CartOrderItemAdmin(admin.ModelAdmin):
    list_display = ['oid', 'order', 'product', 'qty', 'price', 'total', 'vendor', 'date']
    list_filter = ['date', 'vendor', 'size', 'color']
    search_fields = ['oid', 'order__oid', 'product__title']
    readonly_fields = ['oid', 'date']

@admin.register(ProductFeq)
class ProductFeqAdmin(admin.ModelAdmin):
    list_display = ['question', 'product', 'user', 'active', 'date']
    list_filter = ['active', 'date', 'product']
    search_fields = ['question', 'answer', 'user__email']
    list_editable = ['active']
    readonly_fields = ['date']
    
    fieldsets = (
        ('Question', {
            'fields': ('product', 'user', 'email', 'question')
        }),
        ('Answer', {
            'fields': ('answer', 'active')
        }),
        ('Timestamps', {
            'fields': ('date',)
        }),
    )

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'review_preview', 'active', 'date']
    list_filter = ['rating', 'active', 'date', 'product']
    search_fields = ['review', 'user__email', 'product__title']
    list_editable = ['active']
    readonly_fields = ['date']
    
    def review_preview(self, obj):
        return obj.review[:50] + '...' if len(obj.review) > 50 else obj.review
    review_preview.short_description = 'Review'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'vendor', 'order', 'seen', 'date']
    list_filter = ['seen', 'date']
    search_fields = ['user__email', 'vendor__user__email', 'order__oid']
    list_editable = ['seen']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'vendor', 'discount', 'active', 'date']
    list_filter = ['active', 'date', 'vendor']
    search_fields = ['code', 'vendor__user__email']
    list_editable = ['active', 'discount']
    filter_horizontal = ['user_by']

@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ['country', 'rate', 'active', 'data']
    list_filter = ['active', 'data']
    search_fields = ['country']
    list_editable = ['rate', 'active']



# admin.py - Simple version without custom styling

from django.contrib import admin
from django.utils.html import format_html
from .models import Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'image_preview', 'order', 'active', 'created_at']
    list_filter = ['position', 'active', 'created_at']
    search_fields = ['title', 'subtitle', 'description']
    list_editable = ['order', 'active']
    list_per_page = 20
    ordering = ['order', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subtitle', 'description', 'position')
        }),
        ('Images', {
            'fields': ('image', 'mobile_image')
        }),
        ('Button Settings', {
            'fields': ('button_text', 'button_link', 'button_color')
        }),
        ('Display Settings', {
            'fields': ('order', 'active')
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'




