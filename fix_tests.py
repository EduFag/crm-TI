import re

with open('helpdesk/tests.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(
    r'TicketCategory\.objects\.create\(name=(.*?), is_active=(.*?)\)',
    r'TicketCategory.objects.get_or_create(name=\1, defaults={"is_active": \2})[0]',
    text
)

with open('helpdesk/tests.py', 'w', encoding='utf-8') as f:
    f.write(text)
