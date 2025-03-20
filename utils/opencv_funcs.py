"""
@author: 54Coconi
@date: 2024-11-17
@version: 1.0.0
@path: utils/opencv_funcs.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - Opencv 函数封装
"""
import cv2

# 颜色字典(BGR格式)
COLORS = {
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'red': (0, 0, 255),
    'green': (0, 255, 0),
    'blue': (255, 0, 0),
    'yellow': (0, 255, 255),
    'magenta': (255, 0, 255),
    'gray': (128, 128, 128),
    'purple': (255, 0, 255),
    'cyan': (255, 255, 0),
    'orange': (0, 165, 255)
}

'''
########################################################
------------------- decorator functions ----------------
########################################################
'''


# 打印图片类型
def printImgDateTypeDecorator(func):
    """
    打印图片类型装饰器
    :param func: 被装饰函数
    :return:
    """

    def wrapper(*args, **kwargs):
        """
        装饰器，用来判断图像类型
        :param args:
        :param kwargs:
        """
        image = readImageColor(args[0])
        templateImg = readImageColor(args[1])
        print(f"图像类型：{image.dtype}")
        print(f"模板图像类型：{templateImg.dtype}")
        image, max_similarity = func(*args, **kwargs)
        print(f"\n方法：{func.__name__} 执行成功")
        return image, max_similarity

    return wrapper


'''
########################################################
----------------- universal functions ------------------
########################################################
'''


# 将图像、视频帧、直播视频帧缩放到指定大小，默认缩小0.75倍
def rescaleFrame(frame, scale=0.75):
    """
    将图像、视频帧、直播视频帧缩放到指定大小，默认缩小0.75倍
    :param frame: 图像、视频帧、直播视频帧
    :param scale: 缩放比例
    :return: 缩放后的图像、视频帧、直播视频帧
    """
    width = int(frame.shape[1] * scale)
    height = int(frame.shape[0] * scale)
    # 定义缩放后的视频尺寸
    dimensions = (width, height)
    # 返回缩放后的视频帧，指定图像缩放时采用的插值方法 cv2.INTER_AREA
    return cv2.resize(frame, dimensions, interpolation=cv2.INTER_AREA)


'''
########################################################
------------------- image functions --------------------
########################################################
'''


# 读取彩色图片
def readImageColor(imagePath):
    """
    读取彩色图片, 返回值是一个NumPy数组,如果图片成功加载,该数组将包含图片的像素数据；
    数组的形状（shape）通常是(高度, 宽度, 3)，
    对应于图片的高度、宽度和颜色通道数（对于彩色图片是3，因为使用BGR格式表示红、绿、蓝三个颜色通道）。
    如果函数无法读取图片（比如因为文件不存在或者文件格式不被支持），则会返回None
    :param imagePath: 图片路径
    :return: 返回值是一个NumPy数组
    """
    # 从指定的路径 imagePath 读取一幅图片，并以彩色模式返回该图片
    return cv2.imread(imagePath, cv2.IMREAD_COLOR)


# 在匹配到的图片位置绘制矩形
def drawRectangle(imagePath, templateImgPath, threshold=0.8,
                  color=COLORS['red'], thickness=2) -> tuple:
    """
    在匹配到的图片位置绘制矩形,使用归一化相关系数匹配方法(cv2.TM_CCOEFF_NORMED)
    若匹配失败返回一个 None 和最大相似度的阈值log[1]
    :param imagePath: 待绘制矩形框的图像路径或 np.ndarray
    :param templateImgPath: 模板图片路径
    :param threshold: 匹配模板图片的阈值，高于此值则绘制矩形
    :param color: 绘制的矩形框的颜色
    :param thickness: 绘制的矩形框的线条粗细
    :return: image, loc[1] - 返回绘制之后的图片和最大相似度的阈值log[1]

    loc 是由cv2.minMaxLoc 函数返回的结果，其中包含了以下四个值：
        - log[0]：这是模板匹配结果中的最小值，表示所有匹配区域中相似度的最小分数。
        - log[1]：这是模板匹配结果中的最大值，表示所有匹配区域中相似度的最大分数。
        - log[2]：这是最小值的坐标位置，即相似度最低的点在图像中的位置。
        - log[3]：这是最大值的坐标位置，即相似度最高的点在图像中的位置。
    """
    # 读取图片
    if isinstance(imagePath, str):
        image = readImageColor(imagePath)
    else:
        # imagePath 为 np.ndarray
        image = cv2.cvtColor(imagePath, cv2.COLOR_BGR2RGB)
        cv2.imwrite("temp.png", image)  # 保存全屏截图为临时文件

    templateImg = readImageColor(templateImgPath)
    # 使用模板匹配在大图中寻找小图的位置，cv2.TM_CCOEFF_NORMED 表示使用归一化相关系数匹配方法
    result = cv2.matchTemplate(image, templateImg, cv2.TM_CCOEFF_NORMED)
    # 使用cv2.minMaxLoc找出匹配结果中的最小值和最大值及它们的位置
    loc = cv2.minMaxLoc(result)
    # 如果最大值大于等于阈值，则认为找到了模板的位置
    if loc[1] >= threshold:
        # 获取模板匹配到的左上角坐标
        top_left = loc[3]
        # 获取模板图片的高度和宽度
        h, w = templateImg.shape[:2]
        # 计算模板匹配到的右下角坐标
        bottom_right = (top_left[0] + w, top_left[1] + h)
        # 在原始截图上绘制矩形框出匹配到的模板位置，边框颜色为绿色，线条粗细为2
        cv2.rectangle(image, top_left, bottom_right, color=color, thickness=thickness)
        return image, loc[1]
    # 未匹配成功
    return None, loc[1]


# 获取匹配到的图像的中心坐标
def centerPosition(imagePath, templateImgPath, threshold):
    """
    获取匹配到的图像的中心坐标,使用归一化相关系数匹配方法(cv2.TM_CCOEFF_NORMED)
    :param imagePath: 待匹配图片路径
    :param templateImgPath: 作为匹配模板的图片路径
    :param threshold: 匹配模板图片的阈值
    :return: (center_x, center_y), log[1] - 返回匹配到的图像的中心坐标和最大相似度的阈值log[1];
    如果未匹配成功则返回 None 和最大相似度的阈值log[1]
    """
    # 读取图片
    if isinstance(imagePath, str):
        image = readImageColor(imagePath)
    else:
        # imagePath 为 np.ndarray
        image = cv2.cvtColor(imagePath, cv2.COLOR_BGR2RGB)
        cv2.imwrite("Temp/temp.png", image)  # 保存全屏截图为临时文件
    templateImg = readImageColor(templateImgPath)
    # 使用模板匹配在大图中寻找小图的位置，cv2.TM_CCOEFF_NORMED 表示使用归一化相关系数匹配方法
    result = cv2.matchTemplate(image, templateImg, cv2.TM_CCOEFF_NORMED)
    # 使用cv2.minMaxLoc找出匹配结果中的最小值和最大值及它们的位置
    loc = cv2.minMaxLoc(result)
    if loc[1] >= threshold:
        # 获取模板匹配到的左上角坐标
        topLeft = loc[3]
        # 获取模板图片的高度和宽度
        # templateImg.shape 返回一个包含图像维度的元组。对于彩色图像，这个返回值通常是三个元素的元组
        # (高度, 宽度, 颜色通道数)。:2 是一个切片操作符，它获取元组中的第一个元素和第二个元素
        templateImgHeight, templateImgWidth = templateImg.shape[:2]
        print(f"[INFO] - (centerPosition) 匹配成功，模板图片的高度为 {templateImgHeight},宽度为 {templateImgWidth}")
        # 计算匹配到的图片的中心横坐标
        center_x = topLeft[0] + templateImgWidth / 2
        # 计算匹配到的图片的中心纵坐标
        center_y = topLeft[1] + templateImgHeight / 2
        # 返回中心坐标
        print(f"[INFO] - (centerPosition) 模板图片中心坐标为 ({center_x}, {center_y})")
        return (center_x, center_y), loc[1]
    # 未匹配成功
    return None, loc[1]


'''
#######################################################
------------------ video functions --------------------
#######################################################
'''


# 读取视频文件并逐帧显示
def readVideo(video_path, scale=0.75):
    """
    读取视频文件并逐帧显示
    :param video_path: 视频文件的路径
    :param scale: 视频缩放比例
    """
    # 创建一个VideoCapture对象
    cap = cv2.VideoCapture(video_path)
    # 检查视频是否成功打开
    if not cap.isOpened():
        print(f"[ERROR] - 无法打开视频：{video_path}")
        return None
    print(f"[INFO] - 正在打开视频：{video_path}\n按q键退出")
    # 循环直到视频结束
    while True:
        # 逐帧读取视频
        ret, frame = cap.read()
        # 如果正确读取帧，ret为True
        if not ret:
            print("无法接收帧（流结束？），正在退出...")
            break
        # 缩放帧
        rescal_frame = rescaleFrame(frame, scale)
        # 显示帧
        cv2.imshow(f'VideoShow-scale{scale}', rescal_frame)
        # 按'q'键退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    # 释放VideoCapture对象
    cap.release()
    # 关闭所有OpenCV窗口
    cv2.destroyAllWindows()


