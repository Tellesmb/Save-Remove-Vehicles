import requests

AUTH_URL = 'http://localhost:5001'
VEHICLES_URL = 'http://localhost:5002'

LOGIN_USERNAME = 'brian'
LOGIN_PASSWORD = ('12345')

def print_results(label, response):
    print(f'\n --- {label} ---')
    print(f'Status code: {response.status_code}')
    try:
        print(f'Body: {response.json()}')
    except ValueError:
        print(f'Body: {response.text}')

def get_token():
    '''Log in through the real Auth service and return access token'''
    response = requests.post(
        f'{AUTH_URL}/auth/login',
        json={'username': LOGIN_USERNAME, 'password': LOGIN_PASSWORD},
    )
    print_results('Login (Auth service)', response)

    if response.status_code != 200:
        return None
    return response.json()['access_token']

def main():
    token = get_token()
    if not token:
        print('\nCould not log in make sure Auth service is running on port 5001.')
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    # 1 Add a vehicle
    new_vehicle = {
        'make': 'Toyota',
        'model': 'Tacoma',
        'year': 2020,
        'plate': 'ABC1234',
    }
    response = requests.post(f'{VEHICLES_URL}/vehicles', headers=headers, json=new_vehicle)
    print_results('Add Vehicle', response)

    if response.status_code != 201:
        print('\nCould not add Vehicle check token and that both vehicle_service.py and Auth service are running.')
        return

    vehicle_id = response.json()['id']

    # 2 List vehicles
    response = requests.get(f'{VEHICLES_URL}/vehicles', headers=headers)
    print_results('Get Vehicles', response)

    # 3 Remove the vehicle we just add
    response = requests.delete(f'{VEHICLES_URL}/vehicles/{vehicle_id}', headers=headers)
    print_results('Delete Vehicle', response)

    # 4 Confirm it's gone
    response = requests.get(f'{VEHICLES_URL}/vehicles', headers=headers)
    print_results('List vehicles (after removal)', response)

    # 5 Try removing something that no longer exist
    response = requests.delete(f'{VEHICLES_URL}/vehicles/{vehicle_id}', headers=headers)
    print_results('Delete Vehicle again (expect 404)', response)

    # 6 Try to get list without a token
    response = requests.get(f'{VEHICLES_URL}/vehicles')
    print_results('List vehicles with no token (expect 401)', response)


if __name__ == '__main__':
    main()
