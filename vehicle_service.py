from flask import Flask, request, jsonify
import jwt
import json
import os
import uuid

app = Flask(__name__)

VEHICLES_FILE = 'vehicles.json'

JWT_SECRET = os.environ.get('JWT_SECRET', 'cs361-demo-secret')
JWT_ALGORITHM = 'HS256'

def load_vehicles():
    "Load the vehicles.json file into a dict"
    if not os.path.exists(VEHICLES_FILE):
        return {}
    with open(VEHICLES_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_vehicles(data):
    "Save the vehicles dict back to vehicles.json"
    with open(VEHICLES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_authenticated_user():
    "Pulls token from authorization header and asks Auth service to verify it"
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        # Covers expired, malformed, or bad signature tokens
        return None

    if payload.get('type') != 'access':
        return None

    return payload.get('sub')

@app.route('/vehicles', methods=['GET'])
def list_vehicles():
    '''List the logged-in user's vehicles'''
    user_id = get_authenticated_user()
    if not user_id:
        return jsonify({'message': 'Unauthorized access'}), 401

    vehicles = load_vehicles()
    return jsonify({'vehicles': vehicles}), 200

@app.route('/vehicles', methods=['POST'])
def add_vehicle():
    '''
    Add a vehicle to the logged-in user's vehicles
    Expected JSON body {make, model, year} optional plate
    '''
    user_id = get_authenticated_user()
    if not user_id:
        return jsonify({'message': 'Unauthorized access'}), 401

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'message': 'Request body must be JSON'}), 400

    required_fields = ['make', 'model', 'year']
    missing = [
        field
        for field in required_fields
        if field not in payload
    ]
    if missing:
        return jsonify({'message': f'Missing fields {", ".join(missing)}'}), 400

    vehicles = load_vehicles()
    user_vehicles = vehicles.setdefault(user_id, [])

    new_vehicle = {
        'id': str(uuid.uuid4()),
        'make': payload['make'],
        'model': payload['model'],
        'year': payload['year'],
        'plate': payload.get('plate', ""),
    }
    user_vehicles.append(new_vehicle)
    save_vehicles(vehicles)

    return jsonify(new_vehicle), 201


@app.route('/vehicles/<vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id):
    '''Delete one of the logged-in user's vehicles by its id.'''
    user_id = get_authenticated_user()
    if not user_id:
        return jsonify({'message': 'Unauthorized access'}), 401

    vehicles = load_vehicles()
    user_vehicles = vehicles.get(user_id, [])

    remaining = [
        vehicle
        for vehicle in user_vehicles
        if vehicle['id'] != vehicle_id]

    if len(remaining) == len(user_vehicles):
        return jsonify({'message': 'Vehicle not found'}), 404

    vehicles[user_id] = remaining
    save_vehicles(vehicles)

    return jsonify({'message': 'Vehicle deleted'}), 200


if __name__ == '__main__':
    app.run(port=5002, debug=True)
