import urllib.request
import urllib.error

try:
    urllib.request.urlopen('http://127.0.0.1:8000/')
    print('Success')
except urllib.error.HTTPError as e:
    with open('error.html', 'w', encoding='utf-8') as f:
        f.write(e.read().decode('utf-8'))
    print(f'HTTPError: {e.code}')
except Exception as e:
    print(f'Error: {e}')
