"""Unsplash图片服务。

Unsplash 是一个免费的高质量图片网站,提供公开 API 可以按关键词搜索图片。
这个文件封装了它的搜索能力,用来给景点配图(当高德地图拿不到景点图片时做补充)。

注意:Unsplash 需要单独申请 API Key(见 .env.example 里的 UNSPLASH_ACCESS_KEY),
本项目当前主要用高德地图取图,Unsplash 属于可选的补充方案。
"""

import requests
from typing import List, Optional
from ..config import get_settings

class UnsplashService:
    """Unsplash图片服务类。"""

    def __init__(self):
        """初始化服务:读取访问密钥和接口地址。"""
        settings = get_settings()
        self.access_key = settings.unsplash_access_key
        self.base_url = "https://api.unsplash.com"

    def search_photos(self, query: str, per_page: int = 5) -> List[dict]:
        """
        搜索图片

        Args:
            query: 搜索关键词(如景点名称)
            per_page: 每页返回多少张

        Returns:
            图片列表(每个元素是一个 dict,包含 id/url/thumb/描述/摄影师等)
        """
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": self.access_key  # Unsplash 用 client_id 作为访问凭证
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # 把接口返回的原始数据,提取成我们需要的精简结构
            photos = []
            for photo in results:
                photos.append({
                    "id": photo.get("id"),
                    "url": photo.get("urls", {}).get("regular"),   # 常规尺寸
                    "thumb": photo.get("urls", {}).get("thumb"),   # 缩略图
                    "description": photo.get("description") or photo.get("alt_description"),
                    "photographer": photo.get("user", {}).get("name")  # 摄影师(用于署名)
                })

            return photos

        except Exception as e:
            print(f"❌ Unsplash搜索失败: {str(e)}")
            return []

    def get_photo_url(self, query: str) -> Optional[str]:
        """
        获取单张图片URL。

        Args:
            query: 搜索关键词

        Returns:
            图片URL(找不到返回 None)
        """
        photos = self.search_photos(query, per_page=1)  # 只要第一张
        if photos:
            return photos[0].get("url")
        return None


# 全局服务实例(单例)
_unsplash_service = None


def get_unsplash_service() -> UnsplashService:
    """获取Unsplash服务实例(单例模式)。"""
    global _unsplash_service

    if _unsplash_service is None:
        _unsplash_service = UnsplashService()

    return _unsplash_service
