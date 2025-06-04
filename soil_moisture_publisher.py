#!/usr/bin/env python3
"""
IoT Greenhouse - Soil Moisture Node MQTT Publisher
Reads soil moisture data from Arduino via serial and publishes to AWS IoT Core

Requirements:
- pip install pyserial
- pip install AWSIoTPythonSDK

Hachiware:
- Arduino running Soil_Moisture_Node.ino
- 3 soil moisture sensors (A0, A1, A2)
- Water pump servo
- LED status indicator
- Connected via USB to Raspberry Pi

Arduino Output Format:
"Soil Moisture - A: 850 (DRY) | B: 650 (OK) | C: 400 (OK) | State: WATERING"
"""

import serial
import json
import time
import re
import logging
from datetime import datetime
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Configuration
SERIAL_PORT = "/dev/ttyUSB0"  # Change to your Arduino port (/dev/ttyACM0 on some systems)
SERIAL_BAUD = 9600
MQTT_TOPIC = "schedule_1/soil_moisture"
CLIENT_ID = "soil_moisture_node_raspberry_pi"

# AWS IoT Configuration - Use your actual certificate files
AWS_IOT_ENDPOINT = "azoj5h57hjr65-ats.iot.us-east-1.amazonaws.com"
ROOT_CA_PATH = "./cert/AmazonRootCA1.pem"
PRIVATE_KEY_PATH = "./cert/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-private.pem.key"
CERTIFICATE_PATH = "./cert/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-certificate.pem.crt"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SoilMoistureNodePublisher:
    def __init__(self):
        self.serial_connection = None
        self.mqtt_client = None
        self.setup_serial()
        self.setup_mqtt()
        
    def setup_serial(self):
        """Initialize serial connection to Arduino"""
        try:
            self.serial_connection = serial.Serial(
                port=SERIAL_PORT,
                baudrate=SERIAL_BAUD,
                timeout=1
            )
            logger.info(f"Serial connection established on {SERIAL_PORT}")
            time.sleep(2)  # Give Arduino time to reset
        except Exception as e:
            logger.error(f"Failed to setup serial connection: {e}")
            raise
    
    def setup_mqtt(self):
        """Initialize AWS IoT MQTT client"""
        try:
            self.mqtt_client = AWSIoTMQTTClient(CLIENT_ID)
            self.mqtt_client.configureEndpoint(AWS_IOT_ENDPOINT, 8883)
            self.mqtt_client.configureCredentials(ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)
            
            # Configure MQTT settings
            self.mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
            self.mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline publish queueing
            self.mqtt_client.configureDrainingFrequency(2)  # Draining: 2 Hz
            self.mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
            self.mqtt_client.configureMQTTOperationTimeout(5)  # 5 sec
            
            # Connect to AWS IoT
            if self.mqtt_client.connect():
                logger.info("Connected to AWS IoT Core")
            else:
                raise Exception("Failed to connect to AWS IoT Core")
                
        except Exception as e:
            logger.error(f"Failed to setup MQTT connection: {e}")
            raise
    
    def parse_arduino_output(self, line):
        """
        Parse Arduino serial output and extract soil moisture data
        Expected format: "Soil Moisture - A: 850 (DRY) | B: 650 (OK) | C: 400 (OK) | State: WATERING"
        """
        try:
            # Clean the line
            line = line.strip()
            
            # Skip non-data lines (errors, status messages, etc.)
            if not line or "Soil Moisture -" not in line:
                return None
            
            # Extract soil moisture readings (raw analog values 0-1023)
            soil_a_match = re.search(r'A:\s*(\d+)\s*\((\w+)\)', line)
            soil_b_match = re.search(r'B:\s*(\d+)\s*\((\w+)\)', line)
            soil_c_match = re.search(r'C:\s*(\d+)\s*\((\w+)\)', line)
            state_match = re.search(r'State:\s*(\w+)', line)
            growth_match = re.search(r'Growth Cycle:\s*(\d+)', line)
            
            if soil_a_match and soil_b_match and soil_c_match and state_match:
                # Get raw analog values (0-1023 range)
                soil_a_raw = int(soil_a_match.group(1))
                soil_b_raw = int(soil_b_match.group(1))
                soil_c_raw = int(soil_c_match.group(1))
                
                # Get status strings (DRY, OK, WET)
                soil_a_status = soil_a_match.group(2)
                soil_b_status = soil_b_match.group(2)
                soil_c_status = soil_c_match.group(2)
                
                # Convert raw values to percentage (inverted: lower raw value = higher moisture)
                # 1023 = 0% moisture, 0 = 100% moisture
                soil_a_percent = round((1023 - soil_a_raw) / 1023 * 100, 1)
                soil_b_percent = round((1023 - soil_b_raw) / 1023 * 100, 1)
                soil_c_percent = round((1023 - soil_c_raw) / 1023 * 100, 1)
                
                # Calculate average moisture percentage
                average_moisture = round((soil_a_percent + soil_b_percent + soil_c_percent) / 3, 1)
                
                # Get system state
                system_state = state_match.group(1)
                
                # Get growth cycle if present
                growth_cycle = int(growth_match.group(1)) if growth_match else 0
                
                # Determine LED status based on system state
                led_status = "ON" if system_state != "MONITORING" else "OFF"
                
                # Determine if any sensor needs watering
                watering_needed = system_state in ["WATERING", "ALL_DRY"]
                
                data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "node_id": "soil_moisture_node",
                    "soil_sensors": {
                        "sensor_a": {
                            "raw_value": soil_a_raw,
                            "moisture_percent": soil_a_percent,
                            "status": soil_a_status
                        },
                        "sensor_b": {
                            "raw_value": soil_b_raw,
                            "moisture_percent": soil_b_percent,
                            "status": soil_b_status
                        },
                        "sensor_c": {
                            "raw_value": soil_c_raw,
                            "moisture_percent": soil_c_percent,
                            "status": soil_c_status
                        },
                        "average_moisture": average_moisture
                    },
                    "system_state": system_state,
                    "led_status": led_status,
                    "watering_needed": watering_needed,
                    "growth_cycle": growth_cycle,
                    "location": "greenhouse_section_1"
                }
                return data
            
        except Exception as e:
            logger.warning(f"Failed to parse line '{line}': {e}")
            
        return None
    
    def publish_data(self, data):
        """Publish data to AWS IoT Core"""
        try:
            message = json.dumps(data)
            self.mqtt_client.publish(MQTT_TOPIC, message, 1)  # QoS 1
            logger.info(f"Published: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish data: {e}")
            return False
    
    def run(self):
        """Main loop - read serial data and publish to MQTT"""
        logger.info("Starting soil moisture node publisher...")
        
        consecutive_errors = 0
        max_errors = 10
        
        try:
            while True:
                try:
                    # Read line from Arduino
                    if self.serial_connection.in_waiting > 0:
                        line = self.serial_connection.readline().decode('utf-8', errors='ignore')
                        
                        if line:
                            logger.debug(f"Arduino output: {line.strip()}")
                            
                            # Parse the data
                            parsed_data = self.parse_arduino_output(line)
                            
                            if parsed_data:
                                # Publish to AWS IoT
                                if self.publish_data(parsed_data):
                                    consecutive_errors = 0  # Reset error counter
                                else:
                                    consecutive_errors += 1
                    
                    time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                    
                except serial.SerialException as e:
                    logger.error(f"Serial connection error: {e}")
                    consecutive_errors += 1
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    consecutive_errors += 1
                    time.sleep(1)
                
                # If too many consecutive errors, try to reconnect
                if consecutive_errors >= max_errors:
                    logger.warning("Too many consecutive errors, attempting to reconnect...")
                    self.reconnect()
                    consecutive_errors = 0
                    
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()
    
    def reconnect(self):
        """Attempt to reconnect serial and MQTT connections"""
        try:
            # Reconnect serial
            if self.serial_connection:
                self.serial_connection.close()
            time.sleep(2)
            self.setup_serial()
            
            # Reconnect MQTT
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            time.sleep(2)
            self.setup_mqtt()
            
            logger.info("Reconnection successful")
            
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
    
    def cleanup(self):
        """Clean up connections"""
        if self.serial_connection:
            self.serial_connection.close()
            logger.info("Serial connection closed")
            
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            logger.info("MQTT connection closed")

def main():
    """Main function"""
    try:
        publisher = SoilMoistureNodePublisher()
        publisher.run()
    except Exception as e:
        logger.error(f"Failed to start publisher: {e}")

if __name__ == "__main__":
    main()