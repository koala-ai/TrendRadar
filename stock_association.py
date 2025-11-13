import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class StockAssociator:
    """股票关联器，用于将新闻标题与相关股票关联起来"""
    
    def __init__(self, config_path: str = None):
        """初始化股票关联器
        
        Args:
            config_path: 股票关键词映射配置文件路径
        """
        if config_path is None:
            config_path = os.environ.get(
                "STOCK_KEYWORDS_MAP_PATH", "config/stock_keywords_map.json"
            )
        
        self.config_path = Path(config_path)
        self.stock_mappings = []
        self.industry_mappings = []
        self._load_config()
    
    def _load_config(self) -> None:
        """加载股票关键词映射配置"""
        if not self.config_path.exists():
            print(f"警告: 股票关键词映射配置文件 {self.config_path} 不存在")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.stock_mappings = config.get("股票映射配置", [])
            self.industry_mappings = config.get("行业板块映射", [])
            
            print(f"已加载 {len(self.stock_mappings)} 个股票映射和 {len(self.industry_mappings)} 个行业板块映射")
        
        except Exception as e:
            print(f"加载股票关键词映射配置失败: {str(e)}")
    
    def find_related_stocks(self, title: str) -> List[Dict]:
        """根据新闻标题查找相关股票
        
        Args:
            title: 新闻标题
            
        Returns:
            相关股票列表，每个元素包含股票代码、股票名称和匹配的关键词
        """
        related_stocks = []
        title_lower = title.lower()
        
        for stock in self.stock_mappings:
            stock_name = stock["股票名称"]
            stock_code = stock["股票代码"]
            keywords = stock["关联关键词"]
            
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                related_stocks.append({
                    "股票代码": stock_code,
                    "股票名称": stock_name,
                    "匹配关键词": matched_keywords,
                    "匹配强度": len(matched_keywords)  # 匹配的关键词数量作为强度指标
                })
        
        # 按匹配强度降序排序
        related_stocks.sort(key=lambda x: x["匹配强度"], reverse=True)
        
        return related_stocks[:3]  # 返回前3个最相关的股票
    
    def find_related_industries(self, title: str) -> List[Dict]:
        """根据新闻标题查找相关行业板块
        
        Args:
            title: 新闻标题
            
        Returns:
            相关行业板块列表
        """
        related_industries = []
        title_lower = title.lower()
        
        for industry in self.industry_mappings:
            industry_name = industry["板块名称"]
            keywords = industry["关联关键词"]
            
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                related_industries.append({
                    "板块名称": industry_name,
                    "匹配关键词": matched_keywords,
                    "匹配强度": len(matched_keywords)
                })
        
        # 按匹配强度降序排序
        related_industries.sort(key=lambda x: x["匹配强度"], reverse=True)
        
        return related_industries[:2]  # 返回前2个最相关的行业板块
    
    def associate_title_with_stocks(self, title_data: Dict) -> Dict:
        """将股票信息关联到新闻标题数据中
        
        Args:
            title_data: 包含标题信息的字典
            
        Returns:
            更新后的标题数据，添加了相关股票和行业板块信息
        """
        title = title_data.get("title", "")
        if not title:
            return title_data
        
        # 查找相关股票
        related_stocks = self.find_related_stocks(title)
        # 查找相关行业板块
        related_industries = self.find_related_industries(title)
        
        # 添加到标题数据中
        updated_data = title_data.copy()
        updated_data["related_stocks"] = related_stocks
        updated_data["related_industries"] = related_industries
        
        return updated_data


# 全局股票关联器实例
_stock_associator = None


def get_stock_associator() -> StockAssociator:
    """获取全局股票关联器实例
    
    Returns:
        StockAssociator 实例
    """
    global _stock_associator
    if _stock_associator is None:
        _stock_associator = StockAssociator()
    return _stock_associator


def associate_news_with_stocks(news_data: Dict) -> Dict:
    """将股票信息关联到新闻数据中
    
    Args:
        news_data: 新闻数据字典
        
    Returns:
        更新后的新闻数据
    """
    associator = get_stock_associator()
    
    # 处理统计数据中的标题
    stats = news_data.get("stats", [])
    updated_stats = []
    
    for stat in stats:
        updated_titles = []
        for title_data in stat.get("titles", []):
            updated_title_data = associator.associate_title_with_stocks(title_data)
            updated_titles.append(updated_title_data)
        
        updated_stat = stat.copy()
        updated_stat["titles"] = updated_titles
        updated_stats.append(updated_stat)
    
    # 处理新增标题
    new_titles = news_data.get("new_titles", [])
    updated_new_titles = []
    
    for source_data in new_titles:
        updated_source_titles = []
        for title_data in source_data.get("titles", []):
            updated_title_data = associator.associate_title_with_stocks(title_data)
            updated_source_titles.append(updated_title_data)
        
        updated_source = source_data.copy()
        updated_source["titles"] = updated_source_titles
        updated_new_titles.append(updated_source)
    
    # 返回更新后的新闻数据
    updated_news_data = news_data.copy()
    updated_news_data["stats"] = updated_stats
    updated_news_data["new_titles"] = updated_new_titles
    
    return updated_news_data


def format_stock_info(related_stocks: List[Dict], platform: str = "feishu") -> str:
    """格式化股票信息为适合不同平台的显示格式
    
    Args:
        related_stocks: 相关股票列表
        platform: 平台类型 (feishu, dingtalk, wework, telegram, ntfy)
        
    Returns:
        格式化后的股票信息字符串
    """
    if not related_stocks:
        return ""
    
    stock_info_parts = []
    for stock in related_stocks:
        stock_name = stock["股票名称"]
        stock_code = stock["股票代码"]
        
        if platform == "feishu":
            stock_info_parts.append(f"<font color='blue'>[{stock_name}({stock_code})]</font>")
        elif platform in ["dingtalk", "wework"]:
            stock_info_parts.append(f"[{stock_name}({stock_code})]")
        elif platform == "telegram":
            stock_info_parts.append(f"<b>[{stock_name}({stock_code})]</b>")
        elif platform == "ntfy":
            stock_info_parts.append(f"[{stock_name}({stock_code})]")
        else:
            stock_info_parts.append(f"[{stock_name}({stock_code})]")
    
    if platform == "feishu":
        return f" <font color='grey'>相关股票:</font> {' '.join(stock_info_parts)}"
    elif platform in ["dingtalk", "wework", "ntfy"]:
        return f" 相关股票: {' '.join(stock_info_parts)}"
    elif platform == "telegram":
        return f" <b>相关股票:</b> {' '.join(stock_info_parts)}"
    else:
        return f" 相关股票: {' '.join(stock_info_parts)}"