#!/usr/bin/env python3
"""
IoT Greenhouse - Temperature Node MQTT Publisher
Reads temperature data from Arduino via serial and publishes to AWS IoT Core

Requirements:
- pip install pyserial
- pip install AWSIoTPythonSDK

Hardware:
- Arduino running Temperature_Fan_Node.ino
- Connected via USB to Raspberry Pi
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
MQTT_TOPIC = "greenhouse/node2/temperature"
CLIENT_ID = "temperature_node_raspberry_pi"

# AWS IoT Configuration - Updated to match your actual certificate files
AWS_IOT_ENDPOINT = "azoj5h57hjr65-ats.iot.us-east-1.amazonaws.com"
ROOT_CA_PATH = "./certs/AmazonRootCA1.pem"
PRIVATE_KEY_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-private.pem.key"
CERTIFICATE_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-certificate.pem.crt"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemperatureNodePublisher:
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
        Parse Arduino serial output and extract temperature data
        Expected format: "Temp: 29.5°C | Humidity: 65.2% | Fan: OFF"
        """
        try:
            # Clean the line
            line = line.strip()
            
            # Skip non-data lines (errors, status messages, etc.)
            if not line or "Temp:" not in line:
                return None
            
            # Extract temperature
            temp_match = re.search(r'Temp:\s*([\d.]+)', line)
            humidity_match = re.search(r'Humidity:\s*([\d.]+)', line)
            fan_match = re.search(r'Fan:\s*(\w+)', line)
            
            if temp_match and humidity_match and fan_match:
                data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "node_id": "temperature_node",
                    "temperature": float(temp_match.group(1)),
                    "humidity": float(humidity_match.group(1)),
                    "fan_status": fan_match.group(1).upper(),
                    "location": "greenhouse_section_2"
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
        logger.info("Starting temperature node publisher...")
        
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
    # Validate configuration
    if AWS_IOT_ENDPOINT == "your-endpoint.iot.region.amazonaws.com":
        logger.error("Please update AWS_IOT_ENDPOINT with your actual endpoint")
        return
    
    try:
        publisher = TemperatureNodePublisher()
        publisher.run()
    except Exception as e:
        logger.error(f"Failed to start publisher: {e}")

if __name__ == "__main__":
    main()