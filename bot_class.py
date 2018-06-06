# -*- coding: utf-8 -*-
"""
Created on Tue Jun  5 17:19:49 2018

@author: DataAnt
"""

from rocketchat.api import RocketChatAPI
import requests 
from datetime import datetime, timedelta
import pytz
import pandas as pd
from collections import deque
import time
import threading

room_id = 'Z4fmpBJ4cxkwuyXjF'


def BotApi(text_in):
    """
    调用第三方聊天接口，这里使用青云客的免费接口，向接口输入文本，返回一段应答的文本
    :text_in: 输入文本内容
    """
    resp = requests.get("http://api.qingyunke.com/api.php", 
                        {'key': 'free', 'appid': 0, 'msg': text_in})  
    resp.encoding = 'utf8'  
    resp = resp.json()  
    text_out = resp['content']
    text_out = text_out.replace('菲菲', '小智')
    return text_out


class Bot():
    """
    创建一个聊天机器人
    :RoomsDictUpdate: 更新聊天室字典
    :SetRoom: 指定使用本聊天机器人的聊天室
    """
    def __init__(self, username, password, domain):
        # 设置队列，记录最近答复过的消息id，避免重复回答同一条消息，假定1分钟内@bot的人次不超过100
        self.replied_queue = deque([], maxlen=100)
        # 设置rocketchat的api参数
        self.api = RocketChatAPI(settings={'username': username, 
                                           'password': password,
                                           'domain': domain})
    
    
    def _RoomsDict(self, _class='private'):
        """
        获取聊天房间的字典，字典的key为聊天室名，value为聊天室id，聊天室不存在重名
        :_class: 聊天室类型
            - private: 私有聊天室
            - public: 公共聊天室
        """
        if _class == 'private':
            rooms = self.api.get_private_rooms()
        elif _class == 'public':
            rooms = self.api.get_public_rooms()
        else:
            raise ValueError('请指定正确的_class')
        fun = lambda d:tuple(d.values())
        rooms = {fun(d)[0]:fun(d)[1] for d in rooms}
        return rooms
    
    
    def RoomsDictUpdate(self):
        private_rooms = self._RoomsDict('private')
        public_rooms = self._RoomsDict('public')
        self.rooms_dict = dict(private_rooms, **public_rooms)
    
    def SetRoom(self, room_name):
        try:
            self.room_id = self.rooms_dict[room_name]
        except KeyError:
            raise KeyError('房间名<%s>不存在' % room_name)
    
       
    def History(self, oldest=None):
        """
        获取当前聊天室的历史聊天记录
        """
        history = self.api.get_private_room_history(self.room_id, oldest=oldest)
        if history['success']:
            history_msgs = history['messages']
        return history_msgs
  

    def NewMsgs(self):
        """
        获取指定聊天室最近60秒的历史消息
        """
        begin_CCT = datetime.now() + timedelta(seconds=-10)
        begin_UTC = begin_CCT.astimezone(pytz.timezone('UTC'))
        oldest = begin_UTC.strftime('%Y-%m-%dT%H:%M:%SZ')
        msgs = self.History(oldest=oldest)
        msgs.reverse() # 逆序排列
        return msgs
    
    
    def reply(self, ser):
        if ser['_id'] not in self.replied_queue:
            self.replied_queue.append(ser['_id'])
            text_out = BotApi(ser['msg'])
            text_out += ' @%s' % ser['name']
            self.api.send_message(text_out, room_id)
        
    
    def _Msgs2Bot(self, msgs: list):
        """
        解析获取到的聊天记录，筛选出@xbot的记录，保留'_id'，'name'，'msg'这三个字段
        """
        if len(msgs) > 0:
            df_msgs = pd.DataFrame(msgs)
            df_msgs['name'] = df_msgs['u'].map(lambda x:x['username'])
            df_msgs_select = df_msgs[['_id', 'name', 'msg']]
            self.msgs_at_bot = df_msgs_select[df_msgs_select['msg'].str.startswith('@xbot') | 
                                              df_msgs_select['msg'].str.endswith('@xbot')]
            self.msgs_at_bot.apply(self.reply, axis=1)


    def Msgs2Bot(self):
        self._Msgs2Bot(self.NewMsgs())
        
        
    def Run(self):
        while True:
            self.Msgs2Bot()
            time.sleep(0.5)
            
                

if __name__ == '__main__':
    bot = Bot('xbot', 'xxxxxx', 'xxxxxxx')
    bot.RoomsDictUpdate()
    #bot.SetRoom(list(bot.rooms_dict.keys())[0])
    bot.SetRoom('bot测试')
    bot.Run()