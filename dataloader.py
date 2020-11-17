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
import matplotlib.patches as patches
from collections import Counter
import japanize_matplotlib
import requests
from bs4 import BeautifulSoup
import re
import feedparser
import locale
import calendar


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
            #print(key)
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
            "inspections_person.json",
            "hospitalizations.json",
            "querents.json",
            "map_update.json",
            "news.json"
        ]

        #origin_file_list = glob.glob("./origin_data/*.json")
        #print(origin_file_list)

    def main(self):
        self.generate_update()
        self.generate_patients_cnt()
        self.generate_patients()
        self.generate_inspections()
        self.generate_inspections_person()
        self.generate_hospitalizations()
        self.generate_querents()
        self.generate_maps()
        #self.generate_news()
        self.generate_eqal_news()

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

    def generate_inspections_person(self, origin_directory='origin_data/', out_directory='data/'):
        with open(origin_directory + "inspections_people.json", encoding='utf-8') as f:
            data = json.load(f)
        with open("previous_data/inspections_person.json", encoding='utf-8') as f:
            prev_data = json.load(f)
        out = []
        for dic in data["data"]:
            dic["日付"] = dic.pop("実施_年月日")
            dic["日付"] = self.format_date(dic["日付"])
            dic["日付"] += "T08:00:00.000Z"
            dic["小計"] = dic.pop("検査実施_人数 ")
            del_list = ['全国地方公共団体コード', '都道府県名 ', '市区町村名 ', '備考']
            [dic.pop(d) for d in del_list]
            out.append(dic)

        prev_data["data"].extend(out)
        # 昨日までのデータがない場合は暫定で最後のデータを入力
        # 土日だけ抜けてるとめんどくさい...月曜に土日のデータもいれてほしい
        prev_data = self.add_data(prev_data, data)
        prev_data["last_update"] = data["last_update"]
        with open(out_directory + self.outfile[4], 'w') as f:
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
        prev_data["data"][0]["陽性患者数"] = data2["data"][-1]["入院"] + data2["data"][-1]["退院"] + data2["data"][-1]["死亡"]

        with open(out_directory+ self.outfile[5], 'w') as f:
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
        with open(out_directory+ self.outfile[6], 'w') as f:
            json.dump(prev_data, f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def generate_maps(self, origin_directory='origin_data/', out_directory='data/'):
       
        with open(origin_directory + "patients.json", encoding='utf-8') as f:
            data = json.load(f)
        city_list = [
            "下関市", "宇部市", "山口市", "萩市", "防府市", "下松市", "光市", "岩国市", "長門市", "柳井市",
            "美祢市", "周南市", "山陽小野田市", "周防大島町", "和木町", "上関町", "田布施町", "平生町", "阿武町"
        ]
        num_list = np.zeros(len(city_list), int).tolist()
        city_dict = dict(zip(city_list, num_list))	# 各自治体の陽性患者人数のdictを作成
        heat_colorlist = ["#b8f1d5", "#23b16a", "#156a40", "#0e472b", "#031e11"]
        for d in data["data"]:
            if d["市区町村名"] in city_dict: city_dict[d["市区町村名"]] += 1
            else: continue
        color_dict = city_dict.copy()
        for key in city_dict.keys():
            if city_dict[key] == 0:
                color_dict[key] = "white"
            elif city_dict[key] <= 10:
                color_dict[key] = "#b8f1d5"
            elif city_dict[key] <= 20:
                color_dict[key] = "#23b16a"
            elif city_dict[key] <= 30:
                color_dict[key] = "#156a40"
            elif color_dict[key] <= 40:
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
            [132.08, 34.20], [131.95, 33.98], [131.18, 34.34], [132.12, 33.98], [131.21, 34.18], [131.80, 34.16],
            [131.17, 34.02], [132.25, 33.92], [132.21, 34.19], [132.04, 33.82], [132.03, 33.94], [132.08, 33.93], [131.56, 34.54]
        ]
        city_text = [
            [130.70, 33.70], [131.16, 33.66], [131.29, 33.82], [131.26, 34.72], [131.41, 33.66], [131.56, 33.82],
            [131.64, 33.66], [132.08, 34.57], [130.82, 34.67], [132.32, 34.35], [131.09, 34.58], [131.82, 34.54],
            [130.86, 33.82], [132.32, 34.19], [132.28, 34.53], [132.065, 33.62], [131.80, 33.62], [132.28, 33.62], [131.40, 34.78]
        ]
        city_text2 = [
            [0.04, -0.07], [0.04, -0.07],
            [0.04, -0.07], [0.00, -0.07],
            [0.04, -0.07], [0.04, -0.07],
            [0.00, -0.07], [0.04, -0.07],
            [0.04, -0.07], [0.04, -0.07],
            [0.04, -0.07], [0.04, -0.07],
            [0.13, -0.07], [0.10, -0.07],
            [0.04, -0.07], [0.04, -0.07],
            [0.07, -0.07], [0.04, -0.07],
            [0.04, -0.07]
        ]
        plt_line = [
            [[long_lat[0][0]-x for x in np.arange(0, 0.24, 0.06)], [long_lat[0][1]-y for y in np.arange(0, 0.4, 0.1)]],
            [[long_lat[1][0]]*4, [long_lat[1][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[2][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[2][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[3][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[3][1]+y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[4][0]-x for x in np.arange(0, 0.08, 0.02)], [long_lat[4][1]-y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[5][0]-x for x in np.arange(0, 0.28, 0.07)], [long_lat[5][1]-y for y in np.arange(0.0, 0.18, 0.045)]],
            [[long_lat[6][0]+x for x in np.arange(0, 0.12, 0.03)], [long_lat[6][1]+y for y in np.arange(0.0, 0.36, 0.09)]],
            [[long_lat[7][0]-x for x in np.arange(0, 0.32, 0.08)], [long_lat[7][1]-y for y in np.arange(0.0, 0.36, 0.09)]],
            [[long_lat[8][0]-x for x in np.arange(0, 0.32, 0.08)], [long_lat[8][1]+y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[9][0]+x for x in np.arange(0, 0.32, 0.08)], [long_lat[9][1]+y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[10][0]-x for x in np.arange(0, 0.02, 0.005)], [long_lat[10][1]+y for y in np.arange(0.0, 0.40, 0.10)]],
            [[long_lat[11][0]+x for x in np.arange(0, 0.14, 0.035)], [long_lat[11][1]+y for y in np.arange(0.0, 0.38, 0.095)]],
            [[long_lat[12][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[12][1]-y for y in np.arange(0.0, 0.16, 0.04)]],
            [[long_lat[13][0]+x for x in np.arange(0, 0.28, 0.07)], [long_lat[13][1]+y for y in np.arange(0.0, 0.24, 0.06)]],
            [[long_lat[14][0]+x for x in np.arange(0, 0.16, 0.04)], [long_lat[14][1]+y for y in np.arange(0.0, 0.34, 0.085)]],
            [[long_lat[15][0]+x for x in np.arange(0, 0.14, 0.035)], [long_lat[15][1]-y for y in np.arange(0.0, 0.18, 0.045)]],
            [[long_lat[16][0]-x for x in np.arange(0, 0.12, 0.03)], [long_lat[16][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[17][0]+x for x in np.arange(0, 0.36, 0.09)], [long_lat[17][1]-y for y in np.arange(0.0, 0.32, 0.08)]],
            [[long_lat[18][0]-x for x in np.arange(0, 0.08, 0.02)], [long_lat[18][1]+y for y in np.arange(0.0, 0.18, 0.045)]],
        ]
        for fig,pline,cname,cplace,cplace2 in zip(long_lat, plt_line, city_list, city_text, city_text2):
            #plt.plot(fig[0], fig[1], marker='.', color="blue", markersize=6)
            base.plot(pline[0], pline[1], color="black", linewidth = 0.8)
            base.text(cplace[0], cplace[1], cname, size=10, color="black")
            #base.text(cplace[0], cplace[1]-0.03, "ー"*len(cname), size=10, color="black")
            base.text(cplace[0]+cplace2[0], cplace[1]+cplace2[1], str(city_dict[cname])+"人", size=11, color="black")

        base.text(131.88, 35.30, "陽性患者数【人】", size=12, color="black")
        base.add_patch(patches.Rectangle(xy=(131.80, 34.70), width=0.71, height=0.55, ec="black", fill=False))
        for i,heat in enumerate(heat_colorlist):
            base.add_patch(patches.Rectangle(xy=(131.83, 35.12-i*0.1), width=0.25, height=0.1, fc=heat, ec="black", fill=True))
            if i == 4:
                base.text(132.09, 35.05-i*0.1+0.1, "・・・"+str(10*i+1)+"以上")
            else:
                base.text(132.09, 35.05-i*0.1+0.1, "・・・"+str(10*i+1)+"-"+str(10*(i+1)))

        plt.savefig(out_directory+"yamaguchi-map.png", bbox_inches='tight')
        #plt.show()
        with open(out_directory+ self.outfile[7], 'w') as f:
            json.dump(data["last_update"], f, ensure_ascii=False, indent=4, separators=(',', ': '))

    def generate_news(self, origin_directory='origin_data/', out_directory='data/'):
        with open("previous_data/"+self.outfile[8], encoding='utf-8') as f:
            prev_data = json.load(f)

        pat_url = "https://www.pref.yamaguchi.lg.jp/cms/a10000/korona2020/202004240002.html"
        newinfo_url = "https://www.pref.yamaguchi.lg.jp/press/rss.xml"
        pat_date,pat_num = self.new_patients(pat_url)
        newinfo = self.new_info(newinfo_url)

        pat_dt = datetime.datetime(int(pat_date[:4]), int(pat_date[5:7]), int(pat_date[8:]))
        insert_index = 0
        for info in newinfo:
            info_dt = datetime.datetime(int(info[0][:4]), int(info[0][5:7]), int(info[0][8:]))
            if pat_dt < info_dt:
                insert_index += 1
            date, url, text = info
            prev_data["newsItems"].append(
				{
					"date": date,
					"url": url,
					"text": text
				}
			)

        prev_data["newsItems"].insert(
            insert_index,
			{
				"date": pat_date,
				"url": pat_url,
				"text": "山口県内で"+str(pat_num)+"例目となる新型コロナウイルス感染症の感染者を確認"
			}
		)

        with open(out_directory+ self.outfile[8], 'w') as f:
            json.dump(prev_data, f, ensure_ascii=False, indent=4, separators=(',', ': '), sort_keys=True)

    def generate_eqal_news(self, origin_directory='origin_data/', out_directory='data/'):
        with open("previous_data/"+self.outfile[8], encoding='utf-8') as f:
            prev_data = json.load(f)

        newinfo_url = "https://www.pref.yamaguchi.lg.jp/press/rss.xml"
        newinfo = self.new_info(newinfo_url)

        pat_dt = datetime.datetime(int(2020), int(5), int(5))
        insert_index = 0
        for info in newinfo:
            info_dt = datetime.datetime(int(info[0][:4]), int(info[0][5:7]), int(info[0][8:]))
            if pat_dt < info_dt:
                insert_index += 1
            date, url, text = info
            prev_data["newsItems"].append(
				{
					"date": date,
					"url": url,
					"text": text
				}
			)

        prev_data["newsItems"].insert(
            insert_index,
			{
                "date": "2020/11/17",
                "text": "山口県内で269〜280例目となる新型コロナウイルス感染症の感染者を確認",
                "url": "https://www.pref.yamaguchi.lg.jp/cms/a15200/kansensyou/202011170001.html"
            }
		)

        with open(out_directory+ self.outfile[8], 'w') as f:
            json.dump(prev_data, f, ensure_ascii=False, indent=4, separators=(',', ': '), sort_keys=True)

    def format_date(self, date_str):
        #print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), "JST")).isoformat())
        date_dt = datetime.datetime.strptime(date_str, "%Y/%m/%d")

        return date_dt.strftime("%Y-%m-%d")

    def format_date2(self, date_str):
        #print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), "JST")).isoformat())
        date_dt = datetime.datetime.strptime(str(datetime.date.today().year)+"年"+date_str, "%Y年%m月%d日")

        return date_dt.strftime("%Y/%m/%d")

    def format_date3(self, date_str):
        #print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), "JST")).isoformat())
        #locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')	# 英語表記なのでロケールを変更
        #date_dt = datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
        # Sat, 2 May 2020 10:00:00 JST
        #date_str = re.findall(r'[0-9]{1,2} ', date_str)
        date_strlist = date_str.split(" ")[1:4]

        months = {
			"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
			"Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
		}

        if len(date_strlist[0]) == 1:
            date_day = "0" + date_strlist[0]
        else:
            date_day = date_strlist[0]

        return date_strlist[2]+"/"+months[date_strlist[1]]+"/"+date_day

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
                #print("この日の陽性患者はいません")
                pat_num = 0
            else:
                pat_num = daily_cnt[write_day]
            prev_data["data"].append(
				{
					"日付": write_day.strftime("%Y-%m-%d") + "T08:00:00.000Z",
					"小計": pat_num
				}
			)
            #print(write_day)

        return prev_data

    def daily_patients(self, data):
        date_list = []
        for d in data:
            date_str = d.get("公表日")
            dt = self.format_date(date_str)
            dt = datetime.date(int(dt[:4]), int(dt[5:7]), int(dt[8:10]))
            if '欠番' not in d.get('備考'):
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
            #print(write_day)

        return prev_data

    def new_patients(self, url):
        res = requests.get(url)
        res.encoding = res.apparent_encoding	# 日本語文字化け対応
        soup = BeautifulSoup(res.text, 'html.parser')
        out = soup.find('span', class_="fs3").get_text()
        lists = re.findall(r'[1-9][0-9]*', out)
        patients_num = max(lists)
        #print(out, patients_num)

        out2 = soup.find('h2', class_="mn0").get_text()
        lists = re.findall(r'[1-9][0-9]?月[1-9][0-9]?日', out2)
        patients_date = self.format_date2(lists[0])

        return patients_date, patients_num

    # RSSを用いて最新の3件のデータを取得
    def new_info(self, url):
        rss = feedparser.parse(url)
        entries_data = rss.entries[:3]	# 新しい3件のデータを取得
        #newdata = []
        #for i in entries_data:
        #    newdata.append([self.format_date3(i.published), i.link, self.delete_date(i.title)])

        newdata = [[self.format_date3(i.published), i.link, self.delete_date(i.title)] for i in entries_data]

        return newdata

    def delete_date(self, text):
        out = re.sub(r'（[1-9][0-9]?月[1-9][0-9]?日）', '', text)

        return out

if __name__ == "__main__":
    gd = GraphData()
    gd.main()
