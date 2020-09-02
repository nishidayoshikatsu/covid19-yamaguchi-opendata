# covid19-yamaguchi-opendata

## What is this

[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/www/index.html)に掲載されている[新型コロナウイルス感染症の山口県内での発生状況](https://yamaguchi-opendata.jp/ckan/dataset/f6e5cff9-ae43-4cd9-a398-085187277edf)のデータをjsonとして出力するPythonスクリプトです

## Scheduling

GitHub Actionsにより15分に1回、gh-pagesブランチのデータを更新しています

## Output

Json APIで提供しています。

|Content|Source|Json API|
|:---|:---|:---|
|最終更新日|なし|[last_update.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/last_update.json)|
|最新のお知らせ|[山口県公式サイト](https://www.pref.yamaguchi.lg.jp/cms/a15200/kansensyou/202004240001.html)|[news.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/news.json)|
|陽性患者数|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/f56e6552-4c5d-4ec6-91c0-090f553e0aea)|[patients_cnt.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/patients_cnt.json)|
|陽性患者の属性|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/f56e6552-4c5d-4ec6-91c0-090f553e0aea)|[patients.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/patients.json)|
|検査実施件数|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/21b7caeb-05b2-401b-8245-28757de8f444)|[inspections.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/inspections.json)||検査陽性者の状況|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/1a5f9bca-3216-45df-8a99-5c591df8f628)|[hospitalizations.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/hospitalizations.json)|
|検査実施人数|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/21b7caeb-05b2-401b-8245-28757de8f444)|[inspections_person.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/inspections_person.json)|
|相談件数|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/7f2f7b7c-48de-4c41-86ae-bef45da8aeaa)|[querents.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/querents.json)|
|山口県内感染者発生状況1|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/f56e6552-4c5d-4ec6-91c0-090f553e0aea)|[map_update.json](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/map_update.json)|
|山口県内感染者発生状況2|[山口県オープンデータカタログサイト](https://yamaguchi-opendata.jp/ckan/dataset/350001-covid19/resource/f56e6552-4c5d-4ec6-91c0-090f553e0aea)|[yamaguchi-map.png](https://nishidayoshikatsu.github.io/covid19-yamaguchi-opendata/yamaguchi-map.png)|