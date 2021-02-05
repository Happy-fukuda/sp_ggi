#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gcp_texttospeech.srv import TTS
#音声認識
from voice_common_pkg.srv import SpeechToText

import nltk
import pickle
import rospy
import Levenshtein as lev
from voice_common_pkg.srv import GgiLearning
from voice_common_pkg.srv import GgiLearningResponse

file='/home/athome/catkin_ws/src/voice_common_pkg/config' #作成場所の指定


class GgiinStruction:
    def __init__(self):

        #保存ファイルの初期化
        with open(file+'/object_file.pkl',"wb") as f:
            dictionary={'object_name':[],'object_feature':[],
                        'place_name':[],'place_feature':[]}
            pickle.dump(dictionary, f)
        #google speech to textが認識しやすいよう設定する単語をリスト化
        with open(file+'/place_name','r') as f:
            self.object_template=[line.strip() for line in f.readlines()]
        with open(file+'/place_name','r') as c:
            self.place_template=[line.strip() for line in c.readlines()]
        #pickleファイルに保存するデータを保存するリスト
        self.name=[]
        self.feature=[]
        print("Waiting for stt and tts")
        rospy.wait_for_service('/tts')
        rospy.wait_for_service('/stt_server')
        print("server is ready")
        self.stt=rospy.ServiceProxy('/stt_server',SpeechToText)
        self.server=rospy.Service('/ggi_learning',GgiLearning,self.register_object)
        self.tts=rospy.ServiceProxy('/tts', TTS)

    #オブジェクト認識と登録
    def register_object(self,req):
        end=False
        self.tts("please say the object.")
        #ものの登録
        while 1:
            if not end:
                #short_str:短い単語を認識しやすくする　context_phrases:認識しやすくしたい単語のリスト　boost_value:登録した単語の認識度合いを調節
                string=self.stt(short_str=True,
                    context_phrases=self.object_template.append('finish　training'),
                    boost_value=13.0)

                #finish trainingと認識したときpickleファイルに保存してリストを初期化
                if  lev.distance(string.result_str, 'finish　training')/(max(len(string.result_str), len('finish　training')) *1.00)<0.3:
                    self.save_name('' , True)
                    self.name=[]
                    self.feature=[]
                    break

                self.tts(string.result_str + ' is this OK?')

            recognition = self.stt(short_str=True,context_phrases=['yes','no','again'],
                    boost_value=15.0)
            #認識した内容で良いかを確認
            #yesのときリストにその単語を追加
            if 'yes' in recognition.result_str:
                self.save_name(string.result_str , True,add=False)
                end=False
                self.tts('next')
            #noのときリストに追加しない
            elif 'no' in recognition.result_str:
                self.tts('please one more time')
                end=False
            #認識した内容を聞き取れなかったときもう一度発話
            elif 'again' in recognition.result_str:
                self.tts(string.result_str +' is this OK?')
                end=True

        self.tts('Please tell me the place.')
        #場所の登録
        while 1:
            if not end:

                string=self.stt(short_str=True,
                    context_phrases=self.place_template,
                    boost_value=13.0)
                self.tts(string.result_str +' Is this OK?')

            recognition = self.stt(short_str=True,context_phrases=['yes','no','again'],
                    boost_value=15.0)

            if 'yes' in recognition.result_str:
                res=self.save_name(string.result_str , False)
                break

            elif 'no' in recognition.result_str:
                self.tts('please one more time')
                end=False

            elif 'again' in recognition.result_str:
                self.tts(string.result_str +' Is this OK?')
                end=True

        self.feature=[]
        self.name=[]


        return GgiLearningResponse(location_name=res)



    #保存  s=string ob=name or place addはpickleファイルに保存するか否か
    def save_name(self,s,ob,add=True):
        #形態素解析を行う
        split=nltk.word_tokenize(s)
        for h in range(len(split)):
            #theだと形容詞に分解されない
            if split[h]=='the':
                split[h]='a'i
        pos = nltk.pos_tag(split)  #品詞分解

        for i in range(len(pos)):
            #形容詞であれば特徴に追加
            if pos[i][1]=='JJ':
                self.feature.append(pos[i][0])
            #名詞であれば名前に追加
            elif 'NN' in pos[i][1]:
                self.name.append(pos[i][0])
        if add:
            with open(file+'/object_file.pkl','rb') as web:
                dict=pickle.load(web)
            #オブジェクトの登録
            if ob:
                dict['object_name'].append(self.name)
                dict['object_feature'].append(self.feature)
                with open(file+'/object_file.pkl','wb') as f:
                    pickle.dump(dict, f)
            #場所の登録
            else:
                dict['place_name'].append(self.name)
                dict['place_feature'].append(self.feature)
                with open(file+'/object_file.pkl','wb') as f:
                    pickle.dump(dict, f)
                if dict['place_feature'][len(dict['place_feature'])-1]:
                    str=' '.join(dict['place_feature'][len(dict['place_feature'])-1])+' '+' '.join(dict['place_name'][len(dict['place_name'])-1])
                else:
                    str=' '.join(dict['place_name'][len(dict['place_name'])-1])
                print(dict)
                return str


if __name__=='__main__':
    rospy.init_node('ggi_learning')
    GgiinStruction()
    rospy.spin()
