from supabase import create_client, Client
import time
from datetime import datetime

# ==========================================
# 🛑 請在此填入您的 Supabase 資料 🛑
# ==========================================
SUPABASE_URL = "https://kwgzhgvjcoydyblzsxkx.supabase.co"
SUPABASE_KEY = "sb_publishable_moWF6bEuaEthUu06n0C9qQ_GODAwPvY"
# ==========================================

print("--- 1. 開始連線測試 ---")

try:
    # 步驟 A: 嘗試連線
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ 客戶端初始化成功 (格式看起來正確)")

    # 步驟 B: 測試資料庫寫入 (Database Insert)
    print("\n--- 2. 測試寫入資料庫 ---")
    data = {
        "item_type": "TEST_CONNECTION",
        "confidence": 0.99,
        "image_url": "https://via.placeholder.com/150", # 假圖片
        "is_defect": False,
        "created_at": datetime.now().isoformat()
    }
    
    # 嘗試寫入
    response = supabase.table("laundry_logs").insert(data).execute()
    
    # 檢查結果
    # 新版 supabase-py 的 response 是一個物件，data 屬性存放結果
    if response.data:
        print(f"✅ 資料庫寫入成功！回傳資料: {response.data}")
    else:
        print("⚠️ 寫入看似執行了，但沒有回傳資料。請檢查 RLS。")

    # 步驟 C: 測試讀取相簿清單 (Storage Access)
    print("\n--- 3. 測試相簿權限 ---")
    buckets = supabase.storage.list_buckets()
    found = False
    for b in buckets:
        print(f"   發現相簿: {b.name}")
        if b.name == 'laundry-images':
            found = True
    
    if found:
        print("✅ 找到 'laundry-images' 相簿！")
    else:
        print("❌ 找不到 'laundry-images' 相簿，請確認名稱是否正確。")

    print("\n🎉 恭喜！如果以上都打勾，代表連線完全沒問題。")
    print("問題可能出在原本程式的邏輯，或圖片編碼部分。")

except Exception as e:
    print("\n❌ 發生錯誤！請將以下英文訊息貼給 AI 分析：")
    print("------------------------------------------------")
    print(e)
    print("------------------------------------------------")