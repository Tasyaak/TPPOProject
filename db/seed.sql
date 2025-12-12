INSERT INTO error_codes(error_code) VALUES
    ('C2065'), -- использование необъявленной переменной или типа данных / не подключён заголовок
    ('C3861'), -- использование необъявленной функции / не подключён заголовок с етой функцией / неправильное обращение к члену класса
    ('C2143'), -- синтаксическая ошибка с двумя токенами, выше пропущена скобка или разделитель
    ('C2146'), -- синтаксическая ошибка с токеном перед идентификатором / забыта перед идентификатором ;
    ('C2059'), -- синтаксическая ошибка с одним токеном, часто связано с макросами #define, выше или здесь пропущена или вставлены лишние символы, скобка, запятая, оператор или неверно завершена предыдущая конструкция
    ('C1075'), -- количество скобок не сбалансировано
    ('C1083'), -- неправильное название библиотеки
    ('C2131'), -- использование неконстантного выражения, где нужна константа
    ('C2440'), -- нужно использовать явное преобразование типов / исправить типы данных для корректного преобразования типов
    ('C2446'), -- исправить типы данных операндов / добавить разыменовывание для корректной работы оператора
    ('C2676'), -- неправильный тип операндов / неправильное использование оператора
    ('C2678'), -- использование бинарного (унарного) оператора с типом левого операнда, для которого он не определён / неправильное использование оператора
    ('C2679'), -- использование бинарного (унарного) оператора с типом правого операнда, для которого он не определён / неправильное использование оператора
    ('C2039'), -- использование имени члена, которого у етого типа нету / забыли подключить заголовок
    ('C2672'), -- нужно привести список аргументов к существующей перегрузке (количество, типы) / убедитесь, шо используется существующая функция
    ('C2144'), -- ожидался токен, но встретился тип, пропущен ;, ), } перед типом или выше
    ('C2187'), -- ожидался токен, пропущен ;, ), } здесь или выше
    ('C2148'), -- слишком большой размер статичного или автоматического массива
    ('C2064'), -- некорректное количество аргументов, переданных в функцию / убедитесь, шо используется существующая функция
    ('C2181'), -- неправильная конструкция с if else из-за фигурных скобок / из-за ;
    ('C2106'); -- одно = в условном выражении / левый операнд является литералом или результатом временного выражения 


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Убедитесь, что перед использованием переменной/типа написано объявление' AS recommendation,
            'DECL_BEFORE_USE' AS recommendation_code
    UNION ALL
    SELECT 'Исправьте имя переменной/типа, проверьте опечатки и регистр',
            'FIX_NAME_SPELLING'
    UNION ALL
    SELECT 'Если это стандартный тип/контейнер, то подключите правильный заголовок #include <...> и/или добавьте std::',
            'HEADER_OR_STD_NAMESPACE'
) AS t
WHERE e.error_code = 'C2065';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Убедитесь, что перед использованием функции/метода написано объявление или прототип' AS recommendation,
            'DECL_BEFORE_USE' AS recommendation_code
    UNION ALL
    SELECT 'Исправьте имя функции/метода, проверьте опечатки и регистр',
            'FIX_NAME_SPELLING'
    UNION ALL
    SELECT 'Если это функция из стандартной библиотеки, то подключите правильный заголовок #include <...> и/или добавьте std::',
            'HEADER_OR_STD_NAMESPACE'
) AS t
WHERE e.error_code = 'C3861';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Перед указанным в сообщении идентификатором пропущена скобка или разделитель. Проверьте, не забыли ли вы закрыть скобку, добавить ; или корректно завершить выражение сразу на месте ошибки' AS recommendation,
            'MISSING_BRACKET_OR_SEP' AS recommendation_code
) AS t
WHERE e.error_code = 'C2143';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Проверьте, не пропущена ли ; в строке выше' AS recommendation,
            'MISSING_SEMICOLON_BEFORE' AS recommendation_code
    UNION ALL
    SELECT 'Убедитесь, что перед идентификатором завершена конструкция или не пропущена скобка или разделитель',
            'INCORRECT_CONSTRUCTION_OR_SYMBOLS'
) AS t
WHERE e.error_code = 'C2146';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Проверьте синтаксис в строке с ошибкой и в 1-2 строках выше, обычно перед или рядом с указанным символом есть пропущенная или лишняя скобка, запятая, оператор, или использован некорректный символ или макрос' AS recommendation,
            'INCORRECT_SYNTAX' AS recommendation_code
) AS t
WHERE e.error_code = 'C2059';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Количество и расположение фигурных скобок {} не сбалансировано. Проверьте структурные блоки, выровняйте отступы и добавьте/удалите фигурные скобки' AS recommendation,
            'INCORRECT_BRACE' AS recommendation_code
) AS t
WHERE e.error_code = 'C1075';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Проверьте, что файл реально существует и путь к нему корректен' AS recommendation,
            'INCORRECT_FILE_INCLUDE' AS recommendation_code
) AS t
WHERE e.error_code = 'C1083';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Выражение использовано в контексте, где требуется константа. Либо сделайте используемое значение constexpr/const, либо используйте динамическую память' AS recommendation,
            'FIX_CONSTEXPR' AS recommendation_code
) AS t
WHERE e.error_code = 'C2131';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Проверьте совместимость типов при инициализации, присваивании или возвращении значения. Измените тип переменной или возвращаемого значения, или добавьте корректный конструктор/преобразование, или измените выражение так, чтобы его тип совпадал с ожидаемым' AS recommendation,
            'FIX_TYPE_FOR_CAST' AS recommendation_code
    UNION ALL
    SELECT 'Используемое преобразование типов недопустимо для указанных типов. Проверьте, что вы выбрали корректный вид приведения и что между типами действительно должно существовать безопасное преобразование',
            'FIX_CAST'
) AS t
WHERE e.error_code = 'C2440';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Оба операнда указанного оператора сравнения должны иметь совместимые типы или приводиться к общему типу. Используйте операнды подходящих типов и при необходимости явно приведите один из операндов к нужному типу или измените логику сравнения' AS recommendation,
            'FIX_TYPE_FOR_COMPARISON' AS recommendation_code
    UNION ALL
    SELECT 'Для указателей решите, вы сравниваете их адреса или содержимое, в последнем случае разыменовывайте или используйте соответствующие функции',
            'FIX_POINTERS_FOR_CAST'
) AS t
WHERE e.error_code = 'C2446';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Указанный оператор был некорректно использован, замените его на корректный' AS recommendation,
            'FIX_OPERATOR' AS recommendation_code
    UNION ALL
    SELECT 'Используемый оператор не определён. При необходимости измените выражение, перегрузите оператор для своего типа или явно приведите операнды к совместимым типам',
            'FIX_EXPR_FOR_OPERATOR'
) AS t
WHERE e.error_code = 'C2676';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Указанный оператор был некорректно использован, замените его на корректный' AS recommendation,
            'FIX_OPERATOR' AS recommendation_code
    UNION ALL
    SELECT 'Приведите левый операнд к ожидаемому типу (снимите const, если по смыслу допустимо, или измените сигнатуру оператора)',
            'FIX_LEFT_OPERAND'
) AS t
WHERE e.error_code = 'C2678';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Указанный оператор был некорректно использован, замените его на корректный' AS recommendation,
            'FIX_OPERATOR' AS recommendation_code
    UNION ALL
    SELECT 'Приведите правый операнд к ожидаемому типу (снимите const, если по смыслу допустимо, или измените сигнатуру оператора)',
            'FIX_RIGHT_OPERAND'
) AS t
WHERE e.error_code = 'C2679';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Подключите необходимый заголовок через #include для первого идентификатора' AS recommendation,
            'ADD_INCLUDE' AS recommendation_code
    UNION ALL
    SELECT 'Проверьте, что вы обращаетесь к существующему члену, не опечатано ли имя, верно ли выбран тип/контейнер/функция/метод и правильный ли оператор доступа (., ->, ::)',
            'FIX_MEMBER'
) AS t
WHERE e.error_code = 'C2039';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Приведите список аргументов к существующей перегрузке указанной функции (количество, типы, const-квалификаторы)' AS recommendation,
            'FIX_FUNC_ARGUMENTS' AS recommendation_code
    UNION ALL
    SELECT 'Подключите необходимый заголовок через #include для указанной функции',
            'ADD_INCLUDE'
    -- UNION ALL
    -- SELECT 'Использована несуществующая функция, исправьте её название',
    --         'FIX_FUNC_NAME'
) AS t
WHERE e.error_code = 'C2672';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Проверьте, не пропущены ли ;, ), { или } в предыдущих строках и завершена ли конструкция перед указанным типом' AS recommendation,
            'MISSING_SEMICOLON_OR_BRACKET' AS recommendation_code
    -- UNION ALL
    -- SELECT 'Написан лишний указанный тип, удалите его',
    --         'DELETE_TYPE'
) AS t
WHERE e.error_code = 'C2144';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Исправьте имя указанного идентификатора, проверьте опечатки и регистр' AS recommendation,
            'FIX_NAME_SPELLING' AS recommendation_code
    UNION ALL
    SELECT 'Проверьте, не является ли указанный идентификатор лишним и завершена ли конструкция перед ним',
            'INCORRECT_SYNTAX'
) AS t
WHERE e.error_code = 'C2187';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Размер статического или автоматического массива слишком велик. Уменьшите количество элементов массива или размер элемента, либо перенесите хранение данных в динамическую память' AS recommendation,
            'TOO_BIG_SIZE' AS recommendation_code
) AS t
WHERE e.error_code = 'C2148';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Согласуйте число аргументов с сигнатурой функции' AS recommendation,
            'FIX_NUM_ARGS_IN_FUNC' AS recommendation_code
    UNION ALL
    SELECT 'Проверьте опечатки и тип вызываемого выражения, действительно ли это функция/метод',
            'FIX_FUNC_NAME'
) AS t
WHERE e.error_code = 'C2064';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Убедитесь, что все if и else расположены в одной логической цепочке, что else написан после соответствующего if и что вы не закрыли блок } до нужного if. При необходимости добавьте фигурные скобки вокруг тел if и else, чтобы явно задать структуру условного оператора' AS recommendation,
            'BRACE_IN_IF_ELSE_STMT' AS recommendation_code
    UNION ALL
    SELECT 'Проверьте строку с if, нету ли после условия if (условие); лишней ;, из-за которой else отцепился от if',
            'SEMICOLON_IN_IF_ELSE_STMT'
) AS t
WHERE e.error_code = 'C2181';


INSERT INTO recommendations (error_code_id, recommendation, recommendation_code)
SELECT e.error_code_id, t.recommendation, t.recommendation_code
FROM error_codes e
CROSS JOIN (
    SELECT 'Был использован оператор присваивания = вместо оператора равенства == в условном выражении' as recommendation,
            'ONE_EQUAL_SIGN_IN_COND_SENTENCE' as recommendation_code
    UNION ALL
    SELECT 'Оператор присваивания и составные операторы требуют, чтобы слева стояла переменная, элемент массива, разыменованный указатель или другой модифицируемый объект. Убедитесь, что левый операнд — это именно объект, которому можно присвоить новое значение, а не литерал и не результат временного выражения',
            'LEFT_OPERAND_LITER_OR_EXPR'
) AS t
WHERE e.error_code = 'C2106';