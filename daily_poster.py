#!/usr/bin/env python3
"""
CubeBuff 每日定时发帖脚本 (Bluesky)
每天发布 20 篇不同内页（禁止重复引用首页），带精准锚文本与动态富媒体卡片
"""

import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

PDS_URL = "https://bsky.social"
HANDLE = os.getenv("BLUESKY_HANDLE", "info@cubebuff.com")
APP_PASSWORD = os.getenv("BLUESKY_PASSWORD", "etku-db6m-dexn-6gcs")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "posted_history.json")
LOG_FILE = os.path.join(BASE_DIR, "daily_publish.log")

TEMPLATES = [
    "Tired of dusting your build? Keep every single detail pristine with a custom-engineered {anchor} from CubeBuff. Crystal-clear acrylic with snug magnetic closures. #LEGO #AFOL #CubeBuff #ToyDisplay",
    "Give your masterpiece the museum-grade spotlight it truly deserves. Explore precision-crafted {anchor} at CubeBuff! Built to match exact set dimensions. #LEGOCommunity #ToyCollector #CubeBuff #LEGODisplay",
    "Running low on table space? Maximize your room setup with sleek, sturdy {anchor} engineered specifically for LEGO collectors by CubeBuff. #HomeDecor #ToyDisplay #CubeBuff #LEGOStorage",
    "Never settle for generic boxes that don't fit right. Check out {anchor} by CubeBuff for seamless protection and high-end aesthetics. #LEGOCollectors #LEGOSet #CubeBuff #AFOL",
    "Protect your cherished bricks from dust, scratches, and accidental knocks. Upgrade your collection with {anchor} from CubeBuff today! #LEGOCare #BrickLovers #CubeBuff #ToyShowcase",
    "Turn your favorite LEGO build into a centerpiece art piece. Discover premium {anchor} with optional custom background plates at CubeBuff. #Legostagram #AFOL #CubeBuff #LEGOShowcase"
]

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def login() -> dict:
    resp = requests.post(
        f"{PDS_URL}/xrpc/com.atproto.server.createSession",
        json={"identifier": HANDLE, "password": APP_PASSWORD},
        timeout=20
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Bluesky 登录失败 ({resp.status_code}): {resp.text}")
    return resp.json()

def upload_blob(access_jwt: str, img_bytes: bytes, mime_type: str = "image/png") -> dict:
    resp = requests.post(
        f"{PDS_URL}/xrpc/com.atproto.repo.uploadBlob",
        headers={"Content-Type": mime_type, "Authorization": f"Bearer {access_jwt}"},
        data=img_bytes,
        timeout=30
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("blob")

def fetch_all_deep_urls() -> list:
    urls = []
    # 抓取 Collections
    try:
        r = requests.get("https://www.cubebuff.com/sitemap_collections_1.xml?from=519523107138&to=523174773058", timeout=15)
        root = ET.fromstring(r.text)
        for u in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            loc = u.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if loc is not None and "frontpage" not in loc.text:
                urls.append(loc.text)
    except Exception as e:
        log(f"抓取 Collections 异常: {e}")

    # 抓取 Products
    try:
        r2 = requests.get("https://www.cubebuff.com/sitemap_products_1.xml?from=10496173474114&to=10496176456002", timeout=15)
        root2 = ET.fromstring(r2.text)
        for u in root2.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            loc = u.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if loc is not None and loc.text != "https://www.cubebuff.com/":
                urls.append(loc.text)
    except Exception as e:
        log(f"抓取 Products 异常: {e}")

    urls = list(dict.fromkeys(urls))
    return urls

def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history: dict):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存历史记录失败: {e}")

def get_page_meta(url: str):
    r = requests.get(url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    def get_tag(prop, default=""):
        t = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        return t["content"] if t and "content" in t.attrs else default
    title = get_tag("og:title", "CubeBuff LEGO Display Case")
    desc = get_tag("og:description", "Shop premium custom display cases and wall mounts for LEGO sets.")
    img = get_tag("og:image", "")
    if img.startswith("//"):
        img = "https:" + img

    # 生成适用的锚文本
    clean_title = re.sub(r"\|\s*CubeBuff.*", "", title).strip()
    clean_title = clean_title.replace("LEGO®", "LEGO").strip()
    anchor = clean_title
    if len(anchor) > 40 or len(anchor) < 5:
        # 从 URL slug 生成清晰锚文本
        slug = url.rstrip("/").split("/")[-1]
        anchor = slug.replace("-", " ").title()
        if "Display Case" not in anchor and "Frame" not in anchor:
            anchor += " display case"

    return title, desc, img, anchor

def build_facets(text: str, anchor_text: str, target_url: str) -> list:
    text_bytes = text.encode("utf-8")
    anchor_bytes = anchor_text.encode("utf-8")
    start = text_bytes.find(anchor_bytes)
    if start == -1:
        return []
    end = start + len(anchor_bytes)
    return [
        {
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": target_url}]
        }
    ]

def run_daily_task(count: int = 20):
    log(f"=== 开始执行每日定时发布任务 (目标: {count} 篇) ===")
    all_urls = fetch_all_deep_urls()
    log(f"已获取全站深层落地页库，共 {len(all_urls)} 个独立内页。")
    if not all_urls:
        log("❌ 未能获取到内页链接，任务终止。")
        return

    history = load_history()
    # 按照发布次数和上次发布时间排序，优先选择从未发布或最久未发布的 URL
    def sort_key(u):
        rec = history.get(u, {})
        return (rec.get("count", 0), rec.get("last_posted", 0))

    sorted_urls = sorted(all_urls, key=sort_key)
    target_urls = sorted_urls[:count]

    session = login()
    access_jwt = session["accessJwt"]
    user_did = session["did"]
    actual_handle = session.get("handle", "cubebuff.bsky.social")
    log(f"✅ Bluesky 登录成功: @{actual_handle}")

    success_count = 0
    for idx, url in enumerate(target_urls, start=1):
        log(f"\n--- [{idx}/{count}] 正在处理内页: {url} ---")
        try:
            og_title, og_desc, og_img, anchor = get_page_meta(url)
            log(f"提取锚文本: '{anchor}' | 标题: {og_title}")

            tmpl = random.choice(TEMPLATES)
            post_text = tmpl.format(anchor=anchor)

            facets = build_facets(post_text, anchor, url)
            if not facets:
                log(f"⚠️ 锚文本匹配失败，跳过该项")
                continue

            blob = None
            if og_img:
                try:
                    img_res = requests.get(og_img, timeout=12)
                    if img_res.status_code == 200:
                        blob = upload_blob(access_jwt, img_res.content, "image/png")
                except Exception as e:
                    log(f"上传封面缩略图跳过: {e}")

            now_z = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            record = {
                "$type": "app.bsky.feed.post",
                "text": post_text,
                "facets": facets,
                "createdAt": now_z,
                "langs": ["en"],
                "embed": {
                    "$type": "app.bsky.embed.external",
                    "external": {
                        "uri": url,
                        "title": og_title,
                        "description": og_desc[:250],
                    }
                }
            }
            if blob:
                record["embed"]["external"]["thumb"] = blob

            post_resp = requests.post(
                f"{PDS_URL}/xrpc/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {access_jwt}"},
                json={"repo": user_did, "collection": "app.bsky.feed.post", "record": record},
                timeout=15
            )

            if post_resp.status_code == 200:
                resp_data = post_resp.json()
                post_rkey = resp_data["uri"].split("/")[-1]
                post_url = f"https://bsky.app/profile/{actual_handle}/post/{post_rkey}"
                log(f"✅ 第 {idx} 篇发布成功: {post_url}")
                success_count += 1
                history[url] = {
                    "count": history.get(url, {}).get("count", 0) + 1,
                    "last_posted": time.time(),
                    "last_post_url": post_url,
                    "anchor": anchor
                }
                save_history(history)
            else:
                log(f"❌ 第 {idx} 篇发布失败 ({post_resp.status_code}): {post_resp.text}")

        except Exception as err:
            log(f"❌ 处理发生异常: {err}")

        # 发帖间隔 15 秒，平滑分布，规避高频风控
        if idx < count:
            time.sleep(15)

    log(f"\n=== 每日任务完成: 成功 {success_count}/{count} 篇 ===")

if __name__ == "__main__":
    count = 20
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            pass
    run_daily_task(count)
