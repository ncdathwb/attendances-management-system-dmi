import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


def print_header():
    line = "=" * 70
    print(line)
    print("TRỢ LÝ AI - CẤU HÌNH OLLAMA CHATBOT".center(70))
    print(line)
    print()


def try_extend_path_with_common_ollama_locations() -> None:
    """
    Thêm một số đường dẫn cài đặt Ollama phổ biến vào PATH (chỉ trong process này)
    để thử tìm lệnh ollama nếu PATH chưa cập nhật.
    """
    possible_dirs = [
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama",
        Path("C:/Program Files/Ollama"),
        Path("C:/Program Files (x86)/Ollama"),
    ]
    for d in possible_dirs:
        if d.exists():
            os.environ["PATH"] = f"{d};{os.environ['PATH']}"


def check_ollama_installed() -> bool:
    """Kiểm tra xem lệnh 'ollama' có sẵn trong PATH hay không (sau khi đã thử nối PATH)."""
    try_extend_path_with_common_ollama_locations()
    return shutil.which("ollama") is not None


def run_command(cmd, cwd=None) -> int:
    """Chạy lệnh hệ thống đơn giản, in log ra màn hình."""
    print(f"\n> Đang chạy lệnh: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd)
        print(f"> Hoàn thành (mã thoát = {result.returncode})")
        return result.returncode
    except FileNotFoundError:
        print("> LỖI: Không tìm thấy lệnh:", cmd[0])
        return 1
    except Exception as e:
        print("> LỖI:", e)
        return 1


def ensure_deepseek_model():
    """
    Gọi 'ollama pull qwen2.5:7b' để chắc chắn model có sẵn.
    Nếu model đã tồn tại thì lệnh này chỉ kiểm tra rất nhanh.
    """
    print("\n--- BƯỚC 2: Kéo (pull) model qwen2.5:7b cho Ollama ---")
    cmd = ["ollama", "pull", "qwen2.5:7b"]
    code = run_command(cmd)
    if code != 0:
        print(
            "\n❌ Không thể pull model 'qwen2.5:7b'. "
            "Vui lòng kiểm tra lại Ollama hoặc kết nối mạng."
        )
        sys.exit(1)
    print("✅ Model qwen2.5:7b đã sẵn sàng cho chatbot.")


def run_app_with_ollama():
    """
    Thiết lập biến môi trường cho chatbot dùng Ollama + deepseek-r1,
    sau đó chạy app.py bằng cùng Python interpreter hiện tại.
    """
    print("\n--- BƯỚC 3: Chạy app.py với cấu hình OLLAMA ---")

    # Thiết lập biến môi trường cho process con
    env = os.environ.copy()
    env["CHATBOT_PROVIDER"] = "ollama"
    # Co the thay doi model o day
    env["OLLAMA_MODEL"] = "qwen2.5:7b"

    cmd = [sys.executable, "app.py"]
    print(
        "\n> Đang khởi động ứng dụng Flask (app.py) với cấu hình:\n"
        f"  - CHATBOT_PROVIDER = {env['CHATBOT_PROVIDER']}\n"
        f"  - OLLAMA_MODEL     = {env['OLLAMA_MODEL']}\n"
    )
    print("💡 Sau khi app chạy, hãy mở trình duyệt vào Dashboard và dùng chatbot AI.")
    print()
    # Chạy app.py, không bắt output để bạn thấy log trực tiếp
    os.execve(sys.executable, cmd, env)


def is_ollama_responding(url: str = "http://localhost:11434/api/tags", timeout: int = 3) -> bool:
    if requests is None:
        return False
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def ensure_ollama_running():
    """
    Kiểm tra Ollama đã chạy chưa; nếu chưa thì cố gắng khởi động 'ollama serve'
    trong nền và đợi sẵn sàng (tối đa 20 giây).
    """
    print("\n--- BƯỚC 1B: Đảm bảo dịch vụ Ollama đang chạy ---")
    if is_ollama_responding():
        print("✅ Ollama đã sẵn sàng (HTTP 11434).")
        return

    print("⚠️  Chưa thấy Ollama chạy. Đang cố gắng khởi động 'ollama serve' trong nền...")
    creation_flags = 0
    if os.name == "nt":
        try:
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        except Exception:
            creation_flags = 0

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
    except Exception as e:
        print(f"❌ Không thể khởi động 'ollama serve': {e}")
        print("Vui lòng mở cửa sổ PowerShell khác và chạy: ollama serve")
        sys.exit(1)

    # Chờ dịch vụ lên
    for i in range(20):
        time.sleep(1)
        if is_ollama_responding():
            print(f"✅ Ollama đã sẵn sàng sau {i+1} giây.")
            return
        else:
            print(f"... chờ Ollama sẵn sàng ({i+1}s)")

    print("❌ Ollama vẫn chưa sẵn sàng. Hãy tự chạy 'ollama serve' rồi thử lại.")
    sys.exit(1)


def main():
    print_header()

    print("--- BƯỚC 1: Kiểm tra Ollama đã cài đặt chưa ---")
    if not check_ollama_installed():
        print("\n⚠️  Không tìm thấy lệnh 'ollama' trong PATH. Đang thử cài tự động qua winget...")
        # Thử cài qua winget (cần Windows 10/11 và winget sẵn trong máy)
        code = run_command(["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent"])
        if code != 0:
            print(
                "\n❌ Không thể cài Ollama tự động qua winget.\n"
                "Vui lòng tự cài thủ công:\n"
                "  1) Tải và cài: https://ollama.com/download\n"
                "  2) Đóng và mở lại PowerShell / CMD\n"
                "  3) Chạy lại: python run_ollama_chatbot.py\n"
            )
            sys.exit(1)

        # Sau khi cài, thử lại tìm lệnh
        if not check_ollama_installed():
            print(
                "\n❌ Đã thử cài nhưng vẫn chưa tìm thấy lệnh 'ollama'.\n"
                "Hãy kiểm tra PATH hoặc mở cửa sổ PowerShell mới rồi chạy lại:\n"
                "   python run_ollama_chatbot.py\n"
            )
            sys.exit(1)

    print("✅ Đã tìm thấy lệnh 'ollama'.")
    ensure_ollama_running()

    ensure_deepseek_model()
    run_app_with_ollama()


if __name__ == "__main__":
    main()


