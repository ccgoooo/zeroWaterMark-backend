from PIL import Image
import io
import base64

def hex_to_32x32_binary_image(hex_string):
    if len(hex_string) != 64:
        raise ValueError("Hex string must be 64 characters long to represent 256 bits.")

        # 将16进制字符串转换为二进制字符串
    binary_string = bin(int(hex_string, 16))[2:].zfill(128)

    # 创建一个16x16的二值图像，初始为全白
    image = Image.new('1', (16, 16), 0)

    # 根据二进制字符串生成图像的像素
    for i in range(16):
        for j in range(16):
            # 计算二进制位的索引
            bit_index = i * 16 + j
            # 根据二进制位的值设置像素为黑色或白色
            pixel_value = 1 if binary_string[bit_index % 128] == '1' else 0
            image.putpixel((j, i), pixel_value)

    base64_string = image_to_base64(image)
    return base64_string


def image_to_base64(image):
    # 将图片保存到字节流中
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    # 将字节流编码为base64字符串
    base64_encoded = base64.b64encode(buffered.getvalue())
    # 将base64编码的bytes转换为utf-8格式的字符串
    base64_string = base64_encoded.decode('utf-8')
    final_string = "data:image/x-icon;base64,"+base64_string
    return final_string

