import requests

# Send an HTTP GET request to an API endpoint to get the user's location
response = requests.get('https://ipinfo.io/json', verify=False)

# Parse the JSON response
data = response.json()

# Extract the city and IP address from the response
city = data['city']
ip_address = data['ip']

# Speak the results directly to Sadiq
speak(f"Your current location is {city} and your IP address is {ip_address}.")