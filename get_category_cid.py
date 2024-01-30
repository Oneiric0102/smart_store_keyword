import requests
import json
import time

file_path = "./category_cid.json"
base_url = "https://datalab.naver.com/shoppingInsight/getCategory.naver?cid="
headers = {
    "Referer": ("https://datalab.naver.com/shoppingInsight/sCategory.naver"),
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36"
    ),
}
cnt = 0

result = {"name": "전체", "cid": 0, "childList": []}

top_response = requests.get(base_url + str(result["cid"]), headers=headers).json()
top_childList = []
for child in top_response.get("childList"):
    top_childList.append(
        {"name": child.get("name"), "cid": child.get("cid"), "childList": []}
    )

    middle_response = requests.get(
        base_url + str(child.get("cid")), headers=headers
    ).json()
    middle_childList = []
    for middle_child in middle_response.get("childList"):
        middle_childList.append(
            {
                "name": middle_child.get("name"),
                "cid": middle_child.get("cid"),
                "childList": [],
            }
        )
        sub_response = requests.get(
            base_url + str(middle_child.get("cid")), headers=headers
        ).json()
        sub_childList = []
        for sub_child in sub_response.get("childList"):
            sub_childList.append(
                {
                    "name": sub_child.get("name"),
                    "cid": sub_child.get("cid"),
                    "childList": [],
                }
            )
            if not sub_child.get("leaf"):
                lowest_response = requests.get(
                    base_url + str(sub_child.get("cid")), headers=headers
                ).json()
                lowest_childList = []
                for lowest_child in lowest_response.get("childList"):
                    lowest_childList.append(
                        {
                            "name": lowest_child.get("name"),
                            "cid": lowest_child.get("cid"),
                            "childList": [],
                        }
                    )
                sub_childList[-1]["childList"] = lowest_childList
            cnt += 1
            time.sleep(0.5)
            print("크롤링 진행중" + str(cnt))
            middle_childList[-1]["childList"] = sub_childList
        top_childList[-1]["childList"] = middle_childList

result["childList"] = top_childList

with open(file_path, "w") as outfile:
    json.dump(result, outfile, indent="\t", ensure_ascii=False)
