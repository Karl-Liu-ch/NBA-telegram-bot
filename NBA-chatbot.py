# Import necessary modules
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config

# Create a trainer that uses this config
trainer = Trainer(config.load("config_spacy.yml"))

# Load the training data
training_data = load_data('NBA-api.json')

# Create an interpreter by training the model
interpreter = trainer.train(training_data)

# 由于api中的球队搜寻需要连网搜索不方便，并且球队内容不是很多，因此我将球队信息用Datebase_team.py录入为teams.db的数据库进行查询操作
import sqlite3
conn = sqlite3.connect('teams.db', check_same_thread=False) # 由于telegram bot需要多线程查询数据库，因此要加上'check_same_thread=False'
c = conn.cursor()

import requests
# 设置proxy
from telebot import apihelper
apihelper.proxy = {'http':'http://127.0.0.1:1087'}

import json
import random
import spacy
nlp = spacy.load('en_core_web_md')
import re
rules = {'team_fullname': ['The full name of this team is {0}',
                           'Here is the full name, {0}',
                           "Let me tell you, the full name is {0}"],
         'team_nickname': ['The nick name of this team is {0}',
                           "People always call it {0}",
                           'Let me see, it is {0}',],
         'team_location': ['Got the location! It is located in {0}.',
                           'I found that the location of this team is {0}'],
         'team_shortname': ["The short name is {0}",
                            'I\'ve found the shorname, it is {0}',
                            'Hey, it is {0}',],
         'team_Id':[
             'Got the team ID! It is {0}.',
             'I found that the ID of this team is {0}'
         ]
         }

import telebot
bot = telebot.TeleBot("990468307:AAEx1b6jaZ8oAfIvjskSYBDi-hhiSWl_1jc")
# 定义需要更新的实体等为外部变量
name = None
firstname = None
params = {}
last_entity = ''
need_lastname = 0
# bot回复函数
@bot.message_handler(commands=['start'])
@bot.message_handler()
# 分析message中的内容
def analysis_messages(message):
    global last_entity
    global need_lastname
    global firstname
    global lastname
    value = None
    doc = nlp(message.text)
    data = interpreter.parse(message.text)
    # 如果意图为greet，则回复"Hi I'm a NBA robot, can I help?"
    if data['intent']['name'] == 'greet':
        bot.reply_to(message, "Hi I'm a NBA robot, can I help?")
    # 如果意图为bye，则回复"You are welcome!"
    elif data['intent']['name'] == 'bye':
        bot.reply_to(message, "You are welcome!")
    elif doc.ents != ():
        for ent in doc.ents:
            # 如果message中有人名，则自动进行play_info的回复
            if ent.label_ == 'PERSON':
                # 不需要lastname进行球员区分
                if need_lastname == 0:
                    intent = 'player_info'
                    name = ent.text
                    if ' ' in name:
                        firstname = re.split(r'\s',name)[0]
                        lastname = re.split(r'\s',name)[1]
                    else:
                        firstname = name
                        lastname = None
                    value = firstname
                    print(firstname)
                    params['firstName'] = value
                    print(intent, value)
                    # 如果意图为查询球员信息，则进行球员信息的回复
                    responses, need_lastname = send_message_player(intent, value, lastname)
                    bot.reply_to(message, responses)
                else:
                    # 需要lastname对相同firstname的球员的区分
                    lastname = re.split(r'\s',ent.text)[1]
                    value = params['firstName']
                    intent = 'player_info'
                    responses, need_lastname = send_message_player(intent, value, lastname)
                    bot.reply_to(message, responses)
            # 如果message中存在ORG类型的词语，则进行球队信息的查找
            if ent.label_ == 'ORG':
                intent = data['intent']['name']
                if data['entities'] != []:
                    value = data['entities'][0]['value'].capitalize()
                    entity = data['entities'][0]['entity']
                    params[entity] = value
                    last_entity = entity
                    print(last_entity)
                elif last_entity != '':
                    value = params[last_entity]
                print(intent, value)
                responses = send_message_team(intent, value)
                bot.reply_to(message, responses)
    # 当球队实体需要继承时，进行意图识别并将之前的球队作为实体的值
    else:
        intent = data['intent']['name']
        if data['entities'] != []:
            value = data['entities'][0]['value'].capitalize()
            entity = data['entities'][0]['entity']
            params[entity] = value
            last_entity = entity
            print(last_entity)
        elif last_entity != '':
            value = params[last_entity]
        print(intent, value)
        responses = send_message_team(intent, value)
        bot.reply_to(message, responses)
@bot.message_handler()
def send_message_player(intent, value, lastname):
    main_intent = 'players'
    url = "https://api-nba-v1.p.rapidapi.com/players/firstName/"+value
    headers = {
        'x-rapidapi-host': "api-nba-v1.p.rapidapi.com",
        'x-rapidapi-key': "bb1964a290mshf67b124cec9c396p1b74ddjsnd9930eb00087"
    }
    need_lastname = 0
    response = requests.request("GET", url, headers=headers)
    Dict = json.loads(response.text)['api']['players']
    # 如果没有搜索到此球员，则回复there is no + firstname
    if len(Dict) == 0:
        respond = "there is no {}".format(firstname)
        return respond, need_lastname
    # 如果有一个满足条件的球员，则回复此球员的信息
    elif len(Dict) == 1:
        ID = Dict[0]['teamId']
        query = "SELECT * FROM teams WHERE teamid = '{}'".format(ID)
        c.execute(query)
        team = [r[0] for r in c.fetchall()]
        string = "I found {} {}, he is from {}, and he is in {} now".format(value, Dict[0]['lastName'], Dict[0]['country'], *team)
        respond = string
        need_lastname = 0
        return respond, need_lastname
    #如归相同firstname的球员有多个，则需要lastname进行区分
    elif len(Dict)>1 and lastname != None:
        for dict in Dict:
            if dict['lastName'] == lastname:
                ID = dict['teamId']
                query = "SELECT * FROM teams WHERE teamid = '{}'".format(ID)
                c.execute(query)
                team = [r[0] for r in c.fetchall()]
                respond = "I found {} {}, he is from {}, and he is in {} now".format(value, lastname, dict['country'], *team)
                need_lastname = 0
                return respond, need_lastname
    elif len(Dict)>1 and lastname == None:
        need_lastname = 1
        respond = "there are several {}, can you give me the full name?".format(firstname)
        return respond, need_lastname
    # 如果没有，则回复没有找到球员
    else:
        respond = "there is no {}".format(firstname)
        return respond, need_lastname
# 对球队信息进行回复
@bot.message_handler()
def send_message_team(intent, value):
    # 分析用户是对球队的哪个信息进行teams.db数据库查询
    query = "SELECT * FROM teams WHERE nickname = '{}'".format(value)
    c.execute(query)
    if intent == 'team_fullname':
        ans = [r[0] for r in c.fetchall()]
    elif intent == 'team_nickname':
        ans = [r[1] for r in c.fetchall()]
    elif intent == 'team_location':
        ans = [r[2] for r in c.fetchall()]
    elif intent == 'team_shortname':
        ans = [r[3] for r in c.fetchall()]
    else:
        ans = [r[4] for r in c.fetchall()]
    respond = random.choice(rules[intent]).format(*ans)
    return respond

if __name__ == '__main__':
    bot.polling()
