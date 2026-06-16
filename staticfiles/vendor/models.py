from django.db import models
from userauths.models import User
from django.utils.text import slugify
from shortuuid.django_fields import ShortUUIDField

# Create your models here.

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    image = models.FileField(upload_to="vendor", null=True, blank=True, default="vendor.jpj")
    name = models.CharField(max_length=100, help_text="Shop Name", null=True, blank=True)
    email = models.CharField(max_length=100, help_text="Shop Email", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    mobile = models.CharField(max_length=100, help_text="Shop Mobile Number", null=True, blank=True)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)
    vid = ShortUUIDField(unique=True, length=10, max_length=20, alphabet="abcdefghijklmnopqrstuvxyz")
    slug = models.SlugField(unique=True, max_length=500)

    class Meta:
        verbose_name_plural = "Vendors"

    def __str__(self):
        return str(self.name)
    
    def save(self, *args, **kwargs):
        if self.slug == "" or self.slug == None:
            self.slug = slugify(self.name)
        super(Vendor, self).save(*args, **kwargs)

