#!/usr/bin/env python3
"""
互联网行业每日新闻摘要
每天早上 7 点由 GitHub Actions 自动运行
"""

import json
import urllib.request
import urllib.parse
import os
from datetime import datetime

PUSHPLUS_TOKEN = os.environ.get('PUSHPLUS_TOKEN', '6477da44993d48faaf32005b4e0e9d8a')
BING_API_KEY = os.environ.get('BING_API_KEY', '')

def search_news_bing(query, count=10):
    """使用 Bing News Search API 搜索新闻"""
    if not BING_API_KEY:
        return search_news_free(query)
    
    url = f"https://api.bing.microsoft.com/v7.0/news/search?q={urllib.parse.quote(query)}&count={count}&mkt=zh-CN&freshness=Day"
    req = urllib.request.Request(url, headers={'Ocp-Apim-Subscription-Key': BING_API_KEY})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('value', [])
    except Exception as e:
        print(f"Bing API 错误: {e}")
        return []

def search_news_free(query):
    """使用免费的 DuckDuckGo 搜索"""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query + ' 新闻')}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
            # 简单解析搜索结果
            results = []
            import re
            links = re.findall(r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]+)</a>', html)
            
            for i, (link, title) in enumerate(links[:10]):
                snippet = snippets[i] if i < len(snippets) else ""
                results.append({
                    'name': title.strip(),
                    'url': link,
                    'description': snippet.strip()
                })
            return results
    except Exception as e:
        print(f"搜索错误: {e}")
        return []

def get_news_from_rss():
    """从 RSS 源获取新闻"""
    rss_feeds = [
        ('https://36kr.com/feed', '36氪'),
        ('https://www.huxiu.com/rss/0.xml', '虎嗅'),
    ]
    
    all_news = []
    for feed_url, source in rss_feeds:
        try:
            req = urllib.request.Request(feed_url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            })
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode('utf-8')
                import re
                items = re.findall(r'<item>.*?<title>(?:<!\[CDATA\[)?([^\]<]+)(?:\]\]>)?</title>.*?<link>([^<]+)</link>.*?<description>(?:<!\[CDATA\[)?([^\]<]*)(?:\]\]>)?</description>.*?</item>', content, re.DOTALL)
                
                for title, link, desc in items[:5]:
                    all_news.append({
                        'title': title.strip(),
                        'url': link.strip(),
                        'description': desc.strip()[:100],
                        'source': source
                    })
        except Exception as e:
            print(f"RSS {source} 错误: {e}")
    
    return all_news

def generate_news_content():
    """生成新闻内容"""
    print("正在获取新闻...")
    
    # 搜索不同领域的新闻
    queries = [
        "AI 人工智能 最新消息",
        "腾讯 阿里 字节跳动",
        "互联网 科技 今日新闻"
    ]
    
    all_news = []
    
    # 从搜索获取
    for query in queries:
        results = search_news_free(query)
        for r in results:
            all_news.append({
                'title': r.get('name', r.get('title', '')),
                'url': r.get('url', ''),
                'description': r.get('description', '')
            })
    
    # 从 RSS 获取
    rss_news = get_news_from_rss()
    for r in rss_news:
        all_news.append({
            'title': r['title'],
            'url': r['url'],
            'description': r['description']
        })
    
    # 去重并选择前10条
    seen_titles = set()
    unique_news = []
    for news in all_news:
        title = news['title']
        if title and title not in seen_titles and len(title) > 10:
            seen_titles.add(title)
            unique_news.append(news)
            if len(unique_news) >= 10:
                break
    
    return unique_news

def push_to_wechat(title, content):
    """推送到微信"""
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code') == 200:
                print("推送成功!")
                return True
            else:
                print(f"推送失败: {result.get('msg')}")
                return False
    except Exception as e:
        print(f"推送错误: {e}")
        return False

def main():
    today = datetime.now().strftime("%m月%d日")
    
    # 获取新闻
    news_list = generate_news_content()
    
    if not news_list:
        print("未获取到新闻")
        push_to_wechat(
            f"互联网日报 {today}",
            "<p>今日新闻获取失败，请稍后手动查看。</p>"
        )
        return
    
    # 生成 HTML 内容
    html_parts = ["<div style='font-size:15px;line-height:1.6;'>"]
    
    for i, news in enumerate(news_list, 1):
        title = news['title'][:50]  # 限制标题长度
        desc = news['description'][:80] if news['description'] else "点击查看详情"
        url = news['url']
        
        html_parts.append(
            f"<p style='margin-bottom:14px;'>"
            f"<b>{i}. {title}</b><br>"
            f"{desc}<br>"
            f"<a href='{url}' style='color:#1890ff;'>阅读原文</a></p>"
        )
    
    html_parts.append("</div>")
    html_content = "".join(html_parts)
    
    # 推送
    push_to_wechat(f"互联网日报 {today}", html_content)

if __name__ == "__main__":
    main()
