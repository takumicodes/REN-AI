import requests

# Send an HTTP request to the API to get user's IP address
response = requests.get('https://api.ipify.org?format=json')
ip_address = response.json()['ip']

# Use an external API to get city information based on the IP address
city_response = requests.get(f'https://geoip-db.com/json/{ip_address}')
location_data = city_response.json()

speak(f"Your current IP address is {ip_address}. You are in {location_data['city']}.")

speak("DONE")