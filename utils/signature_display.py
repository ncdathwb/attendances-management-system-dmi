"""
Signature Display Utilities
签名显示工具类
"""
import base64
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional, Dict, Any
import logging
from utils.signature_processor import signature_processor

logger = logging.getLogger(__name__)

class SignatureDisplay:
    """签名显示管理器"""
    
    def __init__(self):
        self.default_display_size = (300, 120)  # 默认显示尺寸
        self.pdf_signature_size = (200, 80)     # PDF中的签名尺寸
        self.preview_size = (150, 60)           # 预览尺寸
        self.thumbnail_size = (100, 40)         # 缩略图尺寸
    
    def get_signature_for_display(self, signature_data: str, 
                                display_type: str = 'default',
                                custom_size: Optional[Tuple[int, int]] = None) -> str:
        """
        获取用于显示的签名图像
        
        Args:
            signature_data: Base64编码的签名数据
            display_type: 显示类型 ('default', 'pdf', 'preview', 'thumbnail')
            custom_size: 自定义尺寸 (width, height)
            
        Returns:
            处理后的Base64编码签名图像
        """
        try:
            if not signature_data:
                return self._create_empty_signature_placeholder()
            
            # 根据显示类型确定尺寸
            if custom_size:
                target_size = custom_size
            elif display_type == 'pdf':
                target_size = self.pdf_signature_size
            elif display_type == 'preview':
                target_size = self.preview_size
            elif display_type == 'thumbnail':
                target_size = self.thumbnail_size
            else:
                target_size = self.default_display_size
            
            # 处理签名
            processed_signature = signature_processor.process_signature(
                signature_data, 
                target_size=target_size,
                enhance_quality=True
            )
            
            return processed_signature
            
        except Exception as e:
            logger.error(f"Error getting signature for display: {e}")
            return self._create_empty_signature_placeholder()
    
    def create_signature_with_background(self, signature_data: str, 
                                       background_color: str = '#ffffff',
                                       border_color: str = '#dee2e6',
                                       border_width: int = 1,
                                       padding: int = 10) -> str:
        """
        创建带背景和边框的签名图像
        
        Args:
            signature_data: Base64编码的签名数据
            background_color: 背景颜色
            border_color: 边框颜色
            border_width: 边框宽度
            padding: 内边距
            
        Returns:
            带背景的签名图像
        """
        try:
            if not signature_data:
                return self._create_empty_signature_placeholder()
            
            # 处理签名
            processed_signature = signature_processor.process_signature(signature_data)
            
            # 解码签名图像
            image_data = self._decode_base64_image(processed_signature)
            if image_data is None:
                return processed_signature
            
            # 创建PIL图像
            signature_image = Image.open(io.BytesIO(image_data))
            sig_width, sig_height = signature_image.size
            
            # 计算背景尺寸
            bg_width = sig_width + 2 * padding + 2 * border_width
            bg_height = sig_height + 2 * padding + 2 * border_width
            
            # 创建背景图像
            background = Image.new('RGB', (bg_width, bg_height), background_color)
            
            # 绘制边框
            if border_width > 0:
                draw = ImageDraw.Draw(background)
                draw.rectangle([0, 0, bg_width-1, bg_height-1], 
                             outline=border_color, width=border_width)
            
            # 粘贴签名图像
            paste_x = padding + border_width
            paste_y = padding + border_width
            background.paste(signature_image, (paste_x, paste_y))
            
            # 转换为Base64
            return self._encode_image_to_base64(background)
            
        except Exception as e:
            logger.error(f"Error creating signature with background: {e}")
            return signature_data
    
    def create_signature_watermark(self, signature_data: str, 
                                 opacity: float = 0.3,
                                 size: Tuple[int, int] = (100, 40)) -> str:
        """
        创建签名水印
        
        Args:
            signature_data: Base64编码的签名数据
            opacity: 透明度 (0.0 - 1.0)
            size: 水印尺寸
            
        Returns:
            水印签名图像
        """
        try:
            if not signature_data:
                return ""
            
            # 处理签名
            processed_signature = signature_processor.process_signature(
                signature_data, 
                target_size=size
            )
            
            # 解码签名图像
            image_data = self._decode_base64_image(processed_signature)
            if image_data is None:
                return ""
            
            # 创建PIL图像
            signature_image = Image.open(io.BytesIO(image_data))
            
            # 转换为RGBA模式
            if signature_image.mode != 'RGBA':
                signature_image = signature_image.convert('RGBA')
            
            # 调整透明度
            alpha = signature_image.split()[3]
            alpha = alpha.point(lambda x: int(x * opacity))
            signature_image.putalpha(alpha)
            
            # 转换为Base64
            return self._encode_image_to_base64(signature_image)
            
        except Exception as e:
            logger.error(f"Error creating signature watermark: {e}")
            return ""
    
    def create_signature_comparison(self, original_signature: str, 
                                  processed_signature: str,
                                  comparison_size: Tuple[int, int] = (400, 200)) -> str:
        """
        创建签名对比图像
        
        Args:
            original_signature: 原始签名
            processed_signature: 处理后的签名
            comparison_size: 对比图像尺寸
            
        Returns:
            对比图像
        """
        try:
            # 处理两个签名
            original_processed = signature_processor.process_signature(
                original_signature, 
                target_size=(comparison_size[0]//2 - 10, comparison_size[1] - 20)
            )
            processed_processed = signature_processor.process_signature(
                processed_signature, 
                target_size=(comparison_size[0]//2 - 10, comparison_size[1] - 20)
            )
            
            # 解码图像
            original_data = self._decode_base64_image(original_processed)
            processed_data = self._decode_base64_image(processed_processed)
            
            if original_data is None or processed_data is None:
                return ""
            
            # 创建PIL图像
            original_img = Image.open(io.BytesIO(original_data))
            processed_img = Image.open(io.BytesIO(processed_data))
            
            # 创建对比图像
            comparison_img = Image.new('RGB', comparison_size, '#ffffff')
            
            # 粘贴原始签名
            comparison_img.paste(original_img, (10, 10))
            
            # 粘贴处理后的签名
            comparison_img.paste(processed_img, (comparison_size[0]//2 + 10, 10))
            
            # 添加标签
            draw = ImageDraw.Draw(comparison_img)
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                # 使用默认字体
                font = ImageFont.load_default()
            
            draw.text((10, comparison_size[1] - 25), "Trước khi tối ưu", fill='#000000', font=font)
            draw.text((comparison_size[0]//2 + 10, comparison_size[1] - 25), "Sau khi tối ưu", fill='#000000', font=font)
            
            # 转换为Base64
            return self._encode_image_to_base64(comparison_img)
            
        except Exception as e:
            logger.error(f"Error creating signature comparison: {e}")
            return ""
    
    def _decode_base64_image(self, base64_data: str) -> Optional[bytes]:
        """解码Base64图像数据"""
        try:
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
    
    def _create_empty_signature_placeholder(self) -> str:
        """创建空签名占位符"""
        try:
            # 创建空白图像
            img = Image.new('RGB', (200, 80), '#f8f9fa')
            draw = ImageDraw.Draw(img)
            
            # 绘制虚线边框
            draw.rectangle([0, 0, 199, 79], outline='#dee2e6', width=1)
            
            # 添加文字
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
            
            draw.text((50, 30), "Chưa có chữ ký", fill='#6c757d', font=font)
            
            return self._encode_image_to_base64(img)
            
        except Exception as e:
            logger.error(f"Error creating empty signature placeholder: {e}")
            return ""

# 全局实例
signature_display = SignatureDisplay()
