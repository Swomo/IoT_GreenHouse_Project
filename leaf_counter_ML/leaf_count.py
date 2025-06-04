import torch
from torchvision import transforms
from PIL import Image
import cv2
import time
import os

import torch.nn as nn

class Conv7Net_3Channel_Wide(nn.Module):
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
        print("Flattened size:", out.shape)  # 🔍 DEBUG HERE

        out = self.fc1(out)
        out = self.dropout1(out)
        out = self.fc2(out)
        out = self.dropout2(out)
        out = self.fc3(out)
        return out
    
# Load the model
model = Conv7Net_3Channel_Wide(dropout=0.5)
model.load_state_dict(torch.load("best.pt", map_location=torch.device("cpu")))
model.eval()

# Image capture function
def capture_image():
    cap = cv2.VideoCapture(0)  # Use 0 for default camera
    ret, frame = cap.read()
    img_path = "leaf_image.jpg"
    if ret:
        cv2.imwrite(img_path, frame)
        print(f"[INFO] Image saved to {img_path}")
    else:
        print("[ERROR] Failed to capture image.")
        img_path = None
    cap.release()
    return img_path

# Leaf counting function
def count_leaves(image_path):
    if not os.path.exists(image_path):
        print(f"[ERROR] Image path {image_path} does not exist.")
        return None

    image = Image.open(image_path).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize((256, 256)),  # Match model input
        transforms.ToTensor()
    ])
    image_tensor = transform(image).unsqueeze(0)  # Add batch dimension
    with torch.no_grad():
        output = model(image_tensor)
    count = int(output.item())
    return count

# Test loop
while True:
    print("\n[INFO] Capturing image...")
    img = capture_image()
    if img:
        print("[INFO] Running model inference...")
        leaf_count = count_leaves(img)
        if leaf_count is not None:
            print(f"[RESULT] Leaf Count: {leaf_count}")
    time.sleep(60)  # Wait 60 seconds before next capture