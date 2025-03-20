
name="图片匹配"
template_img=r"C:\Users\Administrator\Desktop\1.png"

cmd = ImageMatchCmd(name=name,template_img=template_img,error_retries=20,error_retries_time=0.5)
cmd.execute()
print_command(cmd)

print(cmd.template_img_center)

import pyautogui
pyautogui.moveTo(cmd.template_img_center, duration=2)