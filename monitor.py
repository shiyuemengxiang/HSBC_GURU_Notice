import os
import re
import requests
from bs4 import BeautifulSoup

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

def clean_html_to_text(html: str) -> str:
    """提取页面纯文本并整理换行，避免 HTML 标签干扰"""
    soup = BeautifulSoup(html, "html.parser")
    # 移除脚本和样式
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return soup.get_text(separator="\n")

def is_irrelevant_update(line: str) -> bool:
    """过滤底部常规版本更新/维护提示，防止误报"""
    ignore_keywords = [
        "條款及細則於", "条款及细则于",
        "最後更新", "最后更新",
        "更新於", "更新于",
        "修訂於", "修订于",
        "版權所有", "版权所有"
    ]
    return any(kw in line for kw in ignore_keywords)

def extract_target_info(text: str) -> list[str]:
    """根据多维度关键词提取目标阶段及报名登记相关内容"""
    extracted = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 1. 匹配各个阶段定义（涵盖繁简，如 階段 1~9、階段 4: 2026 年...）
    stage_pattern = re.compile(
        r"((?:階段|阶段)\s*(?:[0-9一二三四五六七八九十]+|[IVXLCDM]+)[\s\S]*?(?:202[3-9]\s*年[^;\n\r]{2,60}))"
    )

    # 2. 匹配报名/登记/会员资格核心文案
    action_pattern = re.compile(
        r".*?(?:想成[為为]滙?豐?\s*Travel Guru|會員登記日期|会员登记日期|立即登記|立即登记|開放登記|开放登记|新一期).*?"
    )

    for line in lines:
        # 排除常规条款更新说明
        if is_irrelevant_update(line):
            continue

        # 匹配阶段条目
        stage_matches = stage_pattern.findall(line)
        if stage_matches:
            extracted.extend(stage_matches)

        # 匹配核心行动/登记说明语句
        if action_pattern.match(line):
            extracted.append(line)

    # 去重并保持顺序
    return list(dict.fromkeys(extracted))

def send_pushplus(title: str, content: str):
    """通过 PushPlus 发送微信通知"""
    if not PUSHPLUS_TOKEN:
        print("未检测到 PUSHPLUS_TOKEN 环境变量")
        return

    api_url = "https://www.pushplus.plus/send"
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
        "template": "markdown"
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

    text = clean_html_to_text(resp.text)
    items = extract_target_info(text)
    extracted_text = "\n".join(items).strip()

    if not extracted_text:
        print("未提取到匹配信息，页面可能结构变动，保留当前状态")
        return

    print("--- 抓取到的关键内容 ---")
    print(extracted_text)

    # 读取旧快照比对
    old_content = ""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            old_content = f.read().strip()

    if old_content == "":
        print("首次初始化，保存基准快照。")
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(extracted_text)
    elif old_content != extracted_text:
        print("检测到关键登记信息/阶段更新！正在发送推送...")
        send_pushplus("汇丰 Travel Guru 登记信息更新提醒", extracted_text)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(extracted_text)
    else:
        print("内容未发生有效变动，无需推送。")

if __name__ == "__main__":
    main()
