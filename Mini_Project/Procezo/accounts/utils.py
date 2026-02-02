import cv2
import numpy as np
import base64
import io
import torch
import logging
from PIL import Image
from fer.fer import FER
from facenet_pytorch import MTCNN, InceptionResnetV1

logger = logging.getLogger(__name__)

# Device setup (use GPU if available)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Declare models globally
_mtcnn = None
_resnet = None
_emotion_detector = None

def get_mtcnn():
    global _mtcnn
    if _mtcnn is None:
        _mtcnn = MTCNN(keep_all=False, device=device)
    return _mtcnn

def get_resnet():
    global _resnet
    if _resnet is None:
        _resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
    return _resnet

def get_emotion_detector():
    global _emotion_detector
    if _emotion_detector is None:
        try:
            _emotion_detector = FER(mtcnn=True)
        except Exception as e:
            logger.error(f"FER init error: {e}")
    return _emotion_detector

# ================= FACE VERIFICATION =================

def verify_face_with_embedding(base64_image_data, saved_embedding_list):
    """
    Checks whether the logged-in staff’s embedding matches the current photo.
    """
    try:
        if "," in base64_image_data:
            base64_image_data = base64_image_data.split(",", 1)[1]
        
        # Base64 to PIL Image
        img_bytes = base64.b64decode(base64_image_data)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

        mtcnn = get_mtcnn()
        resnet = get_resnet()

        # Detect the face
        face_tensor = mtcnn(pil_img)
        if face_tensor is None:
            return False

        # Generate the embedding
        face_tensor = face_tensor.unsqueeze(0).to(device)
        with torch.no_grad():
            emb = resnet(face_tensor)

        # Normalize current embedding
        current_emb = emb.cpu().numpy().flatten()
        current_emb = current_emb / np.linalg.norm(current_emb)

        # Normalize saved embedding from DB
        saved_emb = np.array(saved_embedding_list)
        saved_emb = saved_emb / np.linalg.norm(saved_emb)

        # Cosine Similarity (If similarity > 0.60, it is the same person)
        similarity = float(np.dot(current_emb, saved_emb))
        logger.info(f"Verification Similarity: {similarity:.4f}")

        return similarity >= 0.60

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

# ================= EMOTION DETECTION =================

def detect_emotion_from_base64_image(base64_image_data):
    detector = get_emotion_detector()
    if not detector: return 'Neutral'
        
    try:
        if "," in base64_image_data:
            base64_image_data = base64_image_data.split(",", 1)[1]
            
        img_bytes = base64.b64decode(base64_image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        results = detector.detect_emotions(frame)
        if results:
            emotions = results[0].get('emotions', {})
            top_emotion_raw = max(emotions.items(), key=lambda x: x[1])[0]
            
            mapping = {
                'happy': 'Happy', 
                'neutral': 'Neutral', 
                'sad': 'Sad',
                'angry': 'Angry', 
                'fear': 'Sad', 
                'disgust': 'Angry', 
                'surprise': 'Focused'
            }
            return mapping.get(top_emotion_raw, 'Neutral')
        return 'Neutral'
    except:
        return None