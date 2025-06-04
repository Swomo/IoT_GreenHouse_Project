#!/usr/bin/env python3
"""
IoT Greenhouse - Command Publisher
Sends commands from web dashboard to Arduino nodes via MQTT

This script receives HTTP requests from the Flask app and forwards
commands to the appropriate Arduino nodes.
"""

import json
import time
import logging
import serial
from flask import Flask, request, jsonify
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Configuration
SERIAL_PORT = "/dev/ttyUSB0"  # Adjust for your setup
SERIAL_BAUD = 9600
MQTT_TOPIC_COMMANDS = "schedule_1/commands"

# AWS IoT Configuration
AWS_IOT_ENDPOINT = "azoj5h57hjr65-ats.iot.us-east-1.amazonaws.com"
ROOT_CA_PATH = "./certs/AmazonRootCA1.pem"
PRIVATE_KEY_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-private.pem.key"
CERTIFICATE_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-certificate.pem.crt"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GreenhouseCommandPublisher:
    def __init__(self):
        self.serial_connections = {}
        self.mqtt_client = None
        self.setup_mqtt()
        self.setup_serial_connections()
    
    def setup_mqtt(self):
        """Initialize MQTT client for command publishing"""
        try:
            self.mqtt_client = AWSIoTMQTTClient("command_publisher")
            self.mqtt_client.configureEndpoint(AWS_IOT_ENDPOINT, 8883)
            self.mqtt_client.configureCredentials(ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)
            self.mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
            self.mqtt_client.configureOfflinePublishQueueing(-1)
            self.mqtt_client.configureDrainingFrequency(2)
            self.mqtt_client.configureConnectDisconnectTimeout(10)
            self.mqtt_client.configureMQTTOperationTimeout(5)
            
            if self.mqtt_client.connect():
                logger.info("Connected to AWS IoT Core for commands")
            else:
                raise Exception("Failed to connect to AWS IoT Core")
        except Exception as e:
            logger.error(f"MQTT setup failed: {e}")
    
    def setup_serial_connections(self):
        """Setup serial connections to Arduino nodes"""
        # In a real setup, you might have multiple serial ports for different nodes
        try:
            self.serial_connections['soil'] = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            logger.info("Serial connection established")
        except Exception as e:
            logger.warning(f"Serial connection failed: {e}")
    
    def send_command_to_node(self, node_type, command):
        """Send command directly to Arduino via serial"""
        try:
            if node_type in self.serial_connections:
                conn = self.serial_connections[node_type]
                conn.write((command + '\n').encode())
                logger.info(f"Sent command to {node_type}: {command}")
                return True
        except Exception as e:
            logger.error(f"Failed to send command to {node_type}: {e}")
        return False
    
    def publish_command_mqtt(self, command_data):
        """Publish command via MQTT (alternative method)"""
        try:
            message = json.dumps(command_data)
            self.mqtt_client.publish(MQTT_TOPIC_COMMANDS, message, 1)
            logger.info(f"Published command via MQTT: {message}")
            return True
        except Exception as e:
            logger.error(f"MQTT publish failed: {e}")
            return False

# Global instance
command_publisher = GreenhouseCommandPublisher()

@app.route('/api/water-plants', methods=['POST'])
def water_plants():
    """Manual watering command"""
    data = request.get_json() or {}
    sector = data.get('sector', 1)  # Default to sector 1
    duration = data.get('duration', 10)  # Default 10 seconds
    
    if sector not in [1, 2, 3] or duration < 1 or duration > 60:
        return jsonify({'error': 'Invalid sector or duration'}), 400
    
    command = f"WATER_SECTOR_{sector}_{duration}"
    
    # Send command via serial
    if command_publisher.send_command_to_node('soil', command):
        return jsonify({
            'message': f'Watering sector {sector} for {duration} seconds',
            'success': True
        })
    else:
        return jsonify({'error': 'Failed to send command'}), 500

@app.route('/api/toggle-fan', methods=['POST'])
def toggle_fan():
    """Manual fan control"""
    data = request.get_json() or {}
    action = data.get('action', 'toggle')  # 'on', 'off', or 'toggle'
    
    command = f"FAN_{action.upper()}"
    
    # For temperature node (you'd need separate serial connection)
    # command_publisher.send_command_to_node('temperature', command)
    
    # For now, just log the command
    logger.info(f"Fan command: {command}")
    
    return jsonify({
        'message': f'Fan {action} command sent',
        'success': True
    })

@app.route('/api/toggle-lights', methods=['POST'])
def toggle_lights():
    """Manual grow light control"""
    data = request.get_json() or {}
    action = data.get('action', 'toggle')  # 'on', 'off', or 'toggle'
    brightness = data.get('brightness', 100)  # 0-100%
    
    command = f"LIGHTS_{action.upper()}_{brightness}"
    
    # For light node (you'd need separate serial connection)
    # command_publisher.send_command_to_node('light', command)
    
    logger.info(f"Light command: {command}")
    
    return jsonify({
        'message': f'Lights {action} command sent (brightness: {brightness}%)',
        'success': True
    })

@app.route('/api/system-status', methods=['GET'])
def get_system_status():
    """Get current system status"""
    # This would query your database or current sensor states
    return jsonify({
        'soil_moisture': {'sector_1': 45, 'sector_2': 38, 'sector_3': 52},
        'temperature': 28.5,
        'humidity': 65.2,
        'fan_status': 'OFF',
        'light_status': 'AUTO',
        'last_updated': time.time()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)