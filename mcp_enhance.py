# mcp_enhance.py - AI 标注插件 for TrendRadar
import requests
import time
import json
import os

MCP_SERVER_URL = "http://localhost:3333/mcp"

def is_mcp_available():
    try:
        res = requests.post(MCP_SERVER_URL, json={"jsonrpc": "2.0", "method": "mcp/ping", "id": 1}, timeout=2)
        return res.status_code == 200
    except:
        return False

def annotate_news_with_ai(news_list):
    if not is_mcp_available():
        print("⚠️ MCP 服务未运行，跳过 AI 标注")
        return news_list
    
    annotated = []
    for i, item in enumerate(news_list):
        title = item.get("title", "")
        platform = item.get("platform", "")
        # 构造 prompt
        prompt = f"""你是一位资深A股事件驱动型投资分析师。请分析以下新闻：
【新闻标题】{title}
【来源平台】{platform}
要求：
1. 判断该新闻是否属于「事件驱动型」（如政策出台、订单签订、技术突破、处罚调查等），若否，返回空
2. 若是，请用一句话概括事件类型
3. 列出最可能受益的2个产业链环节
4. 各环节推荐1家市值<200亿的弹性小盘标的（若无则写“暂无明确小盘标的”）
5. 标注潜在风险：如“信息未证实”“影响有限”等
输出格式（严格按此JSON）：
{{"event_type": "...", "benefit_sectors": ["...", "..."], "small_cap_stocks": ["...", "..."], "risk_note": "..."}}
"""
        try:
            res = requests.post(MCP_SERVER_URL, json={
                "jsonrpc": "2.0",
                "method": "mcp/invoke_tool",
                "params": {
                    "name": "mcp/talk_with_model",
                    "arguments": {
                        "messages": [{"role": "user", "content": prompt}]
                    }
                },
                "id": i+1
            }, timeout=5)
            
            if res.status_code == 200:
                result = res.json()
                if "result" in result and "content" in result["result"]:
                    try:
                        ai_data = json.loads(result["result"]["content"])
                        item["ai_annotation"] = ai_data
                    except:
                        item["ai_annotation"] = {"error": "解析失败"}
            time.sleep(0.2)  # 防限流
        except Exception as e:
            item["ai_annotation"] = {"error": str(e)}
        annotated.append(item)
    return annotated

def add_ai_html_blocks(html_content, news_groups):
    """在 HTML 报告中插入 AI 标注区块"""
    lines = html_content.split('\n')
    new_lines = []
    in_news_item = False
    for line in lines:
        new_lines.append(line)
        # 在每条新闻后插入 AI block（简单匹配）
        if line.strip().startswith('<li>') and 'href=' in line:
            # 找到对应新闻，插入标注
            title_match = line.split('">')[1].split('</a>')[0] if '">' in line and '</a>' in line else ""
            for group in news_groups:
                for item in group.get("news", []):
                    if title_match in item.get("title", "") and "ai_annotation" in item:
                        ann = item["ai_annotation"]
                        if ann and "error" not in ann:
                            block = f'''
                            <div class="ai-annotation" style="background:#f8f9fa; padding:8px; border-left:3px solid #1976d2; margin:8px 0; font-size:0.9em;">
                              🤖 <b>AI分析</b>：{ann.get("event_type", "")}<br>
                              ✅ <b>受益环节</b>：{", ".join(ann.get("benefit_sectors", []))}<br>
                              📌 <b>小盘标的</b>：{", ".join(ann.get("small_cap_stocks", []))}<br>
                              ⚠️ <b>风险提示</b>：{ann.get("risk_note", "")}
                            </div>
                            '''
                            new_lines.append(block)
    return '\n'.join(new_lines)