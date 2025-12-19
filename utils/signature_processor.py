"""
Signature Processing and Optimization System
处理签名图像优化、提取和标准化
"""
import base64
import io
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import logging
from typing import Tuple, Optional, Dict, Any
import re

logger = logging.getLogger(__name__)

class SignatureProcessor:
    """签名图像处理优化器"""
    
    def __init__(self):
        self.min_signature_size = (100, 50)  # 最小签名尺寸 (width, height)
        self.max_signature_size = (800, 300)  # 最大签名尺寸
        self.optimal_signature_size = (400, 150)  # 最优签名尺寸
        self.background_threshold = 240  # 背景色阈值
        self.contrast_factor = 1.5  # 对比度增强因子
        self.brightness_factor = 1.1  # 亮度增强因子
    
    def process_signature(self, signature_data: str, 
                         target_size: Optional[Tuple[int, int]] = None,
                         enhance_quality: bool = True) -> str:
        """
        处理签名图像，优化质量和尺寸
        
        Args:
            signature_data: Base64编码的签名图像数据
            target_size: 目标尺寸 (width, height)，None则使用最优尺寸
            enhance_quality: 是否增强图像质量
            
        Returns:
            处理后的Base64编码签名图像
        """
        try:
            if not signature_data:
                return ""
            
            # 解码Base64数据
            image_data = self._decode_base64_image(signature_data)
            if image_data is None:
                return signature_data
            
            # 转换为PIL图像
            pil_image = Image.open(io.BytesIO(image_data))
            
            # 提取签名区域
            signature_region = self._extract_signature_region(pil_image)
            if signature_region is None:
                return signature_data
            
            # 增强图像质量
            if enhance_quality:
                signature_region = self._enhance_image_quality(signature_region)
            
            # 调整尺寸
            target_size = target_size or self.optimal_signature_size
            resized_image = self._resize_signature(signature_region, target_size)
            
            # 转换为Base64
            return self._encode_image_to_base64(resized_image)
            
        except Exception as e:
            logger.error(f"Error processing signature: {e}")
            return signature_data
    
    def _decode_base64_image(self, base64_data: str) -> Optional[bytes]:
        """解码Base64图像数据"""
        try:
            # 移除data URL前缀
            if base64_data.startswith('data:image'):
                base64_data = base64_data.split(',')[1]
            
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            return None
    
    def _encode_image_to_base64(self, pil_image: Image.Image) -> str:
        """将PIL图像编码为Base64"""
        try:
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG', optimize=True)
            buffer.seek(0)
            image_data = buffer.getvalue()
            return f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}"
        except Exception as e:
            logger.error(f"Error encoding image to base64: {e}")
            return ""
    
    def _extract_signature_region(self, pil_image: Image.Image) -> Optional[Image.Image]:
        """提取签名区域，去除空白背景"""
        try:
            # 转换为OpenCV格式
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # 转换为灰度图
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 二值化处理
            _, binary = cv2.threshold(gray, self.background_threshold, 255, cv2.THRESH_BINARY_INV)
            
            # 查找轮廓
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return pil_image
            
            # 找到最大的轮廓（通常是签名）
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 获取边界框
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 添加边距
            margin = 10
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(cv_image.shape[1] - x, w + 2 * margin)
            h = min(cv_image.shape[0] - y, h + 2 * margin)
            
            # 裁剪签名区域
            signature_region = pil_image.crop((x, y, x + w, y + h))
            
            return signature_region
            
        except Exception as e:
            logger.error(f"Error extracting signature region: {e}")
            return pil_image
    
    def _enhance_image_quality(self, pil_image: Image.Image) -> Image.Image:
        """增强图像质量"""
        try:
            # 增强对比度
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(self.contrast_factor)
            
            # 增强亮度
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(self.brightness_factor)
            
            # 轻微锐化
            pil_image = pil_image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
            
            return pil_image
            
        except Exception as e:
            logger.error(f"Error enhancing image quality: {e}")
            return pil_image
    
    def _resize_signature(self, pil_image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """调整签名尺寸，保持宽高比 - ƯU TIÊN KÍCH THƯỚC MỤC TIÊU"""
        try:
            current_width, current_height = pil_image.size
            target_width, target_height = target_size
            
            # 计算宽高比
            current_ratio = current_width / current_height
            target_ratio = target_width / target_height
            
            # 根据宽高比调整尺寸 - ƯU TIÊN KÍCH THƯỚC MỤC TIÊU
            if current_ratio > target_ratio:
                # 宽度优先 - ưu tiên chiều rộng
                new_width = target_width
                new_height = int(target_width / current_ratio)
            else:
                # 高度优先 - ưu tiên chiều cao
                new_height = target_height
                new_width = int(target_height * current_ratio)
            
            # 确保尺寸在合理范围内 - ƯU TIÊN KÍCH THƯỚC MỤC TIÊU
            # Nếu kích thước tính toán vượt quá mục tiêu, thu nhỏ lại
            if new_width > target_width:
                scale_factor = target_width / new_width
                new_width = target_width
                new_height = int(new_height * scale_factor)
            
            if new_height > target_height:
                scale_factor = target_height / new_height
                new_height = target_height
                new_width = int(new_width * scale_factor)
            
            # Đảm bảo kích thước tối thiểu
            new_width = max(self.min_signature_size[0], new_width)
            new_height = max(self.min_signature_size[1], new_height)
            
            # 调整尺寸
            resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return resized_image
            
        except Exception as e:
            logger.error(f"Error resizing signature: {e}")
            return pil_image
    
    def validate_signature_quality(self, signature_data: str) -> Dict[str, Any]:
        """验证签名质量"""
        try:
            if not signature_data:
                return {
                    'valid': False,
                    'error': 'Không có dữ liệu chữ ký',
                    'score': 0
                }
            
            # 解码图像
            image_data = self._decode_base64_image(signature_data)
            if image_data is None:
                return {
                    'valid': False,
                    'error': 'Không thể giải mã dữ liệu chữ ký',
                    'score': 0
                }
            
            # 转换为PIL图像
            pil_image = Image.open(io.BytesIO(image_data))
            width, height = pil_image.size
            
            # 检查尺寸
            if width < self.min_signature_size[0] or height < self.min_signature_size[1]:
                return {
                    'valid': False,
                    'error': f'Chữ ký quá nhỏ (hiện tại: {width}x{height}, tối thiểu: {self.min_signature_size[0]}x{self.min_signature_size[1]})',
                    'score': 0
                }
            
            if width > self.max_signature_size[0] or height > self.max_signature_size[1]:
                return {
                    'valid': False,
                    'error': f'Chữ ký quá lớn (hiện tại: {width}x{height}, tối đa: {self.max_signature_size[0]}x{self.max_signature_size[1]})',
                    'score': 0
                }
            
            # 检查签名复杂度
            complexity_score = self._calculate_signature_complexity(pil_image)
            
            # 计算总体评分
            size_score = min(1.0, (width * height) / (self.optimal_signature_size[0] * self.optimal_signature_size[1]))
            total_score = (complexity_score + size_score) / 2
            
            return {
                'valid': True,
                'score': total_score,
                'size': (width, height),
                'complexity': complexity_score,
                'recommendations': self._get_quality_recommendations(total_score, width, height)
            }
            
        except Exception as e:
            logger.error(f"Error validating signature quality: {e}")
            return {
                'valid': False,
                'error': f'Lỗi kiểm tra chất lượng: {str(e)}',
                'score': 0
            }
    
    def _calculate_signature_complexity(self, pil_image: Image.Image) -> float:
        """计算签名复杂度"""
        try:
            # 转换为灰度图
            gray = pil_image.convert('L')
            gray_array = np.array(gray)
            
            # 计算边缘密度
            edges = cv2.Canny(gray_array, 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            
            # 计算颜色变化
            color_variance = np.var(gray_array)
            
            # 归一化评分
            complexity_score = min(1.0, (edge_density * 1000 + color_variance / 1000) / 2)
            
            return complexity_score
            
        except Exception as e:
            logger.error(f"Error calculating signature complexity: {e}")
            return 0.5
    
    def _get_quality_recommendations(self, score: float, width: int, height: int) -> list:
        """获取质量改进建议"""
        recommendations = []
        
        if score < 0.3:
            recommendations.append("Chữ ký quá đơn giản, hãy ký rõ ràng hơn")
        
        if width < self.optimal_signature_size[0] * 0.8:
            recommendations.append("Chữ ký hơi nhỏ, hãy ký lớn hơn một chút")
        
        if width > self.optimal_signature_size[0] * 1.2:
            recommendations.append("Chữ ký hơi lớn, hãy ký nhỏ hơn một chút")
        
        if score > 0.8:
            recommendations.append("Chữ ký có chất lượng tốt!")
        
        return recommendations
    
    def create_signature_preview(self, signature_data: str, 
                               preview_size: Tuple[int, int] = (200, 100)) -> str:
        """创建签名预览图像"""
        try:
            processed_signature = self.process_signature(
                signature_data, 
                target_size=preview_size,
                enhance_quality=True
            )
            return processed_signature
        except Exception as e:
            logger.error(f"Error creating signature preview: {e}")
            return signature_data

# 全局实例
signature_processor = SignatureProcessor()
