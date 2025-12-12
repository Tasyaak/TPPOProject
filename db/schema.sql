PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

create table error_codes (
    error_code_id integer primary key,
    error_code text not null
);

create table recommendations (
    recommendation_id integer primary key,
    error_code_id integer references error_codes(error_code_id),
    recommendation text not null,
    recommendation_code text not null,
    is_active integer not null default 1,
    unique(error_code_id, recommendation),
    unique(error_code_id, recommendation_code)
);

create table training_data (
    training_data_id integer primary key,
    label integer references recommendations(recommendation_id),
    error_text text not null,
    normalized_error_text text not null,
    source_code text not null,
    ctx json not null,
    code_tokens json not null, -- ручная сериализация, потом парсинг
    code_numeric json not null,
    is_in_train integer not null default 1
);

create table classification_models (
    classification_model_id integer primary key,
    name text not null,
    description text,
    path text not null,
    accuracy real not null,
    f1score real not null,
    rocauc real not null
);