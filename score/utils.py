import uuid
from django.conf import settings
import os
from rest_framework import serializers
import secrets
from django.core.mail import send_mail

def get_media_url(file):
    return settings.MEDIA_HOST + file.url

def create_file(filebuffer):
    ext = os.path.splitext(filebuffer.name)[1]
    new_file = filebuffer
    new_file.name = f"{str(uuid.uuid4())}{ext}"
    return new_file

class FileSerializer(serializers.Field):
    def to_internal_value(self, data):
        return super().to_internal_value(data)
    
    def to_representation(self, value):
        return get_media_url(value)


def generate_random_code():
    return secrets.token_urlsafe(8)

def send_email(data: dict):
    send_mail(
        subject=data.get("subject"),
        message=data.get("message"),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[data.get("to")],
        fail_silently=True
    )
