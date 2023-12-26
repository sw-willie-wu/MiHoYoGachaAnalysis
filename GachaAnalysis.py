import os
import json
import time
import subprocess
from pathlib import Path
from urllib.parse import unquote

import requests


class GachaAnalysis:

    def __init__(self):
        self.game_info = {
            '1': {
                'name': '原神',
                'name_en': 'genshin',
                'log_file': Path.home() / 'AppData/LocalLow/miHoYo/Genshin Impact/output_log.txt',
                'keyword': 'Warmup file',
                'gacha_type': {
                    '100': '新手祈願',
                    '200': '常駐祈願',
                    '301': '角色活動祈願',
                    '302': '武器活動祈願'
                },
                'normal_character': ['迪盧克','提納里','琴','莫娜','七七','刻晴','迪希雅'],
                'normal_weapon':['天空之翼','天空之脊','四風原典','天空之卷','狼的末路','天空之傲','風鷹劍','天空之刃']
            },
            '2': {
                'name': '崩壞：星穹鐵道',
                'name_en': 'star_rail',
                'log_file': Path.home() / 'AppData/LocalLow/Cognosphere/Star Rail/Player.log',
                'keyword': 'Loading player data from ',
                'gacha_type': {
                    '11': '角色活動躍遷',
                    '12': '光錐活動躍遷',
                    '1': '常駐躍遷',
                    '2': '新手躍遷'
                },
                'normal_character': ['布洛妮婭','白露','傑帕德','姬子','瓦爾特','克拉拉','彥卿'],
                'normal_weapon':['銀河鐵道之夜','無可取代的東西','以世界之名','但戰鬥還未結束','制勝的瞬間','如泥酣眠','時節不拘']
            },
        }


    def select_game(self):
        while True:
            print('請選擇要分析的遊戲 (預設為 1 )：')
            for key, value in self.game_info.items():
                print(f"  ({key}) {value['name']}")
            select = input('\n選擇：')
            if not select:
                select = '1'
            if select in ['1', '2']:
                break
            else:
                os.system('cls')
                print('\033[31m輸入錯誤，請重新確認！\033[0m\n')
        self.game = self.game_info[select]
        print(f"已選擇：{self.game['name']}")


    def find_game_path(self):
        log_path = self.game['log_file']
        with open(log_path, 'r', encoding='utf8') as f:
            for line in f.readlines():
                if self.game['keyword'] in line:
                    game_path = line.split(self.game['keyword'])[-1]
                    if self.game['name'] == '原神':
                        game_path = Path(game_path.split('StreamingAssets')[0][1:])
                    else:
                        game_path = Path(game_path).parent
                    break
        self.game['path'] = game_path


    def read_data2(self):
        data2_path_list = list(self.game['path'].glob('webCaches/*/Cache/Cache_Data/data_2'))
        gacha_log_path = data2_path_list[0]
        for fp in data2_path_list:
            if gacha_log_path.parent.parent.parent.name < fp.parent.parent.parent.name:
                gacha_log_path = fp
        tmp_data = Path() / 'data_2'
        cmd = f'''Copy-Item "{gacha_log_path}" "{tmp_data}"'''
        completed = subprocess.run(["powershell", "-Command", cmd], capture_output=True)

        with open(tmp_data, 'rb') as f:
            content = f.read().decode(errors='ignore')
            for line in content.split('\n'):
                if 'getGachaLog' in line:

                    api_url = line.split('1/0/')[-1].split('\0')[0]
                    self.api_domain = api_url.split('?')[0]
                    self.payload = dict()
                    
                    for elem in api_url[api_url.find('?')+1:].split('&'):
                        k, v = elem.split('=')
                        self.payload[k] = unquote(v)
                    
                    res = requests.get(self.api_domain, params=self.payload)
                    try:
                        data = json.loads(res.content.decode('utf8'))['data']
                    except:
                        data = None                    
                    
                    if data:
                        self.payload['size'] = 10
                        break
        tmp_data.unlink()


    def get_gacha_log(self):
        datas = dict()
        elem = None
        uid = None
        for key in self.game['gacha_type'].keys():
            datas[key] = []
            page = 1
            self.payload['gacha_type'] = key
            self.payload['end_id'] = 0
            res = requests.get(self.api_domain, params=self.payload)
            data = json.loads(res.content.decode('utf8'))['data']
            if not data:
                print('\n查無資料！請多翻幾頁歷史紀錄以利查詢')
                return
            else:
                query_list = json.loads(res.content.decode('utf8'))['data']['list']
                while len(query_list) > 0:
                    print(f"讀取{self.game['gacha_type'][key]}紀錄... 第{page:03d}頁", end='\r')
                    for elem in query_list:
                        uid = elem['uid']
                        del elem['uid']
                        datas[key].append(elem)
                    self.payload['end_id']  = elem['id']
                    time.sleep(0.3)
                    res = requests.get(self.api_domain, params=self.payload)
                    query_list = json.loads(res.content.decode('utf8'))['data']['list']
                    page += 1
                print(f"讀取{self.game['gacha_type'][key]}完畢... 共{page-1:03d}頁")
        
        if not elem:
            print('無抽卡記錄！')
            return None
        
        else:
            self.player_id = uid
            with open(f"{self.game['name_en']}_{self.player_id}.json", 'a', encoding='utf8') as jf:
                try:
                    old_datas = json.loads(jf)
                except:
                    old_datas = {k:[] for k in self.game['gacha_type']}

            for key in datas:
                print(f"\n----{self.game['gacha_type'][key]}----")

                if len(old_datas[key]) > 0:
                    last_time = old_datas[key][-1]['time']
                else:
                    last_time = '2023-04-26 00:00:00'
                
                for record in datas[key][::-1]:
                    if record['time'] > last_time:
                        old_datas[key].append(record)
                
                count = 0
                info = ''
                
                for elem in old_datas[key]:
                    count += 1
                    if elem['rank_type'] == '5':
                        color = '\033[32m' if count < 30 else '\033[33m' if count < 60 else '\033[31m'
                        if self.check_is_up(elem['name'], key):
                            info += f"{color} {count:02d} {'▬'*(int(count/4)+1)}\033[0m {elem['name']}\n"
                        else:
                            info += f"{color} {count:02d} {'▬'*(int(count/4)+1)}\033[0m {elem['name']}\033[31m (歪 \033[0m\n"
                        count = 0                
                color = '\033[32m' if count < 30 else '\033[33m' if count < 60 else '\033[31m'
                info += f"{color} {count:02d} {'▬'*(int(count/4)+1)}\033[0m 目前累積"
                
                print(info)

            with open(f"{self.game['name_en']}_{self.player_id}.json", 'w', encoding='utf8') as jf:
                jf.write(json.dumps(old_datas, ensure_ascii=False))
    
    def check_is_up(self, name, pool):
        if self.game['name_en'] == 'star_rail':
            if name in (self.game['normal_weapon']+self.game['normal_character']) and pool in ['11', '12']:
                return False
            else:
                return True
        
        elif self.game['name_en'] == 'genshin':
            if name in (self.game['normal_weapon']+self.game['normal_character']) and pool in ['301', '302', '400']:
                return False
            else:
                return True
    
    def close(self):
        key = input('\n按 Enter 關閉視窗...')
        return
        


if __name__ == '__main__':
    mihoyo = GachaAnalysis()
    mihoyo.select_game()
    mihoyo.find_game_path()
    mihoyo.read_data2()
    mihoyo.get_gacha_log()
    mihoyo.close()