INSERT INTO error_codes(error_code) VALUES
    ('C2065');

INSERT INTO recommendation_templates (error_code_id, template)
SELECT e.error_code_id, t.template
FROM error_codes e
CROSS JOIN (
    SELECT 'Объявить переменную/функцию перед использованием' AS template
    UNION ALL
    SELECT 'Подключить заголовок с объявлением идентификатора (#include ...)'
) AS t
WHERE e.error_code = 'C2065';