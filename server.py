#!/usr/bin/env python3

import threading
import time
import datetime
import zoneinfo
import asyncio
import cv2
from aiohttp import web
import json
import ctypes
import pyaudio
import requests
import io


#util
def ut2Dt(unixtime):
    #return datetime.datetime.fromtimestamp(unixtime/1000,tz=datetime.timezone.utc)
    return datetime.datetime.fromtimestamp(unixtime/1000,tz=zoneinfo.ZoneInfo(key='Asia/Tokyo'))
def ut2DtUtStr(unixtime):
    return f"{ut2Dt(unixtime)}({unixtime})"

serverUpUnixTime=int(time.time()*1000)
validAlarmBounce=int(time.time()*1000)
validStopAlrmBounce=int(time.time()*1000)

cgi_imgupload_url = "https://cgi.u.tsukuba.ac.jp/~s2520579/upload.py"
cgi_cmdfetch_url = "https://cgi.u.tsukuba.ac.jp/~s2520579/fetch_rc_control.py"
cgi_alarmtimefetch_url = "https://cgi.u.tsukuba.ac.jp/~s2520579/fetch_timer_date.py"
cgi_stopalarmfetch_url = "https://cgi.u.tsukuba.ac.jp/~s2520579/fetch_stop_alarm.py"






# グローバル変数とロック
alarm_mode = False
rc_command = 0  # 0: stop, 1: forward, 2: backward, 3: right, 4: left
alarm_set = False
alarm_hour = 0
alarm_minute = 0
face_seen = False

alarm_unixtime=0

# 個別ロック
alarm_mode_lock = threading.Lock()
rc_command_lock = threading.Lock()
alarm_time_lock = threading.Lock()
alarm_set_lock = threading.Lock()

#モーター操作ライブラリ読み込み
control_motor = ctypes.cdll.LoadLibrary("./ccode/control_motor.so")
control_motor.setup()


# ------------------- CGIサーバーに写真を送信するスレッド -------------------
def send_video_via_cgi():
    global camera
    global cgi_imgupload_url
    while True:
        if not camera.isOpened():
            print("カメラが開けません")
        ret, frame = camera.read()

        if not ret:
            print("画像のキャプチャに失敗しました")

        # メモリ上にJPEGエンコード
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success:
            print("画像のエンコードに失敗しました")

        # バイトIOに変換
        image_bytes = io.BytesIO(encoded_image.tobytes())

        # multipart/form-data形式で送信
        files = {'file': ('image.jpg', image_bytes, 'image/jpeg')}
        response = requests.post(cgi_imgupload_url, files=files)

        #print("サーバーの応答:", response.text)
        time.sleep(0.03)


def get_cmd_via_cgi():
    global rc_command, rc_command_lock
    while(True):
        response=requests.get(cgi_cmdfetch_url)
        command=response.json()["message"]
        cmdSetUnixtime=response.json()["unixtime"]
        if(cmdSetUnixtime>serverUpUnixTime):
            with rc_command_lock:
                if command == 'forward':
                    rc_command = 1
                elif command == 'backward':
                    rc_command = 2
                elif command == 'right':
                    rc_command = 3
                elif command == 'left':
                    rc_command = 4
                elif command == 'stop':
                    rc_command = 0
                print(f"in:{rc_command}")
        else : 
            pass
            #print(f"cmdSetUnixtime>serverUpUnixTime={cmdSetUnixtime>serverUpUnixTime}")
        time.sleep(0.1)

def get_alarmtime_via_cgi():
    global alarm_unixtime, alarm_set,validAlarmBounce
    while(True):
        response=requests.get(cgi_alarmtimefetch_url)
        res_alarmUnixTime=response.json()["alarmUnixTime"]
        alarmSetUnixtime=response.json()["setUnixTime"]
        print(f"ServerState/ alarmUnixTime : {ut2DtUtStr(res_alarmUnixTime)}, setUnixTime : {ut2DtUtStr(alarmSetUnixtime)}")
        with alarm_time_lock, alarm_set_lock:
            alarm_set=(alarmSetUnixtime>validAlarmBounce)
            alarm_unixtime=res_alarmUnixTime
            if(alarm_set):
                print(f"set alarm:{ut2DtUtStr(alarm_unixtime)}")
        time.sleep(10)

def get_stopalarm_via_cgi():
    global alarm_mode_lock, alarm_mode,validStopAlrmBounce
    while(True):
        response=requests.get(cgi_stopalarmfetch_url)
        stopalarmUnixTime=response.json()["unixTime"]
        print(f"ServerState/stop alarm:{ut2DtUtStr(stopalarmUnixTime)}")
        if (stopalarmUnixTime > validStopAlrmBounce) and alarm_mode :
            with alarm_mode_lock :
                alarm_mode=False
                validStopAlrmBounce=stopalarmUnixTime
                print("Alram Stopped")
        time.sleep(10)
    

# ------------------- 車体制御スレッド -------------------
def vehicle_control_thread():
    global face_seen, rc_command
    while True:
        with alarm_mode_lock, rc_command_lock:
            is_alarm_mode = alarm_mode
            command = rc_command

        if is_alarm_mode:
            with rc_command_lock:
                rc_command = 0  # stop
            if not face_seen:
                found, face_pos, face_area = detect_face()
                if found:
                    if face_area < 5000:
                        if face_pos > 0.7:
                            rotate_right()
                        elif face_pos < 0.3:
                            rotate_left()
                        else:
                            move_forward()
                    else:
                        attract_attention()
                        face_seen = True
                else:
                    rotate_right()
            else:
                attract_attention()
        else:
            face_seen = False
            if command == 1:
                move_forward()
            elif command == 2:
                move_backward()
            elif command == 3:
                rotate_right()
            elif command == 4:
                rotate_left()
            elif command == 0:
                stop()
            else:
                print("Unknown command")
        time.sleep(0.1)
    

# ------------------- アラーム確認スレッド -------------------
def alarm_check_thread():
    global alarm_set, alarm_mode, alarm_hour, alarm_minute,alarm_unixtime,validAlarmBounce,validStopAlrmBounce
    while True:
        now = datetime.datetime.now(tz=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=9)))  # 日本時間に変換
        nowunixtime = int(time.time()*1000)
        with alarm_set_lock, alarm_mode_lock, alarm_time_lock:
            print (f"現在時刻: {ut2DtUtStr(nowunixtime)}")
            if alarm_set and (nowunixtime>alarm_unixtime):
                print("Enable alarm")
                alarm_mode = True
                alarm_set = False
                validAlarmBounce=nowunixtime
                validStopAlrmBounce=nowunixtime
            print(f"アラームON: {alarm_set}, アラーム時刻: {ut2DtUtStr(alarm_unixtime)}")
        time.sleep(10)







# ------------------- モーター・顔検出ダミー関数 -------------------
def move_forward():control_motor.control_motor(1) #print("前進")
def move_backward():control_motor.control_motor(2) #print("後退")
def rotate_left():control_motor.control_motor(4) #print("左回転")
def rotate_right():control_motor.control_motor(3) #print("右回転")
def stop(): control_motor.control_motor(0) #print("停止")
def attract_attention(): print("気を引く")
def detect_face():
    import random
    found = random.choice([True, False])
    pos = random.uniform(0.0, 1.0)
    area = random.randint(1000, 10000)
    return found, pos, area

#カメラの設定
camera = cv2.VideoCapture(1)
camera.set(cv2.CAP_PROP_FPS, 30)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
#音声ストリームの設定
CHUNK=1024
FORMAT=pyaudio.paInt16
CHNNELS=1
RATE=16000
audio=pyaudio.PyAudio()
inputstream=audio.open(format=pyaudio.paInt16,channels=1,rate=RATE,input=True)
# ------------------- 起動 -------------------
if __name__ == '__main__':
    thrd1=threading.Thread(target=vehicle_control_thread, daemon=True)
    thrd2=threading.Thread(target=alarm_check_thread, daemon=True)
    thrd3=threading.Thread(target=get_cmd_via_cgi,daemon=True)
    thrd4=threading.Thread(target=get_alarmtime_via_cgi,daemon=True)
    thrd5=threading.Thread(target=get_stopalarm_via_cgi,daemon=True)
    thrd6=threading.Thread(target=send_video_via_cgi,daemon=True)
    thrds= [thrd1,thrd2,thrd3,thrd4,thrd5,thrd6]
    for athrd in thrds:
        athrd.start()
    for athrd in [thrd1,thrd2,thrd3,thrd4,thrd5,thrd6]:
        athrd.join()
    
    
    #app=web.Application()
    #app.add_routes([web.get("/ws",stream_image),
                    #web.post("/set_alarm", handle_set_alarm), 
                    #web.post("/stop_alarm", handle_stop_alarm),
                    #web.post("/rc_control", rc_control),
                    #web.get("/video", stream_image),
                    #web.get("/audio", steram_sound)
                    #])
    #web.run_app(app)


