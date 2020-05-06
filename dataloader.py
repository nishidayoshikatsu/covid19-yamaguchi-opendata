import datetime
import csv
import json
import glob
import os
import urllib.request
import jsonschema
import config
import schemas
import sys
import numpy as np
import collections
import shutil
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
from collections import Counter

from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

class CovidDataManager:
    #日本標準時
    JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")

    #設定ファイル
    REMOTE_SOURCES = config.REMOTE_SOURCES #外部ファイルの参照設定
    HEADER_TRANSLATIONS = config.HEADER_TRANSLATIONS #headerの変換一覧
    INT_CAST_KEYS = config.INT_CAST_KEYS #intにキャストすべきkey
    CODECS = config.CODECS #ファイルエンコーディングリスト

    #バリデーション用のスキーマ定義
    SCHEMAS = schemas.SCHEMAS

    def __init__(self):
        now = datetime.datetime.now(self.JST)
        self.now_str = now.strftime("%Y/%m/%d %H:%M")

        self.data = {
            "last_update":self.now_str,
        }

    def fetch_datas(self):
        for key in self.REMOTE_SOURCES:
            print(key)
            datatype = self.REMOTE_SOURCES[key]['type']
            dataurl = self.REMOTE_SOURCES[key]['url']
            data = {}
            if datatype == 'csv':
                data = self.import_csv_from(dataurl)
            else:
                sys.exit("Unsupported file type")

            self.data[key] = data

    def import_csv_from(self, csvurl):
        request_file = urllib.request.urlopen(csvurl)
        if not request_file.getcode() == 200:
            sys.exit("HTTP status: " + str(request_file.getcode()))
        f = self.decode_csv(request_file.read())
        #filename = os.path.splitext(os.path.basename(csvurl))[0]
        datas = self.csvstr_to_dicts(f)

        return {
            'last_update': self.now_str,
            'data': datas
        }

    #デコード出来るまでCODECS内全コーデックでトライする
    def decode_csv(self, csv_data)->str:
        print('csv decoding')
        for codec in self.CODECS:
            try:
                csv_str = csv_data.decode(codec)
                print('ok:' + codec)
                return csv_str
            except:
                print('ng:' + codec)
                continue
        print('Appropriate codec is not found.')

    #CSV文字列を[dict]型に変換
    def csvstr_to_dicts(self, csvstr) -> list:
        datas = []
        rows = [row for row in csv.reader(csvstr.splitlines())]
        header = rows[0]
        header = self.translate_header(header)
        maindatas = rows[1:]
        for d in maindatas:
            #空行はスキップ
            if d == []:
                continue
            data = {}
            for i in range(len(header)):
                data[header[i]] = d[i]
                if header[i] in self.INT_CAST_KEYS:
                    data[header[i]] = int(d[i])
            datas.append(data)
        return datas

    #HEADER_TRANSLATIONSに基づきデータのヘッダ(key)を変換
    def translate_header(self, header:list)->list:
        for i in range(len(header)):
            for key in self.HEADER_TRANSLATIONS:
                if header[i] == key:
                    header[i] = self.HEADER_TRANSLATIONS[key]
        return header

    #生成されるjsonの正当性チェック
    def validate(self):
        for key in self.data:
            jsonschema.validate(self.data[key], self.SCHEMAS[key])

    def export_jsons(self, directory='origin_data/'):
        for key in self.data:
            print(key + '.json')
            self.export_json_of(key, directory)

    def export_json_of(self, key, directory='origin_data/'):
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(directory + key + '.json', 'w', encoding='utf-8') as f:
            json.dump(self.data[key], f, indent=4, ensure_ascii=False)

class GraphData:
    def __init__(self):
        self.outfile = [
            "last_update.json",
            "patients_cnt.json",
            "patients.json",
            "inspections.json",
            "hospitalizations.json",
            "querents.json",
            "map_update.json"
        ]

        #origin_file_list = glob.glob("./origin_data/*.json")
        #print(origin_file_list)

    def main(self):
        self.generate_update()
        self.generate_patients_cnt()
        self.generate_patients()
        self.generate_inspections()
        self.generate_hospitalizations()
        self.generate_querents()
        self.generate_maps()

    def generate_update(self, origin_directory='origin_data/', out_directory='data/'):
        if not os.path.exists(out_directory):
            os.makedirs(out_directory)
        shutil.copyfile(origin_directory+self.outfile[0], out_directory+self.outfile[0])

    def generate_patients_cnt(self, origin_directory='origin_data/', out_directory='data/'):
        with open(origin_directory + "patients.json", encoding='utf-8') as f:
            data = json.load(f)
        with open("previous_data/patients_cnt.json", encoding='utf-8') as f:
            prev_data = json.load(f)
        prev_data["last_update"] = data["last_update"]

        prev_data = self.add_patiennts_data(prev_data, data)

        with open(out_directory+ self.outfile[1], 'w') as f:
            json.dump(prev_data, f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def generate_patients(self, origin_directory='origin_data/', out_directory='data/'):
        with open(origin_directory + "patients.json", encoding='utf-8') as f:
            data = json.load(f)
        #out = [{elem:dic[elem] for elem in dic if not (elem in ['都道府県名', '全国地方公共団体コード'])} for dic in data["data"]]
        out = []
        for dic in data["data"]:
            dic["居住地"] = dic.pop("市区町村名")
            dic["年代"] = dic.pop("患者_年代")
            dic["性別"] = dic.pop("患者_性別")
            dic["公表日"] = self.format_date(dic["公表日"]) + "T08:00:00.000Z"
            dic["陽性確定日"] = self.format_date(dic["陽性確定日"]) + "T08:00:00.000Z"
            del_list = ['都道府県名', '全国地方公共団体コード']
            [dic.pop(d) for d in del_list]
            out.append(dic)
        data["data"] = out
        with open(out_directory+ self.outfile[2], 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def generate_inspections(self, origin_directory='origin_data/', out_directory='data/'):
        with open(origin_directory + "inspections.json", encoding='utf-8') as f:
            data = json.load(f)
        with open("previous_data/inspections.json", encoding='utf-8') as f:
            prev_data = json.load(f)
        out = []
        for dic in data["data"]:
            dic["日付"] = dic.pop("実施年月日")
            dic["日付"] = self.format_date(dic["日付"])
            dic["日付"] += "T08:00:00.000Z"
            dic["小計"] = dic.pop("検査実施_件数")
            del_list = ['全国地方公共団体コード', '都道府県名', '市区町村名', '備考']
            [dic.pop(d) for d in del_list]
            out.append(dic)

        prev_data["data"].extend(out)
        # 昨日までのデータがない場合は暫定で最後のデータを入力
        # 土日だけ抜けてるとめんどくさい...月曜に土日のデータもいれてほしい
        prev_data = self.add_data(prev_data, data)
        prev_data["last_update"] = data["last_update"]
        with open(out_directory+ self.outfile[3], 'w') as f:
            json.dump(prev_data, f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def generate_hospitalizations(self, origin_directory='origin_data/', out_directory='data/'):
        with open(origin_directory + "inspections_people.json", encoding='utf-8') as f:
            data = json.load(f)
        with open(origin_directory + "hospitalizations.json", encoding='utf-8') as f:
            data2 = json.load(f)
        with open("previous_data/hospitalizations.json", encoding='utf-8') as f:
            prev_data = json.load(f)

        prev_data["last_update"] = data2["last_update"]
        prev_data["data"][0]["検査実施人数"] = data["data"][-1]["検査実施_人数 "]
        prev_data["data"][0]["入院中"] = data2["data"][-1]["入院"]
        prev_data["data"][0]["退院"] = data2["data"][-1]["退院"]
        prev_data["data"][0]["死亡"] = data2["data"][-1]["死亡"]
        prev_data["data"][0]["陽性患者数"] = data2["data"][-1]["入院"] + data2["data"][-1]["退院"]

        with open(out_directory+ self.outfile[4], 'w') as f:
            json.dump(prev_data, f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def generate_querents(self, origin_directory='origin_data/', out_directory='data/'):
        with open(origin_directory + "querents.json", encoding='utf-8') as f:
            data = json.load(f)
        with open("previous_data/querents.json", encoding='utf-8') as f:
            prev_data = json.load(f)
        out = []
        for dic in data["data"]:
            dic["日付"] = dic.pop("受付_年月日")
            dic["日付"] = self.format_date(dic["日付"])
            dic["日付"] += "T08:00:00.000Z"
            dic["小計"] = dic.pop("相談件数")
            del_list = ['全国地方公共団体コード', ' 都道府県名', ' 市区町村名 ']
            [dic.pop(d) for d in del_list]
            out.append(dic)

        prev_data["data"].extend(out)
        # 昨日までのデータがない場合は暫定で最後のデータを入力
        # 土日だけ抜けてるとめんどくさい...月曜に土日のデータもいれてほしい
        prev_data = self.add_data(prev_data, data)
        prev_data["last_update"] = data["last_update"]
        with open(out_directory+ self.outfile[5], 'w') as f:
            json.dump(prev_data, f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def generate_maps(self, origin_directory='origin_data/', out_directory='data/'):
        with open(origin_directory + "patients.json", encoding='utf-8') as f:
            data = json.load(f)
        city_list = [
            "下関市", "宇部市", "山口市", "萩市", "防府市", "下松市", "岩国市", "光市", "長門市", "柳井市",
            "美祢市", "周南市", "山陽小野田市", "周防大島町", "和木町", "上関町", "田布施町", "平生町", "阿武町"
        ]
        num_list = np.zeros(len(city_list), int).tolist()
        city_dict = dict(zip(city_list, num_list))	# 各自治体の陽性患者人数のdictを作成
        for d in data["data"]:
            city_dict[d["市区町村名"]] += 1
        color_dict = city_dict.copy()
        for key in city_dict.keys():
            if city_dict[key] == 0:
                color_dict[key] = "white"
            elif city_dict[key] <= 5:
                color_dict[key] = "#b8f1d5"
            elif city_dict[key] <= 10:
                color_dict[key] = "#23b16a"
            elif city_dict[key] <= 15:
                color_dict[key] = "#156a40"
            elif color_dict[key] <= 20:
                color_dict[key] = "#0e472b"
            else:
                color_dict[key] = "#031e11"
            #color_num = (city_dict[key] - min(city_dict.values())) / (max(city_dict.values()) - min(city_dict.values()))

        df = gpd.read_file('./N03-190101_35_GML/N03-19_35_190101.shp', encoding='SHIFT-JIS')
        #df = gpd.read_file('./N03-190101_35_GML/N03-19_35_190101.geojson', encoding='SHIFT-JIS')
        df = df[df["N03_004"].isin(city_list)]
        base = df.plot(color="white", edgecolor="black")

        # グラフの枠線を削除
        base.axes.xaxis.set_visible(False)
        base.axes.yaxis.set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().spines['left'].set_visible(False)
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['bottom'].set_visible(False)

        for key in color_dict.keys():
            df[df["N03_004"] == key].plot(ax=base, color=color_dict[key], edgecolor="black") # , color=color_dict[key] , cmap='Greens'
        long_lat = [
            [130.98, 34.08], [131.25, 33.98], [131.48, 34.13], [131.41, 34.38], [131.56, 34.05], [131.88, 34.02],
            [132.13, 34.20], [131.95, 33.98], [131.18, 34.34], [132.12, 33.98], [131.21, 34.18], [131.80, 34.16],
            [131.17, 34.02], [132.21, 33.93], [132.21, 34.19], [132.08, 33.82], [132.03, 33.94], [132.08, 33.93], [131.56, 34.54]
        ]
        city_text = [
            [130.78, 33.70], [131.18, 33.68], [131.30, 33.83], [131.26, 34.69], [131.40, 33.68], [131.60, 33.83],
            [131.64, 33.68], [132.08, 34.57], [130.85, 34.65], [132.32, 34.35], [131.11, 34.56], [131.86, 34.54],
            [130.92, 33.84], [132.32, 34.19], [132.24, 34.50], [132.06, 33.65], [131.80, 33.65], [132.24, 33.65], [131.40, 34.71]
        ]
        city_text2 = [
            [0.03, -0.06], [0.03, -0.06],
            [0.03, -0.06], [0.01, -0.06],
            [0.03, -0.06], [0.03, -0.06],
            [0.03, -0.06], [0.01, -0.06],
            [0.03, -0.06], [0.04, -0.06],
            [0.03, -0.06], [0.03, -0.06],
            [0.10, -0.06], [0.06, -0.06],
            [0.03, -0.06], [0.03, -0.06],
            [0.06, -0.06], [0.03, -0.06],
            [0.03, -0.06]
        ]
        plt_line = [
            [[long_lat[0][0]-x for x in np.arange(0, 0.16, 0.04)], [long_lat[0][1]-y for y in np.arange(0, 0.4, 0.1)]],
            [[long_lat[1][0]]*4, [long_lat[1][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[2][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[2][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[3][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[3][1]+y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[4][0]-x for x in np.arange(0, 0.08, 0.02)], [long_lat[4][1]-y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[5][0]-x for x in np.arange(0, 0.24, 0.06)], [long_lat[5][1]-y for y in np.arange(0.0, 0.16, 0.04)]],
            [[long_lat[6][0]]*4, [long_lat[6][1]+y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[7][0]-x for x in np.arange(0, 0.32, 0.08)], [long_lat[7][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[8][0]-x for x in np.arange(0, 0.32, 0.08)], [long_lat[8][1]+y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[9][0]+x for x in np.arange(0, 0.32, 0.08)], [long_lat[9][1]+y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[10][0]-x for x in np.arange(0, 0.02, 0.005)], [long_lat[10][1]+y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[11][0]+x for x in np.arange(0, 0.16, 0.04)], [long_lat[11][1]+y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[12][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[12][1]-y for y in np.arange(0.0, 0.16, 0.04)]],
            [[long_lat[13][0]+x for x in np.arange(0, 0.24, 0.06)], [long_lat[13][1]+y for y in np.arange(0.0, 0.24, 0.06)]],
            [[long_lat[14][0]+x for x in np.arange(0, 0.12, 0.03)], [long_lat[14][1]+y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[15][0]+x for x in np.arange(0, 0.08, 0.02)], [long_lat[15][1]-y for y in np.arange(0.0, 0.16, 0.04)]],
            [[long_lat[16][0]-x for x in np.arange(0, 0.16, 0.04)], [long_lat[16][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[17][0]+x for x in np.arange(0, 0.28, 0.07)], [long_lat[17][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[18][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[18][1]+y for y in np.arange(0.0, 0.12, 0.03)]],
        ]
        for fig,pline,cname,cplace,cplace2 in zip(long_lat, plt_line, city_list, city_text, city_text2):
            #plt.plot(fig[0], fig[1], marker='.', color="blue", markersize=6)
            base.plot(pline[0], pline[1], color="black", linewidth = 0.5)
            base.text(cplace[0], cplace[1], cname, size=10, color="black")
            #base.text(cplace[0], cplace[1]-0.03, "ー"*len(cname), size=10, color="black")
            base.text(cplace[0]+cplace2[0], cplace[1]+cplace2[1], str(city_dict[cname])+"例", size=11, color="black")
        plt.savefig(out_directory+"yamaguchi-map.png")
        #plt.show()
        with open(out_directory+ self.outfile[6], 'w') as f:
            json.dump(data["last_update"], f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def format_date(self, date_str):
        #print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), "JST")).isoformat())
        date_dt = datetime.datetime.strptime(date_str, "%Y/%m/%d")

        return date_dt.strftime("%Y-%m-%d")

    def add_patiennts_data(self, prev_data, data):
        lastday = prev_data["data"][-1]["日付"][:10]
        lastday = datetime.date(int(lastday[:4]), int(lastday[5:7]), int(lastday[8:10]))
        today = datetime.date.today()	# timezoneはどうなるのか調査が必要
        period = today - lastday
        daily_cnt = self.daily_patients(data["data"])
        if period.days == 0:
            if today in daily_cnt.keys():
                prev_data["data"][-1]["小計"] = daily_cnt[today]
        for d in range(period.days):
            write_day = lastday + datetime.timedelta(days=d+1)
            if write_day not in daily_cnt.keys():
                print("この日の陽性患者はいません")
                pat_num = 0
            else:
                pat_num = daily_cnt[write_day]
            prev_data["data"].append(
				{
					"日付": write_day.strftime("%Y-%m-%d") + "T08:00:00.000Z",
					"小計": pat_num
				}
			)
            print(write_day)

        return prev_data

    def daily_patients(self, data):
        date_list = []
        for d in data:
            date_str = d.get("公表日")
            dt = self.format_date(date_str)
            dt = datetime.date(int(dt[:4]), int(dt[5:7]), int(dt[8:10]))
            date_list.append(dt)
        c = collections.Counter(date_list)
        return c

    def add_data(self, prev_data, data):
        lastday = prev_data["data"][-1]["日付"][:10]
        lastday = datetime.date(int(lastday[:4]), int(lastday[5:7]), int(lastday[8:10]))
        today = datetime.date.today()	# timezoneはどうなるのか調査が必要
        period = today - lastday
        if period.days == 1: # こちらの場合はorigin_dataが対応してない土日だけ考えれば良い
            return prev_data
        for d in range(1, period.days):
            write_day = lastday + datetime.timedelta(days=d)
            prev_data["data"].append(
				{
					"日付": write_day.strftime("%Y-%m-%d") + "T08:00:00.000Z",
					"小計": prev_data["data"][-1]["小計"]
				}
			)
            print(write_day)

        return prev_data

    def decide_color(self):
        print("start")

if __name__ == "__main__":
    gd = GraphData()
    gd.main()