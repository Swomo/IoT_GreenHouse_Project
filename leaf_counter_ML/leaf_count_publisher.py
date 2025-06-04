#!/usr/bin/env python3
"""
IoT Greenhouse - Leaf Count MQTT Publisher
Uses machine learning to count leaves from camera images and publishes to AWS IoT Core

Requirements:
- pip install torch torchvision opencv-python pillow AWSIoTPythonSDK

Hardware:
- Camera (USB webcam or Pi camera)
- Pre-trained leaf counting model (best.pt)
- Connected to Raspberry Pi

Model Output:
- Simplified leaf count data (no image metadata)
"""

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import cv2
import time
import os
import json
import logging
from datetime import datetime
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Configuration
MQTT_TOPIC = "schedule_1/leaf_count"
CLIENT_ID = "leaf_count_node_raspberry_pi"
MODEL_PATH = "best.pt"  # Path to your trained model
IMAGE_SAVE_PATH = "leaf_image.jpg"  # Temporary image file
CAPTURE_INTERVAL = 60  # Capture and publish every 60 seconds

# AWS IoT Configuration - Use your actual certificate files
AWS_IOT_ENDPOINT = "azoj5h57hjr65-ats.iot.us-east-1.amazonaws.com"
ROOT_CA_PATH = "./certs/AmazonRootCA1.pem"
PRIVATE_KEY_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-private.pem.key"
CERTIFICATE_PATH = "./certs/5435e0960ffa0fc7dee861aef3306c7ed7fac5896304b3cfa27991354fdfc227-certificate.pem.crt"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Conv7Net_3Channel_Wide(nn.Module):
    """Neural network model for leaf counting (from your original code)"""
    def __init__(self, dropout):
        super().__init__()
        self.layer1 = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer5 = nn.Sequential(
            nn.Conv2d(256, 256, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer6 = nn.Sequential(
            nn.Conv2d(256, 256, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer7 = nn.Sequential(
            nn.Conv2d(256, 256, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.AvgPool2d(kernel_size=2, stride=2))
        self.fc1 = nn.Linear(1024, 2000)
        self.dropout1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(2000, 100)
        self.dropout2 = nn.Dropout(dropout)
        self.fc3 = nn.Linear(100, 1)
        
    def forward(self, x):
        out = self.layer1(x)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.layer5(out)
        out = self.layer6(out)
        out = self.layer7(out)
        out = out.reshape(out.size(0), -1)
        out = self.fc1(out)
        out = self.dropout1(out)
        out = self.fc2(out)
        out = self.dropout2(out)
        out = self.fc3(out)
        return out

class LeafCountPublisher:
    def __init__(self):
        self.mqtt_client = None
        self.model = None
        self.transform = None
        self.setup_model()
        self.setup_mqtt()
        
    def setup_model(self):
        """Load the trained leaf counting model"""
        try:
            # Check if model file exists
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
            
            # Load the model
            self.model = Conv7Net_3Channel_Wide(dropout=0.5)
            self.model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device("cpu")))
            self.model.eval()
            
            # Setup image preprocessing
            self.transform = transforms.Compose([
                transforms.Resize((256, 256)),  # Match model input size
                transforms.ToTensor()
            ])
            
            logger.info("Leaf counting model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
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
    
    def capture_image(self):
        """Capture image from camera"""
        try:
            cap = cv2.VideoCapture(0)  # Use 0 for default camera
            
            if not cap.isOpened():
                logger.error("Cannot access camera")
                return None
            
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(IMAGE_SAVE_PATH, frame)
                logger.info(f"Image captured and saved to {IMAGE_SAVE_PATH}")
                cap.release()
                return IMAGE_SAVE_PATH
            else:
                logger.error("Failed to capture image")
                cap.release()
                return None
                
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            return None
    
    def count_leaves(self, image_path):
        """Count leaves in the captured image using the ML model"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"Image path {image_path} does not exist")
                return None

            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_tensor = self.transform(image).unsqueeze(0)  # Add batch dimension
            
            # Run inference
            with torch.no_grad():
                output = self.model(image_tensor)
            
            # Get leaf count (ensure it's a positive integer)
            leaf_count = max(0, int(round(output.item())))
            
            logger.info(f"Leaf count prediction: {leaf_count}")
            return leaf_count
            
        except Exception as e:
            logger.error(f"Error counting leaves: {e}")
            return None
    
    def publish_leaf_count(self, leaf_count):
        """Publish leaf count data to AWS IoT Core"""
        try:
            data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "node_id": "leaf_count_node",
                "leaf_count": leaf_count,
                "location": "greenhouse_monitoring"
            }
            
            message = json.dumps(data)
            self.mqtt_client.publish(MQTT_TOPIC, message, 1)  # QoS 1
            logger.info(f"Published leaf count data: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish leaf count: {e}")
            return False
    
    def run(self):
        """Main loop - capture images, count leaves, and publish results"""
        logger.info("Starting leaf count publisher...")
        logger.info(f"Will capture and analyze images every {CAPTURE_INTERVAL} seconds")
        
        consecutive_errors = 0
        max_errors = 5
        
        try:
            while True:
                try:
                    logger.info("Starting new leaf count cycle...")
                    
                    # Capture image
                    image_path = self.capture_image()
                    if not image_path:
                        consecutive_errors += 1
                        logger.warning("Failed to capture image, skipping this cycle")
                        time.sleep(CAPTURE_INTERVAL)
                        continue
                    
                    # Count leaves using ML model
                    leaf_count = self.count_leaves(image_path)
                    if leaf_count is None:
                        consecutive_errors += 1
                        logger.warning("Failed to count leaves, skipping this cycle")
                        time.sleep(CAPTURE_INTERVAL)
                        continue
                    
                    # Publish results
                    if self.publish_leaf_count(leaf_count):
                        consecutive_errors = 0  # Reset error counter
                        logger.info(f"Cycle completed successfully. Leaf count: {leaf_count}")
                    else:
                        consecutive_errors += 1
                    
                    # Clean up temporary image file
                    try:
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    except:
                        pass  # Don't fail if cleanup fails
                    
                    # Wait for next cycle
                    logger.info(f"Waiting {CAPTURE_INTERVAL} seconds until next capture...")
                    time.sleep(CAPTURE_INTERVAL)
                    
                except Exception as e:
                    logger.error(f"Unexpected error in main loop: {e}")
                    consecutive_errors += 1
                    time.sleep(CAPTURE_INTERVAL)
                
                # If too many consecutive errors, try to reconnect MQTT
                if consecutive_errors >= max_errors:
                    logger.warning("Too many consecutive errors, attempting to reconnect MQTT...")
                    self.reconnect_mqtt()
                    consecutive_errors = 0
                    
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()
    
    def reconnect_mqtt(self):
        """Attempt to reconnect MQTT connection"""
        try:
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            time.sleep(2)
            self.setup_mqtt()
            logger.info("MQTT reconnection successful")
        except Exception as e:
            logger.error(f"MQTT reconnection failed: {e}")
    
    def cleanup(self):
        """Clean up connections and temporary files"""
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            logger.info("MQTT connection closed")
        
        # Clean up temporary image file
        try:
            if os.path.exists(IMAGE_SAVE_PATH):
                os.remove(IMAGE_SAVE_PATH)
        except:
            pass

def main():
    """Main function"""
    try:
        publisher = LeafCountPublisher()
        publisher.run()
    except Exception as e:
        logger.error(f"Failed to start leaf count publisher: {e}")

if __name__ == "__main__":
    main()