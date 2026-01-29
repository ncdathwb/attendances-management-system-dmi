"""
Signature Fit Adapter - Tự động điều chỉnh chữ ký vừa khít với ô ký
"""
import base64
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional, Dict, Any
import logging
from utils.signature_processor import signature_processor

logger = logging.getLogger(__name__)

class SignatureFitAdapter:
    """Bộ điều chỉnh chữ ký tự động vừa khít với ô ký"""
    
    def __init__(self):
        # Kích thước chuẩn cho các loại ô ký khác nhau
        # Tăng nhẹ kích thước để chữ ký hiển thị RÕ và ĐỦ LỚN trong PDF,
        # nhưng vẫn đảm bảo không bị tràn ra ngoài ô.
        self.signature_box_sizes = {
            'manager': (155, 80),        # Ô Quản lý (PDF size, khớp với phiếu tăng ca)
            'supervisor': (155, 80),     # Ô Cấp trên trực tiếp (PDF size)
            'applicant': (155, 80),      # Ô Người xin phép (PDF size)
            'team_leader': (110, 40),    # Ô Trưởng nhóm
            'employee': (110, 40),       # Ô Nhân viên
            'default': (110, 40)         # Ô mặc định
        }
        
        # Tỷ lệ padding bên trong ô (để chữ ký không sát viền)
        # Giảm padding để chữ ký lớn hơn, fill tốt hơn (từ 1% xuống 0.5%)
        self.padding_ratio = 0.005  # 0.5% padding để chữ ký fill tốt hơn
        # Tỷ lệ fill mục tiêu: chữ ký sẽ chiếm 85-95% kích thước ô
        self.fill_ratio = 0.90  # 90% fill để đảm bảo chữ ký lớn nhưng không tràn
        
        # Màu sắc cho các loại ô khác nhau
        self.box_colors = {
            'manager': '#e3f2fd',        # Xanh nhạt cho quản lý
            'supervisor': '#f3e5f5',     # Tím nhạt cho cấp trên
            'applicant': '#e8f5e8',      # Xanh lá nhạt cho người xin
            'team_leader': '#fff3e0',    # Cam nhạt cho trưởng nhóm
            'employee': '#fce4ec',       # Hồng nhạt cho nhân viên
            'default': '#f5f5f5'         # Xám nhạt mặc định
        }
    
    def fit_signature_to_box(self, signature_data: str, 
                           box_type: str = 'default',
                           custom_size: Optional[Tuple[int, int]] = None,
                           add_background: bool = True) -> str:
        """
        Điều chỉnh chữ ký vừa khít với ô ký
        
        Args:
            signature_data: Dữ liệu chữ ký Base64
            box_type: Loại ô ký ('manager', 'supervisor', 'applicant', etc.)
            custom_size: Kích thước tùy chỉnh (width, height)
            add_background: Có thêm nền cho ô ký không
            
        Returns:
            Chữ ký đã được điều chỉnh vừa khít với ô
        """
        try:
            if not signature_data:
                return self._create_empty_signature_box(box_type, custom_size)
            
            # Xác định kích thước ô
            if custom_size:
                box_size = custom_size
            else:
                box_size = self.signature_box_sizes.get(box_type, self.signature_box_sizes['default'])
            
            # Tính toán kích thước thực tế cho chữ ký với fill ratio để đảm bảo lớn và phù hợp
            # Sử dụng fill_ratio để chữ ký chiếm 90% kích thước ô
            signature_size = (
                int(box_size[0] * self.fill_ratio),
                int(box_size[1] * self.fill_ratio)
            )
            
            # Đảm bảo kích thước tối thiểu hợp lý
            min_size = min(box_size[0], box_size[1])
            if signature_size[0] < min_size * 0.5 or signature_size[1] < min_size * 0.5:
                # Nếu quá nhỏ, scale lên ít nhất 50% kích thước ô
                scale_factor = max(
                    (min_size * 0.5) / signature_size[0],
                    (min_size * 0.5) / signature_size[1]
                )
                signature_size = (
                    int(signature_size[0] * scale_factor),
                    int(signature_size[1] * scale_factor)
                )
                # Đảm bảo không vượt quá fill ratio
                if signature_size[0] > box_size[0] * self.fill_ratio:
                    signature_size = (int(box_size[0] * self.fill_ratio), signature_size[1])
                if signature_size[1] > box_size[1] * self.fill_ratio:
                    signature_size = (signature_size[0], int(box_size[1] * self.fill_ratio))
            
            # Xử lý chữ ký với kích thước mục tiêu
            processed_signature = signature_processor.process_signature(
                signature_data,
                target_size=signature_size,
                enhance_quality=True
            )
            
            if add_background:
                return self._create_signature_with_box(
                    processed_signature, 
                    box_type, 
                    box_size, 
                    0  # Không cần padding vì đã tính trong signature_size
                )
            else:
                return processed_signature
                
        except Exception as e:
            logger.error(f"Error fitting signature to box: {e}")
            return self._create_empty_signature_box(box_type, custom_size)
    
    def _create_signature_with_box(self, signature_data: str, 
                                 box_type: str, 
                                 box_size: Tuple[int, int],
                                 padding: int) -> str:
        """Tạo chữ ký với nền ô ký"""
        try:
            # Nền trắng, KHÔNG vẽ viền để tránh ô vuông màu
            background_color = '#ffffff'
            box_image = Image.new('RGB', box_size, background_color)
            
            # Giải mã chữ ký đã xử lý
            image_data = self._decode_base64_image(signature_data)
            if image_data:
                signature_image = Image.open(io.BytesIO(image_data))
                
                # Tính toán vị trí đặt chữ ký (căn giữa)
                sig_width, sig_height = signature_image.size
                x = (box_size[0] - sig_width) // 2
                y = (box_size[1] - sig_height) // 2
                
                # Đặt chữ ký vào ô
                box_image.paste(signature_image, (x, y))
            
            return self._encode_image_to_base64(box_image)
            
        except Exception as e:
            logger.error(f"Error creating signature with box: {e}")
            return signature_data
    
    def _create_empty_signature_box(self, box_type: str, 
                                  custom_size: Optional[Tuple[int, int]] = None) -> str:
        """Tạo ô ký trống"""
        try:
            # Xác định kích thước
            if custom_size:
                box_size = custom_size
            else:
                box_size = self.signature_box_sizes.get(box_type, self.signature_box_sizes['default'])
            
            # Tạo ảnh nền
            background_color = self.box_colors.get(box_type, self.box_colors['default'])
            box_image = Image.new('RGB', box_size, background_color)
            
            # Vẽ viền
            draw = ImageDraw.Draw(box_image)
            draw.rectangle([0, 0, box_size[0]-1, box_size[1]-1], 
                         outline='#000000', width=1)
            
            # Thêm đường kẻ ngang để ký
            line_y = box_size[1] // 2
            draw.line([(10, line_y), (box_size[0]-10, line_y)], 
                     fill='#666666', width=1)
            
            # Thêm chữ "Ký tên"
            try:
                font = ImageFont.truetype("arial.ttf", 10)
            except:
                font = ImageFont.load_default()
            
            text = "Ký tên"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (box_size[0] - text_width) // 2
            text_y = line_y + 5
            
            draw.text((text_x, text_y), text, fill='#666666', font=font)
            
            return self._encode_image_to_base64(box_image)
            
        except Exception as e:
            logger.error(f"Error creating empty signature box: {e}")
            return ""
    
    def create_form_signatures(self, signatures: Dict[str, str]) -> Dict[str, str]:
        """
        Tạo chữ ký cho toàn bộ biểu mẫu
        
        Args:
            signatures: Dict chứa các chữ ký theo loại
                       {'manager': signature_data, 'supervisor': signature_data, 'applicant': signature_data}
        
        Returns:
            Dict chứa các chữ ký đã được điều chỉnh
        """
        try:
            result = {}
            
            for box_type, signature_data in signatures.items():
                if signature_data:
                    fitted_signature = self.fit_signature_to_box(
                        signature_data, 
                        box_type=box_type,
                        add_background=True
                    )
                    result[box_type] = fitted_signature
                else:
                    # Tạo ô trống nếu không có chữ ký
                    empty_box = self._create_empty_signature_box(box_type)
                    result[box_type] = empty_box
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating form signatures: {e}")
            return {}
    
    def get_box_size(self, box_type: str) -> Tuple[int, int]:
        """Lấy kích thước chuẩn cho loại ô ký"""
        return self.signature_box_sizes.get(box_type, self.signature_box_sizes['default'])
    
    def set_custom_box_size(self, box_type: str, size: Tuple[int, int]) -> None:
        """Thiết lập kích thước tùy chỉnh cho loại ô ký"""
        self.signature_box_sizes[box_type] = size
    
    def validate_signature_fit(self, signature_data: str, 
                             box_type: str = 'default') -> Dict[str, Any]:
        """
        Kiểm tra xem chữ ký có vừa khít với ô không - KIỂM TRA CHỮ KÝ ĐÃ ĐIỀU CHỈNH
        
        Returns:
            Dict chứa thông tin kiểm tra
        """
        try:
            if not signature_data:
                return {
                    'fits': False,
                    'error': 'Không có dữ liệu chữ ký',
                    'recommendation': 'Vui lòng tạo chữ ký trước'
                }
            
            # Lấy kích thước ô
            box_size = self.get_box_size(box_type)
            padding = int(min(box_size) * self.padding_ratio)
            available_size = (
                box_size[0] - 2 * padding,
                box_size[1] - 2 * padding
            )
            
            # Điều chỉnh chữ ký trước khi kiểm tra
            fitted_signature = self.fit_signature_to_box(signature_data, box_type, add_background=False)
            
            # Giải mã chữ ký đã điều chỉnh để kiểm tra kích thước
            image_data = self._decode_base64_image(fitted_signature)
            if not image_data:
                return {
                    'fits': False,
                    'error': 'Không thể giải mã chữ ký đã điều chỉnh',
                    'recommendation': 'Kiểm tra lại định dạng chữ ký'
                }
            
            signature_image = Image.open(io.BytesIO(image_data))
            sig_width, sig_height = signature_image.size
            
            # Kiểm tra xem có vừa không
            width_fits = sig_width <= available_size[0]
            height_fits = sig_height <= available_size[1]
            
            if width_fits and height_fits:
                return {
                    'fits': True,
                    'signature_size': (sig_width, sig_height),
                    'box_size': box_size,
                    'available_size': available_size,
                    'message': 'Chữ ký vừa khít với ô'
                }
            else:
                recommendations = []
                if not width_fits:
                    recommendations.append(f"Chữ ký quá rộng ({sig_width}px > {available_size[0]}px)")
                if not height_fits:
                    recommendations.append(f"Chữ ký quá cao ({sig_height}px > {available_size[1]}px)")
                
                return {
                    'fits': False,
                    'signature_size': (sig_width, sig_height),
                    'box_size': box_size,
                    'available_size': available_size,
                    'recommendations': recommendations,
                    'message': 'Chữ ký cần được điều chỉnh kích thước'
                }
                
        except Exception as e:
            logger.error(f"Error validating signature fit: {e}")
            return {
                'fits': False,
                'error': f'Lỗi kiểm tra: {str(e)}',
                'recommendation': 'Thử lại sau'
            }
    
    def _decode_base64_image(self, base64_data: str) -> Optional[bytes]:
        """Giải mã dữ liệu Base64"""
        try:
            if base64_data.startswith('data:image'):
                base64_data = base64_data.split(',')[1]
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            return None
    
    def _encode_image_to_base64(self, pil_image: Image.Image) -> str:
        """Mã hóa ảnh thành Base64"""
        try:
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG', optimize=True)
            buffer.seek(0)
            image_data = buffer.getvalue()
            return f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}"
        except Exception as e:
            logger.error(f"Error encoding image to base64: {e}")
            return ""

# Global instance
signature_fit_adapter = SignatureFitAdapter()
