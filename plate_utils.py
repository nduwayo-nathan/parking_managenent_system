import cv2
import pytesseract
from ultralytics import YOLO
import os

# Initialize model once
model = YOLO('./best.pt')

def detect_plate(frame):
    """Detect and extract plate from frame"""
    results = model(frame)
    plates = []
    
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            plate_img = frame[y1:y2, x1:x2]
            
            # Process image for OCR
            processed = process_plate_image(plate_img)
            
            # Extract text
            plate_text = pytesseract.image_to_string(
                processed, 
                config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            ).strip().replace(" ", "")
            
            # Validate plate format
            plate = validate_plate(plate_text)
            if plate:
                plates.append({
                    'plate': plate,
                    'image': plate_img,
                    'processed': processed,
                    'coordinates': (x1, y1, x2, y2)
                })
    
    return plates

def process_plate_image(img):
    """Preprocess plate image for better OCR"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

def validate_plate(text):
    """Validate Kenyan plate format (e.g., KAA 123A)"""
    if "RA" not in text:
        return None
    start_idx = text.find("RA")
    plate = text[start_idx:start_idx+7]
    if len(plate) != 7:
        return None
    prefix, digits, suffix = plate[:3], plate[3:6], plate[6]
    if (prefix.isalpha() and prefix.isupper() and 
        digits.isdigit() and suffix.isalpha() and suffix.isupper()):
        return plate
    return None