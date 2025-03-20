import cv2
import numpy as np
import onnxruntime as ort
import pygame
import mss
import win32gui
import win32con
import win32api
import subprocess
from pynput import keyboard
import time

def get_cuda_version():
    try:
        result = subprocess.run(["nvcc", "--version"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if "release" in line:
                return line.strip()
    except FileNotFoundError:
        return "CUDA not found (nvcc not installed)"

print("======== SYSTEM INFORMATION ========")
print(f"OpenCV Version: {cv2.__version__}")
print(f"Numpy Version: {np.__version__}")
print(f"Pygame Version: {pygame.__version__}")
print(f"MSS Version: {mss.__version__}")
print(f"ONNX Runtime Version: {ort.__version__}")
print(f"CUDA Version: {get_cuda_version()}")
print("=====================================")

sess_options = ort.SessionOptions()
sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
sess_options.enable_mem_pattern = False
sess_options.enable_cpu_mem_arena = False
sess_options.log_severity_level = 3

try:
    session = ort.InferenceSession("best.onnx", sess_options, providers=['CUDAExecutionProvider'])
except Exception:
    session = ort.InferenceSession("best.onnx", sess_options, providers=['CPUExecutionProvider'])

CLASSES = ["CT-Body", "CT-Head", "T-Body", "T-Head"]
CLASS_COLORS = {
    "CT-Body": (0, 0, 255),
    "CT-Head": (0, 0, 139),
    "T-Body": (255, 0, 0),
    "T-Head": (139, 0, 0)
}

WIDTH, HEIGHT = 640, 640
BORDER = 10
CONFIDENCE_THRESHOLD = 0.4
NMS_THRESHOLD = 0.5

detection_active = True
show_text = True
aimbot_active = False

pygame.init()
screen = pygame.display.set_mode((WIDTH + BORDER * 2, HEIGHT + BORDER * 2), pygame.NOFRAME | pygame.DOUBLEBUF)
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

hwnd = pygame.display.get_wm_info()["window"]
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                       win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) |
                       win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST | win32con.WS_EX_TRANSPARENT)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY)
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

toggle_button = pygame.Rect(WIDTH - 100, 20, 80, 40)

current_mouse_x, current_mouse_y = win32api.GetCursorPos()
target_x, target_y = current_mouse_x, current_mouse_y
SMOOTHING_FACTOR = 0.6

def capture_screen():
    with mss.mss() as sct:
        screen_w, screen_h = sct.monitors[1]["width"], sct.monitors[1]["height"]
        x, y = (screen_w - WIDTH) // 2, (screen_h - HEIGHT) // 2
        screenshot = sct.grab((x, y, x + WIDTH, y + HEIGHT))
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)

def preprocess(frame):
    img = cv2.resize(frame, (640, 640)) / 255.0
    img = img.transpose(2, 0, 1)
    img = np.expand_dims(img, axis=0).astype(np.float32)
    return img

def postprocess_onnx_output(output):
    output = np.squeeze(output)
    boxes = []

    for pred in output.T:
        x_center, y_center, w, h = pred[:4]
        scores = pred[4:4 + len(CLASSES)]
        class_id, score = int(np.argmax(scores)), float(np.max(scores))

        if score > CONFIDENCE_THRESHOLD:
            x1, y1 = int(x_center - w / 2), int(y_center - h / 2)
            x2, y2 = int(x_center + w / 2), int(y_center + h / 2)
            boxes.append([x1, y1, x2, y2, score, class_id])

    if boxes:
        boxes = np.array(boxes)
        indices = cv2.dnn.NMSBoxes(boxes[:, :4].tolist(), boxes[:, 4].tolist(), CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
        return boxes[indices.flatten()].tolist() if len(indices) > 0 else []
    return []

def infer_yolo(frame):
    if detection_active:
        try:
            inputs = {session.get_inputs()[0].name: preprocess(frame)}
            return postprocess_onnx_output(session.run(None, inputs)[0])
        except Exception:
            return []
    return []

def get_target(detections):
    if not detections:
        return None
    
    body_targets = [d for d in detections if CLASSES[int(d[5])] in ["CT-Body", "T-Body"]]
    if body_targets:
        best_body = max(body_targets, key=lambda x: x[4])
        x1, y1, x2, y2 = best_body[:4]
        center_x = (x1 + x2) // 2
        center_y = y1 + (y2 - y1) // 4
        screen_w, screen_h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        window_x = (screen_w - WIDTH) // 2
        window_y = (screen_h - HEIGHT) // 2
        return (window_x + center_x, window_y + center_y)
    
    head_targets = [d for d in detections if CLASSES[int(d[5])] in ["CT-Head", "T-Head"]]
    if head_targets:
        best_head = max(head_targets, key=lambda x: x[4])
        x1, y1, x2, y2 = best_head[:4]
        center_x = (x1 + x2) // 2
        center_y = y1 + (y2 - y1) // 2
        screen_w, screen_h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        window_x = (screen_w - WIDTH) // 2
        window_y = (screen_h - HEIGHT) // 2
        return (window_x + center_x, window_y + center_y)
    
    return None

def aimbot(target):
    global current_mouse_x, current_mouse_y, target_x, target_y

    if target and aimbot_active:
        target_x, target_y = target
        current_mouse_x, current_mouse_y = win32api.GetCursorPos()
        dx = target_x - current_mouse_x
        dy = target_y - current_mouse_y

        if abs(dx) > 5 or abs(dy) > 5:
            new_x = current_mouse_x + int(dx * SMOOTHING_FACTOR)
            new_y = current_mouse_y + int(dy * SMOOTHING_FACTOR)
            screen_w, screen_h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
            norm_x = int((new_x * 65535) / screen_w)
            norm_y = int((new_y * 65535) / screen_h)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE,
                               norm_x, norm_y, 0, 0)

def draw_detections(detections, screen):
    for x1, y1, x2, y2, score, class_id in detections:
        class_name = CLASSES[int(class_id)]
        color = CLASS_COLORS.get(class_name, (255, 255, 255))
        pygame.draw.rect(screen, color, (x1 + BORDER, y1 + BORDER, x2 - x1, y2 - y1), 2)
        if show_text:
            text_surface = font.render(f"{class_name} {score:.2f}", True, color)
            screen.blit(text_surface, (x1 + BORDER, max(y1 + BORDER - 20, BORDER)))

def draw_toggle_button(screen):
    button_color = (0, 200, 0) if detection_active else (200, 0, 0)
    button_text = "ON" if detection_active else "OFF"
    pygame.draw.rect(screen, button_color, toggle_button)
    text_surface = font.render(button_text, True, (255, 255, 255))
    screen.blit(text_surface, (WIDTH - 75, 30))

def draw_legend(screen):
    legend_text = "F1: Detection | F2: Text | K: Aim"
    text_surface = font.render(legend_text, True, (255, 255, 255))
    screen.blit(text_surface, (BORDER, BORDER))

def on_press(key):
    global detection_active, show_text, aimbot_active
    try:
        if key == keyboard.Key.f1:
            detection_active = not detection_active
        elif key == keyboard.Key.f2:
            show_text = not show_text
        elif key == keyboard.KeyCode.from_char('k'):
            aimbot_active = True
    except AttributeError:
        pass

def on_release(key):
    global aimbot_active
    try:
        if key == keyboard.KeyCode.from_char('k'):
            aimbot_active = False
    except AttributeError:
        pass

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

running = True
while running:
    frame = capture_screen()
    detections = infer_yolo(frame)

    screen.fill((0, 0, 0, 0))

    frame_color = (0, 255, 0) if detection_active else (255, 0, 0)
    pygame.draw.rect(screen, frame_color, (BORDER, BORDER, WIDTH, HEIGHT), 2)

    draw_detections(detections, screen)
    draw_toggle_button(screen)
    draw_legend(screen)

    target = get_target(detections)
    aimbot(target)

    pygame.display.update()
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and toggle_button.collidepoint(event.pos):
            detection_active = not detection_active

pygame.quit()