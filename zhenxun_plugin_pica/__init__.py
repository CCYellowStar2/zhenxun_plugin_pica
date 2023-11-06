# -*- coding: utf-8 -*-
import os
import zipfile
import pyzipper
import random
import re
try:
    import ujson as json
except:
    import json
from .pica import pic2
from utils.message_builder import image
from fuzzywuzzy import process
from os.path import join, getsize

from configs.config import SYSTEM_PROXY, Config
from nonebot.params import CommandArg
import aiohttp
import aiofiles
from utils.utils import change_img_md5
from configs.path_config import IMAGE_PATH
from nonebot import on_command
from utils.message_builder import custom_forward_msg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, GroupMessageEvent, PrivateMessageEvent, NetworkError
from asyncio.exceptions import TimeoutError



__zx_plugin_name__ = "pica漫画"
__plugin_usage__ = """
usage：
======因需向远程请求,视网络环境等因素可能等待时间较长======

根据关键字搜本:
1.[搜pica +关键字],返回符合的本子信息
2.利用[1]中的漫画id, [看pica +漫画id]

指定分区的关键字搜本:
1.[分区搜 +分区+关键字],返回指定分区下的本子信息,空格分割
2.利用[1]中的漫画id, [看pica +漫画id]

随机本子:
1.[随机本子],返回随机本子信息并发送

指定分区的随机本子:
1.[指定随机 +分区名],返回指定分区下的随机本子信息并发送

我的收藏:
1.[我的收藏 +页数(默认第一页)],返回我的收藏下的本子信息
2.利用[1]中的漫画id, [看pica +漫画id]

哔咔排行:
1.[哔咔排行 +排序模式(H24, D7, D30)(默认H24也就是日榜)],返回哔咔排行榜下的本子信息
2.利用[1]中的漫画id, [看pica +漫画id]

清理哔咔缓存
1.[清理哔咔缓存]来清理哔咔缓存的所有文件

检查哔咔
1.检查哔咔链接并重新登录
    
""".strip()
__plugin_des__ = " 可以看bica"
__plugin_cmd__ = ["pica漫画","pica","pika漫画","哔咔漫画"]
__plugin_type__ = ("来点好康的",)
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__
}
__plugin_configs__ = {
    "pica_account": {
        "value": None,
        "help": "你的哔咔账号",
        "default_value": None,
    },
    "pica_password": {
        "value": None,
        "help": "你的哔咔密码",
        "default_value": None,
    },
    "zip_ispwd": {
        "value": False,
        "help": "发送的压缩包是否设置密码",
        "default_value": False,
    },
    "zip_password": {
        "value": 114514,
        "help": "压缩包默认密码",
        "default_value": 114514,
    },
}
proxy = SYSTEM_PROXY
#forward_msg_name = config.FORWARD_MSG_NAME
#forward_msg_uid = config.FORWARD_MSG_UID
#导入类
p = pic2.Pica()

#转发消息画像
forward_msg_name = "神秘的bot"
forward_msg_uid = 3369680096

#请求标头
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"}

#填写pica账号
pica_account = Config.get_config("zhenxun_plugin_pica", "pica_account")
pica_password = Config.get_config("zhenxun_plugin_pica", "pica_password")


#pica存放的文件夹
pica_folder = os.path.abspath(f"{IMAGE_PATH}/pica/")

#默认顺序
Order_Default = "ld"
'''
"ua"  # 默认
"dd"  # 新到旧
"da"  # 旧到新
"ld"  # 最多爱心
"vd"  # 最多指名
'''

#在下载中
isok=True
#单次使用冷却(s)
__plugin_cd_limit__ = {
    "cd": 60,
    "rst": "冲慢点..."
}
__plugin_block_limit__ = {"rst": "冲慢点..."}

#去除特殊字符,Windows下新建文件夹名不得包含以下字符
pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"

#获取分区列表
categories = pic2.categories
#获取排序字典
orders = pic2.orders
Dates = pic2.Dates

'''
usage:生成合并转发消息节点
param:chain:list(固定空列表，用于合成输出), msg(消息内容), #image(图片,目前似乎无法使用)
return:chain(合成后的转发消息节点)
'''
def make_forward_msg(chain:list, msg, imag = ''):
    for _msg in msg:
        data ={
                "type": "node",
                "data": {
                    "name": str(forward_msg_name),
                    "uin": str(forward_msg_uid),
                    "content": _msg,
                }
        }
        chain.append(data)
    if imag:
        data ={
                "type": "node",
                "data": {
                    "name": str(forward_msg_name),
                    "uin": str(forward_msg_uid),
                    "content": imag,
                }
        }
        chain.append(data)
        
    return chain

def make_forward_msgs(chain:list, msg, imag = []):
    for _msg in msg:
        data ={
                "type": "node",
                "data": {
                    "name": str(forward_msg_name),
                    "uin": str(forward_msg_uid),
                    "content": _msg,
                }
        }
        chain.append(data)
    if imag:
        for _img in imag:
            data ={
                    "type": "node",
                    "data": {
                        "name": str(forward_msg_name),
                        "uin": str(forward_msg_uid),
                        "content": _img,
                    }
            }
            chain.append(data)
        
    return chain


'''
usage:进行指令模糊匹配
param:input(用户输入内容), command:list(匹配指令列表)
return:fuzzy_word(匹配到的第一个词), fuzzy_probability(匹配相关度)
'''
def guess_command(input, command:list):
    fuzzy = process.extractOne(input, command)
    fuzzy_word = fuzzy[0]
    fuzzy_probability = fuzzy[1]
    
    return fuzzy_word, fuzzy_probability


async def download_img(url, booktitle, originalName):
    error_recall = []
    print(url)
    booktitle = booktitle.strip()
    sub = re.sub(pattern, "-", booktitle)
    #若不存在文件夹,先创建
    if not os.path.exists(pica_folder):
        os.mkdir(pica_folder)

    comic_folder = os.path.join(pica_folder,sub)
    if not os.path.exists(comic_folder):
        os.mkdir(comic_folder)
    async with aiohttp.ClientSession() as session:
        rs = await session.get(url=url, headers=headers, proxy=proxy, timeout=60)
        filename = str(originalName)
        image_path = os.path.join(comic_folder,filename)
        async with aiofiles.open(image_path, "wb") as download:
            try:
                await download.write(await rs.read())
                change_img_md5(image_path)
            except:
                error_recall = "pica资源获取失败:HTTP状态码:"+str(rs.status)
                print(error_recall)               

    return error_recall


'''
usage:从指定漫画id进行图片下载
param:bookid:str(漫画id)
return:error_recall(错误回执,无错误时为空)
'''
async def get_comic_from_id(bookid:str, name = ''):
    global isok
    error_recall = []
    ex_input = bookid.strip()
    try:
        cm = await p.comic_info(ex_input)
        cm = await cm.text()
        cm_read = json.loads(cm)
        cm_name = cm_read["data"]["comic"]["title"]
        thumb_url = cm_read["data"]["comic"]["thumb"]["fileServer"] + "/static/" + cm_read["data"]["comic"]["thumb"]["path"]
        if not name:
            name = cm_name
        await download_thumb(thumb_url, name)
    except:
        error_recall = "pica获取失败,可能是输入id错误"
        print(error_recall)
        return error_recall
    pic_post = await p.picture(ex_input)
    pic_post = await pic_post.text()
    pic_result = json.loads(pic_post)
    if not pic_result["code"] == 200:
        error_recall = "pica请求出错:HTTP状态码:"+str(pic_result["code"])+"\n响应信息:" + pic_result["message"]
        print(error_recall)
    else:
        isok=False
        pages_num = pic_result["data"]["pages"]["pages"]
        for x in range(1, pages_num+1):
            post_pic = await p.picture(ex_input,page=x)
            post_pic = await post_pic.text()
            meta = json.loads(post_pic)
            docs = meta["data"]["pages"]["docs"]
            for y in range(len(docs)):
                ogname = docs[y]["media"]["originalName"]
                imgpath = docs[y]["media"]["path"]
                fileServer = docs[y]["media"]["fileServer"]
                url = fileServer + "/static/" + imgpath
                print(f"当前正在下载:第{x}页第{y}张:{ogname}")
                try:
                    await download_img(url,cm_name,ogname)
                except:
                    print(f"第{x}页第{y}张:{ogname}下载失败")
                    pass   
        isok=True

'''
usage:下载指定url的封面图
param:url(图片url), booktitle(漫画名,用来作为文件名)
'''
async def download_thumb(url, booktitle):
    error_recall = []
    booktitle = booktitle.strip()
    print(url)
    sub = re.sub(pattern, "-", booktitle)
    #若不存在文件夹,先创建
    if not os.path.exists(pica_folder):
        os.mkdir(pica_folder)

    comic_folder = os.path.join(pica_folder,sub)
    if not os.path.exists(comic_folder):
        os.mkdir(comic_folder)
    try:
        async with aiohttp.ClientSession() as session:
            rs = await session.get(url=url, headers=headers, proxy=proxy, timeout=30)
            filename = sub+"_cover"+".jpg"
            image_path = os.path.join(comic_folder,filename)
            async with aiofiles.open(image_path, "wb") as download:
                try:
                    await download.write(await rs.read())
                    change_img_md5(image_path)
                    thb_path = image(image_path)    
                    return thb_path
                except:
                    error_recall = "pica请求出错:HTTP状态码:"+str(rs.status)
                    print("pica资源获取失败:HTTP状态码:"+str(rs.status))
    except:
        print("这张失败了")
        return error_recall
        pass


'''
usage:获取我的收藏遍历列表
param:res:dict(存有漫画信息的字典)
return:我的收藏遍历列表
'''
async def get_random_favorite(res:dict):
    global isok
    comic_info = []
    comic_info2 = []
    favor = {}
    meta = res["data"]["comics"]["docs"]
    for x in range(0, len(meta)):
        value_list = []
        bkid = meta[x]["_id"]
        bktitle = str(meta[x]["title"])
        author = str(meta[x]["author"])
        bkthumb = str(meta[x]["thumb"]["fileServer"] + "/static/" + meta[x]["thumb"]["path"])
        value_list.append(bktitle)
        value_list.append(author)
        value_list.append(bkthumb)
        favor[bkid] = value_list
    isok=False
    for key,value in favor.items():
        detail = f"{value[0]}：\n作者:{value[1]}\n漫画ID:{key}"
        thumb_url = value[2]
        comic_info.append(detail)
        comic_info2.append(detail)
        try:
            pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"
            sub = re.sub(pattern, "-", value[0])
            comic_info.append(await download_thumb(thumb_url, sub))
        except:
            pass
    print("下完了")
    isok=True
    return comic_info, comic_info2

'''
usage:获取漫画id及信息
param:result:dict(存有漫画信息的字典)
return:error_recall(错误回执/若有), comic_info(漫画信息)
'''
async def get_search_bookid(result:dict, name = ''):
    global isok
    error_recall = []
    comic_info = []
    imgs=[]
    i=0
    isok=False
    if result["data"]["comics"]["total"] == 0:
        error_recall = "pica搜索出错:搜索结果为空.请尝试更换关键词"
        print(error_recall)
        isok=True
        return error_recall, comic_info, imgs

    elif result["data"]["comics"]["total"] == 1:
        meta = result["data"]["comics"]["docs"][0]
        bookid = meta["_id"]
        thumb_url = meta["thumb"]["fileServer"] + "/static/" + meta["thumb"]["path"]
        title = meta["title"]
        author = meta["author"]
        try:
            chineseTeam = meta["chineseTeam"]
        except:
            chineseTeam = "Unknown"
        comic_info = f"{title}：\n作者:{author}\n汉化:{chineseTeam}\n漫画ID:{bookid}"
        if not name:
            name = title
        imgs.append(await download_thumb(thumb_url, name))
        isok=True
        return error_recall, comic_info, imgs

    elif result["data"]["comics"]["total"] == 3:

        meta_1 = result["data"]["comics"]["docs"][0]
        meta_2 = result["data"]["comics"]["docs"][1]
        meta_3 = result["data"]["comics"]["docs"][2]
        #有时返回的JSON不存在chineseTeam
        try:
            chineseTeam_1 = meta_1["chineseTeam"]
        except:
            chineseTeam_1 = "Unknown"
        
        try:
            chineseTeam_2 = meta_2["chineseTeam"]
        except:
            chineseTeam_2 = "Unknown"
        
        try:
            chineseTeam_3 = meta_3["chineseTeam"]
        except:
            chineseTeam_3 = "Unknown"
        cm_info1 = meta_1["title"] + "\n" + "作者:" + meta_1["author"] + "\n" + "汉化:" + chineseTeam_1 + "\n" +"漫画ID:" + meta_1["_id"]
        cm_info2 = meta_2["title"] + "\n" + "作者:" + meta_2["author"] + "\n" + "汉化:" + chineseTeam_2 + "\n" +"漫画ID:" + meta_2["_id"]
        cm_info3 = meta_3["title"] + "\n" + "作者:" + meta_3["author"] + "\n" + "汉化:" + chineseTeam_3 + "\n" +"漫画ID:" + meta_3["_id"]
        comic_info.append(cm_info1)
        comic_info.append(cm_info2)
        comic_info.append(cm_info3)
        thumb_url = meta_1["thumb"]["fileServer"] + "/static/" + meta_1["thumb"]["path"]
        thumb_url2 = meta_2["thumb"]["fileServer"] + "/static/" + meta_2["thumb"]["path"]
        thumb_url3 = meta_3["thumb"]["fileServer"] + "/static/" + meta_3["thumb"]["path"]
        if not name:
            name = meta_1["title"]        
        imgs.append(await download_thumb(thumb_url, name))
        imgs.append(await download_thumb(thumb_url2, meta_2["title"]))
        imgs.append(await download_thumb(thumb_url3, meta_3["title"]))
        isok=True
        return error_recall, comic_info, imgs
        
    elif result["data"]["comics"]["total"] > 3:
        if result["data"]["comics"]["total"] > 20:
            i = 20
        else:
            i = result["data"]["comics"]["total"]
        meta_1 = result["data"]["comics"]["docs"][random.randint(0,i-1)]
        meta_2 = result["data"]["comics"]["docs"][random.randint(0,i-1)]
        meta_3 = result["data"]["comics"]["docs"][random.randint(0,i-1)]
        #有时返回的JSON不存在chineseTeam
        try:
            chineseTeam_1 = meta_1["chineseTeam"]
        except:
            chineseTeam_1 = "Unknown"
        
        try:
            chineseTeam_2 = meta_2["chineseTeam"]
        except:
            chineseTeam_2 = "Unknown"
        
        try:
            chineseTeam_3 = meta_3["chineseTeam"]
        except:
            chineseTeam_3 = "Unknown"
        cm_info1 = meta_1["title"] + "\n" + "作者:" + meta_1["author"] + "\n" + "汉化:" + chineseTeam_1 + "\n" +"漫画ID:" + meta_1["_id"]
        cm_info2 = meta_2["title"] + "\n" + "作者:" + meta_2["author"] + "\n" + "汉化:" + chineseTeam_2 + "\n" +"漫画ID:" + meta_2["_id"]
        cm_info3 = meta_3["title"] + "\n" + "作者:" + meta_3["author"] + "\n" + "汉化:" + chineseTeam_3 + "\n" +"漫画ID:" + meta_3["_id"]
        comic_info.append(cm_info1)
        comic_info.append(cm_info2)
        comic_info.append(cm_info3)
        thumb_url = meta_1["thumb"]["fileServer"] + "/static/" + meta_1["thumb"]["path"]
        thumb_url2 = meta_2["thumb"]["fileServer"] + "/static/" + meta_2["thumb"]["path"]
        thumb_url3 = meta_3["thumb"]["fileServer"] + "/static/" + meta_3["thumb"]["path"]
        if not name:
            name = meta_1["title"]        
        imgs.append(await download_thumb(thumb_url, name))
        imgs.append(await download_thumb(thumb_url2, meta_2["title"]))
        imgs.append(await download_thumb(thumb_url3, meta_3["title"]))
        isok=True
        return error_recall, comic_info, imgs
        
    else:
        meta_1 = result["data"]["comics"]["docs"][0]
        try:
            chineseTeam_1 = meta_1["chineseTeam"]
        except:
            chineseTeam_1 = "Unknown"
        cm_info1 = meta_1["title"] + "\n" + "作者:" + meta_1["author"] + "\n" + "汉化:" + chineseTeam_1 + "\n" +"漫画ID:" + meta_1["_id"]
        thumb_url = meta_1["thumb"]["fileServer"] + "/static/" + meta_1["thumb"]["path"]
        if not name:
            name = meta_1["title"] 
        imgs.append(await download_thumb(thumb_url, name))
        isok=True
        return error_recall, cm_info1, imgs

async def get_rank(result:dict, name = ''):
    global isok
    error_recall = []
    comic_info = []
    comic_info2 =[]
    i=20
    ids=0
    isok=False
    for ids in range(i): 
        meta = result["data"]["comics"][ids]
        try:
            chineseTeam_1 = meta["chineseTeam"]
        except:
            chineseTeam_1 = "Unknown"

        cm_info = meta["title"] + "\n" + "作者:" + meta["author"] + "\n" + "汉化:" + chineseTeam_1 + "\n" +"漫画ID:" + meta["_id"]

        comic_info.append(cm_info)
        comic_info2.append(cm_info)
        thumb_url = meta["thumb"]["fileServer"] + "/static/" + meta["thumb"]["path"]
        name = meta["title"]        
        try:
            pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"
            sub = re.sub(pattern, "-", name)
            comic_info.append(await download_thumb(thumb_url, sub))
        except:
            pass
    isok=True
    return error_recall, comic_info, comic_info2
        
'''
usage:生成压缩包
param:source_dir(需要压缩文件的目录), output_filename(压缩包文件名)
return:压缩包目录
'''
def make_zip(source_dir, output_filename):

    if not Config.get_config("zhenxun_plugin_pica", "zip_ispwd"):
        zipf = zipfile.ZipFile(output_filename, 'w')
        pre_len = len(os.path.dirname(source_dir))
        for parent, _, filenames in os.walk(source_dir):
            for filename in filenames:
                pathfile = os.path.join(parent, filename)
                arcname = pathfile[pre_len:].strip(os.path.sep)
                zipf.write(pathfile, arcname)                
        zipf.close()
    else:
        with pyzipper.AESZipFile(
            output_filename,
            "w",
            compression=pyzipper.ZIP_LZMA,
            encryption=pyzipper.WZ_AES,
        ) as zf:
            ps=str(Config.get_config("zhenxun_plugin_pica", "zip_password"))
            print(ps)            
            zf.setpassword(bytes(ps, encoding='utf-8'))
            zf.setencryption(pyzipper.WZ_AES, nbits=128)
            pre_len = len(os.path.dirname(source_dir))
            for parent, _, filenames in os.walk(source_dir):
                for filename in filenames:
                    pathfile = os.path.join(parent, filename)
                    arcname = pathfile[pre_len:].strip(os.path.sep)
                    zf.write(pathfile, arcname) 
                    

    print(f"压缩包创建完成:位于{output_filename}")
    return output_filename


rank = on_command("哔咔排行", aliases={"哔咔rank", "pikarank"}, block=True, priority=5)
#>>>根据关键字搜本<<<
@rank.handle()
async def pica_rank(bot: Bot, ev: Event, msg: Message = CommandArg()):
    chain = []
    global isok
    if not isok:
        await bot.send(ev, "有任务在进行中")
        return
    if not pica_account or not pica_password:
        await bot.send(ev, "请去config.yaml配置文件设置你的哔咔账号密码")
        return    
    input1 = msg.extract_plain_text()
    if isinstance(ev, GroupMessageEvent):
        gid = ev.group_id
    uid = ev.user_id
    if not input1:
        await bot.send(ev, "未输入排行模式，自动选择24h榜！")
        rank_type = "H24"
    else:
        rank_type = input1.strip().replace('d','D').replace('h','H')
        fuzzy_word, fuzzy_probability = guess_command(rank_type, Dates)
        if fuzzy_probability == 100:
            pass
        else:
            tips = f"您有{fuzzy_probability}%的可能想搜索“{fuzzy_word}”。"
            await bot.send(ev, tips)
            rank_type = fuzzy_word        
    try:
        data = (await p.rank(rank_type))  # type: ignore
        data = await data.json()
    except Exception as e:
        await bot.send(ev, f"请求失败，{e}")  
        return
    print(data)
    if not data["code"] == 200:
        error_recall = "pica请求出错:HTTP状态码:"+str(data["code"])+"\n响应信息:" + data["message"]
        await bot.send(ev, error_recall)
    else:         
        await bot.send(ev, "开始整理")
        try:
            error, comic_info,thb_path = await get_rank(data)
        except Exception as e:
            await bot.send(ev, f"请求失败,{e}")    
            isok=True
            return
        if not error:
            out = custom_forward_msg(comic_info, bot.self_id)
            out2 = custom_forward_msg(thb_path, bot.self_id)        
            if isinstance(ev, GroupMessageEvent):
                try:
                    await bot.send_group_forward_msg(group_id=ev.group_id, messages=out)
                except:
                    await bot.send_group_forward_msg(group_id=ev.group_id, messages=out2)
                    await bot.send(ev, "请使用 [看pica 漫画id] 来查看")
                    return
            else:
                await bot.send_private_forward_msg(user_id=ev.user_id, messages=out)
        else:
            await bot.send(ev, error)
        await bot.send(ev, "请使用 [看pica 漫画id] 来查看")

sv = on_command("搜pica", aliases={"搜哔咔", "搜pika"}, block=True, priority=5)
#>>>根据关键字搜本<<<
@sv.handle()
async def search_pica(bot: Bot, ev: Event, msg: Message = CommandArg()):
    chain = []
    global isok
    if not isok:
        await bot.send(ev, "有任务在进行中")
        return    
    if not pica_account or not pica_password:
        await bot.send(ev, "请去config.yaml配置文件设置你的哔咔账号密码")
        return
    input1 = msg.extract_plain_text()
    if isinstance(ev, GroupMessageEvent):
        gid = ev.group_id
    uid = ev.user_id
    #获取好友列表,并判断当前用户是否在好友列表中
    bot_friend_list = await bot.get_friend_list()
    fd_list = []
    for fd in bot_friend_list:
        gfd = fd["user_id"]
        fd_list.append(str(gfd))   
    #冷却限制

    #忽略空关键词
    if not input1:
        await bot.send(ev, "输入为空！")
        return
    else:
        #转换为繁体
        ex_input = input1.strip()
        #去除特殊字符(使用标题作为文件夹名时,不能包含特殊字符)
        pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"
        sub = re.sub(pattern, "-", ex_input)

        try:
            search_post = await p.search(keyword=ex_input, categories=[], sort=Order_Default)
            search_post = await search_post.json()
        except Exception as e:
            await bot.send(ev, f"请求失败，{e}")   
            return
        search_result = search_post
        print(search_result)
        if not search_result["code"] == 200:
            error_recall = "pica请求出错:HTTP状态码:"+str(search_result["code"])+"\n响应信息:" + search_result["message"]
            await bot.send(ev, error_recall)
        else:         
            await bot.send(ev, "开始整理")
            try:
                error, comic_info,thb_path = await get_search_bookid(search_result)
            except Exception as e:
                await bot.send(ev, f"请求失败,{e}")  
                isok=True
                return
            if not error:
                out = make_forward_msgs(chain, comic_info, thb_path)
                out2 = make_forward_msg(chain, comic_info)                
                if isinstance(ev, GroupMessageEvent):
                    try:
                        await bot.send_group_forward_msg(group_id=ev.group_id, messages=out)
                    except:
                        await bot.send_group_forward_msg(group_id=ev.group_id, messages=out2)
                        await bot.send(ev, "请使用 [看pica 漫画id] 来查看")
                        return
                else:
                    await bot.send_private_forward_msg(user_id=ev.user_id, messages=out)
            else:
                await bot.send(ev, error)
            await bot.send(ev, "请使用 [看pica 漫画id] 来查看")
#冷却计时


svv = on_command("分区搜", aliases={"搜分区"}, block=True, priority=5)
#>>>指定分区的关键字搜本<<<
@svv.handle()
async def search_pica_cate(bot: Bot, ev: Event, msg: Message = CommandArg()):
    chain = []
    global isok
    if not isok:
        await bot.send(ev, "有任务在进行中")
        return    
    if not pica_account or not pica_password:
        await bot.send(ev, "请去config.yaml配置文件设置你的哔咔账号密码")
        return    
    uid = ev.user_id
    input2 = msg.extract_plain_text()
    if not input2:
        await bot.send(ev, "输入为空！")
        return
    else:
        ex_input = input2.strip().split()
        sort_ca = []
        #分区在前,关键字在后
        cate = ex_input[0]
        cates_ex = cate
        #模糊匹配分区
        fuzzy_word, fuzzy_probability = guess_command(cates_ex, categories)
        if fuzzy_probability == 100:
            pass
        else:
            tips = f"您有{fuzzy_probability}%的可能想搜索“{fuzzy_word}”。"
            await bot.send(ev, tips)
            cates_ex = fuzzy_word
        words = ex_input[1]
        keyword = words
        pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"
        sub = re.sub(pattern, "-", keyword)
        sort_ca.append(cates_ex)
        try:
            search_post = await p.search(keyword=keyword, categories=sort_ca, sort=Order_Default)
            search_post = await search_post.json()
        except Exception as e:
            await bot.send(ev, f"请求失败，{e}")   
            return        
        search_result = search_post
        print(search_result)
        if not search_result["code"] == 200:
            error_recall = "pica请求出错:HTTP状态码:"+str(search_result["code"])+"\n响应信息:" + search_result["message"]
            await bot.send(ev, error_recall)
        else:
            await bot.send(ev, "开始整理")
            try:
                error, comic_info,thb_path = await get_search_bookid(search_result)
            except Exception as e:
                await bot.send(ev, f"请求失败,{e}")  
                isok=True
                return
            if not error:
                out = make_forward_msgs(chain, comic_info, thb_path)
                out2 = make_forward_msg(chain, comic_info)            
                if isinstance(ev, GroupMessageEvent):
                    try:
                        await bot.send_group_forward_msg(group_id=ev.group_id, messages=out)
                    except:
                        await bot.send_group_forward_msg(group_id=ev.group_id, messages=out2)
                        await bot.send(ev, "请使用 [看pica 漫画id] 来查看")
                        return
                else:
                    await bot.send_private_forward_msg(user_id=ev.user_id, messages=out)
            else:
                await bot.send(ev, error)
            await bot.send(ev, "请使用 [看pica 漫画id] 来查看")
    #冷却计时


svid = on_command("看pica", aliases={"看哔咔", "看pika"}, block=True, priority=5)
#>>>使用漫画ID查看本子<<<
@svid.handle()
async def get_pica(bot: Bot, ev: Event, msg: Message = CommandArg()):
    chain = []
    global isok
    if not isok:
        await bot.send(ev, "有任务在进行中")
        return    
    if not pica_account or not pica_password:
        await bot.send(ev, "请去config.yaml配置文件设置你的哔咔账号密码")
        return    
    input3 = msg.extract_plain_text()
    if isinstance(ev, GroupMessageEvent):
        gid = ev.group_id
    uid = ev.user_id

    if not input3:
        await bot.send(ev, "输入为空！")
        return
    else:
        try:
            src = await p.comic_info(input3.strip())
            src = await src.json()
        except Exception as e:
            await bot.send(ev, f"请求失败，{e}")    
            return
        src_data = src
        print(src_data)
        try:
            out = src_data["data"]["comic"]
            bookid = out["_id"]
            name = src_data["data"]["comic"]["title"].strip()
            author = src_data["data"]["comic"]["author"]
            pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"
            name = re.sub(pattern, "-", name)
        except:
            await bot.send(ev, f"没有这个id的本子，请检查id是否输入正确") 
            isok=True
            return
        try:
            chineseTeam = src_data["data"]["comic"]["chineseTeam"]
        except:
            chineseTeam = "Unknown"
        zipname = name+".zip"
        zippath = f"{pica_folder}/{zipname}"
        if os.path.exists(zippath):
            await bot.send(ev, "本地已缓存")
        else:
            await bot.send(ev, "开始下载和打包")
            try:
                await get_comic_from_id(bookid)
            except Exception as e:
                await bot.send(ev, f"请求失败,{e}") 
                isok=True
                return
            dirname = os.path.join(pica_folder,str(name))
            output_filename = dirname+".zip"
            zippath = make_zip(source_dir=dirname, output_filename=output_filename)

    bot_friend_list = await bot.get_friend_list()
    fd_list = []
    for fd in bot_friend_list:
        gfd = fd["user_id"]
        fd_list.append(str(gfd))  
    comic_folder = os.path.join(pica_folder,str(name))
    thbname = str(name)+"_cover.jpg"
    image_path = os.path.join(comic_folder,thbname)
    thb_path = image(image_path)
    
    msg = [f"{name}：\n作者:{author}\n汉化:{chineseTeam}\n漫画ID:{bookid}"]
    output = make_forward_msg(chain, msg, thb_path)
    output2 = make_forward_msg(chain, msg)
    if isinstance(ev, PrivateMessageEvent):
        if str(uid) in fd_list:
            await bot.send(ev, f"消息处理成功, 请注意私聊窗口")
            await bot.send_private_msg(user_id=int(uid),message=thb_path)
            await bot.send_private_msg(user_id=int(uid),message=msg[0])
            await bot.upload_private_file(user_id=int(uid),file=zippath,name=name+".zip")

    else:
        try:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=output)
        except:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=output2)        
        try:
            await bot.upload_group_file(group_id=int(gid),file=zippath,name=name+".zip")          
        except:
            await bot.send(ev, f"消息已响应, 但上传失败.请查看日志窗口")
    if Config.get_config("zhenxun_plugin_pica", "zip_ispwd"):
        ps = Config.get_config("zhenxun_plugin_pica", "zip_password")
        await bot.send(ev, f"压缩包已设置密码为{ps}")     


sj = on_command("随机本子", block=True, priority=5)
#>>>随机本子<<<
@sj.handle()
async def get_pica_random(bot: Bot, ev: Event):
    chain = []
    global isok
    if not isok:
        await bot.send(ev, "有任务在进行中")
        return    
    if not pica_account or not pica_password:
        await bot.send(ev, "请去config.yaml配置文件设置你的哔咔账号密码")
        return    
    if isinstance(ev, GroupMessageEvent):
        gid = ev.group_id
    uid = ev.user_id

    #随机分区
    cate = random.choice(categories)
    await bot.send(ev, f"随机分区:{cate}")
    #随机排序
    od_list = []
    for key in orders.keys():
        od_list.append(key)
    order = random.choice(od_list)
    order_cn = orders[order]
    await bot.send(ev, f"随机排序:{order_cn}")
    #随机第几页
    pages = random.randint(1,50)
    try:
        res = await p.comics(block=cate, order=order,page=pages)
    except Exception as e:
        await bot.send(ev, f"请求失败，{e}")   
        return
    out = res["data"]["comics"]["docs"][0]
    bookid = out["_id"]
    thumb_url = out["thumb"]["fileServer"] + "/static/" + out["thumb"]["path"]
    title = out["title"].strip()
    #去除特殊字符(使用标题作为文件夹名时,不能包含特殊字符)
    pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"
    sub = re.sub(pattern, "-", title)
    author = out["author"]
    try:
        chineseTeam = out["chineseTeam"]
    except:
        chineseTeam = "Unknown"
    comic_info = [f"{sub}：\n作者:{author}\n汉化:{chineseTeam}\n漫画ID:{bookid}"]
    await bot.send(ev, "开始下载和打包")
    try:
        await get_comic_from_id(bookid)
    except Exception as e:
        await bot.send(ev, f"请求失败,{e}") 
        isok=True
        return
    dirname = os.path.join(pica_folder,str(sub))
    output_filename = dirname+".zip"
    zippath = make_zip(source_dir=dirname, output_filename=output_filename)

    bot_friend_list = await bot.get_friend_list()
    fd_list = []
    for fd in bot_friend_list:
        gfd = fd["user_id"]
        fd_list.append(str(gfd))


    comic_folder = os.path.join(pica_folder,sub)
    thbname = sub+"_cover.jpg"
    image_path = os.path.join(comic_folder,thbname)
    thb_path = image(image_path)
    output = make_forward_msg(chain, comic_info, thb_path)
    output2 = make_forward_msg(chain, comic_info)
    if isinstance(ev, PrivateMessageEvent):
        if str(uid) in fd_list:
            await bot.send_private_msg(user_id=int(uid),message=thb_path)
            await bot.send_private_msg(user_id=int(uid),message=comic_info[0])
            try:
                await bot.upload_private_file(user_id=int(uid),file=zippath,name=title+".zip")
                await bot.send(ev, f"消息处理成功, 请注意私聊窗口")                
            except:
                await bot.send(ev, f"消息已响应, 但上传失败.请查看日志窗口")
    else:
        try:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=output)
        except:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=output2)        
        try:
            await bot.upload_group_file(group_id=int(gid),file=zippath,name=title+".zip")           
        except:
            await bot.send(ev, f"消息已响应, 但上传失败.请查看日志窗口")
    if Config.get_config("zhenxun_plugin_pica", "zip_ispwd"):
        ps = Config.get_config("zhenxun_plugin_pica", "zip_password")
        await bot.send(ev, f"压缩包已设置密码为{ps}")     
        


sjz = on_command("指定随机", block=True, priority=5)
#>>>指定分区的随机本子<<<
@sjz.handle()
async def get_pica_cate_random(bot: Bot, ev: Event, msg: Message = CommandArg()):
    chain = []
    global isok
    if not isok:
        await bot.send(ev, "有任务在进行中")
        return    
    if not pica_account or not pica_password:
        await bot.send(ev, "请去config.yaml配置文件设置你的哔咔账号密码")
        return    
    uid = ev.user_id
    if isinstance(ev, GroupMessageEvent):
        gid = ev.group_id
    input5 = msg.extract_plain_text()
    cates = input5.strip()
    fuzzy_word, fuzzy_probability = guess_command(cates, categories)
    if fuzzy_probability == 100:
        pass
    else:
        tips = f"您有{fuzzy_probability}%的可能想搜索“{fuzzy_word}”。"
        await bot.send(ev, tips)    
    od_list = []
    for key in orders.keys():
        od_list.append(key)
    order = random.choice(od_list)
    order_cn = orders[order]
    await bot.send(ev, f"随机排序:{order_cn}")
    pages = random.randint(1,50)
    try:
        res = await p.comics(block=fuzzy_word, order=order,page=pages)
    except Exception as e:
        await bot.send(ev, f"请求失败，{e}")    
        return
    out = res["data"]["comics"]["docs"][0]
    bookid = out["_id"]
    thumb_url = out["thumb"]["fileServer"] + "/static/" + out["thumb"]["path"]
    title = out["title"].strip()
    author = out["author"]
    pattern = r"(\\)|(/)|(\|)|(:)|(\*)|(\?)|(\")|(\<)|(\>)"
    sub = re.sub(pattern, "-", title)
    try:
        chineseTeam = out["chineseTeam"]
    except:
        chineseTeam = "Unknown"
    comic_info = [f"{sub}：\n作者:{author}\n汉化:{chineseTeam}\n漫画ID:{bookid}"]
    await bot.send(ev, "开始下载和打包")
    try:
        await get_comic_from_id(bookid)
    except Exception as e:
        await bot.send(ev, f"请求失败,{e}") 
        isok=True
        return
    dirname = os.path.join(pica_folder,str(sub))
    output_filename = dirname+".zip"
    zippath = make_zip(source_dir=dirname, output_filename=output_filename)

    bot_friend_list = await bot.get_friend_list()
    fd_list = []
    for fd in bot_friend_list:
        gfd = fd["user_id"]
        fd_list.append(str(gfd))


    comic_folder = os.path.join(pica_folder,sub)
    thbname = sub+"_cover.jpg"
    image_path = os.path.join(comic_folder,thbname)
    thb_path = image(image_path)
    output = make_forward_msg(chain, comic_info, thb_path)
    output2 = make_forward_msg(chain, comic_info)
    if isinstance(ev, PrivateMessageEvent):
        if str(uid) in fd_list:
            await bot.send_private_msg(user_id=int(uid),message=thb_path)
            await bot.send_private_msg(user_id=int(uid),message=comic_info[0])
            try:
                await bot.upload_private_file(user_id=int(uid),file=zippath,name=title+".zip")
                await bot.send(ev, f"消息处理成功, 请注意私聊窗口")
                
            except:
                await bot.send(ev, f"消息已响应, 但上传失败.请查看日志窗口")
    else:
        try:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=output)
        except:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=output2)        
        try:
            await bot.upload_group_file(group_id=int(gid),file=zippath,name=title+".zip")
           
        except:
            await bot.send(ev, f"消息已响应, 但上传失败.请查看日志窗口")
    if Config.get_config("zhenxun_plugin_pica", "zip_ispwd"):
        ps = Config.get_config("zhenxun_plugin_pica", "zip_password")
        await bot.send(ev, f"压缩包已设置密码为{ps}")     


sjb = on_command("本地随机", block=True, priority=5)
#>>>本地随机本子<<<
@sjb.handle()
async def get_pica_local_random(bot: Bot, ev: Event):
    if isinstance(ev, GroupMessageEvent):
        gid = ev.group_id
    uid = ev.user_id

    
    filelist = os.listdir(pica_folder)
    random.shuffle(filelist)
    for filename in filelist:
        if str(filename).endswith(".zip"):
            zipname = filename
    
    zippath = f"{pica_folder}/{zipname}"
    bot_friend_list = await bot.get_friend_list()
    fd_list = []
    for fd in bot_friend_list:
        gfd = fd["user_id"]
        fd_list.append(str(gfd))
    print(uid)
    if isinstance(ev, PrivateMessageEvent):
        if str(uid) in fd_list:

            try:
                await bot.upload_private_file(user_id=int(uid),file=zippath,name=zipname)
                await bot.send(ev, f"消息处理成功, 请注意私聊窗口")
            except:
                await bot.send(ev, f"消息已响应,但上传失败了.请注意日志窗口")
                
    else:
        await bot.upload_group_file(group_id=int(gid),file=zippath,name=zipname)
    if Config.get_config("zhenxun_plugin_pica", "zip_ispwd"):
        ps = Config.get_config("zhenxun_plugin_pica", "zip_password")
        await bot.send(ev, f"压缩包已设置密码为{ps}")            
     #冷却计时


stj = on_command("我的收藏", block=True, priority=5)
@stj.handle()
async def get_pica_cate_random(bot: Bot, ev: Event, msg: Message = CommandArg()):
    chain = []
    global isok
    if not isok:
        await bot.send(ev, "有任务在进行中")
        return    
    if not pica_account or not pica_password:
        await bot.send(ev, "请去config.yaml配置文件设置你的哔咔账号密码")
        return    
    my_list = []
    my_list2 = []
    uid = ev.user_id
    j=1
    input3 = msg.extract_plain_text().strip()
    if not msg.extract_plain_text():
        j=1
    else:
        j=int(input3)
    
    
    try:
        comment = await p.my_favourite()
        comment = await comment.json()
    except Exception as e:
        await bot.send(ev, f"请求失败，{e}")         
        return  
    comment_js = comment
    page_num = comment_js["data"]["comics"]["pages"]
    await bot.send(ev, f"开始查看第{j}页，共{page_num}页")
    comment = await p.my_favourite(page=j,order=Order_Default)
    comment = await comment.text()
    com_js = json.loads(comment)
    try:
        favors,favors2 = await get_random_favorite(com_js)
    except Exception as e:
        await bot.send(ev, f"请求失败，{e}")  
        isok=True
        return  
    #遍历我的收藏,并将相关信息放入查询列表
    my_list.extend(favors)
    my_list2.extend(favors2)
    out = custom_forward_msg(my_list, bot.self_id)
    out2 = custom_forward_msg(my_list2, bot.self_id)
    #random.shuffle(my_list)
    #lipr = int(random.randint(0,len(my_list)))
    #打乱列表顺序后,随机下标取值
    if isinstance(ev, GroupMessageEvent):
        try:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=out)
        except:
            await bot.send_group_forward_msg(group_id=ev.group_id, messages=out2)
    else:
        await bot.send_private_forward_msg(user_id=ev.user_id, messages=out)
    await bot.send(ev, "请使用 [看pica 漫画id] 来查看")
     #冷却计时

    #todo:随机获取一篇漫画后,直接发送



# 获取文件目录大小
def getdirsize(dir):
    size = 0
    for root, dirs, files in os.walk(dir):
        size += sum([getsize(join(root, name)) for name in files])
    return size

def countFile(dir):
    tmp = 0
    for item in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, item)):
            tmp += 1
        else:
            tmp += countFile(os.path.join(dir, item))
    return tmp
    
sc = on_command("清理哔咔缓存",aliases={"清理pika缓存", "清理pica缓存"}, block=True, permission=SUPERUSER, priority=5)
@sc.handle() 
async def dele_pica(bot: Bot, ev: Event):
    try:
        deleFile(str(pica_folder))
        await bot.send(ev, f"清理完成") 
    except Exception as e:
        await bot.send(ev, f"清理失败,{e}") 
        return
        
def deleFile(dir):
    for item in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, item)):
            os.remove(os.path.join(dir, item))
        else:
            deleFile(os.path.join(dir, item))
    
jc = on_command("检查pica", aliases={"检查哔咔", "检查pika"}, block=True, permission=SUPERUSER, priority=5)
@jc.handle()
async def check_pica(bot: Bot, ev: Event):
    if not os.path.exists(pica_folder):
        os.mkdir(pica_folder)
    shots_all_num = countFile(str(pica_folder)) #同上
    shots_all_size = getdirsize(pica_folder)  #同上
    all_size_num = '%.3f' % (shots_all_size / 1024 / 1024)
    info_before = f"当前目录有{shots_all_num}个文件，占用{all_size_num}Mb"
    await bot.send(ev, info_before)
    try:
        await p.login(pica_account, pica_password)
        ts = await p.comics(order=Order_Default)
        pic2_ck = ts["code"]
        async with aiohttp.ClientSession() as session:
            rs = await session.get(url="https://storage1.picacomic.com/static/653cc9e0-1548-4cc3-bba0-d6e2e1bd9c18.jpg", proxy=proxy, timeout=30)
        await bot.send(ev, f"pic2API连通测试:{pic2_ck}")
        await bot.send(ev, f"PicAcg资源连通测试:{rs.status}")
    except Exception as e:
        await bot.send(ev,f"连接失败{e}")


'''
原项目地址：
作者主页：https://github.com/Soung2279
'''
