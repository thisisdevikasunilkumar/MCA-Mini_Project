import base64
import io
import json
import numpy as np
from PIL import Image
from django.core.files.base import ContentFile

# facenet imports
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch

# initialize once (CPU if no GPU available)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

_mtcnn = None
_resnet = None


def get_mtcnn():
    global _mtcnn
    if _mtcnn is None:
        _mtcnn = MTCNN(keep_all=True, device=device)
    return _mtcnn


def get_resnet():
    global _resnet
    if _resnet is None:
        _resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
    return _resnet


# ================= BASE64 <-> PIL =================
def pil_from_base64(b64str):
    if not b64str:
        return None
    if "," in b64str:
        b64str = b64str.split(",", 1)[1]
    b = base64.b64decode(b64str)
    buf = io.BytesIO(b)
    img = Image.open(buf).convert('RGB')
    return img


def save_base64_to_contentfile(b64str, filename):
    if "," in b64str:
        b64str = b64str.split(",", 1)[1]
    data = base64.b64decode(b64str)
    return ContentFile(data, name=filename)


# ================= FACE UTILS =================
def count_faces(pil_img):
    mtcnn = get_mtcnn()
    boxes, probs = mtcnn.detect(pil_img)
    if boxes is None:
        return 0
    return len(boxes)


def get_embedding_from_pil(pil_img):
    mtcnn = get_mtcnn()
    resnet = get_resnet()

    boxes, probs = mtcnn.detect(pil_img)
    if boxes is None:
        return None

    areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
    idx = int(np.argmax(areas))

    try:
        faces = mtcnn.extract(pil_img, boxes, save_path=None)
        face_tensor = faces[idx].unsqueeze(0).to(device)
    except:
        face_tensor = mtcnn(pil_img)
        if face_tensor is None:
            return None
        if isinstance(face_tensor, list):
            face_tensor = face_tensor[0].unsqueeze(0).to(device)
        else:
            face_tensor = face_tensor.unsqueeze(0).to(device)

    with torch.no_grad():
        emb = resnet(face_tensor)

    emb = emb.cpu().numpy().flatten()
    norm = np.linalg.norm(emb)
    if norm == 0:
        return None

    return (emb / norm).tolist()


def cosine_similarity_vec(a, b):
    if a is None or b is None:
        return -1.0
    a = np.array(a)
    b = np.array(b)

    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return -1.0

    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return float(np.dot(a, b))


# NEW: Compare two PIL faces
def compare_two_images(img1_pil, img2_pil, threshold=0.60):
    emb1 = get_embedding_from_pil(img1_pil)
    emb2 = get_embedding_from_pil(img2_pil)
    if emb1 is None or emb2 is None:
        return False
    sim = cosine_similarity_vec(emb1, emb2)
    return sim >= threshold
