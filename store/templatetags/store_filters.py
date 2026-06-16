from django import template

register = template.Library()

@register.filter(name='discount_percentage')
def discount_percentage(old_price, price):
    """Calculate discount percentage"""
    try:
        old_price = float(old_price)
        price = float(price)
        
        if old_price > 0 and price >= 0 and old_price > price:
            discount = ((old_price - price) / old_price) * 100
            return int(discount)
        return 0
    except (ValueError, TypeError):
        return 0