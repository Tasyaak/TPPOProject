после проставления (строковых) меток надо сделать
```python
df.to_sql("temp_table", conn,
    dtype={
        "source_code": "text",
        "error_text": "text",
        "error_line": "integer",
        "ctx": "json",
        "code_tokens": "json", # ручная сериализация, потом парсинг
        "code_numeric": "json",
        "normalized_error_text": "text"
    })
```
последний разобранный - "C2146"

чекнуть по времени и при необходимости оптимизировать `normalize_source_code`

ids_not_in_train = [
# C2065
# непонятный main
430, 431, 434, 437, 442, 443, 444, 459, 460, 464,
64928, 
# C2187
# подключить библиотеку
2813
# C2143
97264,
# C2146
15971, 77142, 105064, 105065, 121104, 131125
]

C2065:
# первые 100
ids_FIX_NAME_SPELLING = [
    10, 23, 54, 84, 85, 121, 166, 220, 257, 258, 347, 350, 393, 400, 412, 413, 414, 415, 419, 420, 424, 426, 458, 468, 497, 498, 507, 508
]
ids_HEADER_OR_STD_NAMESPACE = [
    
]
ids_DECL_BEFORE_USE = [
    145132
]

C2187:
# первые 50
ids_INCORRECT_SYNTAX = [
    2399, 8191
]