def process_user_data(data_list):
    # 防御性编程：如果列表为空，直接返回 0
    if not data_list:
        return 0

    total_age = 0
    valid_count = 0

    for item in data_list:
        # 检查 'age' 键是否存在
        if "age" in item:
            age = item["age"]
            # 检查 age 是否为数值类型 (int 或 float)，并排除布尔值
            if isinstance(age, (int, float)) and not isinstance(age, bool):
                total_age += age
                valid_count += 1
            # 注：如果业务场景允许字符串数字（如 '30'），可在此处使用 try-except 尝试 float(age) 转换

    # 防止没有合法元素时发生 ZeroDivisionError
    if valid_count == 0:
        return 0

    return total_age / valid_count


# 测试数据
test_data = [
    {"name": "Alice", "age": 25},  # 合法: 25
    {"name": "Bob"},  # 非法: 缺少 'age' 键
    {"name": "Charlie", "age": "30"},  # 非法: 'age' 值为字符串类型
]

print("Result:", process_user_data(test_data))
