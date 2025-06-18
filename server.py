#!/usr/bin/env python3

import threading
import time
import datetime
import asyncio
import cv2
from aiohttp import web
import json
import ctypes
import pyaudio





# グローバル変数とロック
alarm_mode = False
rc_command = 0  # 0: stop, 1: forward, 2: backward, 3: right, 4: left
alarm_set = False
alarm_hour = 0
alarm_minute = 0
face_seen = False

# 個別ロック
alarm_mode_lock = threading.Lock()
rc_command_lock = threading.Lock()
alarm_time_lock = threading.Lock()
alarm_set_lock = threading.Lock()

#モーター操作ライブラリ読み込み
control_motor = ctypes.cdll.LoadLibrary("./ccode/control_motor.so")
control_motor.setup()


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
    global alarm_set, alarm_mode, alarm_hour, alarm_minute
    while True:
        now = datetime.datetime.now(tz=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=9)))  # 日本時間に変換
        with alarm_set_lock, alarm_mode_lock, alarm_time_lock:
            print (f"現在時刻: {now.hour}:{now.minute}")
            print(f"アラーム設定: {alarm_set}, 時刻: {alarm_hour}:{alarm_minute}")
            if alarm_set and (now.hour > alarm_hour or (now.hour == alarm_hour and now.minute >= alarm_minute)):
                alarm_mode = True
                alarm_set = False
        time.sleep(10)

# ------------------- リクエスト処理スレッド群 -------------------
async def stream_image(request):
	ws=web.WebSocketResponse()
	await ws.prepare(request)
	while(True):
		success, frame = camera.read()
		if(success):
			_,buffer=cv2.imencode(".jpg",frame)
			sentbytes=buffer.tobytes()
			try:
				#print(f"送信バイト数: {len(sentbytes)}")
				await ws.send_bytes(sentbytes)
			except Exception as e:
				print(f"WebSocketエラー: {e}")
				break
	return ws

async def steram_sound(request):
    ws=web.WebSocketResponse()
    await ws.prepare(request)
    while(True):
        sound_chunk=inputstream.read(CHUNK,exception_on_overflow=False)
        #サウンドをWebSocketで送信
        try:
            await ws.send_bytes(sound_chunk)
        except Exception as e:
            print(f"WebSocket(Sound)エラー: {e}")
            break


async def rc_control(request):
    global  rc_command
    data = await request.post()
    command = data.get("command")
    print(f"rc_control called:{command}")
    if command in ["forward", "backward", "left", "right", "stop"]:
        
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
        return web.Response(text="OK")
    else:
        return web.Response(text="Invalid command", status=400)



# ------------------- aiohttp サーバー -------------------
async def handle_set_alarm(request):
    global alarm_hour, alarm_minute, alarm_set
    data = await request.json()
    with alarm_time_lock, alarm_set_lock:
        alarm_hour = int(data['hour'])
        alarm_minute = int(data['minute'])
        alarm_set = True
    return web.Response(text='Alarm set')

async def handle_stop_alarm(request):
    global alarm_mode
    with alarm_mode_lock:
        alarm_mode = False
    return web.Response(text='Alarm stopped')


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
camera = cv2.VideoCapture(0)
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
    threading.Thread(target=vehicle_control_thread, daemon=True).start()
    threading.Thread(target=alarm_check_thread, daemon=True).start()
    
    app=web.Application()
    app.add_routes([web.get("/ws",stream_image),
                    web.post("/set_alarm", handle_set_alarm), 
                    web.post("/stop_alarm", handle_stop_alarm),
                    web.post("/rc_control", rc_control),
                    web.get("/video", stream_image),
                    web.get("/audio", steram_sound)])
    web.run_app(app)

