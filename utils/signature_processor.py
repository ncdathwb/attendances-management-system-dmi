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
        处理签名图像，优化质量和尺寸 - CẢI THIỆN: Tự động điều chỉnh dựa trên kích thước thực tế
        
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
            original_size = pil_image.size
            
            # 提取签名区域 (loại bỏ khoảng trắng)
            signature_region = self._extract_signature_region(pil_image)
            if signature_region is None:
                signature_region = pil_image
            
            extracted_size = signature_region.size
            
            # 增强图像质量
            if enhance_quality:
                signature_region = self._enhance_image_quality(signature_region)
            
            # Xác định target_size thông minh
            # Nếu không có target_size, sử dụng kích thước tối ưu
            # Nhưng điều chỉnh dựa trên kích thước thực tế của chữ ký
            if target_size is None:
                # Sử dụng kích thước tối ưu làm base
                target_size = self.optimal_signature_size
                
                # Điều chỉnh dựa trên kích thước thực tế của chữ ký đã extract
                # Nếu chữ ký rất nhỏ, scale lên một chút
                # Nếu chữ ký rất lớn, scale xuống nhưng vẫn giữ tỷ lệ
                extracted_width, extracted_height = extracted_size
                optimal_width, optimal_height = self.optimal_signature_size
                
                # Tính tỷ lệ scale dựa trên kích thước extract
                # Đảm bảo chữ ký không quá nhỏ hoặc quá lớn
                if extracted_width < optimal_width * 0.3 or extracted_height < optimal_height * 0.3:
                    # Chữ ký rất nhỏ, scale lên
                    scale_factor = max(optimal_width / extracted_width, optimal_height / extracted_height)
                    scale_factor = min(scale_factor, 3.0)  # Giới hạn scale tối đa 3x
                    target_size = (
                        int(extracted_width * scale_factor),
                        int(extracted_height * scale_factor)
                    )
                    # Đảm bảo không vượt quá max size
                    target_size = (
                        min(target_size[0], self.max_signature_size[0]),
                        min(target_size[1], self.max_signature_size[1])
                    )
                elif extracted_width > optimal_width * 2 or extracted_height > optimal_height * 2:
                    # Chữ ký rất lớn, scale xuống
                    scale_factor = min(optimal_width / extracted_width, optimal_height / extracted_height)
                    target_size = (
                        int(extracted_width * scale_factor),
                        int(extracted_height * scale_factor)
                    )
            
            # 调整尺寸 với target_size đã được điều chỉnh
            resized_image = self._resize_signature(signature_region, target_size)
            
            # 转换为Base64
            return self._encode_image_to_base64(resized_image)
            
        except Exception as e:
            logger.error(f"Error processing signature: {e}")
            return signature_data
    
    def _decode_base64_image(self, base64_data: str) -> Optional[bytes]:
        """解码Base64图像数据 với validation file type"""
        try:
            # Validate data URL format trước khi decode
            allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']

            if base64_data.startswith('data:'):
                # Extract và validate MIME type
                header_end = base64_data.find(',')
                if header_end == -1:
                    logger.warning("Invalid data URL format: missing comma separator")
                    return None

                header = base64_data[:header_end].lower()
                # Extract MIME type from "data:image/png;base64"
                mime_start = header.find(':') + 1
                mime_end = header.find(';') if ';' in header else len(header)
                mime_type = header[mime_start:mime_end]

                if mime_type not in allowed_types:
                    logger.warning(f"Invalid image type: {mime_type}. Allowed: {allowed_types}")
                    return None

                base64_data = base64_data.split(',')[1]

            # Decode base64
            decoded = base64.b64decode(base64_data)

            # Validate it's actually an image by checking magic bytes
            if len(decoded) < 8:
                logger.warning("Decoded data too small to be a valid image")
                return None

            # Check PNG magic bytes
            if decoded[:8] == b'\x89PNG\r\n\x1a\n':
                return decoded
            # Check JPEG magic bytes
            if decoded[:2] == b'\xff\xd8':
                return decoded
            # Check GIF magic bytes
            if decoded[:6] in (b'GIF87a', b'GIF89a'):
                return decoded
            # Check WebP magic bytes
            if decoded[:4] == b'RIFF' and decoded[8:12] == b'WEBP':
                return decoded

            logger.warning("Decoded data does not match known image magic bytes")
            return None

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
        """提取签名区域，去除空白背景 - CẢI THIỆN: Tự động phát hiện và loại bỏ khoảng trắng tốt hơn"""
        try:
            # Chuyển sang RGBA nếu chưa phải
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
            
            # Chuyển đổi sang numpy array để xử lý
            img_array = np.array(pil_image)
            
            # Tạo mask để tìm vùng có nội dung (không phải nền trắng hoặc trong suốt)
            # Xử lý cả ảnh có nền trắng và ảnh có nền trong suốt
            if img_array.shape[2] == 4:  # RGBA
                # Tìm pixel có alpha > 0 và không phải màu trắng
                alpha_channel = img_array[:, :, 3]
                rgb_channels = img_array[:, :, :3]
                
                # Tạo mask: pixel có alpha > threshold và không phải màu trắng
                non_white_mask = np.any(rgb_channels < self.background_threshold, axis=2)
                has_content_mask = (alpha_channel > 10) & non_white_mask
            else:  # RGB
                # Tìm pixel không phải màu trắng
                has_content_mask = np.any(img_array < self.background_threshold, axis=2)
            
            if not np.any(has_content_mask):
                # Không tìm thấy nội dung, trả về ảnh gốc
                return pil_image
            
            # Tìm bounding box của vùng có nội dung
            rows = np.any(has_content_mask, axis=1)
            cols = np.any(has_content_mask, axis=0)
            
            if not np.any(rows) or not np.any(cols):
                return pil_image
            
            top_row = np.argmax(rows)
            bottom_row = len(rows) - np.argmax(rows[::-1])
            left_col = np.argmax(cols)
            right_col = len(cols) - np.argmax(cols[::-1])
            
            # Thêm margin để không cắt sát chữ ký
            # Margin tỷ lệ với kích thước chữ ký
            width = right_col - left_col
            height = bottom_row - top_row
            margin_ratio = 0.05  # 5% margin
            margin_x = max(10, int(width * margin_ratio))
            margin_y = max(10, int(height * margin_ratio))
            
            x = max(0, left_col - margin_x)
            y = max(0, top_row - margin_y)
            w = min(pil_image.width - x, right_col - left_col + 2 * margin_x)
            h = min(pil_image.height - y, bottom_row - top_row + 2 * margin_y)
            
            # Cắt vùng chữ ký
            signature_region = pil_image.crop((x, y, x + w, y + h))
            
            return signature_region
            
        except Exception as e:
            logger.error(f"Error extracting signature region: {e}")
            # Fallback: thử dùng OpenCV nếu có lỗi
            try:
                cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, self.background_threshold, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    margin = 10
                    x = max(0, x - margin)
                    y = max(0, y - margin)
                    w = min(cv_image.shape[1] - x, w + 2 * margin)
                    h = min(cv_image.shape[0] - y, h + 2 * margin)
                    return pil_image.crop((x, y, x + w, y + h))
            except:
                pass
            
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
        """调整签名尺寸，保持宽高比 - CẢI THIỆN: Tự động điều chỉnh để vừa khít với ô và fill tốt"""
        try:
            current_width, current_height = pil_image.size
            target_width, target_height = target_size
            
            # Tỷ lệ fill tối thiểu: đảm bảo chữ ký chiếm ít nhất 80% kích thước mục tiêu
            min_fill_ratio = 0.80
            
            current_ratio = current_width / current_height
            target_ratio = target_width / target_height
            
            # Tính toán kích thước mới giữ nguyên tỷ lệ và vừa khít với ô
            if current_ratio > target_ratio:
                # Ảnh rộng hơn (tỷ lệ rộng hơn ô) -> scale theo chiều rộng để fill đầy
                new_width = target_width
                new_height = int(target_width / current_ratio)
            else:
                # Ảnh cao hơn (tỷ lệ cao hơn ô) -> scale theo chiều cao để fill đầy
                new_height = target_height
                new_width = int(target_height * current_ratio)
            
            # Đảm bảo không vượt quá kích thước mục tiêu
            if new_width > target_width:
                scale = target_width / new_width
                new_width = target_width
                new_height = int(new_height * scale)
            
            if new_height > target_height:
                scale = target_height / new_height
                new_height = target_height
                new_width = int(new_width * scale)
            
            # Kiểm tra và đảm bảo fill tối thiểu: nếu quá nhỏ, scale lên để đạt min_fill_ratio
            width_fill_ratio = new_width / target_width
            height_fill_ratio = new_height / target_height
            min_actual_fill = min(width_fill_ratio, height_fill_ratio)
            
            if min_actual_fill < min_fill_ratio:
                # Scale lên để đạt min_fill_ratio
                scale_factor = min_fill_ratio / min_actual_fill
                new_width = int(new_width * scale_factor)
                new_height = int(new_height * scale_factor)
                
                # Đảm bảo không vượt quá target sau khi scale
                if new_width > target_width:
                    scale = target_width / new_width
                    new_width = target_width
                    new_height = int(new_height * scale)
                
                if new_height > target_height:
                    scale = target_height / new_height
                    new_height = target_height
                    new_width = int(new_width * scale)
            
            # Đảm bảo kích thước hợp lệ (ít nhất 1 pixel)
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            
            # Resize với LANCZOS để có chất lượng tốt nhất
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
