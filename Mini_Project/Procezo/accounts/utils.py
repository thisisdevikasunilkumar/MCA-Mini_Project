import cv2
import numpy as np
import base64
from fer.fer import FER
import logging # Use logging for cleaner server output

# Set up logging (optional, but good practice)
logger = logging.getLogger(__name__)

try:
    # Use mtcnn=True for better face detection
    emotion_detector = FER(mtcnn=True) 
except Exception as e:
    logger.error(f"FER initialization failed: {e}. Check dependencies (tensorflow, Keras, etc.).")
    emotion_detector = None


def detect_emotion_from_base64_image(base64_image_data):
    if not emotion_detector:
        return 'Neutral' 
        
    try:
        # Decode Base64 string to an OpenCV image
        img_bytes = base64.b64decode(base64_image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return None

        # 3. Detect emotions
        results = emotion_detector.detect_emotions(frame)

        if results:
            first = results[0]
            emotions = first.get('emotions') or {}
            top_emotion_raw = None
            
            # Robustly find the top emotion key
            if isinstance(emotions, dict) and emotions:
                # Find the emotion with the maximum score
                top_emotion_raw = max(emotions.items(), key=lambda x: x[1])[0]
            elif isinstance(first, dict) and 'top_emotion' in first:
                top_emotion_raw = first.get('top_emotion')
            
            if top_emotion_raw:
                # --- Emotion Mapping to your Model Choices ---
                emotion_map = {
                    'happy': 'Happy',
                    'neutral': 'Neutral', # Ensure Neutral is mapped
                    'sad': 'Sad',
                    'angry': 'Angry',
                    'fear': 'Sad',     
                    'disgust': 'Angry', 
                    'surprise': 'Focused'
                }
                
                # Use the mapped emotion, or default to Neutral
                final_emotion = emotion_map.get(top_emotion_raw, 'Neutral')
                logger.info(f"Detected face. Raw: {top_emotion_raw}, Mapped: {final_emotion}")
                return final_emotion

        logger.info("No face detected in the frame.") 
        return 'Neutral' # If no face is detected
        
    except Exception as e:
        logger.error(f"Error during emotion detection: {e}")
        return None