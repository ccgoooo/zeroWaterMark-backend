import greyscaleImage


def comparisonInfomation(dict1,dict2,column_names):
    # 比较两个字典的不同
    different_keys = []
    for key in column_names:
        if dict1[key] != dict2[key]:
            different_keys.append(key)

    info_err = {
        '用户角色': "用户身份错误",
        '生成时间':"时间不一致",
        '用户ID': "用户ID错误",
        '用户名': "用户不一致",
        '用户IP': "IP地址不一致",
        '所属机构': "用户所属机构错误",
        '零水印': "零水印异动"
    }
    mock_data = {
        "code": 200,
        "data": {
            "comparsionData": []
        }
    }
    print(different_keys)
    for key in different_keys:
        dic = {}
        dic["field"] = key
        dic["comparisonReason"] = info_err[key]
        dic["comparisonCode"] = 1
        if key != "零水印":
            dic["isPicture"] = 0
            dic["value1"] = dict2[key]
            dic["value2"] = dict1[key]
        else:
            dic["isPicture"] = 1
            dic["value1"] = greyscaleImage.hex_to_32x32_binary_image(dict2['零水印'])
            print(dic["value1"])
            dic["value2"] = greyscaleImage.hex_to_32x32_binary_image(dict1['零水印'])
        mock_data["data"]["comparsionData"].append(dic)
    return mock_data