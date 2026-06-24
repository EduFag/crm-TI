import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
client = Client(SERVER_NAME='127.0.0.1')
user = User.objects.first()
client.force_login(user)

response = client.get('/helpdesk/history/')
print("Status Code:", response.status_code)
if response.status_code == 500:
    print(response.content.decode('utf-8'))
