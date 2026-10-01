import os
import re
import requests

URL = "https://www.redhotoffers.hsbc.com.hk/tc/latest-offers/travel-guru/"
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
CACHE_FILE = "last_content.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def send_pushplus(title: str, content: str):
    """通过 PushPlus 发送微信通知"""
    if not PUSHPLUS_TOKEN:
        print("未检测到 PUSHPLUS_TOKEN 环境变量")
        return

    api_url = "https://www.pushplus.plus/send"
    
    # 格式化为 Markdown 消息体
    markdown_content = (
        f"### 汇丰 Travel Guru 登记信息更新\n\n"
        f"**最新检测到的关键内容：**\n\n"
        f"```text\n{content}\n```\n\n"
        f"[👉 点击前往汇丰活动官网]({URL})"
    )

    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": markdown_content,
        "template": "markdown"  # 使用 Markdown 模板渲染
    }

    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        result = resp.json()
        if result.get("code") == 200:
            print("PushPlus 推送成功")
        else:
            print(f"PushPlus 推送失败: {result.get('msg')}")
    except Exception as e:
        print(f"网络请求异常: {e}")

def main():
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.encoding = "utf-8"
    html = resp.text

    # 提取所有包含“階段”及日期的文本段落（精确锁定条款与登记日期）
    stages = re.findall(r"(階段\s*[0-9一二三四五六七八九十]+[^，。；\n\r<]{2,60})", html)
    
    # 提取“會員登記”相关的关键句子
    registration_info = re.findall(r"([^。；\n\r<]{0,30}登記[^。；\n\r<]{0,50})", html)

    extracted_items = list(dict.fromkeys(stages + registration_info))
    extracted_text = "\n".join(extracted_items).strip()

    if not extracted_text:
        print("未提取到匹配信息，页面可能结构变动，保留当前状态")
        return

    print("--- 抓取到的关键内容 ---")
    print(extracted_text)

    # 读取上一次的内容快照
    old_content = ""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            old_content = f.read().strip()

    # 首次运行或内容发生变化时触发通知
    if old_content == "":
        print("首次初始化，保存基准快照。")
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(extracted_text)
    elif old_content != extracted_text:
        print("检测到内容更新！正在发送通知...")
        send_pushplus("汇丰 Travel Guru 登记信息变动提醒", extracted_text)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(extracted_text)
    else:
        print("内容未变化，无需提醒。")

if __name__ == "__main__":
    main()
