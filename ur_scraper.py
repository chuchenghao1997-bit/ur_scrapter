import requests
import datetime
import html
import math
import json
import os
import smtplib
import time
from email.mime.text import MIMEText
from email.header import Header

# ======================================================
# 🔧 配置区
# ======================================================

from_addr = "chuchenghao1997@gmail.com"                  # 发件人（你自己的 Gmail）
password = "ezbj wybm fpza fjxr"                          # Gmail 应用专用密码
to_addrs = ["chuchenghao1997@gmail.com", "ganganhaohao2024@gmail.com"]  # 收件人，可以填多个

STATE_FILE = "ur_state.json"
LOG_DIR = "logs"

danchi_list = [
    {"name": "潮見駅前プラザ一番街", "shisya": "20", "danchi": "645", "referer": "https://www.ur-net.go.jp/chintai/kanto/tokyo/20_6450.html"},
    {"name": "幕張ベイタウン パティオス22番街", "shisya": "30", "danchi": "596", "referer": "https://www.ur-net.go.jp/chintai/kanto/chiba/30_5960.html"},
    {"name": "ハートアイランド新田二番街", "shisya": "20", "danchi": "681", "referer": "https://www.ur-net.go.jp/chintai/kanto/tokyo/20_6810.html"},
    {"name": "ひばりが丘パークヒルズ", "shisya": "20", "danchi": "677", "referer": "https://www.ur-net.go.jp/chintai/kanto/tokyo/20_6771.html"},
    {"name": "プラザ新小金井", "shisya": "20", "danchi": "514", "referer": "https://www.ur-net.go.jp/chintai/kanto/tokyo/20_5140.html"},
    {"name": "コンフォール明神台", "shisya": "40", "danchi": "400", "referer": "https://www.ur-net.go.jp/chintai/kanto/kanagawa/40_4000.html"},
    # {"name": "越谷レイクタウン", "shisya": "50", "danchi": "180", "referer": "https://www.ur-net.go.jp/chintai/kanto/saitama/50_1800.html"},
    # {"name": "浜甲子園なぎさ街", "shisya": "80", "danchi": "515", "referer": "https://www.ur-net.go.jp/chintai/kansai/hyogo/80_5150.html"},
]

# ======================================================
# 📨 Gmail 通知
# ======================================================

def send_email(subject, body, retries=3):
    smtp_server = "smtp.gmail.com"
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = Header(subject, "utf-8")

    for i in range(retries):
        try:
            server = smtplib.SMTP(smtp_server, 587, timeout=30)
            server.ehlo()
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            print(f"✅ 已发送邮件到 {', '.join(to_addrs)}")
            return
        except Exception as e:
            print(f"⚠️ 第 {i+1} 次发送失败: {e}")
            time.sleep(5)
    print("❌ 邮件发送最终失败")

# ======================================================
# 🔍 数据抓取
# ======================================================

url = "https://chintai.r6.ur-net.go.jp/chintai/api/bukken/detail/detail_bukken_room/"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.ur-net.go.jp",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

def safe_post(url, headers, data, retries=5, delay=2):
    for i in range(retries):
        resp = requests.post(url, headers=headers, data=data)
        if resp.status_code == 200:
            return resp
        print(f"⚠️ 请求失败 {resp.status_code}, {i+1}/{retries} 次尝试...")
        time.sleep(delay)
    resp.raise_for_status()
    return resp

def fetch_pet_rooms(danchi):
    base_payload = {
        "rent_low": "", "rent_high": "",
        "floorspace_low": "", "floorspace_high": "",
        "shisya": danchi["shisya"], "danchi": danchi["danchi"],
        "shikibetu": "0", "newBukkenRoom": "",
        "orderByField": "0", "orderBySort": "0",
        "pageIndex": "0", "sp": ""
    }

    h = headers.copy()
    h["Referer"] = danchi["referer"]

    resp = safe_post(url, headers=h, data=base_payload)
    first_page = resp.json()
    if not first_page or not isinstance(first_page, list):
        return []

    all_count = int(first_page[0].get("allCount", len(first_page)))
    row_max = int(first_page[0].get("rowMax", len(first_page)))
    total_pages = math.ceil(all_count / row_max)

    pet_rooms = []
    for page in range(total_pages):
        payload = base_payload.copy()
        payload["pageIndex"] = str(page)
        resp = safe_post(url, headers=h, data=payload)
        rooms = resp.json()
        for room in rooms:
            features = [f.get("特徴名") for f in room.get("featureParam", [])]
            if "ペット共生住宅" in features:
                pet_rooms.append(room)
    return pet_rooms

# ======================================================
# 💾 状态存储
# ======================================================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ======================================================
# 📝 日志函数
# ======================================================

def write_log(text):
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"{datetime.date.today()}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")

# ======================================================
# 🚀 主程序
# ======================================================

def main():
    now = datetime.datetime.now()
    header = (
        "\n==============================\n"
        f"==== 抓取时间: {now} ====\n"
        "==============================\n"
    )
    print(header)
    write_log(header)

    prev_state = load_state()
    new_state = {}
    notify_messages = [header]

    for d in danchi_list:
        output_lines = [f"【{d['name']}】"]
        pet_rooms = fetch_pet_rooms(d)
        new_state[d["name"]] = [r["name"] for r in pet_rooms]

        if not pet_rooms:
            output_lines.append("  → 当前没有ペット共生住宅的空房\n")
        else:
            old_rooms = set(prev_state.get(d["name"], []))
            new_rooms = set(new_state[d["name"]])
            added = new_rooms - old_rooms

            if added:
                output_lines.append(f"  🔔 {d['name']} 新出现物件: {', '.join(added)}")

            output_lines.append("  ペット共生住宅空房列表:")
            for r in pet_rooms:
                floorspace = html.unescape(r["floorspace"])
                output_lines.append(
                    f"    - {r['name']} | "
                    f"{r.get('rent') or r.get('rent_normal')} | "
                    f"共益費:{r['commonfee']} | "
                    f"{r['type']} | {floorspace} | {r['floor']}"
                )
            output_lines.append("")

        block_text = "\n".join(output_lines)
        print(block_text)
        write_log(block_text)

        if pet_rooms and added:
            notify_messages.append(block_text)

    if len(notify_messages) > 1:
        body = "\n".join(notify_messages)
        send_email("UR新空房提醒", body)

    save_state(new_state)

if __name__ == "__main__":
    main()
