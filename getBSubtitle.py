import requests
import json
import re
import time
from qrcode import QRCode
from qrcode.image.pil import PilImage
import os


def get_name_aid_cid(bv,pp,headers):
     vedio_info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv}"
     print(f"aid和cid的查询接口 {vedio_info_url}")

     aid_cid_response = requests.get(vedio_info_url, headers=headers)
     aid_cid_json = json.loads(aid_cid_response.text)
     aid = aid_cid_json["data"]["aid"]
     pages = aid_cid_json["data"]["pages"]
     cid = pages[pp-1]["cid"]
     print(f"第{pp}页的cid为{cid}")
     name = pages[pp-1]["part"]

     return name,aid,cid

def get_title_address(aid,cid,headers):
     title_address_url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
     print(f"字幕地址查询接口 {title_address_url}")
     title_address_response = requests.get(title_address_url, headers=headers)
     title_address_json = json.loads(title_address_response.text)
     subtitles = title_address_json["data"]["subtitle"]["subtitles"]
     chinese_title_address = get_chinese_title_address(subtitles)
     english_title_address = get_english_title_address(subtitles)
     if chinese_title_address or english_title_address:
          return chinese_title_address,english_title_address
     else:
          return None,None

def get_chinese_title_address(subtitles):
     chinese_title_address = None
     for subtitle in subtitles:
          if subtitle["lan"] == "zh-CN" or subtitle["lan"] == "ai-zh":
               chinese_title_address = f"https:{subtitle["subtitle_url"]}"
               print(f"中文字幕地址{chinese_title_address}")
               return chinese_title_address
     print("没有中文字幕地址")
     return None

def get_english_title_address(subtitles):
     english_title_address = None
     for subtitle in subtitles:
          if subtitle["lan"] == "en-US":
               english_title_address = f"https:{subtitle["subtitle_url"]}"
               print(f"英文字幕地址{english_title_address}")
               return english_title_address
     print("没有英文字幕地址")
     return None

def get_chinese_contents(chinese_title_address):
     if not chinese_title_address:
          return ""
     chinese_title =  requests.get(chinese_title_address, headers=headers)
     chinese_title_json = json.loads(chinese_title.text)
     chinese_titles = chinese_title_json["body"]
     chinese_contents = ""
     for item in chinese_titles:
          chinese_contents += item["content"]
     if chinese_titles == "":
          print("没有中文字幕")
     return chinese_contents

def get_english_contents(english_title_address):
     if not english_title_address:
          return ""
     english_title =  requests.get(english_title_address, headers=headers)
     english_title_json = json.loads(english_title.text)
     english_titles = english_title_json["body"]
     english_contents = ""
     for item in english_titles:
          english_contents += item["content"]
     if english_titles:
          english_contents += "\n"
     else:
          print("没有英文字幕")
     return english_contents

def get_bv_p(url):
     bv_pattern = r"BV[0-9A-Za-z]+"
     p_pattern = r"p=\d+"

     bv_match = re.search(bv_pattern, url)
     p_match = re.search(p_pattern, url)

     if not p_match :
          p = 1
     else:
          p = int(p_match.group().split("=")[1])

     if bv_match :
          bv = bv_match.group()
          return bv,p
     else:
          return None,None
     
def get_QRcode(request_headers):
     qrcode_url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
     qrcode_response_json = requests.get(qrcode_url,headers=request_headers).json()
     qrcode_key = qrcode_response_json["data"]["qrcode_key"]
     print(f"二维码key为{qrcode_key}")
     qr = QRCode()
     qr.add_data(qrcode_response_json["data"]["url"])
     pil_img = qr.make_image(image_factory=PilImage, fill_color="black", back_color="white")
     if pil_img:
          pil_img.show()
          return qrcode_key
     else:
          print("\033[91m生成二维码失败\033[0m")

def get_cookie(qrcode_key,headers):
     check_login_url = f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}&source=main-fe-header'
     print(f"检查登录接口{check_login_url}")
     session = requests.Session()
     while True:
          response = session.get(check_login_url,headers=headers)
          data = response.json()
          if data["data"]["code"] == 0:
               print("\033[92m登录成功\033[0m")
               
               # 从登录响应中获取完整的cookie
               login_cookies = response.cookies.get_dict()
               print("登录接口返回的cookie: ", login_cookies)
               
               # 访问首页获取更多cookie
               home_response = session.get("https://www.bilibili.com",headers=headers)
               home_cookies = home_response.cookies.get_dict()
               print("首页返回的cookie: ", home_cookies)
               
               # 合并所有cookie
               all_cookies = {**login_cookies, **home_cookies}
               print("合并后的cookie: ", all_cookies)
               
               # 保存cookie到文件
               try:
                    with open("cookies.json",'w', encoding='utf-8') as f:
                         json.dump(all_cookies, f, ensure_ascii=False, indent=2)
                    print(f"cookies写入成功，共{len(all_cookies)}个cookie")
               except Exception as e:
                    print(f"写入cookies.json时出错：{e}")
               break
          else:
               print("二维码未扫描或登录失败")
               time.sleep(5)

     
def fetch_title(bv,pp,headers):
     name,aid,cid = get_name_aid_cid(bv,pp,headers)

     chinese_title_address,english_title_address = get_title_address(aid,cid,headers)

     contents = ""
     #输入中文字幕地址和英文字幕地址，若地址为空，则返回空字符串
     chinese_contents = get_chinese_contents(chinese_title_address)
     english_contents = get_english_contents(english_title_address)
     
     #若中文字幕或英文字幕不为空，则合并为一个字符串
     if chinese_contents or english_contents:
          contents = english_contents + chinese_contents
          try:
               result_dir = "./result"
               if not os.path.exists(result_dir):
                    os.makedirs(result_dir)
               # 将字幕文件写入result目录
               with open(f"{result_dir}/{name}.md",'w') as f:
                    f.write(contents)
               print(f"\033[92m字幕文件{name}.md写入成功\033[0m")
          except Exception as e:
               print(f"\033[91m写入字幕文件时出错：{e}\033[0m")
     else:
          print("没有字幕")

def load_existing_cookies(headers):
    """
    加载已存在的cookies文件
    
    Args:
        headers: 请求头字典
    
    Returns:
        bool: 是否成功加载cookies
    """
    try:
        # 检查cookies.json文件是否存在
        if not os.path.exists("cookies.json"):
            print("cookies.json文件不存在")
            return False
        
        with open("cookies.json", 'r', encoding='utf-8') as f:
            cookies = json.loads(f.read())
            # 检查cookie是否有效
            if cookies and len(cookies) > 0:
                headers["Cookie"] = ";".join([f"{key}={value}" for key, value in cookies.items()])
                print("\033[92m成功加载cookies\033[0m")
                return True
            else:
                print("\033[91mcookies文件为空或无效\033[0m")
                return False
                
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"\033[91m加载cookies文件失败: {e}\033[0m")
        return False

def acquire_new_cookies(headers):
    """
    获取新的cookies（通过二维码登录）
    Args:
        headers: 请求头字典
    Returns:
        bool: 是否成功获取cookies
    """
    print("开始获取新的cookies...")
    
    # 获取二维码并等待用户扫描
    qrcode_key = get_QRcode(headers)
    try:
          get_cookie(qrcode_key, headers)
          print("成功获取cookies")
          return True
    except Exception as e:
          print(f"\033[91m获取cookies失败: {e}\033[0m")
    return False

def load_cookies_with_retry(headers, max_retries=3):
    """
    加载cookies的主函数，包含重试机制
    Args:
        headers: 请求头字典
        max_retries: 最大重试次数
        max_qr_retries: 二维码最大重试次数
    
    Returns:
        bool: 是否成功加载cookies
    """
    retry_count = 0
    
    while retry_count < max_retries:
        # 首先尝试加载已存在的cookies
        if load_existing_cookies(headers):
            return True
        
        # 如果加载失败，则获取新的cookies
        if acquire_new_cookies(headers):
            # 获取成功后，再次尝试加载
            if load_existing_cookies(headers):
                return True
        
        retry_count += 1
        if retry_count < max_retries:
            print(f"第{retry_count}次尝试失败，准备重试...")
            time.sleep(2)  # 等待2秒后重试
    
    print("已达到最大重试次数，程序退出")
    return False

if __name__ == "__main__":
     headers = {
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
           "Origin": "https://www.bilibili.com",
           "Referer": "https://www.bilibili.com"
     }


     if not load_cookies_with_retry(headers):
         print("无法获取cookies，程序退出")
         exit(1)

     is_continue = True

     while is_continue:
          url = input("\033[94m请输入需要获取字幕的视频链接：\033[0m")
          bv,p = get_bv_p(url)
          if bv and p:
               fetch_title(bv,p,headers)
          else:
               print("\033[91mError: 输入的链接格式错误\033[0m")
          is_continue = input("\033[94m是否继续获取字幕？(y/n)\033[0m") == "y"
     print("\033[92m拜拜~~😊😊😊\033[0m")
