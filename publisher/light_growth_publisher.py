#!/usr/bin/env python3
"""
IoT Greenhouse - Light & Growth Node MQTT Publisher
Reads light and plant height data from Arduino via serial and publishes to AWS IoT Core

Requirements:
- pip install pyserial
- pip install AWSIoTPythonSDK

Hardware:
- Arduino running light_sensor.ino
- 3x HC-SR04 Ultrasonic Sensors (plant height)
- 1x LDR (ambient light sensing)
- 3x LEDs (grow lights)
- Connected via USB to Raspberry Pi

Arduino Output Format:
"Light: 25 (DARK) - Timer: 15s remaining | LEDs: OFF"
"Plant 1: 12.5 cm (Vegetative) | Plant 2: 8.2 cm (Seedling) | Plant 3: 18.7 cm (Mature)"
"----------------------------------------"
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
MQTT_TOPIC = "schedule_1/light_growth"
CLIENT_ID = "light_growth_node_raspberry_pi"

# AWS IoT Configuration - Use your actual certificate files
AWS_IOT_ENDPOINT = "azoj5h57hjr65-ats.iot.us-east-1.amazonaws.com"
ROOT_CA_PATH = "./certs/AmazonRootCA1.pem"
PRIVATE_KEY_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-private.pem.key"
CERTIFICATE_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-certificate.pem.crt"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LightGrowthNodePublisher:
    def __init__(self):
        self.serial_connection = None
        self.mqtt_client = None
        self.light_data = None
        self.plant_data = None
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
        Parse Arduino serial output and extract light and plant data
        """
        try:
            line = line.strip()
            
            # Skip empty lines, startup messages, and debug info
            if not line or "===" in line or "Monitoring" in line or "System initialized" in line:
                return None
            
            # Parse light sensor data
            # Format: "Light: 25 (DARK) - Timer: 15s remaining | LEDs: OFF"
            # Format: "Light: 25 (DARK) | LEDs: ON (78%)"
            # Format: "Light: 50 (BRIGHT) | LEDs: OFF"
            if line.startswith("Light:"):
                logger.debug(f"Parsing light line: {line}")
                self.light_data = self.parse_light_line(line)
                return None
            
            # Parse plant height data
            # Format: "Plant 1: 12.5 cm (Vegetative) | Plant 2: 8.2 cm (Seedling) | Plant 3: 18.7 cm (Mature)"
            elif line.startswith("Plant"):
                logger.debug(f"Parsing plant line: {line}")
                self.plant_data = self.parse_plant_line(line)
                return None
            
            # Check for separator - triggers data publishing
            elif line.startswith("---"):
                logger.debug("Found separator, checking if we have complete data")
                if self.light_data and self.plant_data:
                    # Combine light and plant data
                    combined_data = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "node_id": "light_growth_node",
                        "light_sensor": self.light_data,
                        "plant_heights": self.plant_data,
                        "location": "greenhouse_section_3"
                    }
                    
                    # Calculate statistics
                    valid_heights = []
                    for plant_key, plant_info in self.plant_data.items():
                        if plant_info["height_cm"] > 0:
                            valid_heights.append(plant_info["height_cm"])
                    
                    if valid_heights:
                        combined_data["statistics"] = {
                            "average_height": round(sum(valid_heights) / len(valid_heights), 1),
                            "max_height": max(valid_heights),
                            "min_height": min(valid_heights),
                            "plants_with_readings": len(valid_heights),
                            "total_plants": len(self.plant_data)
                        }
                    else:
                        combined_data["statistics"] = {
                            "average_height": 0,
                            "max_height": 0,
                            "min_height": 0,
                            "plants_with_readings": 0,
                            "total_plants": len(self.plant_data)
                        }
                    
                    # Reset for next reading
                    self.light_data = None
                    self.plant_data = None
                    
                    return combined_data
                else:
                    logger.warning(f"Incomplete data: light_data={self.light_data is not None}, plant_data={self.plant_data is not None}")
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse line '{line}': {e}")
            return None
    
    def parse_light_line(self, line):
        """
        Parse light sensor line
        Expected formats:
        - "Light: 25 (DARK) - Timer: 15s remaining | LEDs: OFF"
        - "Light: 25 (DARK) | LEDs: ON (78%)"
        - "Light: 50 (BRIGHT) | LEDs: OFF"
        """
        try:
            # Extract light level and status
            light_match = re.search(r'Light:\s*(\d+)\s*\((\w+)\)', line)
            if not light_match:
                logger.warning(f"Could not match light pattern in: {line}")
                return None
                
            light_level = int(light_match.group(1))
            light_status = light_match.group(2)  # DARK or BRIGHT
            
            # Extract timer if present
            timer_remaining = 0
            timer_match = re.search(r'Timer:\s*(\d+)s remaining', line)
            if timer_match:
                timer_remaining = int(timer_match.group(1))
            
            # Extract LED status
            led_status = "OFF"
            led_brightness = 0
            
            if "LEDs: ON" in line:
                led_status = "ON"
                # Extract brightness percentage
                brightness_match = re.search(r'LEDs:\s*ON\s*\((\d+)%\)', line)
                if brightness_match:
                    led_brightness = int(brightness_match.group(1))
                else:
                    # Calculate from LED_BRIGHTNESS constant (200/255 * 100)
                    led_brightness = round((200 / 255) * 100)
            elif "LEDs: OFF" in line:
                led_status = "OFF"
            
            return {
                "light_level": light_level,
                "light_status": light_status,
                "led_status": led_status,
                "led_brightness": led_brightness,
                "timer_remaining": timer_remaining
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse light line '{line}': {e}")
            return None
    
    def parse_plant_line(self, line):
        """
        Parse plant height line
        Expected format: "Plant 1: 12.5 cm (Vegetative) | Plant 2: 8.2 cm (Seedling) | Plant 3: No reading"
        """
        try:
            plants = {}
            
            # Find all plant readings with height
            plant_matches = re.findall(r'Plant\s+(\d+):\s*([\d.]+)\s*cm\s*\((\w+)\)', line)
            for match in plant_matches:
                plant_num = int(match[0])
                height = float(match[1])
                growth_stage = match[2]  # Seedling, Vegetative, Mature, Overgrown
                
                plants[f"plant_{plant_num}"] = {
                    "sector": plant_num,
                    "height_cm": height,
                    "growth_stage": growth_stage
                }
            
            # Find plants with "No reading"
            no_reading_matches = re.findall(r'Plant\s+(\d+):\s*No reading', line)
            for match in no_reading_matches:
                plant_num = int(match)
                plants[f"plant_{plant_num}"] = {
                    "sector": plant_num,
                    "height_cm": -1,
                    "growth_stage": "No Reading"
                }
            
            return plants if plants else None
            
        except Exception as e:
            logger.warning(f"Failed to parse plant line '{line}': {e}")
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
        logger.info("Starting light & growth node publisher...")
        
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
        publisher = LightGrowthNodePublisher()
        publisher.run()
    except Exception as e:
        logger.error(f"Failed to start publisher: {e}")

if __name__ == "__main__":
    main()