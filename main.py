import requests
import json
from bs4 import BeautifulSoup
import datetime as dt
import time
import signiturehelper
import os

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# driver = webdriver.Chrome()
# driver.implicitly_wait(time_to_wait=5)

BASE_DIR = "./"
secret_file = os.path.join(BASE_DIR, "secrets.json")

with open(secret_file) as f:
    secrets = json.loads(f.read())


def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        err_msg = f"set the {setting} enviroment variable"
        raise print(err_msg)


ad_api_key = get_secret("AD_API_KEY")
ad_secret_key = get_secret("AD_SECRET_KEY")
ad_customer_id = get_secret("AD_CUSTOMER_ID")

naver_client_id = get_secret("NAVER_CLIENT_ID")
naver_client_secret = get_secret("NAVER_CLIENT_SECRET")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36"
    )
}

keyword_base = {
    "keyword": "",
    "pcQcCnt": "",
    "mobileQcCnt": "",
    "totalQcCnt": "",
    "productsCnt": "",
    "ratio": "",
    "category": "",
}

result = {"keywords": []}
temp_keyword_list = []
duplicate_check_list = []


# 네이버 검색 자동완성어 추출
def naver_search_keyword(coreKeyword):
    url = f"https://ac.search.naver.com/nx/ac?q={coreKeyword}&con=0&frm=nv&ans=2&r_format=json&r_enc=UTF-8&r_unicode=0&t_koreng=1&run=2&rev=4&q_enc=UTF-8&st=100&_callback=_jsonp_5"

    response = requests.get(url, headers=headers)
    json_string = response.text.split("(")[1].replace(")", "")
    auto_keywords = json.loads(json_string)  # dict로 변환

    for auto_words in auto_keywords["items"]:
        for word in auto_words:
            temp_keyword_list.append(word[0].replace(" ", ""))


# 네이버 검색 연관검색어 추출
def naver_search_rel_keyword(coreKeyword):
    url = "https://search.naver.com/search.naver?"
    params = {"where": "web", "fbm": "1", "query": coreKeyword, "page": "2"}

    resp = requests.get(url, params)

    soup = BeautifulSoup(resp.text, "html.parser")
    shop_rel_words = soup.select("div.related_srch > ul > li")

    for i in shop_rel_words:
        temp_keyword_list.append(i.text.replace(" ", ""))


# 네이버 쇼핑 자동완성어 추출
def nshopping_keyword(coreKeyword):
    url = (
        "https://shopping.naver.com/api/modules/gnb/auto-complete?_vc_=1706983611197&keyword="
        + coreKeyword
    )
    response = requests.get(url, headers=headers).json()

    for auto_words in response["items"][1]:
        temp_keyword_list.append(auto_words[0][0].replace(" ", ""))


# 네이버 쇼핑 연관검색어 추출
def nshopping_rel_keyword(coreKeyword):
    shop_rel_url = (
        "https://search.shopping.naver.com/search/all?where=all&frm=NVSCTAB&query="
        + coreKeyword
    )
    shop_rel_response = requests.get(shop_rel_url, headers=headers)
    shop_rel_soup = BeautifulSoup(shop_rel_response.text, "html.parser")
    shop_rel_words = shop_rel_soup.select(
        "div.relatedTags_relation_srh__YG9s7 > ul > li"
    )
    if len(shop_rel_words):
        for li in shop_rel_words:
            temp_keyword_list.append(li.text.replace(" ", ""))


# 네이버 쇼핑인사이트 TOP200 추출
def nshopping_insight_top500(cid):
    date = dt.datetime.now()
    startDate = (
        str(date.year - 1) + "-" + str(date.month).zfill(2) + "-" + str(date.day)
    )
    endDate = str(date.year) + "-" + str(date.month).zfill(2) + "-" + str(date.day)
    url = "https://datalab.naver.com/shoppingInsight/getCategoryKeywordRank.naver"
    headers = {
        "Referer": ("https://datalab.naver.com/shoppingInsight/sCategory.naver"),
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36"
        ),
        "Content-Type": ("application/x-www-form-urlencoded; charset=UTF-8"),
    }

    data = {
        "cid": str(cid),
        "timeUnit": "date",
        "startDate": startDate,
        "endDate": endDate,
        "page": str(1),
        "count": "20",
    }

    for page in range(1, 11):
        data = {
            "cid": str(cid),
            "timeUnit": "date",
            "startDate": startDate,
            "endDate": endDate,
            "page": str(page),
            "count": "20",
        }

        response = requests.post(url, headers=headers, data=data).json()
        for keyword_info in response["ranks"]:
            temp_keyword_list.append(keyword_info["keyword"].replace(" ", ""))
        time.sleep(0.5)


# 네이버 쇼핑에 해당 키워드 검색시 상단 노출 제품 카테고리 추출
def nshopping_get_category(coreKeyword):
    url = "https://search.shopping.naver.com/search/all?"
    params = {"query": coreKeyword}

    resp = requests.get(url, params)

    soup = BeautifulSoup(resp.text, "html.parser")
    category_words = soup.select("div.product_depth__I4SqY")[0]

    span_soup = BeautifulSoup(str(category_words), "html.parser")

    categories = [
        span.text
        for span in span_soup.find_all("span", class_="product_category__l4FWz")
    ]

    result = ">".join(categories)
    return result


# 검색광고 api 헤더 추출용
def get_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(round(time.time() * 1000))
    signature = signiturehelper.Signature.generate(timestamp, method, uri, secret_key)

    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": signature,
    }


# 검색광고 api 사용
def naver_searchad_api(hintKeywords):
    BASE_URL = "https://api.naver.com"
    API_KEY = ad_api_key
    SECRET_KEY = ad_secret_key
    CUSTOMER_ID = ad_customer_id

    uri = "/keywordstool"
    method = "GET"

    params = {}

    params["hintKeywords"] = hintKeywords
    params["showDetail"] = "1"
    params["monthlyMobileQcCnt"] = ">1000"

    response = requests.get(
        BASE_URL + uri,
        params=params,
        headers=get_header(method, uri, API_KEY, SECRET_KEY, CUSTOMER_ID),
    ).json()

    keyword_list = response["keywordList"]

    api_result = []
    for i in range(0, min(100, len(keyword_list))):
        keyword = keyword_list[i]
        if keyword["monthlyMobileQcCnt"] == "< 10":
            continue
        elif float(keyword["monthlyMobileQcCnt"]) >= 1000:
            api_result.append(keyword)

    return api_result


# 네이버 검색 API 사용을 통한 총 상품수 추출
def get_total_products(coreKeyword):
    url = "https://openapi.naver.com/v1/search/shop.json?query=" + coreKeyword
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret,
    }
    response = requests.get(url, headers=headers).json()
    return response["total"]


# 전체 키워드 추출
def get_result():
    for i in range(0, len(temp_keyword_list) // 5):
        keywords = temp_keyword_list[5 * i : 5 * i + 5]
        api_result = naver_searchad_api(keywords)
        time.sleep(0.1)

        for keyword_info in api_result:
            if not keyword_info["relKeyword"] in duplicate_check_list:
                duplicate_check_list.append(keyword_info["relKeyword"])
                keyword = keyword_info["relKeyword"]
                pcQcCnt = int(float(keyword_info["monthlyPcQcCnt"]))
                mobileQcCnt = int(float(keyword_info["monthlyMobileQcCnt"]))
                totalQcCnt = pcQcCnt + mobileQcCnt
                productsCnt = int(float(get_total_products(keyword)))
                print(keyword + " " + str(productsCnt))
                try:
                    category = nshopping_get_category(keyword)
                except:
                    category = "-"

                keyword_instance = {
                    "keyword": keyword,
                    "pcQcCnt": pcQcCnt,
                    "mobileQcCnt": mobileQcCnt,
                    "totalQcCnt": totalQcCnt,
                    "productsCnt": productsCnt,
                    "ratio": round(productsCnt / totalQcCnt, 5),
                    "category": category,
                }
                result["keywords"].append(keyword_instance)
                time.sleep(0.1)


# # 셀러마스터 자동 입력/ 키워드리스트 부분 수정 필요
# def get_seller_master():
#     keyword_list = get_result()
#     keyword_list = list(set(keyword_list))
#     url = "https://whereispost.com/seller/"

#     driver.get(url)

#     for i in range(0, len(keyword_list)):
#         if i % 50 == 0:
#             time.sleep(1)
#             driver.refresh()
#             keyword_input = driver.find_element(By.ID, "keyword")
#             search_button = WebDriverWait(driver, 10).until(
#                 EC.element_to_be_clickable(
#                     (
#                         By.XPATH,
#                         "/html/body/content/div/div[2]/div[2]/div/div/div/div/div/div/div/form/button",
#                     )
#                 )
#             )
#         keyword_input.send_keys(keyword_list[i])
#         search_button.click()

#         table = WebDriverWait(driver, 10).until(
#             EC.presence_of_all_elements_located(
#                 (By.CSS_SELECTOR, "#result > tbody > tr")
#             )
#         )

#         while len(table) < (i + 1) % 50:
#             table = WebDriverWait(driver, 10).until(
#                 EC.presence_of_all_elements_located(
#                     (By.CSS_SELECTOR, "#result > tbody > tr")
#                 )
#             )

#         row = driver.find_element(By.CSS_SELECTOR, "#result > tbody >tr ").text
#         data = row[2:].split(" ")
#         if int(float(data[4].replace(",", ""))) > 0:
#             category = nshopping_get_category(data[0])
#         else:
#             category = "-"

#         keyword = {
#             "keyword": data[0],
#             "pcQcCnt": int(float(data[1].replace(",", ""))),
#             "mobileQcCnt": int(float(data[2].replace(",", ""))),
#             "totalQcCnt": int(float(data[3].replace(",", ""))),
#             "productsCnt": int(float(data[4].replace(",", ""))),
#             "ratio": float(data[5]),
#             "category": category,
#         }
#         result["keywords"].append(keyword)


search_keyword = input("메인 키워드 입력: ")
search_cid = input("카테고리 cid 입력: ")


naver_search_keyword(search_keyword)
naver_search_rel_keyword(search_keyword)
nshopping_rel_keyword(search_keyword)
nshopping_keyword(search_keyword)
nshopping_insight_top500(search_cid)
temp_keyword_list = list(set(temp_keyword_list))
get_result()

file_path = "./" + search_keyword + ".json"
with open(file_path, "w") as outfile:
    json.dump(result, outfile, indent="\t", ensure_ascii=False)
