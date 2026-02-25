#!/usr/bin/env python3
"""
Flask Backend for Port AGV Digital Twin Dashboard
Provides REST API and WebSocket endpoints for vehicle state, trajectory, and risk heatmap
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import eventlet
import random
import math
import time
from datetime import datetime

eventlet.monkey_patch()

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Simulation state
vehicle_state = {
    'x': 0.0,
    'y': 0.0,
    'heading': 0.0,
    'speed': 0.0,
    'risk_index': 0.1,
    'scenario': 'Standard Operation'
}

trajectory_history = []
MAX_TRAJECTORY_POINTS = 500

# Simulation parameters
SIMULATION_AREA_SIZE = 100.0  # meters
UPDATE_INTERVAL = 1.0  # seconds


def simulate_vehicle_motion():
    """
    Simulate vehicle motion with random walk
    TODO: Replace with actual ROS2 /tf or /odom topic subscription
    """
    global vehicle_state, trajectory_history

    while True:
        # Random walk motion
        speed_change = random.uniform(-0.5, 0.5)
        vehicle_state['speed'] = max(0.0, min(5.0, vehicle_state['speed'] + speed_change))

        # Update heading with random turn
        heading_change = random.uniform(-15, 15)
        vehicle_state['heading'] = (vehicle_state['heading'] + heading_change) % 360

        # Update position based on speed and heading
        heading_rad = math.radians(vehicle_state['heading'])
        dx = vehicle_state['speed'] * math.cos(heading_rad) * UPDATE_INTERVAL
        dy = vehicle_state['speed'] * math.sin(heading_rad) * UPDATE_INTERVAL

        vehicle_state['x'] += dx
        vehicle_state['y'] += dy

        # Keep vehicle within simulation area
        vehicle_state['x'] = max(-SIMULATION_AREA_SIZE, min(SIMULATION_AREA_SIZE, vehicle_state['x']))
        vehicle_state['y'] = max(-SIMULATION_AREA_SIZE, min(SIMULATION_AREA_SIZE, vehicle_state['y']))

        # Simulate risk index variation
        vehicle_state['risk_index'] = max(0.0, min(1.0, vehicle_state['risk_index'] + random.uniform(-0.1, 0.1)))

        # Update trajectory history
        trajectory_history.append({
            'x': vehicle_state['x'],
            'y': vehicle_state['y'],
            'timestamp': time.time()
        })

        if len(trajectory_history) > MAX_TRAJECTORY_POINTS:
            trajectory_history.pop(0)

        # Emit vehicle pose via WebSocket
        socketio.emit('vehicle_pose', {
            'x': vehicle_state['x'],
            'y': vehicle_state['y'],
            'heading': vehicle_state['heading'],
            'risk': vehicle_state['risk_index']
        })

        eventlet.sleep(UPDATE_INTERVAL)


@app.route('/')
def index():
    """Root endpoint - serve dashboard"""
    return render_template('dashboard.html')


@app.route('/vehicle_state')
def get_vehicle_state():
    """
    GET /vehicle_state
    Returns current vehicle state including pose, speed, and risk index
    TODO: Replace with actual ROS2 vehicle state topic
    """
    return jsonify({
        'pose': {
            'x': vehicle_state['x'],
            'y': vehicle_state['y'],
            'heading': vehicle_state['heading']
        },
        'speed': vehicle_state['speed'],
        'risk_index': vehicle_state['risk_index'],
        'scenario': vehicle_state['scenario'],
        'timestamp': time.time()
    })


@app.route('/trajectory')
def get_trajectory():
    """
    GET /trajectory
    Returns historical trajectory points
    TODO: Replace with actual ROS2 path history or recorded odometry
    """
    return jsonify(trajectory_history)


@app.route('/risk/heatmap')
def get_risk_heatmap():
    """
    GET /risk/heatmap
    Returns risk heatmap data for visualization
    TODO: Replace with actual InSAR risk data or geospatial risk analysis
    """
    # Generate sample heatmap data points
    heatmap_data = []

    # Create a grid of risk points around the simulation area
    grid_size = 20
    for i in range(grid_size):
        for j in range(grid_size):
            x = (i - grid_size/2) * (SIMULATION_AREA_SIZE / grid_size) * 2
            y = (j - grid_size/2) * (SIMULATION_AREA_SIZE / grid_size) * 2

            # Simulate risk hotspots with distance-based risk
            distance_to_center = math.sqrt(x**2 + y**2)
            risk = max(0.0, min(1.0, 0.5 + 0.3 * math.sin(distance_to_center / 20)))

            # Add some random variation
            risk += random.uniform(-0.2, 0.2)
            risk = max(0.0, min(1.0, risk))

            heatmap_data.append({
                'x': x,
                'y': y,
                'risk': risk
            })

    return jsonify(heatmap_data)


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket client connection"""
    print(f'Client connected: {datetime.now().isoformat()}')
    # Send initial vehicle pose
    emit('vehicle_pose', {
        'x': vehicle_state['x'],
        'y': vehicle_state['y'],
        'heading': vehicle_state['heading'],
        'risk': vehicle_state['risk_index']
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnection"""
    print(f'Client disconnected: {datetime.now().isoformat()}')


if __name__ == '__main__':
    print("=" * 60)
    print("🚛 AGV Digital Twin Backend Server")
    print("=" * 60)
    print(f"Starting server at http://0.0.0.0:5000")
    print(f"Dashboard: http://localhost:5000")
    print(f"WebSocket endpoint: ws://localhost:5000/socket.io/")
    print(f"Simulation area: ±{SIMULATION_AREA_SIZE}m")
    print(f"Update interval: {UPDATE_INTERVAL}s")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET  /                 - Dashboard UI")
    print("  GET  /vehicle_state    - Current vehicle state")
    print("  GET  /trajectory       - Historical trajectory")
    print("  GET  /risk/heatmap     - Risk heatmap data")
    print("  WS   /socket.io/       - Real-time vehicle pose")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")

    # Start vehicle simulation in background
    eventlet.spawn(simulate_vehicle_motion)

    # Run Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
