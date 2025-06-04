#!/usr/bin/env python3
"""
Light & Growth Node Command Listener (Raspberry Pi 3)
Handles light control commands for the growth monitoring system

This Pi is dedicated to:
- 3x Ultrasonic sensors (plant height)
- 1x Camera (plant width measurement)
- 1x Light sensor (ambient light)
- 3x LEDs (grow lights)
- 3x LCD displays (growth status)
"""

import mysql.connector
import serial
import time
import logging
from datetime import datetime

# Configuration - Connect to your EC2 database
DB_CONFIG = {
    'host': '34.199.73.137',  # Your EC2 public IP
    'port': 3306,
    'user': 'greenhouse_edge',
    'password': 'EdgeDevice2025!',
    'database': 'greenhouse',
    'connection_timeout': 30,
    'autocommit': True
}

# Serial port for light/growth Arduino (only one Arduino per Pi)
ARDUINO_PORT = '/dev/ttyUSB0'  # Update with your actual port
ARDUINO_BAUD = 9600

# Node identification
NODE_ID = "light_growth_node"
RASPBERRY_PI_ID = "raspberry_pi_3"

# Polling settings
POLL_INTERVAL = 3  # Check for commands every 3 seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LightNodeCommandListener:
    def __init__(self):
        self.arduino_connection = None
        self.running = False
        self.last_command_id = 0
        self.setup_arduino_connection()
        self.register_node()
    
    def setup_arduino_connection(self):
        """Connect to the light/growth Arduino"""
        try:
            self.arduino_connection = serial.Serial(
                port=ARDUINO_PORT,
                baudrate=ARDUINO_BAUD,
                timeout=2
            )
            time.sleep(2)  # Give Arduino time to reset
            logger.info(f"✅ Connected to Light & Growth Arduino on {ARDUINO_PORT}")
            
            # Send test command to verify connection
            self.arduino_connection.write(b"STATUS\n")
            time.sleep(1)
            if self.arduino_connection.in_waiting > 0:
                response = self.arduino_connection.readline().decode('utf-8', errors='ignore').strip()
                logger.info(f"📡 Arduino response: {response}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Arduino: {e}")
            logger.error("Please check:")
            logger.error("1. Arduino is connected and powered")
            logger.error("2. Correct serial port in configuration")
            logger.error("3. User is in dialout group: sudo usermod -a -G dialout $USER")
            self.arduino_connection = None
    
    def register_node(self):
        """Register this node and get last processed command ID"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Create edge_devices table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS edge_devices (
                    id VARCHAR(50) PRIMARY KEY,
                    node_type VARCHAR(50),
                    last_command_id INT DEFAULT 0,
                    last_seen DATETIME,
                    status VARCHAR(20) DEFAULT 'online',
                    arduino_port VARCHAR(50)
                )
            """)
            
            # Register this node
            cursor.execute("""
                INSERT INTO edge_devices (id, node_type, last_command_id, last_seen, status, arduino_port)
                VALUES (%s, %s, 0, %s, 'online', %s)
                ON DUPLICATE KEY UPDATE
                last_seen = %s, status = 'online', arduino_port = %s
            """, (RASPBERRY_PI_ID, NODE_ID, datetime.now(), ARDUINO_PORT, datetime.now(), ARDUINO_PORT))
            
            # Get last processed command ID
            cursor.execute("""
                SELECT last_command_id FROM edge_devices WHERE id = %s
            """, (RASPBERRY_PI_ID,))
            
            result = cursor.fetchone()
            self.last_command_id = result[0] if result else 0
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Node registered. Last command ID: {self.last_command_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to register node: {e}")
            self.last_command_id = 0
    
    def poll_for_light_commands(self):
        """Poll database for new light control commands only"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            
            # Get only LIGHT_CONTROL commands newer than our last processed ID
            cursor.execute("""
                SELECT id, command_type, action, brightness, timestamp
                FROM control_commands 
                WHERE id > %s 
                AND status = 'SUCCESS' 
                AND command_type = 'LIGHT_CONTROL'
                ORDER BY id ASC
                LIMIT 5
            """, (self.last_command_id,))
            
            commands = cursor.fetchall()
            
            processed_count = 0
            for command in commands:
                success = self.process_light_command(command)
                
                if success:
                    self.last_command_id = command['id']
                    processed_count += 1
                    
                    # Update our last processed command ID
                    cursor.execute("""
                        UPDATE edge_devices 
                        SET last_command_id = %s, last_seen = %s
                        WHERE id = %s
                    """, (self.last_command_id, datetime.now(), RASPBERRY_PI_ID))
            
            # Update last seen timestamp even if no commands
            cursor.execute("""
                UPDATE edge_devices 
                SET last_seen = %s
                WHERE id = %s
            """, (datetime.now(), RASPBERRY_PI_ID))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if processed_count > 0:
                logger.info(f"📊 Processed {processed_count} light commands")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Error polling for commands: {e}")
            return 0
    
def process_light_command(self, command):
    """Process light control command and send to Arduino"""
    action = command.get('action', 'toggle').upper()
    brightness = command.get('brightness')  # This might be None
    
    # FIX: Handle None brightness - just use fixed values for ON/OFF LEDs
    if action == 'OFF':
        brightness = 0  # Always 0 for OFF
    else:
        brightness = 100  # Always 100 for ON (or any value > 0)
    
    logger.info(f"💡 Processing light command: {action} at {brightness}% brightness")
    
    if not self.arduino_connection:
        logger.error("❌ No Arduino connection available")
        return False
    
    try:
        # Format command for Arduino: "LIGHTS_ON_100", "LIGHTS_OFF_0", "LIGHTS_AUTO_100"
        arduino_command = f"LIGHTS_{action}_{brightness}"
        
        # Send command to Arduino
        self.arduino_connection.write((arduino_command + '\n').encode())
        self.arduino_connection.flush()
        
        logger.info(f"📤 Sent to Arduino: {arduino_command}")
        
        # Wait for Arduino response
        time.sleep(1)
        if self.arduino_connection.in_waiting > 0:
            response = self.arduino_connection.readline().decode('utf-8', errors='ignore').strip()
            logger.info(f"📥 Arduino response: {response}")
            
            # Check if command was accepted
            if "LIGHTS" in response and action in response:
                logger.info(f"✅ Light command executed successfully: {action}")
                return True
            elif "INVALID" in response or "ERROR" in response:
                logger.error(f"❌ Arduino rejected command: {response}")
                return False
        
        # Consider it successful if we got this far
        logger.info(f"✅ Light command sent successfully: {action}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error sending light command: {e}")
        return False
    
    def test_arduino_connection(self):
        """Test Arduino connection and get status"""
        if not self.arduino_connection:
            logger.error("❌ No Arduino connection to test")
            return False
        
        try:
            logger.info("🧪 Testing Arduino connection...")
            
            # Send status request
            self.arduino_connection.write(b"STATUS\n")
            time.sleep(2)
            
            responses = []
            while self.arduino_connection.in_waiting > 0:
                response = self.arduino_connection.readline().decode('utf-8', errors='ignore').strip()
                if response:
                    responses.append(response)
            
            if responses:
                logger.info("✅ Arduino connection test successful!")
                for response in responses:
                    logger.info(f"   Arduino: {response}")
                return True
            else:
                logger.warning("⚠️ Arduino connection exists but no response to STATUS command")
                return False
                
        except Exception as e:
            logger.error(f"❌ Arduino connection test failed: {e}")
            return False
    
    def run(self):
        """Main loop - continuously poll for light commands"""
        logger.info("🚀 Light & Growth Node Command Listener Starting...")
        logger.info(f"Node: {NODE_ID}")
        logger.info(f"Pi ID: {RASPBERRY_PI_ID}")
        logger.info(f"Arduino Port: {ARDUINO_PORT}")
        logger.info(f"Polling interval: {POLL_INTERVAL} seconds")
        logger.info("Listening for LIGHT_CONTROL commands only...")
        
        # Test connection first
        if not self.test_arduino_connection():
            logger.error("❌ Arduino connection test failed. Continuing anyway...")
        
        self.running = True
        total_commands = 0
        
        try:
            while self.running:
                try:
                    # Poll for light commands
                    new_commands = self.poll_for_light_commands()
                    total_commands += new_commands
                    
                    if new_commands > 0:
                        logger.info(f"💡 Total light commands processed: {total_commands}")
                    
                    time.sleep(POLL_INTERVAL)
                    
                except KeyboardInterrupt:
                    logger.info("🛑 Received Ctrl+C - Shutting down...")
                    break
                except Exception as e:
                    logger.error(f"❌ Error in main loop: {e}")
                    time.sleep(5)  # Wait before retrying
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        logger.info("🛑 Shutting down Light & Growth Node...")
        
        self.running = False
        
        # Close Arduino connection
        if self.arduino_connection:
            try:
                self.arduino_connection.close()
                logger.info("✅ Arduino connection closed")
            except:
                pass
        
        # Update status in database
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE edge_devices 
                SET status = 'offline', last_seen = %s
                WHERE id = %s
            """, (datetime.now(), RASPBERRY_PI_ID))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("✅ Database status updated to offline")
        except:
            pass
        
        logger.info("✅ Light & Growth Node stopped cleanly")

def main():
    """Main function"""
    print("💡 Greenhouse Light & Growth Node Command Listener")
    print("=" * 50)
    print("This listener handles LIGHT CONTROL commands only")
    print("Commands: LIGHT_CONTROL (ON/OFF/AUTO + brightness)")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    listener = LightNodeCommandListener()
    
    try:
        listener.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        listener.shutdown()

if __name__ == "__main__":
    main()