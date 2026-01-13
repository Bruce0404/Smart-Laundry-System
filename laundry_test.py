import cv2
from ultralytics import YOLO
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# --- 1. 安全設定 ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 錯誤：找不到 .env 設定")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
model = YOLO('yolov8n.pt') 
cap = cv2.VideoCapture(1) # 確認鏡頭編號

# 設定解析度
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# ==========================================
# 📋 名單設定
# ==========================================
ALLOWED_CLASSES = [
    'tie', 'scissors', 'backpack', 'handbag', 'suitcase', 'umbrella', 
    'teddy bear', 'stain', 'shirt', 'pants', 'dress'
]
DEFECT_CLASSES = ['tie', 'scissors', 'stain'] 

# 🔥 設定信心門檻 (調低一點，讓 AI 敢說話)
CONF_THRESHOLD = 0.3 

# 除錯模式開關 (預設開啟，讓您先看清楚)
debug_mode = True 

print("========================================")
print("系統啟動！")
print(f"目前模式: {'除錯模式 (看全部)' if debug_mode else '過濾模式 (只看衣物)'}")
print("按 'd' 鍵切換模式")
print("按 's' 鍵上傳")
print("按 'q' 鍵離開")
print("========================================")

def upload_to_supabase(frame, detected_data):
    # (這部分維持不變，省略以節省篇幅)
    # ...
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"laundry_{timestamp}.jpg"
        _, buffer = cv2.imencode('.jpg', frame)
        supabase.storage.from_("laundry-images").upload(filename, buffer.tobytes(), {"content-type": "image/jpeg"})
        image_url = f"{SUPABASE_URL}/storage/v1/object/public/laundry-images/{filename}"
        data = {
            "item_type": detected_data['type'],
            "confidence": detected_data['conf'],
            "image_url": image_url,
            "is_defect": detected_data['is_defect'],
            "created_at": datetime.now().isoformat()
        }
        supabase.table("laundry_logs").insert(data).execute()
        print(f"✅ 上傳成功！")
    except Exception as e:
        print(f"❌ 上傳失敗: {e}")

while True:
    success, frame = cap.read()
    if not success: break

    # 1. 執行 YOLO 辨識 (信心度設低一點 0.3)
    results = model(frame, stream=True, conf=CONF_THRESHOLD)
    
    annotated_frame = frame.copy()
    
    # 畫面上方的狀態列
    status_text = "DEBUG MODE (Show All)" if debug_mode else "FILTER MODE (Laundry Only)"
    status_color = (100, 100, 100) if debug_mode else (0, 0, 0)
    cv2.rectangle(annotated_frame, (0, 0), (1280, 40), (255, 255, 255), -1)
    cv2.putText(annotated_frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

    top_object_data = {'type': 'unknown', 'conf': 0.0, 'is_defect': False}
    valid_object_found = False 

    for r in list(results):
        for box in r.boxes:
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            conf = float(box.conf[0])
            
            # 取得座標
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # 🛑 判斷邏輯 🛑
            is_allowed = class_name in ALLOWED_CLASSES
            
            # 如果是除錯模式，我要在小黑窗看到所有東西
            if debug_mode:
                print(f"👀 AI 看到: {class_name} (信心度: {conf:.2f})")

            if not is_allowed:
                # [非白名單物品]
                if debug_mode:
                    # 除錯模式下，用「灰色虛線框」畫出來，告訴你它被過濾了
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
                    cv2.putText(annotated_frame, f"{class_name} (Ignored)", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
                continue # 如果不是除錯模式，就直接跳過
            
            # --- 以下是有效物品 ---
            valid_object_found = True
            
            if class_name in DEFECT_CLASSES:
                # [瑕疵/領帶] -> 紅框
                color = (0, 0, 255) 
                label = f"DEFECT! {class_name} {conf:.2f}"
                top_object_data = {'type': class_name, 'conf': conf, 'is_defect': True}
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 4)
            else:
                # [正常衣物] -> 綠框
                color = (0, 255, 0)
                label = f"{class_name} {conf:.2f}"
                if not top_object_data['is_defect']:
                    top_object_data = {'type': class_name, 'conf': conf, 'is_defect': False}
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            cv2.putText(annotated_frame, label, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Smart Laundry - Debugger", annotated_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('d'):
        debug_mode = not debug_mode # 切換開關
        print(f"🔄 切換模式 -> {debug_mode}")
    elif key == ord('s'):
        if valid_object_found or debug_mode: # 除錯模式下也可以強制上傳
            print("--- 觸發上傳 ---")
            upload_to_supabase(frame, top_object_data)

cap.release()
cv2.destroyAllWindows()